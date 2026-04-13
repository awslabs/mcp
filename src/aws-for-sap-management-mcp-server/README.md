# AWS Labs AWS Systems Manager for SAP MCP Server

An AWS Labs Model Context Protocol (MCP) server for AWS Systems Manager for SAP. This server enables AI agents to manage SAP applications registered with AWS Systems Manager for SAP, run configuration checks, and schedule recurring operations via Amazon EventBridge Scheduler.

## Instructions

Use this MCP server to manage SAP applications registered with AWS Systems Manager for SAP. It supports listing and inspecting SAP applications, running and reviewing configuration checks, and scheduling recurring operations (configuration checks, start/stop) via Amazon EventBridge Scheduler. All tools support multi-region and multi-profile AWS access.

## Features

- SAP Application Management — List, inspect, register, start, and stop SAP applications (HANA and SAP_ABAP) registered with AWS Systems Manager for SAP.
- Configuration Checks — Discover available configuration check types, trigger checks against applications, and drill into sub-check and rule-level results.
- Scheduling — Create, list, enable/disable, and delete EventBridge Scheduler schedules for recurring configuration checks, application start, and application stop operations.
- Health Summary — Generate comprehensive Markdown-formatted health reports covering application status, component health, configuration checks, HANA log backup status, AWS Backup status, and CloudWatch metrics.

## Prerequisites

1. An AWS account with [AWS Systems Manager for SAP](https://docs.aws.amazon.com/systems-manager/latest/userguide/systems-manager-for-sap.html) configured
2. This MCP server can only be run locally on the same host as your LLM client.
3. Set up AWS credentials with access to AWS services
   - You need an AWS account with appropriate permissions (See required permissions below)
   - Configure AWS credentials with `aws configure` or environment variables

## Available Tools

### SAP Application Tools
* `list_applications` - List all SAP applications registered with AWS Systems Manager for SAP
* `get_application` - Get detailed metadata for a specific SAP application including components
* `get_component` - Get detailed health status for a specific component of an SAP application
* `get_operation` - Get the status of an async operation (register, start, stop)
* `register_application` - Register an SAP application (HANA or SAP_ABAP) with SSM for SAP
* `start_application` - Start an SAP application
* `stop_application` - Stop an SAP application with optional EC2 shutdown

### Configuration Check Tools
* `list_config_check_definitions` - List all available configuration check types and metadata
* `start_config_checks` - Trigger configuration checks against a specified application
* `get_config_check_summary` - Get a summary of the latest configuration check results
* `get_config_check_operation` - Get details of a specific configuration check operation
* `list_sub_check_results` - List sub-check results for a configuration check operation
* `list_sub_check_rule_results` - List rule evaluation results for a specific sub-check

### Scheduling Tools
* `schedule_config_checks` - Schedule recurring configuration checks via EventBridge Scheduler
* `schedule_start_application` - Schedule automatic start of an SAP application
* `schedule_stop_application` - Schedule automatic stop of an SAP application
* `list_app_schedules` - List all EventBridge Scheduler schedules for a specific application
* `delete_schedule` - Delete an EventBridge Scheduler schedule
* `update_schedule_state` - Enable or disable a schedule
* `get_schedule_details` - Get detailed information about a specific schedule

### Health Summary Tools
* `get_sap_health_summary` - Get comprehensive health summary for one or all SAP applications, including application/component status, configuration checks with subchecks and rule results, HANA log backup status, AWS Backup status, and CloudWatch EC2 metrics
* `generate_health_report` - Generate a detailed, downloadable Markdown health report covering all health dimensions for one or all SAP applications

### Required IAM Permissions

#### SSM for SAP
* `ssm-sap:ListApplications`
* `ssm-sap:GetApplication`
* `ssm-sap:ListComponents`
* `ssm-sap:GetComponent`
* `ssm-sap:GetOperation`
* `ssm-sap:RegisterApplication`
* `ssm-sap:StartApplication`
* `ssm-sap:StopApplication`
* `ssm-sap:ListConfigurationCheckDefinitions`
* `ssm-sap:StartConfigurationChecks`
* `ssm-sap:ListConfigurationCheckOperations`
* `ssm-sap:GetConfigurationCheckOperation`
* `ssm-sap:ListSubCheckResults`
* `ssm-sap:ListSubCheckRuleResults`

#### EventBridge Scheduler (for scheduling tools)
* `scheduler:CreateSchedule`
* `scheduler:GetSchedule`
* `scheduler:ListSchedules`
* `scheduler:DeleteSchedule`
* `scheduler:UpdateSchedule`

#### IAM (for scheduler role management)
* `iam:GetRole`
* `iam:CreateRole`
* `iam:AttachRolePolicy`
* `sts:GetCallerIdentity`

#### SSM (for health summary log backup and filesystem checks)
* `ssm:DescribeInstanceInformation`
* `ssm:SendCommand`
* `ssm:GetCommandInvocation`
* `ssm:ListCommands`

#### AWS Backup (for health summary backup status)
* `backup:ListBackupPlans`
* `backup:ListBackupJobs`

#### CloudWatch (for health summary EC2 metrics)
* `cloudwatch:GetMetricStatistics`
* `cloudwatch:ListMetrics`

## Installation

### Option 1: Python (UVX)
#### Prerequisites
1. Install `uv` from [Astral](https://docs.astral.sh/uv/getting-started/installation/) or the [GitHub README](https://github.com/astral-sh/uv#installation)
2. Install Python using `uv python install 3.10`

#### MCP Config (Kiro, Cline)
* For Kiro, update MCP Config (~/.kiro/settings/mcp.json)
* For Cline click on "Configure MCP Servers" option from MCP tab
```json
{
  "mcpServers": {
    "awslabs.aws-for-sap-management-mcp-server": {
      "autoApprove": [],
      "disabled": false,
      "command": "uvx",
      "args": [
        "awslabs.aws-for-sap-management-mcp-server@latest"
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
    "awslabs.aws-for-sap-management-mcp-server": {
      "disabled": false,
      "timeout": 60,
      "type": "stdio",
      "command": "uv",
      "args": [
        "tool",
        "run",
        "--from",
        "awslabs.aws-for-sap-management-mcp-server@latest",
        "awslabs.aws-for-sap-management-mcp-server.exe"
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
3. Go to sub-directory `cd src/aws-for-sap-management-mcp-server/`
4. Run `docker build -t awslabs/aws-for-sap-management-mcp-server:latest .`

#### MCP Config using Docker image (Kiro, Cline)
```json
{
  "mcpServers": {
    "awslabs.aws-for-sap-management-mcp-server": {
      "command": "docker",
      "args": [
        "run",
        "--rm",
        "--interactive",
        "-v",
        "~/.aws:/root/.aws",
        "-e",
        "AWS_PROFILE=[The AWS Profile Name to use for AWS access]",
        "awslabs/aws-for-sap-management-mcp-server:latest"
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

We value your feedback! Submit your feedback, feature requests and any bugs at [GitHub issues](https://github.com/awslabs/mcp/issues) with prefix `aws-for-sap-management-mcp-server` in title.
