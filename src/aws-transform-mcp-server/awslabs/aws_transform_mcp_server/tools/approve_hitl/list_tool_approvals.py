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

"""List pending TOOL_APPROVAL tasks."""

from awslabs.aws_transform_mcp_server.config_store import is_configured
from awslabs.aws_transform_mcp_server.fes_client import call_fes
from awslabs.aws_transform_mcp_server.tool_utils import failure_result, success_result
from awslabs.aws_transform_mcp_server.tools.approve_hitl._common import not_configured_error
from mcp.server.fastmcp import Context
from pydantic import Field
from typing import Any, Dict


async def list_tool_approvals(
    ctx: Context,
    workspaceId: str = Field(..., description='The workspace identifier'),
    jobId: str = Field(..., description='The job identifier'),
) -> Dict[str, Any]:
    """List TOOL_APPROVAL tasks that are waiting for human approval.

    TOOL_APPROVAL tasks are created when an agent requests permission to execute a
    tool during a job. They are always severity=CRITICAL and taskType=NORMAL.
    They remain in AWAITING_APPROVAL status until a human approves or denies them.
    These tasks are time-sensitive — the agent is blocked waiting for a decision.

    This is the first step in the approval workflow:
    1. Call list_tool_approvals to see pending approvals
    2. Present each task to the user for review (show title and agentArtifact)
    3. Call approve_tool_approval or deny_tool_approval per task
    4. Optionally call get_approval_status to confirm

    [CRITICAL] Do NOT use complete_task for TOOL_APPROVAL tasks — the backend
    throws a ValidationException if humanArtifact is present. Use
    approve_tool_approval or deny_tool_approval instead.

    [CRITICAL] Do NOT auto-approve tasks. Always present task details to the
    user and wait for their explicit decision before calling approve or deny.

    Returns: { pendingCount: int, tasks: [{ taskId, title, status, category,
    severity, uxComponentId, agentArtifact, ... }] }. Tasks are server-side
    filtered to category=TOOL_APPROVAL and status=AWAITING_APPROVAL only.

    Requires browser/SSO auth — call configure first.
    """
    if not is_configured():
        return not_configured_error()

    try:
        # Paginate internally rather than exposing nextToken to the MCP caller.
        # MCP pagination (cursor/nextCursor) is for protocol-level list operations
        # (tools/list, resources/list), not tool call results. For tool output,
        # the caller would need multiple round-trips to collect all tasks before
        # presenting them to the user — adding latency to a time-sensitive flow
        # where the agent is blocked. TOOL_APPROVAL tasks are scoped to a single
        # job so the total count is bounded; collecting all pages here keeps the
        # caller's workflow simple: one call, full picture.
        all_tasks: list = []
        next_token: str | None = None

        while True:
            body: Dict[str, Any] = {
                'workspaceId': workspaceId,
                'jobId': jobId,
                'taskType': 'NORMAL',
                'taskFilter': {
                    'categories': ['TOOL_APPROVAL'],
                    'taskStatuses': ['AWAITING_APPROVAL'],
                },
            }
            if next_token:
                body['nextToken'] = next_token

            result = await call_fes('ListHitlTasks', body)
            all_tasks.extend(result.get('hitlTasks', []))

            next_token = result.get('nextToken')
            if not next_token:
                break

        return success_result({'pendingCount': len(all_tasks), 'tasks': all_tasks})
    except Exception as error:
        return failure_result(error)
