# Core MCP Server

MCP server that manages and coordinates other MCP servers in your environment

## Features

### Automatic MCP Server Management

- Automatically installs and configures required MCP servers on startup
- Ensures all necessary MCP servers are available
- Maintains consistent configuration across servers

### Planning and orchestration

- Provides tools to plan and orchestrate AWS Labs MCP servers

### UVX Installation Support

- Provides tools to install MCP servers via UVX
- Simplifies installation of additional MCP servers
- Manages dependencies and version requirements

### Centralized Configuration

- Manages MCP server configurations in one place
- Single configuration file for all servers
- Automatic configuration validation

### Environment Management

- Handles environment variables and AWS credentials
- Ensures proper AWS authentication
- Manages environment variables across servers

### Comprehensive Logging

- Detailed logging for troubleshooting
- Centralized logs for all servers
- Configurable log levels

## Prerequisites

- Python 3.12 or higher
- [uv](https://github.com/astral-sh/uv) - Fast Python package installer and resolver
- AWS credentials configured with Bedrock access
- Node.js (for UVX installation support)

## Environment Requirements

The server requires certain environment variables to be set for proper operation:

### Required Environment Variables

- `MCP_CONFIG_PATH` - Path to the MCP configuration file (e.g., `/Users/username/Library/Application Support/vscode/User/globalStorage/saoudrizwan.claude-dev/settings/cline_mcp_settings.json`)

### Alternative Environment Variables

The server will also check for these alternative environment variables if `MCP_CONFIG_PATH` is not set:

- `CLINE_MCP_SETTINGS_PATH` - Path to Cline MCP settings file
- `MCP_SETTINGS_PATH` - Alternative path to MCP settings file

### Setting Environment Variables

You can set these environment variables in your shell profile (e.g., `~/.zshrc` or `~/.bashrc`):

```bash
# Add to your shell profile
export MCP_CONFIG_PATH="/path/to/your/mcp/config.json"
```

Or you can set them when running the server:

```bash
MCP_CONFIG_PATH="/path/to/your/mcp/config.json" python -m mcp_core.server.server
```

### AWS Environment Variables

For AWS services integration:

- `AWS_PROFILE` - AWS profile to use for AWS services
- `AWS_REGION` - AWS region to use for AWS services

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
        "FASTMCP_LOG_LEVEL": "ERROR",
        "MCP_SETTINGS_PATH": "path to your mcp server settings"
      },
      "autoApprove": [],
      "disabled": false
    }
  }
}
```

## Tools and Resources

The server exposes the following tools through the MCP interface:

- `prompt_understanding` - Helps to provide clear plan for building AWS Solutions
- `install_awslabs_mcp_server` - Installs MCP servers via UVX
- `update` - Updates all MCP servers to ensure they are up-to-date with the latest configuration

## Automatic Server Installation

The server automatically installs and configures required MCP servers on startup and before the server is started. This feature ensures that all necessary MCP servers are always available for use and up-to-date with the latest configuration, even when the server is restarted.

### Configuration

The list of servers to be automatically installed is defined in `mcp_core/server/available_servers.py`. Each server entry includes:

```python
"server-name": {
  "command": "uvx",  # Command to run the server
  "args": ["package-name"],  # Arguments for the command
  "env": {  # Environment variables
    "SHELL": "/usr/bin/zsh",
    "FASTMCP_LOG_LEVEL": "ERROR"
  },
  "disabled": False,  # Whether the server is disabled
  "autoApprove": []  # List of tools to auto-approve
}
```
