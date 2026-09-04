# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## Unreleased

### Added

- `create_cluster` gains an optional `enable_iam_auth` flag (default `False`)
  that enables IAM database authentication (`EnableIAMDatabaseAuthentication`)
  on serverless Aurora clusters it creates. It only permits IAM token auth in
  addition to password auth (nothing is disabled) and is a capability toggle —
  a DB role still needs `GRANT rds_iam` and an `rds-db:connect` IAM policy to
  connect via IAM. Ignored for express clusters, which enable IAM auth via
  their express configuration.

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
  read-only and write mode.
- Read-only mode now rejects several statements the previous keyword list missed,
  including `SELECT … INTO`, `REASSIGN OWNED`, `CHECKPOINT`, `COMMIT PREPARED`,
  `UNLISTEN`, `DEALLOCATE`, and transaction-control statements.
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

### Added

- Initial project setup
