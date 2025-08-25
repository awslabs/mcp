# AWS Labs CloudTrail MCP Server

This AWS Labs Model Context Protocol (MCP) server for CloudTrail enables your AI agents to query AWS account activity for security investigations, compliance auditing, and operational troubleshooting. It provides comprehensive access to CloudTrail events and CloudTrail Lake analytics, allowing agents to track API calls, analyze user activity, and perform advanced security analysis. This server gives AI agents seamless access to CloudTrail data through standardized MCP interfaces, eliminating the need for custom API integrations and enabling powerful security insights and audit capabilities.

## Instructions

The CloudTrail MCP Server provides specialized tools to address common security and operational scenarios including event lookup, user activity analysis, API call tracking, and advanced CloudTrail Lake analytics. Each tool encapsulates one or multiple CloudTrail APIs into task-oriented operations.

## Features

**Event Lookup** - Search CloudTrail events by various attributes including username, event name, resource name, and more. Provides access to the last 90 days of management events for security investigations and troubleshooting.

**CloudTrail Lake Analytics** - Execute advanced SQL queries against CloudTrail Lake for complex analytics, filtering, and aggregation. Supports Trino-compatible SQL syntax for comprehensive event analysis.

**User Activity Analysis** - Track and analyze user activities across AWS services by filtering events by username, access key, or other user-related attributes.

**API Call Tracking** - Monitor specific API calls and their patterns across your AWS environment for security and compliance purposes.

**Event Data Store Management** - List and explore available CloudTrail Lake Event Data Stores to understand data sources and capabilities.

