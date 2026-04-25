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
    @patch(f'{_MOD}.call_fes', new_callable=AsyncMock)
    @patch(f'{_MOD}.is_configured', return_value=True)
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
        assert call_args[0][1]['name'] == 'My Workspace'
        assert call_args[0][1]['description'] == 'A test'
        assert 'idempotencyToken' in call_args[0][1]

    @patch(f'{_MOD}.is_configured', return_value=False)
    async def test_not_configured(self, _mock_configured, handler, ctx):
        result = await handler.create_workspace(ctx, name='Test')
        parsed = _parse(result)

        assert parsed['success'] is False
        assert parsed['error']['code'] == 'NOT_CONFIGURED'
        assert result['isError'] is True


class TestDeleteWorkspace:
    @patch(f'{_MOD}.call_fes', new_callable=AsyncMock)
    @patch(f'{_MOD}.is_configured', return_value=True)
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
        assert call_args[0][1] == {'id': 'ws-123'}

    @patch(f'{_MOD}.is_configured', return_value=True)
    async def test_requires_confirm(self, _mock_configured, handler, ctx):
        result = await handler.delete_workspace(ctx, workspaceId='ws-123', confirm=False)
        parsed = _parse(result)

        assert parsed['success'] is False
        assert parsed['error']['code'] == 'VALIDATION_ERROR'
        assert result['isError'] is True

    @patch(f'{_MOD}.is_configured', return_value=False)
    async def test_not_configured(self, _mock_configured, handler, ctx):
        result = await handler.delete_workspace(ctx, workspaceId='ws-123', confirm=True)
        parsed = _parse(result)

        assert parsed['success'] is False
        assert parsed['error']['code'] == 'NOT_CONFIGURED'
