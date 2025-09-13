# AWS Database Migration Service MCP Server

An AWS MCP Server for AWS Database Migration Service (DMS), providing comprehensive tools for managing database migration workflows including replication instances, endpoints, replication tasks, and table-level operations through MCP tools.

## Features

- **Replication Instance Management**: Create and describe replication instances with support for Multi-AZ deployments
- **Endpoint Management**: Create, test, and describe source and target endpoints for various database engines
- **Replication Task Management**: Create, start, stop, and monitor replication tasks with different migration types
- **Table Operations**: Reload specific tables, get detailed table statistics, and monitor replication progress
- **Connection Testing**: Test connectivity between replication instances and endpoints with detailed results
- **Read-Only Mode**: Built-in read-only mode by default, with optional write access controls

## Available Tools

### Replication Instance Management

#### `describe_replication_instances`
List and describe DMS replication instances with optional filtering.

**Parameters:**
- `replication_instance_identifier` (optional): Filter by specific replication instance identifier
- `max_records` (optional): Maximum number of records to return (default: 20)
- `marker` (optional): Pagination token from previous request

#### `create_replication_instance`
Create a new DMS replication instance.

**Parameters:**
- `replication_instance_identifier`: Unique name for the replication instance
- `replication_instance_class`: Instance class (e.g., dms.t3.micro, dms.r5.large)
- `allocated_storage`: Storage size in GB (minimum 20 GB)
- `multi_az` (optional): Whether to deploy in multiple availability zones (default: false)
- `engine_version` (optional): DMS engine version (uses default if not specified)
- `auto_minor_version_upgrade` (optional): Whether to automatically upgrade minor versions (default: true)
- `preferred_maintenance_window` (optional): Weekly maintenance window (e.g., 'sun:23:00-mon:01:00')
- `replication_subnet_group_identifier` (optional): Subnet group for VPC deployment
- `vpc_security_group_ids` (optional): Comma-separated security group IDs
- `publicly_accessible` (optional): Whether the instance should be publicly accessible (default: false)
- `kms_key_id` (optional): KMS key for encryption
- `tags` (optional): Resource tags in JSON format

### Endpoint Management

#### `describe_endpoints`
List and describe DMS endpoints with optional filtering.

**Parameters:**
- `endpoint_identifier` (optional): Filter by specific endpoint identifier
- `endpoint_type` (optional): Filter by endpoint type ('source' or 'target')
- `engine_name` (optional): Filter by engine name
- `max_records` (optional): Maximum number of records to return (default: 20)
- `marker` (optional): Pagination token from previous request

#### `create_endpoint`
Create a new DMS endpoint for source or target databases.

**Parameters:**
- `endpoint_identifier`: Unique name for the endpoint
- `endpoint_type`: Whether this is a 'source' or 'target' endpoint
- `engine_name`: Database engine type (mysql, oracle, postgres, mariadb, aurora, aurora-postgresql)
- `username`: Database username for authentication
- `password`: Database password for authentication
- `server_name`: Database server hostname or IP address
- `port`: Database server port number
- `database_name`: Name of the database
- `ssl_mode` (optional): SSL connection mode ('none', 'require', 'verify-ca', 'verify-full') (default: 'none')
- `extra_connection_attributes` (optional): Additional connection parameters
- `kms_key_id` (optional): KMS key for encrypting connection parameters
- `tags` (optional): Resource tags in JSON format

#### `test_connection`
Test the connection between a replication instance and an endpoint.

**Parameters:**
- `replication_instance_arn`: The ARN of the replication instance
- `endpoint_arn`: The ARN of the endpoint to test

#### `describe_connections`
List existing connections between replication instances and endpoints.

**Parameters:**
- `filters` (optional): Filters to apply to the connection list. Each filter is a dictionary with:
  - `Name`: The filter name ('endpoint-arn' or 'replication-instance-arn')
  - `Values`: List of string values to filter by
- `max_records` (optional): Maximum number of records to return (default: 20)
- `marker` (optional): Pagination token from previous request

### Replication Task Management

#### `describe_replication_tasks`
List and describe replication tasks with detailed filtering options.

**Parameters:**
- `replication_task_identifier` (optional): Filter by specific replication task identifier
- `replication_instance_arn` (optional): Filter by replication instance ARN
- `migration_type` (optional): Filter by migration type ('full-load', 'cdc', 'full-load-and-cdc')
- `with_statistics` (optional): Include task statistics (default: false)
- `max_records` (optional): Maximum number of records to return (default: 20)
- `marker` (optional): Pagination token from previous request

#### `create_replication_task`
Create a new DMS replication task.

