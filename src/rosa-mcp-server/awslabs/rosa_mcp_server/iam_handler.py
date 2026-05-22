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

"""IAM and service quota handler for the ROSA MCP Server.

Uses boto3 directly for all AWS IAM and Service Quotas operations.
Does NOT require the OCM client.
"""

import boto3
import json
from mcp.server.fastmcp import Context
from mcp.types import TextContent
from typing import Optional


class IAMHandler:
    """Handler for IAM roles, OIDC providers, and service quota verification for ROSA."""

    def __init__(
        self,
        mcp,
        allow_sensitive_data_access: bool = False,
        allow_write: bool = False,
    ):
        """Initialize the IAM handler.

        Args:
            mcp: The FastMCP server instance.
            allow_sensitive_data_access: Whether sensitive data access is permitted.
            allow_write: Whether write operations are permitted.
        """
        self.mcp = mcp
        self.allow_sensitive_data_access = allow_sensitive_data_access
        self.allow_write = allow_write

        self.mcp.tool(name='rosa_manage_iam')(self.rosa_manage_iam)

    async def rosa_manage_iam(
        self,
        ctx: Context,
        operation: str,
        prefix: Optional[str] = None,
        cluster_name: Optional[str] = None,
        role_name: Optional[str] = None,
        policy_name: Optional[str] = None,
        policy_document: Optional[dict] = None,
        region: Optional[str] = None,
    ) -> list[TextContent]:
        """Manage ROSA IAM roles, OIDC providers, and service quotas.

        Args:
            ctx: MCP context.
            operation: One of: list_account_roles, list_operator_roles, list_oidc_providers,
                      verify_quota, get_policies_for_role, add_inline_policy.
            prefix: Filter roles by prefix (list_account_roles).
            cluster_name: Filter operator roles by cluster (list_operator_roles).
            role_name: IAM role name (get_policies_for_role, add_inline_policy).
            policy_name: Inline policy name (add_inline_policy).
            policy_document: Policy document dict (add_inline_policy).
            region: AWS region.
        """
        if operation == 'list_account_roles':
            return await self.rosa_get_account_roles(ctx, prefix, region)
        elif operation == 'list_operator_roles':
            return await self.rosa_get_operator_roles(ctx, cluster_name, region)
        elif operation == 'list_oidc_providers':
            return await self.rosa_list_oidc_providers(ctx, region)
        elif operation == 'verify_quota':
            return await self.rosa_verify_quota(ctx, region)
        elif operation == 'get_policies_for_role':
            if not role_name:
                raise ValueError('role_name is required for get_policies_for_role.')
            return await self.rosa_get_policies_for_role(ctx, role_name, region)
        elif operation == 'add_inline_policy':
            if not role_name or not policy_name or not policy_document:
                raise ValueError(
                    'role_name, policy_name, and policy_document are required for add_inline_policy.'
                )
            return await self.rosa_add_inline_policy(ctx, role_name, policy_name, policy_document, region)
        else:
            raise ValueError(
                f'Invalid operation: {operation}. Use: list_account_roles, list_operator_roles, '
                'list_oidc_providers, verify_quota, get_policies_for_role, add_inline_policy.'
            )

    async def rosa_get_account_roles(
        self,
        ctx: Context,
        prefix: Optional[str] = None,
        region: Optional[str] = None,
    ) -> list[TextContent]:
        """List ROSA account-level IAM roles.

        Filters roles by ManagedOpenShift-* naming pattern or ROSA-related tags.

        Args:
            ctx: MCP context.
            prefix: Filter roles by prefix (default matches ManagedOpenShift-*).
            region: AWS region. If omitted, uses default from environment.
        """
        try:
            kwargs = {}
            if region:
                kwargs['region_name'] = region

            iam_client = boto3.client('iam', **kwargs)
            paginator = iam_client.get_paginator('list_roles')

            rosa_roles = []
            for page in paginator.paginate():
                for role in page['Roles']:
                    role_name = role['RoleName']

                    # Match ROSA account roles by name pattern or tags
                    is_rosa_role = (
                        role_name.startswith('ManagedOpenShift-')
                        or 'ROSA' in role_name
                        or any(
                            tag.get('Key') in ('rosa_managed', 'red-hat-managed')
                            for tag in role.get('Tags', [])
                        )
                    )

                    if not is_rosa_role:
                        continue
                    if prefix and not role_name.startswith(prefix):
                        continue

                    rosa_roles.append({
                        'RoleName': role_name,
                        'RoleId': role['RoleId'],
                        'Arn': role['Arn'],
                        'CreateDate': role.get('CreateDate', ''),
                        'Description': role.get('Description', ''),
                    })

            return [TextContent(
                type='text',
                text=json.dumps({
                    'role_count': len(rosa_roles),
                    'roles': rosa_roles,
                }, default=str),
            )]

        except Exception as e:
            return [TextContent(
                type='text',
                text=f'Error listing account roles: {str(e)}',
            )]

    async def rosa_get_operator_roles(
        self,
        ctx: Context,
        cluster_name: Optional[str] = None,
        region: Optional[str] = None,
    ) -> list[TextContent]:
        """List ROSA operator IAM roles.

        Filters roles used by ROSA cluster operators (ingress, storage,
        image-registry, networking, cloud-credentials).

        Args:
            ctx: MCP context.
            cluster_name: Cluster name to filter operator roles for a specific cluster.
            region: AWS region. If omitted, uses default from environment.
        """
        try:
            kwargs = {}
            if region:
                kwargs['region_name'] = region

            iam_client = boto3.client('iam', **kwargs)
            paginator = iam_client.get_paginator('list_roles')

            operator_keywords = [
                'openshift-ingress',
                'openshift-image-registry',
                'openshift-cluster-csi',
                'openshift-cloud-network',
                'openshift-machine-api',
                'openshift-cloud-credential',
            ]

            operator_roles = []
            for page in paginator.paginate():
                for role in page['Roles']:
                    role_name = role['RoleName']

                    is_operator_role = any(
                        keyword in role_name for keyword in operator_keywords
                    )

                    if not is_operator_role:
                        continue
                    if cluster_name and cluster_name not in role_name:
                        continue

                    operator_roles.append({
                        'RoleName': role_name,
                        'RoleId': role['RoleId'],
                        'Arn': role['Arn'],
                        'CreateDate': role.get('CreateDate', ''),
                    })

            return [TextContent(
                type='text',
                text=json.dumps({
                    'role_count': len(operator_roles),
                    'roles': operator_roles,
                }, default=str),
            )]

        except Exception as e:
            return [TextContent(
                type='text',
                text=f'Error listing operator roles: {str(e)}',
            )]

    async def rosa_list_oidc_providers(
        self,
        ctx: Context,
        region: Optional[str] = None,
    ) -> list[TextContent]:
        """List OIDC providers related to OpenShift/ROSA.

        Filters OIDC providers by those containing 'openshift' in the URL.

        Args:
            ctx: MCP context.
            region: AWS region. If omitted, uses default from environment.
        """
        try:
            kwargs = {}
            if region:
                kwargs['region_name'] = region

            iam_client = boto3.client('iam', **kwargs)
            response = iam_client.list_open_id_connect_providers()

            rosa_providers = []
            for provider in response.get('OpenIDConnectProviderList', []):
                arn = provider['Arn']
                # Get details to check if it is OpenShift related
                detail = iam_client.get_open_id_connect_provider(
                    OpenIDConnectProviderArn=arn
                )
                url = detail.get('Url', '')
                if 'openshift' in url.lower() or 'rosa' in url.lower():
                    rosa_providers.append({
                        'Arn': arn,
                        'Url': url,
                        'CreateDate': detail.get('CreateDate', ''),
                        'ClientIDList': detail.get('ClientIDList', []),
                        'ThumbprintList': detail.get('ThumbprintList', []),
                    })

            return [TextContent(
                type='text',
                text=json.dumps({
                    'provider_count': len(rosa_providers),
                    'providers': rosa_providers,
                }, default=str),
            )]

        except Exception as e:
            return [TextContent(
                type='text',
                text=f'Error listing OIDC providers: {str(e)}',
            )]

    async def rosa_verify_quota(
        self,
        ctx: Context,
        region: Optional[str] = None,
    ) -> list[TextContent]:
        """Verify that the AWS account has sufficient service quota for ROSA.

        Checks EC2 vCPUs, EBS volumes, VPC, and ELB quotas against ROSA requirements.

        Args:
            ctx: MCP context.
            region: AWS region to verify quota in.
        """
        try:
            kwargs = {}
            if region:
                kwargs['region_name'] = region

            sq_client = boto3.client('service-quotas', **kwargs)

            # ROSA minimum requirements
            quota_checks = [
                {
                    'service_code': 'ec2',
                    'quota_code': 'L-1216C47A',  # Running On-Demand Standard instances
                    'name': 'EC2 vCPUs (Standard)',
                    'minimum': 100,
                },
                {
                    'service_code': 'ebs',
                    'quota_code': 'L-D18FCD1D',  # General Purpose SSD (gp2) volume storage
                    'name': 'EBS GP2/GP3 Storage (TiB)',
                    'minimum': 50,
                },
                {
                    'service_code': 'vpc',
                    'quota_code': 'L-F678F1CE',  # VPCs per Region
                    'name': 'VPCs per Region',
                    'minimum': 5,
                },
                {
                    'service_code': 'elasticloadbalancing',
                    'quota_code': 'L-53DA6B97',  # Application Load Balancers per Region
                    'name': 'Load Balancers per Region',
                    'minimum': 20,
                },
                {
                    'service_code': 'ec2',
                    'quota_code': 'L-0263D0A3',  # Elastic IP addresses
                    'name': 'Elastic IPs',
                    'minimum': 5,
                },
            ]

            results = []
            all_sufficient = True

            for check in quota_checks:
                try:
                    response = sq_client.get_service_quota(
                        ServiceCode=check['service_code'],
                        QuotaCode=check['quota_code'],
                    )
                    quota = response.get('Quota', {})
                    current_value = quota.get('Value', 0)
                    sufficient = current_value >= check['minimum']
                    if not sufficient:
                        all_sufficient = False

                    results.append({
                        'name': check['name'],
                        'current_quota': current_value,
                        'minimum_required': check['minimum'],
                        'sufficient': sufficient,
                    })
                except Exception as quota_err:
                    results.append({
                        'name': check['name'],
                        'error': str(quota_err),
                        'sufficient': None,
                    })

            return [TextContent(
                type='text',
                text=json.dumps({
                    'all_sufficient': all_sufficient,
                    'region': region or 'default',
                    'quotas': results,
                }, default=str),
            )]

        except Exception as e:
            return [TextContent(
                type='text',
                text=f'Error verifying quotas: {str(e)}',
            )]

    async def rosa_get_policies_for_role(
        self,
        ctx: Context,
        role_name: str,
        region: Optional[str] = None,
    ) -> list[TextContent]:
        """List all policies (managed and inline) attached to an IAM role.

        Args:
            ctx: MCP context.
            role_name: The IAM role name.
            region: AWS region. If omitted, uses default from environment.
        """
        try:
            kwargs = {}
            if region:
                kwargs['region_name'] = region

            iam_client = boto3.client('iam', **kwargs)

            # Get managed policies
            managed_paginator = iam_client.get_paginator('list_attached_role_policies')
            managed_policies = []
            for page in managed_paginator.paginate(RoleName=role_name):
                managed_policies.extend(page.get('AttachedPolicies', []))

            # Get inline policy names
            inline_paginator = iam_client.get_paginator('list_role_policies')
            inline_policies = []
            for page in inline_paginator.paginate(RoleName=role_name):
                inline_policies.extend(page.get('PolicyNames', []))

            return [TextContent(
                type='text',
                text=json.dumps({
                    'role_name': role_name,
                    'managed_policies': managed_policies,
                    'inline_policies': inline_policies,
                    'total_managed': len(managed_policies),
                    'total_inline': len(inline_policies),
                }, default=str),
            )]

        except Exception as e:
            return [TextContent(
                type='text',
                text=f'Error listing policies for role {role_name}: {str(e)}',
            )]

    async def rosa_add_inline_policy(
        self,
        ctx: Context,
        role_name: str,
        policy_name: str,
        policy_document: dict,
        region: Optional[str] = None,
    ) -> list[TextContent]:
        """Add an inline IAM policy to a role.

        Args:
            ctx: MCP context.
            role_name: The IAM role name to attach the policy to.
            policy_name: Name for the inline policy.
            policy_document: The policy document as a dict.
            region: AWS region. If omitted, uses default from environment.
        """
        if not self.allow_write:
            raise ValueError(
                'Write operations disabled. Start the server with --allow-write.'
            )

        try:
            kwargs = {}
            if region:
                kwargs['region_name'] = region

            iam_client = boto3.client('iam', **kwargs)
            iam_client.put_role_policy(
                RoleName=role_name,
                PolicyName=policy_name,
                PolicyDocument=json.dumps(policy_document),
            )

            return [TextContent(
                type='text',
                text=json.dumps({
                    'message': f'Inline policy "{policy_name}" added to role "{role_name}" successfully.',
                    'role_name': role_name,
                    'policy_name': policy_name,
                }),
            )]

        except Exception as e:
            return [TextContent(
                type='text',
                text=f'Error adding inline policy to role {role_name}: {str(e)}',
            )]
