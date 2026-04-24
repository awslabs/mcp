# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-03-04

### Added

- Initial release of AWS Trusted Advisor MCP Server.
- `list_trusted_advisor_checks` - List all available checks with optional filtering by pillar or service.
- `list_recommendations` - List current recommendations with optional filtering by status, pillar, or date.
- `get_recommendation` - Get detailed information about a specific recommendation including affected resources.
- `get_cost_optimization_summary` - Summarize cost optimization recommendations with estimated savings.
- `get_security_summary` - Summarize security recommendations with active issue details.
- `get_service_limits_summary` - Summarize services approaching or exceeding limits.
- `update_recommendation_lifecycle` - Update recommendation lifecycle stage (dismiss, resolve, etc.).
- `list_organization_recommendations` - List recommendations across AWS Organizations accounts.
- Automatic pagination for all list operations.
- Markdown-formatted output for all tools.
- Comprehensive test suite with mocked boto3 calls.
