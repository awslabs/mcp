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

        self.mcp.tool(name='rosa_manage_addon')(self.rosa_manage_addon)

    async def rosa_manage_addon(
        self,
        ctx: Context,
        operation: str,
        cluster_id: Optional[str] = None,
        addon_id: Optional[str] = None,
        parameters: Optional[dict] = None,
    ) -> list[TextContent]:
        """Manage ROSA cluster add-ons.

        Args:
            ctx: MCP context.
            operation: One of: list_catalog, list_installed, install, uninstall.
            cluster_id: The OCM cluster ID (required for list_installed, install, uninstall).
            addon_id: Add-on ID (required for install, uninstall).
            parameters: Add-on configuration parameters (install only).
        """
        if operation == 'list_catalog':
            data = await self.ocm.request('GET', '/api/clusters_mgmt/v1/addons')
            return [TextContent(type='text', text=json.dumps(data, indent=2))]

        if not cluster_id:
            raise ValueError('cluster_id is required for this operation.')

        if operation == 'list_installed':
            data = await self.ocm.request(
                'GET', f'/api/clusters_mgmt/v1/clusters/{cluster_id}/addons'
            )
            return [TextContent(type='text', text=json.dumps(data, indent=2))]

        if not self.allow_write:
            raise ValueError(
                'Write operations disabled. Start the server with --allow-write.'
            )

        if operation == 'install':
            if not addon_id:
                raise ValueError('addon_id is required for install operation.')
            body: dict = {'addon': {'id': addon_id}}
            if parameters:
                body['parameters'] = {
                    'items': [{'id': k, 'value': v} for k, v in parameters.items()]
                }
            data = await self.ocm.request(
                'POST', f'/api/clusters_mgmt/v1/clusters/{cluster_id}/addons', body=body
            )
            return [TextContent(type='text', text=json.dumps(data, indent=2))]

        elif operation == 'uninstall':
            if not addon_id:
                raise ValueError('addon_id is required for uninstall operation.')
            await self.ocm.request(
                'DELETE', f'/api/clusters_mgmt/v1/clusters/{cluster_id}/addons/{addon_id}'
            )
            return [TextContent(type='text', text=json.dumps({
                'status': 'addon_uninstalled', 'addon_id': addon_id, 'cluster_id': cluster_id,
            }))]

        else:
            raise ValueError(
                f'Invalid operation: {operation}. '
                'Use: list_catalog, list_installed, install, uninstall.'
            )

    # Backward-compatible aliases for tests
    async def rosa_list_available_addons(self, ctx):
        """Alias."""
        return await self.rosa_manage_addon(ctx, operation='list_catalog')

    async def rosa_list_cluster_addons(self, ctx, cluster_id):
        """Alias."""
        return await self.rosa_manage_addon(ctx, operation='list_installed', cluster_id=cluster_id)

    async def rosa_install_addon(self, ctx, cluster_id, addon_id, parameters=None):
        """Alias."""
        return await self.rosa_manage_addon(ctx, operation='install', cluster_id=cluster_id, addon_id=addon_id, parameters=parameters)

    async def rosa_uninstall_addon(self, ctx, cluster_id, addon_id):
        """Alias."""
        return await self.rosa_manage_addon(ctx, operation='uninstall', cluster_id=cluster_id, addon_id=addon_id)
