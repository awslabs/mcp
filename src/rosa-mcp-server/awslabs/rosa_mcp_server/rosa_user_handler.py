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

"""ROSA user and group handler using the OCM REST API."""

import json
from awslabs.rosa_mcp_server.ocm_client import OCMClient
from mcp.server.fastmcp import Context
from mcp.types import TextContent


class RosaUserHandler:
    """Handler for ROSA user and group operations via OCM API."""

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

        self.mcp.tool(name='rosa_list_users')(self.rosa_list_users)
        self.mcp.tool(name='rosa_grant_user')(self.rosa_grant_user)
        self.mcp.tool(name='rosa_revoke_user')(self.rosa_revoke_user)

    async def rosa_list_users(
        self,
        ctx: Context,
        cluster_id: str,
    ) -> list[TextContent]:
        """List groups and users on a ROSA cluster.

        Args:
            ctx: MCP context.
            cluster_id: The OCM cluster ID.
        """
        groups_data = await self.ocm.request('GET', f'/api/clusters_mgmt/v1/clusters/{cluster_id}/groups')
        result = {'cluster_id': cluster_id, 'groups': []}

        groups = groups_data.get('items', [])
        for group in groups:
            group_id = group.get('id', '')
            users_data = await self.ocm.request(
                'GET', f'/api/clusters_mgmt/v1/clusters/{cluster_id}/groups/{group_id}/users'
            )
            result['groups'].append({
                'group': group_id,
                'users': users_data.get('items', []),
            })

        return [TextContent(type='text', text=json.dumps(result, indent=2))]

    async def rosa_grant_user(
        self,
        ctx: Context,
        cluster_id: str,
        username: str,
        group: str = 'dedicated-admins',
    ) -> list[TextContent]:
        """Grant a user membership to a group on the cluster.

        Args:
            ctx: MCP context.
            cluster_id: The OCM cluster ID.
            username: The username to grant access.
            group: The group to add the user to ('dedicated-admins' or 'cluster-admins').
        """
        if not self.allow_write:
            raise ValueError(
                'Write operations disabled. Start the server with --allow-write.'
            )

        if group not in ('dedicated-admins', 'cluster-admins'):
            raise ValueError(
                f"Invalid group '{group}'. Must be 'dedicated-admins' or 'cluster-admins'."
            )

        body = {
            'id': username,
        }

        data = await self.ocm.request(
            'POST', f'/api/clusters_mgmt/v1/clusters/{cluster_id}/groups/{group}/users', body=body
        )
        return [TextContent(type='text', text=json.dumps(data, indent=2))]

    async def rosa_revoke_user(
        self,
        ctx: Context,
        cluster_id: str,
        username: str,
        group: str = 'dedicated-admins',
    ) -> list[TextContent]:
        """Revoke a user's membership from a group on the cluster.

        Args:
            ctx: MCP context.
            cluster_id: The OCM cluster ID.
            username: The username to revoke access from.
            group: The group to remove the user from ('dedicated-admins' or 'cluster-admins').
        """
        if not self.allow_write:
            raise ValueError(
                'Write operations disabled. Start the server with --allow-write.'
            )

        if group not in ('dedicated-admins', 'cluster-admins'):
            raise ValueError(
                f"Invalid group '{group}'. Must be 'dedicated-admins' or 'cluster-admins'."
            )

        await self.ocm.request(
            'DELETE', f'/api/clusters_mgmt/v1/clusters/{cluster_id}/groups/{group}/users/{username}'
        )
        return [TextContent(type='text', text=json.dumps({
            'status': 'user_revoked',
            'username': username,
            'group': group,
            'cluster_id': cluster_id,
        }, indent=2))]
