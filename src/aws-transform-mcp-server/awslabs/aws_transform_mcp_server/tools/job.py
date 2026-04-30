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
from awslabs.aws_transform_mcp_server.config_store import is_fes_available
from awslabs.aws_transform_mcp_server.fes_client import call_fes
from awslabs.aws_transform_mcp_server.fes_models import (
    CreateJobRequest,
    DeleteJobRequest,
    GetJobRequest,
    StartJobRequest,
    StopJobRequest,
)
from awslabs.aws_transform_mcp_server.tool_utils import (
    CREATE,
    DELETE_IDEMPOTENT,
    MUTATE,
    error_result,
    failure_result,
    format_job_response,
    success_result,
)
from mcp.server.fastmcp import Context
from pydantic import Field
from typing import Annotated, Any, Literal, Optional


_NOT_CONFIGURED_CODE = 'NOT_CONFIGURED'
_NOT_CONFIGURED_MSG = 'Not connected to AWS Transform.'
_NOT_CONFIGURED_ACTION = 'Call configure with authMode "cookie" or "sso".'


class JobHandler:
    """Registers job-related MCP tools."""

    def __init__(self, mcp: Any) -> None:
        """Register job tools on the MCP server."""
        audited_tool(mcp, 'create_job', title='Create Job', annotations=MUTATE)(self.create_job)
        audited_tool(mcp, 'control_job', title='Control Job', annotations=CREATE)(self.control_job)
        audited_tool(mcp, 'delete_job', title='Delete Job', annotations=DELETE_IDEMPOTENT)(
            self.delete_job
        )

    async def create_job(
        self,
        ctx: Context,
        workspaceId: Annotated[str, Field(description='The workspace identifier')],
        jobName: Annotated[str, Field(description='Name for the job')],
        objective: Annotated[str, Field(description='The transformation objective')],
        intent: Annotated[str, Field(description='The transformation intent')],
        jobType: Annotated[Optional[str], Field(description='The type of transformation')] = None,
        orchestratorAgent: Annotated[
            Optional[str],
            Field(
                description=(
                    'The orchestrator agent name (alphanumeric, hyphens, underscores). '
                    'Only orchestrator agents can be used here -- not sub-agents. '
                    'If the request fails with jobType, retry using orchestratorAgent instead.'
                ),
            ),
        ] = None,
    ) -> dict:
        """Create a new code transformation job and immediately start it.

        Only orchestrator agents can create jobs. Use list_resources with
        resource="agents" and agentType="ORCHESTRATOR_AGENT" to discover
        available agents before creating a job.
        """
        if not is_fes_available():
            return error_result(_NOT_CONFIGURED_CODE, _NOT_CONFIGURED_MSG, _NOT_CONFIGURED_ACTION)

        try:
            create_req = CreateJobRequest(
                workspaceId=workspaceId,
                jobName=jobName,
                jobType=jobType,
                objective=objective,
                intent=intent,
                idempotencyToken=str(uuid.uuid4()),
                orchestratorAgent=orchestratorAgent,
            )

            result = await call_fes('CreateJob', create_req)
            job_id = result['jobId'] if isinstance(result, dict) else result
            await call_fes(
                'StartJob',
                StartJobRequest(workspaceId=workspaceId, jobId=job_id),
            )
            status = await call_fes(
                'GetJob',
                GetJobRequest(workspaceId=workspaceId, jobId=job_id),
            )
            return success_result(format_job_response(status))
        except Exception as error:
            return failure_result(error)

    async def control_job(
        self,
        ctx: Context,
        workspaceId: Annotated[str, Field(description='The workspace identifier')],
        jobId: Annotated[str, Field(description='The job identifier')],
        action: Annotated[
            Literal['start', 'stop'],
            Field(
                description='Whether to start or stop the job',
            ),
        ],
    ) -> dict:
        """Start or stop a transformation job."""
        if not is_fes_available():
            return error_result(_NOT_CONFIGURED_CODE, _NOT_CONFIGURED_MSG, _NOT_CONFIGURED_ACTION)

        try:
            if action == 'start':
                await call_fes(
                    'StartJob',
                    StartJobRequest(workspaceId=workspaceId, jobId=jobId),
                )
            else:
                await call_fes(
                    'StopJob',
                    StopJobRequest(workspaceId=workspaceId, jobId=jobId),
                )
            status = await call_fes(
                'GetJob',
                GetJobRequest(workspaceId=workspaceId, jobId=jobId),
            )
            return success_result(format_job_response(status))
        except Exception as error:
            return failure_result(error)

    async def delete_job(
        self,
        ctx: Context,
        workspaceId: Annotated[str, Field(description='The workspace identifier')],
        jobId: Annotated[str, Field(description='The job identifier')],
        confirm: Annotated[bool, Field(description='Must be true to confirm deletion.')],
    ) -> dict:
        """Permanently delete a transformation job."""
        if not is_fes_available():
            return error_result(_NOT_CONFIGURED_CODE, _NOT_CONFIGURED_MSG, _NOT_CONFIGURED_ACTION)

        if not confirm:
            return error_result(
                'VALIDATION_ERROR',
                'Delete requires explicit confirmation. Set confirm to true.',
                'Set confirm to true.',
            )

        try:
            data = await call_fes(
                'DeleteJob',
                DeleteJobRequest(workspaceId=workspaceId, jobId=jobId),
            )
            return success_result(data)
        except Exception as error:
            return failure_result(error)
