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

"""Approve a TOOL_APPROVAL HITL task."""

from awslabs.aws_transform_mcp_server.tools.approve_hitl._common import validate_and_submit
from mcp.server.fastmcp import Context
from pydantic import Field
from typing import Any, Dict


async def approve_tool_approval(
    ctx: Context,
    workspaceId: str = Field(..., description='The workspace identifier'),
    jobId: str = Field(..., description='The job identifier'),
    taskId: str = Field(..., description='The TOOL_APPROVAL task identifier to approve'),
) -> Dict[str, Any]:
    """Approve a TOOL_APPROVAL task, allowing the agent to execute the requested tool.

    Use when the user has reviewed a pending TOOL_APPROVAL task and explicitly
    confirmed they want to approve it. The task must be in AWAITING_APPROVAL status.
    After approval, the task transitions to SUBMITTED status and the agent
    reads the APPROVE action to proceed with tool execution.

    [CRITICAL] Do NOT call this without user confirmation. Always present the
    task details (from list_tool_approvals or get_approval_status) first.

    [CRITICAL] Do NOT use complete_task for TOOL_APPROVAL tasks — the backend
    throws a ValidationException if humanArtifact is present.

    Validates the task is category=TOOL_APPROVAL and status=AWAITING_APPROVAL
    before submitting. Returns WRONG_TASK_TYPE or WRONG_STATUS errors if not.

    Returns on success: { action: "APPROVE", taskId: str, result: { status: "SUBMITTED" } }
    Returns on error: { code: "WRONG_TASK_TYPE" | "WRONG_STATUS" | "NOT_CONFIGURED",
    message: str, suggestedAction: str }

    Requires browser/SSO auth — call configure first.
    """
    return await validate_and_submit(workspaceId, jobId, taskId, 'APPROVE')
