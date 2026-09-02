# Design: Parser-based read-only enforcement and dangerous-SQL filtering

Status: Draft — parser decided (`pglast`)
Branch: `parser_based_sql_policy`
Component: `awslabs.postgres-mcp-server`

> **Decision summary.** The parser is **`pglast`** (libpg_query — PostgreSQL's
> own parser compiled in). It is the single parser for all checks; there is no
> sqlglot fallback. Pin `pglast>=8.4,<9` (libpg_query for **PG18**). Windows /
> macOS / Linux binary wheels are published (verified), so `uvx`/`pip` needs no
> compiler. Rationale throughout; the sqlglot analysis is retained in §5.5 only
> as the record of why it was rejected.

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
The sibling `redshift-mcp-server` already moved to an AST guard (`sql_guard.py`)
using `sqlglot`, establishing the in-repo pattern of "parse, then classify by
node type." We adopt that pattern but choose a stronger parser: **`pglast`**,
which embeds PostgreSQL's own parser (libpg_query). Because it is the same
parser the server runs, there is **no parser-differential gap with PostgreSQL**
— including the Unicode-escape decoding that a Postgres-dialect reimplementation
like sqlglot does not replicate (see §5.5).

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
  `SELECT`, `WITH … SELECT` (and other read CTEs), `VALUES`, `TABLE`, `SHOW`,
  and `EXPLAIN` **whose inner statement is itself read-only** — with or without
  `ANALYZE`. The ANALYZE flag is not inspected: `EXPLAIN ANALYZE <X>` executes
  `<X>`, so it is allowed exactly when `<X>` would be allowed on its own
  (`EXPLAIN ANALYZE SELECT …` is permitted — a pure read; `EXPLAIN ANALYZE
  INSERT …` is rejected because the inner statement is a write). Plain
  `EXPLAIN <X>` does not execute `<X>`, but the same "inner must be read-only"
  rule is applied for consistency, so `EXPLAIN INSERT …` is rejected too.
- FR3: In read-only mode, reject any statement in the **write set** (§3.1)
  appearing *anywhere* in the tree, not just at the root. Enforced fail-closed
  as an allowlist: every statement node in the tree must be a read type
  (`SelectStmt`, plus a root `VariableShowStmt` / read `ExplainStmt`), so a
  data-modifying CTE (`WITH x AS (INSERT … RETURNING *) SELECT …`) is rejected
  because it embeds an `InsertStmt`. Read-only mode additionally rejects the two
  write-set members that parse as a `SelectStmt` (§3.1) and so escape the
  node-type allowlist: a `SelectStmt` with a non-null `intoClause`
  (`SELECT … INTO`, a table-creating write) and a `set_config(<any GUC>, …)`
  call.
- FR4: `COPY` is classified per §3.1. `COPY … TO/FROM PROGRAM`
  (`CopyStmt.is_program`) and server-side-file `COPY … TO/FROM '<path>'`
  (`CopyStmt.filename`) are in the **dangerous set** — rejected in **both**
  modes (command execution / host filesystem). Client-side `COPY` (STDIN/STDOUT)
  is in the **write set** — rejected in read-only mode, allowed in write mode.
  Net effect: all `COPY` is rejected in read-only mode; only the PROGRAM/file
  forms are additionally rejected in write mode.
- FR5: In both modes, reject calls to the **dangerous-function set** (§3.1),
  matched two ways from the AST `FuncCall.funcname`:
  - **Bare names** in `DANGEROUS_FUNCTIONS`, matched against the last element
    (tolerating a `pg_catalog.` qualifier): dblink family;
    `pg_read_file`/`pg_read_binary_file`/`pg_stat_file`/`lo_import`/`lo_export`;
    the `pg_ls_dir` family (`pg_ls_dir`, `pg_ls_logdir`, `pg_ls_waldir`,
    `pg_ls_tmpdir`, `pg_ls_archive_statusdir`, `pg_ls_logicalmapdir`,
    `pg_ls_logicalsnapdir`, `pg_ls_replslotdir`); the `adminpack` file functions
    (`pg_file_write`, `pg_file_sync`, `pg_file_rename`, `pg_file_unlink`,
    `pg_logdir_ls`); `pg_sleep*`; `pg_terminate_backend`/`pg_cancel_backend`;
    advisory-lock family; `pg_notify`; `pg_reload_conf`/`pg_rotate_logfile`.
  - **Schema-qualified pairs** in `DANGEROUS_QUALIFIED_FUNCTIONS`, matched
    against the full `funcname` (needed for generic last names):
    `aws_lambda.invoke`, `aws_s3.query_export_to_s3`,
    `aws_s3.table_import_from_s3`.

  Function-name comparison is case-insensitive and uses the decoded name pglast
  exposes (so `U&`/quoted spellings match — §5.5.1).
- FR6: In both modes, reject changes to security-sensitive GUCs
  (`row_security`, `session_replication_role`) via `SET` or `set_config()`
  (dangerous set, §3.1).
- FR6a: Name- and string-literal-based checks (FR5 dangerous functions, FR6 GUC
  names) MUST match against a value decoded to PostgreSQL's own
  identifier/string semantics — Unicode escapes (`U&"…"`/`U&'…'`, `UESCAPE`),
  double-quote unwrapping, and case-folding. **`pglast` satisfies this by
  construction**: it is PostgreSQL's parser, so the identifier/string values it
  exposes are already decoded exactly as the engine decodes them (verified —
  §5.5.1). No hand-written decoder is needed. (Under the rejected sqlglot option
  this would have required an explicit PG escape/quote decoder, because sqlglot
  does not decode `U&` — see §5.5.)
- FR7: Fail closed — reject on parse/tokenize error, recursion limit, oversized
  input (`MAX_SQL_LEN`), or an unrecognized root statement type in read-only
  mode.
- FR8: Rejection reasons are non-sensitive, human-readable, and name the
  offending construct (statement type / function / GUC) without echoing secrets.
- FR9: Applies uniformly regardless of connection backend (RDS Data API and
  psycopg / pgwire both route through the same guard in `run_query`).

### Non-functional
- NFR1: Installable via `uvx`/`pip` on the supported platforms without a build
  toolchain. `pglast` is a C extension but publishes prebuilt binary wheels for
  Windows (`win32`, `win_amd64`), macOS (x86_64 + arm64), and Linux (x86_64 +
  aarch64, glibc + musl), so no compiler is required on any supported target
  (verified against pglast 8.4 on PyPI). An unsupported platform with no wheel
  falls back to the sdist, which needs a compiler — documented, not handled.