## Prerequisites
1. An AWS account with [CloudTrail](https://docs.aws.amazon.com/awscloudtrail/latest/userguide/cloudtrail-user-guide.html) enabled. CloudTrail Event History is enabled by default. CloudTrail Lake needs to be enabled for advance SQL queries.
2. This MCP server can only be run locally on the same host as your LLM client.
3. Set up AWS credentials with access to AWS services
   - You need an AWS account with appropriate permissions (See required permissions below)
   - Configure AWS credentials with `aws configure` or environment variables

## Available Tools

### Tools for CloudTrail Events
* `lookup_events` - Look up CloudTrail events based on various criteria such as username, event name, resource name, etc. Provides access to the last 90 days of management events with pagination support

### Tools for CloudTrail Lake Analytics
* `lake_query` - Execute SQL queries against CloudTrail Lake for complex analytics and filtering. Supports Trino-compatible SQL syntax for advanced analysis
* `list_event_data_stores` - List available CloudTrail Lake Event Data Stores with their capabilities and event selectors
* `get_query_status` - Get the status of a CloudTrail Lake query to monitor long-running queries
* `get_query_results` - Get the results of a completed CloudTrail Lake query with pagination support for large result sets

### Required IAM Permissions
* `cloudtrail:LookupEvents`
* `cloudtrail:ListEventDataStores`
* `cloudtrail:GetEventDataStore`
* `cloudtrail:StartQuery`
* `cloudtrail:DescribeQuery`
* `cloudtrail:GetQueryResults`

## Installation

### Option 1: Python (UVX)
#### Prerequisites
1. Install `uv` from [Astral](https://docs.astral.sh/uv/getting-started/installation/) or the [GitHub README](https://github.com/astral-sh/uv#installation)
2. Install Python using `uv python install 3.10`

#### One Click Install

| Cursor | VS Code |
|:------:|:-------:|
| [![Install MCP Server](https://cursor.com/deeplink/mcp-install-light.svg)](https://cursor.com/en/install-mcp?name=awslabs.cloudtrail-mcp-server&config=ewogICAgImF1dG9BcHByb3ZlIjogW10sCiAgICAiZGlzYWJsZWQiOiBmYWxzZSwKICAgICJjb21tYW5kIjogInV2eCBhd3NsYWJzLmNsb3VkdHJhaWwtbWNwLXNlcnZlckBsYXRlc3QiLAogICAgImVudiI6IHsKICAgICAgIkFXU19QUk9GSUxFIjogIltUaGUgQVdTIFByb2ZpbGUgTmFtZSB0byB1c2UgZm9yIEFXUyBhY2Nlc3NdIiwKICAgICAgIkZBU1RNQ1BfTE9HX0xFVkVMIjogIkVSUk9SIgogICAgfSwKICAgICJ0cmFuc3BvcnRUeXBlIjogInN0ZGlvIgp9) | [![Install on VS Code](https://img.shields.io/badge/Install_on-VS_Code-FF9900?style=flat-square&logo=visualstudiocode&logoColor=white)](https://insiders.vscode.dev/redirect/mcp/install?name=CloudTrail%20MCP%20Server&config=%7B%22autoApprove%22%3A%5B%5D%2C%22disabled%22%3Afalse%2C%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.cloudtrail-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22AWS_PROFILE%22%3A%22%5BThe%20AWS%20Profile%20Name%20to%20use%20for%20AWS%20access%5D%22%2C%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%7D%2C%22transportType%22%3A%22stdio%22%7D) |

#### MCP Config (Q CLI, Cline)
* For Q CLI, update MCP Config Amazon Q Developer CLI (~/.aws/amazonq/mcp.json)
* For Cline click on "Configure MCP Servers" option from MCP tab
```json
{
  "mcpServers": {
    "awslabs.cloudtrail-mcp-server": {
      "autoApprove": [],
      "disabled": false,
      "command": "uvx",
      "args": [
        "awslabs.cloudtrail-mcp-server@latest"
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

Please reference [AWS documentation](https://docs.aws.amazon.com/cli/v1/userguide/cli-configure-files.html) to create and manage your credentials profile

### Option 2: Docker Image
#### Prerequisites
Build and install docker image locally on the same host of your LLM client
1. Install [Docker](https://docs.docker.com/desktop/)
2. `git clone https://github.com/awslabs/mcp.git`
3. Go to sub-directory `cd src/cloudtrail-mcp-server/`
4. Run `docker build -t awslabs/cloudtrail-mcp-server:latest .`

#### One Click Cursor Install
[![Install CloudTrail MCP Server](https://cursor.com/deeplink/mcp-install-light.svg)](https://www.cursor.com/install-mcp?name=awslabs.cloudtrail-mcp-server&config=ewogICAgICAgICJjb21tYW5kIjogImRvY2tlciIsCiAgICAgICAgImFyZ3MiOiBbCiAgICAgICAgICAicnVuIiwKICAgICAgICAgICItLXJtIiwKICAgICAgICAgICItLWludGVyYWN0aXZlIiwKICAgICAgICAgICItZSBBV1NfUFJPRklMRT1bVGhlIEFXUyBQcm9maWxlIE5hbWVdIiwKICAgICAgICAgICJhd3NsYWJzL2Nsb3VkdHJhaWwtbWNwLXNlcnZlcjpsYXRlc3QiCiAgICAgICAgXSwKICAgICAgICAiZW52Ijoge30sCiAgICAgICAgImRpc2FibGVkIjogZmFsc2UsCiAgICAgICAgImF1dG9BcHByb3ZlIjogW10KfQ==)

#### MCP Config using Docker image(Q CLI, Cline)
```json
  {
    "mcpServers": {
      "awslabs.cloudtrail-mcp-server": {
        "command": "docker",
        "args": [
          "run",
          "--rm",
          "--interactive",
          "-v ~/.aws:/root/.aws",
          "-e AWS_PROFILE=[The AWS Profile Name to use for AWS access]",
          "awslabs/cloudtrail-mcp-server:latest"
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

We value your feedback! Submit your feedback, feature requests and any bugs at [GitHub issues](https://github.com/awslabs/mcp/issues) with prefix `cloudtrail-mcp-server` in title.
