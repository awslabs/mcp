# AWS DynamoDB MCP Server

The official MCP Server for interacting with AWS DynamoDB

This comprehensive server provides both operational DynamoDB management and expert design guidance, featuring 30+ operational tools for managing DynamoDB tables, items, indexes, backups, and more, expert data modeling guidance.

## Available MCP Tools

### Design & Modeling
- `dynamodb_data_modeling` - Retrieves the complete DynamoDB Data Modeling Expert prompt

### Table Operations
- `create_table` - Creates a new DynamoDB table with optional secondary indexes
- `delete_table` - Deletes a table and all of its items
- `describe_table` - Returns table information including status, creation time, key schema and indexes
- `list_tables` - Returns a paginated list of table names in your account
- `update_table` - Modifies table settings including provisioned throughput, global secondary indexes, and DynamoDB Streams configuration

### Item Operations
- `get_item` - Returns attributes for an item with the given primary key
- `put_item` - Creates a new item or replaces an existing item in a table
- `update_item` - Edits an existing item's attributes, or adds a new item if it does not already exist
- `delete_item` - Deletes a single item in a table by primary key

### Query and Scan Operations
- `query` - Returns items from a table or index matching a partition key value, with optional sort key filtering
- `scan` - Returns items and attributes by scanning a table or secondary index

### Backup and Recovery
- `create_backup` - Creates a backup of a DynamoDB table
- `describe_backup` - Describes an existing backup of a table
- `list_backups` - Returns a list of table backups
- `restore_table_from_backup` - Creates a new table from a backup
- `describe_continuous_backups` - Returns continuous backup and point in time recovery status
- `update_continuous_backups` - Enables or disables point in time recovery

### Time to Live (TTL)
- `update_time_to_live` - Enables or disables Time to Live (TTL) for the specified table
- `describe_time_to_live` - Returns the Time to Live (TTL) settings for a table

### Export Operations
- `describe_export` - Returns information about a table export
- `list_exports` - Returns a list of table exports

### Tags and Resource Policies
- `put_resource_policy` - Attaches a resource-based policy document to a table or stream
- `get_resource_policy` - Returns the resource-based policy document attached to a table or stream
- `tag_resource` - Adds tags to a DynamoDB resource
- `untag_resource` - Removes tags from a DynamoDB resource
- `list_tags_of_resource` - Returns tags for a DynamoDB resource

### Misc
- `describe_limits` - Returns the current provisioned-capacity quotas for your AWS account
- `describe_endpoints` - Returns DynamoDB endpoints for the current region

## Instructions

The official MCP Server for interacting with AWS DynamoDB provides a comprehensive set of tools for both designing and managing DynamoDB resources.

To use these tools, ensure you have proper AWS credentials configured with appropriate permissions for DynamoDB operations. The server will automatically use credentials from environment variables (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_SESSION_TOKEN) or other standard AWS credential sources.

All tools support an optional `region_name` parameter to specify which AWS region to operate in. If not provided, it will use the AWS_REGION environment variable or default to 'us-west-2'.

## Prerequisites

1. Install `uv` from [Astral](https://docs.astral.sh/uv/getting-started/installation/) or the [GitHub README](https://github.com/astral-sh/uv#installation)
2. Install Python using `uv python install 3.10`
3. Set up AWS credentials with access to AWS services
   - Consider setting up Read-only permission if you don't want the LLM to modify any resources

## Installation

| Cursor | VS Code |
|:------:|:-------:|
| [![Install MCP Server](https://cursor.com/deeplink/mcp-install-light.svg)](https://cursor.com/en/install-mcp?name=awslabs.dynamodb-mcp-server&config=JTdCJTIyY29tbWFuZCUyMiUzQSUyMnV2eCUyMGF3c2xhYnMuZHluYW1vZGItbWNwLXNlcnZlciU0MGxhdGVzdCUyMiUyQyUyMmVudiUyMiUzQSU3QiUyMkREQi1NQ1AtUkVBRE9OTFklMjIlM0ElMjJ0cnVlJTIyJTJDJTIyQVdTX1BST0ZJTEUlMjIlM0ElMjJkZWZhdWx0JTIyJTJDJTIyQVdTX1JFR0lPTiUyMiUzQSUyMnVzLXdlc3QtMiUyMiUyQyUyMkZBU1RNQ1BfTE9HX0xFVkVMJTIyJTNBJTIyRVJST1IlMjIlN0QlMkMlMjJkaXNhYmxlZCUyMiUzQWZhbHNlJTJDJTIyYXV0b0FwcHJvdmUlMjIlM0ElNUIlNUQlN0Q%3D)| [![Install on VS Code](https://img.shields.io/badge/Install_on-VS_Code-FF9900?style=flat-square&logo=visualstudiocode&logoColor=white)](https://insiders.vscode.dev/redirect/mcp/install?name=DynamoDB%20MCP%20Server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.dynamodb-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22DDB-MCP-READONLY%22%3A%22true%22%2C%22AWS_PROFILE%22%3A%22default%22%2C%22AWS_REGION%22%3A%22us-west-2%22%2C%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%7D%2C%22disabled%22%3Afalse%2C%22autoApprove%22%3A%5B%5D%7D) |

Add the MCP to your favorite agentic tools. (e.g. for Amazon Q Developer CLI MCP, `~/.aws/amazonq/mcp.json`):

```json
{
  "mcpServers": {
    "awslabs.dynamodb-mcp-server": {
      "command": "uvx",
      "args": ["awslabs.dynamodb-mcp-server@latest"],
      "env": {
        "DDB-MCP-READONLY": "true",
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
### Windows Installation

For Windows users, the MCP server configuration format is slightly different:

```json
{
  "mcpServers": {
    "awslabs.dynamodb-mcp-server": {
      "disabled": false,
      "timeout": 60,
      "type": "stdio",
      "command": "uv",
      "args": [
        "tool",
        "run",
        "--from",
        "awslabs.dynamodb-mcp-server@latest",
        "awslabs.dynamodb-mcp-server.exe"
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


or docker after a successful `docker build -t awslabs/dynamodb-mcp-server .`:

```json
  {
    "mcpServers": {
      "awslabs.dynamodb-mcp-server": {
        "command": "docker",
        "args": [
          "run",
          "--rm",
          "--interactive",
          "--env",
          "FASTMCP_LOG_LEVEL=ERROR",
          "awslabs/dynamodb-mcp-server:latest"
        ],
        "env": {},
        "disabled": false,
        "autoApprove": []
      }
    }
  }
```
