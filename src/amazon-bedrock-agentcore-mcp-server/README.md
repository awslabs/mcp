# AWS Bedrock AgentCore MCP Server

Model Context Protocol (MCP) server for Amazon Bedrock AgentCore services

This MCP server provides comprehensive access to Amazon Bedrock AgentCore documentation, enabling developers to search and retrieve detailed information about AgentCore platform services, APIs, tutorials, and best practices.

## Features

- **Search Documentation**: Search through curated AgentCore documentation with ranked results and contextual snippets
- **Fetch Full Documents**: Retrieve complete documentation pages for in-depth understanding
- **Comprehensive Coverage**: Access documentation for all AgentCore services including Runtime, Memory, Code Interpreter, Browser, Gateway, Observability, and Identity
- **Smart Caching**: Efficient document caching with on-demand content loading for optimal performance
- **Curated Documentation List**: Uses llm.txt as a curated list of relevant AgentCore documentations, always fetching the latest version of the file

## Prerequisites

### Installation Requirements

1. Install `uv` from [Astral](https://docs.astral.sh/uv/getting-started/installation/) or the [GitHub README](https://github.com/astral-sh/uv#installation)
2. Install Python 3.10 or newer using `uv python install 3.10` (or a more recent version)

## Installation

| Cursor | VS Code |
|:------:|:-------:|
| [![Install MCP Server](https://cursor.com/deeplink/mcp-install-light.svg)](https://cursor.com/en/install-mcp?name=bedrock-agentcore-mcp-server&config=eyJjb21tYW5kIjoidXZ4IGF3c2xhYnMuYW1hem9uLWJlZHJvY2stYWdlbnRjb3JlLW1jcC1zZXJ2ZXJAbGF0ZXN0IiwiZW52Ijp7IkZBU1RNQ1BfTE9HX0xFVkVMIjoiRVJST1IifSwiZGlzYWJsZWQiOmZhbHNlLCJhdXRvQXBwcm92ZSI6WyJzZWFyY2hfYWdlbnRjb3JlX2RvY3MiLCJmZXRjaF9hZ2VudGNvcmVfZG9jIl19) | [![Install on VS Code](https://img.shields.io/badge/Install_on-VS_Code-FF9900?style=flat-square&logo=visualstudiocode&logoColor=white)](https://insiders.vscode.dev/redirect/mcp/install?name=Bedrock%20AgentCore%20MCP%20Server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.amazon-bedrock-agentcore-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%7D%2C%22disabled%22%3Afalse%2C%22autoApprove%22%3A%5B%22search_agentcore_docs%22%2C%22fetch_agentcore_doc%22%5D%7D) |

Configure the MCP server in your MCP client configuration:

For [Kiro](https://kiro.dev/), add at the project level `.kiro/settings/mcp.json`

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

For [Amazon Q Developer CLI](https://docs.aws.amazon.com/amazonq/latest/qdeveloper-ug/command-line.html), add the MCP client configuration and tool command to the agent file in `~/.aws/amazonq/cli-agents`.

Example, `~/.aws/amazonq/cli-agents/default.json`

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
  },
  "tools": [
    // .. other existing tools
    "@awslabs.amazon-bedrock-agentcore-mcp-server"
  ]
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
