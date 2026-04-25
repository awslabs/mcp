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
from awslabs.aws_transform_mcp_server.audit import audited_tool
from awslabs.aws_transform_mcp_server.config_store import is_configured
from awslabs.aws_transform_mcp_server.fes_client import call_fes, paginate_all
from awslabs.aws_transform_mcp_server.guidance_nudge import job_needs_check
from awslabs.aws_transform_mcp_server.tool_utils import (
    READ_ONLY,
    error_result,
    failure_result,
    success_result,
)
from loguru import logger
from mcp.server.fastmcp import Context
from pydantic import Field
from typing import Any, Dict, List, Optional


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

TOOL_DESCRIPTION = (
    'Fetches a complete status snapshot for a long-running AWS Transform job: '
    'job metadata, worklogs, HITL tasks, messages, and plan steps.\n\n'
    '[CRITICAL] After each call, check _pollingGuidance.isTerminal in the response. '
    'If false: present all sections to the user (even if empty), then IMMEDIATELY '
    'call get_job_status again. Do NOT end your turn. Do NOT ask the user anything. '
    'Do NOT stop for pending HITL tasks. Keep polling every 1 minute until isTerminal is true '
    'or the user says stop.'
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
        workspaceId: str = Field(..., description='Workspace ID (UUID format)'),
        jobId: str = Field(..., description='Job ID (UUID format)'),
    ) -> Dict[str, Any]:
        """Fetch a unified job status snapshot for IDE agent polling."""
        if not is_configured():
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

        try:
            results = await asyncio.gather(
                call_fes('GetJob', {'workspaceId': workspaceId, 'jobId': jobId}),
                call_fes(
                    'ListWorklogs',
                    {'workspaceId': workspaceId, 'jobId': jobId},
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
                    'suggestedAction': _build_suggested_action(
                        job_status, is_terminal, pending_tasks
                    ),
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
    metadata = {
        'resourcesOnScreen': {
            'workspace': {
                'workspaceId': workspace_id,
                'jobs': [{'jobId': job_id, 'focusState': 'ACTIVE'}],
            },
        },
    }
    list_result = await call_fes(
        'ListMessages',
        {'metadata': metadata, 'maxResults': 50},
    )
    message_ids: List[str] = (
        list_result.get('messageIds', []) if isinstance(list_result, dict) else []
    )
    if not message_ids:
        return {'messages': []}

    batch_result = await call_fes(
        'BatchGetMessage',
        {'messageIds': message_ids[:100], 'workspaceId': workspace_id},
    )
    messages = batch_result.get('messages', []) if isinstance(batch_result, dict) else []
    return {'messages': messages}


async def _fetch_plan(
    workspace_id: str,
    job_id: str,
) -> Optional[Dict[str, Any]]:
    """Fetch plan steps for the job."""
    result = await call_fes(
        'ListJobPlanSteps',
        {'workspaceId': workspace_id, 'jobId': job_id},
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


_POLL_INSTRUCTION = (
    '[CRITICAL] Call get_job_status again in 1 minute. '
    'Do NOT end your turn. Do NOT ask the user any questions. '
    'Present all sections (job, worklogs, messages, tasks, plan) even if empty, '
    'then immediately call get_job_status again. '
    'Pending HITL tasks do NOT pause polling — the user responds while you poll. '
    'Stop ONLY when isTerminal is true or the user says stop.'
)


def _build_suggested_action(
    job_status: str,
    is_terminal: bool,
    pending_tasks: List[Dict[str, Any]],
) -> str:
    """Build a human-readable suggested action for the polling guidance."""
    if is_terminal:
        return f'Job {job_status.lower()}. No further polling needed.'

    if pending_tasks:
        task_ids = ', '.join(t.get('taskId', '?') for t in pending_tasks[:3])
        suffix = f' (and {len(pending_tasks) - 3} more)' if len(pending_tasks) > 3 else ''
        return (
            f'Job has {len(pending_tasks)} pending HITL task(s) that block progress: '
            f'{task_ids}{suffix}. '
            'Fetch task details with get_resource(resource="task") and present to the user. '
            f'{_POLL_INSTRUCTION}'
        )

    return f'Job is still running. {_POLL_INSTRUCTION}'
