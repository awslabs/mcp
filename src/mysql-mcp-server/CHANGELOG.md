# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## 1.0.22

### Security

- **CWE-184** — extended the read-only-mode denylist to
  close gaps reported by external security review. The previous
  `MUTATING_KEYWORDS` set omitted `SET`, `CALL`, `PREPARE`, `EXECUTE`,
  `DEALLOCATE`, `HANDLER`, `LOCK`, `LOCK TABLES`, `UNLOCK`,
  `UNLOCK TABLES`, `FLUSH`, `RESET`, `KILL`, and `UNINSTALL`, so on the
  RDS Data API path an LLM under prompt injection could fire these
  statements against the operator's database under what the server
  presented as a read-only call. All listed statements are now rejected
  at the MCP layer.
- Added an always-block list (`SECURITY_SENSITIVE_VARS`) that rejects
  `SET sql_log_bin`, `SET foreign_key_checks`, and `SET unique_checks`
  in both read-only and write modes. Flipping these variables disables
  binary logging / referential integrity / uniqueness for the rest of
  the session, and an LLM-driven flow should never be able to flip them
  even when the operator has enabled writes via `--allow_write_query`.
  Pattern handles the comma-separated multi-assignment form
  (`SET @x = 1, sql_log_bin = 0`) and every MySQL scope modifier
  permutation.
- README adds a **Security model** section: the read-only mode is a
  best-effort SQL-text safeguard, not a security boundary; operators
  should connect with a least-privilege MySQL user / IAM role with only
  `SELECT` granted at the database. Aligns the MySQL package with the
  equivalent wording in the Postgres, MSSQL, and Oracle sibling
  packages. `kiro_power/POWER.md` and the
  `kiro_power/steering/aurora-mysql-mcp.md` steering file carry the
  same caveat.
- Existing stacked-queries detection in `SUSPICIOUS_PATTERNS` is now
  pinned by `TestTransactionBypassCoverage`, which exercises the
  canonical bypass payloads (`SELECT 1; COMMIT; INSERT …` and
  variants) so a future change that relaxes the stacked-queries rule
  has to update the tests deliberately.

## Unreleased

### Added

- `database_type` parameter on `connect_to_database` accepts `aurora-mysql`,
  `mysql` (RDS MySQL), and `mariadb` (RDS MariaDB). Engine values match
  AWS RDS engine strings so they can be forwarded directly to RDS APIs.
- `mysqlwire_iam` connection method for IAM-auth connections backed by
  the Amazon RDS CA bundle. The bundle is fetched at build time by
  `hatch_build.py` and shipped inside the wheel; operators can override
  the bundled file with `--ca_bundle <path>` if they maintain their own
  trust store or need a fresher bundle than the latest release.
- `create_cluster` MCP tool for creating Aurora MySQL clusters
  (Serverless v2 by default, or provisioned via `cluster_type='provisioned'`).
  Returns a job id; poll `get_job_status` until the cluster is available.
- `is_database_connected`, `get_database_connection_info`,
  `get_table_schema`, `get_job_status` MCP tools.
- Multi-cluster connection registry (`DBConnectionMap`) replacing the
  previous single-cluster singleton. Two-phase lookup (strict 5-tuple
  match, then port-aware relaxed scan) with ambiguity guard.
- `SUPPORTED_CONNECTION_METHODS` table that gates which (engine, method)
  pairs the server accepts. `rdsapi` is Aurora-only; `mysqlwire_iam` is
  Aurora MySQL + RDS MySQL; `mysqlwire` works for every engine.
- `kiro_power/POWER.md` with workflow guidance for cluster creation,
  schema design, query optimisation, schema migrations, RDS-to-Aurora
  migration, and replication.
- `kiro_proj_steering/` for project-level steering files.

### Changed

- `create_cluster` default `database` is now `'app'` (was `'mysql'`).
  AWS rejects `'mysql'` as a reserved word for the engine, so the
  previous default broke minimal-arg invocations.
- `--allow_write_query` is now the documented CLI flag for enabling
  write queries (replaces `--readonly True/False`).
- README rewritten around the unified `database_type + connection_method`
  surface; previous "RDS Data API vs Direct MySQL" framing removed.

### Removed

- `db_connection_singleton.py` (replaced by `db_connection_map.py`).
- `constants.py` (single `USER_AGENT_*` value moved into
  `awslabs/mysql_mcp_server/__init__.py` alongside `__version__`).
- SHA-256 pinning of the RDS CA bundle in `hatch_build.py` and the
  runtime hash re-check in `asyncmy_pool_connection.py`. The build
  hook still fetches the bundle from
  `truststore.pki.rds.amazonaws.com` at build time and ships it in
  the wheel; CA bundle rotations are picked up automatically on the
  next build. Runtime TLS validation against the bundled CA is
  unchanged.
