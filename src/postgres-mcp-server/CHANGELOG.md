# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## Unreleased

### Breaking

Behavior changes in this release that can break an existing caller or
deployment. Each is intentional; they are collected here because the remedy is
not always obvious from the entries below.

- **Rejection error strings changed.** A blocked query previously returned one
  of two fixed strings — `Your MCP tool only allows readonly query. …` or
  `Your query contains risky injection patterns` — regardless of what was
  actually wrong. It now returns the guard's own message naming the specific
  violation (for example `Exactly one SQL statement is allowed`,
  `Statement type not allowed in read-only mode: InsertStmt`, or
  `Dangerous function call not allowed: dblink_connect`). The messages are more
  actionable but are not a stable API. Callers that branch on the previous two
  strings must update; treat any non-empty `error` as a rejection rather than
  matching text.
- **Direct (psycopg / PG Wire) connections now default to
  `sslmode=verify-full`,** which verifies the server hostname against the
  certificate. Deployments that connect to an IP address, through an SSH tunnel
  or port-forward, or via a CNAME that does not match the certificate will fail
  to connect where they previously succeeded (libpq's old default, `prefer`,
  verified nothing). Remedy: pass `--sslmode=verify-ca` to keep certificate
  verification without the hostname check, or `--ca_bundle <path>` / `--ca_bundle
  system` for a private trust store. Encryption cannot be disabled; plaintext
  modes are not offered. To make the migration self-service, a TLS verification
  failure while opening the pool now logs the specific remediation (hostname
  mismatch → `--sslmode=verify-ca`; untrusted chain or self-signed certificate →
  `--ca_bundle`; unreadable CA file → check the `--ca_bundle` path) instead of
  leaving the operator with raw OpenSSL text. Unrelated failures — unreachable
  host, bad password, pool timeout — are unaffected and produce no TLS advice.

### Fixed

- A query using both an array slice and `query_parameters` no longer fails at
  execution on the direct (psycopg / PG Wire) path. The SQL policy guard and the
  psycopg executor each carried their own rule for deciding which `:name`
  sequences are parameter placeholders, and the executor's was looser: it
  rewrote the slice in `SELECT tags[1:limit_idx] FROM items` — which the guard
  correctly leaves alone — into the unparseable
  `SELECT tags[1%(limit_idx)s] FROM items`, so a statement the guard had already
  approved failed at the database. The looser rule also rewrote `:word`
  sequences preceded by a word character inside string literals (`'a:b'`). The
  matching rule now lives once in `named_params` and both layers import it; only
  the replacement text differs (`$1` for parsing, `%(name)s` for binding).

### Added

- `create_cluster` gains an optional `enable_iam_auth` flag (default `False`)
  that enables IAM database authentication (`EnableIAMDatabaseAuthentication`)
  on serverless Aurora clusters it creates. It only permits IAM token auth in
  addition to password auth (nothing is disabled) and is a capability toggle —
  a DB role still needs `GRANT rds_iam` and an `rds-db:connect` IAM policy to
  connect via IAM. Ignored for express clusters, which enable IAM auth via
  their express configuration.
- Initial project setup

### Security

- Enforce strict TLS on direct (psycopg / PG Wire) connections: the server now
  connects with `sslmode=verify-full`, closing an opportunistic-TLS downgrade
  and missing-certificate-verification gap (libpq previously defaulted to
  `sslmode=prefer`, which allows silent plaintext fallback and does not verify
  the server certificate). Credentials — an IAM auth token or a Secrets Manager
  password — are therefore always encrypted on the wire, and both the server
  certificate chain and hostname are verified. To make this work out of the box
  across Aurora/RDS PostgreSQL, the wheel ships a combined CA bundle (assembled
  at build time) containing both certificate families these endpoints present:
  the Amazon RDS private CAs (`rds-ca-*-g1`, used by direct instance/cluster
  endpoints) and the public Amazon Trust Services roots (`Amazon Root CA 1`–`4`,
  used by ACM-issued certs on RDS Proxy / Aurora Serverless v1). A new
  `--ca_bundle <path>` flag overrides it for self-hosted PostgreSQL or a private
  trust store.
- Add a `--sslmode` option for direct (psycopg / PG Wire) connections, limited
  to encrypted modes `require` / `verify-ca` / `verify-full` (default
  `verify-full`); plaintext modes are intentionally not offered, so credentials
  are always encrypted. This lets deployments opt down to a looser posture for
  endpoints the default can't verify — `verify-ca` skips the hostname check (for
  IP/tunnel/CNAME endpoints), `require` skips certificate verification (for
  self-signed certs) — without ever disabling encryption. A reduced posture is
  logged at startup. `--ca_bundle` also accepts the sentinel `system` to select
  the OS trust store.

- Replaced the regex-based read-only / dangerous-SQL detector with a
  parser-based guard built on `pglast` (libpg_query — PostgreSQL's own parser).
  Statements are now classified from the parse tree, closing the
  Unicode-escaped-identifier bypass (e.g. `U&"pg_read_fil\0065"` resolving to
  `pg_read_file`) that let dangerous functions slip past text matching in both
  read-only and write mode. Scope: this hardening lands in **postgres-mcp-server
  only**. The `mysql`, `mssql`, `oracle`, and `aurora-dsql` MCP servers still
  ship the regex-based `mutable_sql_detector` and remain exposed to the same
  Unicode-escape class; migrating them is tracked separately and is not part of
  this change.
- Read-only mode now rejects several statements the previous keyword list missed,
  including `SELECT … INTO`, `REASSIGN OWNED`, `CHECKPOINT`, `COMMIT PREPARED`,
  `UNLISTEN`, `DEALLOCATE`, and transaction-control statements.
- Defined semantic read-only behavior for function calls and audited PostgreSQL
  core through PG18 plus selected PostgreSQL-supplied/common RDS extensions.
  Known calls that intentionally change sequence, statistics, WAL/backup,
  replication slot/origin, BRIN/GIN index, large-object, catalog, session, or
  scheduled-job state are rejected in read-only mode even when expressed as a
  `SELECT`. Ordinary reads/calculations remain allowed despite incidental engine
  statistics/cache/snapshot/lock bookkeeping. Severe recovery/server control,
  corruption helpers, buffer-cache eviction, PG18 `pg_ls_summariesdir`, and
  bulk session resets (`RESET ALL` / `DISCARD ALL`) that include
  security-sensitive GUCs are blocked in both modes.
- Extended the always-blocked dangerous-function set with the `pg_ls_dir` family,
  the `adminpack` file functions (e.g. `pg_file_write`), and the Aurora-native
  `aws_lambda.invoke` / `aws_s3.query_export_to_s3` / `aws_s3.table_import_from_s3`.

### Changed

- Read-only mode now rejects cursor statements (`DECLARE`/`FETCH`/`MOVE`/`CLOSE`);
  these are unreliable across the tool's stateless, pooled connections.
- `EXPLAIN ANALYZE SELECT …` is now allowed in read-only mode (it executes a pure
  read); `EXPLAIN [ANALYZE]` of a write is still rejected.
- Dropped the SQL-injection pattern heuristics. Valid reads containing
  `OR 1=1` / `UNION SELECT` / trailing comments are no longer false-positived,
  and `DROP`/`TRUNCATE`/`GRANT` are now permitted **in write mode**
  (`--allow_write_query`) where the old heuristic blocked them in all modes.
  Read-only behavior is unchanged for those write statements (still rejected).
