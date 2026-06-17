# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - Unreleased

### Added

- Initial release of the Amazon RDS for Db2 MCP server.
- `connect_to_database` — open and cache an SSL connection to an RDS for Db2 instance using credentials from AWS Secrets Manager.
- `run_query` — run a parameterized SQL query (read-only by default).
- `get_table_schema` — fetch column metadata from `SYSCAT.COLUMNS`.
- `is_database_connected` / `get_database_connection_info` — inspect cached connections.

### Security

- Require an SSL server certificate bundle when `--ssl_encryption require` (the default): the server now refuses to start with `SECURITY=SSL` and no certificate, closing a man-in-the-middle gap where the connection was encrypted but the server was not authenticated.
- Harden the SQL injection detector so `.*` patterns (e.g. the `UNION ... SELECT` guard) match across newlines (`re.DOTALL`); an injected newline no longer bypasses the check.
- Make the connection-map lookup secret-aware so a cached connection built with different credentials is never returned to a caller.

### Changed

- Removed the `list_db2_instances` / `describe_db2_instance` discovery tools (account-wide enumeration with no connection precondition), aligning with the `oracle-mcp-server` template.
- Read-only enforcement now reads a single source of truth (the per-connection flag) for both the mutation and injection checks.
- Query-timeout configuration failures are logged at `warning` (previously `debug`) since the query then runs unbounded.
