# Design: Parser-based read-only enforcement and dangerous-SQL filtering

Status: Draft (brainstorm)
Branch: `parser_based_sql_policy`
Component: `awslabs.postgres-mcp-server`

## 1. Background and motivation

`run_query` currently enforces read-only mode and blocks dangerous SQL using
regular expressions over the raw query text (`mutable_sql_detector.py`):

- `MUTATING_KEYWORDS` — keyword denylist gating read-only mode.
- `DANGEROUS_FUNCTIONS` — function-name denylist (dblink, `pg_read_file`,
  `pg_sleep`, `lo_import`, …), rejected in both modes.
- `SECURITY_SENSITIVE_GUCS` — `row_security`, `session_replication_role`,
  rejected in both modes (both `SET` and `set_config()` forms).
- `COPY_PROGRAM_PATTERN` — `COPY … TO/FROM PROGRAM`, rejected in both modes.
- `SUSPICIOUS_PATTERNS` — injection heuristics.
- Lexical normalization (`strip_sql_comments`, `strip_quoted_identifiers`) to
  undo comment- and quote-based evasion.

This is a **denylist over text**, which is structurally unsound:

- **Missing verbs slip through.** `COPY` (and `CALL`, `LOCK`, `DO`, `SET`) were
  absent from the read-only gate, allowing a read-only bypass and — where the
  role is privileged — `COPY … TO PROGRAM` command execution.
- **Lexer tricks evade text matching.** PostgreSQL Unicode-escaped identifiers
  (`U&"pg_read_fil\0065"`) resolve to `pg_read_file` at parse time but do not
  match the name regex. Every text-normalization fix is a game of whack-a-mole
  against the PostgreSQL lexer (dollar-quoting, `UESCAPE`, `E''` escapes, …).

A real parser evaluates the **statement structure**, so identifiers, string
literals, comments, and escape spellings can no longer disguise an operation.
The sibling `redshift-mcp-server` already does this with `sqlglot`
(`sql_guard.py`), giving us a proven in-repo pattern to align with.

Non-goal restatement: this filter is **defense-in-depth, not a security
boundary.** The authoritative control remains the privilege of the database
role the server connects as. This design makes the in-tool layer sound and
maintainable; it does not replace least-privilege role configuration.

## 2. Goals / Non-goals

### Goals
- Replace regex-based read-only detection and dangerous-SQL filtering with a
  parser-based analysis of the SQL structure.
- Enforce, in read-only mode, that only read statements execute.
- Enforce, in **both** modes, that command-execution / SSRF / filesystem /
  security-control-disabling constructs are rejected (`COPY … PROGRAM`,
  dangerous functions, security-sensitive GUC changes).
- Reject multi-statement submissions (defeats stacked queries).
- Fail closed: unparseable, oversized, or ambiguous input is rejected.
- Be robust to identifier/quoting/comment/Unicode-escape evasions by
  construction.
- Preserve currently-allowed legitimate read queries (no regressions for
  ordinary `SELECT` / `WITH … SELECT` usage).

### Non-goals
- Perfect read-only guarantees against function side effects. A `SELECT` that
  calls a volatile/`SECURITY DEFINER` function which writes cannot be detected
  from syntax alone (requires catalog/volatility knowledge). This remains the
  job of the database role. Documented as a limitation.
- Being a general SQL firewall or WAF.
- Blocking application-logic misuse that is expressible as ordinary reads.

## 3. Requirements

### Functional
- FR1: Accept exactly one statement per call; reject zero or multiple
  statements.
- FR2: In read-only mode, allow only read statement classes at the root:
  `SELECT`, `WITH … SELECT` (and other read CTEs), `VALUES`, `SHOW`, `TABLE`,
  and `EXPLAIN` **without** `ANALYZE` whose inner statement is itself read-only.
