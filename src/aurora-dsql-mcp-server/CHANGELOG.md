# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2025-05-26

### Removed

- **BREAKING CHANGE:** Server Sent Events (SSE) support has been removed in accordance with the Model Context Protocol specification's [backwards compatibility guidelines](https://modelcontextprotocol.io/specification/2025-03-26/basic/transports#backwards-compatibility)
- This change prepares for future support of [Streamable HTTP](https://modelcontextprotocol.io/specification/draft/basic/transports#streamable-http) transport

## Unreleased

### Changed

- Bump `dsql-lint` dependency to `>=0.2.1,<0.3`. The 0.2.x line accepts the `JSON` and `JSONB` data types (both supported by DSQL).
- Update steering, skill, and migration guides to reflect that DSQL supports `JSON` and `JSONB` columns natively. Array column types are still unsupported; arrays must be serialized as JSONB.

### Added

- `dsql_lint` tool: validates SQL for Aurora DSQL compatibility via the `dsql-lint` binary, with optional auto-fix
- Initial project setup
