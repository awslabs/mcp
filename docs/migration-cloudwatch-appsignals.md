# Migration Guide: CloudWatch AppSignals to CloudWatch Application Signals

This guide helps you migrate from `awslabs.cloudwatch-appsignals-mcp-server` to the [CloudWatch Application Signals MCP Server](https://github.com/awslabs/mcp/tree/main/src/cloudwatch-applicationsignals-mcp-server).

## Why We're Deprecating

The `cloudwatch-applicationsignals-mcp-server` is the actively maintained replacement that includes all the same tools plus additional capabilities like group-level monitoring, change event tracking, and enablement guides. Customers on the old server are missing improvements and new tools added to the replacement.

## Installing the Replacement

### Configuration

```json
{
  "mcpServers": {
    "awslabs.cloudwatch-applicationsignals-mcp-server": {
      "command": "uvx",
      "args": ["awslabs.cloudwatch-applicationsignals-mcp-server@latest"],
      "env": {
        "AWS_PROFILE": "your-named-profile",
        "AWS_REGION": "us-east-1",
        "FASTMCP_LOG_LEVEL": "ERROR"
      },
      "disabled": false,
      "autoApprove": []
    }
  }
}
```

**Important:** Remove the old `awslabs.cloudwatch-appsignals-mcp-server` entry from your configuration after adding the new one.

## Tool-by-Tool Migration

All 13 tools from the old server are available in the new server with the **same names and parameters**. This is a direct drop-in replacement.

| Old Server Tool | New Server Tool | Notes |
|---|---|---|
| `audit_services` | `audit_services` | Same API, same parameters |
| `audit_slos` | `audit_slos` | Same API, same parameters |
| `audit_service_operations` | `audit_service_operations` | Same API, same parameters |
| `analyze_canary_failures` | `analyze_canary_failures` | Same API, same parameters |
| `list_monitored_services` | `list_monitored_services` | Same API |
| `get_service_detail` | `get_service_detail` | Same API |
| `query_service_metrics` | `query_service_metrics` | Same API |
| `list_service_operations` | `list_service_operations` | Same API |
| `get_slo` | `get_slo` | Same API |
| `list_slos` | `list_slos` | Same API |
| `search_transaction_spans` | `search_transaction_spans` | Same API |
| `query_sampled_traces` | `query_sampled_traces` | Same API |
| `list_slis` | `list_slis` | Same API |

### New Tools (only in the replacement)

The replacement server includes additional tools not available in the old server:

| Tool | Description |
|---|---|
| `get_enablement_guide` | Get guidance on enabling Application Signals for your services |
| `list_change_events` | Track change events affecting your services |
| `list_group_services` | List services within a service group |
| `audit_group_health` | Assess health across service groups for team-based workflows |
| `get_group_dependencies` | View dependencies between services in a group |
| `get_group_changes` | Track changes within a service group |
| `list_grouping_attribute_definitions` | List available grouping attribute definitions |

## Environment Variables

| Variable | Old Server | New Server |
|---|---|---|
| `AWS_PROFILE` | Supported | Supported |
| `AWS_REGION` | Supported | Supported |
| `FASTMCP_LOG_LEVEL` | Supported | Supported |
| `MCP_CLOUDWATCH_APPSIGNALS_LOG_LEVEL` | Server-specific log level | N/A (removed) |
| `MCP_CLOUDWATCH_APPLICATION_SIGNALS_LOG_LEVEL` | N/A | Server-specific log level |
| `AUDITOR_LOG_PATH` | N/A | Path for auditor log files (defaults to temp dir) |

## Summary

This migration is straightforward — swap the package name in your MCP configuration and you're done. All existing tools work identically, and you gain access to 7 additional tools for group-level monitoring and change tracking.
