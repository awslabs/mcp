# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## Unreleased

### Added

- Initial project setup

### Deprecated

- This server is deprecated in favor of the [AWS MCP Server](https://github.com/aws/agent-toolkit-for-aws). See the [migration guide](https://github.com/awslabs/mcp/blob/main/docs/migration-qindex.md).
- The server now prints a `FutureWarning` at startup, and its instructions and tool descriptions are marked deprecated.

### Fixed

- The server no longer imports the `mypy_boto3_qbusiness` type stubs at runtime, so it starts without `mypy-boto3-qbusiness` installed.
