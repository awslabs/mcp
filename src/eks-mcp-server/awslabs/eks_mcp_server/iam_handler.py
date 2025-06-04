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

"""IAM handler for the EKS MCP Server."""

import json
from awslabs.eks_mcp_server.aws_helper import AwsHelper
from awslabs.eks_mcp_server.logging_helper import LogLevel, log_with_request_id
from awslabs.eks_mcp_server.models import (
    AddInlinePolicyResponse,
    PolicySummary,
    RoleDescriptionResponse,
)
from mcp.server.fastmcp import Context
from mcp.types import TextContent
from pydantic import Field
from typing import Any, Dict, List, Union


class IAMHandler:
    """Handler for AWS IAM operations in the EKS MCP Server.

    This class provides tools for managing IAM roles and policies, including
    describing roles with their attached policies and adding inline permissions
    to policies.
    """

    def __init__(self, mcp, allow_write: bool = False):
        """Initialize the IAM handler.

        Args:
            mcp: The MCP server instance
            allow_write: Whether to enable write access (default: False)
        """
        self.mcp = mcp
        self.iam_client = AwsHelper.create_boto3_client('iam')
        self.allow_write = allow_write

        # Register tools
        self.mcp.tool(name='add_inline_policy')(self.add_inline_policy)
        self.mcp.tool(name='get_policies_for_role')(self.get_policies_for_role)

    async def get_policies_for_role(
        self,
        ctx: Context,
        role_name: str = Field(
            ...,
            description='Name of the IAM role to get policies for. The role must exist in your AWS account.',
        ),
    ) -> RoleDescriptionResponse:
        """Get all policies attached to an IAM role.

        This tool retrieves all policies associated with an IAM role, providing a comprehensive view
        of the role's permissions and trust relationships. It helps you understand the current
        permissions, identify missing or excessive permissions, troubleshoot EKS cluster issues,
        and verify trust relationships for service roles.

        IMPORTANT: Use this tool instead of 'aws iam get-role', 'aws iam list-attached-role-policies',
        'aws iam list-role-policies', and 'aws iam get-role-policy' commands.

        ## Requirements
        - The role must exist in your AWS account
        - Valid AWS credentials with permissions to read IAM role information

        ## Response Information
        The response includes role ARN, assume role policy document (trust relationships),
        role description, managed policies with their documents, and inline policies with
        their documents.

        ## Usage Tips
        - Use this tool before adding new permissions to understand existing access
        - Check the assume role policy to verify which services or roles can assume this role
        - Look for overly permissive policies that might pose security risks
        - Use with add_inline_policy to implement least-privilege permissions

        Args:
            ctx: The MCP context
            role_name: Name of the IAM role to get policies for

        Returns:
            RoleDescriptionResponse: Detailed information about the role's policies
        """
        try:
            log_with_request_id(ctx, LogLevel.INFO, f'Describing IAM role: {role_name}')

            # Get role details
            role_response = self.iam_client.get_role(RoleName=role_name)
            role = role_response['Role']

            # Get attached managed policies
            managed_policies = self._get_managed_policies(ctx, role_name)

            # Get inline policies
            inline_policies = self._get_inline_policies(ctx, role_name)

            # Parse the assume role policy document if it's a string, otherwise use it directly
            if isinstance(role['AssumeRolePolicyDocument'], str):
                assume_role_policy_document = json.loads(role['AssumeRolePolicyDocument'])
            else:
                assume_role_policy_document = role['AssumeRolePolicyDocument']

            # Create the response
            return RoleDescriptionResponse(
                isError=False,
                content=[
                    TextContent(
                        type='text',
                        text=f'Successfully retrieved details for IAM role: {role_name}',
                    )
                ],
                role_arn=role['Arn'],
                assume_role_policy_document=assume_role_policy_document,
                description=role.get('Description'),
                managed_policies=managed_policies,
                inline_policies=inline_policies,
            )
        except Exception as e:
            error_message = f'Failed to describe IAM role: {str(e)}'
            log_with_request_id(ctx, LogLevel.ERROR, error_message)

            # Return a response with error status
            return RoleDescriptionResponse(
                isError=True,
                content=[TextContent(type='text', text=error_message)],
                role_arn='',
                assume_role_policy_document={},
                description=None,
                managed_policies=[],
                inline_policies=[],
            )

    async def add_inline_policy(
        self,
        ctx: Context,
        policy_name: str = Field(
            ..., description='Name of the inline policy to create. Must be unique within the role.'
        ),
        role_name: str = Field(
            ..., description='Name of the IAM role to add the policy to. The role must exist.'
        ),
        permissions: Union[Dict[str, Any], List[Dict[str, Any]]] = Field(
            ...,
            description="""Permissions to include in the policy as IAM policy statements in JSON format.
            Can be either a single statement object or an array of statement objects.""",
        ),
    ) -> AddInlinePolicyResponse:
        """Add a new inline policy to an IAM role.

        This tool creates a new inline policy with the specified permissions and adds it to an IAM role.
        Inline policies are embedded within the role and cannot be attached to multiple roles. Commonly used
        for granting EKS clusters access to AWS services, enabling worker nodes to access resources, and
        configuring permissions for CloudWatch logging and ECR access.

        IMPORTANT: Use this tool instead of 'aws iam put-role-policy' commands.

        ## Requirements
        - The server must be run with the `--allow-write` flag
        - The role must exist in your AWS account
        - The policy name must be unique within the role
        - You cannot modify existing policies with this tool

        ## Permission Format
        The permissions parameter can be either a single policy statement or a list of statements.

        ### Single Statement Example
        ```json
        {
            "Effect": "Allow",
            "Action": ["s3:GetObject", "s3:PutObject"],
            "Resource": "arn:aws:s3:::example-bucket/*"
        }
        ```

        ## Usage Tips
        - Follow the principle of least privilege by granting only necessary permissions
        - Use specific resources rather than "*" whenever possible
        - Consider using conditions to further restrict permissions
        - Group related permissions into logical policies with descriptive names

        Args:
            ctx: The MCP context
            policy_name: Name of the new inline policy to create
            role_name: Name of the role to add the policy to
            permissions: Permissions to include in the policy (in JSON format)

        Returns:
            AddInlinePolicyResponse: Information about the created policy
        """
        try:
            # Check if write access is disabled
            if not self.allow_write:
                error_message = 'Adding inline policies requires --allow-write flag'
                log_with_request_id(ctx, LogLevel.ERROR, error_message)
                return AddInlinePolicyResponse(
                    isError=True,
                    content=[TextContent(type='text', text=error_message)],
                    policy_name=policy_name,
                    role_name=role_name,
                    permissions_added={},
                )

            # Create the inline policy
            return self._create_inline_policy(ctx, role_name, policy_name, permissions)

        except Exception as e:
            error_message = f'Failed to create inline policy: {str(e)}'
            log_with_request_id(ctx, LogLevel.ERROR, error_message)

            # Return a response with error status
            return AddInlinePolicyResponse(
                isError=True,
                content=[TextContent(type='text', text=error_message)],
                policy_name=policy_name,
                role_name=role_name,
                permissions_added={},
            )

    def _get_managed_policies(self, ctx, role_name):
        """Get managed policies attached to a role.

        Args:
            ctx: The MCP context
            role_name: Name of the IAM role

        Returns:
            List of PolicySummary objects
        """
        managed_policies = []
        managed_policies_response = self.iam_client.list_attached_role_policies(RoleName=role_name)

        for policy in managed_policies_response.get('AttachedPolicies', []):
            policy_arn = policy['PolicyArn']
            policy_details = self.iam_client.get_policy(PolicyArn=policy_arn)['Policy']

            # Get the policy version details to get the policy document
            policy_version = None
            try:
                policy_version_response = self.iam_client.get_policy_version(
                    PolicyArn=policy_arn, VersionId=policy_details.get('DefaultVersionId', 'v1')
                )
                policy_version = policy_version_response.get('PolicyVersion', {})
            except Exception as e:
                log_with_request_id(
                    ctx, LogLevel.WARNING, f'Failed to get policy version: {str(e)}'
                )

            managed_policies.append(
                PolicySummary(
                    policy_type='Managed',
                    description=policy_details.get('Description'),
                    policy_document=policy_version.get('Document') if policy_version else None,
                )
            )

        return managed_policies

    def _get_inline_policies(self, ctx, role_name):
        """Get inline policies embedded in a role.

        Args:
            ctx: The MCP context
            role_name: Name of the IAM role

        Returns:
            List of PolicySummary objects
        """
        inline_policies = []
        inline_policies_response = self.iam_client.list_role_policies(RoleName=role_name)

        for policy_name in inline_policies_response.get('PolicyNames', []):
            policy_response = self.iam_client.get_role_policy(
                RoleName=role_name, PolicyName=policy_name
            )

            inline_policies.append(
                PolicySummary(
                    policy_type='Inline',
                    description=None,
                    policy_document=policy_response.get('PolicyDocument'),
                )
            )

        return inline_policies

    def _create_inline_policy(self, ctx, role_name, policy_name, permissions):
        """Create a new inline policy with the specified permissions.

        Args:
            ctx: The MCP context
            role_name: Name of the role
            policy_name: Name of the new policy to create
            permissions: Permissions to include in the policy

        Returns:
            AddInlinePolicyResponse: Information about the created policy
        """
        log_with_request_id(
            ctx,
            LogLevel.INFO,
            f'Creating new inline policy {policy_name} in role {role_name}',
        )

        # Check if the policy already exists
        try:
            self.iam_client.get_role_policy(RoleName=role_name, PolicyName=policy_name)
            # If we get here, the policy exists
            error_message = f'Policy {policy_name} already exists in role {role_name}. Cannot modify existing policies.'
            log_with_request_id(ctx, LogLevel.ERROR, error_message)
            return AddInlinePolicyResponse(
                isError=True,
                content=[TextContent(type='text', text=error_message)],
                policy_name=policy_name,
                role_name=role_name,
                permissions_added={},
            )
        except self.iam_client.exceptions.NoSuchEntityException:
            # Policy doesn't exist, we can create it
            pass

        # Create a new policy document
        policy_document = {'Version': '2012-10-17', 'Statement': []}

        # Add the permissions to the policy document
        self._add_permissions_to_document(policy_document, permissions)

        # Create the policy
        self.iam_client.put_role_policy(
            RoleName=role_name, PolicyName=policy_name, PolicyDocument=json.dumps(policy_document)
        )

        return AddInlinePolicyResponse(
            isError=False,
            content=[
                TextContent(
                    type='text',
                    text=f'Successfully created new inline policy {policy_name} in role {role_name}',
                )
            ],
            policy_name=policy_name,
            role_name=role_name,
            permissions_added=permissions,
        )

    def _add_permissions_to_document(self, policy_document, permissions):
        """Add permissions to a policy document.

        Args:
            policy_document: Policy document to modify
            permissions: Permissions to add
        """
        if isinstance(permissions, dict):
            # Single statement
            policy_document['Statement'].append(permissions)
        elif isinstance(permissions, list):
            # Multiple statements
            policy_document['Statement'].extend(permissions)
