# AWS DocumentDB MCP Server

An AWS Labs Model Context Protocol (MCP) server for AWS DocumentDB that enables AI assistants to interact with DocumentDB databases.

## Overview

The DocumentDB MCP Server provides tools to query a single AWS DocumentDB cluster. It serves as a bridge between AI assistants and AWS DocumentDB, allowing for safe and efficient database operations through the Model Context Protocol (MCP).

The target cluster is configured by the operator at server startup (via the `--connection-string` CLI argument or the `DOCUMENTDB_CONNECTION_STRING` environment variable). Tools operate on that configured cluster directly and take only database/collection/query arguments.

## Features

- **Operator-configured connection**: Connect to a single DocumentDB cluster fixed at startup
- **Database Management**: List databases and retrieve database statistics
- **Collection Management**: List, create, drop collections and retrieve collection statistics
- **Document Operations**: Query, insert, update, and delete documents
- **Aggregation Pipelines**: Execute DocumentDB aggregation pipelines
- **Query Planning**: Get explanations of how operations will be executed
- **Schema Analysis**: Analyze collection schemas by sampling documents
- **Read-Only Mode**: Optional security feature to restrict operations to read-only operations

## Available Tools

The DocumentDB MCP Server provides the following tools. All tools operate on the cluster configured at server startup and take only database/collection/query arguments (no connection string or connection id):

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
- `aggregate`: Run aggregation pipelines (pipelines with `$out` or `$merge` stages are blocked in read-only mode)
- `insert`: Insert documents (blocked in read-only mode)
- `update`: Update documents (blocked in read-only mode)
- `delete`: Delete documents (blocked in read-only mode)

### Query Planning

- `explainOperation`: Get an explanation of how an operation will be executed

## Server Configuration

### Starting the Server

The server requires a connection string for the DocumentDB cluster it should connect to, supplied via the `DOCUMENTDB_CONNECTION_STRING` environment variable (recommended) or the `--connection-string` argument. If no connection string is configured, database tools fail until one is set.

Prefer the environment variable: a connection string passed as a command-line argument is visible to other local users via process listings (e.g. `ps`) and is often persisted in MCP client configuration files. The environment variable keeps the credentials out of `argv`.

```bash
# Recommended: provide the connection string via environment variable
export DOCUMENTDB_CONNECTION_STRING="mongodb://<username>:<password>@docdb-cluster.cluster-xyz.us-west-2.docdb.amazonaws.com:27017/?tls=true&tlsCAFile=global-bundle.pem&retryWrites=false"
python -m awslabs.documentdb_mcp_server.server

# With write operations enabled
DOCUMENTDB_CONNECTION_STRING="mongodb://...&retryWrites=false" \
  python -m awslabs.documentdb_mcp_server.server --allow-write

# Convenience only: pass the connection string as an argument. Note that this
# exposes the connection string (including any password) in process listings
# and client config files; prefer DOCUMENTDB_CONNECTION_STRING instead.
python -m awslabs.documentdb_mcp_server.server \
  --connection-string "mongodb://<username>:<password>@docdb-cluster.cluster-xyz.us-west-2.docdb.amazonaws.com:27017/?tls=true&tlsCAFile=global-bundle.pem&retryWrites=false"
```

### Command Line Options

| Option | Description | Default |
|--------|-------------|---------|
| `--log-level` | Set logging level (TRACE, DEBUG, INFO, etc.) | INFO |
| `--connection-string` | DocumentDB connection string for the cluster to connect to. Prefer the `DOCUMENTDB_CONNECTION_STRING` environment variable, which keeps credentials out of process listings and client config files. | None |
| `--allow-write` | Enable write operations (otherwise defaults to read-only mode) | False |

### Read-Only Mode

By default, the server runs in read-only mode that only allows read operations. This enhances security by preventing any modifications to the database. In read-only mode:

- Read operations (`find`, `listCollections`) work normally
- Aggregation pipelines (`aggregate`) work normally, except pipelines containing `$out` or `$merge` stages are blocked
- Write operations (`insert`, `update`, `delete`, `createCollection`, `dropCollection`) are blocked and return a permission error

This mode is particularly useful for:
- Demonstration environments
- Security-sensitive applications
- Integration with public-facing AI assistants
- Protecting production databases from unintended modifications

## Usage Examples

