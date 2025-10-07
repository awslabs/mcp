# AWS DynamoDB MCP Server

The official MCP Server for interacting with AWS DynamoDB

This server provides expert DynamoDB design guidance and data modeling assistance.

## Available MCP Tools

### Design & Modeling
- `dynamodb_data_modeling` - Retrieves the complete DynamoDB Data Modeling Expert prompt

## Migration Notice

Starting with version 2.0.0, this server focuses exclusively on DynamoDB design and modeling guidance. All operational DynamoDB management tools (table operations, item operations, queries, backups, etc.) have been removed in favour of the [AWS API MCP Server](https://github.com/awslabs/mcp/tree/main/src/aws-api-mcp-server) which provides the same capability and more.

### Recommended: AWS API MCP Server

For operational DynamoDB management, use the [AWS API MCP Server](https://github.com/awslabs/mcp/tree/main/src/aws-api-mcp-server) which provides comprehensive AWS service management including all DynamoDB operations. [Migration guide available here](https://github.com/awslabs/mcp/tree/main/src/aws-api-mcp-server).

### Not Recommended: Legacy Version

If you must use the previous operational tools, you can pin to version 1.0.9, though this is not recommended:

```json
{
  "mcpServers": {
    "awslabs.dynamodb-mcp-server": {
      "command": "uvx",
      "args": ["awslabs.dynamodb-mcp-server@1.0.9"],
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

## Instructions

This MCP Server provides DynamoDB design and modeling guidance only. For operational DynamoDB management (retrieving data, managing tables, etc.), use the [AWS API MCP Server](https://github.com/awslabs/mcp/tree/main/src/aws-api-mcp-server) which provides comprehensive DynamoDB operations. [Migration guide available here](https://github.com/awslabs/mcp/tree/main/src/aws-api-mcp-server).


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
