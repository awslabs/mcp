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

"""Check the current status of a TOOL_APPROVAL task."""

from awslabs.aws_transform_mcp_server.config_store import is_configured
from awslabs.aws_transform_mcp_server.fes_client import call_fes
from awslabs.aws_transform_mcp_server.tool_utils import (
    error_result,
    failure_result,
    success_result,
)
from awslabs.aws_transform_mcp_server.tools.approve_hitl._common import not_configured_error
from mcp.server.fastmcp import Context
from pydantic import Field
from typing import Any, Dict


async def get_approval_status(
    ctx: Context,
    workspaceId: str = Field(..., description='The workspace identifier'),
    jobId: str = Field(..., description='The job identifier'),
    taskId: str = Field(..., description='The task identifier to check'),
) -> Dict[str, Any]:
    """Check the current status of a TOOL_APPROVAL task.

    Use after calling approve_tool_approval or deny_tool_approval to confirm
    the action was applied. Also use to inspect task details before approving
    or denying — the response includes the full task object with agentArtifact,
    title, description, and severity.

    Unlike get_resource(resource="task"), this tool validates the task is
    category=TOOL_APPROVAL and returns the raw task object without HITL
    schema enrichment (_responseTemplate, _responseHint, _outputSchema).
    Use this tool for the approval workflow; use get_resource for full
    task details with artifact content and response templates.

    Returns: { task: { taskId, title, status, category, severity,
    uxComponentId, agentArtifact, action, ... } }

    TOOL_APPROVAL task lifecycle:
    - AWAITING_APPROVAL — pending, not yet acted on
    - SUBMITTED — approve or deny action applied, agent processing the decision
    - CLOSED / CANCELLED / CLOSED_PENDING_NEXT_TASK — terminal

    The action field ("APPROVE" or "REJECT") indicates which decision was made.

    Requires browser/SSO auth — call configure first.
    """
    if not is_configured():
        return not_configured_error()

    try:
        result = await call_fes(
            'GetHitlTask',
            {'workspaceId': workspaceId, 'jobId': jobId, 'taskId': taskId},
        )
        task = result.get('task', {})
        category = task.get('category')
        if category != 'TOOL_APPROVAL':
            return error_result(
                'WRONG_TASK_TYPE',
                f'Task {taskId} is category "{category}", not TOOL_APPROVAL.',
                'Use get_resource(resource="task") for non-TOOL_APPROVAL tasks.',
            )
        return success_result(result)
    except Exception as error:
        return failure_result(error)
