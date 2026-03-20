# Cross-Account CloudWatch MCP Server

An AWS Labs Model Context Protocol (MCP) server for querying CloudWatch Logs across multiple AWS accounts using STS AssumeRole.

## Features

- **Config-Backed Targets** — Load a required `cw_config.yaml` catalog of accounts, regions, roles, and significant log groups for the LLM to inspect via MCP
- **Config-Enforced Access** — Only configured account, region, role, and log group combinations can be queried
- **Cross-Account Log Queries** — Run CloudWatch Logs Insights queries in configured AWS accounts by assuming the configured IAM role
- **Parallel Query Partitioning** — Automatically split large query windows and run partitions in parallel when a query reaches the CloudWatch row limit
- **Session Caching** — Assumed-role sessions are cached and automatically refreshed before expiry
- **Configurable Role** — Each configured target specifies the IAM role to assume

## Prerequisites

1. An AWS account with STS permissions to assume roles in target accounts
2. Target accounts must have an IAM role referenced in `cw_config.yaml` that:
   - Trusts the caller's account/principal
   - Has CloudWatch Logs read permissions (`logs:StartQuery`, `logs:GetQueryResults`, `logs:DescribeLogGroups`)
3. A `cw_config.yaml` file must be present locally or referenced through `CW_CONFIG_PATH`
4. Copy `cw_config.example.yaml` to `cw_config.yaml` and replace the placeholder values with your own
5. Local AWS credentials configured via `aws configure` or environment variables

## Available Tools

### `list_cw_targets`

Return the configured CloudWatch targets from `cw_config.yaml` or from the path in `CW_CONFIG_PATH`.

The config file format is:

```yaml
accounts:
  - accountId: "123456789012"
    region: "us-west-2"
    roleName: "CloudWatchReadOnly"
    logGroups:
      - name: "/aws/lambda/payments-prod"
        description: "Primary payment handler"
      - name: "/aws/ecs/orders"
        description: "Orders service application logs"
```

By default the server looks for `cw_config.yaml` in the current working directory. The repository includes `cw_config.example.yaml` as a template; copy it to `cw_config.yaml` before running the server. You can also override the path with the `CW_CONFIG_PATH` environment variable.

### `query_logs`

Query CloudWatch Logs for a target that is already present in `cw_config.yaml`. Large result sets are automatically partitioned and queried in parallel when the CloudWatch row limit is reached.

| Parameter | Required | Description |
|---|---|---|
| `account_id` | Yes | 12-digit AWS account ID that must match a configured target |
| `log_group` | Yes | CloudWatch log group name that must be present in the configured account entry |
| `query_string` | Yes | CloudWatch Logs Insights query |
| `role_name` | No | IAM role name to assume. Must match the configured account entry |
| `start_time` | Yes | Start of the query window. Timezone-aware values are converted to UTC; naive values are treated as UTC |
| `end_time` | Yes | End of the query window. Timezone-aware values are converted to UTC; naive values are treated as UTC |
| `region` | No | AWS region. Must match the configured account entry |
| `max_timeout` | No | Max seconds to wait for results (default: 30) |

### Required IAM Permissions (on the assumed role)

- `logs:StartQuery`
- `logs:GetQueryResults`
- `logs:DescribeLogGroups`

### Required IAM Permissions (on the caller)

- `sts:AssumeRole`

## Installation

### Option 1: Python (UVX)

#### Prerequisites

1. Install `uv` from [Astral](https://docs.astral.sh/uv/getting-started/installation/)
2. Install Python using `uv python install 3.10`

#### MCP Config (Kiro, Cline)

```json
{
  "mcpServers": {
    "awslabs.cross-account-cloudwatch-mcp-server": {
      "command": "uvx",
      "args": [
        "awslabs.cross-account-cloudwatch-mcp-server@latest"
      ],
      "env": {
        "AWS_PROFILE": "<your-aws-profile>",
        "CW_CONFIG_PATH": "/absolute/path/to/cw_config.yaml",
        "FASTMCP_LOG_LEVEL": "ERROR"
      },
      "disabled": false,
      "autoApprove": []
    }
  }
}
```

If neither `cw_config.yaml` nor `CW_CONFIG_PATH` is provided, the server raises a configuration error and tells the user to create `cw_config.yaml` from `cw_config.example.yaml`.

## Contributing

Contributions are welcome! Please see the [CONTRIBUTING.md](https://github.com/awslabs/mcp/blob/main/CONTRIBUTING.md) in the monorepo root for guidelines.
