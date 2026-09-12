# Changelog

## Unreleased

### Features
- Support for Oracle Database@AWS (ODB): Autonomous Serverless (ADB-S) and Exadata Dedicated databases, with endpoint auto-resolution for Autonomous Databases via `odb:GetAutonomousDatabase`
- Support for RDS for Oracle multi-tenant (CDB) tenant databases (PDBs) via `--tenant_database_name` / the `tenant_database_name` tool argument, with the tenant's RDS-managed master secret auto-resolved from `describe_tenant_databases`
- Validation requiring `tenant_database_name` when connecting to a multi-tenant CDB instance, returning a clear error instead of failing obscurely
- Operator-only TLS mode: `--ssl_encryption` selects `require` (default), `noverify`, or `off` for the connection. TLS mode is never selectable by the model (it is not a `connect_to_database` tool parameter), preventing an adversarial model from downgrading TLS to exfiltrate credentials in cleartext

### Security
- Connection target is pinned to the operator's startup configuration: `connect_to_database` takes **no parameters** — the target (instance/endpoint, service/SID, port, tenant, region), credentials, and TLS mode are all fixed by the server's launch flags, so the model cannot choose or redirect them. If the server was started without a target, the tool refuses to connect. Combined with the operator-only secret ARN and TLS mode, the model controls only whether to connect and which query to run, never where it runs or with what credentials

### Fixes
- `get_database_connection_info` no longer returns the Secrets Manager ARN (operator-only; never surfaced to the model)
- Startup now fails with a clear message (not a traceback) on any AWS error, including `botocore` errors such as missing credentials or an unreachable endpoint
- RDS: when a secret is configured via `--secret_arn`, a `describe_db_instances` failure (e.g. no `rds:DescribeDBInstances`, or a `--db_endpoint`-only startup) is now non-fatal — the connection proceeds and the multi-tenant guard becomes best-effort — so least-privilege / secret-only operators keep working. Without a secret, `describe_db_instances` remains required. IAM requirements are documented in the README
- ODB Autonomous: pin the endpoint resolved at startup so later connects reuse the cached pool without re-calling `get_autonomous_database` on every reconnect
- `is_database_connected` accepts a `port` argument (defaulting to the configured port) so a connection on a non-default port is reported correctly
- ODB Autonomous: resolve the private endpoint before the connection-cache lookup so reconnects reuse the cached pool instead of orphaning it (previously the lookup ran with an empty endpoint and always missed, leaking a pool on every reconnect)
- Connection lookup: an endpoint-only query (no instance identifier or target name) again finds a connection stored under a service name/SID, instead of returning "No database connection available"
- Startup: a missing `--db_endpoint` for an RDS instance (or an AWS error resolving the target) now exits with a clear logged message instead of an uncaught traceback
- Raise minimum `boto3`/`botocore` to `1.43.26`, the first version that provides the `odb.GetAutonomousDatabase` operation used for ODB Autonomous endpoint resolution

## 0.1.0 (initial release)

### Features
- Initial release of the AWS Labs MCP server for Oracle Database on AWS RDS
- Support for direct Oracle connections with password authentication (Secrets Manager)
- SQL injection detection and Oracle-specific mutating keyword blocking
- Read-only transaction enforcement using Oracle's SET TRANSACTION READ ONLY
- Connection pool management using python-oracledb thin mode (no Oracle Instant Client needed)
- Support for both service_name and SID connection styles
