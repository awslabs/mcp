# Changelog

All notable changes to the AWS Security Hub MCP Server will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2024-12-16

### Added
- Initial release of AWS Security Hub MCP Server
- `get_security_findings` tool for retrieving and filtering security findings
- `get_compliance_summary` tool for compliance status across security standards
- `get_insights` tool for accessing Security Hub insights
- `get_finding_statistics` tool for aggregated finding statistics
- `update_finding_workflow` tool for updating finding workflow status
- `get_security_score` tool for overall security posture assessment
- Comprehensive filtering options for findings (severity, workflow status, compliance, etc.)
- Support for AWS credentials via profiles and environment variables
- Extensive test coverage including unit and integration tests
- Complete documentation and usage examples