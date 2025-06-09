# AWS Labs cloudwatch-logs MCP Server

An AWS Labs Model Context Protocol (MCP) server for cloudwatch-logs

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

Contributions are welcome! Please see the [CONTRIBUTING.md](../../CONTRIBUTING.md) in the monorepo root for guidelines.
