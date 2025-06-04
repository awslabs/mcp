# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## Unreleased

### Added

- Add environment variable `AWS_DOCUMENTATION_PARTITION` to select AWS documentation partition.
- Add `get_available_services` and `read_documentation` when `AWS_DOCUMENTATION_PARTITION` is set to `aws-cn`.

## [1.0.0] - 2025-05-26

### Removed

- **BREAKING CHANGE:** Server Sent Events (SSE) support has been removed in accordance with the Model Context Protocol specification's [backwards compatibility guidelines](https://modelcontextprotocol.io/specification/2025-03-26/basic/transports#backwards-compatibility)
- This change prepares for future support of [Streamable HTTP](https://modelcontextprotocol.io/specification/draft/basic/transports#streamable-http) transport

## [0.0.1] - 2025-04-02

First release of AWS Documentation MCP Server.

### Added

- Initial project setup
