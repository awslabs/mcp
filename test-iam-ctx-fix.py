#!/usr/bin/env python3
"""Test script to verify the ctx parameter fix."""

import asyncio
import os
import sys

# Add the src directory to the path so we can import the modified server
sys.path.insert(0, '/home/plex/development/repos/aws/mcp/src/iam-mcp-server')

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def main():
    # Use the local modified version via python -m
    server_params = StdioServerParameters(
        command="python",
        args=["-m", "awslabs.iam_mcp_server.server", "--readonly"],
        env={
            "AWS_PROFILE": os.environ.get("AWS_PROFILE", "default"),
            "AWS_REGION": os.environ.get("AWS_REGION", "us-east-1"),
            "PYTHONPATH": "/home/plex/development/repos/aws/mcp/src/iam-mcp-server"
        }
    )

    print("=" * 70)
    print("Testing IAM MCP Server ctx Parameter Fix")
    print("=" * 70)
    print()

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            print("✓ Connected to server\n")

            # Test 1: List tools and check schema
            print("Test 1: Check list_users tool schema")
            print("-" * 50)
            tools_result = await session.list_tools()
            list_users_tool = [t for t in tools_result.tools if t.name == "list_users"][0]

            schema = list_users_tool.inputSchema
            if "properties" in schema:
                props = schema["properties"]
                if "ctx" in props:
                    print("❌ FAIL: ctx is still in the schema!")
                    print(f"   Properties: {list(props.keys())}")
                    return False
                else:
                    print("✅ PASS: ctx is not in the schema")
                    print(f"   Properties: {list(props.keys())}")
            print()

            # Test 2: Call the tool
            print("Test 2: Call list_users tool")
            print("-" * 50)
            result = await session.call_tool("list_users", arguments={"max_items": 3})

            if result.isError:
                print(f"❌ FAIL: Tool returned error")
                print(f"   Error: {result.content[0].text if result.content else 'Unknown'}")
                return False
            else:
                print("✅ PASS: Tool call succeeded!")
                if result.content:
                    import json
                    from mcp import types
                    content_block = result.content[0]
                    if isinstance(content_block, types.TextContent):
                        data = json.loads(content_block.text)
                        users = data.get('Users', [])
                        print(f"   Retrieved {len(users)} users")
                        if users:
                            print(f"   First user: {users[0].get('UserName')}")

            print()
            print("=" * 70)
            print("✅ ALL TESTS PASSED - Fix verified!")
            print("=" * 70)
            return True


if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
