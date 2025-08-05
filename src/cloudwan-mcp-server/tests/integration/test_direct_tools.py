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
"""Test CloudWAN MCP Tools directly using the tool registry"""

import asyncio
import json
import os
import sys

sys.path.append(".")


async def test_direct_tools() -> None:
    """Test the MCP tools directly via tool registry"""
    # Set correct environment
    os.environ["AWS_PROFILE"] = "taylaand+net-dev-Admin"
    os.environ["AWS_DEFAULT_REGION"] = "us-west-2"
    os.environ["AWS_REGION"] = "us-west-2"

    try:
        from awslabs.cloudwan_mcp_server.aws.client_manager import AWSClientManager
        from awslabs.cloudwan_mcp_server.config import CloudWANConfig
        from awslabs.cloudwan_mcp_server.tools.core.discovery import (
            CoreNetworkDiscoveryTool,
            GlobalNetworkDiscoveryTool,
        )

        print("🔄 Initializing CloudWAN MCP Tools...")

        # Initialize components
        config = CloudWANConfig()
        aws_manager = AWSClientManager(config)

        print("✅ Components initialized successfully")

        # Test Global Networks Discovery
        print("\n🔍 Testing Global Networks Discovery...")
        global_net_tool = GlobalNetworkDiscoveryTool(aws_manager, config)

        result = await global_net_tool.execute({})

        # Extract text content from the result
        if hasattr(result, "content") and result.content:
            response_text = result.content[0].text
            try:
                response_data = json.loads(response_text)
                print("✅ Global Networks Response:")
                print(f"   - Total networks found: {response_data.get('total_count', 0)}")
                print(f"   - Status: {response_data.get('status', 'unknown')}")
                if response_data.get("global_networks"):
                    for gn in response_data["global_networks"]:
                        print(f"   - Global Network: {gn.get('global_network_id', 'N/A')}")
                else:
                    print("   - No global networks found (expected if CloudWAN not configured)")
            except json.JSONDecodeError:
                print(f"Response text: {response_text}")
        else:
            print(f"Raw result: {result}")

        # Test Core Networks Discovery
        print("\n🔍 Testing Core Networks Discovery...")
        core_net_tool = CoreNetworkDiscoveryTool(aws_manager, config)

        result2 = await core_net_tool.execute({})

        # Extract text content from the result
        if hasattr(result2, "content") and result2.content:
            response_text2 = result2.content[0].text
            try:
                response_data2 = json.loads(response_text2)
                print("✅ Core Networks Response:")
                print(f"   - Total networks found: {response_data2.get('total_count', 0)}")
                print(f"   - Status: {response_data2.get('status', 'unknown')}")
                if response_data2.get("core_networks"):
                    for cn in response_data2["core_networks"]:
                        print(f"   - Core Network: {cn.get('core_network_id', 'N/A')}")
                        print(f"     Segments: {len(cn.get('segments', []))}")
                else:
                    print("   - No core networks found")
            except json.JSONDecodeError:
                print(f"Response text: {response_text2}")
        else:
            print(f"Raw result: {result2}")

        print("\n✅ Tool testing completed successfully!")

    except Exception as e:
        print(f"❌ Error testing MCP tools: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_direct_tools())
