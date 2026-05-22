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

"""ROSA authentication and identity provider handler using the OCM REST API."""

import base64
import json
import secrets
import string
from awslabs.rosa_mcp_server.ocm_client import OCMClient
from mcp.server.fastmcp import Context
from mcp.types import TextContent
from typing import Optional


class RosaAuthHandler:
    """Handler for ROSA authentication and identity provider operations."""

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

        self.mcp.tool(name='rosa_whoami')(self.rosa_whoami)
        self.mcp.tool(name='rosa_manage_idp')(self.rosa_manage_idp)

    @staticmethod
    def _decode_jwt_payload(token: str) -> dict:
        """Decode a JWT token payload without verification."""
        parts = token.split('.')
        if len(parts) != 3:
            raise ValueError('Invalid JWT token format')
        payload_b64 = parts[1]
        padding = 4 - len(payload_b64) % 4
        if padding != 4:
            payload_b64 += '=' * padding
        payload_bytes = base64.urlsafe_b64decode(payload_b64)
        return json.loads(payload_bytes)

    async def rosa_whoami(self, ctx: Context) -> list[TextContent]:
        """Show the current ROSA/OCM identity.

        Returns username, email, organization, and account details from the OCM token.
        """
        token = await self.ocm._ensure_token()
        payload = self._decode_jwt_payload(token)
        whoami_info = {
            'username': payload.get('username', payload.get('preferred_username', '')),
            'email': payload.get('email', ''),
            'first_name': payload.get('first_name', payload.get('given_name', '')),
            'last_name': payload.get('last_name', payload.get('family_name', '')),
            'org_id': payload.get('org_id', ''),
            'account_id': payload.get('account_id', ''),
            'is_org_admin': payload.get('is_org_admin', False),
        }
        return [TextContent(type='text', text=json.dumps(whoami_info, indent=2))]

    async def rosa_manage_idp(
        self,
        ctx: Context,
        cluster_id: str,
        operation: str,
        name: Optional[str] = None,
        idp_id: Optional[str] = None,
        idp_type: Optional[str] = None,
        mapping_method: str = 'claim',
        config: Optional[dict] = None,
    ) -> list[TextContent]:
        """Manage identity providers for a ROSA cluster.

        Args:
            ctx: MCP context.
            cluster_id: The OCM cluster ID.
            operation: One of: list, create, delete, create_admin.
            name: IDP name (required for create).
            idp_id: IDP ID (required for delete).
            idp_type: IDP type: github, google, ldap, openid, htpasswd (required for create).
            mapping_method: Identity mapping method (create only, default: claim).
            config: Type-specific config dict (create only). Examples:
                - github: {"client_id": "...", "client_secret": "...", "organizations": [...]}
                - openid: {"client_id": "...", "client_secret": "...", "issuer": "..."}
                - htpasswd: {"username": "...", "password": "..."}
        """
        if operation == 'list':
            data = await self.ocm.list_identity_providers(cluster_id)
            return [TextContent(type='text', text=json.dumps(data, indent=2))]

        if not self.allow_write:
            raise ValueError(
                'Write operations disabled. Start the server with --allow-write.'
            )

        if operation == 'create':
            if not name or not idp_type:
                raise ValueError('name and idp_type are required for create operation.')
            valid_types = ('github', 'google', 'ldap', 'openid', 'htpasswd')
            if idp_type not in valid_types:
                raise ValueError(f'Invalid idp_type: {idp_type}. Must be one of: {valid_types}')
            type_map = {
                'github': 'GithubIdentityProvider',
                'google': 'GoogleIdentityProvider',
                'ldap': 'LDAPIdentityProvider',
                'openid': 'OpenIDIdentityProvider',
                'htpasswd': 'HTPasswdIdentityProvider',
            }
            body: dict = {
                'type': type_map[idp_type],
                'name': name,
                'mapping_method': mapping_method,
            }
            if config:
                body[idp_type] = config
            data = await self.ocm.create_identity_provider(cluster_id, body)
            return [TextContent(type='text', text=json.dumps(data, indent=2))]

        elif operation == 'delete':
            if not idp_id:
                raise ValueError('idp_id is required for delete operation.')
            status_code = await self.ocm.delete_identity_provider(cluster_id, idp_id)
            return [TextContent(type='text', text=json.dumps({
                'status': 'deleted', 'idp_id': idp_id, 'http_status': status_code,
            }))]

        elif operation == 'create_admin':
            alphabet = string.ascii_letters + string.digits + '!@#$%^&*'
            password = ''.join(secrets.choice(alphabet) for _ in range(23))
            body = {
                'type': 'HTPasswdIdentityProvider',
                'name': 'cluster-admin',
                'mapping_method': 'claim',
                'htpasswd': {'username': 'cluster-admin', 'password': password},
            }
            data = await self.ocm.create_identity_provider(cluster_id, body)
            return [TextContent(type='text', text=json.dumps({
                'message': 'Cluster admin created via HTPasswd IDP.',
                'username': 'cluster-admin',
                'password': password,
                'note': 'Login with: oc login <api_url> -u cluster-admin -p <password>',
            }, indent=2))]

        else:
            raise ValueError(
                f'Invalid operation: {operation}. Use: list, create, delete, create_admin.'
            )

    # Backward-compatible aliases for tests
    async def rosa_list_idps(self, ctx, cluster_id):
        """Alias."""
        return await self.rosa_manage_idp(ctx, cluster_id, operation='list')

    async def rosa_create_idp(self, ctx, cluster_id, name='', idp_type='', **kwargs):
        """Alias."""
        return await self.rosa_manage_idp(ctx, cluster_id, operation='create', name=name, idp_type=idp_type, **kwargs)

    async def rosa_delete_idp(self, ctx, cluster_id, idp_id=''):
        """Alias."""
        return await self.rosa_manage_idp(ctx, cluster_id, operation='delete', idp_id=idp_id)

    async def rosa_create_admin(self, ctx, cluster_id):
        """Alias."""
        return await self.rosa_manage_idp(ctx, cluster_id, operation='create_admin')
