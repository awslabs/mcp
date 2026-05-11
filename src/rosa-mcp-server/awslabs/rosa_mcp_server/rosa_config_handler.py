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

        self.mcp.tool(name='rosa_list_tuning_configs')(self.rosa_list_tuning_configs)
        self.mcp.tool(name='rosa_create_tuning_config')(self.rosa_create_tuning_config)
        self.mcp.tool(name='rosa_delete_tuning_config')(self.rosa_delete_tuning_config)
        self.mcp.tool(name='rosa_get_kubelet_config')(self.rosa_get_kubelet_config)
        self.mcp.tool(name='rosa_update_kubelet_config')(self.rosa_update_kubelet_config)

    async def rosa_list_tuning_configs(
        self,
        ctx: Context,
        cluster_id: str,
    ) -> list[TextContent]:
        """List tuning configurations for a cluster.

        Args:
            ctx: MCP context.
            cluster_id: The OCM cluster ID.
        """
        data = await self.ocm.request(
            'GET', f'/api/clusters_mgmt/v1/clusters/{cluster_id}/tuning_configs'
        )
        return [TextContent(type='text', text=json.dumps(data, indent=2))]

    async def rosa_create_tuning_config(
        self,
        ctx: Context,
        cluster_id: str,
        name: str,
        spec: dict,
    ) -> list[TextContent]:
        """Create a tuning configuration for a cluster.

        Args:
            ctx: MCP context.
            cluster_id: The OCM cluster ID.
            name: Name of the tuning configuration.
            spec: The tuning configuration content (sysctl parameters, etc.).
        """
        if not self.allow_write:
            raise ValueError(
                'Write operations disabled. Start the server with --allow-write.'
            )

        body = {
            'name': name,
            'spec': spec,
        }

        data = await self.ocm.request(
            'POST', f'/api/clusters_mgmt/v1/clusters/{cluster_id}/tuning_configs', body=body
        )
        return [TextContent(type='text', text=json.dumps(data, indent=2))]

    async def rosa_delete_tuning_config(
        self,
        ctx: Context,
        cluster_id: str,
        config_id: str,
    ) -> list[TextContent]:
        """Delete a tuning configuration from a cluster.

        Args:
            ctx: MCP context.
            cluster_id: The OCM cluster ID.
            config_id: The tuning configuration ID to delete.
        """
        if not self.allow_write:
            raise ValueError(
                'Write operations disabled. Start the server with --allow-write.'
            )

        await self.ocm.request(
            'DELETE', f'/api/clusters_mgmt/v1/clusters/{cluster_id}/tuning_configs/{config_id}'
        )
        return [TextContent(type='text', text=json.dumps({
            'status': 'tuning_config_deleted',
            'config_id': config_id,
            'cluster_id': cluster_id,
        }, indent=2))]

    async def rosa_get_kubelet_config(
        self,
        ctx: Context,
        cluster_id: str,
    ) -> list[TextContent]:
        """Get the kubelet configuration for a cluster.

        Args:
            ctx: MCP context.
            cluster_id: The OCM cluster ID.
        """
        data = await self.ocm.request(
            'GET', f'/api/clusters_mgmt/v1/clusters/{cluster_id}/kubelet_config'
        )
        return [TextContent(type='text', text=json.dumps(data, indent=2))]

    async def rosa_update_kubelet_config(
        self,
        ctx: Context,
        cluster_id: str,
        pod_pids_limit: Optional[int] = None,
    ) -> list[TextContent]:
        """Update the kubelet configuration for a cluster.

        Args:
            ctx: MCP context.
            cluster_id: The OCM cluster ID.
            pod_pids_limit: Maximum number of PIDs per pod.
        """
        if not self.allow_write:
            raise ValueError(
                'Write operations disabled. Start the server with --allow-write.'
            )

        body: dict = {}
        if pod_pids_limit is not None:
            body['pod_pids_limit'] = pod_pids_limit

        data = await self.ocm.request(
            'PATCH', f'/api/clusters_mgmt/v1/clusters/{cluster_id}/kubelet_config', body=body
        )
        return [TextContent(type='text', text=json.dumps(data, indent=2))]
