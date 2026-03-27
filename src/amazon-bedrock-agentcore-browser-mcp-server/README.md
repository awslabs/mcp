# Amazon Bedrock AgentCore Browser MCP Server

Model Context Protocol (MCP) server for managing ephemeral browser sessions on Amazon Bedrock AgentCore Browser service.

## Overview

This MCP server provides tools to create, manage, and interact with browser sessions on AWS AgentCore Browser. It enables LLMs to automate web browsing tasks through a managed browser environment.

## Quick Start

Run the server using uvx:

```bash
uvx awslabs.amazon-bedrock-agentcore-browser-mcp-server
```

## Available Tools

This server provides 8 MCP tools for browser management:

1. **create_browser_session** - Create a new ephemeral browser session
2. **get_browser_session** - Get details of an existing browser session
3. **list_browser_sessions** - List all browser sessions
4. **delete_browser_session** - Delete a browser session
5. **navigate_to_url** - Navigate the browser to a URL
6. **take_screenshot** - Capture a screenshot of the current page
7. **execute_script** - Execute JavaScript in the browser context
8. **get_page_content** - Get the HTML content of the current page

## Configuration

### Environment Variables

- **AWS_REGION** - AWS region for AgentCore Browser API (default: session region or us-east-1)
- **AWS_PROFILE** - AWS CLI profile name for authentication (optional)
- **BROWSER_IDENTIFIER** - Custom browser identifier for session management (optional)

### AWS Credentials

The server uses standard AWS credential resolution:
1. Environment variables (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY)
2. AWS CLI profile (via AWS_PROFILE)
3. EC2 instance metadata
4. ECS task credentials

## Installation

### From PyPI

```bash
pip install awslabs.amazon-bedrock-agentcore-browser-mcp-server
```

### From Source

```bash
cd src/amazon-bedrock-agentcore-browser-mcp-server
pip install -e .
```

## Development

### Setup

```bash
# Install development dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run linting
ruff check .

# Run type checking
pyright
```

## License

Apache-2.0