- FR3: In read-only mode, reject a statement whose tree contains any
  data-modifying or side-effecting node anywhere — not just at the root — so a
  data-modifying CTE (`WITH x AS (INSERT … RETURNING *) SELECT …`) is rejected.
- FR4: In both modes, reject `COPY … TO/FROM PROGRAM` and server-side-file
  `COPY … TO/FROM '<path>'` (command execution / host filesystem). Client-side
  `COPY … TO STDOUT` may be permitted in write mode but is a read-only-mode
  mutation candidate — default to rejecting all `COPY` in read-only mode.
- FR5: In both modes, reject calls to the dangerous-function set (dblink family,
  `pg_read_file`/`pg_read_binary_file`/`pg_ls_dir`/`pg_stat_file`,
  `lo_import`/`lo_export`, `pg_sleep*`, `pg_terminate_backend`/`pg_cancel_backend`,
  advisory-lock family, `pg_notify`, `pg_reload_conf`/`pg_rotate_logfile`),
  matched by resolved function name from the AST (schema-qualified or not).
- FR6: In both modes, reject changes to security-sensitive GUCs
  (`row_security`, `session_replication_role`) via `SET` or `set_config()`.
- FR6a: Name- and string-literal-based checks (FR5 dangerous functions, FR6 GUC
  names) MUST match against a value decoded to PostgreSQL's own
  identifier/string semantics — Unicode escapes (`U&"…"`/`U&'…'`, `UESCAPE`),
  double-quote unwrapping, and case-folding. The chosen parser does **not**
  guarantee this (sqlglot does not decode `U&` — see §5.5), so decoding must be
  performed explicitly (or a PG-fidelity parser used) for these checks;
  otherwise the encoding bypass is carried forward.
- FR7: Fail closed — reject on parse/tokenize error, recursion limit, oversized
  input (`MAX_SQL_LEN`), or an unrecognized root statement type in read-only
  mode.
- FR8: Rejection reasons are non-sensitive, human-readable, and name the
  offending construct (statement type / function / GUC) without echoing secrets.
- FR9: Applies uniformly regardless of connection backend (RDS Data API and
  psycopg / pgwire both route through the same guard in `run_query`).

### Non-functional
- NFR1: Pure-Python dependency (no native build) to keep `uvx`/`pip`
  distribution simple across platforms. `sqlglot` satisfies this.
- NFR2: Dependency pinned to a validated range and aligned with
  `redshift-mcp-server` (`sqlglot>=29.0.1,<30`) to share a vetted line; a major
  bump requires re-verifying the node-type mapping and the guard test suite.
- NFR3: Per-query parse overhead is negligible relative to the DB round-trip.
- NFR4: Deterministic decisions; extensive unit tests including evasion corpora.
- NFR5: No behavioral regression for currently-allowed read queries (validated
  against a corpus, see §7).

## 4. Library evaluation

| | sqlglot (recommended) | pglast / libpg_query |
|---|---|---|
| Parser fidelity | Own Postgres dialect; very good, not identical to PG grammar | Exact — wraps the real PostgreSQL parser |
| Dependency | Pure Python, no native build | Native C extension; wheels must exist per platform/arch |
| Distribution (`uvx`) | Simple | Heavier; build/compat risk |
| In-repo precedent | Yes — `redshift-mcp-server` uses it | None |
| Exotic PG syntax | May fail to parse some constructs → fail-closed rejection | Parses anything PG parses |

**Recommendation: prefer `pglast` (libpg_query) as the single parser for the
security-critical checks.** pglast embeds PostgreSQL's own `raw_parser` C source
(via libpg_query), so it lexes and parses byte-for-byte as the server does.
That eliminates the entire parser-differential class *by construction*: any
input we misjudge, PostgreSQL parses identically — there is no
"benign-to-the-checker, dangerous-to-the-engine" gap at the syntax layer,
including `U&`/`UESCAPE` identifier and string decoding, dollar-quoting,
comments, and statement splitting. This is the decisive advantage over sqlglot,
which was empirically shown to *not* decode `U&` and to silently misparse it
(§5.5) — a gap fail-closed does not catch. Using pglast also removes the need to
hand-maintain a PostgreSQL escape/quote decoder for FR6a.

