# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
