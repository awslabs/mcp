# Changelog

## [Unreleased]

### Deprecated
- This server is deprecated in favor of the [AWS MCP Server](https://github.com/aws/agent-toolkit-for-aws). See the [migration guide](https://github.com/awslabs/mcp/blob/main/docs/migration-cloudwatch-applicationsignals.md).
- The server prints a `FutureWarning` at startup, and its instructions and tool descriptions are marked deprecated.

### Added
- Dynamic instrumentation tools for interactively debugging live
  Application Signals services without redeploying:
  - `create_instrumentation`, `list_instrumentations`, `get_instrumentation`,
    `delete_instrumentation`, `batch_delete_instrumentations_by_scope`,
    `batch_delete_instrumentations_by_arns` for managing instrumentation
    configurations.
  - `get_instrumentation_configuration_status`, `check_instrumentation_status`
    for status inspection.
  - `search_snapshots_for_status_event`, `get_sample_snapshot_for_breakpoint`
    for analyzing captured snapshots from CloudWatch Logs.
  - Calls the public `application-signals` dynamic instrumentation operations
    (`boto3` >= 1.43.35).

## [0.1.0] - 2025-01-18

### Added
- Initial release of CloudWatch Application Signals MCP Server
- `list_monitored_services` tool for listing all monitored services
- `get_service_detail` tool for detailed service information
- Support for AWS Application Signals monitoring
- Integration with Claude Desktop and Amazon Q
