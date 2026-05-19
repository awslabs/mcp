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

import asyncio
import uuid
from awslabs.aws_transform_mcp_server.audit import audited_tool
from awslabs.aws_transform_mcp_server.config_store import is_fes_available
from awslabs.aws_transform_mcp_server.tool_utils import (
    CREATE,
    DELETE_IDEMPOTENT,
    MUTATE,
    error_result,
    failure_result,
    format_job_response,
    success_result,
)
from awslabs.aws_transform_mcp_server.transform_api_client import call_transform_api
from awslabs.aws_transform_mcp_server.transform_api_models import (
    BatchGetMessageRequest,
    ChatJobMetadata,
    CreateJobRequest,
    DeleteJobRequest,
    GetJobRequest,
    ListMessagesRequest,
    Metadata,
    ResourcesOnScreen,
    StartJobRequest,
    StopJobRequest,
    WorkspaceMetadata,
)
from loguru import logger
from mcp.server.fastmcp import Context
from pydantic import Field
from typing import Annotated, Any, Dict, List, Literal, Optional


_NOT_CONFIGURED_CODE = 'NOT_CONFIGURED'
_NOT_CONFIGURED_MSG = 'Not connected to AWS Transform.'
_NOT_CONFIGURED_ACTION = 'Call configure with authMode "cookie" or "sso".'

_POLL_INTERVAL = 3  # seconds between GetJob polls
_POLL_MAX_WAIT = 90  # max seconds to wait for job to exit ASSESSING
_TRANSITIONAL_STATUSES = {'CREATED', 'STARTING', 'ASSESSING'}


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

        Polls until the agent is ready for interaction (job exits ASSESSING
        state), then returns the job status along with any initial messages
        from the agent.

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

            result = await call_transform_api('CreateJob', create_req)
            job_id = result['jobId'] if isinstance(result, dict) else result
            await call_transform_api(
                'StartJob',
                StartJobRequest(workspaceId=workspaceId, jobId=job_id),
            )

            # Poll until job exits transitional states (CREATED/STARTING/ASSESSING)
            status = await self._poll_until_ready(workspaceId, job_id)
            job_data = format_job_response(status)

            # Fetch initial messages from the agent
            messages = await self._fetch_initial_messages(workspaceId, job_id)

            result_data: Dict[str, Any] = {'job': job_data}
            if messages:
                result_data['messages'] = messages
            return success_result(result_data)
        except Exception as error:
            return failure_result(error)

    async def _poll_until_ready(self, workspace_id: str, job_id: str) -> dict:
        """Poll GetJob until status exits ASSESSING/STARTING/CREATED."""
        elapsed = 0.0
        status: dict = {}
        current = ''
        while elapsed < _POLL_MAX_WAIT:
            status = await call_transform_api(
                'GetJob',
                GetJobRequest(workspaceId=workspace_id, jobId=job_id),
            )
            job = status.get('job', status) if isinstance(status, dict) else {}
            current = job.get('status', '') if isinstance(job, dict) else ''
            if current not in _TRANSITIONAL_STATUSES:
                logger.info('[create_job] Job {} ready: status={}', job_id, current)
                return status
            await asyncio.sleep(_POLL_INTERVAL)
            elapsed += _POLL_INTERVAL
        logger.warning(
            '[create_job] Job {} still in {} after {}s', job_id, current, _POLL_MAX_WAIT
        )
        return status

    async def _fetch_initial_messages(
        self, workspace_id: str, job_id: str
    ) -> List[Dict[str, Any]]:
        """List and fetch initial messages for the job."""
        try:
            metadata = Metadata(
                resourcesOnScreen=ResourcesOnScreen(
                    workspace=WorkspaceMetadata(
                        workspaceId=workspace_id,
                        jobs=[ChatJobMetadata(jobId=job_id, focusState='ACTIVE')],
                    ),
                ),
            )
            list_result = await call_transform_api(
                'ListMessages',
                ListMessagesRequest(metadata=metadata, maxResults=10),
            )
            message_ids: List[str] = (
                list_result.get('messageIds', []) if isinstance(list_result, dict) else []
            )
            if not message_ids:
                return []
            batch_result = await call_transform_api(
                'BatchGetMessage',
                BatchGetMessageRequest(messageIds=message_ids[:10], workspaceId=workspace_id),
            )
            messages = batch_result.get('messages', []) if isinstance(batch_result, dict) else []
            return [
                {k: m[k] for k in ('messageId', 'body', 'sender', 'createdAt') if k in m}
                for m in messages
                if isinstance(m, dict)
            ]
        except Exception as exc:
            logger.debug('[create_job] Failed to fetch initial messages: {}', exc)
            return []

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
                await call_transform_api(
                    'StartJob',
                    StartJobRequest(workspaceId=workspaceId, jobId=jobId),
                )
            else:
                await call_transform_api(
                    'StopJob',
                    StopJobRequest(workspaceId=workspaceId, jobId=jobId),
                )
            status = await call_transform_api(
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
            data = await call_transform_api(
                'DeleteJob',
                DeleteJobRequest(workspaceId=workspaceId, jobId=jobId),
            )
            return success_result(data)
        except Exception as error:
            return failure_result(error)
