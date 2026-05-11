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

"""get_job_status tool — aggregated job status snapshot for IDE agent polling."""

import asyncio
import time
import uuid
from awslabs.aws_transform_mcp_server.audit import audited_tool
from awslabs.aws_transform_mcp_server.config_store import is_fes_available
from awslabs.aws_transform_mcp_server.guidance_nudge import job_needs_check
from awslabs.aws_transform_mcp_server.tool_utils import (
    READ_ONLY,
    error_result,
    failure_result,
    success_result,
)
from awslabs.aws_transform_mcp_server.tools.chat._common import (
    build_metadata,
    build_timeout_data,
    format_response,
    poll_for_response,
)
from awslabs.aws_transform_mcp_server.transform_api_client import call_transform_api, paginate_all
from awslabs.aws_transform_mcp_server.transform_api_models import (
    BatchGetMessageRequest,
    ChatJobMetadata,
    GetJobRequest,
    ListJobPlanStepsRequest,
    ListMessagesRequest,
    ListWorklogsRequest,
    Metadata,
    ResourcesOnScreen,
    SendMessageRequest,
    WorkspaceMetadata,
)
from loguru import logger
from mcp.server.fastmcp import Context
from pydantic import Field
from typing import Annotated, Any, Dict, List, Optional


_TERMINAL_JOB_STATUSES = frozenset({'COMPLETED', 'FAILED', 'STOPPED'})

_TERMINAL_HITL_STATUSES = frozenset(
    {
        'CANCELLED',
        'CLOSED',
        'CLOSED_PENDING_NEXT_TASK',
        'DELIVERED',
    }
)

_ACTIONABLE_HITL_STATUSES = (
    'IN_PROGRESS',
    'AWAITING_HUMAN_INPUT',
    'AWAITING_APPROVAL',
)

_DEFAULT_STATUS_MESSAGE = (
    'What is the current status and what are the next steps needed from the user?'
)

TOOL_DESCRIPTION = (
    'Check the status of a running AWS Transform job.\n\n'
    'By default, asks the Transform assistant for a concise status summary '
    '(uses send_message internally). Pass an optional message to ask a '
    'specific question.\n\n'
    'Set detailed=true to get the full raw snapshot: job metadata, worklogs, '
    'HITL tasks, messages, and plan steps with _pollingGuidance.'
)


