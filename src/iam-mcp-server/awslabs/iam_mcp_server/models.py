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

"""Data models for the AWS IAM MCP Server."""

from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional


class IamUser(BaseModel):
    """IAM User model."""

    user_name: str = Field(..., description='The name of the IAM user')
    user_id: str = Field(..., description='The unique identifier for the user')
    arn: str = Field(..., description='The Amazon Resource Name (ARN) of the user')
    path: str = Field(..., description='The path to the user')
    create_date: str = Field(..., description='The date and time when the user was created')
    password_last_used: Optional[str] = Field(
        None, description="The date and time when the user's password was last used"
    )


class IamRole(BaseModel):
    """IAM Role model."""

    role_name: str = Field(..., description='The name of the IAM role')
    role_id: str = Field(..., description='The unique identifier for the role')
    arn: str = Field(..., description='The Amazon Resource Name (ARN) of the role')
    path: str = Field(..., description='The path to the role')
    create_date: str = Field(..., description='The date and time when the role was created')
    assume_role_policy_document: Optional[str] = Field(
        None, description='The trust policy document'
    )
    description: Optional[str] = Field(None, description='The description of the role')
    max_session_duration: Optional[int] = Field(
        None, description='Maximum session duration in seconds'
    )


class IamPolicy(BaseModel):
    """IAM Policy model."""

    policy_name: str = Field(..., description='The name of the policy')
    policy_id: str = Field(..., description='The unique identifier for the policy')
    arn: str = Field(..., description='The Amazon Resource Name (ARN) of the policy')
    path: str = Field(..., description='The path to the policy')
    default_version_id: str = Field(
        ..., description='The identifier for the default version of the policy'
    )
    attachment_count: int = Field(..., description='The number of entities attached to the policy')
    permissions_boundary_usage_count: int = Field(
        0, description='The number of entities using this policy as a permissions boundary'
    )
    is_attachable: bool = Field(
        ..., description='Whether the policy can be attached to users, groups, or roles'
    )
    description: Optional[str] = Field(None, description='The description of the policy')
    create_date: str = Field(..., description='The date and time when the policy was created')
    update_date: str = Field(..., description='The date and time when the policy was last updated')


class IamGroup(BaseModel):
    """IAM Group model."""

    group_name: str = Field(..., description='The name of the IAM group')
    group_id: str = Field(..., description='The unique identifier for the group')
    arn: str = Field(..., description='The Amazon Resource Name (ARN) of the group')
    path: str = Field(..., description='The path to the group')
    create_date: str = Field(..., description='The date and time when the group was created')


class AccessKey(BaseModel):
    """IAM Access Key model."""

    access_key_id: str = Field(..., description='The access key ID')
    status: str = Field(..., description='The status of the access key (Active or Inactive)')
    create_date: str = Field(..., description='The date and time when the access key was created')


class AttachedPolicy(BaseModel):
    """Attached Policy model."""

    policy_name: str = Field(..., description='The name of the policy')
    policy_arn: str = Field(..., description='The ARN of the policy')


class UserDetailsResponse(BaseModel):
    """Response model for detailed user information."""

    user: IamUser = Field(..., description='User details')
    attached_policies: List[AttachedPolicy] = Field(
        default_factory=list, description='List of attached managed policies'
    )
    inline_policies: List[str] = Field(
        default_factory=list, description='List of inline policy names'
    )
    groups: List[str] = Field(
        default_factory=list, description='List of group names the user belongs to'
    )
    access_keys: List[AccessKey] = Field(
        default_factory=list, description='List of access keys for the user'
    )


class UsersListResponse(BaseModel):
    """Response model for listing users."""

    users: List[IamUser] = Field(..., description='List of IAM users')
    is_truncated: bool = Field(False, description='Whether the response is truncated')
    marker: Optional[str] = Field(None, description='Marker for pagination')
    count: int = Field(..., description='Number of users returned')


class RolesListResponse(BaseModel):
    """Response model for listing roles."""

    roles: List[IamRole] = Field(..., description='List of IAM roles')
    is_truncated: bool = Field(False, description='Whether the response is truncated')
    marker: Optional[str] = Field(None, description='Marker for pagination')
    count: int = Field(..., description='Number of roles returned')


class PoliciesListResponse(BaseModel):
    """Response model for listing policies."""

    policies: List[IamPolicy] = Field(..., description='List of IAM policies')
    is_truncated: bool = Field(False, description='Whether the response is truncated')
    marker: Optional[str] = Field(None, description='Marker for pagination')
    count: int = Field(..., description='Number of policies returned')


class CreateUserResponse(BaseModel):
    """Response model for creating a user."""

    user: IamUser = Field(..., description='Created user details')
    message: str = Field(..., description='Success message')


class CreateRoleResponse(BaseModel):
    """Response model for creating a role."""

    role: IamRole = Field(..., description='Created role details')
    message: str = Field(..., description='Success message')


