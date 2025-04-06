"""List of available MCP servers that should be automatically installed.

This file is imported by the server.py file to ensure all required MCP servers are installed as part of CORE Suite.
"""

# List of available MCP servers that should be automatically installed
AVAILABLE_MCP_SERVERS = {
    'awslabs.cdk-mcp-server': {
        'command': 'uvx',
        'args': ['awslabs.cdk-mcp-server@latest'],
        'env': {'SHELL': '/usr/bin/zsh', 'FASTMCP_LOG_LEVEL': 'ERROR'},
        'autoApprove': [''],
    },
}
