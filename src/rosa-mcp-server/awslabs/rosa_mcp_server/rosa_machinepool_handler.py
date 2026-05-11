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
    """Handler for ROSA machine pool and node pool operations."""

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

        self.mcp.tool(name='rosa_list_machinepools')(self.rosa_list_machinepools)
        self.mcp.tool(name='rosa_create_machinepool')(self.rosa_create_machinepool)
        self.mcp.tool(name='rosa_update_machinepool')(self.rosa_update_machinepool)
        self.mcp.tool(name='rosa_delete_machinepool')(self.rosa_delete_machinepool)

    async def rosa_list_machinepools(
        self,
        ctx: Context,
        cluster_id: str,
    ) -> list[TextContent]:
        """List machine pools for a ROSA cluster.

        Args:
            ctx: MCP context.
            cluster_id: The OCM cluster ID.
        """
        data = await self.ocm.list_machine_pools(cluster_id)
        return [TextContent(type='text', text=json.dumps(data, indent=2))]

    async def rosa_create_machinepool(
        self,
        ctx: Context,
        cluster_id: str,
        name: str,
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
        """Create a machine pool for a ROSA cluster.

        Args:
            ctx: MCP context.
            cluster_id: The OCM cluster ID.
            name: Machine pool name (ID).
            instance_type: EC2 instance type (e.g., m5.xlarge, r5.2xlarge).
            replicas: Fixed number of nodes. Mutually exclusive with min/max_replicas.
            min_replicas: Minimum nodes for autoscaling.
            max_replicas: Maximum nodes for autoscaling.
            labels: Node labels as key-value pairs.
            taints: Node taints as list of {key, value, effect} dicts.
                   Effect must be NoSchedule, PreferNoSchedule, or NoExecute.
            availability_zones: AZ placement list.
            subnet: Specific subnet ID for this pool.
            spot_max_price: Use Spot instances with this max price (0 = on-demand price cap).
            root_volume_size: Root volume size in GiB.
        """
        if not self.allow_write:
            raise ValueError(
                'Write operations disabled. Start the server with --allow-write.'
            )

        body: dict = {
            'id': name,
            'instance_type': instance_type,
        }

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
            body.setdefault('aws', {})
            body['root_volume'] = {'aws': {'size': root_volume_size}}

        data = await self.ocm.create_machine_pool(cluster_id, body)
        return [TextContent(type='text', text=json.dumps(data, indent=2))]

    async def rosa_update_machinepool(
        self,
        ctx: Context,
        cluster_id: str,
        pool_id: str,
        replicas: Optional[int] = None,
        min_replicas: Optional[int] = None,
        max_replicas: Optional[int] = None,
        labels: Optional[dict[str, str]] = None,
        taints: Optional[list[dict[str, str]]] = None,
    ) -> list[TextContent]:
        """Update a machine pool's configuration.

        Args:
            ctx: MCP context.
            cluster_id: The OCM cluster ID.
            pool_id: Machine pool ID to update.
            replicas: New fixed replica count (disables autoscaling).
            min_replicas: New minimum for autoscaling.
            max_replicas: New maximum for autoscaling.
            labels: Replace node labels.
            taints: Replace node taints.
        """
        if not self.allow_write:
            raise ValueError(
                'Write operations disabled. Start the server with --allow-write.'
            )

        body: dict = {}
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

        data = await self.ocm.update_machine_pool(cluster_id, pool_id, body)
        return [TextContent(type='text', text=json.dumps(data, indent=2))]

    async def rosa_delete_machinepool(
        self,
        ctx: Context,
        cluster_id: str,
        pool_id: str,
    ) -> list[TextContent]:
        """Delete a machine pool.

        Args:
            ctx: MCP context.
            cluster_id: The OCM cluster ID.
            pool_id: Machine pool ID to delete.
        """
        if not self.allow_write:
            raise ValueError(
                'Write operations disabled. Start the server with --allow-write.'
            )

        status_code = await self.ocm.delete_machine_pool(cluster_id, pool_id)
        return [TextContent(
            type='text',
            text=json.dumps({'status': 'deleted', 'pool_id': pool_id, 'http_status': status_code}),
        )]
