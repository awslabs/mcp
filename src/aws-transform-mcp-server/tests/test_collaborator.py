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

"""Tests for CollaboratorHandler tools."""
# ruff: noqa: D101, D102, D103

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


_MOD = 'awslabs.aws_transform_mcp_server.tools.collaborator'


@pytest.fixture
def handler():
    from awslabs.aws_transform_mcp_server.tools.collaborator import CollaboratorHandler

    mcp = MagicMock()
    mcp.tool = MagicMock(side_effect=lambda **kwargs: lambda fn: fn)
    return CollaboratorHandler(mcp)


@pytest.fixture
def ctx():
    return AsyncMock()


def _parse(result: dict) -> dict:
    return json.loads(result['content'][0]['text'])


class TestNotConfigured:
    @patch(f'{_MOD}.is_fes_available', return_value=False)
    async def test_returns_not_configured(self, _mock, handler, ctx):
        result = await handler.manage_collaborator(
            ctx, workspaceId='ws-1', action='put', userId='u-1', role='ADMIN'
        )
        parsed = _parse(result)
        assert parsed['success'] is False
        assert parsed['error']['code'] == 'NOT_CONFIGURED'
        assert result['isError'] is True


class TestPutAction:
    @patch(f'{_MOD}.call_transform_api', new_callable=AsyncMock)
    @patch(f'{_MOD}.is_fes_available', return_value=True)
    async def test_success(self, _mock_cfg, mock_fes, handler, ctx):
        mock_fes.return_value = {'updated': True}
        result = await handler.manage_collaborator(
            ctx, workspaceId='ws-1', action='put', userId='u-1', role='CONTRIBUTOR'
        )
        parsed = _parse(result)
        assert parsed['success'] is True
        assert result['isError'] is False
        call_args = mock_fes.call_args[0]
        assert call_args[0] == 'PutUserRoleMappings'
        assert call_args[1].workspaceId == 'ws-1'
        assert call_args[1].userId == 'u-1'
        assert call_args[1].roles == ['CONTRIBUTOR']

    @patch(f'{_MOD}.is_fes_available', return_value=True)
    async def test_missing_user_id(self, _mock_cfg, handler, ctx):
        result = await handler.manage_collaborator(
            ctx, workspaceId='ws-1', action='put', userId=None, role='ADMIN'
        )
        parsed = _parse(result)
        assert parsed['success'] is False
        assert parsed['error']['code'] == 'VALIDATION_ERROR'

    @patch(f'{_MOD}.is_fes_available', return_value=True)
    async def test_missing_role(self, _mock_cfg, handler, ctx):
        result = await handler.manage_collaborator(
            ctx, workspaceId='ws-1', action='put', userId='u-1', role=None
        )
        parsed = _parse(result)
        assert parsed['success'] is False
        assert parsed['error']['code'] == 'VALIDATION_ERROR'


class TestRemoveAction:
    @patch(f'{_MOD}.call_transform_api', new_callable=AsyncMock)
    @patch(f'{_MOD}.is_fes_available', return_value=True)
    async def test_success(self, _mock_cfg, mock_fes, handler, ctx):
        mock_fes.return_value = {'detail': 'ok'}
        result = await handler.manage_collaborator(
            ctx, workspaceId='ws-1', action='remove', userId='u-1', confirm=True
        )
        parsed = _parse(result)
        assert parsed['success'] is True
        assert parsed['data']['removed'] is True
        assert parsed['data']['userId'] == 'u-1'
        mock_fes.assert_called_once()
        assert mock_fes.call_args[0][0] == 'DeleteUserRoleMappings'

    @patch(f'{_MOD}.is_fes_available', return_value=True)
    async def test_missing_user_id(self, _mock_cfg, handler, ctx):
        result = await handler.manage_collaborator(
            ctx, workspaceId='ws-1', action='remove', userId=None, confirm=True
        )
        parsed = _parse(result)
        assert parsed['success'] is False
        assert parsed['error']['code'] == 'VALIDATION_ERROR'

    @patch(f'{_MOD}.is_fes_available', return_value=True)
    async def test_missing_confirm(self, _mock_cfg, handler, ctx):
        result = await handler.manage_collaborator(
            ctx, workspaceId='ws-1', action='remove', userId='u-1', confirm=None
        )
        parsed = _parse(result)
        assert parsed['success'] is False
        assert parsed['error']['code'] == 'VALIDATION_ERROR'


class TestLeaveAction:
    @patch(f'{_MOD}.call_transform_api', new_callable=AsyncMock)
    @patch(f'{_MOD}.is_fes_available', return_value=True)
    async def test_success(self, _mock_cfg, mock_fes, handler, ctx):
        mock_fes.return_value = {'detail': 'left'}
        result = await handler.manage_collaborator(
            ctx, workspaceId='ws-1', action='leave', userId=None, confirm=True
        )
        parsed = _parse(result)
        assert parsed['success'] is True
        assert parsed['data']['left'] is True
        assert parsed['data']['workspaceId'] == 'ws-1'
        mock_fes.assert_called_once()
        assert mock_fes.call_args[0][0] == 'DeleteSelfRoleMappings'

    @patch(f'{_MOD}.is_fes_available', return_value=True)
    async def test_user_id_not_allowed(self, _mock_cfg, handler, ctx):
        result = await handler.manage_collaborator(
            ctx, workspaceId='ws-1', action='leave', userId='u-1', confirm=True
        )
        parsed = _parse(result)
        assert parsed['success'] is False
        assert parsed['error']['code'] == 'VALIDATION_ERROR'

    @patch(f'{_MOD}.is_fes_available', return_value=True)
    async def test_missing_confirm(self, _mock_cfg, handler, ctx):
        result = await handler.manage_collaborator(
            ctx, workspaceId='ws-1', action='leave', confirm=None
        )
        parsed = _parse(result)
        assert parsed['success'] is False
        assert parsed['error']['code'] == 'VALIDATION_ERROR'


class TestExceptionHandling:
    @patch(f'{_MOD}.call_transform_api', new_callable=AsyncMock, side_effect=RuntimeError('boom'))
    @patch(f'{_MOD}.is_fes_available', return_value=True)
    async def test_returns_failure(self, _mock_cfg, _mock_fes, handler, ctx):
        result = await handler.manage_collaborator(
            ctx, workspaceId='ws-1', action='put', userId='u-1', role='ADMIN'
        )
        parsed = _parse(result)
        assert parsed['success'] is False
        assert result['isError'] is True
