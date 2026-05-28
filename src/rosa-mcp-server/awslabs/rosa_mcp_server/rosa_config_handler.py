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

"""ROSA tuning and kubelet config handler using the OCM REST API."""

import json
from awslabs.rosa_mcp_server.ocm_client import OCMClient
from mcp.server.fastmcp import Context
from mcp.types import TextContent
from typing import Optional


class RosaConfigHandler:
    """Handler for ROSA tuning and kubelet configuration operations via OCM API."""

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

        self.mcp.tool(name='rosa_manage_config')(self.rosa_manage_config)

    async def rosa_manage_config(
        self,
        ctx: Context,
        cluster_id: str,
        operation: str,
        config_id: Optional[str] = None,
        name: Optional[str] = None,
        spec: Optional[dict] = None,
        pod_pids_limit: Optional[int] = None,
    ) -> list[TextContent]:
        """Manage ROSA cluster tuning and kubelet configuration.

        Args:
            ctx: MCP context.
            cluster_id: The OCM cluster ID.
            operation: One of: list_tuning, create_tuning, delete_tuning, get_kubelet, update_kubelet.
            config_id: Tuning config ID (required for delete_tuning).
            name: Tuning config name (required for create_tuning).
            spec: Tuning config content/sysctl params (required for create_tuning).
            pod_pids_limit: Max PIDs per pod (update_kubelet).
        """
        base = f'/api/clusters_mgmt/v1/clusters/{cluster_id}'

        if operation == 'list_tuning':
            data = await self.ocm.request('GET', f'{base}/tuning_configs')
            return [TextContent(type='text', text=json.dumps(data, indent=2))]

        elif operation == 'get_kubelet':
            data = await self.ocm.request('GET', f'{base}/kubelet_config')
            return [TextContent(type='text', text=json.dumps(data, indent=2))]

        if not self.allow_write:
            raise ValueError(
                'Write operations disabled. Start the server with --allow-write.'
            )

        if operation == 'create_tuning':
            if not name or not spec:
                raise ValueError('name and spec are required for create_tuning.')
            data = await self.ocm.request(
                'POST', f'{base}/tuning_configs', body={'name': name, 'spec': spec}
            )
            return [TextContent(type='text', text=json.dumps(data, indent=2))]

        elif operation == 'delete_tuning':
            if not config_id:
                raise ValueError('config_id is required for delete_tuning.')
            await self.ocm.request('DELETE', f'{base}/tuning_configs/{config_id}')
            return [TextContent(type='text', text=json.dumps({
                'status': 'tuning_config_deleted', 'config_id': config_id,
            }))]

        elif operation == 'update_kubelet':
            body: dict = {}
            if pod_pids_limit is not None:
                body['pod_pids_limit'] = pod_pids_limit
            data = await self.ocm.request('PATCH', f'{base}/kubelet_config', body=body)
            return [TextContent(type='text', text=json.dumps(data, indent=2))]

        else:
            raise ValueError(
                f'Invalid operation: {operation}. '
                'Use: list_tuning, create_tuning, delete_tuning, get_kubelet, update_kubelet.'
            )

    # Backward-compatible aliases for tests
    async def rosa_list_tuning_configs(self, ctx, cluster_id):
        """Alias."""
        return await self.rosa_manage_config(ctx, cluster_id, operation='list_tuning')

    async def rosa_create_tuning_config(self, ctx, cluster_id, name='', spec=None):
        """Alias."""
        return await self.rosa_manage_config(ctx, cluster_id, operation='create_tuning', name=name, spec=spec)

    async def rosa_delete_tuning_config(self, ctx, cluster_id, config_id=''):
        """Alias."""
        return await self.rosa_manage_config(ctx, cluster_id, operation='delete_tuning', config_id=config_id)

    async def rosa_get_kubelet_config(self, ctx, cluster_id):
        """Alias."""
        return await self.rosa_manage_config(ctx, cluster_id, operation='get_kubelet')

    async def rosa_update_kubelet_config(self, ctx, cluster_id, **kwargs):
        """Alias."""
        return await self.rosa_manage_config(ctx, cluster_id, operation='update_kubelet', **kwargs)
