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
"""Test CloudWAN MCP Tools directly"""

import asyncio
import os
import sys

sys.path.append(".")


async def test_mcp_tools() -> None:
    """Test the MCP tools directly"""
    # Set correct environment
    os.environ["AWS_PROFILE"] = "taylaand+net-dev-Admin"
    os.environ["AWS_DEFAULT_REGION"] = "us-west-2"
    os.environ["AWS_REGION"] = "us-west-2"

    try:
        from awslabs.cloudwan_mcp_server.aws.client_manager import AWSClientManager
        from awslabs.cloudwan_mcp_server.config import CloudWANConfig
        from awslabs.cloudwan_mcp_server.server import CloudWANMCPServer

        print("🔄 Initializing CloudWAN MCP Server...")

        # Initialize server
        config = CloudWANConfig()
        AWSClientManager(config)
        server = CloudWANMCPServer()
        await server.initialize()

        print("✅ Server initialized successfully")

        # Test list_core_networks tool
        print("\n🔍 Testing list_core_networks tool...")
        result = await server.call_tool("list_core_networks", {})
        print(f"Result type: {type(result)}")
        print(f"Result: {result}")

        # Test get_global_networks tool
        print("\n🔍 Testing get_global_networks tool...")
        result2 = await server.call_tool("get_global_networks", {})
        print(f"Result type: {type(result2)}")
        print(f"Result: {result2}")

    except Exception as e:
        print(f"❌ Error testing MCP tools: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_mcp_tools())
