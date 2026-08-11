# Changelog

## 0.1.0 (initial release)

### Features
- Initial release of the AWS Labs MCP server for Oracle Database on AWS RDS
- Support for direct Oracle connections with password authentication (Secrets Manager)
- SQL injection detection and Oracle-specific mutating keyword blocking
- Read-only transaction enforcement using Oracle's SET TRANSACTION READ ONLY
- Connection pool management using python-oracledb thin mode (no Oracle Instant Client needed)
- Support for both service_name and SID connection styles
