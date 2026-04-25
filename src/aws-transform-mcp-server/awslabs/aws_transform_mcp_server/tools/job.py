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

"""Job tool handlers for AWS Transform MCP server."""

import uuid
from awslabs.aws_transform_mcp_server.audit import audited_tool
from awslabs.aws_transform_mcp_server.config_store import is_configured
from awslabs.aws_transform_mcp_server.fes_client import call_fes
from awslabs.aws_transform_mcp_server.tool_utils import (
    error_result,
    failure_result,
    success_result,
)
from mcp.server.fastmcp import Context
from pydantic import Field
from typing import Any, Literal, Optional


_NOT_CONFIGURED_CODE = 'NOT_CONFIGURED'
_NOT_CONFIGURED_MSG = 'Not connected to AWS Transform.'
_NOT_CONFIGURED_ACTION = 'Call configure with authMode "cookie" or "sso".'


class JobHandler:
    """Registers job-related MCP tools."""

    def __init__(self, mcp: Any) -> None:
        """Register job tools on the MCP server."""
        audited_tool(mcp, 'create_job')(self.create_job)
        audited_tool(mcp, 'control_job')(self.control_job)
        audited_tool(mcp, 'delete_job')(self.delete_job)

    async def create_job(
        self,
        ctx: Context,
        workspaceId: str = Field(..., description='The workspace identifier'),
        jobName: str = Field(..., description='Name for the job'),
        objective: str = Field(..., description='The transformation objective'),
        intent: str = Field(..., description='The transformation intent'),
        jobType: Optional[str] = Field(None, description='The type of transformation'),
        orchestratorAgent: Optional[str] = Field(
            None,
            description=(
                'The orchestrator agent name (alphanumeric, hyphens, underscores). '
                'Only orchestrator agents can be used here -- not sub-agents. '
                'If the request fails with jobType, retry using orchestratorAgent instead.'
            ),
        ),
    ) -> dict:
        """Create a new code transformation job and immediately start it.

        Only orchestrator agents can create jobs. Use list_resources with
        resource="agents" and agentType="ORCHESTRATOR_AGENT" to discover
        available agents before creating a job.
        """
        if not is_configured():
            return error_result(_NOT_CONFIGURED_CODE, _NOT_CONFIGURED_MSG, _NOT_CONFIGURED_ACTION)

        _jobType: Optional[str] = jobType if isinstance(jobType, str) else None
        _orchestratorAgent: Optional[str] = (
            orchestratorAgent if isinstance(orchestratorAgent, str) else None
        )

        try:
            body: dict = {
                'workspaceId': workspaceId,
                'jobName': jobName,
                'jobType': _jobType,
                'objective': objective,
                'intent': intent,
                'idempotencyToken': str(uuid.uuid4()),
            }
            if _orchestratorAgent is not None:
                body['orchestratorAgent'] = _orchestratorAgent

            result = await call_fes('CreateJob', body)
            job_id = result['jobId'] if isinstance(result, dict) else result
            await call_fes('StartJob', {'workspaceId': workspaceId, 'jobId': job_id})
            status = await call_fes('GetJob', {'workspaceId': workspaceId, 'jobId': job_id})
            return success_result(status)
        except Exception as error:
            return failure_result(error)

    async def control_job(
        self,
        ctx: Context,
        workspaceId: str = Field(..., description='The workspace identifier'),
        jobId: str = Field(..., description='The job identifier'),
        action: Literal['start', 'stop'] = Field(
            ..., description='Whether to start or stop the job'
        ),
    ) -> dict:
        """Start or stop a transformation job."""
        if not is_configured():
            return error_result(_NOT_CONFIGURED_CODE, _NOT_CONFIGURED_MSG, _NOT_CONFIGURED_ACTION)

        try:
            operation = 'StartJob' if action == 'start' else 'StopJob'
            await call_fes(operation, {'workspaceId': workspaceId, 'jobId': jobId})
            status = await call_fes('GetJob', {'workspaceId': workspaceId, 'jobId': jobId})
            return success_result(status)
        except Exception as error:
            return failure_result(error)

    async def delete_job(
        self,
        ctx: Context,
        workspaceId: str = Field(..., description='The workspace identifier'),
        jobId: str = Field(..., description='The job identifier'),
        confirm: bool = Field(..., description='Must be true to confirm deletion.'),
    ) -> dict:
        """Permanently delete a transformation job."""
        if not is_configured():
            return error_result(_NOT_CONFIGURED_CODE, _NOT_CONFIGURED_MSG, _NOT_CONFIGURED_ACTION)

        if not confirm:
            return error_result(
                'VALIDATION_ERROR',
                'Delete requires explicit confirmation. Set confirm to true.',
                'Set confirm to true.',
            )

        try:
            data = await call_fes('DeleteJob', {'workspaceId': workspaceId, 'jobId': jobId})
            return success_result(data)
        except Exception as error:
            return failure_result(error)
