# AWS Documentation MCP Server

Model Context Protocol (MCP) server for AWS Documentation

This MCP server provides tools to access AWS documentation, search for content, and get recommendations.

## Features

- **Read Documentation**: Fetch and convert AWS documentation pages to markdown format
- **Search Documentation**: Search AWS documentation using the official search API (global only)
- **Recommendations**: Get content recommendations for AWS documentation pages (global only)
- **Get Available Services List**: Get a list of available AWS services in China regions (China only)

## Prerequisites

### Installation Requirements

1. Install `uv` from [Astral](https://docs.astral.sh/uv/getting-started/installation/) or the [GitHub README](https://github.com/astral-sh/uv#installation)
2. Install Python 3.10 or newer using `uv python install 3.10` (or a more recent version)

## Installation

[![Install MCP Server](https://cursor.com/deeplink/mcp-install-light.svg)](https://cursor.com/install-mcp?name=awslabs.aws-documentation-mcp-server&config=eyJjb21tYW5kIjoidXZ4IGF3c2xhYnMuYXdzLWRvY3VtZW50YXRpb24tbWNwLXNlcnZlckBsYXRlc3QiLCJlbnYiOnsiRkFTVE1DUF9MT0dfTEVWRUwiOiJFUlJPUiIsIkFXU19ET0NVTUVOVEFUSU9OX1BBUlRJVElPTiI6ImF3cyJ9LCJkaXNhYmxlZCI6ZmFsc2UsImF1dG9BcHByb3ZlIjpbXX0%3D)

Configure the MCP server in your MCP client configuration (e.g., for Amazon Q Developer CLI, edit `~/.aws/amazonq/mcp.json`):

```json
{
  "mcpServers": {
    "awslabs.aws-documentation-mcp-server": {
      "command": "uvx",
      "args": ["awslabs.aws-documentation-mcp-server@latest"],
      "env": {
        "FASTMCP_LOG_LEVEL": "ERROR",
        "AWS_DOCUMENTATION_PARTITION": "aws"
      },
      "disabled": false,
      "autoApprove": []
    }
  }
}
```

> **Note**: Set `AWS_DOCUMENTATION_PARTITION` to `aws-cn` to query AWS China documentation instead of global AWS documentation.

or docker after a successful `docker build -t mcp/aws-documentation .`:

```json
{
  "mcpServers": {
    "awslabs.aws-documentation-mcp-server": {
      "command": "docker",
      "args": [
        "run",
        "--rm",
        "--interactive",
        "--env",
        "FASTMCP_LOG_LEVEL=ERROR",
        "--env",
        "AWS_DOCUMENTATION_PARTITION=aws",
        "mcp/aws-documentation:latest"
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

- "look up documentation on S3 bucket naming rule. cite your sources"
- "recommend content for page https://docs.aws.amazon.com/AmazonS3/latest/userguide/bucketnamingrules.html"

![AWS Documentation MCP Demo](https://github.com/awslabs/mcp/blob/main/src/aws-documentation-mcp-server/basic-usage.gif?raw=true)

## Tools

### read_documentation

Fetches an AWS documentation page and converts it to markdown format.

```python
read_documentation(url: str) -> str
```

### search_documentation (global only)

Searches AWS documentation using the official AWS Documentation Search API.

```python
search_documentation(search_phrase: str, limit: int) -> list[dict]
```

### recommend (global only)

Gets content recommendations for an AWS documentation page.

```python
recommend(url: str) -> list[dict]
```

### get_available_services (China only)

Gets a list of available AWS services in China regions.

```python
get_available_services() -> str
```
