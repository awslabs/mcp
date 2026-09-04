# Changelog

## Unreleased

### Features
- Support for Oracle Database@AWS (ODB): Autonomous Serverless (ADB-S) and Exadata Dedicated databases, with endpoint auto-resolution for Autonomous Databases via `odb:GetAutonomousDatabase`
- Support for RDS for Oracle multi-tenant (CDB) tenant databases (PDBs) via `--tenant_database_name` / the `tenant_database_name` tool argument, with the tenant's RDS-managed master secret auto-resolved from `describe_tenant_databases`
- Validation requiring `tenant_database_name` when connecting to a multi-tenant CDB instance, returning a clear error instead of failing obscurely
- Per-connection TLS: `connect_to_database` accepts an optional `ssl_encryption` argument (falling back to the `--ssl_encryption` launch value) so a single server can hold both plain-TCP (e.g. RDS on 1521) and TCPS (e.g. ODB Autonomous on 1522) connections at once

### Fixes
- Raise minimum `boto3`/`botocore` to `1.43.26`, the first version that provides the `odb.GetAutonomousDatabase` operation used for ODB Autonomous endpoint resolution

## 0.1.0 (initial release)

### Features
- Initial release of the AWS Labs MCP server for Oracle Database on AWS RDS
- Support for direct Oracle connections with password authentication (Secrets Manager)
- SQL injection detection and Oracle-specific mutating keyword blocking
- Read-only transaction enforcement using Oracle's SET TRANSACTION READ ONLY
- Connection pool management using python-oracledb thin mode (no Oracle Instant Client needed)
- Support for both service_name and SID connection styles
