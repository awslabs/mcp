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

#!/usr/bin/env python3
"""Quick local test script for Carbon Footprint MCP Server."""

import asyncio
from awslabs.carbon_footprint_mcp_server.server import mcp


async def test_tools():
    """Test the MCP server tools locally."""
    print('🧪 Testing Carbon Footprint MCP Server Tools...')

    # Get available tools
    tools = await mcp.list_tools()
    print(f'\n📋 Available Tools ({len(tools)}):')
    for tool in tools:
        print(f'  • {tool.name}: {tool.description}')

    print('\n📖 Server Instructions:')
    print(mcp.instructions[:200] + '...' if len(mcp.instructions) > 200 else mcp.instructions)

    print('\n✅ MCP Server loaded successfully!')
    print('\n🚀 To test with a real MCP client:')
    print('   mcp inspect awslabs.carbon-footprint-mcp-server')


if __name__ == '__main__':
    asyncio.run(test_tools())
