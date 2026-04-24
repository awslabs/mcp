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

"""Tests for the get_session helper (VerifySession)."""
# ruff: noqa: D101, D102, D103

import pytest
from awslabs.aws_transform_mcp_server.tools.get_resource import get_session
from unittest.mock import AsyncMock, patch


class TestGetSession:
    """Tests for the inlined get_session helper."""

    @pytest.mark.asyncio
    @patch('awslabs.aws_transform_mcp_server.tools.get_resource.call_fes', new_callable=AsyncMock)
    async def test_success(self, mock_fes):
        mock_fes.return_value = {'userId': 'user-1', 'tenantId': 'tenant-1'}
        result = await get_session()
        assert result['success'] is True
        assert result['data']['session']['userId'] == 'user-1'
        assert result['data']['session']['tenantId'] == 'tenant-1'
        mock_fes.assert_called_once_with('VerifySession', {})

    @pytest.mark.asyncio
    @patch('awslabs.aws_transform_mcp_server.tools.get_resource.call_fes', new_callable=AsyncMock)
    async def test_failure(self, mock_fes):
        mock_fes.side_effect = RuntimeError('session expired')
        result = await get_session()
        assert result['success'] is False
        assert result['error']['code'] == 'REQUEST_FAILED'
        assert 'session expired' in result['error']['message']

    @pytest.mark.asyncio
    @patch('awslabs.aws_transform_mcp_server.tools.get_resource.call_fes', new_callable=AsyncMock)
    async def test_returns_full_session_data(self, mock_fes):
        mock_fes.return_value = {
            'userId': 'u1',
            'tenantId': 't1',
            'email': 'test@example.com',
            'roles': ['admin'],
        }
        result = await get_session()
        assert result['success'] is True
        session = result['data']['session']
        assert session['email'] == 'test@example.com'
        assert session['roles'] == ['admin']

    @pytest.mark.asyncio
    @patch('awslabs.aws_transform_mcp_server.tools.get_resource.call_fes', new_callable=AsyncMock)
    async def test_generic_exception(self, mock_fes):
        mock_fes.side_effect = ValueError('bad value')
        result = await get_session()
        assert result['success'] is False
        assert 'bad value' in result['error']['message']
