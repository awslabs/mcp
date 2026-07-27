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

"""Tests for WorkspaceHandler tools."""
# ruff: noqa: D101, D102, D103

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


_MOD = 'awslabs.aws_transform_mcp_server.tools.workspace'


@pytest.fixture
def handler():
    """Create a WorkspaceHandler with a mock MCP server."""
    from awslabs.aws_transform_mcp_server.tools.workspace import WorkspaceHandler

    mcp = MagicMock()
    mcp.tool = MagicMock(side_effect=lambda **kwargs: lambda fn: fn)
    return WorkspaceHandler(mcp)


@pytest.fixture
def ctx():
    """Return a mock MCP context."""
    return AsyncMock()


def _parse(result: dict) -> dict:
    """Extract the parsed JSON payload from an MCP result envelope."""
    return json.loads(result['content'][0]['text'])


class TestCreateWorkspace:
    @patch(f'{_MOD}.call_transform_api', new_callable=AsyncMock)
    @patch(f'{_MOD}.is_fes_available', return_value=True)
    async def test_success(self, _mock_configured, mock_fes, handler, ctx):
        mock_fes.return_value = {
            'workspace': {'id': 'ws-123', 'status': 'ACTIVE', 'name': 'My Workspace'}
        }

        result = await handler.create_workspace(ctx, name='My Workspace', description='A test')
        parsed = _parse(result)

        assert parsed['success'] is True
        assert parsed['data']['id'] == 'ws-123'
        assert result['isError'] is False

        call_args = mock_fes.call_args
        assert call_args[0][0] == 'CreateWorkspace'
        body = call_args[0][1].model_dump(by_alias=True, exclude_none=True)
        assert body['name'] == 'My Workspace'
        assert body['description'] == 'A test'
        assert 'idempotencyToken' in body

    @patch(f'{_MOD}.is_fes_available', return_value=False)
    async def test_not_configured(self, _mock_configured, handler, ctx):
        result = await handler.create_workspace(ctx, name='Test')
        parsed = _parse(result)

        assert parsed['success'] is False
        assert parsed['error']['code'] == 'NOT_CONFIGURED'
        assert result['isError'] is True


class TestDeleteWorkspace:
    @patch(f'{_MOD}.call_transform_api', new_callable=AsyncMock)
    @patch(f'{_MOD}.is_fes_available', return_value=True)
    async def test_success(self, _mock_configured, mock_fes, handler, ctx):
        mock_fes.return_value = {'status': 'DELETED'}

        result = await handler.delete_workspace(ctx, workspaceId='ws-123', confirm=True)
        parsed = _parse(result)

        assert parsed['success'] is True
        assert parsed['data']['deleted'] is True
        assert parsed['data']['workspaceId'] == 'ws-123'
        assert result['isError'] is False

        mock_fes.assert_called_once()
        call_args = mock_fes.call_args
        assert call_args[0][0] == 'DeleteWorkspace'
        assert call_args[0][1].model_dump(by_alias=True, exclude_none=True) == {'id': 'ws-123'}

    @patch(f'{_MOD}.is_fes_available', return_value=True)
    async def test_requires_confirm(self, _mock_configured, handler, ctx):
        result = await handler.delete_workspace(ctx, workspaceId='ws-123', confirm=False)
        parsed = _parse(result)

        assert parsed['success'] is False
        assert parsed['error']['code'] == 'VALIDATION_ERROR'
        assert result['isError'] is True

    @patch(f'{_MOD}.is_fes_available', return_value=False)
    async def test_not_configured(self, _mock_configured, handler, ctx):
        result = await handler.delete_workspace(ctx, workspaceId='ws-123', confirm=True)
        parsed = _parse(result)

        assert parsed['success'] is False
        assert parsed['error']['code'] == 'NOT_CONFIGURED'


class TestWorkspaceErrors:
    @pytest.fixture
    def handler(self, mock_mcp):
        from awslabs.aws_transform_mcp_server.tools.workspace import WorkspaceHandler

        return WorkspaceHandler(mock_mcp)

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
    async def test_create_workspace_fes_error(self, _, mock_fes, handler, ctx):
        result = await handler.create_workspace(ctx, name='test')
        parsed = _parse(result)
        assert parsed['success'] is False

    @pytest.mark.asyncio
    @patch(f'{_MOD}.call_transform_api', new_callable=AsyncMock, side_effect=Exception('fail'))
    @patch(f'{_MOD}.is_fes_available', return_value=True)
    async def test_delete_workspace_fes_error(self, _, mock_fes, handler, ctx):
        result = await handler.delete_workspace(ctx, workspaceId='ws-1', confirm=True)
        parsed = _parse(result)
        assert parsed['success'] is False
