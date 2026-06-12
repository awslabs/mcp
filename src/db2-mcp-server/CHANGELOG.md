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
- `list_db2_instances` / `describe_db2_instance` — discover RDS for Db2 instances (endpoint, port, master secret ARN) to bridge provisioning and connection.
- `is_database_connected` / `get_database_connection_info` — inspect cached connections.
