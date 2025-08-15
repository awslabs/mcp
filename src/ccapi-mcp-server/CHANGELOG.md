# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.1.0] - 2025-07-08

### Added

- Added support for default tagging to ease resource visibility post-deployment
- Added `explain()` tool to enforce explanation of resources between CREATE/UPDATE/DELETE updates, similar to an execution plan

## [1.0.0] - 2025-07-08

### Added

- Initial release of Cloud Control API MCP Server
- Support for AWS resource CRUDL operations via Cloud Control API
- Security scanning with Checkov integration
- CloudFormation template generation via IaC Generator APIs
- Support for 1,100+ AWS resource types
- Read-only mode support
