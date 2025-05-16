# Memcached MCP Server

MCP server for interacting with Amazon ElastiCache Memcached through a secure and reliable connection

## Features

### Complete Memcached Protocol Support

- Full support for all standard Memcached operations
- Secure communication with SSL/TLS encryption
- Automatic connection management and pooling
- Built-in retry mechanism for failed operations

### Robust Connection Management

- Configurable connection settings and timeouts
- Automatic connection retrying with customizable parameters
- Connection pooling for improved performance
- Comprehensive error handling and recovery

### Security and Reliability

- SSL/TLS support for encrypted communication
- Certificate-based authentication
- Configurable verification settings
- Automatic handling of connection failures

## Prerequisites

1. Install `uv` from [Astral](https://docs.astral.sh/uv/getting-started/installation/) or the [GitHub README](https://github.com/astral-sh/uv#installation)
2. Install Python using `uv python install 3.10`
3. Access to a Memcached server (local or Amazon ElastiCache)
   - For Amazon ElastiCache, you need appropriate AWS credentials and permissions
   - For local development, ensure Memcached is installed and running

## Installation

Here are some ways you can work with MCP (e.g. for Amazon Q Developer CLI MCP, `~/.aws/amazonq/mcp.json`):

```json
{
  "mcpServers": {
    "awslabs.memcached-mcp-server": {
      "command": "uvx",
      "args": ["awslabs.memcached-mcp-server@latest"],
      "env": {
        "FASTMCP_LOG_LEVEL": "ERROR",
        "MEMCACHED_HOST": "your-memcached-host",
        "MEMCACHED_PORT": "11211"
      },
      "disabled": false,
      "autoApprove": []
    }
  }
}
```

or docker after a successful `docker build -t awslabs/memcached-mcp-server .`:

```json
{
  "mcpServers": {
    "awslabs.memcached-mcp-server": {
      "command": "docker",
      "args": [
        "run",
        "--rm",
        "--interactive",
        "--env",
        "FASTMCP_LOG_LEVEL=ERROR",
        "--env",
        "MEMCACHED_HOST=your-memcached-host",
        "--env",
        "MEMCACHED_PORT=11211",
        "awslabs/memcached-mcp-server:latest"
      ],
      "env": {},
      "disabled": false,
      "autoApprove": []
    }
  }
}
```

## Configuration

### Basic Connection Settings

Configure the connection using these environment variables:

```bash
# Basic settings
MEMCACHED_HOST=127.0.0.1          # Memcached server hostname
MEMCACHED_PORT=11211              # Memcached server port
MEMCACHED_TIMEOUT=1              # Operation timeout in seconds
MEMCACHED_CONNECT_TIMEOUT=5      # Connection timeout in seconds
MEMCACHED_RETRY_TIMEOUT=1        # Retry delay in seconds
MEMCACHED_MAX_RETRIES=3         # Maximum number of retry attempts
```

### SSL/TLS Configuration

Enable and configure SSL/TLS support with these variables:

```bash
# SSL/TLS settings
MEMCACHED_USE_TLS=true                           # Enable SSL/TLS
MEMCACHED_TLS_CERT_PATH=/path/to/client-cert.pem # Client certificate
MEMCACHED_TLS_KEY_PATH=/path/to/client-key.pem   # Client private key
MEMCACHED_TLS_CA_CERT_PATH=/path/to/ca-cert.pem  # CA certificate
MEMCACHED_TLS_VERIFY=true                        # Enable cert verification
```

The server automatically handles:
- Connection establishment and management
- SSL/TLS encryption when enabled
- Automatic retrying of failed operations
- Timeout enforcement and error handling
