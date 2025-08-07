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

"""Core Network management tools for AWS CloudWAN MCP Server."""

from typing import Any, Dict

from mcp.server.fastmcp import FastMCP

from ..models.aws_models import CoreNetwork, CoreNetworkPolicy
from ..server import aws_config, get_aws_client, handle_aws_error, safe_json_dumps
from ..tools.base import AWSBaseTool


class CoreNetworkTools:
    """Collection of core network management tools for CloudWAN."""
    
    def __init__(self, mcp_server: FastMCP) -> None:
        """Initialize core network tools.
        
        Args:
            mcp_server: FastMCP server instance
        """
        self.mcp = mcp_server
        self._register_tools()
    
    def _register_tools(self) -> None:
        """Register all core network tools with the MCP server."""
        # Register list_core_networks tool
        @self.mcp.tool(name="list_core_networks")
        async def list_core_networks(region: str | None = None) -> str:
            """List CloudWAN core networks."""
            return await self._list_core_networks(region)
        
        # Register get_core_network_policy tool
        @self.mcp.tool(name="get_core_network_policy")
        async def get_core_network_policy(core_network_id: str, alias: str = "LIVE") -> str:
            """Retrieve the policy document for a CloudWAN Core Network."""
            return await self._get_core_network_policy(core_network_id, alias)
        
        # Register get_core_network_change_set tool
        @self.mcp.tool(name="get_core_network_change_set")
        async def get_core_network_change_set(core_network_id: str, policy_version_id: str) -> str:
            """Retrieve policy change sets for a CloudWAN Core Network."""
            return await self._get_core_network_change_set(core_network_id, policy_version_id)
        
        # Register get_core_network_change_events tool
        @self.mcp.tool(name="get_core_network_change_events")
        async def get_core_network_change_events(core_network_id: str, policy_version_id: str) -> str:
            """Retrieve change events for a CloudWAN Core Network."""
            return await self._get_core_network_change_events(core_network_id, policy_version_id)

    async def _list_core_networks(self, region: str | None = None) -> str:
        """Internal implementation for listing core networks."""
        try:
            region = region or aws_config.default_region
            client = get_aws_client("networkmanager", region)

            response = client.list_core_networks()
            core_networks = response.get("CoreNetworks", [])

            if not core_networks:
                return safe_json_dumps(
                    {
                        "success": True,
                        "region": region,
                        "message": "No CloudWAN core networks found in the specified region.",
                        "core_networks": [],
                    },
                    indent=2,
                )

            result = {
                "success": True, 
                "region": region, 
                "total_count": len(core_networks), 
                "core_networks": core_networks
            }

            return safe_json_dumps(result, indent=2)

        except Exception as e:
            return handle_aws_error(e, "list_core_networks")

    async def _get_core_network_policy(self, core_network_id: str, alias: str = "LIVE") -> str:
        """Internal implementation for retrieving core network policy."""
        try:
            client = get_aws_client("networkmanager")  # Region already handled in get_aws_client

            response = client.get_core_network_policy(CoreNetworkId=core_network_id, Alias=alias)

            policy = response.get("CoreNetworkPolicy", {})

            result = {
                "success": True,
                "core_network_id": core_network_id,
                "alias": alias,
                "policy_version_id": policy.get("PolicyVersionId"),
                "policy_document": policy.get("PolicyDocument"),
                "description": policy.get("Description"),
                "created_at": policy.get("CreatedAt").isoformat()
                if hasattr(policy.get("CreatedAt"), "isoformat")
                else policy.get("CreatedAt"),
            }

            return safe_json_dumps(result, indent=2)

        except Exception as e:
            return handle_aws_error(e, "get_core_network_policy")

    async def _get_core_network_change_set(self, core_network_id: str, policy_version_id: str) -> str:
        """Internal implementation for retrieving core network change set."""
        try:
            client = get_aws_client("networkmanager")  # Region already handled

            response = client.get_core_network_change_set(
                CoreNetworkId=core_network_id, 
                PolicyVersionId=policy_version_id
            )

            result = {
                "success": True,
                "core_network_id": core_network_id,
                "policy_version_id": policy_version_id,
                "change_sets": response.get("CoreNetworkChanges", []),
            }

            return safe_json_dumps(result, indent=2)

        except Exception as e:
            return handle_aws_error(e, "get_core_network_change_set")

    async def _get_core_network_change_events(self, core_network_id: str, policy_version_id: str) -> str:
        """Internal implementation for retrieving core network change events."""
        try:
            client = get_aws_client("networkmanager")  # Region already handled

            response = client.get_core_network_change_events(
                CoreNetworkId=core_network_id, 
                PolicyVersionId=policy_version_id
            )

            result = {
                "success": True,
                "core_network_id": core_network_id,
                "policy_version_id": policy_version_id,
                "change_events": response.get("CoreNetworkChangeEvents", []),
            }

            return safe_json_dumps(result, indent=2)

        except Exception as e:
            return handle_aws_error(e, "get_core_network_change_events")