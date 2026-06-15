# Changelog

## [Unreleased]

### Added
- Dynamic instrumentation tools (preview) for interactively debugging live
  Application Signals services without redeploying:
  - `create_instrumentation`, `list_instrumentations`, `get_instrumentation`,
    `delete_instrumentation`, `batch_delete_instrumentations_by_scope`,
    `batch_delete_instrumentations_by_arns` for managing instrumentation
    configurations.
  - `get_instrumentation_configuration_status`, `check_instrumentation_status`
    for status inspection.
  - `search_snapshots_for_status_event`, `get_sample_snapshot_for_breakpoint`
    for analyzing captured snapshots from CloudWatch Logs.
  - Ships a trimmed preview `application-signals` service model bundled under
    `dynamic_instrumentation/aws_data/`, loaded via a session-scoped botocore
    data loader. The bundled model is removed once the operations are generally
    available in `botocore`.

## [0.1.0] - 2025-01-18

### Added
- Initial release of CloudWatch Application Signals MCP Server
- `list_monitored_services` tool for listing all monitored services
- `get_service_detail` tool for detailed service information
- Support for AWS Application Signals monitoring
- Integration with Claude Desktop and Amazon Q
