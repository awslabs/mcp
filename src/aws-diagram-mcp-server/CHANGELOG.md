# Changelog

All notable changes to the AWS Diagram MCP Server will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.9.4] - 2025-05-14

### Added
- Windows compatibility for diagram generation
- Cross-platform timeout mechanism that works on both Windows and Unix-like systems
- New tests to verify Windows compatibility

### Fixed
- Fixed issue with `signal.SIGALRM` not being available on Windows
- Updated GitHub workflow to test on both Windows and Ubuntu

## [0.9.1] - Previous Release

Initial release of the AWS Diagram MCP Server.
