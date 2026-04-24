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

"""Tests for ApproveHitlHandler: list, approve, deny, get_approval_status tools."""
# ruff: noqa: D101, D102, D103

import json
import pytest
from awslabs.aws_transform_mcp_server.tools.approve_hitl import ApproveHitlHandler
from awslabs.aws_transform_mcp_server.tools.approve_hitl.approve_tool_approval import (
    approve_tool_approval,
)
from awslabs.aws_transform_mcp_server.tools.approve_hitl.deny_tool_approval import (
    deny_tool_approval,
)
from awslabs.aws_transform_mcp_server.tools.approve_hitl.get_approval_status import (
    get_approval_status,
)
from awslabs.aws_transform_mcp_server.tools.approve_hitl.list_tool_approvals import (
    list_tool_approvals,
)
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.fixture
def handler():
    mcp = MagicMock()
    mcp.tool = MagicMock(side_effect=lambda **kwargs: lambda fn: fn)
    return ApproveHitlHandler(mcp)


@pytest.fixture
def ctx():
    return AsyncMock()


def _parse(result: dict) -> dict:
    return json.loads(result['content'][0]['text'])


# ── Handler registration ────────────────────────────────────────────────


class TestHandlerRegistration:
    def test_registers_four_tools(self):
        mcp = MagicMock()
        mcp.tool = MagicMock(side_effect=lambda **kwargs: lambda fn: fn)
        ApproveHitlHandler(mcp)
        assert mcp.tool.call_count == 4

    def test_registered_tool_names(self):
        mcp = MagicMock()
        mcp.tool = MagicMock(side_effect=lambda **kwargs: lambda fn: fn)
        ApproveHitlHandler(mcp)
        names = [call.kwargs['name'] for call in mcp.tool.call_args_list]
        assert set(names) == {
            'list_tool_approvals',
            'approve_tool_approval',
            'deny_tool_approval',
            'get_approval_status',
        }


# ── list_tool_approvals ─────────────────────────────────────────────────


