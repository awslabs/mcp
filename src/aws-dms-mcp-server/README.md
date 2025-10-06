# AWS Database Migration Service (DMS) MCP Server

[![Python Version](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE)

A Model Context Protocol (MCP) server providing natural language access to AWS Database Migration Service operations. Built on FastMCP framework with comprehensive type safety and validation.

## Features

- **13 MCP Tools** covering complete DMS workflows:
  - Replication instance management
  - Source/target endpoint configuration
  - Replication task lifecycle management
  - Table-level monitoring and operations
  - Connection testing and validation

- **Multi-Engine Support**: MySQL, PostgreSQL, Oracle, MariaDB, Aurora, Aurora-PostgreSQL

- **Production Ready**:
  - Type-safe with Pydantic validation
  - Comprehensive error handling
  - Read-only mode for safe analysis
  - Structured logging with loguru
  - 90%+ test coverage goal

## Installation

### Using uv (Recommended)

```bash
# Install from PyPI
uvx awslabs.aws-dms-mcp-server

# Or install in development mode
git clone https://github.com/awslabs/mcp.git
cd mcp/src/aws-dms-mcp-server
uv sync --group dev
```

### Using pip

```bash
pip install awslabs.aws-dms-mcp-server
```

## Quick Start

### 1. Configure AWS Credentials

```bash
export AWS_REGION=us-east-1
export AWS_ACCESS_KEY_ID=your-access-key
export AWS_SECRET_ACCESS_KEY=your-secret-key
```

### 2. Configure the Server

```bash
# Optional: Enable read-only mode
export DMS_READ_ONLY_MODE=true

# Optional: Set log level
export DMS_LOG_LEVEL=INFO
```

### 3. Run the Server

```bash
# Using the installed command
awslabs.aws-dms-mcp-server

# Or using Python module
python -m awslabs.aws_dms_mcp_server.server
```

### 4. Use with MCP Client

Add to your MCP client configuration:

```json
{
  "mcpServers": {
    "aws-dms": {
      "command": "awslabs.aws-dms-mcp-server",
      "env": {
        "AWS_REGION": "us-east-1",
        "DMS_READ_ONLY_MODE": "false"
      }
    }
  }
}
```

## Available Tools

### Replication Instance Tools

- **`describe_replication_instances`** - List and describe replication instances
- **`create_replication_instance`** - Create new replication instance with Multi-AZ support

### Endpoint Tools

- **`describe_endpoints`** - List source/target database endpoints
- **`create_endpoint`** - Create database endpoint with SSL support
- **`delete_endpoint`** - Delete a database endpoint
- **`test_connection`** - Test connectivity between instance and endpoint
- **`describe_connections`** - List connection test results

### Task Management Tools

- **`describe_replication_tasks`** - List replication tasks with status
- **`create_replication_task`** - Create migration task with table mappings
- **`start_replication_task`** - Start/resume/reload tasks
- **`stop_replication_task`** - Stop running tasks

### Table Operations Tools

- **`describe_table_statistics`** - Get table-level metrics
- **`reload_replication_tables`** - Reload specific tables

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DMS_AWS_REGION` | us-east-1 | AWS region for DMS operations |
| `DMS_AWS_PROFILE` | None | AWS credentials profile |
| `DMS_READ_ONLY_MODE` | false | Enable read-only mode |
| `DMS_DEFAULT_TIMEOUT` | 300 | Operation timeout (seconds) |
| `DMS_LOG_LEVEL` | INFO | Logging level |
| `DMS_ENABLE_STRUCTURED_LOGGING` | true | Enable JSON logging |

### Programmatic Configuration

```python
from awslabs.aws_dms_mcp_server import create_server, DMSServerConfig

config = DMSServerConfig(
    aws_region="us-west-2",
    read_only_mode=True,
    log_level="DEBUG"
)

server = create_server(config)
server.run()
```

## Development

### Setup Development Environment

```bash
# Clone repository
git clone https://github.com/awslabs/mcp.git
cd mcp/src/aws-dms-mcp-server

# Install with development dependencies
uv sync --group dev

# Run tests
pytest

# Run tests with coverage
pytest --cov

# Lint code
ruff check .

# Format code
ruff format .

# Type check
pyright
```

### Project Structure

```
awslabs/aws_dms_mcp_server/
├── __init__.py              # Package initialization
├── server.py                # MCP tool definitions
├── config.py                # Configuration models
├── models/                  # Pydantic data models
│   ├── config_models.py     # Input validation models
│   └── dms_models.py        # Response models
├── utils/                   # Business logic
│   ├── dms_client.py        # AWS SDK wrapper
│   ├── *_manager.py         # Operation managers
│   └── response_formatter.py
└── exceptions/              # Custom exceptions
    └── dms_exceptions.py
```

## IAM Permissions

Minimum required IAM permissions:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "dms:Describe*",
        "dms:TestConnection"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "dms:Create*",
        "dms:Start*",
        "dms:Stop*",
        "dms:ReloadTables"
      ],
      "Resource": "*"
    }
  ]
}
```

## Examples

### Example: Create Migration Workflow

```python
# 1. Create replication instance
create_replication_instance(
    replication_instance_identifier="my-instance",
    replication_instance_class="dms.t3.medium",
    allocated_storage=50,
    multi_az=True
)

# 2. Create source endpoint
create_endpoint(
    endpoint_identifier="source-mysql",
    endpoint_type="source",
    engine_name="mysql",
    server_name="mysql.example.com",
    port=3306,
    database_name="sourcedb",
    username="admin",
    password="password123",
    ssl_mode="require"
)

# 3. Create target endpoint
create_endpoint(
    endpoint_identifier="target-postgresql",
    endpoint_type="target",
    engine_name="postgres",
    server_name="postgres.example.com",
    port=5432,
    database_name="targetdb",
    username="admin",
    password="password456"
)

# 4. Test connections
test_connection(
    replication_instance_arn="arn:aws:dms:...:rep:my-instance",
    endpoint_arn="arn:aws:dms:...:endpoint:source-mysql"
)

# 5. Create replication task
create_replication_task(
    replication_task_identifier="migration-task",
    source_endpoint_arn="arn:aws:dms:...:endpoint:source-mysql",
    target_endpoint_arn="arn:aws:dms:...:endpoint:target-postgresql",
    replication_instance_arn="arn:aws:dms:...:rep:my-instance",
    migration_type="full-load-and-cdc",
    table_mappings='{"rules":[{"rule-type":"selection","rule-id":"1","object-locator":{"schema-name":"%","table-name":"%"},"rule-action":"include"}]}'
)

# 6. Start replication
start_replication_task(
    replication_task_arn="arn:aws:dms:...:task:migration-task",
    start_replication_task_type="start-replication"
)
```

## Troubleshooting

### Common Issues

1. **Connection Test Failures**
   - Verify security group rules allow traffic
   - Check database credentials
   - Ensure replication instance can reach endpoint

2. **Task Creation Failures**
   - Validate table mappings JSON syntax
   - Ensure endpoints are in "active" status
   - Check replication instance capacity

3. **Permission Errors**
   - Verify IAM permissions include required DMS actions
   - Check AWS credentials are properly configured

## Contributing

Contributions welcome! Please read [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

This project is licensed under the Apache License 2.0 - see [LICENSE](LICENSE) file for details.

## Support

- **Documentation**: [AWS Labs MCP Servers](https://awslabs.github.io/mcp/servers/aws-dms-mcp-server/)
- **Issues**: [GitHub Issues](https://github.com/awslabs/mcp/issues)
- **AWS DMS Documentation**: [AWS DMS User Guide](https://docs.aws.amazon.com/dms/)

## Related Projects

- [AWS Labs MCP](https://github.com/awslabs/mcp) - Monorepo for AWS MCP servers
- [FastMCP](https://github.com/jlowin/fastmcp) - MCP framework used by this server
- [Model Context Protocol](https://modelcontextprotocol.io/) - Protocol specification
- [AWS DMS](https://aws.amazon.com/dms/) - AWS Database Migration Service