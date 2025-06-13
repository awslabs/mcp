# AWS S3 Tables MCP Server

An AWS Labs Model Context Protocol (MCP) server for AWS S3 Tables that enables AI assistants to interact with S3-based table storage.

## Overview

The S3 Tables MCP Server provides tools to manage AWS S3 Tables, including table buckets, namespaces, and individual tables. It serves as a bridge between AI assistants and AWS S3 Tables, allowing for safe and efficient table operations through the Model Context Protocol (MCP).

## Features

- **Table Bucket Management**: Create, delete, and manage table buckets
- **Namespace Management**: Create and delete namespaces within table buckets
- **Table Management**: Create, delete, rename, and manage individual tables
- **Encryption Management**: Configure and manage encryption settings for tables and buckets
- **Maintenance Configuration**: Set up and manage maintenance configurations for tables and buckets
- **Policy Management**: Manage resource policies for tables and buckets
- **Metadata Management**: Handle table metadata and locations
- **Read-Only Mode**: Optional security feature to restrict operations to read-only operations

## Prerequisites

1. Install `uv` from [Astral](https://docs.astral.sh/uv/getting-started/installation/) or the [GitHub README](https://github.com/astral-sh/uv#installation)
2. Install Python using `uv python install 3.10`
3. AWS account with permissions to create and manage AWS S3 Tables resources

## Setup

### IAM Configuration

The authorization between the MCP server and your AWS accounts are performed with AWS profile you setup on the host. There are several ways to setup a AWS profile, however we recommend creating a new IAM role that has `AmazonS3TablesReadOnlyAccess` permission following the principle of "least privilege". Note, if you want to use tools that mutate your resources, you need to grant `AmazonS3TablesFullAccess`. Finally, configure a AWS profile on the host that assumes the new role (for more information, check out the [AWS CLI help page](https://docs.aws.amazon.com/cli/v1/userguide/cli-configure-role.html)).

### Installation

Configure the MCP server in your MCP client configuration (e.g., for Amazon Q Developer CLI, edit `~/.aws/amazonq/mcp.json`):

```json
{
  "mcpServers": {
    "awslabs.s3-tables-mcp-server": {
      "command": "uvx",
      "args": ["awslabs.s3-tables-mcp-server@latest"],
      "env": {
        "AWS_PROFILE": "your-aws-profile",
        "AWS_REGION": "us-east-1"
      }
    }
  }
}
```

or docker after a successful `docker build -t awslabs/s3-tables-mcp-server.`:

```file
# fictitious `.env` file with AWS temporary credentials
AWS_ACCESS_KEY_ID=<from the profile you set up>
AWS_SECRET_ACCESS_KEY=<from the profile you set up>
AWS_SESSION_TOKEN=<from the profile you set up>
```

```json
{
  "mcpServers": {
    "awslabs.s3-tables-mcp-server": {
      "command": "docker",
      "args": [
        "run",
        "--rm",
        "--interactive",
        "--env-file",
        "/full/path/to/file/above/.env",
        "awslabs/s3-tables-mcp-server:latest"
      ],
      "env": {},
      "disabled": false,
      "autoApprove": []
    }
  }
}
```

## Server Configuration Options

The AWS S3 Tables MCP Server supports several command-line arguments that can be used to configure its behavior:

### `--allow-write`

Enables tools that create or modify resources in the user's AWS account. When this flag is not enabled, the server runs in read-only mode that only allows read operations. This enhances security by preventing any modifications to the tables. In read-only mode:

- Read operations (`list_table_buckets`, `list_namespaces`, `list_tables`) work normally
- Write operations (`create_table_bucket`, `delete_table_bucket`, etc.) are blocked and return a permission error

This mode is particularly useful for:
- Demonstration environments
- Security-sensitive applications
- Integration with public-facing AI assistants
- Protecting production tables from unintended modifications

Example:
```bash
python -m awslabs.s3_tables_mcp_server.server --allow-write
```

## Available Tools

The S3 Tables MCP Server provides the following tools:

### Table Bucket Management

- `create_table_bucket`: Create a new table bucket
- `delete_table_bucket`: Delete a table bucket
- `list_table_buckets`: List all table buckets for your AWS account

### Namespace Management

- `create_namespace`: Create a new namespace within a table bucket
- `delete_namespace`: Delete a namespace
- `list_namespaces`: List all namespaces across all table buckets

### Table Management

- `create_table`: Create a new table in a namespace
- `delete_table`: Delete a table
- `rename_table`: Rename a table or move it to a different namespace
- `list_tables`: List all tables across all table buckets and namespaces

### Encryption Management

- `put_table_bucket_encryption`: Set encryption configuration for a table bucket
- `delete_table_bucket_encryption`: Delete encryption configuration for a table bucket
- `get_table_encryption`: Get encryption configuration for a table

### Maintenance Configuration

- `put_table_bucket_maintenance_configuration`: Set maintenance configuration for a table bucket
- `put_table_maintenance_configuration`: Set maintenance configuration for a table
- `get_table_maintenance_configuration`: Get maintenance configuration for a table
- `get_table_maintenance_job_status`: Get status of a maintenance job

### Policy Management

- `put_table_bucket_policy`: Create or replace a table bucket policy
- `delete_table_bucket_policy`: Delete a table bucket policy
- `get_table_policy`: Get details about a table policy
- `delete_table_policy`: Delete a table policy

### Metadata Management

- `get_table_metadata_location`: Get the location of table metadata
- `update_table_metadata_location`: Update the metadata location for a table

## Usage Examples

### Basic Table Operations (Read-Only)

```python
# List all table buckets
buckets_result = await use_mcp_tool(
    server_name="awslabs.s3-tables-mcp-server",
    tool_name="list_table_buckets"
)

# List all namespaces
namespaces_result = await use_mcp_tool(
    server_name="awslabs.s3-tables-mcp-server",
    tool_name="list_namespaces"
)

# List all tables
tables_result = await use_mcp_tool(
    server_name="awslabs.s3-tables-mcp-server",
    tool_name="list_tables"
)
```

### Enabling Write Operations

To enable write operations, start the server with the `--allow-write` flag:

```bash
python -m awslabs.s3_tables_mcp_server.server --allow-write
```

When the server is running with write operations enabled:

```python
# Create a new table bucket
create_bucket_result = await use_mcp_tool(
    server_name="awslabs.s3-tables-mcp-server",
    tool_name="create_table_bucket",
    arguments={
        "name": "my-table-bucket",
        "encryption_configuration": {
            "type": "SSE_S3"
        }
    }
)

# Create a new namespace
create_namespace_result = await use_mcp_tool(
    server_name="awslabs.s3-tables-mcp-server",
    tool_name="create_namespace",
    arguments={
        "table_bucket_arn": "arn:aws:s3tables:region:account:table-bucket/my-table-bucket",
        "namespace": "my-namespace"
    }
)

# Create a new table
create_table_result = await use_mcp_tool(
    server_name="awslabs.s3-tables-mcp-server",
    tool_name="create_table",
    arguments={
        "table_bucket_arn": "arn:aws:s3tables:region:account:table-bucket/my-table-bucket",
        "namespace": "my-namespace",
        "name": "my-table",
        "format": "ICEBERG"
    }
)

# Without the --allow-write flag, you would receive this error:
# ValueError: "Operation not permitted: Server is configured in read-only mode"
```

## Security Considerations

When using this MCP server, consider:

- The MCP server needs permissions to create and manage AWS S3 Tables resources
- Resource creation is disabled by default, enable it by setting the `--allow-write` flag
- Follow the principle of least privilege when setting up IAM permissions
- Use separate AWS profiles for different environments (dev, test, prod)
- Implement proper error handling in your client applications

## Troubleshooting

- If you encounter permission errors, verify your IAM user has the correct policies attached
- For connection issues, check network configurations and security groups
- For general AWS S3 Tables issues, consult the [AWS S3 Tables documentation](https://docs.aws.amazon.com/s3/)

## Version

Current MCP server version: 0.1.0
