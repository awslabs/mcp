# AWS Lake Formation MCP Server

An AWS Labs Model Context Protocol (MCP) server for AWS Lake Formation. This server provides read-only tools for querying Lake Formation permissions, data lake settings, registered resources, and effective permissions for S3 paths.

## Features

- **Permissions Management**: List and filter Lake Formation permissions by principal, database, table, or resource type
- **Data Lake Settings**: Retrieve data lake administrator configuration and default permissions
- **Resource Management**: List and describe registered Lake Formation resources (S3 locations)
- **Effective Permissions**: Query effective permissions for a given S3 resource path

## Prerequisites

1. Python 3.10 or newer
2. [uv](https://docs.astral.sh/uv/getting-started/installation/) package manager
3. AWS credentials configured via AWS CLI or environment variables
4. IAM permissions for Lake Formation read operations:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "lakeformation:ListPermissions",
        "lakeformation:GetDataLakeSettings",
        "lakeformation:ListResources",
        "lakeformation:DescribeResource",
        "lakeformation:GetEffectivePermissionsForPath"
      ],
      "Resource": "*"
    }
  ]
}
```

## Installation

Configure the MCP server in your MCP client configuration (e.g., for Kiro, edit `~/.kiro/settings/mcp.json`):

```json
{
  "mcpServers": {
    "awslabs.lakeformation-mcp-server": {
      "command": "uvx",
      "args": ["awslabs.lakeformation-mcp-server@latest"],
      "env": {
        "AWS_PROFILE": "default",
        "AWS_REGION": "us-east-1",
        "FASTMCP_LOG_LEVEL": "ERROR"
      },
      "disabled": false,
      "autoApprove": []
    }
  }
}
```

### Docker

After building with `docker build -t awslabs/lakeformation-mcp-server:latest .`:

```json
{
  "mcpServers": {
    "awslabs.lakeformation-mcp-server": {
      "command": "docker",
      "args": [
        "run",
        "--rm",
        "--interactive",
        "--env",
        "AWS_ACCESS_KEY_ID",
        "--env",
        "AWS_SECRET_ACCESS_KEY",
        "--env",
        "AWS_REGION=us-east-1",
        "awslabs/lakeformation-mcp-server:latest"
      ]
    }
  }
}
```

### Environment Variables

- `AWS_REGION`: AWS region to use (default: `us-east-1`)
- `AWS_PROFILE`: AWS profile to use (optional)
- `FASTMCP_LOG_LEVEL`: Logging level (`DEBUG`, `INFO`, `WARNING`, `ERROR`)

## Available Tools

### manage_aws_lakeformation_permissions

List Lake Formation permissions with optional filters.

**Parameters:**

- `operation` (required): `list-permissions`
- `principal` (optional): Principal ARN to filter by
- `database_name` (optional): Database name to filter by
- `table_name` (optional): Table name to filter by
- `catalog_id` (optional): AWS account ID of the Data Catalog
- `resource_type` (optional): One of `CATALOG`, `DATABASE`, `TABLE`, `DATA_LOCATION`
- `max_results` (optional): Maximum results (1-1000, default: 100)

### manage_aws_lakeformation_datalakesettings

Retrieve data lake settings.

**Parameters:**

- `operation` (required): `get-data-lake-settings`
- `catalog_id` (optional): AWS account ID

### manage_aws_lakeformation_resources

List or describe registered Lake Formation resources.

**Parameters:**

- `operation` (required): `list-resources` or `describe-resource`
- `resource_arn` (optional): S3 resource ARN (required for `describe-resource`)
- `max_results` (optional): Maximum results (1-1000, default: 100)

### manage_aws_lakeformation_effective_permissions

Get effective permissions for a given S3 resource path.

**Parameters:**

- `resource_arn` (required): S3 path ARN to get effective permissions for
- `catalog_id` (optional): AWS account ID of the Data Catalog

## Known Limitations

- When using `manage_aws_lakeformation_permissions` with only a `principal` filter and no resource filter, the Lake Formation API may return incomplete or unexpected results. Always combine a `principal` filter with a resource filter (e.g., `database_name`, `table_name`, or `resource_type`) for reliable output.
