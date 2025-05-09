# Valkey MCP Server

This server provides a natural language interface to interact with Amazon ElastiCache and MemoryDB [Valkey](https://valkey.io/) datastores. Amazon ElastiCache is a serverless, fully managed cache delivering real-time, cost-optimized performance for data-driven applications. Amazon MemoryDB is a durable, in-memory database service for ultra-fast performance. Both servuces offer full Valkey compatibility. At its core, Valkey provides a collection of native data types that help you solve a wide variety of problems, from caching to queuing to event processing.

## Features

### Supported Data Types
- **Strings**: Strings are the most basic Valkey data type, representing a sequence of bytes. You can store and retrieve strings with optional expiration for caching and session data.
- **Lists**: Lists are collections of strings sorted by insertion order. You can manage these collections with push/pop operations.
- **Sets**: Sets are unordered collections of unique strings that act like the sets from your favorite programming language. With a Set, you can add, remove, and test for existence in O(1) time (in other words, regardless of the number of set elements).
- **Sorted Sets**: Sorted Sets are collections of unique strings that maintain order by each string's associated score. These are typically used to manage scored elements for leaderboards and priority queues.
- **Hashes**: Hashes are record types modeled as collections of field-value pairs. As such, Hashes resemble Python dictionaries, Java HashMaps, and Ruby hashes.
- **Streams**: A Stream is a data structure that acts like an append-only log. Streams help record events in the order they occur and then syndicate them for processing. These are typically used to process time-series data and event streams.
- **Bitmaps**: Bitmaps let you perform bitwise operations on strings.
- **HyperLogLog**: HyperLogLog data structures provide probabilistic estimates of the cardinality (i.e., number of elements) of large sets.
- **JSONs**: Store and query JSON documents with path-based access

### Advanced Features
- **Cluster Support**: Support for standalone and clustered Valkey deployments.
- **SSL/TLS Security**: Configure secure connections using SSL/TLS.
- **Connection Pooling**: Pools connections by default to enable efficient connection management.

## Prerequisites

1. Install `uv` from [Astral](https://docs.astral.sh/uv/getting-started/installation/) or the [GitHub README](https://github.com/astral-sh/uv#installation)
2. Install Python using `uv python install 3.10`
3. Access to a Valkey datastore instance

## Installation

Here are some ways you can work with MCP across AWS tools (e.g., for Amazon Q Developer CLI MCP, `~/.aws/amazonq/mcp.json`):

```json
{
  "mcpServers": {
    "awslabs.valkey-mcp-server": {
      "command": "uvx",
      "args": [
        "awslabs.valkey-mcp-server@latest"
      ],
      "env": {
        "VALKEY_HOST": "127.0.0.1",
        "VALKEY_PORT": "6379",
        "FASTMCP_LOG_LEVEL": "ERROR"
      },
      "autoApprove": [],
      "disabled": false
    }
  }
}
```

Or using Docker after a successful `docker build -t awslabs/valkey-mcp-server .`:

```json
{
  "mcpServers": {
    "awslabs.valkey-mcp-server": {
      "command": "docker",
      "args": [
        "run",
        "--rm",
        "--interactive",
        "--env",
        "FASTMCP_LOG_LEVEL=ERROR",
        "--env",
        "VALKEY_HOST=127.0.0.1",
        "--env",
        "VALKEY_PORT=6379",
        "awslabs/valkey-mcp-server:latest"
      ],
      "env": {},
      "disabled": false,
      "autoApprove": []
    }
  }
}
```

## Configuration

The server can be configured using the following environment variables:

| Name | Description | Default Value |
|------|-------------|---------------|
| `VALKEY_HOST` | ElastiCache Primary Endpoint or MemoryDB Cluster Endpoint or Valkey IP or hostname | `"127.0.0.1"` |
| `VALKEY_PORT` | Valkey port | `6379` |
| `VALKEY_USERNAME` | Default database username | `None` |
| `VALKEY_PWD` | Default database password | `""` |
| `VALKEY_SSL` | Enables or disables SSL/TLS | `False` |
| `VALKEY_CA_PATH` | CA certificate for verifying server | `None` |
| `VALKEY_SSL_KEYFILE` | Client's private key file | `None` |
| `VALKEY_SSL_CERTFILE` | Client's certificate file | `None` |
| `VALKEY_CERT_REQS` | Server certificate verification | `"required"` |
| `VALKEY_CA_CERTS` | Path to trusted CA certificates | `None` |
| `VALKEY_CLUSTER_MODE` | Enable Valkey Cluster mode | `False` |

## Example Usage

Here are some example natural language queries that the server can handle:

```
"Store user profile data in a hash"
"Add this event to the activity stream"
"Cache API response for 5 minutes"
"Store JSON document with nested fields"
"Add score 100 to user123 in leaderboard"
"Get all members of the admins set"
```

## Development

### Running Tests
```bash
uv venv
source .venv/bin/activate
uv sync
uv run --frozen pytest
```

### Building Docker Image
```bash
docker build -t awslabs/valkey-mcp-server .
```

### Running Docker Container
```bash
docker run -p 8080:8080 \
  -e VALKEY_HOST=host.docker.internal \
  -e VALKEY_PORT=6379 \
  awslabs/valkey-mcp-server
```
