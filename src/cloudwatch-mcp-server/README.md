# AWS Labs cloudwatch MCP Server

This AWS Labs Model Context Protocol (MCP) server for CloudWatch enables your troubleshooting agents to use CloudWatch data to do AI-powered root cause analysis and provide recommendations. It offers comprehensive observability tools that simplify monitoring, reduce context switching, and help teams quickly diagnose and resolve service issues. This server will provide AI agents with seamless access to CloudWatch telemetry data through standardized MCP interfaces, eliminating the need for custom API integrations and reducing context switching during troubleshooting workflows. By consolidating access to all CloudWatch capabilities, we enable powerful cross-service correlations and insights that accelerate incident resolution and improve operational visibility.

## Instructions

The CloudWatch MCP Server provides specialized tools to address common operational scenarios including alarm troubleshooting, understand metrics definitions, alarm recommendations and log analysis. Each tool encapsulates one or multiple CloudWatch APIs into task-oriented operations.

## Features

Alarm Based Troubleshooting - Identifies active alarms, retrieves related metrics and logs, and analyzes historical alarm patterns to determine root causes of triggered alerts. Provides context-aware recommendations for remediation.

Log Analyzer - Analyzes a CloudWatch log group for anomalies, message patterns, and error patterns within a specified time window.

Metric Definition Analyzer - Provides comprehensive descriptions of what metrics represent, how they're calculated, recommended statistics to use for metric data retrieval

Alarm Recommendations - Suggests recommended alarm configurations for CloudWatch metrics, including thresholds, evaluation periods, and other alarm

## Prerequisites

1. Install `uv` from [Astral](https://docs.astral.sh/uv/getting-started/installation/) or the [GitHub README](https://github.com/astral-sh/uv#installation)
2. Install Python using `uv python install 3.10`
3. An AWS account with [CloudWatch Telemetry](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/WhatIsCloudWatch.html)
4. This MCP server can only be run locally on the same host as your LLM client.
5. Set up AWS credentials with access to AWS services
   - You need an AWS account with appropriate permissions
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
        "AWS_REGION": "[The target AWS region]",
        "FASTMCP_LOG_LEVEL": "ERROR"
      },
      "transportType": "stdio"
    }
  }
}
```

Please reference [AWS documentation](https://docs.aws.amazon.com/cli/v1/userguide/cli-configure-files.html) to create and manage your credentials profile

### Build and install docker image locally on the same host of your LLM client

1. `git clone https://github.com/awslabs/mcp.git`
2. Go to sub-directory 'src/cloudwatch-mcp-server/'
3. Run 'docker build -t awslabs/cloudwatch-mcp-server:latest .'

### Add or update your LLM client's config with following:
```file
# fictitious `.env` file with AWS temporary credentials
AWS_ACCESS_KEY_ID=<from the profile you set up>
AWS_SECRET_ACCESS_KEY=<from the profile you set up>
AWS_SESSION_TOKEN=<from the profile you set up>
```

```json
  {
    "mcpServers": {
      "awslabs.cloudwatch-mcp-server": {
        "command": "docker",
        "args": [
          "run",
          "--rm",
          "--interactive",
          "--env-file",
          "/full/path/to/file/above/.env",
          "awslabs/cloudwatch-mcp-server:latest"
        ],
        "env": {},
        "disabled": false,
        "autoApprove": []
      }
    }
  }
```
NOTE: Your credentials will need to be kept refreshed from your host

## Contributing

Contributions are welcome! Please see the [CONTRIBUTING.md](../../CONTRIBUTING.md) in the monorepo root for guidelines.