class TestListToolApprovals:
    @patch(
        'awslabs.aws_transform_mcp_server.tools.approve_hitl.list_tool_approvals.call_fes',
        new_callable=AsyncMock,
    )
    @patch(
        'awslabs.aws_transform_mcp_server.tools.approve_hitl.list_tool_approvals.is_configured',
        return_value=True,
    )
    async def test_returns_server_filtered_tasks(self, _mock_cfg, mock_fes, ctx):
        mock_fes.return_value = {
            'hitlTasks': [
                {'taskId': 't-1', 'category': 'TOOL_APPROVAL', 'status': 'AWAITING_APPROVAL'},
                {'taskId': 't-4', 'category': 'TOOL_APPROVAL', 'status': 'AWAITING_APPROVAL'},
            ],
        }

        result = await list_tool_approvals(ctx, workspaceId='ws-1', jobId='job-1')
        parsed = _parse(result)

        assert parsed['success'] is True
        assert parsed['data']['pendingCount'] == 2
        task_ids = [t['taskId'] for t in parsed['data']['tasks']]
        assert task_ids == ['t-1', 't-4']

        mock_fes.assert_called_once_with(
            'ListHitlTasks',
            {
                'workspaceId': 'ws-1',
                'jobId': 'job-1',
                'taskType': 'NORMAL',
                'taskFilter': {
                    'categories': ['TOOL_APPROVAL'],
                    'taskStatuses': ['AWAITING_APPROVAL'],
                },
            },
        )

    @patch(
        'awslabs.aws_transform_mcp_server.tools.approve_hitl.list_tool_approvals.call_fes',
        new_callable=AsyncMock,
    )
    @patch(
        'awslabs.aws_transform_mcp_server.tools.approve_hitl.list_tool_approvals.is_configured',
        return_value=True,
    )
    async def test_empty_tasks(self, _mock_cfg, mock_fes, ctx):
        mock_fes.return_value = {'hitlTasks': []}

        result = await list_tool_approvals(ctx, workspaceId='ws-1', jobId='job-1')
        parsed = _parse(result)

        assert parsed['success'] is True
        assert parsed['data']['pendingCount'] == 0
        assert parsed['data']['tasks'] == []

    @patch(
        'awslabs.aws_transform_mcp_server.tools.approve_hitl.list_tool_approvals.call_fes',
        new_callable=AsyncMock,
    )
    @patch(
        'awslabs.aws_transform_mcp_server.tools.approve_hitl.list_tool_approvals.is_configured',
        return_value=True,
    )
    async def test_paginates_through_all_pages(self, _mock_cfg, mock_fes, ctx):
        mock_fes.side_effect = [
            {
                'hitlTasks': [
                    {'taskId': 't-1', 'category': 'TOOL_APPROVAL', 'status': 'AWAITING_APPROVAL'},
                ],
                'nextToken': 'page2',
            },
            {
                'hitlTasks': [
                    {'taskId': 't-2', 'category': 'TOOL_APPROVAL', 'status': 'AWAITING_APPROVAL'},
                ],
            },
        ]

        result = await list_tool_approvals(ctx, workspaceId='ws-1', jobId='job-1')
        parsed = _parse(result)

        assert parsed['success'] is True
        assert parsed['data']['pendingCount'] == 2
        task_ids = [t['taskId'] for t in parsed['data']['tasks']]
        assert task_ids == ['t-1', 't-2']
        assert mock_fes.call_count == 2

        second_call_body = mock_fes.call_args_list[1][0][1]
        assert second_call_body['nextToken'] == 'page2'

    @patch(
        'awslabs.aws_transform_mcp_server.tools.approve_hitl.list_tool_approvals.is_configured',
        return_value=False,
    )
    async def test_not_configured(self, _mock_cfg, ctx):
        result = await list_tool_approvals(ctx, workspaceId='ws-1', jobId='job-1')
        parsed = _parse(result)

        assert parsed['success'] is False
        assert parsed['error']['code'] == 'NOT_CONFIGURED'

    @patch(
        'awslabs.aws_transform_mcp_server.tools.approve_hitl.list_tool_approvals.call_fes',
        new_callable=AsyncMock,
    )
    @patch(
        'awslabs.aws_transform_mcp_server.tools.approve_hitl.list_tool_approvals.is_configured',
        return_value=True,
    )
    async def test_fes_error(self, _mock_cfg, mock_fes, ctx):
        mock_fes.side_effect = RuntimeError('connection failed')

        result = await list_tool_approvals(ctx, workspaceId='ws-1', jobId='job-1')
        parsed = _parse(result)

        assert parsed['success'] is False
        assert parsed['error']['code'] == 'REQUEST_FAILED'


# ── approve_tool_approval ───────────────────────────────────────────────


