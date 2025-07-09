# Core MCP Server

MCP server that provides a starting point for using the following awslabs MCP servers
- awslabs.cdk-mcp-server
- awslabs.bedrock-kb-retrieval-mcp-server
- awslabs.nova-canvas-mcp-server
- awslabs.aws-pricing-mcp-server
- awslabs.aws-documentation-mcp-server
- awslabs.aws-diagram-mcp-server

## Features


### Planning and orchestration

- Provides tool for prompt understanding and translation to AWS services

## Prerequisites

- Python 3.12 or higher
- [uv](https://github.com/astral-sh/uv) - Fast Python package installer and resolver
- AWS credentials configured with Bedrock access
- Node.js (for UVX installation support)


## Installation

[![Install MCP Server](https://cursor.com/deeplink/mcp-install-light.svg)](https://cursor.com/install-mcp?name=awslabs.core-mcp-server&config=eyJjb21tYW5kIjoidXZ4IGF3c2xhYnMuY29yZS1tY3Atc2VydmVyQGxhdGVzdCIsImVudiI6eyJGQVNUTUNQX0xPR19MRVZFTCI6IkVSUk9SIn0sImF1dG9BcHByb3ZlIjpbXSwiZGlzYWJsZWQiOmZhbHNlfQ%3D%3D)

Configure the MCP server in your MCP client configuration (e.g., for Amazon Q Developer CLI, edit `~/.aws/amazonq/mcp.json`):

```json
{
  "mcpServers": {
    "awslabs.core-mcp-server": {
      "command": "uvx",
      "args": [
        "awslabs.core-mcp-server@latest"
      ],
      "env": {
        "FASTMCP_LOG_LEVEL": "ERROR"
      },
      "autoApprove": [],
      "disabled": false
    }
  }
}
```

or docker after a successful `docker build -t awslabs/core-mcp-server .`:

```json
  {
    "mcpServers": {
      "awslabs.core-mcp-server": {
        "command": "docker",
        "args": [
          "run",
          "--rm",
          "--interactive",
          "--env",
          "FASTMCP_LOG_LEVEL=ERROR",
          "awslabs/core-mcp-server:latest"
        ],
        "env": {},
        "disabled": false,
        "autoApprove": []
      }
    }
  }
```

## Tools and Resources

The server exposes the following tools through the MCP interface:

- `prompt_understanding` - Helps to provide guidance and planning support when building AWS Solutions for the given prompt
