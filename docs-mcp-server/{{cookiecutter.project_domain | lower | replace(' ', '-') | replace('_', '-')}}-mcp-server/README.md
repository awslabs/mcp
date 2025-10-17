# {{cookiecutter.project_domain}} MCP Server

Model Context Protocol (MCP) server for {{cookiecutter.project_domain}} documentation

This MCP server provides comprehensive access to {{cookiecutter.project_domain}} documentation, enabling developers to search and retrieve detailed information about {{cookiecutter.project_domain}} services, APIs, tutorials, and best practices.

## Features

- **Search Documentation**: Search through curated {{cookiecutter.project_domain}} documentation with ranked results and contextual snippets
- **Fetch Full Documents**: Retrieve complete documentation pages for in-depth understanding
- **Comprehensive Coverage**: Access documentation for all {{cookiecutter.project_domain}} services and features
- **Smart Caching**: Efficient document caching with on-demand content loading for optimal performance
- **Curated Documentation List**: Uses llms.txt as a curated list of relevant {{cookiecutter.project_domain}} documentations, always fetching the latest version of the file

## Prerequisites

### Installation Requirements

1. Install `uv` from [Astral](https://docs.astral.sh/uv/getting-started/installation/) or the [GitHub README](https://github.com/astral-sh/uv#installation)
2. Install Python 3.10 or newer using `uv python install 3.10` (or a more recent version)

## Installation

| Cursor | VS Code |
|:------:|:-------:|
| [![Install MCP Server](https://cursor.com/deeplink/mcp-install-light.svg)](<Cursor Installation Link>) | [![Install on VS Code](https://img.shields.io/badge/Install_on-VS_Code-FF9900?style=flat-square&logo=visualstudiocode&logoColor=white)](<VS Code Installation Link>) |

Configure the MCP server in your MCP client configuration:

For [Kiro](https://kiro.dev/), add at the project level `.kiro/settings/mcp.json`

```json
{
  "mcpServers": {
    "awslabs.{{cookiecutter.project_domain | lower | replace(' ', '-') | replace('_', '-')}}-mcp-server": {
      "command": "uvx",
      "args": ["awslabs.{{cookiecutter.project_domain | lower | replace(' ', '-') | replace('_', '-')}}-mcp-server@latest"],
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
    "awslabs.{{cookiecutter.project_domain | lower | replace(' ', '-') | replace('_', '-')}}-mcp-server": {
      "command": "uvx",
      "args": ["awslabs.{{cookiecutter.project_domain | lower | replace(' ', '-') | replace('_', '-')}}-mcp-server@latest"],
      "env": {
        "FASTMCP_LOG_LEVEL": "ERROR"
      },
      "disabled": false,
      "autoApprove": []
    }
  },
  "tools": [
    // .. other existing tools
    "@awslabs.{{cookiecutter.project_domain | lower | replace(' ', '-') | replace('_', '-')}}-mcp-server"
  ]
}
```

### Windows Installation

For Windows users, the MCP server configuration format is slightly different:

```json
{
  "mcpServers": {
    "awslabs.{{cookiecutter.project_domain | lower | replace(' ', '-') | replace('_', '-')}}-mcp-server": {
      "disabled": false,
      "timeout": 60,
      "type": "stdio",
      "command": "uv",
      "args": [
        "tool",
        "run",
        "--from",
        "awslabs.{{cookiecutter.project_domain | lower | replace(' ', '-') | replace('_', '-')}}-mcp-server@latest",
        "awslabs.{{cookiecutter.project_domain | lower | replace(' ', '-') | replace('_', '-')}}-mcp-server.exe"
      ],
      "env": {
        "FASTMCP_LOG_LEVEL": "ERROR"
      }
    }
  }
}
```

Or using Docker after a successful `docker build -t mcp/{{cookiecutter.project_domain | lower | replace(' ', '-') | replace('_', '-')}} .`:

```json
{
  "mcpServers": {
    "awslabs.{{cookiecutter.project_domain | lower | replace(' ', '-') | replace('_', '-')}}-mcp-server": {
      "command": "docker",
      "args": [
        "run",
        "--rm",
        "--interactive",
        "--env",
        "FASTMCP_LOG_LEVEL=ERROR",
        "mcp/{{cookiecutter.project_domain | lower | replace(' ', '-') | replace('_', '-')}}:latest"
      ],
      "env": {},
      "disabled": false,
      "autoApprove": []
    }
  }
}
```

## Basic Usage

The server provides access to comprehensive {{cookiecutter.project_domain}} documentation covering:

**Core Services:**
- Service documentation and API references
- Getting started guides and tutorials
- Best practices and examples
- Integration guides and troubleshooting

**Development Resources:**
- Prerequisites & environment setup
- Building your first application
- Local development & testing
- Deployment and configuration
- API reference documentation

**Examples & Tutorials:**
- Basic usage examples
- Advanced integration patterns
- Error handling and debugging
- Performance optimization

Example queries:
- "How do I get started with {{cookiecutter.project_domain}}?"
- "Show me examples of using {{cookiecutter.project_domain}} APIs"
- "What are the best practices for {{cookiecutter.project_domain}}?"
- "How do I integrate {{cookiecutter.project_domain}} with my application?"

## Tools

### {{cookiecutter.search_tool_name}}

Search curated {{cookiecutter.project_domain}} documentation and return ranked results with snippets.

```python
{{cookiecutter.search_tool_name}}(query: str, k: int = 5) -> List[Dict[str, Any]]
```

**Parameters:**
- `query`: Search query string (e.g., "{{cookiecutter.project_domain | lower}}", "getting started", "api reference")
- `k`: Maximum number of results to return (default: 5)

**Returns:**
List of dictionaries containing:
- `url`: Document URL
- `title`: Display title
- `score`: Relevance score (0-1, higher is better)
- `snippet`: Contextual content preview

### {{cookiecutter.fetch_tool_name}}

Fetch full document content by URL.

```python
{{cookiecutter.fetch_tool_name}}(uri: str) -> Dict[str, Any]
```

**Parameters:**
- `uri`: Document URI (supports http/https URLs)

**Returns:**
Dictionary containing:
- `url`: Canonical document URL
- `title`: Document title
- `content`: Full document text content
- `error`: Error message (if fetch failed)

Use this tool to get complete documentation pages when search snippets aren't sufficient for understanding or implementing {{cookiecutter.project_domain}} features.

## Configuration

The MCP server can be configured by modifying the `config.py` file or by setting environment variables:

- `LLM_TEXTS_URL`: Comma-separated list of llms.txt URLs to index

## Development

### Setup

1. Clone the repository
2. Install dependencies: `uv sync`
3. Run tests: `uv run pytest`
4. Run the server: `uv run python -m awslabs.{{cookiecutter.project_domain | lower | replace(' ', '-') | replace('_', '-') | replace('-', '_')}}_mcp_server.server`

### Adding New Documentation Sources

To add new documentation sources, update the `llm_texts_url` list in `config.py` with the URLs of llms.txt files that contain your documentation links.

## License

Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

Licensed under the Apache License, Version 2.0 (the "License").
