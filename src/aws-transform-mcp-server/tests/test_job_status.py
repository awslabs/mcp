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

"""Tests for JobStatusHandler (get_job_status tool)."""
# ruff: noqa: D101, D102, D103

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


_MOD = 'awslabs.aws_transform_mcp_server.tools.job_status'


@pytest.fixture
def handler():
    """Create a JobStatusHandler with a mock MCP server."""
    from awslabs.aws_transform_mcp_server.tools.job_status import JobStatusHandler

    mcp = MagicMock()
    mcp.tool = MagicMock(side_effect=lambda **kwargs: lambda fn: fn)
    return JobStatusHandler(mcp)


@pytest.fixture
def ctx():
    """Return a mock MCP context."""
    return AsyncMock()


def _parse(result: dict) -> dict:
    """Extract the parsed JSON payload from an MCP result envelope."""
    return json.loads(result['content'][0]['text'])


# call_fes order in asyncio.gather:
#   1. GetJob
#   2. ListWorklogs
#   3. _fetch_recent_messages → ListMessages, (BatchGetMessage if IDs found)
#   4. _fetch_plan → ListJobPlanSteps
#
# paginate_all order:
#   1. ListHitlTasks


class TestNotConfigured:
    @patch(f'{_MOD}.is_configured', return_value=False)
    async def test_returns_not_configured(self, _mock_configured, handler, ctx):
        result = await handler.get_job_status(ctx, workspaceId='ws-1', jobId='job-1')
        parsed = _parse(result)
        assert parsed['success'] is False
        assert parsed['error']['code'] == 'NOT_CONFIGURED'


class TestInstructionsRequired:
    @patch(f'{_MOD}.job_needs_check', return_value='STOP: call load_instructions first')
    @patch(f'{_MOD}.is_configured', return_value=True)
    async def test_returns_instructions_required(self, _mock_cfg, _mock_nudge, handler, ctx):
        result = await handler.get_job_status(ctx, workspaceId='ws-1', jobId='job-1')
        parsed = _parse(result)
        assert parsed['success'] is False
        assert parsed['error']['code'] == 'INSTRUCTIONS_REQUIRED'


class TestInProgressJob:
    @patch(f'{_MOD}.paginate_all', new_callable=AsyncMock)
    @patch(f'{_MOD}.call_fes', new_callable=AsyncMock)
    @patch(f'{_MOD}.job_needs_check', return_value=None)
    @patch(f'{_MOD}.is_configured', return_value=True)
    async def test_returns_snapshot_with_polling_guidance(
        self, _mock_cfg, _mock_nudge, mock_fes, mock_paginate, handler, ctx
    ):
        mock_fes.side_effect = [
            # GetJob
            {'jobId': 'job-1', 'status': 'IN_PROGRESS'},
            # ListWorklogs
            {'worklogs': [{'description': 'Started step 2'}]},
            # _fetch_recent_messages: ListMessages
            {'messageIds': ['msg-1']},
            # _fetch_recent_messages: BatchGetMessage
            {'messages': [{'messageId': 'msg-1', 'text': 'Working on step 2'}]},
            # _fetch_plan: ListJobPlanSteps
            {'steps': [{'stepId': 's1', 'status': 'SUCCEEDED'}]},
        ]
        mock_paginate.side_effect = [
            # ListHitlTasks
            {'hitlTasks': []},
        ]

        result = await handler.get_job_status(ctx, workspaceId='ws-1', jobId='job-1')
        parsed = _parse(result)

        assert parsed['success'] is True
        data = parsed['data']

        assert data['job']['status'] == 'IN_PROGRESS'
        assert data['worklogs'] == {'worklogs': [{'description': 'Started step 2'}]}
        assert data['tasks'] == {'hitlTasks': []}
        assert len(data['messages']['messages']) == 1
        assert data['plan']['steps'] == [{'stepId': 's1', 'status': 'SUCCEEDED'}]

        guidance = data['_pollingGuidance']
        assert guidance['isTerminal'] is False
        assert guidance['jobStatus'] == 'IN_PROGRESS'
        assert guidance['hasPendingTasks'] is False
        assert guidance['pendingTaskCount'] == 0
        assert '[CRITICAL] Call get_job_status again in 1 minute' in guidance['suggestedAction']


