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

"""ROSA user/group management handler using the OCM REST API."""

import json
from awslabs.rosa_mcp_server.ocm_client import OCMClient
from mcp.server.fastmcp import Context
from mcp.types import TextContent
from typing import Optional


class RosaUserHandler:
    """Handler for ROSA user and group management via OCM API."""

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

        self.mcp.tool(name='rosa_manage_user')(self.rosa_manage_user)

    async def rosa_manage_user(
        self,
        ctx: Context,
        cluster_id: str,
        operation: str,
        username: Optional[str] = None,
        group: str = 'dedicated-admins',
    ) -> list[TextContent]:
        """Manage cluster users and admin groups.

        Args:
            ctx: MCP context.
            cluster_id: The OCM cluster ID.
            operation: One of: list, grant, revoke.
            username: Username to grant/revoke (required for grant, revoke).
            group: Group name: 'dedicated-admins' or 'cluster-admins' (default: dedicated-admins).
        """
        base_path = f'/api/clusters_mgmt/v1/clusters/{cluster_id}/groups'

        if operation == 'list':
            groups_data = await self.ocm.request('GET', base_path)
            result = []
            for g in groups_data.get('items', []):
                group_id = g.get('id', '')
                users_data = await self.ocm.request('GET', f'{base_path}/{group_id}/users')
                result.append({
                    'group': group_id,
                    'users': users_data.get('items', []),
                })
            return [TextContent(type='text', text=json.dumps({
                'cluster_id': cluster_id, 'groups': result,
            }, indent=2))]

        if not self.allow_write:
            raise ValueError(
                'Write operations disabled. Start the server with --allow-write.'
            )
        if not username:
            raise ValueError('username is required for grant/revoke operations.')

        if operation == 'grant':
            await self.ocm.request(
                'POST', f'{base_path}/{group}/users', body={'id': username}
            )
            return [TextContent(type='text', text=json.dumps({
                'status': 'granted', 'username': username, 'group': group,
            }))]

        elif operation == 'revoke':
            await self.ocm.request('DELETE', f'{base_path}/{group}/users/{username}')
            return [TextContent(type='text', text=json.dumps({
                'status': 'revoked', 'username': username, 'group': group,
            }))]

        else:
            raise ValueError(f'Invalid operation: {operation}. Use: list, grant, revoke.')

    # Backward-compatible aliases for tests
    async def rosa_list_users(self, ctx, cluster_id):
        """Alias."""
        return await self.rosa_manage_user(ctx, cluster_id, operation='list')

    async def rosa_grant_user(self, ctx, cluster_id, username, group='dedicated-admins'):
        """Alias."""
        return await self.rosa_manage_user(ctx, cluster_id, operation='grant', username=username, group=group)

    async def rosa_revoke_user(self, ctx, cluster_id, username, group='dedicated-admins'):
        """Alias."""
        return await self.rosa_manage_user(ctx, cluster_id, operation='revoke', username=username, group=group)