class TestApproveToolApproval:
    @patch(
        'awslabs.aws_transform_mcp_server.tools.approve_hitl._common.call_fes',
        new_callable=AsyncMock,
    )
    @patch(
        'awslabs.aws_transform_mcp_server.tools.approve_hitl._common.is_configured',
        return_value=True,
    )
    async def test_approve_success(self, _mock_cfg, mock_fes, ctx):
        mock_fes.side_effect = [
            {
                'task': {
                    'taskId': 't-1',
                    'category': 'TOOL_APPROVAL',
                    'status': 'AWAITING_APPROVAL',
                }
            },
            {'approved': True},
        ]

        result = await approve_tool_approval(ctx, workspaceId='ws-1', jobId='job-1', taskId='t-1')
        parsed = _parse(result)

        assert parsed['success'] is True
        assert parsed['data']['action'] == 'APPROVE'
        assert parsed['data']['taskId'] == 't-1'

        submit_call = mock_fes.call_args_list[1]
        assert submit_call[0][0] == 'SubmitCriticalHitlTask'
        assert submit_call[0][1]['action'] == 'APPROVE'
        assert 'humanArtifact' not in submit_call[0][1]

    @patch(
        'awslabs.aws_transform_mcp_server.tools.approve_hitl._common.call_fes',
        new_callable=AsyncMock,
    )
    @patch(
        'awslabs.aws_transform_mcp_server.tools.approve_hitl._common.is_configured',
        return_value=True,
    )
    async def test_wrong_category(self, _mock_cfg, mock_fes, ctx):
        mock_fes.return_value = {
            'task': {'taskId': 't-1', 'category': 'CONTENT_REVIEW', 'status': 'AWAITING_APPROVAL'}
        }

        result = await approve_tool_approval(ctx, workspaceId='ws-1', jobId='job-1', taskId='t-1')
        parsed = _parse(result)

        assert parsed['success'] is False
        assert parsed['error']['code'] == 'WRONG_TASK_TYPE'

    @patch(
        'awslabs.aws_transform_mcp_server.tools.approve_hitl._common.call_fes',
        new_callable=AsyncMock,
    )
    @patch(
        'awslabs.aws_transform_mcp_server.tools.approve_hitl._common.is_configured',
        return_value=True,
    )
    async def test_wrong_status(self, _mock_cfg, mock_fes, ctx):
        mock_fes.return_value = {
            'task': {'taskId': 't-1', 'category': 'TOOL_APPROVAL', 'status': 'COMPLETED'}
        }

        result = await approve_tool_approval(ctx, workspaceId='ws-1', jobId='job-1', taskId='t-1')
        parsed = _parse(result)

        assert parsed['success'] is False
        assert parsed['error']['code'] == 'WRONG_STATUS'

    @patch(
        'awslabs.aws_transform_mcp_server.tools.approve_hitl._common.is_configured',
        return_value=False,
    )
    async def test_not_configured(self, _mock_cfg, ctx):
        result = await approve_tool_approval(ctx, workspaceId='ws-1', jobId='job-1', taskId='t-1')
        parsed = _parse(result)

        assert parsed['success'] is False
        assert parsed['error']['code'] == 'NOT_CONFIGURED'

    @patch(
        'awslabs.aws_transform_mcp_server.tools.approve_hitl._common.call_fes',
        new_callable=AsyncMock,
    )
    @patch(
        'awslabs.aws_transform_mcp_server.tools.approve_hitl._common.is_configured',
        return_value=True,
    )
    async def test_missing_category_rejected(self, _mock_cfg, mock_fes, ctx):
        mock_fes.return_value = {'task': {'taskId': 't-1', 'status': 'AWAITING_APPROVAL'}}

        result = await approve_tool_approval(ctx, workspaceId='ws-1', jobId='job-1', taskId='t-1')
        parsed = _parse(result)

        assert parsed['success'] is False
        assert parsed['error']['code'] == 'WRONG_TASK_TYPE'

    @patch(
        'awslabs.aws_transform_mcp_server.tools.approve_hitl._common.call_fes',
        new_callable=AsyncMock,
    )
    @patch(
        'awslabs.aws_transform_mcp_server.tools.approve_hitl._common.is_configured',
        return_value=True,
    )
    async def test_missing_status_rejected(self, _mock_cfg, mock_fes, ctx):
        mock_fes.return_value = {'task': {'taskId': 't-1', 'category': 'TOOL_APPROVAL'}}

        result = await approve_tool_approval(ctx, workspaceId='ws-1', jobId='job-1', taskId='t-1')
        parsed = _parse(result)

        assert parsed['success'] is False
        assert parsed['error']['code'] == 'WRONG_STATUS'


# ── deny_tool_approval ──────────────────────────────────────────────────


