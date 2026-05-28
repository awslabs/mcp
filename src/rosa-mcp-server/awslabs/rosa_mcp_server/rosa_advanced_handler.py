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

"""ROSA advanced and HCP-specific handler using the OCM REST API."""

import json
from awslabs.rosa_mcp_server.ocm_client import OCMClient
from mcp.server.fastmcp import Context
from mcp.types import TextContent
from typing import Optional


class RosaAdvancedHandler:
    """Handler for ROSA advanced and HCP-specific operations via OCM API."""

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

        self.mcp.tool(name='rosa_cluster_ops')(self.rosa_cluster_ops)

    async def rosa_cluster_ops(
        self,
        ctx: Context,
        cluster_id: str,
        operation: str,
        enabled: Optional[bool] = None,
        ttl: Optional[str] = None,
    ) -> list[TextContent]:
        """Advanced cluster operations: hibernate, resume, status, metrics, break-glass, delete protection, machine types.

        Args:
            ctx: MCP context.
            cluster_id: The OCM cluster ID.
            operation: One of: hibernate, resume, status, metrics, list_break_glass,
                      create_break_glass, get_delete_protection, set_delete_protection, list_machine_types.
            enabled: Delete protection enabled state (set_delete_protection only).
            ttl: TTL for break-glass credential (create_break_glass only, e.g. '24h').
        """
        if operation == 'status':
            return await self.rosa_get_cluster_status(ctx, cluster_id)
        elif operation == 'metrics':
            return await self.rosa_get_cluster_metrics(ctx, cluster_id)
        elif operation == 'list_break_glass':
            return await self.rosa_list_break_glass_credentials(ctx, cluster_id)
        elif operation == 'get_delete_protection':
            return await self.rosa_get_delete_protection(ctx, cluster_id)
        elif operation == 'list_machine_types':
            return await self.rosa_list_machine_types(ctx, cluster_id)
        elif operation == 'hibernate':
            return await self.rosa_hibernate_cluster(ctx, cluster_id)
        elif operation == 'resume':
            return await self.rosa_resume_cluster(ctx, cluster_id)
        elif operation == 'create_break_glass':
            return await self.rosa_create_break_glass_credential(ctx, cluster_id, ttl)
        elif operation == 'set_delete_protection':
            if enabled is None:
                raise ValueError('enabled is required for set_delete_protection.')
            return await self.rosa_set_delete_protection(ctx, cluster_id, enabled)
        else:
            raise ValueError(
                f'Invalid operation: {operation}. Use: hibernate, resume, status, metrics, '
                'list_break_glass, create_break_glass, get_delete_protection, '
                'set_delete_protection, list_machine_types.'
            )

    async def rosa_hibernate_cluster(
        self,
        ctx: Context,
        cluster_id: str,
    ) -> list[TextContent]:
        """Hibernate a Classic ROSA cluster to save costs.

        Args:
            ctx: MCP context.
            cluster_id: The OCM cluster ID.
        """
        if not self.allow_write:
            raise ValueError(
                'Write operations disabled. Start the server with --allow-write.'
            )

        await self.ocm.request('POST', f'/api/clusters_mgmt/v1/clusters/{cluster_id}/hibernate')
        return [TextContent(type='text', text=json.dumps({'status': 'hibernation_initiated', 'cluster_id': cluster_id}, indent=2))]

    async def rosa_resume_cluster(
        self,
        ctx: Context,
        cluster_id: str,
    ) -> list[TextContent]:
        """Resume a hibernated ROSA cluster.

        Args:
            ctx: MCP context.
            cluster_id: The OCM cluster ID.
        """
        if not self.allow_write:
            raise ValueError(
                'Write operations disabled. Start the server with --allow-write.'
            )

        await self.ocm.request('POST', f'/api/clusters_mgmt/v1/clusters/{cluster_id}/resume')
        return [TextContent(type='text', text=json.dumps({'status': 'resume_initiated', 'cluster_id': cluster_id}, indent=2))]

    async def rosa_get_cluster_status(
        self,
        ctx: Context,
        cluster_id: str,
    ) -> list[TextContent]:
        """Get cluster health and status information.

        Args:
            ctx: MCP context.
            cluster_id: The OCM cluster ID.
        """
        data = await self.ocm.request('GET', f'/api/clusters_mgmt/v1/clusters/{cluster_id}/status')
        return [TextContent(type='text', text=json.dumps(data, indent=2))]

    async def rosa_get_cluster_metrics(
        self,
        ctx: Context,
        cluster_id: str,
        metric: str = 'alerts',
    ) -> list[TextContent]:
        """Get cluster metric queries.

        Args:
            ctx: MCP context.
            cluster_id: The OCM cluster ID.
            metric: The metric type to query. Options: alerts, cluster_operators, nodes.
        """
        valid_metrics = ('alerts', 'cluster_operators', 'nodes')
        if metric not in valid_metrics:
            raise ValueError(
                f"Invalid metric '{metric}'. Must be one of: {', '.join(valid_metrics)}"
            )

        data = await self.ocm.request(
            'GET', f'/api/clusters_mgmt/v1/clusters/{cluster_id}/metric_queries/{metric}'
        )
        return [TextContent(type='text', text=json.dumps(data, indent=2))]

    async def rosa_list_break_glass_credentials(
        self,
        ctx: Context,
        cluster_id: str,
    ) -> list[TextContent]:
        """List HCP break-glass credentials for a cluster.

        Args:
            ctx: MCP context.
            cluster_id: The OCM cluster ID.
        """
        data = await self.ocm.request(
            'GET', f'/api/clusters_mgmt/v1/clusters/{cluster_id}/break_glass_credentials'
        )
        return [TextContent(type='text', text=json.dumps(data, indent=2))]

    async def rosa_create_break_glass_credential(
        self,
        ctx: Context,
        cluster_id: str,
        ttl: str = '24h',
    ) -> list[TextContent]:
        """Create an HCP break-glass credential for emergency cluster access.

        Args:
            ctx: MCP context.
            cluster_id: The OCM cluster ID.
            ttl: Time-to-live for the credential (e.g., '24h', '1h').
        """
        if not self.allow_write:
            raise ValueError(
                'Write operations disabled. Start the server with --allow-write.'
            )

        body = {
            'ttl': ttl,
        }

        data = await self.ocm.request(
            'POST', f'/api/clusters_mgmt/v1/clusters/{cluster_id}/break_glass_credentials', body=body
        )
        return [TextContent(type='text', text=json.dumps(data, indent=2))]

    async def rosa_get_delete_protection(
        self,
        ctx: Context,
        cluster_id: str,
    ) -> list[TextContent]:
        """Check the delete protection status of a cluster.

        Args:
            ctx: MCP context.
            cluster_id: The OCM cluster ID.
        """
        data = await self.ocm.request('GET', f'/api/clusters_mgmt/v1/clusters/{cluster_id}')
        delete_protection = data.get('delete_protection', {})
        result = {
            'cluster_id': cluster_id,
            'delete_protection_enabled': delete_protection.get('enabled', False),
        }
        return [TextContent(type='text', text=json.dumps(result, indent=2))]

    async def rosa_set_delete_protection(
        self,
        ctx: Context,
        cluster_id: str,
        enabled: bool,
    ) -> list[TextContent]:
        """Set the delete protection status of a cluster.

        Args:
            ctx: MCP context.
            cluster_id: The OCM cluster ID.
            enabled: Whether to enable or disable delete protection.
        """
        if not self.allow_write:
            raise ValueError(
                'Write operations disabled. Start the server with --allow-write.'
            )

        body = {
            'delete_protection': {
                'enabled': enabled,
            },
        }

        await self.ocm.request('PATCH', f'/api/clusters_mgmt/v1/clusters/{cluster_id}', body=body)
        return [TextContent(type='text', text=json.dumps({
            'status': 'delete_protection_updated',
            'cluster_id': cluster_id,
            'enabled': enabled,
        }, indent=2))]

    async def rosa_list_machine_types(
        self,
        ctx: Context,
        region: Optional[str] = None,
    ) -> list[TextContent]:
        """List available EC2 instance types for ROSA clusters.

        Args:
            ctx: MCP context.
            region: Optional AWS region to filter machine types.
        """
        path = '/api/clusters_mgmt/v1/machine_types'
        params = []
        if region:
            params.append("search=cloud_provider.id%20%3D%20'aws'")
        data = await self.ocm.request('GET', path + (f'?{"&".join(params)}' if params else ''))
        return [TextContent(type='text', text=json.dumps(data, indent=2))]
