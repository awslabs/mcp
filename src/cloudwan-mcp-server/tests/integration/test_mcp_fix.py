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
"""Test CloudWAN MCP server fix directly"""

import asyncio
import os
import sys

sys.path.append(".")


async def test_mcp_server_fix() -> None:
    """Test the MCP server fix to ensure tools return visible results"""
    os.environ["AWS_PROFILE"] = "taylaand+net-dev-Admin"
    os.environ["AWS_DEFAULT_REGION"] = "us-west-2"
    os.environ["AWS_REGION"] = "us-west-2"

    try:
        from awslabs.cloudwan_mcp_server.server import CloudWANMCPServer

        print("🔧 Testing CloudWAN MCP Server Fix")
        print("=" * 40)

        # Initialize server
        server = CloudWANMCPServer()
        await server.initialize()

        print("✅ Server initialized successfully")

        # Test the call_tool method directly
        print("\n🧪 Testing list_core_networks tool...")
        try:
            result = await server.server.call_tool("list_core_networks", {})
            print("✅ Tool executed successfully!")
            print(f"Result type: {type(result)}")

            if hasattr(result, "content") and result.content:
                print("📊 Tool returned content:")
                for item in result.content:
                    if hasattr(item, "text"):
                        print(f"Content: {item.text}")
                    else:
                        print(f"Content: {item}")
            else:
                print("❌ No content returned")
                print(f"Result: {result}")

        except Exception as e:
            print(f"❌ Tool execution failed: {e}")
            import traceback

            traceback.print_exc()

        # Test another tool
        print("\n🧪 Testing get_global_networks tool...")
        try:
            result = await server.server.call_tool("get_global_networks", {})
            print("✅ Tool executed successfully!")

            if hasattr(result, "content") and result.content:
                print("📊 Tool returned content:")
                for item in result.content:
                    if hasattr(item, "text"):
                        print(f"Content: {item.text}")
            else:
                print("❌ No content returned")

        except Exception as e:
            print(f"❌ Tool execution failed: {e}")

    except Exception as e:
        print(f"❌ Server initialization failed: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_mcp_server_fix())
