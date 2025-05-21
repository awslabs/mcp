# AWS Labs Frontend MCP Server

[![smithery badge](https://smithery.ai/badge/@awslabs/frontend-mcp-server)](https://smithery.ai/server/@awslabs/frontend-mcp-server)

A Model Context Protocol (MCP) server that provides specialized tools for modern web application development.

## Features

### Modern React Application Documentation

This MCP Server provides comprehensive documentation on modern React application development through its `GetReactDocsByTopic` tool, which offers guidance on:

- **Essential Knowledge**: Fundamental concepts for building React applications
- **Basic UI Setup**: Setting up a React project with Tailwind CSS and shadcn/ui
- **Authentication**: AWS Amplify authentication integration
- **Routing**: Implementing routing with React Router
- **Customizing**: Theming with AWS Amplify components
- **Creating Components**: Building React components with AWS integrations
- **Troubleshooting**: Common issues and solutions for React development

## Prerequisites

1. Install `uv` from [Astral](https://docs.astral.sh/uv/getting-started/installation/) or the [GitHub README](https://github.com/astral-sh/uv#installation)
2. Install Python using `uv python install 3.10`

## Installation

Here are some ways you can work with MCP across AWS, and we'll be adding support to more products including Amazon Q Developer CLI soon: (e.g. for Amazon Q Developer CLI MCP, `~/.aws/amazonq/mcp.json`):

```json
{
  "mcpServers": {
    "awslabs.frontend-mcp-server": {
      "command": "uvx",
      "args": ["awslabs.frontend-mcp-server@latest"],
      "env": {
        "FASTMCP_LOG_LEVEL": "ERROR"
      },
      "disabled": false,
      "autoApprove": []
    }
  }
}
```

## Usage

The Frontend MCP Server provides the `GetReactDocsByTopic` tool for accessing specialized documentation on modern web application development with AWS technologies. This server will instruct the caller to clone a base web application repo and use that as the starting point for customization.

### GetReactDocsByTopic

This tool retrieves comprehensive documentation on specific React and AWS integration topics. To use it, specify which topic you need information on:

```python
result = await get_react_docs_by_topic('essential-knowledge')
```

Available topics:

1. **essential-knowledge**: Foundational concepts for building React applications with AWS services
2. **troubleshooting**: Common issues and solutions for React development with AWS integrations

Each topic returns comprehensive markdown documentation with explanations, code examples, and implementation guidance.
