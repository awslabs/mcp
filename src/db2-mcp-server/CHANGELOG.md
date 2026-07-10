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

- Require an SSL server certificate bundle when `--ssl_encryption require` (the default): the server now refuses to start with `SECURITY=SSL` and no certificate, closing a man-in-the-middle gap where the connection was encrypted but the server was not authenticated. The certificate path is also validated to point at a real file (fast-fail).
- Harden the SQL injection detector so `.*` patterns (e.g. the `UNION ... SELECT` guard) match across newlines (`re.DOTALL`); an injected newline no longer bypasses the check.
- Make the connection-map lookup secret-aware so a cached connection built with different credentials is never returned to a caller.

### Changed

- Removed the `list_db2_instances` / `describe_db2_instance` discovery tools (account-wide enumeration with no connection precondition), aligning with the `oracle-mcp-server` template.
- Read-only enforcement now reads a single source of truth (the per-connection flag) for both the mutation and injection checks.
- `connect_to_database` now also handles `BotoCoreError` (endpoint/credential failures, timeouts) via the `Failed` contract instead of crashing the tool.
- Query execution now **refuses to run** if the configured per-query timeout cannot be applied (previously it logged a warning and ran unbounded, which could hold the connection lock indefinitely). Both exception-based and falsy-return failure modes from `ibm_db.set_option` are now checked.
- Replaced cached connections are now closed on overwrite (fixes a connection leak when reconnecting under a different secret); the `get()` docstring was corrected to describe the actual secret/replacement semantics.
- **Credential injection protection**: UID/PWD values in the connection string are now wrapped in Db2 CLI `{}` braces so passwords containing `;` or `=` delimiters are treated literally and cannot corrupt the DSN or inject connection attributes. A credential containing a closing brace `}` (unrepresentable in Db2 CLI syntax) is rejected with a clear error.
- **Explicit hostname validation mode**: `SSLClientHostnameValidation` is now emitted explicitly (BASIC in production, OFF only for tunnel testing) rather than relying on the clidriver's implicit default, closing an injection vector from unescaped credentials.
- **Connect-time validation**: `connect_to_database` now validates connectivity (SSL handshake, auth, network) immediately and reports real failures ("unreachable endpoint", "bad secret") at connect time instead of returning "Connected" and only surfacing errors on the first query. Broken connections are evicted from the cache on validation failure.
- Startup instance-identifier derivation guards dotless/IP (tunnel) endpoints and gives an actionable error asking for `--instance_identifier` / `--secret_arn` instead of a misleading "instance not found".
- `_to_positional` handles an explicit `{'isNull': False}` marker instead of raising an "unrecognized format" error.

### Documented

- `UNION` / `UNION ALL` are intentionally rejected even in read-only mode (data-exfiltration vector); the limitation and workaround are noted in the README.
