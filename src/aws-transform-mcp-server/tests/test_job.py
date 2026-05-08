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

"""Tests for JobHandler tools."""
# ruff: noqa: D101, D102, D103

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


_MOD = 'awslabs.aws_transform_mcp_server.tools.job'


@pytest.fixture
def handler():
    """Create a JobHandler with a mock MCP server."""
    from awslabs.aws_transform_mcp_server.tools.job import JobHandler

    mcp = MagicMock()
    mcp.tool = MagicMock(side_effect=lambda **kwargs: lambda fn: fn)
    return JobHandler(mcp)


@pytest.fixture
def ctx():
    """Return a mock MCP context."""
    return AsyncMock()


def _parse(result: dict) -> dict:
    """Extract the parsed JSON payload from an MCP result envelope."""
    return json.loads(result['content'][0]['text'])


class TestCreateJob:
    @patch(f'{_MOD}.call_transform_api', new_callable=AsyncMock)
    @patch(f'{_MOD}.is_fes_available', return_value=True)
    async def test_create_start_get(self, _mock_configured, mock_fes, handler, ctx):
        """CreateJob -> StartJob -> poll GetJob -> ListMessages chain."""
        mock_fes.side_effect = [
            {'jobId': 'job-001'},  # CreateJob
            {},  # StartJob
            {
                'job': {
                    'jobId': 'job-001',
                    'jobName': 'Migration',
                    'status': 'EXECUTING',
                    'statusDetails': {'status': 'RUNNING'},
                    'workspaceId': 'ws-1',
                }
            },  # GetJob (poll)
            {'messageIds': []},  # ListMessages
        ]

        result = await handler.create_job(
            ctx,
            workspaceId='ws-1',
            jobName='Migration',
            objective='Migrate code',
            intent='modernize',
        )
        parsed = _parse(result)

        assert parsed['success'] is True
        assert parsed['data']['job']['statusDetails']['status'] == 'RUNNING'
        assert parsed['data']['job']['jobId'] == 'job-001'
        assert mock_fes.call_count == 4

        calls = mock_fes.call_args_list
        assert calls[0][0][0] == 'CreateJob'
        assert calls[0][0][1].workspaceId == 'ws-1'
        assert calls[0][0][1].jobName == 'Migration'
        assert calls[0][0][1].idempotencyToken is not None
        assert calls[1][0][0] == 'StartJob'
        assert calls[1][0][1].model_dump(by_alias=True, exclude_none=True) == {
            'workspaceId': 'ws-1',
            'jobId': 'job-001',
        }
        assert calls[2][0][0] == 'GetJob'
        assert calls[2][0][1].model_dump(by_alias=True, exclude_none=True) == {
            'workspaceId': 'ws-1',
            'jobId': 'job-001',
        }
        assert calls[3][0][0] == 'ListMessages'

    @patch(f'{_MOD}.is_fes_available', return_value=False)
    async def test_not_configured(self, _mock_configured, handler, ctx):
        result = await handler.create_job(
            ctx,
            workspaceId='ws-1',
            jobName='Test',
            objective='test',
            intent='test',
        )
        parsed = _parse(result)
        assert parsed['success'] is False
        assert parsed['error']['code'] == 'NOT_CONFIGURED'


class TestControlJob:
    @patch(f'{_MOD}.call_transform_api', new_callable=AsyncMock)
    @patch(f'{_MOD}.is_fes_available', return_value=True)
    async def test_start(self, _mock_configured, mock_fes, handler, ctx):
        mock_fes.side_effect = [
            {},  # StartJob
            {'job': {'jobId': 'job-1', 'statusDetails': {'status': 'RUNNING'}}},  # GetJob
        ]

        result = await handler.control_job(ctx, workspaceId='ws-1', jobId='job-1', action='start')
        parsed = _parse(result)

        assert parsed['success'] is True
        assert parsed['data']['statusDetails']['status'] == 'RUNNING'
        calls = mock_fes.call_args_list
        assert calls[0][0][0] == 'StartJob'

    @patch(f'{_MOD}.call_transform_api', new_callable=AsyncMock)
    @patch(f'{_MOD}.is_fes_available', return_value=True)
    async def test_stop(self, _mock_configured, mock_fes, handler, ctx):
        mock_fes.side_effect = [
            {},  # StopJob
            {'job': {'jobId': 'job-1', 'statusDetails': {'status': 'STOPPED'}}},  # GetJob
        ]

        result = await handler.control_job(ctx, workspaceId='ws-1', jobId='job-1', action='stop')
        parsed = _parse(result)

        assert parsed['success'] is True
        assert parsed['data']['statusDetails']['status'] == 'STOPPED'
        calls = mock_fes.call_args_list
        assert calls[0][0][0] == 'StopJob'

    @patch(f'{_MOD}.is_fes_available', return_value=False)
    async def test_not_configured(self, _mock_configured, handler, ctx):
        result = await handler.control_job(ctx, workspaceId='ws-1', jobId='job-1', action='start')
        parsed = _parse(result)
        assert parsed['error']['code'] == 'NOT_CONFIGURED'


