# AWS Labs cloudwatch-logs MCP Server (DEPRECATED)

An AWS Labs Model Context Protocol (MCP) server for cloudwatch-logs. (DEPRECATED). Please use [CloudWatch MCP Server](https://github.com/awslabs/mcp/blob/main/src/cloudwatch-mcp-server/README.md) for unified CloudWatch Telemetry related tools.

## Instructions

Use this MCP server to run read-only commands and analyze CloudWatchLogs. Supports discovering logs groups as well as running CloudWatch Log Insight
Queries. With CloudWatch Logs Insights, you can interactively search and analyze your log data in Amazon CloudWatch Logs and perform queries to help
you more efficiently and effectively respond to operational issues.

## Features

- Discovering log groups and metadata about them within your AWS account or accounts connected by CloudWatch Cross Account Observability
- Converting human-readable questions and commands into CloudWatch Log Insight queries and executing them against the discovered log groups.

## Prerequisites

1. Install `uv` from [Astral](https://docs.astral.sh/uv/getting-started/installation/) or the [GitHub README](https://github.com/astral-sh/uv#installation)
2. Install Python using `uv python install 3.10`
3. An AWS account with [CloudWatch Log Groups](https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/CWL_GettingStarted.html)
4. This MCP server can only be run locally on the same host as your LLM client.
5. Set up AWS credentials with access to AWS services
   - You need an AWS account with appropriate permissions
   - Configure AWS credentials with `aws configure` or environment variables

## Available Tools
* `describe_log_groups` - Describe log groups in the account and region, including user saved queries applicable to them. Supports Cross Account Observability.
* `analyze_log_group` - Analyzes a CloudWatch log group for anomalies, top message patterns, and top error patterns within a specified time window.
Log group must have at least one [CloudWatch Log Anomaly Detector](https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/LogsAnomalyDetection.html) configured to search for anomalies.
* `execute_log_insights_query` - Execute a Log Insights query against one or more log groups. Will wait for the query to complete for a configurable timeout.
* `get_query_results` - Get the results of a query previously started by `execute_log_insights_query`.
* `cancel_query` - Cancel an ongoing query that was previously started by `execute_log_insights_query`.

### Required IAM Permissions
* `logs:Describe*`
* `logs:Get*`
* `logs:List*`
* `logs:StartQuery`
* `logs:StopQuery`

## Installation

(DEPRECATED). Please use [CloudWatch MCP Server](https://github.com/awslabs/mcp/blob/main/src/cloudwatch-mcp-server/README.md) for unified CloudWatch Telemetry related tools.

| Cursor | VS Code |
|:------:|:-------:|
| [![Install MCP Server](https://cursor.com/deeplink/mcp-install-light.svg)](https://cursor.com/en/install-mcp?name=awslabs.cloudwatch-logs-mcp-server&config=eyJhdXRvQXBwcm92ZSI6W10sImRpc2FibGVkIjpmYWxzZSwidGltZW91dCI6NjAsImNvbW1hbmQiOiJ1dnggYXdzbGFicy5jbG91ZHdhdGNoLWxvZ3MtbWNwLXNlcnZlckBsYXRlc3QiLCJlbnYiOnsiQVdTX1BST0ZJTEUiOiJbVGhlIEFXUyBQcm9maWxlIE5hbWUgdG8gdXNlIGZvciBBV1MgYWNjZXNzXSIsIkFXU19SRUdJT04iOiJbVGhlIEFXUyByZWdpb24gdG8gcnVuIGluXSIsIkZBU1RNQ1BfTE9HX0xFVkVMIjoiRVJST1IifSwidHJhbnNwb3J0VHlwZSI6InN0ZGlvIn0%3D) | [![Install on VS Code](https://img.shields.io/badge/Install_on-VS_Code-FF9900?style=flat-square&logo=visualstudiocode&logoColor=white)](https://insiders.vscode.dev/redirect/mcp/install?name=CloudWatch%20Logs%20MCP%20Server&config=%7B%22autoApprove%22%3A%5B%5D%2C%22disabled%22%3Afalse%2C%22timeout%22%3A60%2C%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.cloudwatch-logs-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22AWS_PROFILE%22%3A%22%5BThe%20AWS%20Profile%20Name%20to%20use%20for%20AWS%20access%5D%22%2C%22AWS_REGION%22%3A%22%5BThe%20AWS%20region%20to%20run%20in%5D%22%2C%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%7D%2C%22transportType%22%3A%22stdio%22%7D) |

Example for Amazon Q Developer CLI (~/.aws/amazonq/mcp.json):

```json
{
  "mcpServers": {
    "awslabs.cloudwatch-logs-mcp-server": {
      "autoApprove": [],
      "disabled": false,
      "timeout": 60,
      "command": "uvx",
      "args": [
        "awslabs.cloudwatch-logs-mcp-server@latest"
      ],
      "env": {
        "AWS_PROFILE": "[The AWS Profile Name to use for AWS access]",
        "AWS_REGION": "[The AWS region to run in]",
        "FASTMCP_LOG_LEVEL": "ERROR"
      },
      "transportType": "stdio"
    }
  }
}
```
### Windows Installation

For Windows users, the MCP server configuration format is slightly different:

```json
{
  "mcpServers": {
    "awslabs.cloudwatch-logs-mcp-server": {
      "disabled": false,
      "timeout": 60,
      "type": "stdio",
      "command": "uv",
      "args": [
        "tool",
        "run",
        "--from",
        "awslabs.cloudwatch-logs-mcp-server@latest",
        "awslabs.cloudwatch-logs-mcp-server.exe"
      ],
      "env": {
        "FASTMCP_LOG_LEVEL": "ERROR",
        "AWS_PROFILE": "your-aws-profile",
        "AWS_REGION": "us-east-1"
      }
    }
  }
}
```


### Build and install docker image locally on the same host of your LLM client

1. `git clone https://github.com/awslabs/mcp.git`
2. Go to sub-directory 'src/cloudwatch-logs-mcp-server/'
3. Run 'docker build -t awslabs/cloudwatch-logs-mcp-server:latest .'

### Add or update your LLM client's config with following:
```json
{
  "mcpServers": {
    "awslabs.cloudwatch-logs-mcp-server": {
      "command": "docker",
      "args": [
        "run",
        "-i",
        "--rm",
        "-e", "AWS_PROFILE=[your data]",
        "-e", "AWS_REGION=[your data]",
        "awslabs/cloudwatch-logs-mcp-server:latest"
      ]
    }
  }
}
```

## Contributing

Contributions are welcome! Please see the [CONTRIBUTING.md](https://github.com/awslabs/mcp/blob/main/CONTRIBUTING.md) in the monorepo root for guidelines.
