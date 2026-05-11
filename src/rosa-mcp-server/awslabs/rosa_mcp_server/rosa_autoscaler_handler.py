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

        self.mcp.tool(name='rosa_get_autoscaler')(self.rosa_get_autoscaler)
        self.mcp.tool(name='rosa_create_autoscaler')(self.rosa_create_autoscaler)
        self.mcp.tool(name='rosa_update_autoscaler')(self.rosa_update_autoscaler)
        self.mcp.tool(name='rosa_delete_autoscaler')(self.rosa_delete_autoscaler)

    async def rosa_get_autoscaler(
        self,
        ctx: Context,
        cluster_id: str,
    ) -> list[TextContent]:
        """Get the cluster autoscaler configuration.

        Args:
            ctx: MCP context.
            cluster_id: The OCM cluster ID.
        """
        data = await self.ocm.request('GET', f'/api/clusters_mgmt/v1/clusters/{cluster_id}/autoscaler')
        return [TextContent(type='text', text=json.dumps(data, indent=2))]

    async def rosa_create_autoscaler(
        self,
        ctx: Context,
        cluster_id: str,
        min_replicas: int,
        max_replicas: int,
        scale_down_enabled: bool = True,
        scale_down_delay_after_add: str = '10m',
        scale_down_unneeded_time: str = '10m',
        scale_down_utilization_threshold: str = '0.5',
        max_pod_grace_period: int = 600,
        balance_similar_node_groups: bool = False,
        skip_nodes_with_local_storage: bool = True,
    ) -> list[TextContent]:
        """Create a cluster autoscaler configuration.

        Args:
            ctx: MCP context.
            cluster_id: The OCM cluster ID.
            min_replicas: Minimum number of replicas for autoscaling.
            max_replicas: Maximum number of replicas for autoscaling.
            scale_down_enabled: Whether scale-down is enabled.
            scale_down_delay_after_add: Delay after a scale-up before scale-down evaluation.
            scale_down_unneeded_time: Time a node must be unneeded before scale-down.
            scale_down_utilization_threshold: Utilization threshold below which nodes are candidates for scale-down.
            max_pod_grace_period: Maximum grace period in seconds for pod eviction during scale-down.
            balance_similar_node_groups: Whether to balance similar node groups.
            skip_nodes_with_local_storage: Whether to skip nodes with local storage during scale-down.
        """
        if not self.allow_write:
            raise ValueError(
                'Write operations disabled. Start the server with --allow-write.'
            )

        body = {
            'resource_limits': {
                'min_replicas': min_replicas,
                'max_replicas': max_replicas,
            },
            'scale_down': {
                'enabled': scale_down_enabled,
                'delay_after_add': scale_down_delay_after_add,
                'unneeded_time': scale_down_unneeded_time,
                'utilization_threshold': scale_down_utilization_threshold,
            },
            'max_pod_grace_period': max_pod_grace_period,
            'balance_similar_node_groups': balance_similar_node_groups,
            'skip_nodes_with_local_storage': skip_nodes_with_local_storage,
        }

        data = await self.ocm.request('POST', f'/api/clusters_mgmt/v1/clusters/{cluster_id}/autoscaler', body=body)
        return [TextContent(type='text', text=json.dumps(data, indent=2))]

    async def rosa_update_autoscaler(
        self,
        ctx: Context,
        cluster_id: str,
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
        """Update the cluster autoscaler configuration.

        Args:
            ctx: MCP context.
            cluster_id: The OCM cluster ID.
            min_replicas: Minimum number of replicas for autoscaling.
            max_replicas: Maximum number of replicas for autoscaling.
            scale_down_enabled: Whether scale-down is enabled.
            scale_down_delay_after_add: Delay after a scale-up before scale-down evaluation.
            scale_down_unneeded_time: Time a node must be unneeded before scale-down.
            scale_down_utilization_threshold: Utilization threshold below which nodes are candidates for scale-down.
            max_pod_grace_period: Maximum grace period in seconds for pod eviction during scale-down.
            balance_similar_node_groups: Whether to balance similar node groups.
            skip_nodes_with_local_storage: Whether to skip nodes with local storage during scale-down.
        """
        if not self.allow_write:
            raise ValueError(
                'Write operations disabled. Start the server with --allow-write.'
            )

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

        data = await self.ocm.request('PATCH', f'/api/clusters_mgmt/v1/clusters/{cluster_id}/autoscaler', body=body)
        return [TextContent(type='text', text=json.dumps(data, indent=2))]

    async def rosa_delete_autoscaler(
        self,
        ctx: Context,
        cluster_id: str,
    ) -> list[TextContent]:
        """Delete the cluster autoscaler configuration.

        Args:
            ctx: MCP context.
            cluster_id: The OCM cluster ID.
        """
        if not self.allow_write:
            raise ValueError(
                'Write operations disabled. Start the server with --allow-write.'
            )

        await self.ocm.request('DELETE', f'/api/clusters_mgmt/v1/clusters/{cluster_id}/autoscaler')
        return [TextContent(type='text', text=json.dumps({'status': 'autoscaler_deleted', 'cluster_id': cluster_id}, indent=2))]