- NFR2: Dependency pinned to `pglast>=8.4,<9` (libpg_query for PG18). The pin
  ties the grammar to one PG major; a major bump requires re-verifying the
  node-type mapping and the guard test suite. See §8 for version-skew behavior.
- NFR3: Per-query parse overhead is negligible relative to the DB round-trip
  (libpg_query is compiled C).
- NFR4: Deterministic decisions; extensive unit tests including evasion corpora.
- NFR5: No behavioral regression for currently-allowed read queries (validated
  against a corpus, see §7).

### 3.1 Operation classification: the write set and the dangerous set

Every rejection is explained by membership in one of two named sets. This is the
authoritative enumeration for functional review; FR2–FR6 above are the
behavioral rules that follow from it.

**Enforcement model (how the two sets differ):**

- The **write set (W)** is enforced *fail-closed as an allowlist*: read-only mode
  permits only the read node types (below); anything else in the statement tree
  is, by definition, in W and is rejected. A new PostgreSQL statement type we
  have never seen is therefore rejected in read-only mode automatically.
- The **dangerous set (D)** is enforced as an *explicit denylist* of constructs.
  It is defense-in-depth (the authoritative control is the DB role — §5.6), so a
  denylist is acceptable here; a construct we failed to enumerate is not blocked
  by the tool but is still gated by role privileges.

**Precedence:** D is checked first and applies in **both** modes. An operation
may belong to **both** sets; when it does, D dominates (blocked in all modes).

---

**Read node types (the read-only allowlist — everything else is in W):**
- `SelectStmt` — covers `SELECT`, `WITH … SELECT`, `VALUES`, `TABLE`.
- `VariableShowStmt` — `SHOW`.
- `ExplainStmt` whose inner `.query` is itself a read (FR2).
- Embedded statement nodes anywhere in the tree must also be `SelectStmt`
  (so a data-modifying CTE, which embeds an `InsertStmt`/`UpdateStmt`/etc., is
  rejected — FR3).

---

**Write set (W) — mutating / state-changing. Rejected in read-only mode; allowed
in write mode (`allow_write_query=True`).** Not inherently dangerous; a
write-enabled operator legitimately uses these.

| Category | SQL | pglast node type(s) |
|---|---|---|
| DML | INSERT / UPDATE / DELETE / MERGE / TRUNCATE | `InsertStmt`, `UpdateStmt`, `DeleteStmt`, `MergeStmt`, `TruncateStmt` |
| DDL | CREATE / ALTER / DROP / RENAME, CREATE FUNCTION/EXTENSION/SCHEMA/VIEW/INDEX/SEQUENCE | `CreateStmt`, `AlterTableStmt`, `DropStmt`, `RenameStmt`, `CreateFunctionStmt`, `CreateExtensionStmt`, `CreateSchemaStmt`, `ViewStmt`, `IndexStmt`, `CreateSeqStmt`, `DefineStmt`, … |
| Metadata | COMMENT ON / SECURITY LABEL / IMPORT FOREIGN SCHEMA | `CommentStmt`, `SecLabelStmt`, `ImportForeignSchemaStmt` |
| Permissions | GRANT / REVOKE | `GrantStmt`, `GrantRoleStmt` |
| Maintenance | VACUUM / ANALYZE / CLUSTER / REINDEX / REFRESH MATERIALIZED VIEW | `VacuumStmt`, `ClusterStmt`, `ReindexStmt`, `RefreshMatViewStmt` |
| Procedural / dynamic | DO / CALL | `DoStmt`, `CallStmt` |
| Prepared statements | PREPARE / EXECUTE / DEALLOCATE | `PrepareStmt`, `ExecuteStmt`, `DeallocateStmt` |
| Async / locking | LISTEN / NOTIFY / UNLISTEN / LOCK | `ListenStmt`, `NotifyStmt`, `UnlistenStmt`, `LockStmt` |
| Session / backend state | SET / RESET / DISCARD / LOAD / transaction control | `VariableSetStmt`, `DiscardStmt`, `LoadStmt`, `TransactionStmt` |
| Client-side COPY | COPY … FROM STDIN / TO STDOUT (no PROGRAM, no file) | `CopyStmt` (not a read root type — see COPY note) |
| `SELECT … INTO` (creates a table) | `SELECT * INTO t2 …` | `SelectStmt` with `intoClause is not None` |
| Function-form session write | `set_config(<any GUC>, …)` | `FuncCall` name `set_config` |

In read-only mode W is enforced structurally (allowlist), so the statement-node
rows above are illustrative, not the matcher. **Two write-set members are *not*
distinguishable by node type** and need an explicit field check, because they
parse as an allowed `SelectStmt`:

