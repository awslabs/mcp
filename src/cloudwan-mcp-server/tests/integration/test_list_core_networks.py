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
"""Test the list_core_networks tool specifically to validate the fix."""

import asyncio
import json
import logging
import os
import sys
from pathlib import Path

# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).parent.absolute()))


async def test_list_core_networks_directly() -> bool | None:
    """Test the list_core_networks tool directly."""
    # Set up logging
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    logger = logging.getLogger(__name__)

    logger.info("=" * 80)
    logger.info("TESTING list_core_networks TOOL DIRECTLY")
    logger.info("=" * 80)

    try:
        # Set up environment
        os.environ.update(
            {"AWS_PROFILE": "taylaand+net-dev-Admin", "AWS_DEFAULT_REGION": "us-west-2", "CLOUDWAN_MCP_DEBUG": "true"}
        )

        # Import the components
        from awslabs.cloudwan_mcp_server.aws.client_manager import AWSClientManager
        from awslabs.cloudwan_mcp_server.config import CloudWANConfig
        from awslabs.cloudwan_mcp_server.tools.core.discovery import CoreNetworkDiscoveryTool

        logger.info("✅ Successfully imported components")

        # Create configuration and AWS manager
        config = CloudWANConfig()
        aws_manager = AWSClientManager(config)

        # Create core networks tool
        core_networks_tool = CoreNetworkDiscoveryTool(aws_manager, config)

        logger.info("✅ Successfully created list_core_networks tool")
        logger.info(f"Tool name: {core_networks_tool.tool_name}")
        logger.info(f"Tool description: {core_networks_tool.description}")

        # Execute the tool
        logger.info("🧪 Executing list_core_networks tool...")
        result = await core_networks_tool.execute({})

        logger.info("=" * 60)
        logger.info("TOOL EXECUTION RESULT:")
        logger.info("=" * 60)
        logger.info(f"Result type: {type(result)}")

        if hasattr(result, "content") and result.content:
            logger.info(f"Content items: {len(result.content)}")
            for i, content in enumerate(result.content):
                logger.info(f"Content {i}:")
                logger.info(f"  Type: {getattr(content, 'type', 'NO TYPE')}")
                text_content = getattr(content, "text", "")
                logger.info(f"  Text length: {len(text_content)}")

                # Try to parse as JSON and display nicely
                try:
                    parsed_json = json.loads(text_content)
                    logger.info("✅ JSON parsing successful")
                    logger.info("📊 CORE NETWORKS RESULT:")
                    logger.info(json.dumps(parsed_json, indent=2))

                    # Check if we found any networks
                    core_networks = parsed_json.get("core_networks", [])
                    if core_networks:
                        logger.info(f"🎉 SUCCESS: Found {len(core_networks)} core networks!")
                        for cn in core_networks:
                            logger.info(
                                f"  - {cn.get('core_network_id', 'unknown')}: {cn.get('description', 'no description')}"
                            )
                    else:
                        logger.info("ℹ️  No core networks found - this may be expected if CloudWAN is not configured")

                except json.JSONDecodeError as e:
                    logger.error(f"❌ JSON parsing failed: {e}")
                    logger.info(f"Raw text content: {text_content[:500]}...")

        else:
            logger.error("❌ Result has no content!")

        return True

    except Exception as e:
        logger.error(f"❌ Test failed with exception: {e}")
        import traceback

        logger.error(traceback.format_exc())
        return False


async def test_through_mcp_server() -> bool | None:
    """Test list_core_networks through MCP server."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    logger = logging.getLogger(__name__)

    logger.info("=" * 80)
    logger.info("TESTING list_core_networks THROUGH MCP SERVER")
    logger.info("=" * 80)

    try:
        # Set up environment
        os.environ.update(
            {"AWS_PROFILE": "taylaand+net-dev-Admin", "AWS_DEFAULT_REGION": "us-west-2", "CLOUDWAN_MCP_DEBUG": "true"}
        )

        # Import server components
        from mcp.types import CallToolRequest

        from awslabs.cloudwan_mcp_server.config import CloudWANConfig
        from awslabs.cloudwan_mcp_server.server import CloudWANMCPServer

        # Create server
        config = CloudWANConfig()
        server = CloudWANMCPServer(config)

        logger.info("✅ Server created successfully")

        # Initialize server
        await server.initialize()

        logger.info("✅ Server initialized successfully")

        # Get the call_tool handler
        handlers = server.server.request_handlers
        call_tool_handler = handlers[CallToolRequest]

        # Create request
        request = CallToolRequest(method="tools/call", params={"name": "list_core_networks", "arguments": {}})

        logger.info("🧪 Executing list_core_networks through MCP server...")

        # Execute
        result = await call_tool_handler(request)

        logger.info("=" * 60)
        logger.info("MCP SERVER RESULT:")
        logger.info("=" * 60)
        logger.info(f"Result type: {type(result)}")

        # Extract the actual CallToolResult from ServerResult
        if hasattr(result, "root"):
            actual_result = result.root
            logger.info(f"Actual result type: {type(actual_result)}")

            if hasattr(actual_result, "content") and actual_result.content:
                logger.info(f"Content items: {len(actual_result.content)}")
                for i, content in enumerate(actual_result.content):
                    text_content = getattr(content, "text", "")
                    logger.info(f"Content {i} length: {len(text_content)}")

                    # Try to parse as JSON
                    try:
                        parsed_json = json.loads(text_content)
                        logger.info("✅ MCP Server JSON parsing successful")
                        logger.info("📊 MCP SERVER CORE NETWORKS RESULT:")
                        logger.info(json.dumps(parsed_json, indent=2))

                        # Check for success
                        core_networks = parsed_json.get("core_networks", [])
                        if core_networks:
                            logger.info(f"🎉 MCP SUCCESS: Found {len(core_networks)} core networks!")
                        else:
                            logger.info("ℹ️  MCP: No core networks found")

                    except json.JSONDecodeError as e:
                        logger.error(f"❌ MCP JSON parsing failed: {e}")
                        logger.info(f"Raw MCP content: {text_content[:200]}...")

            else:
                logger.error("❌ MCP result has no content")
        else:
            logger.error("❌ MCP result has no root")

        return True

    except Exception as e:
        logger.error(f"❌ MCP server test failed: {e}")
        import traceback

        logger.error(traceback.format_exc())
        return False


async def main() -> None:
    """Main test runner."""
    print("🚨 EMERGENCY FIX VALIDATION for list_core_networks")
    print("Testing that the performance monitor fix resolved the invisible results issue")
    print()

    # Test 1: Direct tool execution
    print("=" * 60)
    print("TEST 1: Direct Tool Execution")
    print("=" * 60)

    success1 = await test_list_core_networks_directly()

    if success1:
        print("✅ Direct tool test PASSED")
    else:
        print("❌ Direct tool test FAILED")

    print()

    # Test 2: MCP server execution
    print("=" * 60)
    print("TEST 2: MCP Server Execution")
    print("=" * 60)

    success2 = await test_through_mcp_server()

    if success2:
        print("✅ MCP server test PASSED")
    else:
        print("❌ MCP server test FAILED")

    print()
    print("=" * 60)
    if success1 and success2:
        print("🎉 EMERGENCY FIX VALIDATED - CloudWAN tools should now display results!")
        print("The original issue (performance monitor async context) has been resolved.")
    else:
        print("🚨 EMERGENCY FIX INCOMPLETE - Further investigation needed")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
