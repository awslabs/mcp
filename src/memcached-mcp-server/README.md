# Amazon ElastiCache Memcached MCP Server

MCP server for interacting with Amazon ElastiCache Memcached through a secure and reliable connection

## Features

### Complete Memcached Protocol Support

- Full support for all standard Memcached operations
- Secure communication with SSL/TLS encryption
- Automatic connection management and pooling
- Built-in retry mechanism for failed operations
- Readonly mode to prevent write operations

### Readonly Mode

The server can be started in readonly mode, which prevents any write operations from being performed. This is useful for scenarios where you want to ensure that no data is modified, such as:

- Read-only replicas
- Production environments where writes should be restricted
- Debugging and monitoring without risk of data modification

When readonly mode is enabled, any attempt to perform a write operation (set, add, replace, delete, etc.) will return an error message.

## Prerequisites

1. Install `uv` from [Astral](https://docs.astral.sh/uv/getting-started/installation/) or the [GitHub README](https://github.com/astral-sh/uv#installation)
2. Install Python using `uv python install 3.10`
3. Access to a Memcached server.
4. For instructions to connect to an Amazon ElastiCache Memcached cache [click here](https://github.com/awslabs/mcp/blob/main/src/memcached-mcp-server/ELASTICACHECONNECT.md)


## Installation

| Cursor | VS Code |
|:------:|:-------:|
| [![Install MCP Server](https://cursor.com/deeplink/mcp-install-light.svg)](https://cursor.com/en/install-mcp?name=awslabs.memcached-mcp-server&config=eyJjb21tYW5kIjoidXZ4IGF3c2xhYnMubWVtY2FjaGVkLW1jcC1zZXJ2ZXJAbGF0ZXN0IiwiZW52Ijp7IkZBU1RNQ1BfTE9HX0xFVkVMIjoiRVJST1IiLCJNRU1DQUNIRURfSE9TVCI6InlvdXItbWVtY2FjaGVkLWhvc3QiLCJNRU1DQUNIRURfUE9SVCI6IjExMjExIn0sImRpc2FibGVkIjpmYWxzZSwiYXV0b0FwcHJvdmUiOltdfQ%3D%3D) | [![Install on VS Code](https://img.shields.io/badge/Install_on-VS_Code-FF9900?style=flat-square&logo=visualstudiocode&logoColor=white)](https://insiders.vscode.dev/redirect/mcp/install?name=Memcached%20MCP%20Server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.memcached-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%2C%22MEMCACHED_HOST%22%3A%22your-memcached-host%22%2C%22MEMCACHED_PORT%22%3A%2211211%22%7D%2C%22disabled%22%3Afalse%2C%22autoApprove%22%3A%5B%5D%7D) |

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

To run in readonly mode:

```json
{
  "mcpServers": {
    "awslabs.memcached-mcp-server": {
      "command": "uvx",
      "args": ["awslabs.memcached-mcp-server@latest", "--readonly"],
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

### Windows Installation

For Windows users, the MCP server configuration format is slightly different:

```json
{
  "mcpServers": {
    "awslabs.memcached-mcp-server": {
      "disabled": false,
      "timeout": 60,
      "type": "stdio",
      "command": "uv",
      "args": [
        "tool",
        "run",
        "--from",
        "awslabs.memcached-mcp-server@latest",
        "awslabs.memcached-mcp-server.exe"
      ],
      "env": {
        "FASTMCP_LOG_LEVEL": "ERROR",
        "MEMCACHED_HOST": "your-memcached-host",
        "MEMCACHED_PORT": "11211"
      },
    }
  }
}
```

To run in readonly mode:

```json
{
  "mcpServers": {
    "awslabs.memcached-mcp-server": {
      "command": "uvx",
      "args": [
        "tool",
        "run",
        "--from",
        "awslabs.memcached-mcp-server@latest",
        "awslabs.memcached-mcp-server.exe",
        "--readonly"
      ],
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

To run in readonly mode with Docker:

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
        "awslabs/memcached-mcp-server:latest",
        "--readonly"
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
docker build -t awslabs/memcached-mcp-server .
```

### Running Docker Container
```bash
docker run -p 8080:8080 \
  -e MEMCACHED_HOST=host.docker.internal \
  -e MEMCACHED_PORT=11211 \
  awslabs/memcached-mcp-server
```

To run in readonly mode:
```bash
docker run -p 8080:8080 \
  -e MEMCACHED_HOST=host.docker.internal \
  -e MEMCACHED_PORT=11211 \
  awslabs/memcached-mcp-server --readonly
```