class TestDeleteJob:
    @patch(f'{_MOD}.call_transform_api', new_callable=AsyncMock)
    @patch(f'{_MOD}.is_fes_available', return_value=True)
    async def test_success(self, _mock_configured, mock_fes, handler, ctx):
        mock_fes.return_value = {'deleted': True}

        result = await handler.delete_job(ctx, workspaceId='ws-1', jobId='job-1', confirm=True)
        parsed = _parse(result)

        assert parsed['success'] is True
        mock_fes.assert_called_once()
        assert mock_fes.call_args[0][0] == 'DeleteJob'

    @patch(f'{_MOD}.is_fes_available', return_value=True)
    async def test_requires_confirm(self, _mock_configured, handler, ctx):
        result = await handler.delete_job(ctx, workspaceId='ws-1', jobId='job-1', confirm=False)
        parsed = _parse(result)

        assert parsed['success'] is False
        assert parsed['error']['code'] == 'VALIDATION_ERROR'

    @patch(f'{_MOD}.is_fes_available', return_value=False)
    async def test_not_configured(self, _mock_configured, handler, ctx):
        result = await handler.delete_job(ctx, workspaceId='ws-1', jobId='job-1', confirm=True)
        parsed = _parse(result)
        assert parsed['error']['code'] == 'NOT_CONFIGURED'


class TestCreateJobWithOrchestrator:
    @pytest.fixture
    def handler(self, mock_mcp):
        from awslabs.aws_transform_mcp_server.tools.job import JobHandler

        return JobHandler(mock_mcp)

    @pytest.fixture
    def mock_mcp(self):
        mcp = MagicMock()
        mcp.tool = MagicMock(side_effect=lambda **kwargs: lambda fn: fn)
        return mcp

    @pytest.fixture
    def ctx(self):
        return AsyncMock()

    @pytest.mark.asyncio
    @patch(f'{_MOD}.call_transform_api', new_callable=AsyncMock)
    @patch(f'{_MOD}.is_fes_available', return_value=True)
    async def test_create_job_with_orchestrator(self, _, mock_fes, handler, ctx):
        mock_fes.side_effect = [
            {'jobId': 'j-1'},
            None,
            {'job': {'jobId': 'j-1', 'status': 'EXECUTING', 'workspaceId': 'ws-1'}},
            {'messageIds': []},
        ]
        result = await handler.create_job(
            ctx,
            workspaceId='ws-1',
            jobName='test',
            objective='test obj',
            intent='test',
            orchestratorAgent='agent-1',
        )
        parsed = _parse(result)
        assert parsed['success'] is True
        create_body = mock_fes.call_args_list[0][0][1]
        assert create_body.orchestratorAgent == 'agent-1'

    @pytest.mark.asyncio
    @patch(f'{_MOD}.call_transform_api', new_callable=AsyncMock, side_effect=Exception('fail'))
    @patch(f'{_MOD}.is_fes_available', return_value=True)
    async def test_create_job_fes_error(self, _, mock_fes, handler, ctx):
        result = await handler.create_job(
            ctx, workspaceId='ws-1', jobName='test', objective='obj', intent='test'
        )
        parsed = _parse(result)
        assert parsed['success'] is False


class TestControlJobError:
    @pytest.fixture
    def handler(self, mock_mcp):
        from awslabs.aws_transform_mcp_server.tools.job import JobHandler

        return JobHandler(mock_mcp)

    @pytest.fixture
    def mock_mcp(self):
        mcp = MagicMock()
        mcp.tool = MagicMock(side_effect=lambda **kwargs: lambda fn: fn)
        return mcp

    @pytest.fixture
    def ctx(self):
        return AsyncMock()

    @pytest.mark.asyncio
    @patch(f'{_MOD}.call_transform_api', new_callable=AsyncMock, side_effect=Exception('fail'))
    @patch(f'{_MOD}.is_fes_available', return_value=True)
    async def test_control_job_error(self, _, mock_fes, handler, ctx):
        result = await handler.control_job(ctx, workspaceId='ws-1', jobId='j-1', action='stop')
        parsed = _parse(result)
        assert parsed['success'] is False

    @pytest.mark.asyncio
    @patch(f'{_MOD}.call_transform_api', new_callable=AsyncMock, side_effect=Exception('fail'))
    @patch(f'{_MOD}.is_fes_available', return_value=True)
    async def test_delete_job_fes_error(self, _, mock_fes, handler, ctx):
        result = await handler.delete_job(ctx, workspaceId='ws-1', jobId='j-1', confirm=True)
        parsed = _parse(result)
        assert parsed['success'] is False
