# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## Unreleased

### Fixed

- SNS operations with acronyms in their names (e.g. `GetSMSAttributes`) are now resolved from the
  botocore service model instead of being silently skipped. This registers the read-only tools
  `get_sms_attributes`, `get_sms_sandbox_account_status`, and `list_sms_sandbox_phone_numbers`.
  `verify_sms_sandbox_phone_number` is explicitly ignored alongside the other A2P SMS operations
  that change state.

## [2.0.0] - 2025-05-26

### Removed

- **BREAKING CHANGE:** Server Sent Events (SSE) support has been removed in accordance with the Model Context Protocol specification's [backwards compatibility guidelines](https://modelcontextprotocol.io/specification/2025-03-26/basic/transports#backwards-compatibility)
- This change prepares for future support of [Streamable HTTP](https://modelcontextprotocol.io/specification/draft/basic/transports#streamable-http) transport

## [1.0.0] - 2025-05-06

### Added

- Initial release of the Amazon SNS and SQS MCP Server
- Support for Amazon SNS topics and subscriptions
- Support for Amazon SQS queues
- Resource tagging for SNS topics and SQS queues
- Validation to prevent mutation of untagged resources