1. `set_config(<any GUC>, …)` — a `FuncCall` inside an otherwise-read `SELECT`;
   read-only mode rejects a call to `set_config` for **any** GUC (matches
   today's behavior).
2. `SELECT … INTO` — a `SelectStmt` with a non-null `intoClause`; it creates a
   table (equivalent to `CREATE TABLE AS`) and so is a write. Read-only mode
   rejects any `SelectStmt` in the tree whose `intoClause is not None`. (Note:
   the current regex guard misses this entirely — `INTO` is not in
   `MUTATING_KEYWORDS` — so closing it is a strict improvement.)

`INSTALL` deserves a note: it appears in today's `MUTATING_KEYWORDS` but is not
valid PostgreSQL (it is MySQL syntax), so pglast raises `ParseError` on it and
it is rejected fail-closed (FR7) rather than by an enumerated node type.

**Dangerous set (D) — command execution / SSRF / host filesystem / DoS /
security-control disabling. Rejected in BOTH modes.** Defense-in-depth; the DB
role is the authoritative control (§5.6).

| Threat | Construct | pglast detection |
|---|---|---|
| RCE | `COPY … TO/FROM PROGRAM 'cmd'` | `CopyStmt.is_program is True` |
| Host filesystem (read/write) | `COPY … TO/FROM '<path>'` (server-side file) | `CopyStmt.filename is not None` |
| SSRF | dblink family (`dblink`, `dblink_connect`, `dblink_connect_u`, `dblink_exec`, `dblink_send_query`, `dblink_open`, `dblink_fetch`, `dblink_close`, `dblink_get_connections`) | bare name ∈ `DANGEROUS_FUNCTIONS` |
| Filesystem read | `pg_read_file`, `pg_read_binary_file`, `pg_stat_file`, `lo_import`, `lo_export` | bare name ∈ `DANGEROUS_FUNCTIONS` |
| Filesystem enumeration | `pg_ls_dir`, `pg_ls_logdir`, `pg_ls_waldir`, `pg_ls_tmpdir`, `pg_ls_archive_statusdir`, `pg_ls_logicalmapdir`, `pg_ls_logicalsnapdir`, `pg_ls_replslotdir` *(Tier 1 — `pg_ls_dir` siblings)* | bare name ∈ `DANGEROUS_FUNCTIONS` |
| Host file write / RCE | `pg_file_write`, `pg_file_sync`, `pg_file_rename`, `pg_file_unlink`, `pg_logdir_ls` *(Tier 2 — `adminpack`; arbitrary host-file write)* | bare name ∈ `DANGEROUS_FUNCTIONS` |
| DoS | `pg_sleep`, `pg_sleep_for`, `pg_sleep_until`, `pg_terminate_backend`, `pg_cancel_backend`, advisory-lock family | bare name ∈ `DANGEROUS_FUNCTIONS` |
| Side channel / server control | `pg_notify`, `pg_reload_conf`, `pg_rotate_logfile` | bare name ∈ `DANGEROUS_FUNCTIONS` |
| SSRF / exfil / invoke (Aurora) | `aws_lambda.invoke`, `aws_s3.query_export_to_s3`, `aws_s3.table_import_from_s3` *(Tier 3 — Aurora-native equivalents of the reported dblink→exfil/SSRF class)* | schema-qualified pair ∈ `DANGEROUS_QUALIFIED_FUNCTIONS` |
| Disable RLS / triggers | `SET row_security`/`session_replication_role`; `set_config('row_security'/'session_replication_role', …)` | `VariableSetStmt.name` or `set_config` 1st arg ∈ `SECURITY_SENSITIVE_GUCS` |

**Matching model (two forms).** `pg_*` built-ins live in `pg_catalog` and have
distinctive names, so they are matched by **bare last element**
(`funcname[-1]`), which also catches an explicit `pg_catalog.` qualifier. But
some extension functions have **generic last names** (`aws_lambda.invoke` →
`invoke`), where a bare-name match would either miss the function or over-block
an innocent user function of the same name. Those are matched as a
**schema-qualified pair** via a separate `DANGEROUS_QUALIFIED_FUNCTIONS` set of
`(schema, name)` tuples compared against the full `funcname`. FR5 covers both
forms.

**Deliberately NOT in the dangerous set (reviewed, kept out — see §5.4.2).** A
comprehensive sweep (§5.4.2) surfaced further candidates that we consciously do
**not** add, to keep the denylist focused rather than chasing completeness on a
control the DB role is meant to own:

- *Replication / server-state control* (`pg_promote`,
  `pg_create_physical_replication_slot`, `pg_create_logical_replication_slot`,
  `pg_drop_replication_slot`, `pg_replication_slot_advance`,
  `pg_wal_replay_pause`/`resume`, `pg_switch_wal`, `pg_backup_start`/`stop`,
  `pg_create_restore_point`, `pg_stat_reset*`) — DoS/operational impact, but all
  are superuser / `rds_superuser`-gated and have zero use in LLM read queries;
  the role is the right control (Tier 4).
- *Optional SSRF extension* pgsql-http (`http`, `http_get`, `http_post`, …) —
  same SSRF class as dblink, but not present on RDS/Aurora by default and not a
  managed extension; if a deployment installs it, the role must not grant it
  (Tier 5).
- *Data-level large-object writes* (`lowrite`, `lo_put`, `lo_creat`) — a data
  write via function (the §5.6 semantic gap), not a host-level primitive.
- *Untrusted PL languages* (`plpythonu`, `plperlu`) — reached via
  `CREATE FUNCTION` (write-set) then an opaque call (§5.6).
- *Password-hash access* (`pg_authid`) — table access governed by role grants.

The authoritative control for all of these is a least-privilege role: not
`rds_superuser`, and specifically without the predefined roles
`pg_read_server_files` / `pg_write_server_files` / `pg_execute_server_program`
(README to state this).

**Operations that belong to both sets (D dominates → blocked in all modes):**
- `COPY … FROM PROGRAM` / `COPY … FROM '<file>'` — a table write (W) *and* RCE /
  filesystem access (D).
- `SET row_security = off` / `set_config('row_security', …)` — a session-state
  mutation (W) *and* a security-control disable (D). Generic `SET`/`set_config`
  (e.g. `work_mem`) is **W only**: rejected in read-only, allowed in write mode.

**COPY — full breakdown** (COPY is never a read root type, so *all* COPY is
rejected in read-only mode; only the PROGRAM/file forms are additionally
rejected in write mode):

| COPY form | pglast fields | Set(s) | read-only | write mode |
|---|---|---|---|---|
| `… TO/FROM PROGRAM 'cmd'` | `is_program=True` | D (and W) | reject | **reject** |
| `… TO/FROM '/path'` | `filename` set | D (and W) | reject | **reject** |
| `tbl FROM STDIN` | client, `is_from=True` | W | reject | allow |
| `tbl` / `(query) TO STDOUT` | client, `is_from=False` | W | reject | allow |

## 4. Parser choice: pglast (decided)

Two candidates were evaluated. The decision is **`pglast`**.

| | **pglast / libpg_query (chosen)** | sqlglot (rejected) |
|---|---|---|
| Parser fidelity | **Exact** — embeds PostgreSQL's own `raw_parser` C source | Own Postgres dialect; close, but not PostgreSQL's lexer |
| PG-differential gap | **None by construction** — same parser as the engine | Real: does not decode `U&`/`UESCAPE` (§5.5) → silent bypass |
| FR6a (decoded names) | **Automatic** — values already decoded as PG decodes them | Needs a hand-written PG escape/quote/case decoder |
| Dependency | C extension, but prebuilt wheels for Win/macOS/Linux (verified) | Pure Python |
| Distribution (`uvx`/`pip`) | No compiler needed on supported platforms | Simple |
| In-repo precedent | AST-guard pattern shared with redshift; parser differs | `redshift-mcp-server` uses it |
| Exotic PG syntax | Parses anything PG parses | May fail to parse → fail-closed rejection |

**Why pglast.** It embeds PostgreSQL's own parser (via libpg_query), so it lexes
and parses byte-for-byte as the server does. That eliminates the entire
parser-differential class *by construction*: any bytes we misjudge, PostgreSQL
parses identically — there is no "benign-to-the-checker, dangerous-to-the-engine"
gap at the syntax layer. This directly covers `U&`/`UESCAPE` identifier and
string decoding, dollar-quoting, comments, and statement splitting. It is the
decisive advantage over sqlglot, which was empirically shown to *not* decode
`U&` and to silently misparse it (§5.5, §5.5.1) — a gap that fail-closed does
not catch because the escaped form parses cleanly with a benign-looking name.
pglast also makes FR6a automatic: no PostgreSQL escape/quote decoder to
hand-maintain.

Tradeoffs accepted:
- **Native dependency — resolved.** pglast is a C extension, but prebuilt wheels
  are published for Windows (`win32`, `win_amd64`), macOS (x86_64 + arm64), and
  Linux (x86_64 + aarch64, glibc + musl), verified against pglast 8.4 on PyPI.
  `uvx`/`pip` therefore needs no compiler on the platforms MCP servers run on.
  Only an exotic platform with no matching wheel would hit the sdist (compiler
  required) — documented as a known limitation, no code fallback.
- **PG version pinning.** pglast's grammar matches one PG major (v6→PG16,
  v7→PG17, **v8→PG18**). We pin `pglast>=8.4,<9` (PG18), a superset that parses
  the SQL older Aurora/RDS majors accept. Version skew degrades toward
  **over-rejection (fail-closed)**, never bypass — a construct a newer server
  accepts that this pglast rejects is safely refused. Bump deliberately as new
  PG majors land.
