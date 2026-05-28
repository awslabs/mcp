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

"""ROSA operator handler using the OCM REST API."""

import json
from awslabs.rosa_mcp_server.ocm_client import OCMClient
from mcp.server.fastmcp import Context
from mcp.types import TextContent
from typing import Optional


class RosaOperatorHandler:
    """Handler for ROSA STS operator roles and cluster operator operations via OCM API."""

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

        self.mcp.tool(name='rosa_manage_operator')(self.rosa_manage_operator)

    async def rosa_manage_operator(
        self,
        ctx: Context,
        cluster_id: str,
        operation: str,
        operator_id: Optional[str] = None,
    ) -> list[TextContent]:
        """Manage ROSA STS operators, roles, and policies.

        Args:
            ctx: MCP context.
            cluster_id: The OCM cluster ID.
            operation: One of: list_sts_roles, get_operators, list_credential_requests,
                      list_policies, install, uninstall, get_status.
            operator_id: Operator/add-on ID (required for install, uninstall, get_status).
        """
        if operation == 'list_sts_roles':
            return await self.rosa_list_sts_operator_roles(ctx, cluster_id)
        elif operation == 'get_operators':
            return await self.rosa_get_cluster_operators(ctx, cluster_id)
        elif operation == 'list_credential_requests':
            return await self.rosa_list_sts_credential_requests(ctx, cluster_id)
        elif operation == 'list_policies':
            return await self.rosa_list_sts_policies(ctx, cluster_id)
        elif operation == 'install':
            return await self.rosa_install_operator(ctx, cluster_id, operator_id)
        elif operation == 'uninstall':
            return await self.rosa_uninstall_operator(ctx, cluster_id, operator_id)
        elif operation == 'get_status':
            return await self.rosa_get_operator_status(ctx, cluster_id, operator_id)
        else:
            raise ValueError(
                f'Invalid operation: {operation}. Use: list_sts_roles, get_operators, '
                'list_credential_requests, list_policies, install, uninstall, get_status.'
            )

    async def rosa_list_sts_operator_roles(
        self,
        ctx: Context,
        cluster_id: str,
    ) -> list[TextContent]:
        """List STS operator IAM roles for a cluster (name, namespace, role_arn).

        Args:
            ctx: MCP context.
            cluster_id: The OCM cluster ID.
        """
        data = await self.ocm.request(
            'GET', f'/api/clusters_mgmt/v1/clusters/{cluster_id}/sts_operator_roles'
        )
        return [TextContent(type='text', text=json.dumps(data, indent=2))]

    async def rosa_get_cluster_operators(
        self,
        ctx: Context,
        cluster_id: str,
    ) -> list[TextContent]:
        """Get status of all cluster operators (available/degraded/progressing).

        Args:
            ctx: MCP context.
            cluster_id: The OCM cluster ID.
        """
        data = await self.ocm.request(
            'GET', f'/api/clusters_mgmt/v1/clusters/{cluster_id}/metric_queries/cluster_operators'
        )
        return [TextContent(type='text', text=json.dumps(data, indent=2))]

    async def rosa_list_sts_credential_requests(
        self,
        ctx: Context,
    ) -> list[TextContent]:
        """List required STS credential request templates (what roles need to be created).

        Args:
            ctx: MCP context.
        """
        data = await self.ocm.request(
            'GET', '/api/clusters_mgmt/v1/aws_inquiries/sts_credential_requests'
        )
        return [TextContent(type='text', text=json.dumps(data, indent=2))]

    async def rosa_list_sts_policies(
        self,
        ctx: Context,
    ) -> list[TextContent]:
        """List all available STS IAM policies (operator, account, backup roles).

        Args:
            ctx: MCP context.
        """
        data = await self.ocm.request(
            'GET', '/api/clusters_mgmt/v1/aws_inquiries/sts_policies'
        )
        return [TextContent(type='text', text=json.dumps(data, indent=2))]

    async def rosa_install_operator(
        self,
        ctx: Context,
        cluster_id: str,
        addon_id: str,
        parameters: Optional[dict] = None,
    ) -> list[TextContent]:
        """Install an operator/add-on on the cluster.

        Args:
            ctx: MCP context.
            cluster_id: The OCM cluster ID.
            addon_id: The operator/add-on ID to install.
            parameters: Optional operator configuration parameters.
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

        data = await self.ocm.request(
            'POST', f'/api/clusters_mgmt/v1/clusters/{cluster_id}/addons', body=body
        )
        return [TextContent(type='text', text=json.dumps(data, indent=2))]

    async def rosa_uninstall_operator(
        self,
        ctx: Context,
        cluster_id: str,
        addon_id: str,
    ) -> list[TextContent]:
        """Uninstall an operator/add-on from the cluster.

        Args:
            ctx: MCP context.
            cluster_id: The OCM cluster ID.
            addon_id: The operator/add-on ID to uninstall.
        """
        if not self.allow_write:
            raise ValueError(
                'Write operations disabled. Start the server with --allow-write.'
            )

        await self.ocm.request(
            'DELETE', f'/api/clusters_mgmt/v1/clusters/{cluster_id}/addons/{addon_id}'
        )
        return [TextContent(type='text', text=json.dumps({
            'status': 'operator_uninstalled',
            'addon_id': addon_id,
            'cluster_id': cluster_id,
        }, indent=2))]

    async def rosa_get_operator_status(
        self,
        ctx: Context,
        cluster_id: str,
        addon_id: str,
    ) -> list[TextContent]:
        """Get installation status of a specific operator/add-on.

        Args:
            ctx: MCP context.
            cluster_id: The OCM cluster ID.
            addon_id: The operator/add-on ID to check.
        """
        data = await self.ocm.request(
            'GET', f'/api/clusters_mgmt/v1/clusters/{cluster_id}/addons/{addon_id}'
        )
        return [TextContent(type='text', text=json.dumps(data, indent=2))]
