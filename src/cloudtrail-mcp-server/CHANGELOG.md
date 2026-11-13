# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.0.3] - 2025-09-22

### Changed

- Update the context to include event schema for better generation of SQL.

## [0.0.1] - 2025-08-25

### Added

- Tools for CloudTrail Lookup and Lake.

## Unreleased

### Deprecated

- Deprecate this server in favor of the
  [AWS MCP Server](https://github.com/aws/agent-toolkit-for-aws). See the
  [migration guide](https://github.com/awslabs/mcp/blob/main/docs/migration-cloudtrail.md).
  The server now prints a `FutureWarning` at startup, and its instructions and
  tool descriptions are marked deprecated.

### Added

- Initial project setup
