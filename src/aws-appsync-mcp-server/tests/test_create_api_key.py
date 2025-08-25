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

"""Tests for the create_api_key operation."""

import pytest
from awslabs.aws_appsync_mcp_server.operations.create_api_key import create_api_key_operation
from awslabs.aws_appsync_mcp_server.tools.create_api_key import register_create_api_key_tool
from unittest.mock import MagicMock, patch


@pytest.mark.asyncio
async def test_create_api_key_minimal():
    """Test create_api_key tool with minimal parameters."""
    mock_client = MagicMock()
    mock_response = {
        'apiKey': {
            'id': 'da2-abcdefghijklmnopqrstuvwxyz',  # pragma: allowlist secret
            'description': None,
            'expires': None,
            'deletes': None,
        }
    }
    mock_client.create_api_key.return_value = mock_response

    with patch(
        'awslabs.aws_appsync_mcp_server.operations.create_api_key.get_appsync_client',
        return_value=mock_client,
    ):
        result = await create_api_key_operation(api_id='test-api-id')

        mock_client.create_api_key.assert_called_once_with(apiId='test-api-id')
        assert result == mock_response


@pytest.mark.asyncio
async def test_create_api_key_with_description():
    """Test create_api_key tool with description."""
    mock_client = MagicMock()
    mock_response = {
        'apiKey': {
            'id': 'da2-abcdefghijklmnopqrstuvwxyz',  # pragma: allowlist secret
            'description': 'Test API Key',
            'expires': None,
            'deletes': None,
        }
    }
    mock_client.create_api_key.return_value = mock_response

    with patch(
        'awslabs.aws_appsync_mcp_server.operations.create_api_key.get_appsync_client',
        return_value=mock_client,
    ):
        result = await create_api_key_operation(api_id='test-api-id', description='Test API Key')

        mock_client.create_api_key.assert_called_once_with(
            apiId='test-api-id', description='Test API Key'
        )
        assert result == mock_response


@pytest.mark.asyncio
async def test_create_api_key_with_expiration():
    """Test create_api_key tool with expiration time."""
    mock_client = MagicMock()
    expires_timestamp = 1640995200  # 2022-01-01 00:00:00 UTC
    mock_response = {
        'apiKey': {
            'id': 'da2-abcdefghijklmnopqrstuvwxyz',  # pragma: allowlist secret
            'description': None,
            'expires': expires_timestamp,
            'deletes': expires_timestamp + 86400,  # 24 hours later
        }
    }
    mock_client.create_api_key.return_value = mock_response

    with patch(
        'awslabs.aws_appsync_mcp_server.operations.create_api_key.get_appsync_client',
        return_value=mock_client,
    ):
        result = await create_api_key_operation(api_id='test-api-id', expires=expires_timestamp)

        mock_client.create_api_key.assert_called_once_with(
            apiId='test-api-id', expires=expires_timestamp
        )
        assert result == mock_response


@pytest.mark.asyncio
async def test_create_api_key_full():
    """Test create_api_key tool with all parameters."""
    mock_client = MagicMock()
    expires_timestamp = 1640995200  # 2022-01-01 00:00:00 UTC
    mock_response = {
        'apiKey': {
            'id': 'da2-abcdefghijklmnopqrstuvwxyz',  # pragma: allowlist secret
            'description': 'Production API Key',
            'expires': expires_timestamp,
            'deletes': expires_timestamp + 86400,  # 24 hours later
        }
    }
    mock_client.create_api_key.return_value = mock_response

    with patch(
        'awslabs.aws_appsync_mcp_server.operations.create_api_key.get_appsync_client',
        return_value=mock_client,
    ):
        result = await create_api_key_operation(
            api_id='test-api-id', description='Production API Key', expires=expires_timestamp
        )

        mock_client.create_api_key.assert_called_once_with(
            apiId='test-api-id', description='Production API Key', expires=expires_timestamp
        )
        assert result == mock_response


@pytest.mark.asyncio
async def test_create_api_key_empty_response():
    """Test create_api_key tool with empty response from AWS."""
    mock_client = MagicMock()
    mock_response = {}
    mock_client.create_api_key.return_value = mock_response

    with patch(
        'awslabs.aws_appsync_mcp_server.operations.create_api_key.get_appsync_client',
        return_value=mock_client,
    ):
        result = await create_api_key_operation(api_id='test-api-id')

        mock_client.create_api_key.assert_called_once_with(apiId='test-api-id')
        assert result == {'apiKey': {}}


def test_register_create_api_key_tool():
    """Test that create_api_key tool is registered correctly."""
    mock_mcp = MagicMock()
    register_create_api_key_tool(mock_mcp)
    mock_mcp.tool.assert_called_once()


@pytest.mark.asyncio
async def test_create_api_key_tool_execution():
    """Test create_api_key tool execution through MCP."""
    from awslabs.aws_appsync_mcp_server.decorators import set_write_allowed
    from typing import Any, Callable

    mock_mcp = MagicMock()
    captured_func: Callable[..., Any] | None = None

    def capture_tool(**kwargs):
        def decorator(func):
            nonlocal captured_func
            captured_func = func
            return func

        return decorator

    mock_mcp.tool = capture_tool
    set_write_allowed(True)

    register_create_api_key_tool(mock_mcp)

    with patch(
        'awslabs.aws_appsync_mcp_server.tools.create_api_key.create_api_key_operation'
    ) as mock_op:
        mock_op.return_value = {'apiKey': {'id': 'test-key'}}
        if captured_func is not None:
            result = await captured_func('test-api')
            mock_op.assert_called_once_with('test-api', None, None)
            assert result == {'apiKey': {'id': 'test-key'}}
