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

"""ROSA add-on handler using the OCM REST API."""

import json
from awslabs.rosa_mcp_server.ocm_client import OCMClient
from mcp.server.fastmcp import Context
from mcp.types import TextContent
from typing import Optional


class RosaAddonHandler:
    """Handler for ROSA add-on operations via OCM API."""

    def __init__(self, mcp, ocm_client: OCMClient, allow_write: bool = False):
        """Initialize the handler.

        Args:
            mcp: The FastMCP server instance.
            ocm_client: Shared OCM API client.
            allow_write: Whether write operations are permitted.
        """
        self.mcp = mcp
        self.ocm = ocm_client
        self.allow_write = allow_write

        self.mcp.tool(name='rosa_list_available_addons')(self.rosa_list_available_addons)
        self.mcp.tool(name='rosa_list_cluster_addons')(self.rosa_list_cluster_addons)
        self.mcp.tool(name='rosa_install_addon')(self.rosa_install_addon)
        self.mcp.tool(name='rosa_uninstall_addon')(self.rosa_uninstall_addon)

    async def rosa_list_available_addons(
        self,
        ctx: Context,
    ) -> list[TextContent]:
        """List all available add-ons from the OCM catalog.

        Args:
            ctx: MCP context.
        """
        data = await self.ocm.request('GET', '/api/clusters_mgmt/v1/addons')
        return [TextContent(type='text', text=json.dumps(data, indent=2))]

    async def rosa_list_cluster_addons(
        self,
        ctx: Context,
        cluster_id: str,
    ) -> list[TextContent]:
        """List installed add-ons on a cluster.

        Args:
            ctx: MCP context.
            cluster_id: The OCM cluster ID.
        """
        data = await self.ocm.request('GET', f'/api/clusters_mgmt/v1/clusters/{cluster_id}/addons')
        return [TextContent(type='text', text=json.dumps(data, indent=2))]

    async def rosa_install_addon(
        self,
        ctx: Context,
        cluster_id: str,
        addon_id: str,
        parameters: Optional[dict] = None,
    ) -> list[TextContent]:
        """Install an add-on on a cluster.

        Args:
            ctx: MCP context.
            cluster_id: The OCM cluster ID.
            addon_id: The add-on ID to install.
            parameters: Optional add-on configuration parameters.
        """
        if not self.allow_write:
            raise ValueError(
                'Write operations disabled. Start the server with --allow-write.'
            )

        body: dict = {
            'addon': {'id': addon_id},
        }

        if parameters:
            body['parameters'] = {
                'items': [{'id': k, 'value': v} for k, v in parameters.items()]
            }

        data = await self.ocm.request('POST', f'/api/clusters_mgmt/v1/clusters/{cluster_id}/addons', body=body)
        return [TextContent(type='text', text=json.dumps(data, indent=2))]

    async def rosa_uninstall_addon(
        self,
        ctx: Context,
        cluster_id: str,
        addon_id: str,
    ) -> list[TextContent]:
        """Uninstall an add-on from a cluster.

        Args:
            ctx: MCP context.
            cluster_id: The OCM cluster ID.
            addon_id: The add-on ID to uninstall.
        """
        if not self.allow_write:
            raise ValueError(
                'Write operations disabled. Start the server with --allow-write.'
            )

        await self.ocm.request('DELETE', f'/api/clusters_mgmt/v1/clusters/{cluster_id}/addons/{addon_id}')
        return [TextContent(type='text', text=json.dumps({'status': 'addon_uninstalled', 'addon_id': addon_id, 'cluster_id': cluster_id}, indent=2))]