Tradeoffs to accept and manage:
- **Native dependency.** pglast is a C extension. Prebuilt wheels exist for
  Linux (manylinux/musllinux, x86_64/aarch64) and macOS (x86_64/arm64), so
  `uvx`/`pip` needs no compiler there. **Windows wheel availability must be
  verified** before committing — MCP servers run on user laptops, and a missing
  Windows wheel would force a build toolchain or break install. If Windows
  support is inadequate, fall back to sqlglot-plus-decoder on that platform, or
  gate accordingly.
- **PG version pinning.** pglast's grammar matches one PG major (v6→PG16,
  v7→PG17, v8→PG18). Pick the major closest to the deployment targets
  (Aurora/RDS track PG majors). A construct a *newer* server accepts that an
  older pglast rejects fails **closed** (safe rejection), not open — so version
  skew degrades toward over-rejection, not bypass.
- **Semantic gaps remain regardless of parser** (see §5.6): exact-PG parsing
  does not give catalog knowledge, so function-mediated side effects and
  name-resolution indirection are still out of reach. "Matches PG's parser" is
  not "matches PG's execution semantics."

Keep `sqlglot` as the documented alternative if the native dependency proves
unacceptable for distribution; in that case FR6a's explicit decoder becomes
mandatory, not optional.

## 5. Design

### 5.1 Module and entry point
New module `sql_guard.py` (mirroring redshift), exposing a single entry point:

```python
def assert_executable(sql: str, allow_write_query: bool = False) -> None:
    """Raise if `sql` is not a single permitted statement. Fails closed."""
```

`run_query` calls this **once**, before executing, replacing the current
`detect_mutating_keywords` + `check_sql_injection_risk` calls. On rejection it
returns the existing error-response shape to the caller (no behavior change to
the tool contract, only to what is allowed).

### 5.2 Algorithm
1. **Length guard.** Reject if `len(sql) > MAX_SQL_LEN`.
2. **Parse** with `sqlglot.parse(sql, read='postgres')`; any exception →
   fail-closed reject (chain the cause for logs, do not surface internals).
3. **Single statement.** Drop empty fragments; require exactly one statement.
4. **Both-mode dangerous-construct pass** (runs regardless of `allow_write_query`),
   by walking the full AST:
   - reject `COPY` with `PROGRAM` or a server-side file target;
   - reject any call to a dangerous function (resolved name match, schema
     qualifier tolerated);
   - reject `SET` / `set_config()` targeting a security-sensitive GUC.
5. **Read-only pass** (only when `allow_write_query` is False):
   - the **root** statement must be an allowed read type (FR2), unwrapping
     `EXPLAIN` (reject `EXPLAIN ANALYZE`; recurse into the explained statement);
   - the **whole tree** must contain no mutating/side-effecting node (FR3) —
     `Insert`, `Update`, `Delete`, `Merge`, `Copy`, DDL (`Create`/`Drop`/`Alter`/
     `TruncateTable`), `Grant`/`Revoke`, transaction-control, `Command`-class
     nodes whose name is a denied verb (`CALL`, `DO`, `LOCK`, `SET`, `VACUUM`,
     `LISTEN`, `NOTIFY`, `LOAD`, …).

Classification is structural (node type; for statements sqlglot represents as a
generic `exp.Command`, the command name), exactly as redshift's guard does — so
a denied word used as an identifier, alias, or string literal is not flagged,
and a denied operation cannot be hidden by comments or quoting.

### 5.3 Which bypasses this closes — and which it does not

