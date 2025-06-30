# AWS Labs cloudwatch MCP Server

An AWS Labs Model Context Protocol (MCP) server for CloudWatch provides AI-powered troubleshooting tools across metrics, alarms, and logs, enabling rapid root cause analysis and intelligent recommendations. It offers comprehensive observability tools that simplify monitoring, reduce context switching, and help teams quickly diagnose and resolve service issues. This server will provide AI agents and application developers with seamless access to CloudWatch telemetry data through standardized MCP interfaces, eliminating the need for custom API solutions and reducing context switching during troubleshooting workflows. By consolidating access to all CloudWatch capabilities, we enable powerful cross-service correlations and insights that accelerate incident resolution and improve operational visibility.

## Instructions

The CloudWatch MCP Server provides specialized tools to address common operational scenarios including alarm troubleshooting, understand metrics definitions,  alarm recommendations and log analysis. Each tool encapsulates multiple CloudWatch APIs into task-oriented operations. Along with specialized tools, each service offers core tools that enables seamless interaction with CloudWatch services.

## Features

Alarm Based Troubleshooting - Identifies active alarms, retrieves related metrics and logs, and analyzes historical alarm patterns to determine root causes of triggered alerts. Provides context-aware recommendations for remediation.

Log Analyzer -  Analyzes a CloudWatch log group for anomalies, message patterns, and error patterns within a specified time window.

Metric Definition Analyzer - Provides comprehensive descriptions of what metrics represent, how they're calculated. 

Alarm Recommendations - Suggests optimal alarm configurations based on historical patterns and best practices. Helps reduce false positives and ensure appropriate coverage of critical metrics.


## Prerequisites

1. Install `uv` from [Astral](https://docs.astral.sh/uv/getting-started/installation/) or the [GitHub README](https://github.com/astral-sh/uv#installation)
2. Install Python using `uv python install 3.10`
3. An AWS account with [CloudWatch Telemetry](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/WhatIsCloudWatch.html)
4. This MCP server can only be run locally on the same host as your LLM client.
5. Set up AWS credentials with access to AWS services
   - You need an AWS account with appropriate permissions
   - Configure AWS credentials with `aws configure` or environment variables

## Available Tools

### Core Tools from CloudWatch Metrics
* `get_metric_data` - Retrieves detailed metric data for any CloudWatch metric
* `get_metric_metadata` - Retrieves comprehensive metadata about a specific CloudWatch metric
* `get_recommended_metric_alarms` - Gets recommended alarms for a CloudWatch metric

### Core Tools from CloudWatch Alarms
* `get_active_alarms` - Identifies currently active alarms across the account
* `get_alarm_history` - Retrieves historical alarm state changes and patterns

### Core Tools from CloudWatch Logs
* `describe_log_groups` - Finds metadata about log groups
* `analyze_log_group` - Analyzes logs for anomalies, message patterns, and error patterns
* `execute_log_insights_query` - Executes queries with time-frame and query input
* `get_logs_insight_query_results` - Retrieves results from executed queries
* `cancel_logs_insight_query` - Cancels running queries

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

[![Install MCP Server](https://cursor.com/deeplink/mcp-install-light.svg)](https://www.cursor.com/install-mcp?name=awslabs.cloudwatch-mcp-server&config=eyJhdXRvQXBwcm92ZSI6W10sImRpc2FibGVkIjpmYWxzZSwidGltZW91dCI6NjAsImNvbW1hbmQiOiJ1dnggYXdzbGFicy5jbG91ZHdhdGNoLW1jcC1zZXJ2ZXJAbGF0ZXN0IiwiZW52Ijp7IkFXU19QUk9GSUxFIjoiW1RoZSBBV1MgUHJvZmlsZSBOYW1lIHRvIHVzZSBmb3IgQVdTIGFjY2Vzc10iLCJBV1NfUkVHSU9OIjoiW1RoZSBBV1MgcmVnaW9uIHRvIHJ1biBpbl0iLCJGQVNUTUNQX0xPR19MRVZFTCI6IkVSUk9SIn0sInRyYW5zcG9ydFR5cGUiOiJzdGRpbyJ9)

Example for Amazon Q Developer CLI (~/.aws/amazonq/mcp.json):

```json
{
  "mcpServers": {
    "awslabs.cloudwatch-mcp-server": {
      "autoApprove": [],
      "disabled": false,
      "timeout": 60,
      "command": "uvx",
      "args": [
        "awslabs.cloudwatch-mcp-server@latest"
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
2. Go to sub-directory 'src/cloudwatch-mcp-server/'
3. Run 'docker build -t awslabs/cloudwatch-mcp-server:latest .'

### Add or update your LLM client's config with following:
```json
{
  "mcpServers": {
    "awslabs.cloudwatch-mcp-server": {
      "command": "docker",
      "args": [
        "run",
        "-i",
        "--rm",
        "-e", "AWS_PROFILE=[your data]",
        "-e", "AWS_REGION=[your data]",
        "awslabs/cloudwatch-mcp-server:latest"
      ]
    }
  }
}
```

## Contributing

Contributions are welcome! Please see the [CONTRIBUTING.md](../../CONTRIBUTING.md) in the monorepo root for guidelines.
