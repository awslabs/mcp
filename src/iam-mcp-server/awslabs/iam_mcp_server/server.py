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

"""AWS IAM MCP Server implementation."""

import argparse
import json
from awslabs.iam_mcp_server.aws_client import get_iam_client
from awslabs.iam_mcp_server.context import Context
from awslabs.iam_mcp_server.errors import IamClientError, IamValidationError, handle_iam_error
from awslabs.iam_mcp_server.models import (
    AccessKey,
    AttachedPolicy,
    CreateUserResponse,
    IamUser,
    UserDetailsResponse,
    UsersListResponse,
)
from loguru import logger
from mcp.server.fastmcp import FastMCP
from mcp.types import CallToolResult
from pydantic import Field
from typing import Any, Dict, List, Optional, Union


mcp = FastMCP(
    'awslabs.iam-mcp-server',
    instructions="""
    # AWS IAM MCP Server

    This MCP server provides comprehensive AWS Identity and Access Management (IAM) capabilities:

    ## Core Features:
    1. **User Management**: Create, list, update, and delete IAM users
    2. **Role Management**: Create, list, update, and delete IAM roles
    3. **Policy Management**: Create, list, update, and delete IAM policies
    4. **Group Management**: Create, list, update, and delete IAM groups
    5. **Permission Management**: Attach/detach policies to users, roles, and groups
    6. **Access Key Management**: Create, list, and delete access keys for users
    7. **Security Analysis**: Analyze permissions, find unused resources, and security recommendations

    ## Security Best Practices:
    - Always follow the principle of least privilege
    - Regularly rotate access keys
    - Use roles instead of users for applications
    - Enable MFA where possible
    - Review and audit permissions regularly

    ## Usage Requirements:
    - Requires valid AWS credentials with appropriate IAM permissions
    - Some operations may be restricted in read-only mode
    - Always test policy changes in a safe environment first
    """,
    dependencies=['pydantic', 'loguru', 'boto3', 'botocore'],
)


@mcp.tool()
async def list_users(
    ctx: CallToolResult,
    path_prefix: Optional[str] = Field(
        description='Path prefix to filter users (e.g., "/division_abc/")', default=None
    ),
    max_items: int = Field(description='Maximum number of users to return', default=100),
) -> UsersListResponse:
    """List IAM users in the account.

    This tool retrieves a list of IAM users from your AWS account with optional filtering.
    Use this to get an overview of all users or find specific users by path prefix.

    ## Usage Tips:
    - Use path_prefix to filter users by organizational structure
    - Adjust max_items to control response size for large accounts
    - Results may be paginated for accounts with many users

    Args:
        ctx: MCP context for error reporting
        path_prefix: Optional path prefix to filter users
        max_items: Maximum number of users to return

    Returns:
        UsersListResponse containing list of users and metadata
    """
    try:
        logger.info(f"Listing IAM users with path_prefix='{path_prefix}', max_items={max_items}")

        iam = get_iam_client()

        kwargs: Dict[str, Any] = {'MaxItems': max_items}
        if path_prefix:
            kwargs['PathPrefix'] = path_prefix

        response = iam.list_users(**kwargs)

        users = []
        for user in response.get('Users', []):
            users.append(
                IamUser(
                    user_name=user['UserName'],
                    user_id=user['UserId'],
                    arn=user['Arn'],
                    path=user['Path'],
                    create_date=user['CreateDate'].isoformat(),
                    password_last_used=user.get('PasswordLastUsed', '').isoformat()
                    if user.get('PasswordLastUsed')
                    else None,
                )
            )

        result = UsersListResponse(
            users=users,
            is_truncated=response.get('IsTruncated', False),
            marker=response.get('Marker'),
            count=len(users),
        )

        logger.info(f'Successfully listed {len(users)} IAM users')
        return result

    except Exception as e:
        error = handle_iam_error(e)
        logger.error(f'Error listing users: {error}')
        raise error


