# Implementation tasks: parser-based SQL policy

Tracks the implementation of `docs/design/parser-based-sql-policy.md` on branch
`parser_based_sql_policy`. Each task lists its scope, the design section it
implements, and how it is verified. Check off as completed.

## T1 — Add the `pglast` dependency
- [ ] Add `pglast>=8.4,<9` to `pyproject.toml` `[project].dependencies` (PG18 grammar; §NFR2).
- [ ] Regenerate `uv.lock` (`uv sync`).
- [ ] Verify import works: `python -c "import pglast; print(pglast.__version__)"`.
- Verify: lock updated, import succeeds.

## T2 — `sql_guard.py`: constants
Implements §5.4 / §3.1. New module `awslabs/postgres_mcp_server/sql_guard.py`.
- [ ] `MAX_SQL_LEN` (align with a sane cap).
- [ ] `READ_ONLY_ALLOWED_ROOT = {SelectStmt, VariableShowStmt, ExplainStmt}`.
- [ ] `READ_ONLY_ALLOWED_EMBEDDED = {SelectStmt}`.
- [ ] `READ_ONLY_PROHIBITED_FUNCTIONS = {'set_config'}`.
- [ ] `DANGEROUS_FUNCTIONS` — bare names: dblink family; `pg_read_file`,
      `pg_read_binary_file`, `pg_stat_file`, `lo_import`, `lo_export`;
      `pg_ls_dir` family (Tier 1); adminpack file fns (Tier 2); `pg_sleep*`;
      `pg_terminate_backend`/`pg_cancel_backend`; advisory-lock family;
      `pg_notify`; `pg_reload_conf`/`pg_rotate_logfile`.
- [ ] `DANGEROUS_QUALIFIED_FUNCTIONS` — `(schema, name)` tuples (Tier 3):
      `('aws_lambda','invoke')`, `('aws_s3','query_export_to_s3')`,
      `('aws_s3','table_import_from_s3')`.
- [ ] `SECURITY_SENSITIVE_GUCS = {'row_security','session_replication_role'}`.
- Verify: module imports; constants match design tables.

## T3 — `sql_guard.py`: `assert_executable`
Implements §5.1 / §5.2. Raises a dedicated exception on rejection; fails closed.
- [ ] Define `SqlPolicyError(Exception)` (non-sensitive message; §FR8).
- [ ] Length guard (`MAX_SQL_LEN`) → reject (§5.2.1).
- [ ] `parse_sql`; any `ParseError`/exception → reject, chain cause for logs (§5.2.2, FR7).
- [ ] Single-statement rule: exactly one `RawStmt`, else reject (FR1).
- [ ] Both-mode dangerous pass via `pglast.visitors.Visitor` (§5.2.4):
      `CopyStmt.is_program`/`.filename`; `FuncCall` bare + qualified match;
      `VariableSetStmt` + `set_config` security-GUC.
- [ ] Read-only pass (when not `allow_write_query`) (§5.2.5, FR2/FR3):
      root ∈ `READ_ONLY_ALLOWED_ROOT`; `ExplainStmt` recurse into `.query`;
      every statement node ∈ `READ_ONLY_ALLOWED_EMBEDDED`; reject
      `SelectStmt.intoClause is not None`; reject `set_config` (any GUC).
- Verify: covered by T4.

## T4 — Unit tests for `sql_guard`
Implements §7. New `tests/test_sql_guard.py`, data-driven/parametrized.
- [ ] Evasion corpus incl. `U&`/`UESCAPE`/quoted/comment variants for every
      dangerous function + security GUC → all rejected (§5.5.1, §7).
- [ ] Dangerous funcs Tiers 1–3 (incl. `U&` spellings) rejected in both modes;
      negative: bare `invoke()` in non-`aws_lambda` schema NOT rejected.
- [ ] Read-only allow-set: `SELECT`/`WITH … SELECT`/`VALUES`/`TABLE`/`SHOW`/
      `EXPLAIN <read>`/`EXPLAIN ANALYZE <read>` pass.
- [ ] Read-only reject: `EXPLAIN [ANALYZE] INSERT`, DML-in-CTE, `SELECT … INTO`,
      `set_config('work_mem',…)`, cursor family, latent-gap commands
      (`REASSIGN OWNED`, `CHECKPOINT`, `COMMIT PREPARED`, `UNLISTEN`,
      `DEALLOCATE`, txn control).
- [ ] Write-mode: `INSERT`/`UPDATE`/`DELETE`/`DROP` pass with
      `allow_write_query=True`; `COPY … PROGRAM`, dangerous funcs, security GUCs
      still rejected.
- [ ] Fail-closed: malformed, oversized, multi-statement, deep nesting.
- [ ] Node-mapping drift test over the allowlist/dangerous sets.
- Verify: `pytest tests/test_sql_guard.py` green.

## T5 — Wire `run_query` to the guard
Implements §5.1 / rollout step 4. Edit `server.py`.
- [ ] Replace `detect_mutating_keywords` + `check_sql_injection_risk` calls with
      a single `assert_executable(sql, allow_write_query=not readonly)` call.
- [ ] Catch `SqlPolicyError`, log (non-sensitive), return existing error-response
      shape (`ctx.error(...)` + `[{'error': ...}]`); preserve tool contract.
- [ ] Update import.
- Verify: `tests/test_server*.py` pass (adjust expectations for new messages).

## T6 — Remove `mutable_sql_detector.py`
Implements §6 / rollout step 5. No regex remains.
- [ ] Delete `awslabs/postgres_mcp_server/mutable_sql_detector.py`.
- [ ] Remove its imports from `server.py`.
- [ ] Delete/replace `tests/test_mutable_sql_detector.py`.
- [ ] Grep the tree for stray references.
- Verify: no import errors; full suite green.

## T7 — README + CHANGELOG
Implements rollout steps 6–7.
- [ ] README: describe parser-based enforcement; reiterate least-privilege role
      as the authoritative control (name `pg_read_server_files` /
      `pg_write_server_files` / `pg_execute_server_program`).
- [ ] CHANGELOG: (a) `U&`-escape bypass closed; (b) latent read-only gaps closed
      (`REASSIGN OWNED`, `CHECKPOINT`, `COMMIT PREPARED`, `UNLISTEN`,
      `DEALLOCATE`, txn control, `SELECT INTO`); (c) cursor tightening;
      (d) `EXPLAIN ANALYZE SELECT` allowed in read-only; (e) injection heuristics
      dropped — fewer false positives, `DROP`/`TRUNCATE`/`GRANT` allowed in write
      mode.

## T8 — Full verification
- [ ] `uv run pytest` (whole suite) green.
- [ ] `uv run ruff check` + `uv run ruff format --check`.
- [ ] `uv run pyright`.
- [ ] Clean up any temporary files.