class TestDenyToolApproval:
    @patch(
        'awslabs.aws_transform_mcp_server.tools.approve_hitl._common.call_fes',
        new_callable=AsyncMock,
    )
    @patch(
        'awslabs.aws_transform_mcp_server.tools.approve_hitl._common.is_configured',
        return_value=True,
    )
    async def test_deny_success(self, _mock_cfg, mock_fes, ctx):
        mock_fes.side_effect = [
            {
                'task': {
                    'taskId': 't-1',
                    'category': 'TOOL_APPROVAL',
                    'status': 'AWAITING_APPROVAL',
                }
            },
            {'rejected': True},
        ]

        result = await deny_tool_approval(ctx, workspaceId='ws-1', jobId='job-1', taskId='t-1')
        parsed = _parse(result)

        assert parsed['success'] is True
        assert parsed['data']['action'] == 'REJECT'
        assert parsed['data']['taskId'] == 't-1'

        submit_call = mock_fes.call_args_list[1]
        assert submit_call[0][0] == 'SubmitCriticalHitlTask'
        assert submit_call[0][1]['action'] == 'REJECT'
        assert 'humanArtifact' not in submit_call[0][1]

    @patch(
        'awslabs.aws_transform_mcp_server.tools.approve_hitl._common.call_fes',
        new_callable=AsyncMock,
    )
    @patch(
        'awslabs.aws_transform_mcp_server.tools.approve_hitl._common.is_configured',
        return_value=True,
    )
    async def test_wrong_category(self, _mock_cfg, mock_fes, ctx):
        mock_fes.return_value = {
            'task': {'taskId': 't-1', 'category': 'CONTENT_REVIEW', 'status': 'AWAITING_APPROVAL'}
        }

        result = await deny_tool_approval(ctx, workspaceId='ws-1', jobId='job-1', taskId='t-1')
        parsed = _parse(result)

        assert parsed['success'] is False
        assert parsed['error']['code'] == 'WRONG_TASK_TYPE'

    @patch(
        'awslabs.aws_transform_mcp_server.tools.approve_hitl._common.is_configured',
        return_value=False,
    )
    async def test_not_configured(self, _mock_cfg, ctx):
        result = await deny_tool_approval(ctx, workspaceId='ws-1', jobId='job-1', taskId='t-1')
        parsed = _parse(result)

        assert parsed['success'] is False
        assert parsed['error']['code'] == 'NOT_CONFIGURED'


# ── get_approval_status ─────────────────────────────────────────────────


class TestGetApprovalStatus:
    @patch(
        'awslabs.aws_transform_mcp_server.tools.approve_hitl.get_approval_status.call_fes',
        new_callable=AsyncMock,
    )
    @patch(
        'awslabs.aws_transform_mcp_server.tools.approve_hitl.get_approval_status.is_configured',
        return_value=True,
    )
    async def test_get_status_success(self, _mock_cfg, mock_fes, ctx):
        mock_fes.return_value = {
            'task': {'taskId': 't-1', 'status': 'APPROVED', 'category': 'TOOL_APPROVAL'}
        }

        result = await get_approval_status(ctx, workspaceId='ws-1', jobId='job-1', taskId='t-1')
        parsed = _parse(result)

        assert parsed['success'] is True
        assert parsed['data']['task']['status'] == 'APPROVED'

    @patch(
        'awslabs.aws_transform_mcp_server.tools.approve_hitl.get_approval_status.call_fes',
        new_callable=AsyncMock,
    )
    @patch(
        'awslabs.aws_transform_mcp_server.tools.approve_hitl.get_approval_status.is_configured',
        return_value=True,
    )
    async def test_wrong_category_rejected(self, _mock_cfg, mock_fes, ctx):
        mock_fes.return_value = {
            'task': {'taskId': 't-1', 'status': 'IN_PROGRESS', 'category': 'REGULAR'}
        }

        result = await get_approval_status(ctx, workspaceId='ws-1', jobId='job-1', taskId='t-1')
        parsed = _parse(result)

        assert parsed['success'] is False
        assert parsed['error']['code'] == 'WRONG_TASK_TYPE'

    @patch(
        'awslabs.aws_transform_mcp_server.tools.approve_hitl.get_approval_status.is_configured',
        return_value=False,
    )
    async def test_not_configured(self, _mock_cfg, ctx):
        result = await get_approval_status(ctx, workspaceId='ws-1', jobId='job-1', taskId='t-1')
        parsed = _parse(result)

        assert parsed['success'] is False
        assert parsed['error']['code'] == 'NOT_CONFIGURED'

    @patch(
        'awslabs.aws_transform_mcp_server.tools.approve_hitl.get_approval_status.call_fes',
        new_callable=AsyncMock,
    )
    @patch(
        'awslabs.aws_transform_mcp_server.tools.approve_hitl.get_approval_status.is_configured',
        return_value=True,
    )
    async def test_fes_error(self, _mock_cfg, mock_fes, ctx):
        mock_fes.side_effect = RuntimeError('connection failed')

        result = await get_approval_status(ctx, workspaceId='ws-1', jobId='job-1', taskId='t-1')
        parsed = _parse(result)

        assert parsed['success'] is False
        assert parsed['error']['code'] == 'REQUEST_FAILED'
