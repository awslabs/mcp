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

"""Approve/deny HITL tools for TOOL_APPROVAL category tasks."""

from awslabs.aws_transform_mcp_server.audit import audited_tool
from awslabs.aws_transform_mcp_server.tool_utils import READ_ONLY, SUBMIT_IDEMPOTENT
from awslabs.aws_transform_mcp_server.tools.approve_hitl.approve_tool_approval import (
    approve_tool_approval as _approve_tool_approval_fn,
)
from awslabs.aws_transform_mcp_server.tools.approve_hitl.deny_tool_approval import (
    deny_tool_approval as _deny_tool_approval_fn,
)
from awslabs.aws_transform_mcp_server.tools.approve_hitl.get_approval_status import (
    get_approval_status as _get_approval_status_fn,
)
from awslabs.aws_transform_mcp_server.tools.approve_hitl.list_tool_approvals import (
    list_tool_approvals as _list_tool_approvals_fn,
)
from typing import Any


class ApproveHitlHandler:
    """Registers TOOL_APPROVAL-specific MCP tools.

    This handler uses the package pattern: each tool function lives in its
    own module and is imported here for registration. Shared validation
    logic lives in _common.py.
    """

    def __init__(self, mcp: Any) -> None:
        """Register approve-hitl tools on the MCP server."""
        audited_tool(
            mcp,
            'list_tool_approvals',
            title='List Pending Tool Approvals',
            annotations=READ_ONLY,
        )(_list_tool_approvals_fn)
        audited_tool(
            mcp,
            'approve_tool_approval',
            title='Approve Tool Approval',
            annotations=SUBMIT_IDEMPOTENT,
        )(_approve_tool_approval_fn)
        audited_tool(
            mcp,
            'deny_tool_approval',
            title='Deny Tool Approval',
            annotations=SUBMIT_IDEMPOTENT,
        )(_deny_tool_approval_fn)
        audited_tool(
            mcp,
            'get_approval_status',
            title='Get Tool Approval Status',
            annotations=READ_ONLY,
        )(_get_approval_status_fn)
