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

"""IAM handler for the ROSA MCP Server."""

import json
from awslabs.rosa_mcp_server.aws_helper import AwsHelper
from awslabs.rosa_mcp_server.consts import MCP_MANAGED_TAG_KEY, MCP_MANAGED_TAG_VALUE
from awslabs.rosa_mcp_server.logging_helper import LogLevel, log_with_request_id
from awslabs.rosa_mcp_server.models import IAMRoleResponse
from loguru import logger
from mcp.server.fastmcp import Context, FastMCP
from mcp.types import CallToolResult
from pydantic import Field
from typing import Dict, List, Optional


class IAMHandler:
    """Handler for IAM operations related to ROSA."""

    def __init__(self, mcp: FastMCP, allow_write: bool = False):
        """Initialize the IAM handler."""
        self.mcp = mcp
        self.allow_write = allow_write
        self._register_tools()

    def _register_tools(self):
        """Register IAM tools with the MCP server."""
        
        # List IAM roles
        @self.mcp.tool()
        async def list_rosa_iam_roles(
            ctx: Context,
            prefix: Optional[str] = Field(None, description='Filter roles by prefix'),
            cluster_name: Optional[str] = Field(None, description='Filter roles for specific cluster'),
        ) -> CallToolResult:
            """List IAM roles related to ROSA.

            This tool lists IAM roles that are used by ROSA, including account roles
            and operator roles.

            Args:
                ctx: MCP context
                prefix: Optional prefix to filter roles
                cluster_name: Optional cluster name to filter roles

            Returns:
                CallToolResult with list of roles

            Example:
                list_rosa_iam_roles(prefix="ManagedOpenShift")
            """
            log_with_request_id(ctx, LogLevel.INFO, 'Listing ROSA IAM roles', 
                              prefix=prefix, cluster_name=cluster_name)
            
            try:
                iam_client = AwsHelper.create_boto3_client('iam')
                
                # List all roles
                paginator = iam_client.get_paginator('list_roles')
                roles = []
                
                for page in paginator.paginate():
                    for role in page['Roles']:
                        role_name = role['RoleName']
                        
                        # Filter by prefix if provided
                        if prefix and not role_name.startswith(prefix):
                            continue
                        
                        # Check if it's a ROSA-related role
                        if any(pattern in role_name for pattern in ['ManagedOpenShift', 'ROSA', 'openshift']):
                            # Get role tags to check cluster association
                            try:
                                tags_response = iam_client.list_role_tags(RoleName=role_name)
                                tags = {tag['Key']: tag['Value'] for tag in tags_response.get('Tags', [])}
                                
                                # Filter by cluster if specified
                                if cluster_name:
                                    cluster_tag = tags.get('rosa_cluster_id') or tags.get('red-hat-managed')
                                    if cluster_tag and cluster_name not in str(cluster_tag):
                                        continue
                                
                                roles.append({
                                    'RoleName': role_name,
                                    'RoleArn': role['Arn'],
                                    'CreateDate': role['CreateDate'].isoformat(),
                                    'Tags': tags
                                })
                            except:
                                # If we can't get tags, include the role anyway
                                roles.append({
                                    'RoleName': role_name,
                                    'RoleArn': role['Arn'],
                                    'CreateDate': role['CreateDate'].isoformat()
                                })
                
                return CallToolResult(
                    success=True,
                    content=json.dumps(roles, indent=2)
                )
                
            except Exception as e:
                error_msg = f'Failed to list IAM roles: {str(e)}'
                log_with_request_id(ctx, LogLevel.ERROR, error_msg)
                return CallToolResult(success=False, content=error_msg)

        # Create IAM policy
        @self.mcp.tool()
        async def create_rosa_iam_policy(
            ctx: Context,
            policy_name: str = Field(..., description='Name for the IAM policy'),
            policy_document: Dict = Field(..., description='IAM policy document'),
            description: Optional[str] = Field(None, description='Policy description'),
            tags: Optional[Dict[str, str]] = Field(None, description='Tags for the policy'),
        ) -> CallToolResult:
            """Create an IAM policy for ROSA.

            This tool creates a custom IAM policy that can be attached to ROSA roles.

            Args:
                ctx: MCP context
                policy_name: Name for the policy
                policy_document: IAM policy document in JSON format
                description: Optional description
                tags: Optional tags

            Returns:
                CallToolResult with created policy details

            Example:
                create_rosa_iam_policy(
                    policy_name="rosa-s3-access",
                    policy_document={
                        "Version": "2012-10-17",
                        "Statement": [{
                            "Effect": "Allow",
                            "Action": ["s3:GetObject"],
                            "Resource": ["arn:aws:s3:::my-bucket/*"]
                        }]
                    }
                )
            """
            if not self.allow_write:
                return CallToolResult(
                    success=False,
                    content='Write access is required to create IAM policies. Run with --allow-write flag.'
                )
            
            log_with_request_id(ctx, LogLevel.INFO, 'Creating IAM policy', 
                              policy_name=policy_name)
            
            try:
                iam_client = AwsHelper.create_boto3_client('iam')
                
                # Add MCP managed tags
                all_tags = [
                    {'Key': MCP_MANAGED_TAG_KEY, 'Value': MCP_MANAGED_TAG_VALUE},
                    {'Key': 'Purpose', 'Value': 'ROSA'}
                ]
                if tags:
                    for k, v in tags.items():
                        all_tags.append({'Key': k, 'Value': v})
                
                # Create the policy
                response = iam_client.create_policy(
                    PolicyName=policy_name,
                    PolicyDocument=json.dumps(policy_document),
                    Description=description or f'Policy for ROSA created by MCP',
                    Tags=all_tags
                )
                
                policy = response['Policy']
                
                return CallToolResult(
                    success=True,
                    content=f'Successfully created IAM policy {policy_name}\nARN: {policy["Arn"]}'
                )
                
            except Exception as e:
                error_msg = f'Failed to create IAM policy: {str(e)}'
                log_with_request_id(ctx, LogLevel.ERROR, error_msg)
                return CallToolResult(success=False, content=error_msg)

        # Attach policy to role
        @self.mcp.tool()
        async def attach_rosa_policy_to_role(
            ctx: Context,
            role_name: str = Field(..., description='Name of the IAM role'),
            policy_arn: str = Field(..., description='ARN of the policy to attach'),
        ) -> CallToolResult:
            """Attach an IAM policy to a ROSA-related role.

            This tool attaches a policy to an existing ROSA role to grant additional permissions.

            Args:
                ctx: MCP context
                role_name: Name of the IAM role
                policy_arn: ARN of the policy to attach

            Returns:
                CallToolResult indicating success or failure

            Example:
                attach_rosa_policy_to_role(
                    role_name="ManagedOpenShift-Worker-Role",
                    policy_arn="arn:aws:iam::123456789012:policy/rosa-s3-access"
                )
            """
            if not self.allow_write:
                return CallToolResult(
                    success=False,
                    content='Write access is required to attach policies. Run with --allow-write flag.'
                )
            
            log_with_request_id(ctx, LogLevel.INFO, 'Attaching policy to role', 
                              role_name=role_name, policy_arn=policy_arn)
            
            try:
                iam_client = AwsHelper.create_boto3_client('iam')
                
                # Verify the role exists and is ROSA-related
                try:
                    role = iam_client.get_role(RoleName=role_name)
                    if not any(pattern in role_name for pattern in ['ManagedOpenShift', 'ROSA', 'openshift']):
                        return CallToolResult(
                            success=False,
                            content=f'Role {role_name} does not appear to be a ROSA-related role'
                        )
                except iam_client.exceptions.NoSuchEntityException:
                    return CallToolResult(
                        success=False,
                        content=f'Role {role_name} not found'
                    )
                
                # Attach the policy
                iam_client.attach_role_policy(
                    RoleName=role_name,
                    PolicyArn=policy_arn
                )
                
                return CallToolResult(
                    success=True,
                    content=f'Successfully attached policy {policy_arn} to role {role_name}'
                )
                
            except Exception as e:
                error_msg = f'Failed to attach policy: {str(e)}'
                log_with_request_id(ctx, LogLevel.ERROR, error_msg)
                return CallToolResult(success=False, content=error_msg)

        # List policies attached to role
        @self.mcp.tool()
        async def list_rosa_role_policies(
            ctx: Context,
            role_name: str = Field(..., description='Name of the IAM role'),
        ) -> CallToolResult:
            """List policies attached to a ROSA-related role.

            This tool lists both inline and managed policies attached to a role.

            Args:
                ctx: MCP context
                role_name: Name of the IAM role

            Returns:
                CallToolResult with policy list

            Example:
                list_rosa_role_policies(role_name="ManagedOpenShift-Worker-Role")
            """
            log_with_request_id(ctx, LogLevel.INFO, 'Listing role policies', 
                              role_name=role_name)
            
            try:
                iam_client = AwsHelper.create_boto3_client('iam')
                
                policies = {
                    'ManagedPolicies': [],
                    'InlinePolicies': []
                }
                
                # Get attached managed policies
                paginator = iam_client.get_paginator('list_attached_role_policies')
                for page in paginator.paginate(RoleName=role_name):
                    for policy in page['AttachedPolicies']:
                        policies['ManagedPolicies'].append({
                            'PolicyName': policy['PolicyName'],
                            'PolicyArn': policy['PolicyArn']
                        })
                
                # Get inline policies
                paginator = iam_client.get_paginator('list_role_policies')
                for page in paginator.paginate(RoleName=role_name):
                    for policy_name in page['PolicyNames']:
                        # Get the inline policy document
                        response = iam_client.get_role_policy(
                            RoleName=role_name,
                            PolicyName=policy_name
                        )
                        policies['InlinePolicies'].append({
                            'PolicyName': policy_name,
                            'PolicyDocument': response['PolicyDocument']
                        })
                
                return CallToolResult(
                    success=True,
                    content=json.dumps(policies, indent=2)
                )
                
            except Exception as e:
                error_msg = f'Failed to list role policies: {str(e)}'
                log_with_request_id(ctx, LogLevel.ERROR, error_msg)
                return CallToolResult(success=False, content=error_msg)

        # Create service-linked role
        @self.mcp.tool()
        async def create_rosa_service_linked_role(
            ctx: Context,
            service_name: str = Field('elasticloadbalancing.amazonaws.com', 
                                    description='AWS service name for the SLR'),
        ) -> CallToolResult:
            """Create a service-linked role for ROSA.

            This tool creates service-linked roles required by ROSA for AWS service integration.

            Args:
                ctx: MCP context
                service_name: AWS service name (e.g., elasticloadbalancing.amazonaws.com)

            Returns:
                CallToolResult with created role details

            Example:
                create_rosa_service_linked_role(service_name="elasticloadbalancing.amazonaws.com")
            """
            if not self.allow_write:
                return CallToolResult(
                    success=False,
                    content='Write access is required to create service-linked roles. Run with --allow-write flag.'
                )
            
            log_with_request_id(ctx, LogLevel.INFO, 'Creating service-linked role', 
                              service_name=service_name)
            
            try:
                iam_client = AwsHelper.create_boto3_client('iam')
                
                # Try to create the service-linked role
                response = iam_client.create_service_linked_role(
                    AWSServiceName=service_name,
                    Description='Service-linked role for ROSA'
                )
                
                role = response['Role']
                
                return CallToolResult(
                    success=True,
                    content=f'Successfully created service-linked role\nRole ARN: {role["Arn"]}'
                )
                
            except iam_client.exceptions.InvalidInputException as e:
                if 'already been taken in this account' in str(e):
                    return CallToolResult(
                        success=True,
                        content=f'Service-linked role for {service_name} already exists'
                    )
                else:
                    error_msg = f'Failed to create service-linked role: {str(e)}'
                    log_with_request_id(ctx, LogLevel.ERROR, error_msg)
                    return CallToolResult(success=False, content=error_msg)
            except Exception as e:
                error_msg = f'Failed to create service-linked role: {str(e)}'
                log_with_request_id(ctx, LogLevel.ERROR, error_msg)
                return CallToolResult(success=False, content=error_msg)

        # Validate ROSA permissions
        @self.mcp.tool()
        async def validate_rosa_permissions(
            ctx: Context,
            cluster_name: Optional[str] = Field(None, description='Cluster name to validate permissions for'),
        ) -> CallToolResult:
            """Validate that required IAM permissions are set up for ROSA.

            This tool checks that all necessary IAM roles and policies are in place
            for ROSA to function properly.

            Args:
                ctx: MCP context
                cluster_name: Optional cluster name for cluster-specific validation

            Returns:
                CallToolResult with validation results

            Example:
                validate_rosa_permissions()
            """
            log_with_request_id(ctx, LogLevel.INFO, 'Validating ROSA permissions')
            
            try:
                iam_client = AwsHelper.create_boto3_client('iam')
                sts_client = AwsHelper.create_boto3_client('sts')
                
                # Get current account ID
                account_id = sts_client.get_caller_identity()['Account']
                
                validation_results = {
                    'AccountID': account_id,
                    'RequiredRoles': {},
                    'ServiceLinkedRoles': {},
                    'Issues': []
                }
                
                # Check for account-wide ROSA roles
                required_account_roles = [
                    'ManagedOpenShift-Installer-Role',
                    'ManagedOpenShift-ControlPlane-Role',
                    'ManagedOpenShift-Worker-Role',
                    'ManagedOpenShift-Support-Role'
                ]
                
                for role_name in required_account_roles:
                    try:
                        iam_client.get_role(RoleName=role_name)
                        validation_results['RequiredRoles'][role_name] = 'Present'
                    except iam_client.exceptions.NoSuchEntityException:
                        validation_results['RequiredRoles'][role_name] = 'Missing'
                        validation_results['Issues'].append(f'Missing required role: {role_name}')
                
                # Check for service-linked roles
                slr_services = ['elasticloadbalancing.amazonaws.com', 'ec2.amazonaws.com']
                for service in slr_services:
                    slr_name = f'AWSServiceRoleFor{service.split(".")[0].title()}'
                    try:
                        iam_client.get_role(RoleName=slr_name)
                        validation_results['ServiceLinkedRoles'][service] = 'Present'
                    except:
                        validation_results['ServiceLinkedRoles'][service] = 'Missing'
                        # This is often OK as SLRs are created automatically
                
                # Add summary
                if validation_results['Issues']:
                    validation_results['Status'] = 'Issues Found'
                    validation_results['Message'] = 'Some required IAM resources are missing. Run setup_rosa_account_roles() to fix.'
                else:
                    validation_results['Status'] = 'Valid'
                    validation_results['Message'] = 'All required IAM permissions are properly configured.'
                
                return CallToolResult(
                    success=True,
                    content=json.dumps(validation_results, indent=2)
                )
                
            except Exception as e:
                error_msg = f'Failed to validate permissions: {str(e)}'
                log_with_request_id(ctx, LogLevel.ERROR, error_msg)
                return CallToolResult(success=False, content=error_msg)