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

"""ROSA machine pool and node pool handler using the OCM REST API."""

import json
from awslabs.rosa_mcp_server.ocm_client import OCMClient
from mcp.server.fastmcp import Context
from mcp.types import TextContent
from typing import Optional


class RosaMachinePoolHandler:
    """Handler for ROSA machine pool and node pool operations.

    Automatically detects HCP (Hosted Control Plane) vs Classic clusters
    and uses the correct API endpoint (node_pools vs machine_pools).
    """

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

        self.mcp.tool(name='rosa_manage_machinepool')(self.rosa_manage_machinepool)

    async def _is_hcp(self, cluster_id: str) -> bool:
        """Check if a cluster is HCP (Hosted Control Plane)."""
        cluster = await self.ocm.get_cluster(cluster_id)
        return cluster.get('hypershift', {}).get('enabled', False)

    async def rosa_manage_machinepool(
        self,
        ctx: Context,
        cluster_id: str,
        operation: str,
        pool_id: Optional[str] = None,
        instance_type: str = 'm5.xlarge',
        replicas: Optional[int] = None,
        min_replicas: Optional[int] = None,
        max_replicas: Optional[int] = None,
        labels: Optional[dict[str, str]] = None,
        taints: Optional[list[dict[str, str]]] = None,
        availability_zones: Optional[list[str]] = None,
        subnet: Optional[str] = None,
        spot_max_price: Optional[float] = None,
        root_volume_size: Optional[int] = None,
    ) -> list[TextContent]:
        """Manage machine/node pools for a ROSA cluster.

        Auto-detects HCP vs Classic and uses the correct endpoint.

        Args:
            ctx: MCP context.
            cluster_id: The OCM cluster ID.
            operation: One of: list, create, update, delete.
            pool_id: Pool ID (required for create, update, delete).
            instance_type: EC2 instance type (create only, default: m5.xlarge).
            replicas: Fixed node count. Mutually exclusive with min/max_replicas.
            min_replicas: Minimum nodes for autoscaling.
            max_replicas: Maximum nodes for autoscaling.
            labels: Node labels as key-value pairs.
            taints: Node taints as list of {key, value, effect} dicts.
            availability_zones: AZ placement list (create only).
            subnet: Specific subnet ID (create only).
            spot_max_price: Use Spot instances with this max price (create only).
            root_volume_size: Root volume size in GiB (create only).
        """
        if operation == 'list':
            if await self._is_hcp(cluster_id):
                data = await self.ocm.list_node_pools(cluster_id)
            else:
                data = await self.ocm.list_machine_pools(cluster_id)
            return [TextContent(type='text', text=json.dumps(data, indent=2))]

        if not self.allow_write:
            raise ValueError(
                'Write operations disabled. Start the server with --allow-write.'
            )

        if operation == 'create':
            if not pool_id:
                raise ValueError('pool_id is required for create operation.')
            body: dict = {'id': pool_id, 'instance_type': instance_type}
            if min_replicas is not None and max_replicas is not None:
                body['autoscaling'] = {
                    'min_replicas': min_replicas,
                    'max_replicas': max_replicas,
                }
            else:
                body['replicas'] = replicas or 2
            if labels:
                body['labels'] = labels
            if taints:
                body['taints'] = taints
            if availability_zones:
                body['availability_zones'] = availability_zones
            if subnet:
                body['subnets'] = [subnet]
            if spot_max_price is not None:
                body['aws'] = {'spot_market_options': {'max_price': spot_max_price}}
            if root_volume_size:
                body['root_volume'] = {'aws': {'size': root_volume_size}}

            if await self._is_hcp(cluster_id):
                body['aws_node_pool'] = {'instance_type': body.pop('instance_type')}
                data = await self.ocm.create_node_pool(cluster_id, body)
            else:
                data = await self.ocm.create_machine_pool(cluster_id, body)
            return [TextContent(type='text', text=json.dumps(data, indent=2))]

        elif operation == 'update':
            if not pool_id:
                raise ValueError('pool_id is required for update operation.')
            body = {}
            if min_replicas is not None and max_replicas is not None:
                body['autoscaling'] = {
                    'min_replicas': min_replicas,
                    'max_replicas': max_replicas,
                }
            elif replicas is not None:
                body['replicas'] = replicas
            if labels is not None:
                body['labels'] = labels
            if taints is not None:
                body['taints'] = taints

            if await self._is_hcp(cluster_id):
                data = await self.ocm.update_node_pool(cluster_id, pool_id, body)
            else:
                data = await self.ocm.update_machine_pool(cluster_id, pool_id, body)
            return [TextContent(type='text', text=json.dumps(data, indent=2))]

        elif operation == 'delete':
            if not pool_id:
                raise ValueError('pool_id is required for delete operation.')
            if await self._is_hcp(cluster_id):
                status_code = await self.ocm.delete_node_pool(cluster_id, pool_id)
            else:
                status_code = await self.ocm.delete_machine_pool(cluster_id, pool_id)
            return [TextContent(
                type='text',
                text=json.dumps({
                    'status': 'deleted', 'pool_id': pool_id, 'http_status': status_code,
                }),
            )]

        else:
            raise ValueError(f'Invalid operation: {operation}. Use: list, create, update, delete.')

    # Backward-compatible aliases for tests
    async def rosa_list_machinepools(self, ctx, cluster_id):
        """Alias for rosa_manage_machinepool(operation='list')."""
        return await self.rosa_manage_machinepool(ctx, cluster_id, operation='list')

    async def rosa_create_machinepool(self, ctx, cluster_id, name='', **kwargs):
        """Alias for rosa_manage_machinepool(operation='create')."""
        return await self.rosa_manage_machinepool(ctx, cluster_id, operation='create', pool_id=name, **kwargs)

    async def rosa_update_machinepool(self, ctx, cluster_id, pool_id='', **kwargs):
        """Alias for rosa_manage_machinepool(operation='update')."""
        return await self.rosa_manage_machinepool(ctx, cluster_id, operation='update', pool_id=pool_id, **kwargs)

    async def rosa_delete_machinepool(self, ctx, cluster_id, pool_id=''):
        """Alias for rosa_manage_machinepool(operation='delete')."""
        return await self.rosa_manage_machinepool(ctx, cluster_id, operation='delete', pool_id=pool_id)