@mcp.tool()
async def get_user(
    ctx: CallToolResult, user_name: str = Field(description='The name of the IAM user to retrieve')
) -> UserDetailsResponse:
    """Get detailed information about a specific IAM user.

    This tool retrieves comprehensive information about an IAM user including
    attached policies, group memberships, and access keys. Use this to get
    a complete picture of a user's permissions and configuration.

    ## Usage Tips:
    - Use this after list_users to get detailed information about specific users
    - Review attached policies to understand user permissions
    - Check access keys to identify potential security issues

    Args:
        ctx: MCP context for error reporting
        user_name: The name of the IAM user

    Returns:
        UserDetailsResponse containing comprehensive user information
    """
    try:
        logger.info(f'Getting details for IAM user: {user_name}')

        if not user_name:
            raise IamValidationError('User name is required')

        iam = get_iam_client()

        # Get user details
        user_response = iam.get_user(UserName=user_name)
        user = user_response['User']

        # Get attached policies
        attached_policies_response = iam.list_attached_user_policies(UserName=user_name)
        attached_policies = [
            AttachedPolicy(policy_name=policy['PolicyName'], policy_arn=policy['PolicyArn'])
            for policy in attached_policies_response.get('AttachedPolicies', [])
        ]

        # Get inline policies
        inline_policies_response = iam.list_user_policies(UserName=user_name)
        inline_policies = inline_policies_response.get('PolicyNames', [])

        # Get groups
        groups_response = iam.get_groups_for_user(UserName=user_name)
        groups = [group['GroupName'] for group in groups_response.get('Groups', [])]

        # Get access keys
        access_keys_response = iam.list_access_keys(UserName=user_name)
        access_keys = [
            AccessKey(
                access_key_id=key['AccessKeyId'],
                status=key['Status'],
                create_date=key['CreateDate'].isoformat(),
            )
            for key in access_keys_response.get('AccessKeyMetadata', [])
        ]

        user_details = IamUser(
            user_name=user['UserName'],
            user_id=user['UserId'],
            arn=user['Arn'],
            path=user['Path'],
            create_date=user['CreateDate'].isoformat(),
            password_last_used=user.get('PasswordLastUsed', '').isoformat()
            if user.get('PasswordLastUsed')
            else None,
        )

        result = UserDetailsResponse(
            user=user_details,
            attached_policies=attached_policies,
            inline_policies=inline_policies,
            groups=groups,
            access_keys=access_keys,
        )

        logger.info(f'Successfully retrieved details for user: {user_name}')
        return result

    except Exception as e:
        error = handle_iam_error(e)
        logger.error(f'Error getting user details: {error}')
        raise error


@mcp.tool()
async def create_user(
    ctx: CallToolResult,
    user_name: str = Field(description='The name of the new IAM user'),
    path: str = Field(description='The path for the user', default='/'),
    permissions_boundary: Optional[str] = Field(
        description='ARN of the permissions boundary policy', default=None
    ),
) -> CreateUserResponse:
    """Create a new IAM user.

    This tool creates a new IAM user in your AWS account. The user will be created
    without any permissions by default - you'll need to attach policies separately.

    ## Security Best Practices:
    - Use descriptive user names that indicate the user's role or purpose
    - Set appropriate paths for organizational structure
    - Consider using permissions boundaries to limit maximum permissions
    - Follow the principle of least privilege when assigning permissions later

    Args:
        ctx: MCP context for error reporting
        user_name: The name of the new IAM user
        path: The path for the user (default: '/')
        permissions_boundary: Optional ARN of the permissions boundary policy

    Returns:
        CreateUserResponse containing the created user details
    """
    try:
        logger.info(f'Creating IAM user: {user_name}')

        # Check if server is in read-only mode
        if Context.is_readonly():
            raise IamClientError('Cannot create user: server is running in read-only mode')

        if not user_name:
            raise IamValidationError('User name is required')

        iam = get_iam_client()

        kwargs = {'UserName': user_name, 'Path': path}

        if permissions_boundary:
            kwargs['PermissionsBoundary'] = permissions_boundary

        response = iam.create_user(**kwargs)
        user = response['User']

        user_details = IamUser(
            user_name=user['UserName'],
            user_id=user['UserId'],
            arn=user['Arn'],
            path=user['Path'],
            create_date=user['CreateDate'].isoformat(),
            password_last_used=user.get('PasswordLastUsed').isoformat()
            if user.get('PasswordLastUsed')
            else None,
        )

        result = CreateUserResponse(
            user=user_details, message=f'Successfully created user: {user_name}'
        )

        logger.info(f'Successfully created IAM user: {user_name}')
        return result

    except Exception as e:
        error = handle_iam_error(e)
        logger.error(f'Error creating user: {error}')
        raise error


