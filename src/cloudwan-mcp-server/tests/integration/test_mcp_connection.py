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
"""Test the CloudWAN MCP server directly via MCP protocol."""

import asyncio
import json
import os
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client import stdio


async def test_mcp_server() -> bool:
    """Test MCP server connection and tool usage."""
    print("🚀 Testing CloudWAN MCP Server via MCP protocol...")

    # Set required environment variables
    os.environ["AWS_DEFAULT_REGION"] = "us-west-2"

    # Server parameters - using the installed package
    server_params = StdioServerParameters(
        command="python",
        args=["-m", "awslabs.cloudwan_mcp_server"],
        env={
            **os.environ,
            "AWS_DEFAULT_REGION": "us-west-2",
        },
    )

    try:
        async with stdio.stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                # Initialize the connection
                await session.initialize()
                print("✅ MCP connection established")

                # List available tools
                tools = await session.list_tools()
                print(f"📋 Found {len(tools.tools)} tools:")
                for tool in tools.tools[:5]:  # Show first 5 tools
                    print(f"  - {tool.name}: {tool.description}")

                # Test get_global_networks tool specifically
                if any(tool.name == "get_global_networks" for tool in tools.tools):
                    print("\n🔍 Testing get_global_networks tool...")
                    result = await session.call_tool("get_global_networks", arguments={})
                    print("✅ Tool executed successfully!")
                    print(f"📄 Content type: {type(result.content[0]) if result.content else 'None'}")

                    if result.content and hasattr(result.content[0], "text"):
                        # Parse the JSON content
                        response_data = json.loads(result.content[0].text)
                        print(f"🌐 Found {response_data.get('total_count', 0)} global networks")
                        for network in response_data.get("global_networks", [])[:2]:
                            print(f"  - {network['global_network_id']}: {network.get('description', 'No description')}")
                    else:
                        print(f"⚠️  Unexpected content format: {result.content}")

                else:
                    print("❌ get_global_networks tool not found")

    except Exception as e:
        print(f"❌ MCP connection failed: {e}")
        import traceback

        traceback.print_exc()
        return False

    return True


if __name__ == "__main__":
    success = asyncio.run(test_mcp_server())
    sys.exit(0 if success else 1)