Structural checks (closed, robustly):
- **Missing verbs** (`COPY`, `CALL`, `DO`, `LOCK`, `SET`): recognized as
  statement/command nodes, not as an enumerated keyword list — the read-only
  pass rejects any non-read node type. PostgreSQL keywords cannot be
  Unicode-escaped (only identifiers can), so an attacker cannot encode a write
  into a read.
- **Quoted-identifier and comment evasion**: the parser folds `"pg_read_file"`
  to `pg_read_file` and strips comments as part of parsing (empirically
  confirmed for sqlglot).
- **Stacked queries**: rejected by the single-statement rule.
- **Data-modifying CTEs**: rejected by the whole-tree walk, not just root type
  (`WITH x AS (INSERT … RETURNING *) SELECT …` has an `Insert` node in the tree
  even though the root is `Select`).

Name/string-based checks (NOT closed by sqlglot alone — see §5.5):
- **Unicode-escaped identifiers/strings** (`U&"pg_read_fil\0065"`,
  `U&'row_securit\0079'`, `UESCAPE`): sqlglot does **not** decode these, so the
  function/GUC name it exposes is the raw escaped text, and a denylist match
  against the real name misses. This must be handled explicitly (§5.5) or the
  encoding bypass survives for the dangerous-function and security-GUC checks.
  The read-only statement-type check is unaffected (keyword-driven).