The cluster is configured when the server is started (see [Starting the Server](#starting-the-server)). Tools operate on that configured cluster and do not take a connection string or connection id.

### Basic Query (Read-Only Operations)

```python
# Query documents on the configured cluster
query_result = await use_mcp_tool(
    server_name="awslabs.aws-documentdb-mcp-server",
    tool_name="find",
    arguments={
        "database": "my_database",
        "collection": "users",
        "query": {"active": True},
        "limit": 5
    }
)
```

### Enabling Write Operations

To enable write operations, start the server with the `--allow-write` flag:

```bash
python -m awslabs.documentdb_mcp_server.server \
  --connection-string "mongodb://...&retryWrites=false" --allow-write
```

When the server is running with write operations enabled:

```python
# This operation will now succeed when --allow-write is used
insert_result = await use_mcp_tool(
    server_name="awslabs.aws-documentdb-mcp-server",
    tool_name="insert",
    arguments={
        "database": "my_database",
        "collection": "users",
        "documents": {"name": "New User", "active": True}
    }
)

# Without the --allow-write flag, you would receive this error:
# ValueError: "Operation not permitted: Server is configured in read-only mode. Use --allow-write flag when starting the server to enable write operations."
```

### Configure in your MCP client

| Kiro | Cursor | VS Code |
|:----:|:------:|:-------:|
| [![Add to Kiro](https://kiro.dev/images/add-to-kiro.svg)](https://kiro.dev/launch/mcp/add?name=awslabs.documentdb-mcp-server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.documentdb-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%2C%22AWS_PROFILE%22%3A%22your-aws-profile%22%7D%7D) | [![Install MCP Server](https://cursor.com/deeplink/mcp-install-light.svg)](https://cursor.com/en/install-mcp?name=awslabs.documentdb-mcp-server&config=eyJjb21tYW5kIjoidXZ4IGF3c2xhYnMuZG9jdW1lbnRkYi1tY3Atc2VydmVyQGxhdGVzdCIsImVudiI6eyJGQVNUTUNQX0xPR19MRVZFTCI6IkVSUk9SIiwiQVdTX1BST0ZJTEUiOiJ5b3VyLWF3cy1wcm9maWxlIn0sImRpc2FibGVkIjpmYWxzZSwiYXV0b0FwcHJvdmUiOltdfQ==) | [![Install on VS Code](https://img.shields.io/badge/Install_on-VS_Code-FF9900?style=flat-square&logo=visualstudiocode&logoColor=white)](https://insiders.vscode.dev/redirect/mcp/install?name=DocumentDB%20MCP%20Server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.documentdb-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%2C%22AWS_PROFILE%22%3A%22your-aws-profile%22%7D%2C%22disabled%22%3Afalse%2C%22autoApprove%22%3A%5B%5D%7D) |

Configure the MCP server in your MCP client configuration (e.g., for Kiro, edit ~/.kiro/settings/mcp.json):

```json
{
  "mcpServers": {
    "awslabs.documentdb-mcp-server": {
      "command": "uvx",
      "args": [
        "awslabs.documentdb-mcp-server@latest",
      ],
      "env": {
        "DOCUMENTDB_CONNECTION_STRING": "mongodb://<username>:<password>@docdb-cluster.cluster-xyz.us-west-2.docdb.amazonaws.com:27017/?tls=true&tlsCAFile=global-bundle.pem&retryWrites=false",
        "AWS_PROFILE": "your-aws-profile",
        "AWS_REGION": "us-east-1",
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
    "awslabs.documentdb-mcp-server": {
      "disabled": false,
      "timeout": 60,
      "type": "stdio",
      "command": "uv",
      "args": [
        "tool",
        "run",
        "--from",
        "awslabs.documentdb-mcp-server@latest",
        "awslabs.documentdb-mcp-server.exe"
      ],
      "env": {
        "DOCUMENTDB_CONNECTION_STRING": "mongodb://<username>:<password>@docdb-cluster.cluster-xyz.us-west-2.docdb.amazonaws.com:27017/?tls=true&tlsCAFile=global-bundle.pem&retryWrites=false",
        "FASTMCP_LOG_LEVEL": "ERROR",
        "AWS_PROFILE": "your-aws-profile",
        "AWS_REGION": "us-east-1"
      }
    }
  }
}
```


## Prerequisites

- Network access to your DocumentDB cluster
- SSL/TLS certificate if your cluster requires TLS (typically `global-bundle.pem`)
