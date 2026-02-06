# Changelog

All notable changes to the AWS Security Hub MCP Server will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.0.0] - 2026-01-06

### Added
- **New Report Generation Tools:**
  - `generate_security_report` - Comprehensive security analysis with executive summary and recommendations
  - `generate_compliance_report` - Standards-focused compliance analysis with control status
  - `generate_security_trends_report` - Historical trend analysis to identify security posture patterns
- Enhanced MCP server instructions with detailed tool selection guide
- Anti-hallucination design for trend analysis using only actual Security Hub data
- Statistical analysis and period comparisons in trend reports
- Actionable insights and recommendations based on detected patterns

### Changed
- Updated tool documentation with comprehensive examples and use cases
- Enhanced README with Kiro installation instructions
- Improved error handling and parameter validation across all tools
- Updated tool count from 7 to 10 tools total

### Fixed
- Parameter validation issues with `days_back` parameter type conversion
- Made optional parameters truly optional to prevent unwanted default filtering
- Improved pagination handling for large datasets

## [1.0.0] - 2024-12-16

### Added
- Initial release of AWS Security Hub MCP Server
- `get_security_findings` tool for retrieving and filtering security findings
- `get_finding_statistics` tool for aggregated finding statistics
- `get_security_score` tool for overall security posture assessment
- `get_enabled_standards` tool for listing enabled security standards
- `list_security_control_definitions` tool for browsing available security controls
- `get_finding_history` tool for tracking finding changes over time
- `describe_standards_controls` tool for detailed control information
- Comprehensive filtering options for findings (severity, workflow status, compliance, etc.)
- Support for AWS credentials via profiles and environment variables
- Extensive test coverage including unit and integration tests
- Complete documentation and usage examples
