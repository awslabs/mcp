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

"""Test MCP server functionality."""

import asyncio
import sys


sys.path.append('.')

from awslabs.amazon_bedrock_agentcore_mcp_server.server import mcp


async def test_server():
    """Test the MCP server tools."""
    print('=== MCP Server Test ===')

    # List all available tools first
    tools_response = await mcp.list_tools()
    tools = tools_response.tools if hasattr(tools_response, 'tools') else []

    print(f'\n=== Available Tools ({len(tools)}) ===')
    memory_tools = []
    for tool in tools:
        tool_name = tool.name
        print(f'  ✅ {tool_name}')
        if 'memory' in tool_name:
            memory_tools.append(tool_name)

    print(f'\n=== Memory Tools Found ({len(memory_tools)}) ===')
    for tool_name in memory_tools:
        print(f'  🧠 {tool_name}')

    # Test calling a tool using call_tool
    try:
        result = await mcp.call_tool('server_info', {})
        print('\n✅ server_info tool works')
        print('First 200 chars:', result.content[0].text[:200] if result.content else 'No content')
    except Exception as e:
        print(f'❌ server_info error: {e}')

    # Test agent_memory tool
    try:
        result = await mcp.call_tool('agent_memory', {'action': 'list'})
        print('\n✅ agent_memory tool works')
        content = result.content[0].text if result.content else 'No content'
        print('First 200 chars:', content[:200])
    except Exception as e:
        print(f'❌ agent_memory error: {e}')

    print('\n=== Test Complete ===')


if __name__ == '__main__':
    asyncio.run(test_server())
