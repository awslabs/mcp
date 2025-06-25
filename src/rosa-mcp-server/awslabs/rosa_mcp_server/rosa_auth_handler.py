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

"""ROSA authentication and identity provider handler for the ROSA MCP Server."""

import json
import subprocess
from awslabs.rosa_mcp_server.aws_helper import AwsHelper
from awslabs.rosa_mcp_server.consts import (
    IDP_TYPES,
    ROSA_ACCOUNT_ROLE_PREFIX,
    ROSA_OPERATOR_ROLE_PREFIX,
)
from awslabs.rosa_mcp_server.logging_helper import LogLevel, log_with_request_id
from awslabs.rosa_mcp_server.models import (
    AccountRolesResponse,
    IdentityProviderListResponse,
    IdentityProviderResponse,
    IdentityProviderSummary,
    OIDCProviderResponse,
    OperatorRolesResponse,
)
from loguru import logger
from mcp.server.fastmcp import Context, FastMCP
from mcp.types import CallToolResult
from pydantic import Field
from typing import Dict, List, Optional


class ROSAAuthHandler:
    """Handler for ROSA authentication and identity provider operations."""

    def __init__(self, mcp: FastMCP, allow_write: bool = False):
        """Initialize the ROSA auth handler."""
        self.mcp = mcp
        self.allow_write = allow_write
        self._register_tools()

    def _register_tools(self):
        """Register ROSA auth tools with the MCP server."""
        
        # Setup account roles
        @self.mcp.tool()
        async def setup_rosa_account_roles(
            ctx: Context,
            prefix: str = Field(ROSA_ACCOUNT_ROLE_PREFIX, description='Prefix for IAM role names'),
            mode: str = Field('auto', description='Mode for role creation (auto or manual)'),
        ) -> AccountRolesResponse:
            """Set up ROSA account-wide IAM roles.

            This tool creates the required IAM roles for ROSA installation. These roles
            are account-wide and can be shared across multiple ROSA clusters.

            Args:
                ctx: MCP context
                prefix: Prefix for IAM role names
                mode: Creation mode - 'auto' or 'manual'

            Returns:
                AccountRolesResponse with created role ARNs

            Example:
                setup_rosa_account_roles()
            """
            if not self.allow_write:
                return CallToolResult(
                    success=False,
                    content='Write access is required to create IAM roles. Run with --allow-write flag.'
                )
            
            log_with_request_id(ctx, LogLevel.INFO, 'Setting up ROSA account roles', prefix=prefix)
            
            try:
                cmd = [
                    'rosa', 'create', 'account-roles',
                    '--mode', mode,
                    '--prefix', prefix,
                    '--yes'
                ]
                
                result = subprocess.run(cmd, capture_output=True, text=True, check=True)
                
                # Parse the output to get role ARNs
                # In a real implementation, we would parse the actual output
                # For now, we'll construct the expected ARNs
                account_id = AwsHelper.create_boto3_client('sts').get_caller_identity()['Account']
                
                return AccountRolesResponse(
                    installer_role_arn=f'arn:aws:iam::{account_id}:role/{prefix}-Installer-Role',
                    control_plane_role_arn=f'arn:aws:iam::{account_id}:role/{prefix}-ControlPlane-Role',
                    worker_role_arn=f'arn:aws:iam::{account_id}:role/{prefix}-Worker-Role',
                    support_role_arn=f'arn:aws:iam::{account_id}:role/{prefix}-Support-Role',
                    success=True,
                    content='Successfully created ROSA account roles'
                )
                
            except subprocess.CalledProcessError as e:
                error_msg = f'Failed to create account roles: {e.stderr}'
                log_with_request_id(ctx, LogLevel.ERROR, error_msg)
                return CallToolResult(success=False, content=error_msg)

        # Create operator roles
        @self.mcp.tool()
        async def create_rosa_operator_roles(
            ctx: Context,
            cluster_name: str = Field(..., description='Name of the ROSA cluster'),
            prefix: Optional[str] = Field(None, description='Custom prefix for operator roles'),
        ) -> OperatorRolesResponse:
            """Create operator-specific IAM roles for a ROSA cluster.

            This tool creates the IAM roles required for ROSA operators to function.
            These roles are specific to a single cluster.

            Args:
                ctx: MCP context
                cluster_name: Name of the ROSA cluster
                prefix: Optional custom prefix for role names

            Returns:
                OperatorRolesResponse with created role ARNs

            Example:
                create_rosa_operator_roles(cluster_name="my-cluster")
            """
            if not self.allow_write:
                return CallToolResult(
                    success=False,
                    content='Write access is required to create operator roles. Run with --allow-write flag.'
                )
            
            log_with_request_id(ctx, LogLevel.INFO, 'Creating ROSA operator roles', 
                              cluster_name=cluster_name)
            
            try:
                cmd = [
                    'rosa', 'create', 'operator-roles',
                    '--cluster', cluster_name,
                    '--mode', 'auto',
                    '--yes'
                ]
                
                if prefix:
                    cmd.extend(['--prefix', prefix])
                
                result = subprocess.run(cmd, capture_output=True, text=True, check=True)
                
                # Parse output to get created roles
                # In practice, we'd parse the actual rosa output
                operator_roles = []
                for line in result.stdout.split('\n'):
                    if 'role' in line.lower() and 'arn:aws:iam' in line:
                        # Extract ARN from line
                        parts = line.split()
                        for part in parts:
                            if part.startswith('arn:aws:iam'):
                                operator_roles.append(part)
                                break
                
                return OperatorRolesResponse(
                    cluster_name=cluster_name,
                    operator_roles=operator_roles,
                    success=True,
                    content=f'Successfully created {len(operator_roles)} operator roles'
                )
                
            except subprocess.CalledProcessError as e:
                error_msg = f'Failed to create operator roles: {e.stderr}'
                log_with_request_id(ctx, LogLevel.ERROR, error_msg)
                return CallToolResult(success=False, content=error_msg)

        # Create OIDC provider
        @self.mcp.tool()
        async def create_rosa_oidc_provider(
            ctx: Context,
            cluster_name: str = Field(..., description='Name of the ROSA cluster'),
        ) -> OIDCProviderResponse:
            """Create an OIDC provider for a ROSA cluster.

            This tool creates an OpenID Connect (OIDC) provider in IAM for the ROSA cluster.
            This is required for STS-based clusters to enable pod identity.

            Args:
                ctx: MCP context
                cluster_name: Name of the ROSA cluster

            Returns:
                OIDCProviderResponse with OIDC provider details

            Example:
                create_rosa_oidc_provider(cluster_name="my-cluster")
            """
            if not self.allow_write:
                return CallToolResult(
                    success=False,
                    content='Write access is required to create OIDC provider. Run with --allow-write flag.'
                )
            
            log_with_request_id(ctx, LogLevel.INFO, 'Creating ROSA OIDC provider', 
                              cluster_name=cluster_name)
            
            try:
                cmd = [
                    'rosa', 'create', 'oidc-provider',
                    '--cluster', cluster_name,
                    '--mode', 'auto',
                    '--yes'
                ]
                
                result = subprocess.run(cmd, capture_output=True, text=True, check=True)
                
                # Get OIDC endpoint from cluster details
                describe_cmd = ['rosa', 'describe', 'cluster', '--cluster', cluster_name, '--output', 'json']
                describe_result = subprocess.run(describe_cmd, capture_output=True, text=True, check=True)
                cluster_data = json.loads(describe_result.stdout) if describe_result.stdout else {}
                
                oidc_endpoint = cluster_data.get('aws', {}).get('sts', {}).get('oidc_endpoint_url', '')
                
                # Construct OIDC provider ARN
                account_id = AwsHelper.create_boto3_client('sts').get_caller_identity()['Account']
                oidc_provider_arn = f"arn:aws:iam::{account_id}:oidc-provider/{oidc_endpoint.replace('https://', '')}"
                
                return OIDCProviderResponse(
                    cluster_name=cluster_name,
                    oidc_endpoint=oidc_endpoint,
                    oidc_provider_arn=oidc_provider_arn,
                    operation='create',
                    success=True,
                    content='Successfully created OIDC provider'
                )
                
            except subprocess.CalledProcessError as e:
                error_msg = f'Failed to create OIDC provider: {e.stderr}'
                log_with_request_id(ctx, LogLevel.ERROR, error_msg)
                return CallToolResult(success=False, content=error_msg)

        # List identity providers
        @self.mcp.tool()
        async def list_rosa_idps(
            ctx: Context,
            cluster_name: str = Field(..., description='Name of the ROSA cluster'),
        ) -> IdentityProviderListResponse:
            """List all identity providers configured for a ROSA cluster.

            This tool lists all identity providers (IDPs) that have been configured
            for user authentication in the cluster.

            Args:
                ctx: MCP context
                cluster_name: Name of the cluster

            Returns:
                IdentityProviderListResponse with list of IDPs

            Example:
                list_rosa_idps(cluster_name="my-cluster")
            """
            log_with_request_id(ctx, LogLevel.INFO, 'Listing identity providers', 
                              cluster_name=cluster_name)
            
            try:
                cmd = ['rosa', 'list', 'idps', '--cluster', cluster_name, '--output', 'json']
                result = subprocess.run(cmd, capture_output=True, text=True, check=True)
                idps_data = json.loads(result.stdout) if result.stdout else []
                
                idps = []
                for idp in idps_data:
                    idp_summary = IdentityProviderSummary(
                        name=idp.get('name', ''),
                        type=idp.get('type', ''),
                        mapping_method=idp.get('mapping_method', 'claim'),
                        challenge=idp.get('challenge', True)
                    )
                    idps.append(idp_summary)
                
                return IdentityProviderListResponse(
                    cluster_name=cluster_name,
                    count=len(idps),
                    idps=idps,
                    success=True,
                    content=f'Found {len(idps)} identity providers'
                )
                
            except subprocess.CalledProcessError as e:
                error_msg = f'Failed to list identity providers: {e.stderr}'
                log_with_request_id(ctx, LogLevel.ERROR, error_msg)
                return IdentityProviderListResponse(
                    cluster_name=cluster_name,
                    count=0,
                    idps=[],
                    success=False,
                    content=error_msg
                )

        # Create identity provider
        @self.mcp.tool()
        async def create_rosa_idp(
            ctx: Context,
            cluster_name: str = Field(..., description='Name of the ROSA cluster'),
            type: str = Field(..., description=f'Type of identity provider: {", ".join(IDP_TYPES)}'),
            name: str = Field(..., description='Name for the identity provider'),
            client_id: Optional[str] = Field(None, description='OAuth client ID (for OAuth-based IDPs)'),
            client_secret: Optional[str] = Field(None, description='OAuth client secret (for OAuth-based IDPs)'),
            organizations: Optional[List[str]] = Field(None, description='GitHub organizations (for GitHub IDP)'),
            hosted_domain: Optional[str] = Field(None, description='Google hosted domain (for Google IDP)'),
            ldap_url: Optional[str] = Field(None, description='LDAP server URL (for LDAP IDP)'),
            ldap_bind_dn: Optional[str] = Field(None, description='LDAP bind DN (for LDAP IDP)'),
            ldap_bind_password: Optional[str] = Field(None, description='LDAP bind password (for LDAP IDP)'),
            issuer_url: Optional[str] = Field(None, description='OpenID issuer URL (for OpenID IDP)'),
        ) -> IdentityProviderResponse:
            """Create a new identity provider for a ROSA cluster.

            This tool configures an identity provider for user authentication.
            Different IDP types require different parameters.

            Args:
                ctx: MCP context
                cluster_name: Name of the cluster
                type: Type of IDP (github, gitlab, google, ldap, openid, htpasswd)
                name: Name for the IDP
                client_id: OAuth client ID (for OAuth providers)
                client_secret: OAuth client secret (for OAuth providers)
                organizations: GitHub organizations to allow (GitHub only)
                hosted_domain: Google Apps domain (Google only)
                ldap_url: LDAP server URL (LDAP only)
                ldap_bind_dn: LDAP bind DN (LDAP only)
                ldap_bind_password: LDAP bind password (LDAP only)
                issuer_url: OpenID issuer URL (OpenID only)

            Returns:
                IdentityProviderResponse with created IDP details

            Example:
                # GitHub IDP
                create_rosa_idp(
                    cluster_name="my-cluster",
                    type="github",
                    name="github-auth",
                    client_id="abc123",
                    client_secret="secret123",
                    organizations=["my-org"]
                )
                
                # LDAP IDP
                create_rosa_idp(
                    cluster_name="my-cluster",
                    type="ldap",
                    name="ldap-auth",
                    ldap_url="ldaps://ldap.example.com",
                    ldap_bind_dn="cn=admin,dc=example,dc=com",
                    ldap_bind_password="password"
                )
            """
            if not self.allow_write:
                return CallToolResult(
                    success=False,
                    content='Write access is required to create identity providers. Run with --allow-write flag.'
                )
            
            if type not in IDP_TYPES:
                return CallToolResult(
                    success=False,
                    content=f'Invalid IDP type. Must be one of: {", ".join(IDP_TYPES)}'
                )
            
            log_with_request_id(ctx, LogLevel.INFO, 'Creating identity provider', 
                              cluster_name=cluster_name, type=type, name=name)
            
            try:
                cmd = [
                    'rosa', 'create', 'idp',
                    '--cluster', cluster_name,
                    '--type', type,
                    '--name', name
                ]
                
                # Add type-specific parameters
                if type == 'github':
                    if not client_id or not client_secret:
                        return CallToolResult(
                            success=False,
                            content='GitHub IDP requires client_id and client_secret'
                        )
                    cmd.extend(['--client-id', client_id, '--client-secret', client_secret])
                    if organizations:
                        cmd.extend(['--organizations', ','.join(organizations)])
                
                elif type == 'gitlab':
                    if not client_id or not client_secret:
                        return CallToolResult(
                            success=False,
                            content='GitLab IDP requires client_id and client_secret'
                        )
                    cmd.extend(['--client-id', client_id, '--client-secret', client_secret])
                
                elif type == 'google':
                    if not client_id or not client_secret:
                        return CallToolResult(
                            success=False,
                            content='Google IDP requires client_id and client_secret'
                        )
                    cmd.extend(['--client-id', client_id, '--client-secret', client_secret])
                    if hosted_domain:
                        cmd.extend(['--hosted-domain', hosted_domain])
                
                elif type == 'ldap':
                    if not ldap_url:
                        return CallToolResult(
                            success=False,
                            content='LDAP IDP requires ldap_url'
                        )
                    cmd.extend(['--url', ldap_url])
                    if ldap_bind_dn:
                        cmd.extend(['--bind-dn', ldap_bind_dn])
                    if ldap_bind_password:
                        cmd.extend(['--bind-password', ldap_bind_password])
                
                elif type == 'openid':
                    if not client_id or not client_secret or not issuer_url:
                        return CallToolResult(
                            success=False,
                            content='OpenID IDP requires client_id, client_secret, and issuer_url'
                        )
                    cmd.extend([
                        '--client-id', client_id,
                        '--client-secret', client_secret,
                        '--issuer-url', issuer_url
                    ])
                
                result = subprocess.run(cmd, capture_output=True, text=True, check=True)
                
                idp_summary = IdentityProviderSummary(
                    name=name,
                    type=type,
                    mapping_method='claim',
                    challenge=True
                )
                
                return IdentityProviderResponse(
                    idp=idp_summary,
                    cluster_name=cluster_name,
                    operation='create',
                    success=True,
                    content=f'Successfully created {type} identity provider {name}'
                )
                
            except subprocess.CalledProcessError as e:
                error_msg = f'Failed to create identity provider: {e.stderr}'
                log_with_request_id(ctx, LogLevel.ERROR, error_msg)
                return CallToolResult(success=False, content=error_msg)

        # Delete identity provider
        @self.mcp.tool()
        async def delete_rosa_idp(
            ctx: Context,
            cluster_name: str = Field(..., description='Name of the ROSA cluster'),
            name: str = Field(..., description='Name of the identity provider to delete'),
        ) -> CallToolResult:
            """Delete an identity provider from a ROSA cluster.

            This tool removes an identity provider configuration from the cluster.

            Args:
                ctx: MCP context
                cluster_name: Name of the cluster
                name: Name of the IDP to delete

            Returns:
                CallToolResult indicating success or failure

            Example:
                delete_rosa_idp(cluster_name="my-cluster", name="github-auth")
            """
            if not self.allow_write:
                return CallToolResult(
                    success=False,
                    content='Write access is required to delete identity providers. Run with --allow-write flag.'
                )
            
            log_with_request_id(ctx, LogLevel.INFO, 'Deleting identity provider', 
                              cluster_name=cluster_name, name=name)
            
            try:
                cmd = [
                    'rosa', 'delete', 'idp',
                    '--cluster', cluster_name,
                    name,
                    '--yes'
                ]
                
                result = subprocess.run(cmd, capture_output=True, text=True, check=True)
                
                return CallToolResult(
                    success=True,
                    content=f'Successfully deleted identity provider {name}'
                )
                
            except subprocess.CalledProcessError as e:
                error_msg = f'Failed to delete identity provider {name}: {e.stderr}'
                log_with_request_id(ctx, LogLevel.ERROR, error_msg)
                return CallToolResult(success=False, content=error_msg)

        # Create admin user
        @self.mcp.tool()
        async def create_rosa_admin(
            ctx: Context,
            cluster_name: str = Field(..., description='Name of the ROSA cluster'),
        ) -> CallToolResult:
            """Create a cluster-admin user for a ROSA cluster.

            This tool creates a temporary cluster-admin user for emergency access.
            The credentials will expire after 24 hours.

            Args:
                ctx: MCP context
                cluster_name: Name of the cluster

            Returns:
                CallToolResult with admin credentials

            Example:
                create_rosa_admin(cluster_name="my-cluster")
            """
            if not self.allow_write:
                return CallToolResult(
                    success=False,
                    content='Write access is required to create admin users. Run with --allow-write flag.'
                )
            
            log_with_request_id(ctx, LogLevel.INFO, 'Creating cluster admin', 
                              cluster_name=cluster_name)
            
            try:
                cmd = ['rosa', 'create', 'admin', '--cluster', cluster_name, '--yes']
                
                result = subprocess.run(cmd, capture_output=True, text=True, check=True)
                
                # Parse credentials from output
                output_lines = result.stdout.split('\n')
                credentials_info = []
                
                for line in output_lines:
                    if 'username:' in line.lower() or 'password:' in line.lower() or 'api url:' in line.lower():
                        credentials_info.append(line.strip())
                
                return CallToolResult(
                    success=True,
                    content='\n'.join(credentials_info) + '\n\nNote: These credentials expire after 24 hours.'
                )
                
            except subprocess.CalledProcessError as e:
                error_msg = f'Failed to create admin user: {e.stderr}'
                log_with_request_id(ctx, LogLevel.ERROR, error_msg)
                return CallToolResult(success=False, content=error_msg)

        # Grant user access
        @self.mcp.tool()
        async def grant_rosa_user_access(
            ctx: Context,
            cluster_name: str = Field(..., description='Name of the ROSA cluster'),
            username: str = Field(..., description='Username to grant access to'),
            role: str = Field('dedicated-admin', description='Role to grant (dedicated-admin or cluster-admin)'),
        ) -> CallToolResult:
            """Grant a user access to a ROSA cluster.

            This tool grants cluster access to a user who has authenticated through
            an identity provider.

            Args:
                ctx: MCP context
                cluster_name: Name of the cluster
                username: Username from the identity provider
                role: Role to grant (dedicated-admin or cluster-admin)

            Returns:
                CallToolResult indicating success or failure

            Example:
                grant_rosa_user_access(
                    cluster_name="my-cluster",
                    username="john.doe",
                    role="cluster-admin"
                )
            """
            if not self.allow_write:
                return CallToolResult(
                    success=False,
                    content='Write access is required to grant user access. Run with --allow-write flag.'
                )
            
            log_with_request_id(ctx, LogLevel.INFO, 'Granting user access', 
                              cluster_name=cluster_name, username=username, role=role)
            
            try:
                cmd = [
                    'rosa', 'grant', 'user',
                    role,
                    '--user', username,
                    '--cluster', cluster_name,
                    '--yes'
                ]
                
                result = subprocess.run(cmd, capture_output=True, text=True, check=True)
                
                return CallToolResult(
                    success=True,
                    content=f'Successfully granted {role} access to user {username}'
                )
                
            except subprocess.CalledProcessError as e:
                error_msg = f'Failed to grant user access: {e.stderr}'
                log_with_request_id(ctx, LogLevel.ERROR, error_msg)
                return CallToolResult(success=False, content=error_msg)