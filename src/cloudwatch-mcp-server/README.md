# AWS Labs cloudwatch MCP Server

This AWS Labs Model Context Protocol (MCP) server for CloudWatch enables your troubleshooting agents to use CloudWatch data to do AI-powered root cause analysis and provide recommendations. It offers comprehensive observability tools that simplify monitoring, reduce context switching, and help teams quickly diagnose and resolve service issues. This server will provide AI agents with seamless access to CloudWatch telemetry data through standardized MCP interfaces, eliminating the need for custom API integrations and reducing context switching during troubleshooting workflows. By consolidating access to all CloudWatch capabilities, we enable powerful cross-service correlations and insights that accelerate incident resolution and improve operational visibility.

## Instructions

The CloudWatch MCP Server provides specialized tools to address common operational scenarios including alarm troubleshooting, understand metrics definitions, alarm recommendations and log analysis. Each tool encapsulates one or multiple CloudWatch APIs into task-oriented operations.

## Features

Alarm Based Troubleshooting - Identifies active alarms, retrieves related metrics and logs, and analyzes historical alarm patterns to determine root causes of triggered alerts. Provides context-aware recommendations for remediation.

Log Analyzer - Analyzes a CloudWatch log group for anomalies, message patterns, and error patterns within a specified time window.

Metric Definition Analyzer - Provides comprehensive descriptions of what metrics represent, how they're calculated, recommended statistics to use for metric data retrieval

Alarm Recommendations - Suggests recommended alarm configurations for CloudWatch metrics, including thresholds, evaluation periods, and other alarm settings.

## Prerequisites
1. An AWS account with [CloudWatch Telemetry](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/WhatIsCloudWatch.html)
2. This MCP server can only be run locally on the same host as your LLM client.
3. Set up AWS credentials with access to AWS services
   - You need an AWS account with appropriate permissions (See required permissions below)
   - Configure AWS credentials with `aws configure` or environment variables

## Available Tools

### Tools for CloudWatch Metrics
* `get_metric_data` - Retrieves detailed CloudWatch metric data for any CloudWatch metric. Use this for general CloudWatch metrics that aren't specific to Application Signals. Provides ability to query any metric namespace, dimension, and statistic
* `get_metric_metadata` - Retrieves comprehensive metadata about a specific CloudWatch metric
* `get_recommended_metric_alarms` - Gets recommended alarms for a CloudWatch metric

### Tools for CloudWatch Alarms
* `get_active_alarms` - Identifies currently active CloudWatch alarms across the account
* `get_alarm_history` - Retrieves historical state changes and patterns for a given CloudWatch alarm

### Tools for CloudWatch Logs
* `describe_log_groups` - Finds metadata about CloudWatch log groups
* `analyze_log_group` - Analyzes CloudWatch logs for anomalies, message patterns, and error patterns
* `execute_log_insights_query` - Executes CloudWatch Logs insights query on CloudWatch log group(s) with specified time range and query syntax, returns a unique ID used to retrieve results
* `get_logs_insight_query_results` - Retrieves the results of an executed CloudWatch insights query using the query ID. It is used after `execute_log_insights_query` has been called
* `cancel_logs_insight_query` - Cancels in progress CloudWatch logs insights query

### Required IAM Permissions
* `cloudwatch:DescribeAlarms`
* `cloudwatch:DescribeAlarmHistory`
* `cloudwatch:GetMetricData`
* `cloudwatch:ListMetrics`

* `logs:DescribeLogGroups`
* `logs:DescribeQueryDefinitions`
* `logs:ListLogAnomalyDetectors`
* `logs:ListAnomalies`
* `logs:StartQuery`
* `logs:GetQueryResults`
* `logs:StopQuery`

## Installation

