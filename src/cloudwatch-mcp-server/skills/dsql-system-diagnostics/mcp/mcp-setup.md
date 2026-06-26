# MCP Server Setup Instructions

This skill uses the CloudWatch MCP Server with PromQL tools for querying Aurora DSQL OTel metrics.

## Prerequisites

```bash
uv --version
```

**If missing:** Install from [Astral](https://docs.astral.sh/uv/getting-started/installation/)

## Required Tools

| Tool | Purpose |
|------|---------|
| `execute_promql_query` | Instant point-in-time query |
| `execute_promql_range_query` | Time-series query over a window |
| `get_promql_label_values` | Discover label values (cluster IDs, wait events) |
| `get_promql_series` | Discover available metric series |
| `get_promql_labels` | List available label names |

## MCP Configuration

```json
{
  "mcpServers": {
    "cloudwatch": {
      "command": "uvx",
      "args": ["awslabs.cloudwatch-mcp-server@latest"],
      "env": {
        "FASTMCP_LOG_LEVEL": "ERROR"
      }
    }
  }
}
```

### Optional Environment Variables

| Variable | When Needed |
|----------|-------------|
| `AWS_PROFILE` | Non-default AWS profile |
| `AWS_REGION` | Override default region — MUST match the DSQL cluster's region |

## Example: Kiro CLI

Create `~/.kiro/agents/dsql-diagnostics.json`:

```json
{
  "$schema": "https://raw.githubusercontent.com/aws/amazon-q-developer-cli/refs/heads/main/schemas/agent-v1.json",
  "name": "dsql-diagnostics",
  "description": "Diagnose Aurora DSQL performance via CloudWatch PromQL metrics",
  "mcpServers": {
    "cloudwatch": {
      "command": "uvx",
      "args": ["awslabs.cloudwatch-mcp-server@latest"],
      "env": { "FASTMCP_LOG_LEVEL": "ERROR" }
    }
  },
  "resources": [
    "skill://.kiro/skills/dsql-system-diagnostics/SKILL.md"
  ],
  "tools": ["fs_read", "execute_bash", "@cloudwatch"]
}
```

### Launch

```bash
kiro-cli chat --agent dsql-diagnostics
```

### Verification

Confirm the CloudWatch MCP server is connected, then run:
```
check health of cluster <CLUSTER_ID>
```
