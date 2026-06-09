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

- Bump `dsql-lint` dependency to `>=0.2.1,<0.3` and lock to `0.2.6`. `0.2.6` accepts both `JSON` and `JSONB` as stored column types (earlier 0.2.x versions rewrote `JSONB` → `JSON`).
- Steering, skill, and migration guides reframe array/document storage as a `JSONB` / `JSON` / `TEXT` choice driven by access pattern (with an `ASK` claim for the user). The previous guidance ("store JSON as TEXT" / comma-separated, then "MUST serialize arrays as JSONB") prescribed a single answer in both directions.

### Added

- `dsql_lint` tool: validates SQL for Aurora DSQL compatibility via the `dsql-lint` binary, with optional auto-fix
- Initial project setup
