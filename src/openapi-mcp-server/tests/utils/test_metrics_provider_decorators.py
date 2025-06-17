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
"""Tests for the metrics provider decorators."""

import pytest
from awslabs.openapi_mcp_server.utils.metrics_provider import (
    api_call_timer,
    tool_usage_timer,
)
from unittest.mock import MagicMock, patch


@pytest.mark.asyncio
async def test_api_call_timer_success():
    """Test the api_call_timer decorator with a successful API call."""
    # Mock the metrics provider
    mock_metrics = MagicMock()

    # Create a mock async function that returns a response
    mock_response = MagicMock()
    mock_response.status_code = 200

    async def mock_func(path, method):
        return mock_response

    # Apply the decorator with our mock metrics
    with patch('awslabs.openapi_mcp_server.utils.metrics_provider.metrics', mock_metrics):
        decorated_func = api_call_timer(mock_func)
        result = await decorated_func(path='/test', method='GET')

    # Check that the function was called and returned the expected result
    assert result == mock_response

    # Check that metrics were recorded
    mock_metrics.record_api_call.assert_called_once()
    call_args = mock_metrics.record_api_call.call_args[1]
    assert call_args['path'] == '/test'
    assert call_args['method'] == 'GET'
    assert call_args['status_code'] == 200
    assert isinstance(call_args['duration_ms'], float)
    assert 'error' not in call_args


@pytest.mark.asyncio
async def test_api_call_timer_error():
    """Test the api_call_timer decorator with an API call that raises an exception."""
    # Mock the metrics provider
    mock_metrics = MagicMock()

    # Create a mock async function that raises an exception
    async def mock_func(path, method):
        raise ValueError('Test error')

    # Apply the decorator with our mock metrics
    with patch('awslabs.openapi_mcp_server.utils.metrics_provider.metrics', mock_metrics):
        decorated_func = api_call_timer(mock_func)

        # Call the function and expect an exception
        with pytest.raises(ValueError, match='Test error'):
            await decorated_func(path='/test', method='POST')

    # Check that metrics were recorded with error
    mock_metrics.record_api_call.assert_called_once()
    call_args = mock_metrics.record_api_call.call_args[1]
    assert call_args['path'] == '/test'
    assert call_args['method'] == 'POST'
    assert call_args['status_code'] == 500
    assert isinstance(call_args['duration_ms'], float)
    assert call_args['error'] == 'Test error'


@pytest.mark.asyncio
async def test_tool_usage_timer_success():
    """Test the tool_usage_timer decorator with successful tool execution."""
    # Mock the metrics provider
    mock_metrics = MagicMock()

    # Create a mock async function
    async def test_tool():
        return 'success'

    # Apply the decorator with our mock metrics
    with patch('awslabs.openapi_mcp_server.utils.metrics_provider.metrics', mock_metrics):
        decorated_func = tool_usage_timer(test_tool)
        result = await decorated_func()

    # Check that the function was called and returned the expected result
    assert result == 'success'

    # Check that metrics were recorded
    mock_metrics.record_tool_usage.assert_called_once()
    call_args = mock_metrics.record_tool_usage.call_args[1]
    assert call_args['tool_name'] == 'test_tool'
    assert isinstance(call_args['duration_ms'], float)
    assert call_args['success'] is True
    assert 'error' not in call_args


@pytest.mark.asyncio
async def test_tool_usage_timer_error():
    """Test the tool_usage_timer decorator with tool execution that raises an exception."""
    # Mock the metrics provider
    mock_metrics = MagicMock()

    # Create a mock async function that raises an exception
    async def test_tool():
        raise ValueError('Tool error')

    # Apply the decorator with our mock metrics
    with patch('awslabs.openapi_mcp_server.utils.metrics_provider.metrics', mock_metrics):
        decorated_func = tool_usage_timer(test_tool)

        # Call the function and expect an exception
        with pytest.raises(ValueError, match='Tool error'):
            await decorated_func()

    # Check that metrics were recorded with error
    mock_metrics.record_tool_usage.assert_called_once()
    call_args = mock_metrics.record_tool_usage.call_args[1]
    assert call_args['tool_name'] == 'test_tool'
    assert isinstance(call_args['duration_ms'], float)
    assert call_args['success'] is False
    assert call_args['error'] == 'Tool error'