- **Semantic gaps remain regardless of parser** (see §5.6): exact-PG parsing
  does not give catalog knowledge, so function-mediated side effects and
  name-resolution indirection are still out of reach. "Matches PG's parser" is
  not "matches PG's execution semantics." These are owned by the DB role.

sqlglot is **not** kept as a fallback. Maintaining two parsers (two node
mappings, two evasion-test matrices) for a security control is a liability, and
the pure-Python benefit is moot now that pglast wheels cover every supported
platform.

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
2. **Parse** with `pglast.parse_sql(sql)`, which returns a list of `RawStmt`
   nodes. Any `pglast.parser.ParseError` (or other exception) → fail-closed
   reject (chain the cause for logs; do not surface parser internals to the
   caller).
3. **Single statement.** `parse_sql` splits on `;` the way the server does;
   require exactly one statement. Zero statements (empty/whitespace/comment-only
   input) and two-or-more statements are both rejected (FR1).
4. **Both-mode dangerous-construct pass** (runs regardless of
   `allow_write_query`), by walking the parse tree once with a
   `pglast.visitors.Visitor`:
   - **`CopyStmt`** — reject if `is_program` is true (COPY … TO/FROM PROGRAM,
     command execution) or `filename is not None` (server-side file read/write).
     `STDIN`/`STDOUT` present as `is_program=False, filename=None`.
   - **`FuncCall`** — reject if either (a) the last element
     (`funcname[-1].sval`, tolerating a `pg_catalog.` qualifier) is in
     `DANGEROUS_FUNCTIONS`, or (b) the full `funcname` matches a `(schema, name)`
     tuple in `DANGEROUS_QUALIFIED_FUNCTIONS` (for generic-named extension
     functions like `aws_lambda.invoke`). pglast has already decoded any
     `U&`/quoted spelling, so the value compared is the real name.
   - **`VariableSetStmt`** — reject if `name` is a security-sensitive GUC; and
     reject a `FuncCall` to `set_config` whose first argument (a decoded string
     `A_Const`) is a security-sensitive GUC.
   The `set_config` first argument being a security GUC is matched on the
   decoded `A_Const` string value.
