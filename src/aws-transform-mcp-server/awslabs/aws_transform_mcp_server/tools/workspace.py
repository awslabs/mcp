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

"""Workspace tool handlers for AWS Transform MCP server."""

import uuid
from awslabs.aws_transform_mcp_server.audit import audited_tool
from awslabs.aws_transform_mcp_server.config_store import is_fes_available
from awslabs.aws_transform_mcp_server.tool_utils import (
    DELETE_IDEMPOTENT,
    MUTATE,
    error_result,
    failure_result,
    success_result,
)
from awslabs.aws_transform_mcp_server.transform_api_client import call_transform_api
from awslabs.aws_transform_mcp_server.transform_api_models import (
    CreateWorkspaceRequest,
    DeleteWorkspaceRequest,
)
from mcp.server.fastmcp import Context
from pydantic import Field
from typing import Annotated, Any, Optional


_NOT_CONFIGURED_CODE = 'NOT_CONFIGURED'
_NOT_CONFIGURED_MSG = 'Not connected to AWS Transform.'
_NOT_CONFIGURED_ACTION = 'Call configure with authMode "cookie" or "sso".'


class WorkspaceHandler:
    """Registers workspace-related MCP tools."""

    def __init__(self, mcp: Any) -> None:
        """Register workspace tools on the MCP server."""
        audited_tool(mcp, 'create_workspace', title='Create Workspace', annotations=MUTATE)(
            self.create_workspace
        )
        audited_tool(
            mcp, 'delete_workspace', title='Delete Workspace', annotations=DELETE_IDEMPOTENT
        )(self.delete_workspace)

    async def create_workspace(
        self,
        ctx: Context,
        name: Annotated[str, Field(description='Name for the workspace')],
        description: Annotated[Optional[str], Field(description='Optional description')] = None,
    ) -> dict:
        """Create a new transformation workspace.

        Requires configure (cookie or sso).
        """
        if not is_fes_available():
            return error_result(_NOT_CONFIGURED_CODE, _NOT_CONFIGURED_MSG, _NOT_CONFIGURED_ACTION)

        try:
            result = await call_transform_api(
                'CreateWorkspace',
                CreateWorkspaceRequest(
                    name=name,
                    description=description,
                    idempotencyToken=str(uuid.uuid4()),
                ),
            )
            workspace = result.get('workspace', result) if isinstance(result, dict) else result
            return success_result(workspace)
        except Exception as error:
            return failure_result(error)

    async def delete_workspace(
        self,
        ctx: Context,
        workspaceId: Annotated[str, Field(description='The workspace ID to delete')],
        confirm: Annotated[bool, Field(description='Must be true to confirm deletion')],
    ) -> dict:
        """Permanently delete a workspace.

        This is irreversible -- all jobs, artifacts, and connectors in the
        workspace will be lost.  Requires confirm=True.
        """
        if not is_fes_available():
            return error_result(_NOT_CONFIGURED_CODE, _NOT_CONFIGURED_MSG, _NOT_CONFIGURED_ACTION)

        if not confirm:
            return error_result(
                'VALIDATION_ERROR',
                'Workspace deletion requires explicit confirmation. Set confirm to true.',
                'Set confirm to true to proceed with deletion.',
            )

        try:
            result = await call_transform_api(
                'DeleteWorkspace', DeleteWorkspaceRequest(id=workspaceId)
            )
            data = {'deleted': True, 'workspaceId': workspaceId}
            if result and isinstance(result, dict):
                data.update(result)
            return success_result(data)
        except Exception as error:
            return failure_result(error)