class TestCompletedJob:
    @patch(f'{_MOD}.paginate_all', new_callable=AsyncMock)
    @patch(f'{_MOD}.call_fes', new_callable=AsyncMock)
    @patch(f'{_MOD}.job_needs_check', return_value=None)
    @patch(f'{_MOD}.is_configured', return_value=True)
    async def test_terminal_state_stops_polling(
        self, _mock_cfg, _mock_nudge, mock_fes, mock_paginate, handler, ctx
    ):
        mock_fes.side_effect = [
            {'jobId': 'job-1', 'status': 'COMPLETED'},
            # ListWorklogs
            {'worklogs': []},
            # ListMessages
            {'messageIds': []},
            # ListJobPlanSteps
            {'steps': []},
        ]
        mock_paginate.side_effect = [
            {'hitlTasks': []},
        ]

        result = await handler.get_job_status(ctx, workspaceId='ws-1', jobId='job-1')
        parsed = _parse(result)

        assert parsed['success'] is True
        guidance = parsed['data']['_pollingGuidance']
        assert guidance['isTerminal'] is True
        assert guidance['jobStatus'] == 'COMPLETED'
        assert 'No further polling needed' in guidance['suggestedAction']


class TestFailedJob:
    @patch(f'{_MOD}.paginate_all', new_callable=AsyncMock)
    @patch(f'{_MOD}.call_fes', new_callable=AsyncMock)
    @patch(f'{_MOD}.job_needs_check', return_value=None)
    @patch(f'{_MOD}.is_configured', return_value=True)
    async def test_failed_is_terminal(
        self, _mock_cfg, _mock_nudge, mock_fes, mock_paginate, handler, ctx
    ):
        mock_fes.side_effect = [
            {'jobId': 'job-1', 'status': 'FAILED'},
            {'worklogs': []},
            {'messageIds': []},
            {'steps': []},
        ]
        mock_paginate.side_effect = [
            {'hitlTasks': []},
        ]

        result = await handler.get_job_status(ctx, workspaceId='ws-1', jobId='job-1')
        parsed = _parse(result)

        guidance = parsed['data']['_pollingGuidance']
        assert guidance['isTerminal'] is True
        assert guidance['jobStatus'] == 'FAILED'


class TestPendingHitlTasks:
    @patch(f'{_MOD}.paginate_all', new_callable=AsyncMock)
    @patch(f'{_MOD}.call_fes', new_callable=AsyncMock)
    @patch(f'{_MOD}.job_needs_check', return_value=None)
    @patch(f'{_MOD}.is_configured', return_value=True)
    async def test_pending_tasks_flagged(
        self, _mock_cfg, _mock_nudge, mock_fes, mock_paginate, handler, ctx
    ):
        mock_fes.side_effect = [
            {'jobId': 'job-1', 'status': 'IN_PROGRESS'},
            {'worklogs': []},
            {'messageIds': []},
            {'steps': []},
        ]
        mock_paginate.side_effect = [
            {
                'hitlTasks': [
                    {'taskId': 'task-1', 'status': 'AWAITING_HUMAN_INPUT'},
                    {'taskId': 'task-2', 'status': 'IN_PROGRESS'},
                    {'taskId': 'task-3', 'status': 'CLOSED'},
                ]
            },
        ]

        result = await handler.get_job_status(ctx, workspaceId='ws-1', jobId='job-1')
        parsed = _parse(result)

        guidance = parsed['data']['_pollingGuidance']
        assert guidance['isTerminal'] is False
        assert guidance['hasPendingTasks'] is True
        assert guidance['pendingTaskCount'] == 2
        assert 'task-1' in guidance['suggestedAction']
        assert 'task-2' in guidance['suggestedAction']
        assert 'get_resource(resource="task")' in guidance['suggestedAction']
        assert '[CRITICAL] Call get_job_status again in 1 minute' in guidance['suggestedAction']