@mcp.tool()
async def delete_user(
    user_name: str = Field(description='The name of the IAM user to delete'),
    force: bool = Field(
        description='Force delete user by removing all attached policies, groups, and access keys first',
        default=False,
    ),
) -> Dict[str, Any]:
    """Delete an IAM user.

    Args:
        user_name: The name of the IAM user to delete
        force: If True, removes all attached policies, groups, and access keys first

    Returns:
        Dictionary containing deletion status
    """
    try:
        # Check if server is in read-only mode
        if Context.is_readonly():
            raise IamClientError('Cannot delete user: server is running in read-only mode')

        iam = get_iam_client()

        if force:
            # Remove from all groups
            groups = iam.get_groups_for_user(UserName=user_name)
            for group in groups.get('Groups', []):
                iam.remove_user_from_group(GroupName=group['GroupName'], UserName=user_name)

            # Detach all managed policies
            attached_policies = iam.list_attached_user_policies(UserName=user_name)
            for policy in attached_policies.get('AttachedPolicies', []):
                iam.detach_user_policy(UserName=user_name, PolicyArn=policy['PolicyArn'])

            # Delete all inline policies
            inline_policies = iam.list_user_policies(UserName=user_name)
            for policy_name in inline_policies.get('PolicyNames', []):
                iam.delete_user_policy(UserName=user_name, PolicyName=policy_name)

            # Delete all access keys
            access_keys = iam.list_access_keys(UserName=user_name)
            for key in access_keys.get('AccessKeyMetadata', []):
                iam.delete_access_key(UserName=user_name, AccessKeyId=key['AccessKeyId'])

        # Delete the user
        iam.delete_user(UserName=user_name)

        return {'Message': f'Successfully deleted user: {user_name}', 'ForcedCleanup': force}

    except Exception as e:
        raise handle_iam_error(e)


@mcp.tool()
async def list_roles(
    path_prefix: Optional[str] = Field(
        description='Path prefix to filter roles (e.g., "/service-role/")', default=None
    ),
    max_items: int = Field(description='Maximum number of roles to return', default=100),
) -> Dict[str, Any]:
    """List IAM roles in the account.

    Args:
        path_prefix: Optional path prefix to filter roles
        max_items: Maximum number of roles to return

    Returns:
        Dictionary containing list of roles and metadata
    """
    try:
        iam = get_iam_client()

        kwargs: Dict[str, Any] = {'MaxItems': max_items}
        if path_prefix:
            kwargs['PathPrefix'] = path_prefix

        response = iam.list_roles(**kwargs)

        roles = []
        for role in response.get('Roles', []):
            roles.append(
                {
                    'RoleName': role['RoleName'],
                    'RoleId': role['RoleId'],
                    'Arn': role['Arn'],
                    'Path': role['Path'],
                    'CreateDate': role['CreateDate'].isoformat(),
                    'AssumeRolePolicyDocument': role.get('AssumeRolePolicyDocument'),
                    'Description': role.get('Description'),
                    'MaxSessionDuration': role.get('MaxSessionDuration'),
                }
            )

        return {
            'Roles': roles,
            'IsTruncated': response.get('IsTruncated', False),
            'Marker': response.get('Marker'),
            'Count': len(roles),
        }

    except Exception as e:
        raise handle_iam_error(e)


@mcp.tool()
async def create_role(
    role_name: str = Field(description='The name of the new IAM role'),
    assume_role_policy_document: Union[str, dict] = Field(
        description='The trust policy document in JSON format (string or dict)'
    ),
    path: str = Field(description='The path for the role', default='/'),
    description: Optional[str] = Field(description='Description of the role', default=None),
    max_session_duration: int = Field(
        description='Maximum session duration in seconds (3600-43200)', default=3600
    ),
    permissions_boundary: Optional[str] = Field(
        description='ARN of the permissions boundary policy', default=None
    ),
) -> Dict[str, Any]:
    """Create a new IAM role.

    Args:
        role_name: The name of the new IAM role
        assume_role_policy_document: The trust policy document in JSON format
        path: The path for the role (default: '/')
        description: Optional description of the role
        max_session_duration: Maximum session duration in seconds
        permissions_boundary: Optional ARN of the permissions boundary policy

    Returns:
        Dictionary containing the created role details
    """
    try:
        # Check if server is in read-only mode
        if Context.is_readonly():
            raise IamClientError('Cannot create role: server is running in read-only mode')

        iam = get_iam_client()

        # Handle both string and dict types
        if isinstance(assume_role_policy_document, dict):
            policy_document = json.dumps(assume_role_policy_document)
        else:
            policy_document = assume_role_policy_document
            # Validate JSON
            try:
                json.loads(policy_document)
            except json.JSONDecodeError:
                raise Exception('Invalid JSON in assume_role_policy_document')

        kwargs = {
            'RoleName': role_name,
            'AssumeRolePolicyDocument': policy_document,
            'Path': path,
            'MaxSessionDuration': max_session_duration,
        }

        if description:
            kwargs['Description'] = description
        if permissions_boundary:
            kwargs['PermissionsBoundary'] = permissions_boundary

        response = iam.create_role(**kwargs)
        role = response['Role']

        return {
            'Role': {
                'RoleName': role['RoleName'],
                'RoleId': role['RoleId'],
                'Arn': role['Arn'],
                'Path': role['Path'],
                'CreateDate': role['CreateDate'].isoformat(),
                'AssumeRolePolicyDocument': role.get('AssumeRolePolicyDocument'),
                'Description': role.get('Description'),
                'MaxSessionDuration': role.get('MaxSessionDuration'),
            },
            'Message': f'Successfully created role: {role_name}',
        }

    except Exception as e:
        raise handle_iam_error(e)


