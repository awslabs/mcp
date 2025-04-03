"""List of available MCP servers that should be automatically installed.

This file is imported by the server.py file to ensure all required MCP servers are installed as part of CORE Suite.
"""

# List of available MCP servers that should be automatically installed
AVAILABLE_MCP_SERVERS = {
    'awslabs.nova-canvas-mcp-server': {
        'command': 'uvx',
        'args': ['awslabs.nova-canvas-mcp-server@latest'],
        'env': {
            'SHELL': '/usr/bin/zsh',
            'FASTMCP_LOG_LEVEL': 'ERROR',
            'AWS_PROFILE': 'MCP_NOVA_CANVAS_PROFILE',
        },
        'disabled': False,
        'autoApprove': ['generate_image'],
    },
    'awslabs.bedrock-kb-retrieval-mcp-server': {
        'command': 'uvx',
        'args': ['awslabs.bedrock-kb-retrieval-mcp-server@latest'],
        'env': {
            'SHELL': '/usr/bin/zsh',
            'AWS_PROFILE': 'MCP_BEDROCK_KB_PROFILE',
            'FASTMCP_LOG_LEVEL': 'ERROR',
        },
        'autoApprove': ['QueryKnowledgeBases'],
    },
    'awslabs.cdk-mcp-server': {
        'command': 'uvx',
        'args': ['awslabs.cdk-mcp-server@latest'],
        'env': {'SHELL': '/usr/bin/zsh', 'FASTMCP_LOG_LEVEL': 'ERROR'},
        'autoApprove': [''],
    },
    'awslabs.cost-analysis-mcp-server': {
        'command': 'uvx',
        'args': ['awslabs.cost-analysis-mcp-server@latest'],
        'env': {'SHELL': '/usr/bin/zsh', 'FASTMCP_LOG_LEVEL': 'ERROR'},
        'autoApprove': [''],
    },
    'awslabs.aws-documentation-mcp-server': {
        'command': 'uvx',
        'args': ['awslabs.aws-documentation-mcp-server@latest'],
        'env': {'SHELL': '/usr/bin/zsh', 'FASTMCP_LOG_LEVEL': 'ERROR'},
        'autoApprove': [''],
    },
}