class TestGetJobFails:
    @patch(f'{_MOD}.paginate_all', new_callable=AsyncMock)
    @patch(f'{_MOD}.call_fes', new_callable=AsyncMock)
    @patch(f'{_MOD}.job_needs_check', return_value=None)
    @patch(f'{_MOD}.is_configured', return_value=True)
    async def test_returns_error_when_getjob_fails(
        self, _mock_cfg, _mock_nudge, mock_fes, mock_paginate, handler, ctx
    ):
        mock_fes.side_effect = [
            RuntimeError('connection refused'),
            {'worklogs': []},
            {'messageIds': []},
            {'steps': []},
        ]
        mock_paginate.side_effect = [
            {'hitlTasks': []},
        ]

        result = await handler.get_job_status(ctx, workspaceId='ws-1', jobId='job-1')
        parsed = _parse(result)

        assert parsed['success'] is False
        assert parsed['error']['code'] == 'REQUEST_FAILED'


class TestPartialFailures:
    @patch(f'{_MOD}.paginate_all', new_callable=AsyncMock)
    @patch(f'{_MOD}.call_fes', new_callable=AsyncMock)
    @patch(f'{_MOD}.job_needs_check', return_value=None)
    @patch(f'{_MOD}.is_configured', return_value=True)
    async def test_returns_none_for_failed_sections(
        self, _mock_cfg, _mock_nudge, mock_fes, mock_paginate, handler, ctx
    ):
        mock_fes.side_effect = [
            {'jobId': 'job-1', 'status': 'IN_PROGRESS'},
            # ListWorklogs fails
            RuntimeError('worklogs unavailable'),
            # ListMessages fails
            RuntimeError('messages unavailable'),
            # ListJobPlanSteps fails
            RuntimeError('plan unavailable'),
        ]
        mock_paginate.side_effect = [
            {'hitlTasks': []},
        ]

        result = await handler.get_job_status(ctx, workspaceId='ws-1', jobId='job-1')
        parsed = _parse(result)

        assert parsed['success'] is True
        data = parsed['data']
        assert data['job']['status'] == 'IN_PROGRESS'
        assert data['worklogs'] is None
        assert data['messages'] is None
        assert data['plan'] is None
        assert data['_pollingGuidance']['isTerminal'] is False


class TestCancellationInProgress:
    @patch(f'{_MOD}.paginate_all', new_callable=AsyncMock)
    @patch(f'{_MOD}.call_fes', new_callable=AsyncMock)
    @patch(f'{_MOD}.job_needs_check', return_value=None)
    @patch(f'{_MOD}.is_configured', return_value=True)
    async def test_cancellation_in_progress_is_not_terminal(
        self, _mock_cfg, _mock_nudge, mock_fes, mock_paginate, handler, ctx
    ):
        mock_fes.side_effect = [
            {'jobId': 'job-1', 'status': 'CANCELLATION_IN_PROGRESS'},
            {'worklogs': []},
            {'messageIds': []},
            {'steps': []},
        ]
        mock_paginate.side_effect = [
            {'hitlTasks': []},
        ]

        result = await handler.get_job_status(ctx, workspaceId='ws-1', jobId='job-1')
        parsed = _parse(result)

        guidance = parsed['data']['_pollingGuidance']
        assert guidance['isTerminal'] is False
        assert guidance['jobStatus'] == 'CANCELLATION_IN_PROGRESS'
        assert '[CRITICAL] Call get_job_status again in 1 minute' in guidance['suggestedAction']
