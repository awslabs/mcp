# MCP Core

MCP Core is a central server that manages and coordinates other MCP servers in your environment. It provides automatic installation, configuration, and management of MCP servers to ensure a seamless experience when working with AWS services.

## Core Features

- **Automatic MCP Server Management**: Automatically installs and configures required MCP servers on startup
- **UVX Installation Support**: Provides tools to install MCP servers via UVX
- **AWS Service Integration**: Connects to various AWS services through specialized MCP servers
- **Centralized Configuration**: Manages MCP server configurations in one place
- **Environment Management**: Handles environment variables and AWS credentials
- **Comprehensive Logging**: Detailed logging for troubleshooting

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

1. Install uv if you haven't already:

Follow the instructions here: <https://docs.astral.sh/uv/getting-started/installation/#installing-uv>

2. Install with uv tools

```bash
uv tool install awslabs.core-mcp-server
```

3. Configure your MCP client (e.g., Amazon Q Developer CLI, Cline):


```json
{
  "mcpServers": {
    ...
    "awslabs.core-mcp-server": {
      "command": "uvx",
      "args": [
        "aswlabs.core-mcp-server",
      ],
      "env": {
        "SHELL": "/usr/bin/zsh",
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






