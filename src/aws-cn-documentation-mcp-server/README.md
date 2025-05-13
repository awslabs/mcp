# AWS Documentation MCP Server

Model Context Protocol (MCP) server for AWS Documentation

This MCP server provides tools to access AWS documentation, search for content, and get recommendations.

## Features

- **Read Documentation**: Fetch and convert AWS documentation pages to markdown format
- **Search Documentation**: Search AWS documentation using the official search API
- **Recommendations**: Get content recommendations for AWS documentation pages

## Prerequisites

### Installation Requirements

1. Install `uv` from [Astral](https://docs.astral.sh/uv/getting-started/installation/) or the [GitHub README](https://github.com/astral-sh/uv#installation)
2. Install Python 3.10 or newer using `uv python install 3.10` (or a more recent version)

## Installation

Here are some ways you can work with MCP across AWS, and we'll be adding support to more products including Amazon Q Developer CLI soon: (e.g. for Amazon Q Developer CLI MCP, ~/.aws/amazonq/mcp.json):

```json
{
  "mcpServers": {
    "awslabs.aws-documentation-mcp-server": {
        "command": "uvx",
        "args": ["awslabs.aws-documentation-mcp-server@latest"],
        "env": {
          "FASTMCP_LOG_LEVEL": "ERROR"
        },
        "disabled": false,
        "autoApprove": []
    }
  }
}
```

or docker after a succesful `docker build -t awslabs/aws-documentation-mcp-server .`:

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
          "awslabs/aws-documentation-mcp-server:latest"
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

### search_documentation

Searches AWS documentation using the official AWS Documentation Search API.

```python
search_documentation(search_phrase: str, limit: int) -> list[dict]
```

### recommend

Gets content recommendations for an AWS documentation page.

```python
recommend(url: str) -> list[dict]
```
