# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2025-05-26

### Removed

- **BREAKING CHANGE:** Server Sent Events (SSE) support has been removed in accordance with the Model Context Protocol specification's [backwards compatibility guidelines](https://modelcontextprotocol.io/specification/2025-03-26/basic/transports#backwards-compatibility)
- This change prepares for future support of [Streamable HTTP](https://modelcontextprotocol.io/specification/draft/basic/transports#streamable-http) transport

## Unreleased

### Security

- Close read-only bypasses in `readonly_query` / `transact` (read-only mode), aligning the SQL classifier with the `postgres-mcp-server` sibling:
  - Detect Postgres session-state mutation that a `BEGIN TRANSACTION READ ONLY` does not block, using a broad keyword approach matched at statement start (mirroring the sibling) rather than an assignment-shape regex: assignment `SET <name> = ...` / `... TO ...`, keyword-syntax `SET ROLE` / `SET SESSION AUTHORIZATION` / `SET SCHEMA` / `SET NAMES`, the session commands `RESET` / `DISCARD` / `LISTEN` / `NOTIFY` / `UNLISTEN` / `LOCK` / `EXECUTE`, prepared-statement / cursor commands `PREPARE` / `DEALLOCATE` / `DECLARE ... CURSOR` (session-scoped, not cleared by `RESET ALL`), and the `set_config(...)` function form (including when embedded as a `SELECT` subquery). `SET TRANSACTION READ ONLY` / isolation-only remains allowed so read-only mode can be asserted, but `SET TRANSACTION ... READ WRITE` (an escalation) is blocked, including when split across a newline.
  - Normalize SQL (strip comments, unwrap double-quoted identifiers) before matching so comment-injection payloads like `SET/**/search_path = ...` can no longer slip past the classifier. This replaces the earlier `sqlparse`-based comment stripping with a self-contained, literal- and dollar-quote-aware normalizer (matching the `postgres-mcp-server` sibling), removing the `sqlparse` dependency.
  - Blank string-literal and dollar-quoted contents before the bare-keyword / bare-name scans so a keyword or function name that is merely data (`SELECT 'INSERT INTO' AS action`, `... WHERE query LIKE '%dblink(%'`, `SELECT 'set_config(' AS x`) is not falsely rejected. A shared literal-boundary scanner models `E'...'` backslash escapes, double-quoted identifiers, and dollar-quotes, closing escape bypasses where a naive scanner mis-detected the literal's end and hid a following dangerous call (`SELECT E'\'' UNION SELECT ...`, `SELECT $$q'$$, pg_terminate_backend(1)`, and an apostrophe inside a quoted identifier such as `SELECT 1 AS "o'clock", pg_terminate_backend(1)`).
  - Block statement-level mutations matched at statement start: `CALL`, `DO`, `VACUUM`, `ANALYZE`, `REINDEX`, `CLUSTER`, `REFRESH`, `COMMENT ON`, `SECURITY LABEL`, `IMPORT FOREIGN SCHEMA`, `LOAD`, `DISCARD`, plus the sequence-mutation functions `setval(...)` / `nextval(...)`. Anchoring at statement start keeps mid-query occurrences allowed — notably `EXPLAIN ANALYZE ... SELECT` (the query-plan workflow) and column/table names like `comment` or `cluster_id`. Aurora DSQL rejects these at the engine today; enforced here as forward-looking defense-in-depth.
  - Harden the classifier against CPU-exhaustion (ReDoS) on attacker-supplied SQL, replacing several catastrophic-backtracking / O(n^2) patterns with linear equivalents: the `'.*?--` comment-injection regex (now a bounded per-line scan), the `SELECT\s+.*\s+INTO OUTFILE` / `COPY\s+.*\s+FROM|TO` system-command branches (now anchored, single-line), the `union\s...\bselect` keyword check (now two linear substring presence checks), the `(begin|commit|rollback).*;\w+` and dollar-quote-tag scans, and the redundant `commit.*?;` branch in the transaction-bypass detector (removed; the linear stacked-statement scan already covers it).
  - Block high-blast-radius Postgres functions (`pg_sleep`/`pg_sleep_for`/`pg_sleep_until`, `pg_terminate_backend`, `pg_read_file`, advisory-lock family, `dblink` family, etc.), the security-sensitive GUCs `row_security` / `session_replication_role`, and `COPY ... TO/FROM PROGRAM` in both read-only and write mode. Most are already rejected by the Aurora DSQL engine today; they are enforced here as forward-looking defense-in-depth.
  - Issue `RESET ALL` and `RESET ROLE` on the pooled connection after each read-only query so no session state (including `role` / `session_authorization`, which `RESET ALL` does not clear) persists across MCP tool calls. `DISCARD ALL` would cover both but is unsupported by Aurora DSQL. If the scrub fails, the connection is discarded so the next request reconnects with clean state. Read-only `transact` also rolls back before scrubbing on a read-only violation so the reset does not run inside an aborted transaction.

### Changed

- Bump `dsql-lint` dependency to `>=0.2.1,<0.3` and lock to `0.2.6`. `0.2.6` accepts both `JSON` and `JSONB` as stored column types (earlier 0.2.x versions rewrote `JSONB` → `JSON`).
- Steering, skill, and migration guides updated:
  - For arrays: PREFER `JSONB` (operators and `jsonb_array_elements_text` work directly); MAY use `TEXT` for columns the database never inspects.
  - For document columns: `JSONB` when querying with `@>`/`?`/indexed paths; `JSON` for write-heavy or byte-exact paths.
  - When migrating an existing `JSON` column, SHOULD keep it as `JSON`; MAY upgrade to `JSONB` if the application needs JSONB-only operators or indexed paths.
  - Replaces the prior "store JSON as TEXT" / comma-separated guidance and the over-corrected "MUST serialize arrays as JSONB" framing.

### Added

- DSQL skill and Kiro Power guidance for the `Amazon.AuroraDsql.EntityFrameworkCore` (EF Core) adapter: C# / .NET connectivity section, EF Core adapter entry, and updated adapter count
- `dsql_lint` tool: validates SQL for Aurora DSQL compatibility via the `dsql-lint` binary, with optional auto-fix
- Initial project setup
