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

"""ROSA networking and ingress handler using the OCM REST API."""

import json
from awslabs.rosa_mcp_server.ocm_client import OCMClient
from mcp.server.fastmcp import Context
from mcp.types import TextContent
from typing import Optional


class RosaNetworkingHandler:
    """Handler for ROSA networking and ingress operations via OCM API."""

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

        self.mcp.tool(name='rosa_list_ingresses')(self.rosa_list_ingresses)
        self.mcp.tool(name='rosa_create_ingress')(self.rosa_create_ingress)
        self.mcp.tool(name='rosa_update_ingress')(self.rosa_update_ingress)
        self.mcp.tool(name='rosa_delete_ingress')(self.rosa_delete_ingress)

    async def rosa_list_ingresses(
        self,
        ctx: Context,
        cluster_id: str,
    ) -> list[TextContent]:
        """List ingress controllers for a ROSA cluster.

        Args:
            ctx: MCP context.
            cluster_id: The OCM cluster ID.
        """
        data = await self.ocm.list_ingresses(cluster_id)
        return [TextContent(type='text', text=json.dumps(data, indent=2))]

    async def rosa_create_ingress(
        self,
        ctx: Context,
        cluster_id: str,
        private: bool = False,
        lb_type: str = 'classic',
        route_selectors: Optional[dict[str, str]] = None,
        excluded_namespaces: Optional[list[str]] = None,
    ) -> list[TextContent]:
        """Create a new ingress controller for a ROSA cluster.

        Args:
            ctx: MCP context.
            cluster_id: The OCM cluster ID.
            private: Make the ingress private (internal-facing only).
            lb_type: Load balancer type: 'nlb' or 'classic'.
            route_selectors: Route label selectors as key-value pairs.
            excluded_namespaces: List of namespaces to exclude from this ingress.
        """
        if not self.allow_write:
            raise ValueError(
                'Write operations disabled. Start the server with --allow-write.'
            )

        body: dict = {
            'listening': 'internal' if private else 'external',
        }

        if lb_type:
            body['load_balancer_type'] = lb_type

        if route_selectors:
            body['route_selectors'] = route_selectors

        if excluded_namespaces:
            body['excluded_namespaces'] = excluded_namespaces

        data = await self.ocm.create_ingress(cluster_id, body)
        return [TextContent(type='text', text=json.dumps(data, indent=2))]

    async def rosa_update_ingress(
        self,
        ctx: Context,
        cluster_id: str,
        ingress_id: str,
        private: Optional[bool] = None,
        lb_type: Optional[str] = None,
        route_selectors: Optional[dict[str, str]] = None,
        excluded_namespaces: Optional[list[str]] = None,
    ) -> list[TextContent]:
        """Update an ingress controller for a ROSA cluster.

        Args:
            ctx: MCP context.
            cluster_id: The OCM cluster ID.
            ingress_id: The ingress ID to update.
            private: Set the ingress to private (internal) or public (external).
            lb_type: Load balancer type: 'nlb' or 'classic'.
            route_selectors: Route label selectors as key-value pairs.
            excluded_namespaces: List of namespaces to exclude from this ingress.
        """
        if not self.allow_write:
            raise ValueError(
                'Write operations disabled. Start the server with --allow-write.'
            )

        body: dict = {}

        if private is not None:
            body['listening'] = 'internal' if private else 'external'

        if lb_type is not None:
            body['load_balancer_type'] = lb_type

        if route_selectors is not None:
            body['route_selectors'] = route_selectors

        if excluded_namespaces is not None:
            body['excluded_namespaces'] = excluded_namespaces

        data = await self.ocm.update_ingress(cluster_id, ingress_id, body)
        return [TextContent(type='text', text=json.dumps(data, indent=2))]

    async def rosa_delete_ingress(
        self,
        ctx: Context,
        cluster_id: str,
        ingress_id: str,
    ) -> list[TextContent]:
        """Delete an ingress controller from a ROSA cluster.

        Args:
            ctx: MCP context.
            cluster_id: The OCM cluster ID.
            ingress_id: The ingress ID to delete.
        """
        if not self.allow_write:
            raise ValueError(
                'Write operations disabled. Start the server with --allow-write.'
            )

        status_code = await self.ocm.delete_ingress(cluster_id, ingress_id)
        return [TextContent(
            type='text',
            text=json.dumps({
                'status': 'deleted',
                'ingress_id': ingress_id,
                'http_status': status_code,
            }),
        )]
