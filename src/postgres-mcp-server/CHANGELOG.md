# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## Unreleased

### Security

- Enforce strict TLS on direct (psycopg / PG Wire) connections: the server now
  connects with `sslmode=verify-full`, closing an opportunistic-TLS downgrade
  and missing-certificate-verification gap (libpq previously defaulted to
  `sslmode=prefer`, which allows silent plaintext fallback and does not verify
  the server certificate). The Amazon RDS global CA bundle is shipped in the
  wheel (fetched at build time) for out-of-the-box Aurora/RDS verification; a
  new `--ca_bundle <path>` flag overrides it for self-hosted PostgreSQL or a
  private trust store.

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
