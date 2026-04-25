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

"""Shared constants and validation logic for approve_hitl tools."""

from awslabs.aws_transform_mcp_server.config_store import is_configured
from awslabs.aws_transform_mcp_server.fes_client import call_fes
from awslabs.aws_transform_mcp_server.tool_utils import (
    error_result,
    failure_result,
    success_result,
)
from typing import Any, Dict


NOT_CONFIGURED_CODE = 'NOT_CONFIGURED'
NOT_CONFIGURED_MSG = 'Not connected to AWS Transform.'
NOT_CONFIGURED_ACTION = 'Call configure with authMode "cookie" or "sso".'


def not_configured_error() -> Dict[str, Any]:
    """Return a standard not-configured error result."""
    return error_result(NOT_CONFIGURED_CODE, NOT_CONFIGURED_MSG, NOT_CONFIGURED_ACTION)


async def validate_and_submit(
    workspaceId: str,
    jobId: str,
    taskId: str,
    action: str,
) -> Dict[str, Any]:
    """Fetch a task, validate it is TOOL_APPROVAL + AWAITING_APPROVAL, then submit.

    Calls SubmitCriticalHitlTask without humanArtifact.

    Args:
        workspaceId: The workspace identifier.
        jobId: The job identifier.
        taskId: The task identifier.
        action: 'APPROVE' or 'REJECT'.

    Returns:
        MCP result envelope (success or error).
    """
    if not is_configured():
        return not_configured_error()

    try:
        task_result = await call_fes(
            'GetHitlTask',
            {'workspaceId': workspaceId, 'jobId': jobId, 'taskId': taskId},
        )
        task = task_result.get('task', {})

        category = task.get('category')
        if category != 'TOOL_APPROVAL':
            return error_result(
                'WRONG_TASK_TYPE',
                f'Task {taskId} is category "{category}", not TOOL_APPROVAL.',
                'Use complete_task for non-TOOL_APPROVAL tasks.',
            )

        status = task.get('status')
        if status != 'AWAITING_APPROVAL':
            return error_result(
                'WRONG_STATUS',
                f'Task {taskId} is in status "{status}", not AWAITING_APPROVAL.',
                'Only tasks in AWAITING_APPROVAL status can be approved or denied.',
            )

        fes_result = await call_fes(
            'SubmitCriticalHitlTask',
            {
                'workspaceId': workspaceId,
                'jobId': jobId,
                'taskId': taskId,
                'action': action,
            },
        )
        return success_result(
            {
                'action': action,
                'taskId': taskId,
                'result': fes_result,
            }
        )
    except Exception as error:
        return failure_result(error)