5. **Read-only pass** (only when `allow_write_query` is False) — the **write
   set** (§3.1), enforced fail-closed as an allowlist rather than a denylist:
   - the **root** statement (`RawStmt.stmt`) must be an allowed read node type
     (FR2): `SelectStmt` (this single type covers `SELECT`, `VALUES`, and
     `TABLE`), `VariableShowStmt` (`SHOW`), or `ExplainStmt`. For `ExplainStmt`,
     recurse into `.query` and re-apply the read-only root-type test to the
     explained statement — the `ANALYZE` option is **not** inspected, because
     `EXPLAIN ANALYZE <X>` executes `<X>` and so is allowed exactly when `<X>`
     is (a read). This permits `EXPLAIN ANALYZE SELECT …` and rejects
     `EXPLAIN ANALYZE INSERT …` / `EXPLAIN INSERT …` (inner is `InsertStmt`).
   - **every statement node in the tree must be `SelectStmt`** (FR3). The
     visitor walks the whole tree; any statement node that is not `SelectStmt`
     (and is not the permitted root `VariableShowStmt`/`ExplainStmt`) is, by
     definition, in the write set and is rejected. This is an *allowlist*, so a
     PostgreSQL statement type we never enumerated (a future node, or one we
     forgot) is still rejected — fail-closed. A data-modifying CTE
     (`WITH x AS (INSERT … RETURNING *) SELECT …`) embeds an `InsertStmt`, which
     is not `SelectStmt`, so it is rejected even though the root is a `SelectStmt`.
   - additionally reject the two write-set members that parse as an allowed
     `SelectStmt` and so are invisible to the node-type allowlist (§3.1):
     (a) any `SelectStmt` in the tree with `intoClause is not None`
     (`SELECT … INTO`, which creates a table — a write); and
     (b) a `FuncCall` to `set_config` for **any** GUC (session-state mutation,
     matching today's behavior).

Classification is purely by **PostgreSQL parse-node type** (and, for `CopyStmt`,
a boolean/field on the node; for the two function-based checks, the decoded
name/argument). A denied word used as an identifier, alias, or string literal is
a `String`/`A_Const` node, not a statement node, so it is never mistaken for the
operation — and a denied operation cannot be hidden by comments, quoting, or
Unicode escapes, because pglast strips/decodes all of those during parsing
exactly as the engine does.

### 5.3 Which bypasses this closes

With pglast every syntactic evasion class is closed, because the checker and the
engine share one parser:

- **Missing verbs** (`COPY`, `CALL`, `DO`, `LOCK`, `SET`): recognized as their
  own parse-node types (`CopyStmt`, `CallStmt`, `DoStmt`, `LockStmt`,
  `VariableSetStmt`), not as an enumerated keyword list — the read-only pass
  rejects any non-read node type. PostgreSQL keywords cannot be Unicode-escaped
  (only identifiers can), so an attacker cannot encode a write into a read.
- **Quoted-identifier, comment, and dollar-quote evasion**: the parser folds
  `"pg_read_file"` to `pg_read_file` and strips comments/normalizes quoting as
  part of parsing — it is PostgreSQL's lexer.
- **Unicode-escaped identifiers/strings** (`U&"pg_read_fil\0065"`,
  `U&'row_securit\0079'`, `UESCAPE`): decoded to the real name/value during
  parsing, so the dangerous-function and security-GUC checks match on the
  resolved name. This is the class the reported bug exploited against the regex
  guard; pglast closes it by construction (verified — §5.5.1).
- **Stacked queries**: rejected by the single-statement rule.
- **Data-modifying CTEs**: rejected by the whole-tree walk, not just root type
  (`WITH x AS (INSERT … RETURNING *) SELECT …` has an `InsertStmt` node in the
  tree even though the root is `SelectStmt`).

What remains open is **not** syntactic and no parser can close it — see §5.6
(function-mediated side effects, name resolution/`search_path`, dynamic SQL).
Those are owned by the database role.

### 5.4 Constants
Mapping to the two sets in §3.1:
- `MAX_SQL_LEN` — cap input size (align with redshift's value).
- **Read-only allowlist (write set enforcement, FR3):**
  - `READ_ONLY_ALLOWED_ROOT` — allowed root node types: `SelectStmt`,
    `VariableShowStmt`, `ExplainStmt`.
  - `READ_ONLY_ALLOWED_EMBEDDED` — statement node types permitted anywhere in
    the tree: `{SelectStmt}`. Any other statement node ⇒ write set ⇒ rejected
    in read-only mode (fail-closed; no `MUTATING_NODE_TYPES` denylist to keep in
    sync).
  - `READ_ONLY_PROHIBITED_FUNCTIONS` — `{set_config}`, the function-form
    session-state write rejected in read-only mode for any GUC.
  - `SelectStmt.intoClause is not None` — a field check (not a constant) that
    rejects `SELECT … INTO` (a table-creating write that otherwise parses as an
    allowed `SelectStmt`). Applied to every `SelectStmt` in the tree.
- **Dangerous set (both modes, FR4–FR6):**
  - `DANGEROUS_FUNCTIONS` — bare function names matched against `funcname[-1]`.
    Seeded from the existing set in `mutable_sql_detector.py`, extended with the
    `pg_ls_dir` family (Tier 1) and the `adminpack` file functions (Tier 2) —
    see §5.4.2.
  - `DANGEROUS_QUALIFIED_FUNCTIONS` — **new**: `(schema, name)` tuples matched
    against the full `funcname`, for extension functions with generic last
    names: `('aws_lambda','invoke')`, `('aws_s3','query_export_to_s3')`,
    `('aws_s3','table_import_from_s3')` (Tier 3).
  - `SECURITY_SENSITIVE_GUCS` — reuse existing set (`row_security`,
    `session_replication_role`).
  - `CopyStmt` PROGRAM/file is a field check on the node, not a constant.

Node classes come from `pglast.ast`; the walk uses `pglast.visitors.Visitor`.
The allowlist sets (`READ_ONLY_ALLOWED_ROOT` / `READ_ONLY_ALLOWED_EMBEDDED`) and
`DANGEROUS_FUNCTIONS` are the version-sensitive surface — a `pglast` major bump
must re-verify them against the new libpg_query node schema (§8). Using an
allowlist for the write set means a bump that *adds* statement types fails
closed (new types are rejected in read-only until reviewed), not open.

### 5.4.1 Full-command cross-check (read-only allowlist coverage)

Every top-level command in the PostgreSQL SQL reference (Part VI) was run
through pglast and its node type recorded, to confirm nothing that writes maps
to an allowed read node type. Result: of ~76 commands, only these ten parse into
the allowlist node types, and all are genuine reads except the two handled by
the field/tree checks:

| Command | pglast node | Read-only verdict |
|---|---|---|
| `SELECT` / `TABLE` / `VALUES` / `WITH … SELECT` | `SelectStmt` | allow |
| `SELECT … INTO` | `SelectStmt` (`intoClause`) | **reject** (field check — a write) |
| `WITH x AS (INSERT …) SELECT …` | `SelectStmt` (embeds `InsertStmt`) | **reject** (tree walk) |
| `SHOW` / `SHOW ALL` | `VariableShowStmt` | allow |
| `EXPLAIN [ANALYZE] <X>` | `ExplainStmt` | allow iff inner `<X>` is read |

All other commands resolve to non-allowed node types and are rejected
fail-closed. No hidden-write gap exists in the allowlist.

**Latent gaps in the current regex that the allowlist closes.** The cross-check
also found commands today's `MUTATING_KEYWORDS` regex *allows* in read-only mode
but that are writes / side effects — the allowlist rejects them by construction
(call these out in the CHANGELOG):
- `REASSIGN OWNED BY …` — object-ownership change (a write); no keyword covers it today.
- `CHECKPOINT` — forces a server checkpoint (I/O side effect).
- `COMMIT PREPARED` / two-phase-commit verbs — `COMMIT` is not in the keyword list.
- `UNLISTEN`, `DEALLOCATE`, and transaction control (`BEGIN`/`COMMIT`/`ROLLBACK`/`SAVEPOINT`).

**Deliberate tightening — cursor family (Decision A).** `DECLARE … CURSOR FOR
<read>`, `FETCH`, `MOVE`, and `CLOSE` are reads that the current regex allows but
the allowlist rejects (they are not `SelectStmt`). We **accept this tightening**
rather than widen the allowlist: this tool issues stateless, single-statement
`run_query` calls over pooled connections, so a cursor declared in one call
rarely survives to the `FETCH` in the next (it needs an explicit transaction or
`WITH HOLD` on the same connection). Keeping the read-only allowlist to exactly
`{SelectStmt(read), VariableShowStmt, ExplainStmt(read)}` is simpler and safer;
the loss of server-side-cursor pagination through the tool is negligible. Noted
in the CHANGELOG as a behavior change.

Out of read-only scope but flagged by the same sweep for later consideration:
`ALTER SYSTEM` (persistent server-config write) and `LOAD` (loads a shared
library) are currently **write-set** (allowed in write mode). Whether either
should move to the **dangerous set** (rejected in both modes) is an open
question tracked in §8 — not decided here.

### 5.4.2 Dangerous-function sweep (coverage and reachability)

The dangerous-function set was reviewed comprehensively against core PostgreSQL
and the extensions reachable on RDS/Aurora, along two axes.

**Reachability — no non-`FuncCall` escape.** Every function-invocation position
was checked with the `pglast.visitors.Visitor` walk: target list, `FROM` /
`LATERAL` range functions, `WHERE`, CTE bodies, scalar subqueries, `CASE`,
`ORDER BY`, and schema-qualified calls. All surface as `FuncCall` nodes the walk
visits. Verified. The only ways a dangerous function reaches the engine unseen
are the opaque-body paths — `DO`/`CALL`/`EXECUTE` and dynamic SQL — which are
blocked in read-only mode and are the §5.6 semantic gap owned by the DB role in
write mode.

**Coverage — added (Tiers 1–3).** Beyond the functions inherited from
`mutable_sql_detector.py`:
- *Tier 1 — `pg_ls_dir` siblings* (`pg_ls_logdir`, `pg_ls_waldir`,
  `pg_ls_tmpdir`, `pg_ls_archive_statusdir`, `pg_ls_logicalmapdir`,
  `pg_ls_logicalsnapdir`, `pg_ls_replslotdir`): closes a consistency gap — we
  blocked `pg_ls_dir` but not its variants (same filesystem enumeration).
- *Tier 2 — `adminpack` file functions* (`pg_file_write`, `pg_file_sync`,
  `pg_file_rename`, `pg_file_unlink`, `pg_logdir_ls`): `pg_file_write` is an
  arbitrary host-file write — strictly higher impact than the `pg_read_file` we
  already block, and a direct RCE path. Blocking the names is free if the
  contrib module is not installed.
- *Tier 3 — Aurora-native SSRF/exfil/invoke* (`aws_lambda.invoke`,
  `aws_s3.query_export_to_s3`, `aws_s3.table_import_from_s3`): the managed
  equivalents of the reported dblink→exfil/SSRF class, matched schema-qualified.

**Coverage — deliberately excluded (Tiers 4–5).** Enumerated in §3.1 with the
rationale: replication/server-state control (Tier 4) and the optional pgsql-http
extension (Tier 5), plus data-level large-object writes, untrusted PL languages,
and `pg_authid` access. All are superuser/`rds_superuser`-gated, not present by
default, or a semantic-layer concern — kept out to keep the denylist focused,
with the least-privilege role as the authoritative control. Revisit if a
concrete need arises.

**SQL-standard vs PG-specific.** Dangerous *functions* are inherently
PG/extension-specific; the SQL-standard danger surface is at the *statement*
level (`GRANT`/`REVOKE`, `COPY`, DDL), already covered by the write/dangerous
statement classification. No separate SQL-standard function gap exists.

### 5.5 Threat model: parser differentials (and why sqlglot was rejected)

An evasion exists whenever the **checker** and **PostgreSQL** interpret the same
bytes differently. This is the core threat the parser choice must address, and
it is the reason sqlglot was rejected in favor of pglast.

pglast *is* PostgreSQL's parser (libpg_query), so this differential class is
empty by construction: there are no bytes pglast and the engine read
differently. The rest of this section is the **evidence that motivated the
decision** — the concrete sqlglot differential we measured — retained so the
choice is auditable.

sqlglot is a re-implementation of a Postgres-*like* dialect, not PostgreSQL's
lexer, so any decoding it does not replicate is a differential and a potential
bypass. Empirical results (sqlglot `read='postgres'`, pinned line), measured on
this branch:

| Input | sqlglot sees | pglast sees | Safe under sqlglot? |
|---|---|---|---|
| `pg_read_file('/x')` | func `pg_read_file` | func `pg_read_file` | yes |
| `"pg_read_file"(1)` | func `pg_read_file` | func `pg_read_file` | yes (quote folded) |
| `pg_read_file /**/ (1)` | func `pg_read_file` | func `pg_read_file` | yes (comment stripped) |
| `U&"pg_read_fil\0065"(1)` | func `pg_read_fil\0065` | func **`pg_read_file`** | **NO — not decoded** |
| `set_config(U&'row_securit\0079',…)` | GUC arg not decoded | GUC arg **`row_security`** | **NO** |
| `COPY … TO PROGRAM 'id'` | root `Copy` | `CopyStmt(is_program=True)` | yes (structural) |
| `WITH x AS (INSERT … RETURNING *) SELECT …` | `Insert` node in tree | `InsertStmt` in tree | yes (tree walk) |

The decisive rows are the two `U&` cases. sqlglot parses the escaped form
*successfully* with a benign-looking name, so **fail-closed does not help** —
there is no parse error to reject on. That is a *silent misparse*, the dangerous
kind of differential, and it would have carried the exact reported bug (§5.5.1)
forward into the "fixed" parser-based guard. Closing it under sqlglot would have
required hand-writing a PostgreSQL `U&`/`UESCAPE`/quote/case decoder and keeping
it in sync with the lexer — the whack-a-mole this migration exists to end.

pglast removes the differential entirely (the `pglast sees` column above), which
is why it is the chosen parser and why FR6a needs no explicit decoder.

Residual (true regardless of parser): the function/GUC denylists remain
defense-in-depth. PostgreSQL's own permission check runs on the *decoded*
object, so even a hypothetical denylist miss only has impact if the connected
role can actually execute the function or owns the table. A least-privilege,
non-superuser role without EXECUTE on the dangerous functions and without
`pg_execute_server_program` is the authoritative control (§5.6).

### 5.5.1 Worked example: the reported U&-escape bypass

A vulnerability report (received via aws-security@, AWS Vulnerability Reporting
Program) demonstrated a live bypass of the current regex denylist using
PostgreSQL Unicode-escaped identifiers. It is the concrete instance of the
"name/string-based checks" differential described above, and the reason it is
worth a worked example is that it is a *silent* bypass — the guard certifies the
query as safe while PostgreSQL executes a denylisted function.

**The escape syntax.** `U&"pg_read_fil\0065"` is a Unicode-escape identifier: the
`U&` prefix makes `\0065` a code point (hex for `e`) rather than four literal
characters, so PostgreSQL resolves the identifier to `pg_read_file` *at parse
time*, before function lookup. The two spellings are identical to the engine.

**Why the regex misses it.** `strip_quoted_identifiers` folds only
`_QUOTED_IDENTIFIER_PATTERN = r'"(\w+)"'` — plain double-quoted, word characters
only. The backslash in `pg_read_fil\0065` breaks `\w+`, so the fold is skipped,
the escape is never decoded, and `DANGEROUS_FUNCTION_PATTERN` scans text that
still reads `pg_read_fil\0065` — not on the denylist, so it passes. Closing this
in regex means hand-implementing the PostgreSQL lexer's `\XXXX` / `\+XXXXXX` and
`UESCAPE` custom-escape decoding — the whack-a-mole this migration exists to end.

**Reported payloads (all pass the current guard, all execute on PostgreSQL 16):**

| Payload | Resolves to | Primitive |
|---|---|---|
| `SELECT U&"pg_read_fil\0065"('/etc/passwd')` | `pg_read_file` | host file read |
| `SELECT U&"lo_impor\0074"(0,'/etc/passwd')` | `lo_import` | host file access |
| `SELECT U&"pg_sl\0065ep"(10)` | `pg_sleep` | DoS / pool exhaustion |
| `SELECT U&"dblin\006b"('host=169.254.169.254 …')` | `dblink` | SSRF → IMDS → IAM creds |

**How pglast closes it — verified.** pglast embeds PostgreSQL's own parser, so it
performs the identical Unicode decoding and exposes the *resolved* function name.
Matching the denylist against `FuncCall.funcname[-1]` (schema qualifier
tolerated) therefore sees the real name. Confirmed empirically against pglast
8.4 on the exact reported payloads:

| Payload | `funcname[-1]` from pglast AST | Verdict |
|---|---|---|
| `U&"pg_read_fil\0065"(…)` | `pg_read_file` | BLOCKED |
| `U&"lo_impor\0074"(…)` | `lo_import` | BLOCKED |
| `U&"pg_sl\0065ep"(10)` | `pg_sleep` | BLOCKED |
| `U&"dblin\006b"(…)` | `dblink` | BLOCKED |

The escape spelling gains the attacker nothing because the match happens on the
decoded name — the same name PostgreSQL will execute. No hand-written decoder is
required; this is an inherent property of reusing the engine's own parser (§5.5).

**Sibling servers.** The report notes `aurora-dsql-mcp-server` shares the
identical `r'"(\w+)"'` normalizer against Postgres-compatible SQL, so the same
bypass class applies there and the same parser-based fix pattern is the remedy
(its reachable-function set differs and must be confirmed separately).
`redshift-mcp-server` already uses an AST parser (`sqlglot`) and was reported not
affected.

**Scope boundary (do not over-claim).** This closes the *syntactic* bypass —
the U&/`UESCAPE`/quoted/comment class — completely. It does not close semantic
indirection (a user-defined wrapper `my_helper()` that calls `pg_read_file`
internally, `search_path`/overload shadowing of which `dblink` runs). Those are
invisible to any parser and remain owned by the database role, consistent with
the report's own remediation: run the MCP with a least-privilege role that
cannot execute these functions and cannot reach IMDS. See §5.6.

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
  - *Intentional loosening*: `EXPLAIN ANALYZE SELECT …` (and other EXPLAIN of a
    read) is now **allowed** in read-only mode, where the old regex guard
    rejected it. It is a pure read, so this is correct, not a regression — but
    note it in the CHANGELOG since it is a visible behavior change.
  - *New false positives*: a valid read query pglast fails to parse is now
    rejected. This risk is low — pglast is PostgreSQL's own parser, so it
    accepts what the engine accepts (modulo the PG18-vs-older-major skew in §8,
    which errs toward over-rejection). Mitigate with the regression corpus (§7).
- **Decision: no shadow mode.** A shadow/observability pass (run the new guard
  alongside the old, log disagreements without enforcing) was considered to
  measure parse-failure rate on real traffic. Rejected: pglast parse-failures on
  valid PG SQL are not expected (same parser as the engine), and this is a
  security fix we want enforced, not observed. The regression corpus (§7) covers
  the concern.
- **Decision: remove `mutable_sql_detector.py` in its entirety** — no regex-based
  matching remains anywhere. All three of its regex groups are superseded:
  1. `MUTATING_KEYWORDS` (read-only gate) → the parser write-set allowlist (§3.1).
  2. `DANGEROUS_FUNCTIONS` / security-GUC / `COPY … PROGRAM` regex → the parser
     node/field checks (§3.1 dangerous set).
  3. `SUSPICIOUS_PATTERNS` (SQL-injection heuristics: `OR 1=1`, `UNION SELECT`,
     comment-injection, `sleep(`, `into outfile`, …) → **dropped, not
     re-implemented.** Rationale: the parser subsumes every *dangerous* item the
     heuristic caught, more robustly (comments/whitespace/encoding cannot evade
     structural checks): stacked queries → single-statement rule (both modes);
     `pg_sleep` → dangerous set (both modes); `DROP`/`TRUNCATE`/`GRANT` → write
     set (read-only); `INTO OUTFILE` → invalid PG, fail-closed. What the
     heuristic *uniquely* caught is tautology/`UNION`/comment signatures that
     match **valid read SQL** — false positives with no security value here,
     since the DB role (not a text pattern) governs what data a read may touch
     (§5.6). Two behavior changes to note in the CHANGELOG:
     - *Fewer false positives:* valid single reads containing `OR 1=1`,
       `UNION SELECT`, a trailing `-- comment`, or even an innocent string
       literal like `'please drop by'` (which the `\bdrop\b` pattern matched)
       are now allowed.
     - *Write mode:* `DROP`/`TRUNCATE`/`GRANT` are now allowed **in write mode**.
       The old injection regex ran in *both* modes, so it blocked these even
       when writes were enabled — the tool effectively could not issue DDL at
       all. The parser correctly blocks them in read-only and permits them in
       write mode (its intended purpose; `allow_write_query` is best-effort, not
       a security boundary). Read-only behavior is unchanged (still blocked).
  The module is internal (imported only by `server.py` and its tests, both
  updated in the same change), so there is no external contract to preserve.

## 7. Testing strategy

- **Port the evasion corpus** already proven this cycle: dblink family (incl.
  `U&"dblin\006b"`), `pg_read_file`/`lo_import`/`pg_sleep`, `COPY … TO PROGRAM`,
  `set_config('row_security',…)`, `SET row_security`, quoted/comment-wedged
  variants, stacked queries. All must be rejected.
- **New dangerous functions (Tiers 1–3, §5.4.2)**: the `pg_ls_dir` family
  (`pg_ls_waldir`, `pg_ls_tmpdir`, …), the `adminpack` functions (esp.
  `pg_file_write`), and the schema-qualified Aurora functions
  (`aws_lambda.invoke`, `aws_s3.query_export_to_s3`,
  `aws_s3.table_import_from_s3`) must all be rejected in **both** modes,
  including their `U&`/quoted spellings. Include a negative case ensuring a
  bare `invoke(...)` user function in a non-`aws_lambda` schema is **not**
  rejected (guards the schema-qualified matching from over-blocking).
- **Read-only allow-set**: representative `SELECT`, `WITH … SELECT`, `VALUES`,
  `TABLE`, `SHOW`, `EXPLAIN <select>`, and `EXPLAIN ANALYZE <select>` — all must
  pass. `EXPLAIN INSERT …`, `EXPLAIN ANALYZE INSERT …`, and data-modifying CTEs
  must fail. (The EXPLAIN cases specifically pin the "inner must be read-only"
  rule from FR2.)
- **`SelectStmt`-that-writes**: `SELECT … INTO t2 …` and
  `set_config('work_mem', …)` must fail in read-only mode even though both parse
  as `SelectStmt` (pins the two field-level write-set members from §3.1;
  `SELECT INTO` also covers a gap the current regex guard misses).
- **Latent-gap commands (regression pins for §5.4.1)**: `REASSIGN OWNED BY …`,
  `CHECKPOINT`, `COMMIT PREPARED 'g'`, `UNLISTEN c`, `DEALLOCATE p`, and
  transaction control (`BEGIN`/`COMMIT`/`ROLLBACK`) must fail in read-only mode.
- **Cursor family (Decision A)**: `DECLARE c CURSOR FOR SELECT 1`, `FETCH 1 FROM c`,
  `MOVE 1 IN c`, `CLOSE c` must fail in read-only mode (deliberate tightening).
- **Write-mode set**: `INSERT`/`UPDATE`/`DELETE` pass with `allow_write_query`,
  while `COPY … PROGRAM`, dangerous functions, and security GUCs still fail.
- **Fail-closed**: malformed SQL, oversized input, multi-statement,
  deeply-nested input (recursion) → rejected.
- **Regression corpus**: collect the SQL from existing `tests/` that is expected
  to pass today and assert the new guard still allows it.
- Data-driven parametrization so the dangerous-function/GUC sets can't silently
  drift (as done for the dblink guard).

## 8. Risks and open questions

Resolved (recorded here so the decisions are traceable):
- **pglast wheel availability — resolved.** Windows (`win32`, `win_amd64`),
  macOS (x86_64 + arm64), and Linux (x86_64 + aarch64, glibc + musl) wheels are
  published for pglast 8.4 (verified on PyPI). No compiler needed on supported
  platforms; no sqlglot fallback.
- **Encoding differential — resolved by pglast.** pglast decodes `U&`/`UESCAPE`
  identically to the engine, so FR6a needs no hand-written decoder (§5.5.1).

Open / to manage:
- **pglast PG-version pin.** Pinned to `pglast>=8.4,<9` (PG18). Version skew vs.
  older Aurora/RDS majors degrades to **over-rejection (fail-closed)**, not
  bypass. Requires a deliberate bump as new PG majors ship; each bump re-runs
  the node-mapping verification and the guard test suite.
- **pglast node-schema drift.** The `READ_ONLY_ALLOWED_ROOT` /
  `READ_ONLY_ALLOWED_EMBEDDED` allowlists and `DANGEROUS_FUNCTIONS` are keyed to
  libpg_query's node classes; a major bump can rename/restructure nodes.
  Mitigated by the pinned range and the data-driven node-mapping tests (§7); the
  write-set allowlist additionally fails closed on newly-added statement types.
- **`COPY … TO STDOUT` — decided.** Reject **all** `COPY` in read-only mode
  (simplest, safe). In write mode, allow only `COPY` that is neither `PROGRAM`
  nor a server-side file target (i.e. `STDIN`/`STDOUT` client-side transfer);
  `is_program` or a non-null `filename` is rejected in both modes.
- **Function side effects in read-only** remain undetectable from syntax
  (volatile / SECURITY DEFINER writers). Explicitly out of scope; rely on the
  role. Document in README alongside the existing best-effort note (§5.6).
- **Aurora/RDS-specific syntax.** Verify constructs like `aws_s3.*` calls parse
  under the PG18 grammar (they are ordinary function calls, so they should) or
  are intentionally rejected. Add representative cases to the corpus.
- **`ALTER SYSTEM` / `LOAD` — dangerous set candidates (deferred).** Both are
  currently write-set (rejected in read-only, allowed in write mode). `ALTER
  SYSTEM` writes persistent server config; `LOAD` pulls a shared library into
  the backend. Each is arguably a both-modes (dangerous-set) construct. Both are
  superuser/rds_superuser-gated at the DB anyway; decision deferred — not part
  of the read-only cross-check scope. Surfaced by the §5.4.1 command sweep.

## 9. Rollout plan

1. Add the dependency to `pyproject.toml`, pinned: `pglast>=8.4,<9` (PG18).
   Regenerate `uv.lock`.
2. Implement `sql_guard.py::assert_executable` + constants (§5.1, §5.2, §5.4)
   using `pglast.parse_sql` and a `pglast.visitors.Visitor`. Name resolution is
   exact — no decoder to write (FR6a).
3. Port and expand the test corpus; add the regression corpus from existing
   tests. The corpus MUST include the `U&`/`UESCAPE`/`E''` escape variants for
   every dangerous function and security GUC, asserting they are still rejected,
   plus a data-driven node-mapping test over `READ_ONLY_ALLOWED_ROOT` /
   `READ_ONLY_ALLOWED_EMBEDDED` and `DANGEROUS_FUNCTIONS` so the sets cannot
   silently drift.
4. Wire `run_query` to the new guard, replacing the `detect_mutating_keywords` +
   `check_sql_injection_risk` calls; keep the tool's error-response contract.
5. Remove `mutable_sql_detector.py` and update its importers/tests once the new
   guard's suite passes.
6. README: update the read-only "best-effort, defense-in-depth" note to describe
   parser-based enforcement and reiterate the least-privilege role as the
   authoritative control.
7. CHANGELOG: note (a) the `U&`-escape dangerous-function bypass is closed;
   (b) the read-only gate now correctly rejects `COPY`/`CALL`/`DO`/`SELECT INTO`
   and the latent-gap commands the old regex missed (`REASSIGN OWNED`,
   `CHECKPOINT`, `COMMIT PREPARED`, `UNLISTEN`, `DEALLOCATE`, transaction
   control); (c) the deliberate cursor-family tightening (Decision A, §5.4.1) —
   `DECLARE`/`FETCH`/`MOVE`/`CLOSE` are now rejected in read-only mode;
   (d) `EXPLAIN ANALYZE SELECT` is now allowed in read-only (intentional
   loosening, §6); (e) the SQL-injection heuristics (`SUSPICIOUS_PATTERNS`) are
   dropped — valid reads with `OR 1=1`/`UNION SELECT`/trailing comments are no
   longer false-positived, and `DROP`/`TRUNCATE`/`GRANT` are now permitted in
   write mode (previously blocked in all modes), read-only unchanged (§6).
