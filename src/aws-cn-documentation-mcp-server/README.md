# AWS China Documentation MCP Server

Model Context Protocol (MCP) server for AWS China Documentation

This MCP server provides tools to access AWS China documentation, search for content, and get recommendations specifically for AWS China regions.

## Features

- **Read Documentation**: Fetch and convert AWS China documentation pages to markdown format
- **Search Documentation**: Search AWS China documentation using the official search API
- **Recommendations**: Get content recommendations for AWS China documentation pages

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

or docker after a succesful `docker build -t awslabs/aws-cn-documentation-mcp-server .`:

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

- "look up documentation on S3 bucket naming rule for AWS China. cite your sources"
- "recommend content for page https://docs.amazonaws.cn/AmazonS3/latest/userguide/bucketnamingrules.html"

![AWS China Documentation MCP Demo](https://github.com/awslabs/mcp/blob/main/src/aws-cn-documentation-mcp-server/basic-usage.gif?raw=true)

## Tools

### read_documentation

Fetches an AWS China documentation page and converts it to markdown format.

```python
read_documentation(url: str) -> str
```

### search_documentation

Searches AWS China documentation using the official AWS China Documentation Search API.

```python
search_documentation(search_phrase: str, limit: int) -> list[dict]
```

### recommend

Gets content recommendations for an AWS China documentation page.

```python
recommend(url: str) -> list[dict]
```
