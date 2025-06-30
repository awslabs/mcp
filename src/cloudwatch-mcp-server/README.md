# AWS Labs cloudwatch MCP Server

An AWS Labs Model Context Protocol (MCP) server for CloudWatch provides AI-powered troubleshooting tools across metrics, alarms, logs, and traces, enabling rapid root cause analysis and intelligent recommendations. It offers comprehensive observability tools that simplify monitoring, reduce context switching, and help teams quickly diagnose and resolve service issues. This server will provide AI agents and application developers with seamless access to CloudWatch telemetry data through standardized MCP interfaces, eliminating the need for custom API solutions and reducing context switching during troubleshooting workflows. By consolidating access to all CloudWatch capabilities, we enable powerful cross-service correlations and insights that accelerate incident resolution and improve operational visibility.

## Instructions

The CloudWatch MCP Server provides specialized tools to address common operational scenarios including alarm troubleshooting, understand metrics definitions,  alarm recommendations and log analysis. Each tool encapsulates multiple CloudWatch APIs into task-oriented operations. Along with specialized tools, each service offers core tools that enables seamless interaction with CloudWatch services.

## Features

Alarm Based Troubleshooting - Identifies active alarms, retrieves related metrics and logs, and analyzes historical alarm patterns to determine root causes of triggered alerts. Provides context-aware recommendations for remediation.

API Gateway Lambda Diagnostics - Correlates API Gateway metrics with Lambda execution logs to pinpoint failures in serverless applications. Identifies cold starts, timeouts, and error patterns affecting API performance.

Log Analyzer -  Analyzes a CloudWatch log group for anomalies, message patterns, and error patterns within a specified time window.

SLO Compliance Analyzer - Evaluates Service Level Objective compliance by examining traces and logs for breached thresholds. Helps identify service dependencies contributing to SLO violations and recommend corrective actions.

Metric Definition Analyzer - Provides comprehensive descriptions of what metrics represent, how they're calculated. Differentiates between standard and custom metrics.

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
* `get_metric_metadata` - Retrieves retrieves comprehensive metadata about a specific CloudWatch metric
* `get_recommended_metric_alarms` - Gets recommended alarms for a CloudWatch metric

### Core Tools from CloudWatch Alarms
* `get_active_alarms` - Identifies currently active alarms across the account
* `get_alarm_history` - Retrieves historical alarm state changes and patterns

### Core Tools from CloudWatch Dashboards
* `list_dashboards` - Discovers available CloudWatch dashboards
* `get_dashboard_data` - Retrieves the widgets and data from dashboards
* `get_dashboard_recommendations` - Recommends dashboard improvements

### Core Tools from CloudWatch Logs
* `describe_log_groups` - Finds metadata about log groups
* `analyze_log_group` - Analyzes logs for anomalies, message patterns, and error patterns
* `execute_log_insights_query` - Executes queries with time-frame and query input
* `get_logs_insight_query_results` - Retrieves results from executed queries
* `cancel_logs_insight_query` - Cancels running queries

### Core Tools from CloudWatch Application Signals
* `list_monitored_services` - Lists all services monitored by Application Signals
* `get_service_detail` - Gets health data for specific services
* `get_service_metrics` - Queries CloudWatch metrics for monitored services
* `list_slis` - Monitors SLI status and SLO compliance across services
* `get_slo` - Gets SLO setup information in the account
* `get_traces_for_slo` - Retrieves traces related to SLO breaches
* `query_sampled_traces` - Queries AWS X-Ray traces data
* `search_transaction_spans` - Queries OTel Spans data via Transaction Search

### Required IAM Permissions
* `cloudwatch:DescribeAlarms`
* `cloudwatch:DescribeAlarmHistory`
* `cloudwatch:GetMetricData`
* `cloudwatch:ListMetrics`
* `cloudwatch:GetMetricStatistics`
* `cloudwatch:DescribeInsightRules`
* `cloudwatch:GetInsightRuleReport`

* `logs:DescribeLogGroups`
* `logs:DescribeQueryDefinitions`
* `logs:ListLogAnomalyDetectors`
* `logs:ListAnomalies`
* `logs:StartQuery`
* `logs:GetQueryResults`
* `logs:StopQuery`

## Installation

[![Install MCP Server](https://cursor.com/deeplink/mcp-install-light.svg)](https://cursor.com/install-mcp?name=awslabs.cloudwatch-mcp-server&config=ewogICAgImF1dG9BcHByb3ZlIjogW10sCiAgICAiZGlzYWJsZWQiOiBmYWxzZSwKICAgICJ0aW1lb3V0IjogNjAsCiAgICAiY29tbWFuZCI6ICJ1dnggYXdzbGFicy5jbG91ZHdhdGNoLW1jcC1zZXJ2ZXJAbGF0ZXN0IiwKICAgICJlbnYiOiB7CiAgICAgICJBV1NfUFJPRklMRSI6ICJbVGhlIEFXUyBQcm9maWxlIE5hbWUgdG8gdXNlIGZvciBBV1MgYWNjZXNzXSIsCiAgICAgICJBV1NfUkVHSU9OIjogIltUaGUgQVdTIHJlZ2lvbiB0byBydW4gaW5dIiwKICAgICAgIkZBU1RNQ1BfTE9HX0xFVkVMIjogIkVSUk9SIgogICAgfSwKICAgICJ0cmFuc3BvcnRUeXBlIjogInN0ZGlvIgp)

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