class JobStatusHandler:
    """Registers and handles the get_job_status tool."""

    def __init__(self, mcp: Any) -> None:
        """Register the get_job_status tool on the given MCP server."""
        audited_tool(
            mcp,
            'get_job_status',
            title='Get Job Status',
            annotations=READ_ONLY,
            description=TOOL_DESCRIPTION,
        )(self.get_job_status)

    async def get_job_status(
        self,
        ctx: Context,
        workspaceId: Annotated[str, Field(description='Workspace ID (UUID format)')],
        jobId: Annotated[str, Field(description='Job ID (UUID format)')],
        detailed: Annotated[
            Optional[bool],
            Field(
                description=(
                    'Set to true for full raw snapshot (job, worklogs, tasks, messages, plan). '
                    'Default false returns a concise assistant summary.'
                ),
            ),
        ] = False,
        message: Annotated[
            Optional[str],
            Field(
                description=(
                    'Custom question to ask the assistant. '
                    'Only used when detailed is false. '
                    'Defaults to a standard status inquiry.'
                ),
            ),
        ] = None,
    ) -> Dict[str, Any]:
        """Fetch job status — concise assistant summary by default, full snapshot when detailed."""
        if not is_fes_available():
            return error_result(
                'NOT_CONFIGURED',
                'Not connected to AWS Transform.',
                'Call configure with authMode "cookie" or "sso".',
            )

        nudge = job_needs_check(jobId)
        if nudge:
            return error_result(
                'INSTRUCTIONS_REQUIRED',
                nudge,
                f'Call load_instructions with workspaceId and jobId="{jobId}".',
            )

        if detailed:
            return await self._detailed_status(workspaceId, jobId)
        return await self._summary_status(workspaceId, jobId, message)

    async def _summary_status(
        self, workspaceId: str, jobId: str, message: Optional[str]
    ) -> Dict[str, Any]:
        """Send a message to the assistant and return its status summary with recent worklogs."""
        try:
            metadata = build_metadata(workspaceId, jobId)
            start_timestamp = time.time()
            text = message or _DEFAULT_STATUS_MESSAGE

            body = SendMessageRequest(
                text=text,
                idempotencyToken=str(uuid.uuid4()),
                metadata=metadata,
            )

            send_result, worklogs_result = await asyncio.gather(
                call_transform_api('SendMessage', body),
                call_transform_api(
                    'ListWorklogs',
                    ListWorklogsRequest(
                        workspaceId=workspaceId,
                        jobId=jobId,
                    ),
                ),
                return_exceptions=True,
            )

            worklogs = _unwrap_or_none(worklogs_result, 'ListWorklogs')

            if isinstance(send_result, Exception):
                raise send_result

            sent_msg = (
                send_result.get('message', send_result)
                if isinstance(send_result, dict)
                else send_result
            )
            sent_message_id = sent_msg.get('messageId') if isinstance(sent_msg, dict) else None

            if not sent_message_id:
                return error_result(
                    'MESSAGE_ID_EXTRACTION_FAILED',
                    'SendMessage succeeded but messageId could not be extracted.',
                    'Retry with detailed=true for the full data snapshot.',
                )

            result = await poll_for_response(
                metadata,
                workspaceId,
                sent_message_id,
                max_attempts=30,
                start_timestamp=start_timestamp,
            )

            if result['terminal']:
                resp = format_response(result['terminal'])
                if result['is_error']:
                    return error_result(
                        'ASSISTANT_ERROR',
                        resp.get('text') or 'The assistant returned an error.',
                        'Retry with detailed=true for the full data snapshot.',
                    )
                return success_result(
                    {
                        'sentMessage': sent_msg,
                        'response': resp,
                        'recentWorklogs': worklogs,
                    }
                )

            timeout_data = build_timeout_data(
                60,
                result['last_thinking'],
                workspaceId,
                sent_message_id,
                jobId,
            )
            timeout_data['sentMessage'] = sent_msg
            timeout_data['recentWorklogs'] = worklogs
            return success_result(timeout_data)
        except Exception as exc:
            return failure_result(exc)

    async def _detailed_status(self, workspaceId: str, jobId: str) -> Dict[str, Any]:
        """Fetch the full data snapshot (original get_job_status behavior)."""
        try:
            results = await asyncio.gather(
                call_transform_api(
                    'GetJob',
                    GetJobRequest(workspaceId=workspaceId, jobId=jobId),
                ),
                call_transform_api(
                    'ListWorklogs',
                    ListWorklogsRequest(workspaceId=workspaceId, jobId=jobId),
                ),
                paginate_all(
                    'ListHitlTasks',
                    {
                        'workspaceId': workspaceId,
                        'jobId': jobId,
                        'taskType': 'NORMAL',
                        'taskFilter': {
                            'taskStatuses': _ACTIONABLE_HITL_STATUSES,
                        },
                    },
                    'hitlTasks',
                ),
                _fetch_recent_messages(workspaceId, jobId),
                _fetch_plan(workspaceId, jobId),
                return_exceptions=True,
            )

            job = _unwrap_or_none(results[0], 'GetJob')
            worklogs = _unwrap_or_none(results[1], 'ListWorklogs')
            tasks = _unwrap_or_none(results[2], 'ListHitlTasks')
            messages = _unwrap_or_none(results[3], 'messages')
            plan = _unwrap_or_none(results[4], 'plan')

            if job is None:
                return error_result(
                    'REQUEST_FAILED',
                    'Failed to fetch job metadata — cannot determine job status.',
                    f'Try get_resource(resource="job", workspaceId="{workspaceId}", '
                    f'jobId="{jobId}") for details.',
                )

            job_status = job.get('status', 'UNKNOWN') if isinstance(job, dict) else 'UNKNOWN'
            is_terminal = job_status in _TERMINAL_JOB_STATUSES

            pending_tasks = _extract_pending_tasks(tasks)

            data: Dict[str, Any] = {
                'job': job,
                'worklogs': worklogs,
                'tasks': tasks,
                'messages': messages,
                'plan': plan,
                '_pollingGuidance': {
                    'isTerminal': is_terminal,
                    'jobStatus': job_status,
                    'hasPendingTasks': len(pending_tasks) > 0,
                    'pendingTaskCount': len(pending_tasks),
                },
            }

            return success_result(data)

        except Exception as exc:
            return failure_result(exc)


async def _fetch_recent_messages(
    workspace_id: str,
    job_id: str,
) -> Dict[str, Any]:
    """Fetch the most recent messages for a job (up to 50)."""
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
        ListMessagesRequest(metadata=metadata, maxResults=50),
    )
    message_ids: List[str] = (
        list_result.get('messageIds', []) if isinstance(list_result, dict) else []
    )
    if not message_ids:
        return {'messages': []}

    batch_result = await call_transform_api(
        'BatchGetMessage',
        BatchGetMessageRequest(messageIds=message_ids[:100], workspaceId=workspace_id),
    )
    messages = batch_result.get('messages', []) if isinstance(batch_result, dict) else []
    return {'messages': messages}


async def _fetch_plan(
    workspace_id: str,
    job_id: str,
) -> Optional[Dict[str, Any]]:
    """Fetch plan steps for the job."""
    result = await call_transform_api(
        'ListJobPlanSteps',
        ListJobPlanStepsRequest(workspaceId=workspace_id, jobId=job_id),
    )
    if not result:
        return None
    return result


def _unwrap_or_none(result: Any, label: str) -> Any:
    """Return the result if successful, or None with a logged warning if it was an exception."""
    if isinstance(result, Exception):
        logger.warning('[get_job_status] {} failed: {}', label, result)
        return None
    return result


def _extract_pending_tasks(tasks: Any) -> List[Dict[str, Any]]:
    """Extract tasks that still need action.

    Server-side filtering already limits to actionable statuses, but guard
    against any terminal tasks that slip through.
    """
    if not isinstance(tasks, dict):
        return []
    task_list = tasks.get('hitlTasks', [])
    if not isinstance(task_list, list):
        return []
    return [
        t
        for t in task_list
        if isinstance(t, dict) and t.get('status') not in _TERMINAL_HITL_STATUSES
    ]
