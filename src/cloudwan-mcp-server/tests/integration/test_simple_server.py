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


"""Simplified CloudWAN MCP Server for Claude Code compatibility testing.

This is a minimal version based on the working core-mcp-server pattern.
"""

import sys
from typing import TypedDict

from mcp.server.fastmcp import FastMCP


class ContentItem(TypedDict):
    type: str
    text: str


class McpResponse(TypedDict, total=False):
    content: list[ContentItem]
    isError: bool


# Create FastMCP server with minimal configuration
mcp = FastMCP(
    "CloudWAN MCP server for AWS CloudWAN network analysis",
    dependencies=[
        "boto3",
    ],
)


@mcp.tool(name="get_global_networks")
async def get_global_networks() -> str:
    """Get AWS CloudWAN Global Networks.

    Lists all CloudWAN Global Networks in your AWS account.
    """
    try:
        # Simple implementation for testing
        import os

        import boto3

        # Get AWS session
        profile = os.getenv("AWS_PROFILE")
        region = os.getenv("AWS_DEFAULT_REGION", "us-west-2")

        if profile:
            session = boto3.Session(profile_name=profile)
        else:
            session = boto3.Session()

        client = session.client("networkmanager", region_name=region)

        # Get global networks
        response = client.describe_global_networks()
        global_networks = response.get("GlobalNetworks", [])

        if not global_networks:
            return "No CloudWAN Global Networks found in your account."

        result = f"Found {len(global_networks)} CloudWAN Global Network(s):\n\n"

        for i, gn in enumerate(global_networks, 1):
            result += f"{i}. Global Network ID: {gn.get('GlobalNetworkId', 'N/A')}\n"
            result += f"   State: {gn.get('State', 'N/A')}\n"
            result += f"   Description: {gn.get('Description', 'No description')}\n"
            result += f"   Created: {gn.get('CreatedAt', 'N/A')}\n"

            # Tags
            tags = gn.get("Tags", [])
            if tags:
                tag_str = ", ".join([f"{t.get('Key')}={t.get('Value')}" for t in tags[:3]])
                result += f"   Tags: {tag_str}\n"

            result += "\n"

        return result

    except Exception as e:
        return f"Error retrieving global networks: {str(e)}"


@mcp.tool(name="list_core_networks")
async def list_core_networks() -> str:
    """List AWS CloudWAN Core Networks.

    Lists all CloudWAN Core Networks associated with Global Networks.
    """
    try:
        import os

        import boto3

        # Get AWS session
        profile = os.getenv("AWS_PROFILE")
        region = os.getenv("AWS_DEFAULT_REGION", "us-west-2")

        if profile:
            session = boto3.Session(profile_name=profile)
        else:
            session = boto3.Session()

        client = session.client("networkmanager", region_name=region)

        # Get core networks
        response = client.describe_core_networks()
        core_networks = response.get("CoreNetworks", [])

        if not core_networks:
            return "No CloudWAN Core Networks found in your account."

        result = f"Found {len(core_networks)} CloudWAN Core Network(s):\n\n"

        for i, cn in enumerate(core_networks, 1):
            result += f"{i}. Core Network ID: {cn.get('CoreNetworkId', 'N/A')}\n"
            result += f"   State: {cn.get('State', 'N/A')}\n"
            result += f"   Global Network: {cn.get('GlobalNetworkId', 'N/A')}\n"
            result += f"   Policy Version: {cn.get('PolicyVersionId', 'N/A')}\n"
            result += f"   Created: {cn.get('CreatedAt', 'N/A')}\n"

            # Tags
            tags = cn.get("Tags", [])
            if tags:
                tag_str = ", ".join([f"{t.get('Key')}={t.get('Value')}" for t in tags[:3]])
                result += f"   Tags: {tag_str}\n"

            result += "\n"

        return result

    except Exception as e:
        return f"Error retrieving core networks: {str(e)}"


def main() -> None:
    """Run the simplified CloudWAN MCP server."""
    try:
        mcp.run()
    except KeyboardInterrupt:
        print("Server shutdown requested")
    except Exception as e:
        print(f"Server error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