### 5.4 Constants
- `MAX_SQL_LEN` — cap input size (align with redshift's value).
- `DANGEROUS_FUNCTIONS` — reuse the existing set from `mutable_sql_detector.py`.
- `SECURITY_SENSITIVE_GUCS` — reuse existing set.
- `READ_ONLY_ALLOWED_ROOT` / `MUTATING_NODE_TYPES` — new, sqlglot node types.

### 5.5 Threat model: parser differentials and encoding evasion

An evasion exists whenever the **checker** and **PostgreSQL** interpret the same
bytes differently. sqlglot is a re-implementation of a Postgres-like dialect,
not PostgreSQL's lexer, so any decoding it does not replicate is a differential
and a potential bypass.

Empirical results (sqlglot `read='postgres'`, pinned line), confirmed on this
branch:

| Input | sqlglot sees | Robust? |
|---|---|---|
| `pg_read_file('/x')` | func `pg_read_file` | yes |
| `"pg_read_file"(1)` | func `pg_read_file` | yes (quote folded) |
| `pg_read_file /**/ (1)` | func `pg_read_file` | yes (comment stripped) |
| `U&"pg_read_fil\0065"(1)` | func `pg_read_fil\0065` | **NO — not decoded** |
| `set_config(U&'row_securit\0079',…)` | GUC arg not decoded | **NO** |
| `COPY … TO PROGRAM 'id'` | root `Copy` | yes (structural) |
| `WITH x AS (INSERT … RETURNING *) SELECT …` | `Insert` node in tree | yes (tree walk) |

Consequences:
- **Structural checks are sound.** Read-only classification, `COPY`, DML, and
  DML-in-CTE are keyword/grammar-driven; keywords cannot be Unicode-escaped, so
  encoding cannot turn a write into a read.
- **Name/string denylists are not sound under sqlglot alone.** Because sqlglot
  does not decode `U&"…"`/`U&'…'`, the dangerous-function and security-GUC checks
  retain the same encoding bypass the regex had. **Fail-closed does not help
  here** — sqlglot parses the escaped form successfully with a benign-looking
  name, so there is no parse error to reject on. This is a *silent misparse*,
  the dangerous kind of differential.

Mitigations (choose per check; not mutually exclusive):
1. **Decode to PostgreSQL semantics ourselves** before matching a name/string:
   apply `U&`/`UESCAPE` decoding, `""` unquoting, and case-folding to the
   identifier/literal node value. Scope is small (one identifier/string at a
   time) versus the old whole-query text normalization, but it re-implements a
   slice of the PG lexer and must track its rules.
2. **Use pglast / libpg_query for the name-based checks.** It *is* PostgreSQL's
   parser and decodes escapes identically, eliminating the differential. This
   is the one place pglast has a concrete advantage over sqlglot; the cost is a
   native dependency. A hybrid (sqlglot for structure/read-only, pglast for
   name resolution) is possible but adds two parsers.
3. **Rely on the database role as the authoritative control.** The
   function/GUC denylists are defense-in-depth; PostgreSQL's own permission
   check runs on the *decoded* object, so an encoding evasion of our denylist
   only has impact if the connected role can actually execute the function or
   owns the table. A least-privilege, non-superuser role without EXECUTE on the
   dangerous functions and without `pg_execute_server_program` neutralizes the
   residual regardless of parser fidelity.

Recommendation: adopt (1) or (2) for the name-based checks so the parser
migration does not silently carry the encoding bypass forward, and document (3)
as the authoritative control. Do not claim encoding closure for the name-based
checks on the strength of sqlglot alone. Choosing pglast (§4) subsumes (1)/(2)
because it decodes exactly as PostgreSQL does.

### 5.6 Semantic gaps that no parser closes

Exact-PG *parsing* (pglast) removes syntactic differentials, but a parser only
sees structure, not runtime semantics or catalog state. These gaps remain and
are **not** parser bugs — they are legitimate PostgreSQL behavior our filter
cannot see, so they must be owned by the database role, not the filter:

- **Function-mediated side effects.** `SELECT some_func()` where `some_func` is
  volatile / `SECURITY DEFINER` and internally writes, calls dblink, or reads
  files. The parse tree is a benign `SELECT` calling a function; volatility and
  the function body require the catalog. Read-only cannot be guaranteed against
  this from syntax.
- **Name resolution / overloading / `search_path`.** Our denylist matches
  function/GUC names syntactically, but which function actually executes depends
  on `search_path` and argument-type overload resolution at run time. A
  user-defined wrapper (`my_helper()` that calls `pg_read_file` inside) is not
  on any name denylist, and shadowing via `search_path` can redirect a name.
- **Dynamic SQL.** SQL assembled and executed at run time inside functions or
  procedures is opaque to a static parse. (`DO`/`CALL` are blocked in read-only
  mode, but this remains relevant in write mode and inside callable objects.)

Implication: "any bypass of a pglast-based checker is also a bypass of
PostgreSQL's parser" is true and valuable **at the syntactic layer** — it closes
the class we were actually hit by. It does **not** extend to these semantic
gaps. The authoritative control for them is a least-privilege, non-superuser
role that lacks EXECUTE on the dangerous functions, lacks
`pg_execute_server_program`/server-file roles, and does not own the RLS-protected
tables — because PostgreSQL enforces those privileges on the *resolved* object
regardless of how the SQL was written.

## 6. Backward compatibility and migration

- The guard must be **at least as strict** as today for dangerous constructs and
  **no stricter** for ordinary read queries. Two risks:
  - *False negatives removed*: previously-allowed `COPY`/`CALL`/etc. now
    correctly rejected in read-only mode — intended, but a behavior change for
    anyone who (incorrectly) relied on it. Call out in CHANGELOG.
  - *New false positives*: a valid read query sqlglot fails to parse is now
    rejected. Mitigate with the corpus test (§7) and consider a brief
    **shadow/observability mode**: run the new guard alongside the old path,
    log disagreements without enforcing, to quantify parse-failure rate before
    flipping enforcement. (Optional; decide during implementation.)
- Keep `mutable_sql_detector.py` until the parser guard is validated, then
  remove or reduce it to avoid two sources of truth.

## 7. Testing strategy

- **Port the evasion corpus** already proven this cycle: dblink family (incl.
  `U&"dblin\006b"`), `pg_read_file`/`lo_import`/`pg_sleep`, `COPY … TO PROGRAM`,
  `set_config('row_security',…)`, `SET row_security`, quoted/comment-wedged
  variants, stacked queries. All must be rejected.
- **Read-only allow-set**: representative `SELECT`, `WITH … SELECT`, `VALUES`,
  `SHOW`, `EXPLAIN <select>` — all must pass; `EXPLAIN ANALYZE <select>` and
  data-modifying CTEs must fail.
- **Write-mode set**: `INSERT`/`UPDATE`/`DELETE` pass with `allow_write_query`,
  while `COPY … PROGRAM`, dangerous functions, and security GUCs still fail.
- **Fail-closed**: malformed SQL, oversized input, multi-statement,
  deeply-nested input (recursion) → rejected.
- **Regression corpus**: collect the SQL from existing `tests/` that is expected
  to pass today and assert the new guard still allows it.
- Data-driven parametrization so the dangerous-function/GUC sets can't silently
  drift (as done for the dblink guard).

## 8. Risks and open questions

- **pglast Windows wheel availability (blocking for the pglast choice).** Verify
  current pglast/libpg_query provides Windows wheels for supported Python
  versions. If not, decide the fallback (sqlglot-plus-decoder on Windows) before
  committing — otherwise Windows installs break or require a compiler.
- **pglast PG-version selection.** Pin the pglast major to the PG grammar
  closest to deployment targets (Aurora/RDS majors). Version skew degrades to
  over-rejection (fail-closed), not bypass, but pick deliberately and document.
- **Encoding differential (resolved by pglast; a risk only if sqlglot is
  chosen).** sqlglot does not decode `U&` escapes, so under a sqlglot-based
  build the dangerous-function/GUC name checks require the explicit decoder
  (§5.5, FR6a) or they silently carry the known bypass forward. pglast removes
  this concern entirely.
- **Parse-failure false positives.** How often does sqlglot's Postgres dialect
  reject valid queries LLMs emit? Needs measurement (shadow mode). If material,
  reconsider pglast or a narrow fallback.
- **sqlglot representation drift.** Some statements parse as generic `exp.Command`;
  the exact node classes vary by version — hence the pinned range and the
  node-mapping test suite. A major bump requires re-verification.
- **Function side effects in read-only** remain undetectable from syntax
  (volatile / SECURITY DEFINER writers). Explicitly out of scope; rely on the
  role. Document in README alongside the existing best-effort note.
- **`COPY … TO STDOUT`** — allow in write mode, reject in read-only? Proposed:
  reject all `COPY` in read-only mode (simplest, safe), allow non-PROGRAM /
  non-server-file `COPY` in write mode. Confirm during implementation.
- **Dialect selection** — `read='postgres'`; verify Aurora/RDS-specific syntax
  (e.g., `aws_s3` calls) parses or is intentionally rejected.

## 9. Rollout plan

0. Decide the parser: confirm pglast wheel coverage for target platforms
   (esp. Windows) and pick the pglast major matching the deployment PG version;
   if native distribution is unacceptable, fall back to sqlglot + FR6a decoder.
1. Add the chosen parser dependency (pinned): `pglast` (preferred) or `sqlglot`
   (aligned with redshift) as the fallback.
2. Implement `sql_guard.py::assert_executable` + constants. With pglast, name
   resolution is exact; with sqlglot, also implement the PostgreSQL
   escape/quote/case decoder for name-based checks (FR6a).
3. Port and expand the test corpus; add the regression corpus from existing
   tests. The corpus MUST include the `U&`/`UESCAPE`/`E''` escape variants for
   every dangerous function and security GUC, asserting they are still rejected.
4. Wire `run_query` to the new guard; keep the tool's error-response contract.
5. (Optional) shadow mode to measure parse-failure rate on real traffic.
6. Remove/trim `mutable_sql_detector.py` once validated.
7. README: update the read-only "best-effort, defense-in-depth" note to
   describe parser-based enforcement and reiterate the least-privilege role as
   the authoritative control.
