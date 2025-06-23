# AWS Labs Athena MCP Server

A Model Context Protocol (MCP) server for Amazon Athena.

## Features
- **Execute Read-Only SQL Statements**: Run commands such as SELECT, VALUES, DESCRIBE, and SHOW
- **Data Discovery**: Browse databases, tables, and schema information across multiple regions and catalogs
- **Workgroup Information**: List and view configuration values for Athena workgroups
- **Pagination Support**: Handle large result sets via pagination

## Prerequisites
1. Install `uv` from [Astral](https://docs.astral.sh/uv/getting-started/installation/) or follow instruction from [the Astral GitHub README](https://github.com/astral-sh/uv#installation)
2. Install Python 3.10 or newer using, for example: `uv python install 3.10`
3. Configure AWS credentials with read-only access to Athena. This MCP server will attempt to block queries that are not read-only, but ensuring the credentials are read-only is a belt-and-suspenders approach.

## Installation
Configure the MCP server in your MCP client configuration, for example:

```json
{
  "mcpServers": {
    "awslabs.athena-mcp-server": {
      "command": "uvx",
      "args": ["awslabs.athena-mcp-server@latest"],
      "env": {
        "AWS_PROFILE": "your-aws-profile",
      },
      "disabled": false,
      "autoApprove": []
    }
  }
}
```

## Basic Usage Examples
- "Show me the top 10 most popular products in the sales table in Athena"
- "Show me all databases available in us-west-2 and us-east-1"
- "What tables are available in the sales database?"
- "What data is stored in the customers table in the sales database?"
- "List all Athena workgroups and their configurations"
- "Execute this SQL query using the workgroup called my_workgroup: SELECT * FROM my_db.my_table LIMIT 10"

## Tools
### execute_query
Executes a read-only SQL query in Athena and returns the results directly.

### get_query_results
Retrieves results from a completed query execution (mainly for pagination).

### list_databases
Lists databases in the specified data catalog.

### list_tables
Lists tables within a specified database.

### get_table_metadata
Gets detailed metadata for a specific table including schema.

### list_work_groups
Lists available Athena workgroups with their configuration.

### get_work_group
Gets detailed workgroup configuration and settings.

### list_data_catalogs
Lists available data catalogs beyond the default AwsDataCatalog.