@mcp.tool()
async def list_policies(
    scope: str = Field(
        description='Scope of policies to list: "All", "AWS", or "Local"', default='Local'
    ),
    only_attached: bool = Field(
        description='Only return policies that are attached to a user, group, or role',
        default=False,
    ),
    path_prefix: Optional[str] = Field(description='Path prefix to filter policies', default=None),
    max_items: int = Field(description='Maximum number of policies to return', default=100),
) -> Dict[str, Any]:
    """List IAM policies in the account.

    Args:
        scope: Scope of policies to list ("All", "AWS", or "Local")
        only_attached: Only return policies that are attached
        path_prefix: Optional path prefix to filter policies
        max_items: Maximum number of policies to return

    Returns:
        Dictionary containing list of policies and metadata
    """
    try:
        iam = get_iam_client()

        kwargs = {'Scope': scope, 'OnlyAttached': only_attached, 'MaxItems': max_items}
        if path_prefix:
            kwargs['PathPrefix'] = path_prefix

        response = iam.list_policies(**kwargs)

        policies = []
        for policy in response.get('Policies', []):
            policies.append(
                {
                    'PolicyName': policy['PolicyName'],
                    'PolicyId': policy['PolicyId'],
                    'Arn': policy['Arn'],
                    'Path': policy['Path'],
                    'DefaultVersionId': policy['DefaultVersionId'],
                    'AttachmentCount': policy['AttachmentCount'],
                    'PermissionsBoundaryUsageCount': policy.get(
                        'PermissionsBoundaryUsageCount', 0
                    ),
                    'IsAttachable': policy['IsAttachable'],
                    'Description': policy.get('Description'),
                    'CreateDate': policy['CreateDate'].isoformat(),
                    'UpdateDate': policy['UpdateDate'].isoformat(),
                }
            )

        return {
            'Policies': policies,
            'IsTruncated': response.get('IsTruncated', False),
            'Marker': response.get('Marker'),
            'Count': len(policies),
        }

    except Exception as e:
        raise handle_iam_error(e)


@mcp.tool()
async def attach_user_policy(
    user_name: str = Field(description='The name of the IAM user'),
    policy_arn: str = Field(description='The ARN of the policy to attach'),
) -> Dict[str, Any]:
    """Attach a managed policy to an IAM user.

    Args:
        user_name: The name of the IAM user
        policy_arn: The ARN of the policy to attach

    Returns:
        Dictionary containing attachment status
    """
    try:
        # Check if server is in read-only mode
        if Context.is_readonly():
            raise IamClientError('Cannot attach policy: server is running in read-only mode')

        iam = get_iam_client()

        iam.attach_user_policy(UserName=user_name, PolicyArn=policy_arn)

        return {
            'Message': f'Successfully attached policy {policy_arn} to user {user_name}',
            'UserName': user_name,
            'PolicyArn': policy_arn,
        }

    except Exception as e:
        raise handle_iam_error(e)


@mcp.tool()
async def detach_user_policy(
    user_name: str = Field(description='The name of the IAM user'),
    policy_arn: str = Field(description='The ARN of the policy to detach'),
) -> Dict[str, Any]:
    """Detach a managed policy from an IAM user.

    Args:
        user_name: The name of the IAM user
        policy_arn: The ARN of the policy to detach

    Returns:
        Dictionary containing detachment status
    """
    try:
        # Check if server is in read-only mode
        if Context.is_readonly():
            raise IamClientError('Cannot detach policy: server is running in read-only mode')

        iam = get_iam_client()

        iam.detach_user_policy(UserName=user_name, PolicyArn=policy_arn)

        return {
            'Message': f'Successfully detached policy {policy_arn} from user {user_name}',
            'UserName': user_name,
            'PolicyArn': policy_arn,
        }

    except Exception as e:
        raise handle_iam_error(e)


