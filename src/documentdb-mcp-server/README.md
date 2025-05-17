# AWS DocumentDB MCP Server

An AWS Labs Model Context Protocol (MCP) server for AWS DocumentDB that enables AI assistants to interact with DocumentDB databases.

## Overview

The DocumentDB MCP Server provides tools to connect to and query AWS DocumentDB databases. It serves as a bridge between AI assistants and AWS DocumentDB, allowing for safe and efficient database operations through the Model Context Protocol (MCP).

## Features

- **Connection Management**: Establish and maintain connections to DocumentDB clusters
- **Database Management**: List databases and retrieve database statistics
- **Collection Management**: List, create, drop collections and retrieve collection statistics
- **Document Operations**: Query, insert, update, and delete documents
- **Aggregation Pipelines**: Execute DocumentDB aggregation pipelines
- **Query Planning**: Get explanations of how operations will be executed
- **Schema Analysis**: Analyze collection schemas by sampling documents
- **Read-Only Mode**: Optional security feature to restrict operations to read-only operations

## Available Tools

The DocumentDB MCP Server provides the following tools:

### Connection Management

- `connect`: Connect to a DocumentDB cluster and get a connection ID
- `disconnect`: Close an active connection

### Database Management

- `listDatabases`: List all available databases in the DocumentDB cluster
- `getDatabaseStats`: Get statistics about a DocumentDB database

### Collection Management

- `listCollections`: List collections in a database
- `createCollection`: Create a new collection in a database (blocked in read-only mode)
- `dropCollection`: Drop a collection from a database (blocked in read-only mode)
- `getCollectionStats`: Get statistics about a collection
- `countDocuments`: Count documents in a collection
- `analyzeSchema`: Analyze the schema of a collection by sampling documents and providing field coverage

### Document Operations

- `find`: Query documents from a collection
- `aggregate`: Run aggregation pipelines
- `insert`: Insert documents (blocked in read-only mode)
- `update`: Update documents (blocked in read-only mode)
- `delete`: Delete documents (blocked in read-only mode)

### Query Planning

- `explainOperation`: Get an explanation of how an operation will be executed

## Server Configuration

### Starting the Server

```bash
# Basic usage
python -m awslabs.documentdb_mcp_server.server

# With custom port and host
python -m awslabs.documentdb_mcp_server.server --port 9000 --host 0.0.0.0

# With write operations enabled
python -m awslabs.documentdb_mcp_server.server --allow-write
```

### Command Line Options

| Option | Description | Default |
|--------|-------------|---------|
| `--port` | Port to run the server on | 8888 |
| `--host` | Host to bind the server to | 127.0.0.1 |
| `--sse` | Use SSE transport | False |
| `--log-level` | Set logging level (TRACE, DEBUG, INFO, etc.) | INFO |
| `--connection-timeout` | Idle connection timeout in minutes | 30 |
| `--allow-write` | Enable write operations (otherwise defaults to read-only mode) | False |

### Read-Only Mode

By default, the server runs in read-only mode that only allows read operations. This enhances security by preventing any modifications to the database. In read-only mode:

- Read operations (`find`, `aggregate`, `listCollections`) work normally
- Write operations (`insert`, `update`, `delete`) are blocked and return a permission error
- Connection management operations (`connect`, `disconnect`) work normally

This mode is particularly useful for:
- Demonstration environments
- Security-sensitive applications
- Integration with public-facing AI assistants
- Protecting production databases from unintended modifications

## Usage Examples

### Basic Connection and Query (Read-Only Operations)

```python
# Connect to a DocumentDB cluster
connection_result = await use_mcp_tool(
    server_name="awslabs.aws-documentdb-mcp-server",
    tool_name="connect",
    arguments={
        "connection_string": "mongodb://<username>:<password>@docdb-cluster.cluster-xyz.us-west-2.docdb.amazonaws.com:27017/?tls=true&tlsCAFile=global-bundle.pem"
    }
)
connection_id = connection_result["connection_id"]

# Query documents
query_result = await use_mcp_tool(
    server_name="awslabs.aws-documentdb-mcp-server",
    tool_name="find",
    arguments={
        "connection_id": connection_id,
        "database": "my_database",
        "collection": "users",
        "query": {"active": True},
        "limit": 5
    }
)

# Close the connection when done
await use_mcp_tool(
    server_name="awslabs.aws-documentdb-mcp-server",
    tool_name="disconnect",
    arguments={"connection_id": connection_id}
)
```

### Enabling Write Operations

To enable write operations, start the server with the `--allow-write` flag:

```bash
python -m awslabs.documentdb_mcp_server.server --allow-write
```

When the server is running with write operations enabled:

```python
# This operation will succeed
query_result = await use_mcp_tool(
    server_name="awslabs.aws-documentdb-mcp-server",
    tool_name="find",
    arguments={
        "connection_id": connection_id,
        "database": "my_database",
        "collection": "users",
        "query": {"active": True}
    }
)

# This operation will now succeed when --allow-write is used
insert_result = await use_mcp_tool(
    server_name="awslabs.aws-documentdb-mcp-server",
    tool_name="insert",
    arguments={
        "connection_id": connection_id,
        "database": "my_database",
        "collection": "users",
        "documents": {"name": "New User", "active": True}
    }
)

# Without the --allow-write flag, you would receive this error:
# ValueError: "Operation not permitted: Server is configured in read-only mode. Use --allow-write flag when starting the server to enable write operations."
```

## Prerequisites

- Network access to your DocumentDB cluster
- SSL/TLS certificate if your cluster requires TLS (typically `global-bundle.pem`)