### Option 1: Python (UVX)
#### Prerequisites
1. Install `uv` from [Astral](https://docs.astral.sh/uv/getting-started/installation/) or the [GitHub README](https://github.com/astral-sh/uv#installation)
2. Install Python using `uv python install 3.10`

#### One Click Install

| Cursor | VS Code |
|:------:|:-------:|
| [![Install MCP Server](https://cursor.com/deeplink/mcp-install-light.svg)](https://cursor.com/en/install-mcp?name=awslabs.cloudwatch-mcp-server&config=ewogICAgImF1dG9BcHByb3ZlIjogW10sCiAgICAiZGlzYWJsZWQiOiBmYWxzZSwKICAgICJjb21tYW5kIjogInV2eCBhd3NsYWJzLmNsb3Vkd2F0Y2gtbWNwLXNlcnZlckBsYXRlc3QiLAogICAgImVudiI6IHsKICAgICAgIkFXU19QUk9GSUxFIjogIltUaGUgQVdTIFByb2ZpbGUgTmFtZSB0byB1c2UgZm9yIEFXUyBhY2Nlc3NdIiwKICAgICAgIkZBU1RNQ1BfTE9HX0xFVkVMIjogIkVSUk9SIgogICAgfSwKICAgICJ0cmFuc3BvcnRUeXBlIjogInN0ZGlvIgp9) | [![Install on VS Code](https://img.shields.io/badge/Install_on-VS_Code-FF9900?style=flat-square&logo=visualstudiocode&logoColor=white)](https://insiders.vscode.dev/redirect/mcp/install?name=CloudWatch%20MCP%20Server&config=%7B%22autoApprove%22%3A%5B%5D%2C%22disabled%22%3Afalse%2C%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.cloudwatch-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22AWS_PROFILE%22%3A%22%5BThe%20AWS%20Profile%20Name%20to%20use%20for%20AWS%20access%5D%22%2C%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%7D%2C%22transportType%22%3A%22stdio%22%7D) |

#### MCP Config (Q CLI, Cline)
* For Q CLI, update MCP Config Amazon Q Developer CLI (~/.aws/amazonq/mcp.json)
* For Cline click on "Configure MCP Servers" option from MCP tab
```json
{
  "mcpServers": {
    "awslabs.cloudwatch-mcp-server": {
      "autoApprove": [],
      "disabled": false,
      "command": "uvx",
      "args": [
        "awslabs.cloudwatch-mcp-server@latest"
      ],
      "env": {
        "AWS_PROFILE": "[The AWS Profile Name to use for AWS access]",
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
    "awslabs.cloudwatch-mcp-server": {
      "disabled": false,
      "timeout": 60,
      "type": "stdio",
      "command": "uv",
      "args": [
        "tool",
        "run",
        "--from",
        "awslabs.cloudwatch-mcp-server@latest",
        "awslabs.cloudwatch-mcp-server.exe"
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


Please reference [AWS documentation](https://docs.aws.amazon.com/cli/v1/userguide/cli-configure-files.html) to create and manage your credentials profile

### Option 2: Docker Image
#### Prerequisites
Build and install docker image locally on the same host of your LLM client
1. Install [Docker](https://docs.docker.com/desktop/)
2. `git clone https://github.com/awslabs/mcp.git`
3. Go to sub-directory `cd src/cloudwatch-mcp-server/`
4. Run `docker build -t awslabs/cloudwatch-mcp-server:latest .`

#### One Click Cursor Install
[![Install CloudWatch MCP Server](https://cursor.com/deeplink/mcp-install-light.svg)](https://www.cursor.com/install-mcp?name=awslabs.cloudwatch-mcp-server&config=ewogICAgICAgICJjb21tYW5kIjogImRvY2tlciIsCiAgICAgICAgImFyZ3MiOiBbCiAgICAgICAgICAicnVuIiwKICAgICAgICAgICItLXJtIiwKICAgICAgICAgICItLWludGVyYWN0aXZlIiwKICAgICAgICAgICItZSBBV1NfUFJPRklMRT1bVGhlIEFXUyBQcm9maWxlIE5hbWVdIiwKICAgICAgICAgICJhd3NsYWJzL2Nsb3Vkd2F0Y2gtbWNwLXNlcnZlcjpsYXRlc3QiCiAgICAgICAgXSwKICAgICAgICAiZW52Ijoge30sCiAgICAgICAgImRpc2FibGVkIjogZmFsc2UsCiAgICAgICAgImF1dG9BcHByb3ZlIjogW10KfQ==)

#### MCP Config using Docker image(Q CLI, Cline)
```json
  {
    "mcpServers": {
      "awslabs.cloudwatch-mcp-server": {
        "command": "docker",
        "args": [
          "run",
          "--rm",
          "--interactive",
          "-v ~/.aws:/root/.aws",
          "-e AWS_PROFILE=[The AWS Profile Name to use for AWS access]",
          "awslabs/cloudwatch-mcp-server:latest"
        ],
        "env": {},
        "disabled": false,
        "autoApprove": []
      }
    }
  }
```
Please reference [AWS documentation](https://docs.aws.amazon.com/cli/v1/userguide/cli-configure-files.html) to create and manage your credentials profile

## Contributing

Contributions are welcome! Please see the [CONTRIBUTING.md](https://github.com/awslabs/mcp/blob/main/CONTRIBUTING.md) in the monorepo root for guidelines.

## Feedback and Issues

We value your feedback! Submit your feedback, feature requests and any bugs at [GitHub issues](https://github.com/awslabs/mcp/issues) with prefix `cloudwatch-mcp-server` in title.