@mcp.tool()
async def create_access_key(
    user_name: str = Field(description='The name of the IAM user'),
) -> Dict[str, Any]:
    """Create a new access key for an IAM user.

    Args:
        user_name: The name of the IAM user

    Returns:
        Dictionary containing the new access key details
    """
    try:
        # Check if server is in read-only mode
        if Context.is_readonly():
            raise IamClientError('Cannot create access key: server is running in read-only mode')

        iam = get_iam_client()

        response = iam.create_access_key(UserName=user_name)
        access_key = response['AccessKey']

        return {
            'AccessKey': {
                'AccessKeyId': access_key['AccessKeyId'],
                'SecretAccessKey': access_key['SecretAccessKey'],
                'Status': access_key['Status'],
                'UserName': access_key['UserName'],
                'CreateDate': access_key['CreateDate'].isoformat(),
            },
            'Message': f'Successfully created access key for user: {user_name}',
            'Warning': 'Store the SecretAccessKey securely - it cannot be retrieved again!',
        }

    except Exception as e:
        raise handle_iam_error(e)


@mcp.tool()
async def delete_access_key(
    user_name: str = Field(description='The name of the IAM user'),
    access_key_id: str = Field(description='The access key ID to delete'),
) -> Dict[str, Any]:
    """Delete an access key for an IAM user.

    Args:
        user_name: The name of the IAM user
        access_key_id: The access key ID to delete

    Returns:
        Dictionary containing deletion status
    """
    try:
        # Check if server is in read-only mode
        if Context.is_readonly():
            raise IamClientError('Cannot delete access key: server is running in read-only mode')

        iam = get_iam_client()

        iam.delete_access_key(UserName=user_name, AccessKeyId=access_key_id)

        return {
            'Message': f'Successfully deleted access key {access_key_id} for user {user_name}',
            'UserName': user_name,
            'AccessKeyId': access_key_id,
        }

    except Exception as e:
        raise handle_iam_error(e)


@mcp.tool()
async def simulate_principal_policy(
    policy_source_arn: str = Field(description='ARN of the user or role to simulate'),
    action_names: List[str] = Field(description='List of actions to simulate'),
    resource_arns: Optional[List[str]] = Field(
        description='List of resource ARNs to test against', default=None
    ),
    context_entries: Optional[Dict[str, str]] = Field(
        description='Context entries for the simulation', default=None
    ),
) -> Dict[str, Any]:
    """Simulate IAM policy evaluation for a principal.

    Args:
        policy_source_arn: ARN of the user or role to simulate
        action_names: List of actions to simulate
        resource_arns: Optional list of resource ARNs to test against
        context_entries: Optional context entries for the simulation

    Returns:
        Dictionary containing simulation results
    """
    try:
        iam = get_iam_client()

        kwargs = {'PolicySourceArn': policy_source_arn, 'ActionNames': action_names}

        if resource_arns:
            kwargs['ResourceArns'] = resource_arns
        if context_entries:
            kwargs['ContextEntries'] = [
                {'ContextKeyName': k, 'ContextKeyValues': [v]} for k, v in context_entries.items()
            ]

        response = iam.simulate_principal_policy(**kwargs)

        results = []
        for result in response.get('EvaluationResults', []):
            results.append(
                {
                    'EvalActionName': result['EvalActionName'],
                    'EvalResourceName': result.get('EvalResourceName', '*'),
                    'EvalDecision': result['EvalDecision'],
                    'MatchedStatements': result.get('MatchedStatements', []),
                    'MissingContextValues': result.get('MissingContextValues', []),
                }
            )

        return {
            'EvaluationResults': results,
            'IsTruncated': response.get('IsTruncated', False),
            'Marker': response.get('Marker'),
            'PolicySourceArn': policy_source_arn,
        }

    except Exception as e:
        raise handle_iam_error(e)


def main():
    """Run the MCP server with CLI argument support."""
    parser = argparse.ArgumentParser(
        description='An AWS Labs Model Context Protocol (MCP) server for comprehensive AWS IAM management'
    )
    parser.add_argument(
        '--readonly',
        action=argparse.BooleanOptionalAction,
        help='Prevents the MCP server from performing mutating operations',
        default=False,
    )
    parser.add_argument('--region', help='AWS region to use for operations')

    args = parser.parse_args()

    # Initialize context with configuration
    Context.initialize(readonly=args.readonly, region=args.region)

    if args.region:
        logger.info(f'Using AWS region: {args.region}')

    if args.readonly:
        logger.info('Running in read-only mode - mutating operations will be disabled')

    mcp.run()


if __name__ == '__main__':
    main()