class CreateAccessKeyResponse(BaseModel):
    """Response model for creating an access key."""

    access_key_id: str = Field(..., description='The access key ID')
    secret_access_key: str = Field(..., description='The secret access key')
    status: str = Field(..., description='The status of the access key')
    user_name: str = Field(..., description='The name of the user')
    create_date: str = Field(..., description='The date and time when the access key was created')
    message: str = Field(..., description='Success message')
    warning: str = Field(..., description='Security warning about storing the secret key')


class OperationResponse(BaseModel):
    """Generic response model for operations."""

    message: str = Field(..., description='Operation result message')
    details: Optional[Dict[str, Any]] = Field(None, description='Additional operation details')


class PolicyAttachmentResponse(BaseModel):
    """Response model for policy attachment operations."""

    message: str = Field(..., description='Operation result message')
    user_name: Optional[str] = Field(None, description='The name of the user')
    role_name: Optional[str] = Field(None, description='The name of the role')
    policy_arn: str = Field(..., description='The ARN of the policy')


class SimulationResult(BaseModel):
    """Model for policy simulation result."""

    eval_action_name: str = Field(..., description='The action that was evaluated')
    eval_resource_name: str = Field(..., description='The resource that was evaluated')
    eval_decision: str = Field(..., description='The result of the evaluation (Allow, Deny, etc.)')
    matched_statements: List[Dict[str, Any]] = Field(
        default_factory=list, description='Statements that matched'
    )
    missing_context_values: List[str] = Field(
        default_factory=list, description='Context values that were missing'
    )


class PolicySimulationResponse(BaseModel):
    """Response model for policy simulation."""

    evaluation_results: List[SimulationResult] = Field(
        ..., description='List of evaluation results'
    )
    is_truncated: bool = Field(False, description='Whether the response is truncated')
    marker: Optional[str] = Field(None, description='Marker for pagination')
    policy_source_arn: str = Field(..., description='ARN of the principal that was simulated')


class GroupDetailsResponse(BaseModel):
    """Response model for detailed group information."""

    group: IamGroup = Field(..., description='Group details')
    users: List[str] = Field(default_factory=list, description='List of user names in the group')
    attached_policies: List[AttachedPolicy] = Field(
        default_factory=list, description='List of attached managed policies'
    )
    inline_policies: List[str] = Field(
        default_factory=list, description='List of inline policy names'
    )


class GroupsListResponse(BaseModel):
    """Response model for listing groups."""

    groups: List[IamGroup] = Field(..., description='List of IAM groups')
    is_truncated: bool = Field(False, description='Whether the response is truncated')
    marker: Optional[str] = Field(None, description='Marker for pagination')
    count: int = Field(..., description='Number of groups returned')


class CreateGroupResponse(BaseModel):
    """Response model for creating a group."""

    group: IamGroup = Field(..., description='Created group details')
    message: str = Field(..., description='Success message')


class GroupMembershipResponse(BaseModel):
    """Response model for group membership operations."""

    message: str = Field(..., description='Operation result message')
    group_name: str = Field(..., description='The name of the group')
    user_name: str = Field(..., description='The name of the user')


class GroupPolicyAttachmentResponse(BaseModel):
    """Response model for group policy attachment operations."""

    message: str = Field(..., description='Operation result message')
    group_name: str = Field(..., description='The name of the group')
    policy_arn: str = Field(..., description='The ARN of the policy')


class InlinePolicy(BaseModel):
    """Inline Policy model."""

    policy_name: str = Field(..., description='The name of the inline policy')
    policy_document: str = Field(..., description='The policy document in JSON format')


class InlinePolicyResponse(BaseModel):
    """Response model for inline policy operations."""

    policy_name: str = Field(..., description='The name of the policy')
    policy_document: str = Field(..., description='The policy document in JSON format')
    user_name: Optional[str] = Field(None, description='The name of the user (for user policies)')
    role_name: Optional[str] = Field(None, description='The name of the role (for role policies)')
    message: str = Field(..., description='Operation result message')


class InlinePolicyListResponse(BaseModel):
    """Response model for listing inline policies."""

    policy_names: List[str] = Field(..., description='List of inline policy names')
    user_name: Optional[str] = Field(None, description='The name of the user (for user policies)')
    role_name: Optional[str] = Field(None, description='The name of the role (for role policies)')
    count: int = Field(..., description='Number of policies returned')


class ManagedPolicyResponse(BaseModel):
    """Response model for managed policy document operations."""

    policy_arn: str = Field(..., description='The ARN of the managed policy')
    policy_name: str = Field(..., description='The name of the policy')
    version_id: str = Field(..., description='The version ID of the policy')
    policy_document: str = Field(..., description='The policy document in JSON format')
    is_default_version: bool = Field(..., description='Whether this is the default version')
    create_date: str = Field(..., description='The date and time when this version was created')
    message: str = Field(..., description='Operation result message')
