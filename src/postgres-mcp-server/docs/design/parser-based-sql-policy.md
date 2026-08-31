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

**Recommendation: `sqlglot`.** Pure-Python distribution and in-repo consistency
outweigh pglast's grammar exactness for a defense-in-depth layer. The main
tradeoff — sqlglot may fail to parse some valid-but-exotic PostgreSQL, which we
reject fail-closed — is acceptable for the LLM-generated read queries this tool
serves, and is far safer than the current text matching. Keep pglast as a
documented fallback if false-positive parse failures prove common in practice.

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

### 5.3 Why this closes the known bypasses
- **Missing verbs** (`COPY`, `CALL`, `DO`, `LOCK`, `SET`): recognized as
  statement/command nodes, not as an enumerated keyword list — the read-only
  pass rejects any non-read node type.
- **Unicode-escape / quoted-identifier / comment evasion**: the parser resolves
  identifiers and strips comments as part of parsing, so
  `U&"pg_read_fil\0065"(…)` is a `pg_read_file` function node before our check
  ever runs. No text normalization needed.
- **Stacked queries**: rejected by the single-statement rule.
- **Data-modifying CTEs**: rejected by the whole-tree walk, not just root type.

### 5.4 Constants
- `MAX_SQL_LEN` — cap input size (align with redshift's value).
- `DANGEROUS_FUNCTIONS` — reuse the existing set from `mutable_sql_detector.py`.
- `SECURITY_SENSITIVE_GUCS` — reuse existing set.
- `READ_ONLY_ALLOWED_ROOT` / `MUTATING_NODE_TYPES` — new, sqlglot node types.

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

1. Add `sqlglot` dependency (pinned, aligned with redshift).
2. Implement `sql_guard.py::assert_executable` + constants.
3. Port and expand the test corpus; add the regression corpus from existing
   tests.
4. Wire `run_query` to the new guard; keep the tool's error-response contract.
5. (Optional) shadow mode to measure parse-failure rate on real traffic.
6. Remove/trim `mutable_sql_detector.py` once validated.
7. README: update the read-only "best-effort, defense-in-depth" note to
   describe parser-based enforcement and reiterate the least-privilege role as
   the authoritative control.
