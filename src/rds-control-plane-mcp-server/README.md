# AWS RDS Control Plane MCP Server

The official MCP Server for interacting with AWS RDS control plane. This server provides resources for monitoring, analyzing, and managing your Amazon RDS database instances and clusters.

## Available Resource Templates

### DB Cluster Resources
- `aws-rds://db-cluster` - List all available Amazon RDS clusters in your account
- `aws-rds://db-cluster/{cluster_id}` - Get detailed information about a specific RDS cluster

### DB Instance Resources
- `aws-rds://db-instance` - List all available Amazon RDS instances in your account
- `aws-rds://db-instance/{instance_id}` - Get detailed information about a specific RDS instance
- `aws-rds://db-instance/{dbi_resource_identifier}/log` - List all available non-empty log files for a specific RDS instance
- `aws-rds://db-instance/{dbi_resource_identifier}/performance_report` - List all available performance reports for a specific RDS instance
- `aws-rds://db-instance/{dbi_resource_identifier}/performance_report/{report_id}` - Read a specific performance report

### General Resources
- `aws-rds://{resource_type}/{resource_identifier}/cloudwatch_metrics` - List available metrics for a RDS resource (db-instance or db-cluster).

## Available Tools

### General Tools

- **DescribeRDSEvents** - List events for RDS resources (instances, clusters, snapshots, etc.) with filtering by category, time period, and source type.

### DB Cluster Tools

- **CreateDBCluster** - Create a new Amazon RDS database cluster.
- **DeleteDBCluster** - Delete an RDS database cluster.
- **FailoverDBCluster** - Force a failover for an RDS database cluster.
- **ModifyDBCluster** - Modify an existing RDS database cluster configuration.
- **ChangeDBClusterStatus** - Manage the status of an RDS database cluster.

### DB Instance Tools

- **CreateDBInstance** - Create a new Amazon RDS database instance.
- **DeleteDBInstance** - Delete an Amazon RDS database instance.
- **ModifyDBInstance** - Modify an existing Amazon RDS database instance.
- **ManageDBInstanceStatus** - Manage the status of an Amazon RDS database instance.
- **ReadDBLogFiles** - Read database log files from RDS instances.
- **CreatePerformanceReport** - Generate a comprehensive performance report for RDS resources including metrics, events, and recommendations.


## Instructions

The AWS RDS Control Plane MCP Server provides a comprehensive set of tools for monitoring, analyzing, and managing your Amazon RDS database instances and clusters. Each tool provides specific functionality for working with RDS resources, including performance analysis, log management, and accessing recommendations.

To use these tools, ensure you have proper AWS credentials configured with appropriate permissions for RDS operations. The server will automatically use credentials from environment variables (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_SESSION_TOKEN) or other standard AWS credential sources.

All tools support an optional `region_name` parameter to specify which AWS region to operate in. If not provided, it will use the AWS_REGION environment variable.

## Prerequisites

1. Install `uv` from [Astral](https://docs.astral.sh/uv/getting-started/installation/) or the [GitHub README](https://github.com/astral-sh/uv#installation)
2. Install Python using `uv python install 3.10`
3. Set up AWS credentials with access to RDS services
   - Consider setting up Read-only permission if you don't want the LLM to modify any resources

## Installation

[![Install MCP Server](https://cursor.com/deeplink/mcp-install-light.svg)](https://cursor.com/install-mcp?name=awslabs.rds-control-plane-mcp-server&config=eyJjb21tYW5kIjoidXZ4IGF3c2xhYnMucmRzLWNvbnRyb2wtcGxhbmUtbWNwLXNlcnZlckBsYXRlc3QiLCJlbnYiOnsiQVdTX1BST0ZJTEUiOiJkZWZhdWx0IiwiQVdTX1JFR0lPTiI6InVzLXdlc3QtMiIsIkZBU1RNQ1BfTE9HX0xFVkVMIjoiRVJST1IifSwiZGlzYWJsZWQiOmZhbHNlLCJhdXRvQXBwcm92ZSI6W119)

Add the MCP to your favorite agentic tools. (e.g. for Amazon Q Developer CLI MCP, `~/.aws/amazonq/mcp.json`):

```json
{
  "mcpServers": {
    "awslabs.rds-control-plane-mcp-server": {
      "command": "uvx",
      "args": ["awslabs.rds-control-plane-mcp-server@latest"],
      "env": {
        "AWS_PROFILE": "default",
        "AWS_REGION": "us-west-2",
        "FASTMCP_LOG_LEVEL": "ERROR"
      },
      "disabled": false,
      "autoApprove": []
    }
  }
}
```

If you would like to prevent the MCP from taking any mutating actions (i.e. Create/Update/Delete Resource), you can specify the readonly flag as demonstrated below:

```json
{
  "mcpServers": {
    "awslabs.rds-control-plane-mcp-server": {
      "command": "uvx",
      "args": [
        "awslabs.rds-control-plane-mcp-server@latest",
        "--readonly"
      ],
      "env": {
        "AWS_PROFILE": "default",
        "AWS_REGION": "us-west-2",
        "FASTMCP_LOG_LEVEL": "ERROR"
      },
      "disabled": false,
      "autoApprove": []
    }
  }
}
```

or docker after a successful `docker build -t awslabs/rds-control-plane-mcp-server .`:

```json
{
  "mcpServers": {
    "awslabs.rds-control-plane-mcp-server": {
      "command": "docker",
      "args": [
        "run",
        "--rm",
        "--interactive",
        "--env",
        "FASTMCP_LOG_LEVEL=ERROR",
        "awslabs/rds-control-plane-mcp-server:latest",
        "--readonly" // Optional parameter if you would like to restrict the MCP to only read actions
      ],
      "env": {},
      "disabled": false,
      "autoApprove": []
    }
  }
}
```

## Configuration

### AWS Configuration

Configure AWS credentials and region:

```bash
# AWS settings
AWS_PROFILE=default              # AWS credential profile to use
AWS_REGION=us-east-1             # AWS region to connect to
```

The server automatically handles:
- AWS authentication and credential management
- Connection establishment and management

### Server Settings

The following CLI arguments can be passed when running the server:

```bash
# Server CLI arguments
--max-items 100                # Maximum number of items returned from API responses
--port 8888                    # Port to run the server on
--readonly                     # Whether to run in readonly mode (prevents mutating operations)
--no-readonly                  # Whether to turn off readonly mode (allow mutating operations)
```

```json
{
  "mcpServers": {
    "awslabs.rds-control-plane-mcp-server": {
      "command": "uvx",
      "args": [
        "awslabs.rds-control-plane-mcp-server@latest",
        "--readonly", "[your data]",
        "--max-items", "[your data]",
        "--port", "[your data]",
      ],
      "env": {
        "AWS_PROFILE": "default",
        "AWS_REGION": "us-west-2",
        "FASTMCP_LOG_LEVEL": "ERROR"
      },
      "disabled": false,
      "autoApprove": []
    }
  }
}
```

## Development

### Running Tests
```bash
uv venv
source .venv/bin/activate
uv sync
uv run --frozen pytest
```

### Building Docker Image
```bash
docker build -t awslabs/rds-control-plane-mcp-server .
```

### Running Docker Container
```bash
docker run -p 8888:8888 \
  -e AWS_PROFILE=default \
  -e AWS_REGION=us-west-2 \
  awslabs/rds-control-plane-mcp-server
