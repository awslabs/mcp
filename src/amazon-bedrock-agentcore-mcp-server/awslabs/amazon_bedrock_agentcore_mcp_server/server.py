# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Amazon Bedrock AgentCore MCP Server.

Model Context Protocol server for Amazon Bedrock AgentCore operations.
Designed with a modular architecture to improve maintainability.

Module Organization:
- utils.py: Core utilities, OAuth, and environment validation
- runtime.py: Agent deployment and invocation management
- gateway.py: Gateway operations and MCP integration
- identity.py: Credential provider management
- memory.py: Memory operations and integration
- Main server: Module coordination and tool registration

Available Tools:

Authentication:
- get_oauth_access_token: Generate OAuth tokens for gateway access
- validate_agentcore_environment: Check development environment

Discovery:
- what_agents_can_i_invoke: Find available agents (local + AWS)
- project_discover: Locate agent files and configurations
- discover_agentcore_examples: GitHub examples discovery
- analyze_agent_code: Code analysis and migration planning

Agent Operations:
- transform_to_agentcore: Convert code to AgentCore format
- deploy_agentcore_app: Deploy agents with multiple modes
- get_agent_status: Check deployment status
- invoke_agent: Standard agent invocation
- invoke_oauth_agent: OAuth-enabled invocation
- invoke_agent_smart: Automatic fallback invocation
- check_oauth_status: OAuth deployment validation
- get_runtime_oauth_token: Runtime token generation

Gateway Management:
- agent_gateway: Gateway creation and management

Credential Management:
- manage_credentials: Credential provider operations
- create_credential_provider: New credential creation
- list_credential_providers: List available providers
- get_credential_provider: Provider details
- update_credential_provider: Update existing providers
- delete_credential_provider: Remove providers

Memory Operations:
- agent_memory: Memory management and integration

Requires: Python 3.10+, Amazon Bedrock AgentCore SDK 2.x
"""

import sys
import traceback
from .gateway import register_gateway_tools

# Identity and credential management
from .identity import register_identity_tools, register_oauth_tools

# Memory management and integration
from .memory import register_memory_tools

# Agent lifecycle and runtime management
from .runtime import register_analysis_tools, register_deployment_tools
from .utils import (
    register_discovery_tools,
    register_environment_tools,
    register_github_discovery_tools,
)

# MCP server framework
from mcp.server.fastmcp import FastMCP
from pathlib import Path


# === SERVER INITIALIZATION ===
# Initialize FastMCP server with descriptive name
mcp = FastMCP('AgentCore MCP Server')

register_oauth_tools(mcp)
register_environment_tools(mcp)
register_discovery_tools(mcp)  # Enhanced agent discovery from legacy servers
register_github_discovery_tools(mcp)  # GitHub examples discovery
register_analysis_tools(mcp)
register_deployment_tools(mcp)
register_gateway_tools(mcp)
register_identity_tools(mcp)
register_memory_tools(mcp)


def run_main():
    """Run the main function, handling asyncio properly."""
    print('Starting AgentCore MCP Server ...')

    print(f'Server directory: {Path(__file__).parent}')
    print('Ready for MCP client connections...')

    # Run the server directly without asyncio.run()
    mcp.run()


if __name__ == '__main__':
    try:
        run_main()
    except KeyboardInterrupt:
        print('\nAgentCore MCP Server shutting down...')
        sys.exit(0)
    except Exception as e:
        print(f'\nServer error: {str(e)}')
        traceback.print_exc()
        sys.exit(1)
