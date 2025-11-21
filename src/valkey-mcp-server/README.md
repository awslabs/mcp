# Amazon ElastiCache/MemoryDB Valkey MCP Server

An AWS Labs Model Context Protocol (MCP) server for Amazon ElastiCache [Valkey](https://valkey.io/) datastores.

## Features

This MCP server provides 9 purpose-built tools for AI agents working with Valkey Search and JSON data. The tool surface is designed to minimize token costs and agent error rates by accepting structured JSON input and handling command translation internally.

### Valkey AI Search — 4 tools

| Tool | What It Does |
|------|-------------|
| `manage_index` | Create, drop, inspect, or list search indices. Accepts structured schema definitions with TEXT, NUMERIC, TAG, and VECTOR fields. Defaults to COSINE distance + HNSW algorithm. |
| `add_documents` | Ingest documents with optional embedding generation. Supports Bedrock, OpenAI, and Ollama providers. Auto-creates the index if missing. |
| `search` | Unified semantic, text, hybrid, and find-similar search. Auto-detects mode from parameters, or accepts an explicit `mode` override. |
| `aggregate` | Structured pipeline builder for FT.AGGREGATE. Supports GROUPBY, SORTBY, APPLY, FILTER, and LIMIT stages with 12 REDUCE functions. |

### Valkey JSON Intelligence — 5 tools

| Tool | What It Does |
|------|-------------|
| `json_get` | Get a JSON value at a path from a Valkey key. |
| `json_set` | Set a JSON value at a path with optional TTL. |
| `json_arrappend` | Append values to a JSON array at a path. |
| `json_arrpop` | Pop an element from a JSON array at a path. |
| `json_arrtrim` | Trim a JSON array to a specified range. |

### Additional Features

- **Valkey-GLIDE**: Built on [Valkey GLIDE](https://github.com/valkey-io/valkey-glide) for async-native performance.
- **Cluster Support**: Standalone and clustered Valkey deployments.
- **SSL/TLS Security**: Secure connections via TLS with CA certificate verification.
- **Readonly Mode**: Prevent write operations with `--readonly`.
- **Multi-provider Embeddings**: Bedrock, OpenAI, Ollama, with automatic fallback.
- **Health Check**: `GET /health` endpoint for ALB target group health checks.

## Prerequisites

1. Install `uv` from [Astral](https://docs.astral.sh/uv/getting-started/installation/)
2. Install Python using `uv python install 3.10`
3. Access to a Valkey datastore:
   - **AI Search tools** require the [Valkey Search module](https://valkey.io/commands/?group=search)
   - **JSON tools** require the [Valkey JSON module](https://valkey.io/commands/?group=json)
   - The `valkey/valkey-bundle` Docker image includes both modules
4. **Embedding provider credentials** (only needed for semantic search with `add_documents` and `search`):
   - **Bedrock** (default): Requires AWS credentials — `AWS_ACCESS_KEY_ID`/`AWS_SECRET_ACCESS_KEY`, `AWS_PROFILE`, or an IAM role. Without credentials, semantic search will fail with a `NoCredentialsError`.
   - **OpenAI**: Requires `OPENAI_API_KEY`
   - **Ollama**: Requires a running Ollama instance (no credentials needed)
5. For Amazon ElastiCache/MemoryDB connection instructions, see [ELASTICACHECONNECT.md](ELASTICACHECONNECT.md).

## Quickstart

Start a local Valkey instance with Search and JSON modules:

```bash
docker run -d --name valkey -p 6379:6379 valkey/valkey-bundle:latest
```

Verify it's running:

```bash
docker exec valkey valkey-cli PING
# Should return: PONG
```

Run the MCP server (using Ollama for embeddings — no AWS credentials needed):

```bash
uvx awslabs.valkey-mcp-server@latest
```

Or with Ollama embeddings for semantic search:

```bash
EMBEDDING_PROVIDER=ollama uvx awslabs.valkey-mcp-server@latest
```

Try these example queries in your AI IDE:

```
"Create a search index called products with title (TEXT), category (TAG), and price (NUMERIC) fields"
"Add 3 product documents to the products index"
"Search for electronics in the products index"
"Show me the average price by category"
```

## Installation

| Kiro | Cursor | VS Code |
|:----:|:------:|:-------:|
| [![Add to Kiro](https://kiro.dev/images/add-to-kiro.svg)](https://kiro.dev/launch/mcp/add?name=awslabs.valkey-mcp-server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.valkey-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22VALKEY_HOST%22%3A%22127.0.0.1%22%2C%22VALKEY_PORT%22%3A%226379%22%2C%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%7D%7D) | [![Install MCP Server](https://cursor.com/deeplink/mcp-install-light.svg)](https://cursor.com/en/install-mcp?name=awslabs.valkey-mcp-server&config=eyJjb21tYW5kIjoidXZ4IGF3c2xhYnMudmFsa2V5LW1jcC1zZXJ2ZXJAbGF0ZXN0IiwiZW52Ijp7IlZBTEtFWV9IT1NUIjoiMTI3LjAuMC4xIiwiVkFMS0VZX1BPUlQiOiI2Mzc5IiwiRkFTVE1DUF9MT0dfTEVWRUwiOiJFUlJPUiJ9LCJhdXRvQXBwcm92ZSI6W10sImRpc2FibGVkIjpmYWxzZX0%3D) | [![Install on VS Code](https://img.shields.io/badge/Install_on-VS_Code-FF9900?style=flat-square&logo=visualstudiocode&logoColor=white)](https://insiders.vscode.dev/redirect/mcp/install?name=Valkey%20MCP%20Server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.valkey-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22VALKEY_HOST%22%3A%22127.0.0.1%22%2C%22VALKEY_PORT%22%3A%226379%22%2C%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%7D%2C%22autoApprove%22%3A%5B%5D%2C%22disabled%22%3Afalse%7D) |

### MCP Configuration

Add the following to your MCP settings file (e.g., `~/.kiro/settings/mcp.json` for Kiro, `.cursor/mcp.json` for Cursor, or `.vscode/mcp.json` for VS Code):

```json
{
  "mcpServers": {
    "awslabs.valkey-mcp-server": {
      "command": "uvx",
      "args": ["awslabs.valkey-mcp-server@latest"],
      "env": {
        "VALKEY_HOST": "127.0.0.1",
        "VALKEY_PORT": "6379",
        "FASTMCP_LOG_LEVEL": "ERROR"
      }
    }
  }
}
```

> **Tip:** Use `FASTMCP_LOG_LEVEL=INFO` or `DEBUG` during initial setup to see connection and tool registration output. Switch to `ERROR` for production use.

The default embedding provider is Bedrock, which requires AWS credentials. To use Ollama instead (no credentials needed), add:

```json
        "EMBEDDING_PROVIDER": "ollama",
        "OLLAMA_HOST": "http://localhost:11434"
```

Readonly mode (disables all write operations — embedding config is only needed if you use semantic search):

```json
{
  "mcpServers": {
    "awslabs.valkey-mcp-server": {
      "command": "uvx",
      "args": ["awslabs.valkey-mcp-server@latest", "--readonly"],
      "env": {
        "VALKEY_HOST": "127.0.0.1",
        "VALKEY_PORT": "6379",
        "FASTMCP_LOG_LEVEL": "ERROR"
      }
    }
  }
}
```

### Windows Installation

```json
{
  "mcpServers": {
    "awslabs.valkey-mcp-server": {
      "command": "uv",
      "args": [
        "tool", "run", "--from",
        "awslabs.valkey-mcp-server@latest",
        "awslabs.valkey-mcp-server.exe"
      ],
      "env": {
        "VALKEY_HOST": "127.0.0.1",
        "VALKEY_PORT": "6379",
        "FASTMCP_LOG_LEVEL": "ERROR"
      }
    }
  }
}
```

### Docker

Build the image first:

```bash
docker build -t awslabs/valkey-mcp-server .
```

MCP configuration (use `host.docker.internal` to reach Valkey on the host; on Linux, use `--network host` instead):

```json
{
  "mcpServers": {
    "awslabs.valkey-mcp-server": {
      "command": "docker",
      "args": [
        "run", "--rm", "--interactive",
        "--env", "FASTMCP_LOG_LEVEL=ERROR",
        "--env", "VALKEY_HOST=host.docker.internal",
        "--env", "VALKEY_PORT=6379",
        "awslabs/valkey-mcp-server:latest"
      ]
    }
  }
}
```

Readonly mode with Docker:

```json
{
  "mcpServers": {
    "awslabs.valkey-mcp-server": {
      "command": "docker",
      "args": [
        "run", "--rm", "--interactive",
        "--env", "FASTMCP_LOG_LEVEL=ERROR",
        "--env", "VALKEY_HOST=host.docker.internal",
        "--env", "VALKEY_PORT=6379",
        "awslabs/valkey-mcp-server:latest",
        "--readonly"
      ]
    }
  }
}
```

Running the Docker container directly:

```bash
docker run -p 8080:8080 \
  -e VALKEY_HOST=host.docker.internal \
  -e VALKEY_PORT=6379 \
  awslabs/valkey-mcp-server
```

## Configuration

### Server

| Variable | Description | Default |
|----------|-------------|---------|
| `MCP_TRANSPORT` | Transport protocol (`stdio`, `sse`) | `stdio` |

### Valkey Connection

| Variable | Description | Default |
|----------|-------------|---------|
| `VALKEY_HOST` | Valkey hostname or IP | `127.0.0.1` |
| `VALKEY_PORT` | Valkey port | `6379` |
| `VALKEY_USERNAME` | Username for authentication | `None` |
| `VALKEY_PWD` | Password for authentication (note: not `VALKEY_PASSWORD`) | `""` |
| `VALKEY_USE_SSL` | Enable TLS | `false` |
| `VALKEY_SSL_CA_CERTS` | Path to CA certificate (PEM) for TLS verification | `None` |
| `VALKEY_CLUSTER_MODE` | Enable cluster mode | `false` |

### Embeddings Provider

Embedding generation is used by `add_documents` (to generate vectors) and `search` (for semantic/hybrid modes). If you only use text search, JSON tools, or `manage_index`, no embedding provider is needed.

| Variable | Description | Default |
|----------|-------------|---------|
| `EMBEDDING_PROVIDER` | Provider: `bedrock`, `openai`, `ollama`, or `hash` | `bedrock` |

> **Note:** The default provider is Bedrock, which requires AWS credentials. If you don't have AWS credentials configured, set `EMBEDDING_PROVIDER=ollama` and run a local Ollama instance, or set `EMBEDDING_PROVIDER=hash` for testing (deterministic, low-quality embeddings).

#### Bedrock

Credentials via `AWS_ACCESS_KEY_ID`/`AWS_SECRET_ACCESS_KEY`, `AWS_PROFILE`, or IAM role.

| Variable | Description | Default |
|----------|-------------|---------|
| `AWS_REGION` | AWS region | `us-east-1` |
| `BEDROCK_MODEL_ID` | Model ID | `amazon.nova-2-multimodal-embeddings-v1:0` |
| `BEDROCK_NORMALIZE` | Normalize embeddings | `None` |
| `BEDROCK_DIMENSIONS` | Embedding dimensions | `None` (model default) |
| `BEDROCK_INPUT_TYPE` | Input type | `None` |
| `BEDROCK_MAX_ATTEMPTS` | Max retry attempts | `3` |
| `BEDROCK_MAX_POOL_CONNECTIONS` | Connection pool size | `50` |
| `BEDROCK_RETRY_MODE` | Retry mode | `adaptive` |

#### OpenAI

| Variable | Description | Default |
|----------|-------------|---------|
| `OPENAI_API_KEY` | API key (required) | `None` |
| `OPENAI_MODEL` | Model name | `text-embedding-3-small` |

#### Ollama

| Variable | Description | Default |
|----------|-------------|---------|
| `OLLAMA_HOST` | Ollama endpoint URL (protocol required, e.g., `http://localhost:11434`) | `http://localhost:11434` |
| `OLLAMA_EMBEDDING_MODEL` | Model name | `nomic-embed-text` |

## Example Usage

```
"Create a search index for product data with title, category, price, and embedding fields"
"Add these product documents and generate embeddings from the title field"
"Search for products similar to 'wireless headphones'"
"Find products similar to product:123"
"Show me the average price by category"
"Store this JSON config and set a 1-hour TTL"
"Get the nested value at $.settings.theme from the config key"
```

## Troubleshooting

| Problem | Cause | Fix |
|---------|-------|-----|
| `Connection refused` or `timed out` | Valkey not running or wrong host/port | Verify `VALKEY_HOST` and `VALKEY_PORT`. Test with `valkey-cli -h <host> -p <port> PING`. |
| `NoCredentialsError` on semantic search | Bedrock is the default provider but no AWS credentials configured | Set `EMBEDDING_PROVIDER=ollama` or configure AWS credentials. |
| `Unknown command 'FT.CREATE'` | Valkey Search module not loaded | Use `valkey/valkey-bundle` Docker image or load the search module. |
| `Unknown command 'JSON.GET'` | Valkey JSON module not loaded | Use `valkey/valkey-bundle` Docker image or load the JSON module. |
| Docker: `Connection refused` to `127.0.0.1` | Container loopback is not the host | Use `VALKEY_HOST=host.docker.internal` (macOS/Windows) or `--network host` (Linux). |
| `Request URL is missing 'http://'` | `OLLAMA_HOST` set without protocol | Include the protocol: `http://localhost:11434`, not just `localhost:11434`. |
| No output from server | `FASTMCP_LOG_LEVEL=ERROR` suppresses info | Set `FASTMCP_LOG_LEVEL=INFO` or `DEBUG` for troubleshooting. |

## Development

### Running Tests

```bash
uv venv && source .venv/bin/activate && uv sync

# Unit tests
uv run --frozen pytest tests/ -m "not live and not integration"

# Live integration tests (requires VALKEY_HOST and EMBEDDING_PROVIDER)
uv run --frozen pytest tests/test_search_live.py -m live -v

# Type checking
uv run --frozen pyright
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

Readonly mode:

```bash
docker run -p 8080:8080 \
  -e VALKEY_HOST=host.docker.internal \
  -e VALKEY_PORT=6379 \
  awslabs/valkey-mcp-server --readonly
```
