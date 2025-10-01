# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] - 2025-01-10

### Added
- Initial release of AWS Security MCP Server
- Health check tool for AWS connectivity verification
- GuardDuty integration for threat detection findings
- Security Hub integration for centralized security findings
- AWS profile support for secure credential management
- Structured JSON responses with consistent error handling
- Comprehensive logging with loguru
- Type safety with Pydantic models
- Unit tests with pytest
- Pre-commit hooks for code quality
- Documentation following awslabs standards

### Security
- Read-only IAM permissions for security best practices
- No hardcoded credentials or secrets
- Secure AWS profile-based authentication
