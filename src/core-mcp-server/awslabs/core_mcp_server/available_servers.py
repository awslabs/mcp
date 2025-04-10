# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance
# with the License. A copy of the License is located at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES
# OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions
# and limitations under the License.
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
