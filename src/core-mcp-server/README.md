# Core MCP Server

MCP server that provides a starting point for using the following awslabs MCP servers
- awslabs.cdk-mcp-server
- awslabs.bedrock-kb-retrieval-mcp-server
- awslabs.nova-canvas-mcp-server
- awslabs.cost-analysis-mcp-server
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

Here are some ways you can work with MCP across AWS, and we'll be adding support to more products including Amazon Q Developer CLI soon: (e.g. for Amazon Q Developer CLI MCP, `~/.aws/amazonq/mcp.json`):

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
