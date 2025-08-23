# AWS Labs Athena MCP Server

A Model Context Protocol (MCP) server for Amazon Athena.

## Features
- **Execute Read-Only SQL Statements**: Run commands such as `SELECT`, `VALUES`, `DESCRIBE`, and `SHOW`
- **Data Discovery**: Browse databases, tables, and schema information across multiple regions and catalogs
- **Workgroup Information**: List and view configuration values for Athena workgroups
- **Pagination Support**: Handle large result sets via pagination

## Basic Usage Examples
- "Show me the top 10 most popular products in the sales table in Athena"
- "Show me all databases available in us-west-2 and us-east-1"
- "What tables are available in the sales database?"
- "What data is stored in the customers table in the sales database?"
- "List all Athena workgroups and their configurations"
- "Execute this SQL query using the workgroup called my_workgroup: `SELECT * FROM my_db.my_table LIMIT 10`"

## Prerequisites
1. Install `uv` from [Astral](https://docs.astral.sh/uv/getting-started/installation/) or follow instructions from [the Astral GitHub README](https://github.com/astral-sh/uv#installation)
2. Install Python 3.10 or newer using, for example: `uv python install 3.10`
3. Configure AWS credentials with read-only access to Athena. This MCP server will attempt to block queries that are not read-only, but ensuring the credentials are read-only provides an additional layer of security.

## Installation Options

Note that all of the below options include setting the environment variable `AWS_PROFILE`. You'll need to change the example value of `the-aws-profile-name` to the actual name of the AWS profile you want the Athena MCP server to use.

[![Install](https://img.shields.io/badge/Install-Cursor-blue?style=flat-square&logo=cursor)](https://cursor.com/en/install-mcp?name=awslabs.athena-mcp-server&config=eyJjb21tYW5kIjoidXZ4IGF3c2xhYnMuYXRoZW5hLW1jcC1zZXJ2ZXJAbGF0ZXN0IiwiZW52Ijp7IkFXU19QUk9GSUxFIjoidGhlLWF3cy1wcm9maWxlLW5hbWUifSwiZGlzYWJsZWQiOmZhbHNlLCJhdXRvQXBwcm92ZSI6W119)
[![Install on VS Code](https://img.shields.io/badge/Install-VS_Code-FF9900?style=flat-square&logo=visualstudiocode&logoColor=white)](https://insiders.vscode.dev/redirect/mcp/install?name=Amazon%20Athena%20MCP%20Server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.athena-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22AWS_PROFILE%22%3A%22the-aws-profile-name%22%7D%2C%22disabled%22%3Afalse%2C%22autoApprove%22%3A%5B%5D%7D)

### JSON
Configure the MCP server in your MCP client configuration, for example:

```json
{
  "mcpServers": {
    "awslabs.athena-mcp-server": {
      "command": "uvx",
      "args": ["awslabs.athena-mcp-server@latest"],
      "env": {
        "AWS_PROFILE": "the-aws-profile-name"
      },
      "disabled": false,
      "autoApprove": []
    }
  }
}
```

### Claude Code
Run:
```sh
claude mcp add awslabs.athena-mcp-server -e AWS_PROFILE=the-aws-profile-name -- uvx awslabs.athena-mcp-server@latest
```

## Tools

| Tool | Description |
|------|-------------|
| `execute_query` | Executes a read-only SQL query in Athena and returns the results directly |
| `get_query_results` | Retrieves results from a completed query execution (mainly for pagination) |
| `list_databases` | Lists databases in the specified data catalog |
| `list_tables` | Lists tables within a specified database |
| `get_table_metadata` | Gets detailed metadata for a specific table including schema |
| `list_work_groups` | Lists available Athena workgroups with their configuration |
| `get_work_group` | Gets detailed workgroup configuration and settings |
| `list_data_catalogs` | Lists available data catalogs beyond the default AwsDataCatalog |