**Parameters:**
- `replication_task_identifier`: Unique identifier for the replication task
- `source_endpoint_arn`: ARN of the source database endpoint
- `target_endpoint_arn`: ARN of the target database endpoint
- `replication_instance_arn`: ARN of the replication instance to use
- `migration_type`: Type of migration ('full-load', 'cdc', or 'full-load-and-cdc')
- `table_mappings`: JSON string defining which tables/schemas to migrate
- `replication_task_settings` (optional): JSON string with task configuration
- `cdc_start_time` (optional): Start time for CDC (ISO 8601 format)
- `cdc_start_position` (optional): Start position for CDC
- `tags` (optional): Resource tags in JSON format

#### `start_replication_task`
Start a DMS replication task.

**Parameters:**
- `replication_task_arn`: ARN of the replication task to start
- `start_replication_task_type`: Type of start operation:
  - `'start-replication'`: Start a new replication task
  - `'resume-processing'`: Resume a paused task
  - `'reload-target'`: Reload the target database and restart replication

#### `stop_replication_task`
Stop a running DMS replication task.

**Parameters:**
- `replication_task_arn`: ARN of the replication task to stop

### Table-Level Operations

#### `describe_table_statistics`
Get detailed statistics about table replication progress.

**Parameters:**
- `replication_task_arn`: The ARN of the replication task
- `filters` (optional): Filters to apply to table statistics
- `max_records` (optional): Maximum number of records to return (default: 20)
- `marker` (optional): Pagination token from previous request

#### `reload_replication_task_tables`
Reload specific tables in a DMS replication task.

**Parameters:**
- `replication_task_arn`: The ARN of the replication task
- `tables_to_reload`: List of tables to reload, each with 'schema-name' and 'table-name' keys
- `reload_option` (optional): Either 'data-reload' (default) to reload data, or 'validate-only' to validate without reloading


## Migration Types Supported

- **full-load**: One-time migration of existing data from source to target
- **cdc**: Ongoing replication of changes only (Change Data Capture)
- **full-load-and-cdc**: Complete migration followed by ongoing replication

## Supported Database Engines

The following database engines are supported for both source and target endpoints:

- **mysql**: MySQL databases
- **oracle**: Oracle databases
- **postgres**: PostgreSQL databases
- **mariadb**: MariaDB databases
- **aurora**: Amazon Aurora (MySQL-compatible)
- **aurora-postgresql**: Amazon Aurora (PostgreSQL-compatible)

> **Note**: These engines can be used for both on-premises and cloud-based databases including Amazon RDS instances.

## Installation

Install using uv:

```bash
uv tool install awslabs.dms-mcp-server
```

Or using pip:

```bash
pip install awslabs.dms-mcp-server
```

## Prerequisites

