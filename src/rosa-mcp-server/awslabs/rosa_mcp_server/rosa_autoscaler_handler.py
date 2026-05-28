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

"""ROSA cluster autoscaler handler using the OCM REST API."""

import json
from awslabs.rosa_mcp_server.ocm_client import OCMClient
from mcp.server.fastmcp import Context
from mcp.types import TextContent
from typing import Optional


class RosaAutoscalerHandler:
    """Handler for ROSA cluster autoscaler operations via OCM API."""

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

        self.mcp.tool(name='rosa_manage_autoscaler')(self.rosa_manage_autoscaler)

    async def rosa_manage_autoscaler(
        self,
        ctx: Context,
        cluster_id: str,
        operation: str,
        min_replicas: Optional[int] = None,
        max_replicas: Optional[int] = None,
        scale_down_enabled: Optional[bool] = None,
        scale_down_delay_after_add: Optional[str] = None,
        scale_down_unneeded_time: Optional[str] = None,
        scale_down_utilization_threshold: Optional[str] = None,
        max_pod_grace_period: Optional[int] = None,
        balance_similar_node_groups: Optional[bool] = None,
        skip_nodes_with_local_storage: Optional[bool] = None,
    ) -> list[TextContent]:
        """Manage the cluster autoscaler configuration.

        Args:
            ctx: MCP context.
            cluster_id: The OCM cluster ID.
            operation: One of: get, create, update, delete.
            min_replicas: Minimum replicas (create, update).
            max_replicas: Maximum replicas (create, update).
            scale_down_enabled: Enable scale-down (create, update).
            scale_down_delay_after_add: Delay after scale-up before scale-down (create, update).
            scale_down_unneeded_time: Time node must be unneeded (create, update).
            scale_down_utilization_threshold: Utilization threshold for scale-down (create, update).
            max_pod_grace_period: Max pod eviction grace period in seconds (create, update).
            balance_similar_node_groups: Balance similar node groups (create, update).
            skip_nodes_with_local_storage: Skip nodes with local storage (create, update).
        """
        base_path = f'/api/clusters_mgmt/v1/clusters/{cluster_id}/autoscaler'

        if operation == 'get':
            data = await self.ocm.request('GET', base_path)
            return [TextContent(type='text', text=json.dumps(data, indent=2))]

        if not self.allow_write:
            raise ValueError(
                'Write operations disabled. Start the server with --allow-write.'
            )

        if operation == 'delete':
            await self.ocm.request('DELETE', base_path)
            return [TextContent(type='text', text=json.dumps({
                'status': 'autoscaler_deleted', 'cluster_id': cluster_id,
            }))]

        # Build body for create/update
        body: dict = {}
        resource_limits: dict = {}
        scale_down: dict = {}

        if min_replicas is not None:
            resource_limits['min_replicas'] = min_replicas
        if max_replicas is not None:
            resource_limits['max_replicas'] = max_replicas
        if resource_limits:
            body['resource_limits'] = resource_limits

        if scale_down_enabled is not None:
            scale_down['enabled'] = scale_down_enabled
        if scale_down_delay_after_add is not None:
            scale_down['delay_after_add'] = scale_down_delay_after_add
        if scale_down_unneeded_time is not None:
            scale_down['unneeded_time'] = scale_down_unneeded_time
        if scale_down_utilization_threshold is not None:
            scale_down['utilization_threshold'] = scale_down_utilization_threshold
        if scale_down:
            body['scale_down'] = scale_down

        if max_pod_grace_period is not None:
            body['max_pod_grace_period'] = max_pod_grace_period
        if balance_similar_node_groups is not None:
            body['balance_similar_node_groups'] = balance_similar_node_groups
        if skip_nodes_with_local_storage is not None:
            body['skip_nodes_with_local_storage'] = skip_nodes_with_local_storage

        if operation == 'create':
            data = await self.ocm.request('POST', base_path, body=body)
        elif operation == 'update':
            data = await self.ocm.request('PATCH', base_path, body=body)
        else:
            raise ValueError(f'Invalid operation: {operation}. Use: get, create, update, delete.')

        return [TextContent(type='text', text=json.dumps(data, indent=2))]

    # Backward-compatible aliases for tests
    async def rosa_get_autoscaler(self, ctx, cluster_id):
        """Alias."""
        return await self.rosa_manage_autoscaler(ctx, cluster_id, operation='get')

    async def rosa_create_autoscaler(self, ctx, cluster_id, **kwargs):
        """Alias."""
        return await self.rosa_manage_autoscaler(ctx, cluster_id, operation='create', **kwargs)

    async def rosa_update_autoscaler(self, ctx, cluster_id, **kwargs):
        """Alias."""
        return await self.rosa_manage_autoscaler(ctx, cluster_id, operation='update', **kwargs)

    async def rosa_delete_autoscaler(self, ctx, cluster_id):
        """Alias."""
        return await self.rosa_manage_autoscaler(ctx, cluster_id, operation='delete')
