# AWS Bedrock AgentCore MCP Server

Model Context Protocol (MCP) server for Amazon Bedrock AgentCore services

This MCP server provides comprehensive access to Amazon Bedrock AgentCore documentation, enabling developers to search and retrieve detailed information about AgentCore platform services, APIs, tutorials, and best practices.

## Features

- **Search Documentation**: Search through curated AgentCore documentation with ranked results and contextual snippets
- **Fetch Full Documents**: Retrieve complete documentation pages for in-depth understanding
- **Browser Automation**: 25 cloud-based browser tools for web navigation, interaction, and data extraction — no local browser installation required
- **Comprehensive Coverage**: Access documentation for all AgentCore services including Runtime, Memory, Code Interpreter, Browser, Gateway, Observability, and Identity
- **Smart Caching**: Efficient document caching with on-demand content loading for optimal performance
- **Registry Discovery**: Search, list, and inspect AWS Agent Registry records and registries
- **Curated Documentation List**: Uses llm.txt as a curated list of relevant AgentCore documentations, always fetching the latest version of the file

## Prerequisites

### Installation Requirements

1. Install `uv` from [Astral](https://docs.astral.sh/uv/getting-started/installation/) or the [GitHub README](https://github.com/astral-sh/uv#installation)
2. Install Python 3.10 or newer using `uv python install 3.10` (or a more recent version)

## Installation

| Kiro | Cursor | VS Code |
|:----:|:------:|:-------:|
| [![Add to Kiro](https://kiro.dev/images/add-to-kiro.svg)](https://kiro.dev/launch/mcp/add?name=bedrock-agentcore-mcp-server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.amazon-bedrock-agentcore-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%7D%7D) | [![Install MCP Server](https://cursor.com/deeplink/mcp-install-light.svg)](https://cursor.com/en/install-mcp?name=bedrock-agentcore-mcp-server&config=eyJjb21tYW5kIjoidXZ4IGF3c2xhYnMuYW1hem9uLWJlZHJvY2stYWdlbnRjb3JlLW1jcC1zZXJ2ZXJAbGF0ZXN0IiwiZW52Ijp7IkZBU1RNQ1BfTE9HX0xFVkVMIjoiRVJST1IifSwiZGlzYWJsZWQiOmZhbHNlLCJhdXRvQXBwcm92ZSI6WyJzZWFyY2hfYWdlbnRjb3JlX2RvY3MiLCJmZXRjaF9hZ2VudGNvcmVfZG9jIl19) | [![Install on VS Code](https://img.shields.io/badge/Install_on-VS_Code-FF9900?style=flat-square&logo=visualstudiocode&logoColor=white)](https://insiders.vscode.dev/redirect/mcp/install?name=Bedrock%20AgentCore%20MCP%20Server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.amazon-bedrock-agentcore-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%7D%2C%22disabled%22%3Afalse%2C%22autoApprove%22%3A%5B%22search_agentcore_docs%22%2C%22fetch_agentcore_doc%22%5D%7D) |

Configure the MCP server in your MCP client configuration:

For [Kiro](https://kiro.dev/), see the [Kiro IDE documentation](https://kiro.dev/docs/mcp/configuration/) or the [Kiro CLI documentation](https://kiro.dev/docs/cli/mcp/configuration/) for details.

For global configuration, edit `~/.kiro/settings/mcp.json`. For project-specific configuration, edit `.kiro/settings/mcp.json` in your project directory.

Example configuration for Kiro (`~/.kiro/settings/mcp.json`):

```json
{
  "mcpServers": {
    "bedrock-agentcore-mcp-server": {
      "command": "uvx",
      "args": ["awslabs.amazon-bedrock-agentcore-mcp-server@latest"],
      "env": {
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
    "bedrock-agentcore-mcp-server": {
      "disabled": false,
      "timeout": 60,
      "type": "stdio",
      "command": "uv",
      "args": [
        "tool",
        "run",
        "--from",
        "awslabs.amazon-bedrock-agentcore-mcp-server@latest",
        "awslabs.amazon-bedrock-agentcore-mcp-server.exe"
      ],
      "env": {
        "FASTMCP_LOG_LEVEL": "ERROR"
      }
    }
  }
}
```

Or using Docker after a successful `docker build -t mcp/amazon-bedrock-agentcore .`:

```json
{
  "mcpServers": {
    "bedrock-agentcore-mcp-server": {
      "command": "docker",
      "args": [
        "run",
        "--rm",
        "--interactive",
        "--env",
        "FASTMCP_LOG_LEVEL=ERROR",
        "mcp/amazon-bedrock-agentcore:latest"
      ],
      "env": {},
      "disabled": false,
      "autoApprove": []
    }
  }
}
```

## Basic Usage

The server provides access to comprehensive Amazon Bedrock AgentCore documentation covering:

**Platform Services:**
- AgentCore Runtime (serverless deployment and scaling)
- AgentCore Memory (persistent knowledge with event and semantic memory)
- AgentCore Code Interpreter (secure code execution in isolated sandboxes)
- AgentCore Browser (fast, secure cloud-based browser for web interaction)
- AgentCore Gateway (transform existing APIs into agent tools)
- AgentCore Observability (real-time monitoring and tracing)
- AgentCore Identity (secure authentication and access management)

**Development Resources:**
- Getting started guides and prerequisites
- Building your first agent or transforming existing code
- Local development and testing workflows
- Deployment to AgentCore using CLI
- API reference documentation
- Examples and tutorials for various use cases

Example queries:
- "How do I set up AgentCore Memory for my agent?"
- "Show me examples of using the Code Interpreter service"
- "What are the deployment options for AgentCore Runtime?"
- "How do I integrate AgentCore Browser with my application?"
- "Start a browser session and navigate to docs.aws.amazon.com"
- "Take a screenshot of the current page and extract all links"

## Browser Tools

The server includes 25 browser automation tools powered by Amazon Bedrock AgentCore. Each session runs in an isolated Firecracker microVM — no local browser installation is needed.

### Quick Start

```python
# 1. Start a session
start_browser_session(timeout_seconds=300)

# 2. Navigate and interact
browser_navigate(session_id="...", url="https://example.com")
browser_snapshot(session_id="...")       # accessibility tree with element refs
browser_click(session_id="...", ref="e3")
browser_type(session_id="...", ref="e5", text="search query")

# 3. Clean up
stop_browser_session(session_id="...")
```

### Tool Categories

| Category | Tools | Description |
|----------|-------|-------------|
| **Session** (4) | `start_browser_session`, `get_browser_session`, `list_browser_sessions`, `stop_browser_session` | Create, inspect, list, and terminate sessions |
| **Navigation** (3) | `browser_navigate`, `browser_navigate_back`, `browser_navigate_forward` | URL navigation and history |
| **Observation** (6) | `browser_snapshot`, `browser_take_screenshot`, `browser_evaluate`, `browser_wait_for`, `browser_console_messages`, `browser_network_requests` | Page state, screenshots, JS execution, network |
| **Interaction** (9) | `browser_click`, `browser_type`, `browser_fill_form`, `browser_select_option`, `browser_hover`, `browser_press_key`, `browser_upload_file`, `browser_handle_dialog`, `browser_mouse_wheel` | Click, type, forms, keyboard, dialogs |
| **Management** (3) | `browser_tabs`, `browser_resize`, `browser_close` | Tab management, viewport, page lifecycle |

### Tips

- **Use DuckDuckGo or Bing** instead of Google — Google blocks cloud browser IPs with CAPTCHAs.
- **Prefer `browser_evaluate` for data extraction** — snapshots show page structure; `browser_evaluate` with `querySelectorAll` extracts actual data efficiently.
- **Use `browser_evaluate` for long text** — `browser_type` types character-by-character. For long inputs, use `document.querySelector("selector").value = "text"` instead.
- **Idle timeout, not absolute** — `timeout_seconds` on `start_browser_session` resets on each tool call, not wall-clock duration.

## Tools

### search_agentcore_docs

Search curated AgentCore documentation and return ranked results with snippets.

```python
search_agentcore_docs(query: str, k: int = 5) -> List[Dict[str, Any]]
```

**Parameters:**
- `query`: Search query string (e.g., "bedrock agentcore", "memory integration", "deployment guide")
- `k`: Maximum number of results to return (default: 5)

**Returns:**
List of dictionaries containing:
- `url`: Document URL
- `title`: Display title
- `score`: Relevance score (0-1, higher is better)
- `snippet`: Contextual content preview

### fetch_agentcore_doc

Fetch full document content by URL.

```python
fetch_agentcore_doc(uri: str) -> Dict[str, Any]
```

**Parameters:**
- `uri`: Document URI (supports http/https URLs)

**Returns:**
Dictionary containing:
- `url`: Canonical document URL
- `title`: Document title
- `content`: Full document text content
- `error`: Error message (if fetch failed)

Use this tool to get complete documentation pages when search snippets aren't sufficient for understanding or implementing AgentCore features.

### manage_agentcore_runtime

Provides comprehensive information on deploying and managing agents in AgentCore Runtime.

```python
manage_agentcore_runtime() -> Dict[str, Any]
```

**Returns:**
Detailed deployment guide covering:
- Code requirements and validation checklist
- Step-by-step CLI deployment workflow (configure, launch, invoke, status, destroy)
- Required code patterns with BedrockAgentCoreApp
- Common issues and troubleshooting
- Session management and cleanup procedures

Use this tool when you need to deploy agents to AgentCore Runtime or troubleshoot deployment issues.

### manage_agentcore_memory

Provides comprehensive information on managing AgentCore Memory resources.

```python
manage_agentcore_memory() -> Dict[str, Any]
```

**Returns:**
Complete memory management guide covering:
- Memory resource creation and configuration
- Short-term memory (STM) and long-term memory (LTM) concepts
- Semantic memory strategies for facts and knowledge
- Full CLI command reference (create, get, list, delete, status)
- Common workflows and examples

Use this tool when working with AgentCore Memory for persistent knowledge storage.

### manage_agentcore_gateway

Provides comprehensive information on deploying and managing MCP Gateways in AgentCore.

```python
manage_agentcore_gateway() -> Dict[str, Any]
```

**Returns:**
Complete gateway deployment guide covering:
- Gateway creation and configuration requirements
- Step-by-step CLI deployment workflow
- Target management for Lambda, OpenAPI, and Smithy models
- Authentication and authorization setup (Cognito, OAuth2, API keys)
- Management commands (list, get, delete)
- Common patterns and troubleshooting

Use this tool when deploying MCP Gateways to provide managed endpoints for Model Context Protocol servers.

### search_registry

Search AWS Agent Registry for MCP tools, A2A agents, or custom resources using natural language.

```python
search_registry(query: str, registry_arn: str, max_results: int = 5) -> str
```

**Parameters:**
- `query` (str, required): Natural language search query describing what you need
- `registry_arn` (str, required): Registry ARN to search within
- `max_results` (int, optional, default: 5): Maximum number of results to return

**Returns:**
JSON string of matching records with name, description, type, status, and relevance score. MCP descriptor records include endpoint, transport type, and tool names.

### list_records

List all records in a specific Agent Registry.

```python
list_records(registry_id: str) -> str
```

**Parameters:**
- `registry_id` (str, required): Registry ID to list records from

**Returns:**
JSON array of records with name, record ID, descriptor type, and status.

### get_record

Get full details of a specific registry record including descriptors.

```python
get_record(registry_id: str, record_id: str) -> str
```

**Parameters:**
- `registry_id` (str, required): Registry ID
- `record_id` (str, required): Record ID

**Returns:**
Full record details as JSON with parsed inline descriptor content.

### list_registries

List all Agent Registries in the AWS account.

```python
list_registries() -> str
```

**Parameters:** None

**Returns:**
JSON array of registries with name, registry ID, status, and auto-approval configuration.

## Environment Variables

### `AGENTCORE_ENABLE_TOOLS`

Comma-separated list of service names to enable. When set, only the listed services are registered. If not set, all services are enabled by default.

### `AGENTCORE_DISABLE_TOOLS`

Comma-separated list of service names to disable. When set, the listed services are excluded from registration. If both `AGENTCORE_ENABLE_TOOLS` and `AGENTCORE_DISABLE_TOOLS` are set, `AGENTCORE_ENABLE_TOOLS` takes precedence.

**Valid service names:** `runtime`, `memory`, `gateway`, `registry`, `browser`, `code_interpreter`

> **Note:** Documentation tools (`search_agentcore_docs`, `fetch_agentcore_doc`) are always registered and cannot be disabled.
