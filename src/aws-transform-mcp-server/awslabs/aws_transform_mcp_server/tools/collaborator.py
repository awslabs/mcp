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

"""Collaborator tool handler for AWS Transform MCP server."""

from awslabs.aws_transform_mcp_server.audit import audited_tool
from awslabs.aws_transform_mcp_server.config_store import is_fes_available
from awslabs.aws_transform_mcp_server.tool_utils import (
    DELETE_IDEMPOTENT,
    error_result,
    failure_result,
    success_result,
)
from awslabs.aws_transform_mcp_server.transform_api_client import call_transform_api
from awslabs.aws_transform_mcp_server.transform_api_models import (
    DeleteSelfRoleMappingsRequest,
    DeleteUserRoleMappingsRequest,
    PutUserRoleMappingsRequest,
)
from mcp.server.fastmcp import Context
from pydantic import Field
from typing import Annotated, Any, Dict, Literal, Optional


_NOT_CONFIGURED_CODE = 'NOT_CONFIGURED'
_NOT_CONFIGURED_MSG = 'Not connected to AWS Transform.'
_NOT_CONFIGURED_ACTION = 'Call configure with authMode "cookie" or "sso".'


class CollaboratorHandler:
    """Registers the manage_collaborator tool."""

    def __init__(self, mcp: Any) -> None:
        """Register manage_collaborator on the MCP server."""
        audited_tool(
            mcp, 'manage_collaborator', title='Manage Collaborator', annotations=DELETE_IDEMPOTENT
        )(self.manage_collaborator)

    async def manage_collaborator(
        self,
        ctx: Context,
        workspaceId: Annotated[str, Field(description='The workspace ID')],
        action: Annotated[
            Literal['put', 'remove', 'leave'],
            Field(
                description=(
                    'put = add or change role; '
                    'remove = admin removes another user; '
                    'leave = caller removes themselves'
                )
            ),
        ],
        userId: Annotated[
            Optional[str],
            Field(
                description='Target user ID. Required for "put" and "remove". Omit for "leave".',
            ),
        ] = None,
        role: Annotated[
            Optional[Literal['ADMIN', 'APPROVER', 'CONTRIBUTOR', 'READ_ONLY']],
            Field(description='Role to assign. Required for "put".'),
        ] = None,
        confirm: Annotated[
            Optional[bool],
            Field(
                description='Must be true for destructive actions ("remove", "leave").',
            ),
        ] = None,
    ) -> Dict[str, Any]:
        """Add, update, or remove a workspace collaborator.

        Actions:
        - put: add a user OR change their role (upsert). Requires userId and role.
        - remove: admin removes ANOTHER user. Requires userId and confirm:true.
        - leave: caller leaves the workspace (self-removal). Requires confirm:true; do NOT pass userId.

        Role enum: ADMIN | APPROVER | CONTRIBUTOR | READ_ONLY.
        To list current collaborators use list_resources resource="collaborators".
        To find a userId by name or email use list_resources resource="users".
        Requires configure (cookie or sso).
        """
        if not is_fes_available():
            return error_result(_NOT_CONFIGURED_CODE, _NOT_CONFIGURED_MSG, _NOT_CONFIGURED_ACTION)

        try:
            if action == 'put':
                if not userId:
                    return error_result('VALIDATION_ERROR', 'userId is required for action="put".')
                if not role:
                    return error_result('VALIDATION_ERROR', 'role is required for action="put".')
                result = await call_transform_api(
                    'PutUserRoleMappings',
                    PutUserRoleMappingsRequest(
                        workspaceId=workspaceId,
                        userId=userId,
                        roles=[role],
                    ),
                )
                return success_result(result)

            if action == 'remove':
                if not userId:
                    return error_result(
                        'VALIDATION_ERROR', 'userId is required for action="remove".'
                    )
                if not confirm:
                    return error_result(
                        'VALIDATION_ERROR',
                        'Removing a collaborator requires confirm:true.',
                        'Set confirm:true to proceed.',
                    )
                result = await call_transform_api(
                    'DeleteUserRoleMappings',
                    DeleteUserRoleMappingsRequest(workspaceId=workspaceId, userId=userId),
                )
                data = {'removed': True, 'workspaceId': workspaceId, 'userId': userId}
                if isinstance(result, dict):
                    data.update(result)
                return success_result(data)

            # action == 'leave'
            if userId:
                return error_result(
                    'VALIDATION_ERROR',
                    'userId must not be provided for action="leave" (it removes the caller).',
                    'Omit userId for "leave", or use action="remove" to remove another user.',
                )
            if not confirm:
                return error_result(
                    'VALIDATION_ERROR',
                    'Leaving a workspace requires confirm:true.',
                    'Set confirm:true to proceed.',
                )
            result = await call_transform_api(
                'DeleteSelfRoleMappings',
                DeleteSelfRoleMappingsRequest(workspaceId=workspaceId),
            )
            data = {'left': True, 'workspaceId': workspaceId}
            if isinstance(result, dict):
                data.update(result)
            return success_result(data)

        except Exception as error:
            return failure_result(error)
