# AWS China Documentation MCP Server

Model Context Protocol (MCP) server for AWS China Documentation

This server provides tools to access public AWS China documentation, and get service differences between AWS China and global regions.

## Features

- **Get Available Services**: Fetch available services from AWS China documentation
- **Read Documentation**: Fetch and convert AWS China documentation pages to markdown format

## Prerequisites

### Installation Requirements

1. Install `uv` from [Astral](https://docs.astral.sh/uv/getting-started/installation/) or the [GitHub README](https://github.com/astral-sh/uv#installation)
2. Install Python 3.10 or newer using `uv python install 3.10` (or a more recent version)

## Installation

Here are some ways you can work with MCP across AWS China, and we'll be adding support to more products including Amazon Q Developer CLI soon: (e.g. for Amazon Q Developer CLI MCP, ~/.aws/amazonq/mcp.json):

```json
{
  "mcpServers": {
    "awslabs.aws-cn-documentation-mcp-server": {
      "command": "uvx",
      "args": ["awslabs.aws-cn-documentation-mcp-server@latest"],
      "env": {
        "FASTMCP_LOG_LEVEL": "ERROR"
      },
      "disabled": false,
      "autoApprove": []
    }
  }
}
```

or docker after a successful `docker build -t awslabs/aws-cn-documentation-mcp-server .`:

```json
{
  "mcpServers": {
    "awslabs.aws-cn-documentation-mcp-server": {
      "command": "docker",
      "args": [
        "run",
        "--rm",
        "--interactive",
        "--env",
        "FASTMCP_LOG_LEVEL=ERROR",
        "awslabs/aws-cn-documentation-mcp-server:latest"
      ],
      "env": {},
      "disabled": false,
      "autoApprove": []
    }
  }
}
```

## Basic Usage

Example:

- "look up feature differences on EC2 between AWS China regions and global regions. cite your sources"

## Tools

### get_available_services

Fetch available services from AWS China documentation.

```python
get_available_services() -> str
```

### read_documentation

Fetches an AWS China documentation page and converts it to markdown format.

```python
read_documentation(url: str) -> str
```