1. Install `uv` from [Astral](https://docs.astral.sh/uv/getting-started/installation/) or the [GitHub README](https://github.com/astral-sh/uv#installation)
2. Install Python using `uv python install 3.10`
3. Set up AWS credentials with access to AWS services
   - Consider setting up Read-only permission if you don't want the LLM to modify any resources

## Installation

| Cursor | VS Code |
|:------:|:-------:|
| [![Install MCP Server](https://cursor.com/deeplink/mcp-install-light.svg)](https://cursor.com/en/install-mcp?name=awslabs.dms-mcp-server&config=eyJjb21tYW5kIjogInV2eCIsICJhcmdzIjogWyJhd3NsYWJzLmRtcy1tY3Atc2VydmVyQGxhdGVzdCJdLCAiZW52IjogeyJBV1NfUFJPRklMRSI6ICJkZWZhdWx0IiwgIkFXU19SRUdJT04iOiAidXMtZWFzdC0xIiwgIkZBU1RNQ1BfTE9HX0xFVkVMIjogIkVSUk9SIn0sICJkaXNhYmxlZCI6IGZhbHNlLCAiYXV0b0FwcHJvdmUiOiBbXX0=) | [![Install on VS Code](https://img.shields.io/badge/Install_on-VS_Code-FF9900?style=flat-square&logo=visualstudiocode&logoColor=white)](https://insiders.vscode.dev/redirect/mcp/install?name=DMS%20MCP%20Server&config=%7B%22command%22%3A%20%22uvx%22%2C%20%22args%22%3A%20%5B%22awslabs.dms-mcp-server%40latest%22%5D%2C%20%22env%22%3A%20%7B%22AWS_PROFILE%22%3A%20%22default%22%2C%20%22AWS_REGION%22%3A%20%22us-east-1%22%2C%20%22FASTMCP_LOG_LEVEL%22%3A%20%22ERROR%22%7D%2C%20%22disabled%22%3A%20false%2C%20%22autoApprove%22%3A%20%5B%5D%7D) |

Add the MCP to your favorite agentic tools. (e.g. for Amazon Q Developer CLI MCP, `~/.aws/amazonq/mcp.json`):

```json
{
  "mcpServers": {
    "awslabs.dms-mcp-mcp": {
      "command": "uvx",
      "args": [
        "awslabs.dms-mcp-server@latest",
        "--no-read-only-mode"
      ],
      "env": {
        "AWS_REGION": "us-east-1",
        "AWS_PROFILE": "default"
      }
    }
  }
}
```

### Windows Installation

For Windows users, the MCP server configuration format is slightly different:

```json
{
  "mcpServers": {
    "awslabs.dms-mcp-server": {
      "disabled": false,
      "timeout": 60,
      "type": "stdio",
      "command": "uv",
      "args": [
        "tool",
        "run",
        "--from",
        "awslabs.dms-mcp-server@latest",
        "awslabs.dms-mcp-server.exe"
      ],
      "env": {
        "FASTMCP_LOG_LEVEL": "ERROR",
        "AWS_PROFILE": "default",
        "AWS_REGION": "us-east-1"
      }
    }
  }
}
```

or docker after a successful `docker build -t awslabs/dms-mcp-server .`:

```json
  {
    "mcpServers": {
      "awslabs.dms-mcp-server": {
        "command": "docker",
        "args": [
          "run",
          "--rm",
          "--interactive",
          "--env",
          "FASTMCP_LOG_LEVEL=ERROR",
          "awslabs/dms-mcp-server:latest"
        ],
        "env": {},
        "disabled": false,
        "autoApprove": []
      }
    }
  }
```


### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `AWS_REGION` | `us-east-1` | AWS region for DMS operations |
| `AWS_PROFILE` | `default` | AWS profile to use for authentication |

### Server Configuration Options

#### `--read-only-mode` / `--no-read-only-mode`

By default, the DMS MCP server runs in read-only mode for security (`--read-only-mode` is `true` by default).

To enable write operations, use the `--no-read-only-mode` parameter in your MCP client configuration:

```json
"args": [
    "awslabs.dms-mcp-server",
    "--no-read-only-mode"
]
```

To explicitly run in read-only mode (default behavior):

```json
"args": [
    "awslabs.dms-mcp-server",
    "--read-only-mode"
]
```

In read-only mode, only read operations (describe, test connection) are available. Write operations (create, start, stop) are disabled.

### AWS Authentication

The server supports standard AWS authentication methods:

- AWS CLI profiles (`aws configure`)
- Environment variables (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`)
- IAM roles (when running on EC2/ECS/Lambda)
- AWS SSO

### Required IAM Permissions

For full functionality, your AWS credentials need the following DMS permissions:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "dms:DescribeReplicationInstances",
        "dms:DescribeEndpoints",
        "dms:DescribeReplicationTasks",
        "dms:DescribeTableStatistics",
        "dms:TestConnection",
        "dms:DescribeConnections",
        "dms:CreateReplicationInstance",
        "dms:CreateEndpoint",
        "dms:CreateReplicationTask",
        "dms:StartReplicationTask",
        "dms:StopReplicationTask",
        "dms:ReloadTables"
      ],
      "Resource": "*"
    }
  ]
}
```


## Development

### Running Tests
```bash
uv venv
source .venv/bin/activate
uv sync
uv run --frozen pytest

# Run tests with coverage
uv run pytest --cov=awslabs.dms_mcp_server
```

### Local Development
```bash
# Install in development mode
uv pip install -e .

# Run the server directly
python -m awslabs.dms_mcp_server.server

# Run with write access enabled
python -m awslabs.dms_mcp_server.server --no-read-only-mode
```

## Contributing

Contributions are welcome! Please see the main repository's [CONTRIBUTING.md](https://github.com/awslabs/mcp/blob/main/CONTRIBUTING.md) for guidelines.

## License

This project is licensed under the Apache License 2.0. See the [LICENSE](https://github.com/awslabs/mcp/blob/main/src/dms-mcp-server/LICENSE) file for details.

## Support

For issues and questions:
1. Check the [AWS DMS documentation](https://docs.aws.amazon.com/dms/)
2. Review the [MCP specification](https://modelcontextprotocol.io/)
3. Open an issue in the [GitHub repository](https://github.com/awslabs/mcp)

## Changelog

See [CHANGELOG.md](https://github.com/awslabs/mcp/blob/main/src/dms-mcp-server/CHANGELOG.md) for version history and changes.
