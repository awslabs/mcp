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
"""Extended tests for the metrics provider module."""

import pytest
import time
from awslabs.openapi_mcp_server.utils.metrics_provider import (
    ApiCallMetrics,
    MetricsProvider,
    ToolMetrics,
    api_call_timer,
    tool_usage_timer,
)
from unittest.mock import MagicMock, patch


class TestApiCallMetrics:
    """Tests for the ApiCallMetrics dataclass."""

    def test_api_call_metrics_creation(self):
        """Test creating an ApiCallMetrics instance."""
        now = time.time()
        metrics = ApiCallMetrics(
            path='/pets',
            method='GET',
            status_code=200,
            duration_ms=150.5,
            timestamp=now,
            error=None,
        )

        assert metrics.path == '/pets'
        assert metrics.method == 'GET'
        assert metrics.status_code == 200
        assert metrics.duration_ms == 150.5
        assert metrics.timestamp == now
        assert metrics.error is None

    def test_api_call_metrics_with_error(self):
        """Test creating an ApiCallMetrics instance with an error."""
        now = time.time()
        metrics = ApiCallMetrics(
            path='/pets',
            method='GET',
            status_code=500,
            duration_ms=250.0,
            timestamp=now,
            error='Internal Server Error',
        )

        assert metrics.path == '/pets'
        assert metrics.method == 'GET'
        assert metrics.status_code == 500
        assert metrics.duration_ms == 250.0
        assert metrics.timestamp == now
        assert metrics.error == 'Internal Server Error'


class TestToolMetrics:
    """Tests for the ToolMetrics dataclass."""

    def test_tool_metrics_creation(self):
        """Test creating a ToolMetrics instance."""
        now = time.time()
        metrics = ToolMetrics(
            tool_name='getPet',
            duration_ms=200.0,
            timestamp=now,
            success=True,
            error=None,
        )

        assert metrics.tool_name == 'getPet'
        assert metrics.duration_ms == 200.0
        assert metrics.timestamp == now
        assert metrics.success is True
        assert metrics.error is None

    def test_tool_metrics_with_error(self):
        """Test creating a ToolMetrics instance with an error."""
        now = time.time()
        metrics = ToolMetrics(
            tool_name='getPet',
            duration_ms=300.0,
            timestamp=now,
            success=False,
            error='Not found',
        )

        assert metrics.tool_name == 'getPet'
        assert metrics.duration_ms == 300.0
        assert metrics.timestamp == now
        assert metrics.success is False
        assert metrics.error == 'Not found'


class TestMetricsProvider:
    """Tests for the MetricsProvider abstract class."""

    def test_metrics_provider_is_abstract(self):
        """Test that MetricsProvider is an abstract class."""
        with pytest.raises(TypeError):
            MetricsProvider()


class TestApiCallTimer:
    """Tests for the api_call_timer decorator."""

    @pytest.mark.asyncio
    async def test_api_call_timer_success(self):
        """Test api_call_timer with a successful API call."""
        # Create a mock function that returns a successful response
        mock_response = MagicMock()
        mock_response.status_code = 200

        async def mock_func(path='/test', method='GET'):
            return mock_response

        # Apply the decorator
        decorated_func = api_call_timer(mock_func)

        # Mock the metrics.record_api_call method
        with patch(
            'awslabs.openapi_mcp_server.utils.metrics_provider.metrics.record_api_call'
        ) as mock_record:
            # Call the decorated function
            result = await decorated_func(path='/test', method='GET')

            # Verify the result
            assert result == mock_response

            # Verify that record_api_call was called with the correct arguments
            mock_record.assert_called_once()
            call_args = mock_record.call_args[1]
            assert call_args['path'] == '/test'
            assert call_args['method'] == 'GET'
            assert call_args['status_code'] == 200
            assert isinstance(call_args['duration_ms'], float)
            assert 'error' not in call_args

    @pytest.mark.asyncio
    async def test_api_call_timer_error(self):
        """Test api_call_timer with an API call that raises an exception."""

        # Create a mock function that raises an exception
        async def mock_func(path='/test', method='GET'):
            raise ValueError('Test error')

        # Apply the decorator
        decorated_func = api_call_timer(mock_func)

        # Mock the metrics.record_api_call method
        with patch(
            'awslabs.openapi_mcp_server.utils.metrics_provider.metrics.record_api_call'
        ) as mock_record:
            # Call the decorated function and expect an exception
            with pytest.raises(ValueError, match='Test error'):
                await decorated_func(path='/test', method='GET')

            # Verify that record_api_call was called with the correct arguments
            mock_record.assert_called_once()
            call_args = mock_record.call_args[1]
            assert call_args['path'] == '/test'
            assert call_args['method'] == 'GET'
            assert call_args['status_code'] == 500
            assert isinstance(call_args['duration_ms'], float)
            assert call_args['error'] == 'Test error'


class TestToolUsageTimer:
    """Tests for the tool_usage_timer decorator."""

    @pytest.mark.asyncio
    async def test_tool_usage_timer_success(self):
        """Test tool_usage_timer with a successful tool call."""

        # Create a mock function that returns successfully
        async def mock_tool():
            return 'success'

        # Set the function name
        mock_tool.__name__ = 'test_tool'

        # Apply the decorator
        decorated_func = tool_usage_timer(mock_tool)

        # Mock the metrics.record_tool_usage method
        with patch(
            'awslabs.openapi_mcp_server.utils.metrics_provider.metrics.record_tool_usage'
        ) as mock_record:
            # Call the decorated function
            result = await decorated_func()

            # Verify the result
            assert result == 'success'

            # Verify that record_tool_usage was called with the correct arguments
            mock_record.assert_called_once()
            call_args = mock_record.call_args[1]
            assert call_args['tool_name'] == 'test_tool'
            assert isinstance(call_args['duration_ms'], float)
            assert call_args['success'] is True
            assert 'error' not in call_args

    @pytest.mark.asyncio
    async def test_tool_usage_timer_error(self):
        """Test tool_usage_timer with a tool call that raises an exception."""

        # Create a mock function that raises an exception
        async def mock_tool():
            raise ValueError('Tool error')

        # Set the function name
        mock_tool.__name__ = 'test_tool'

        # Apply the decorator
        decorated_func = tool_usage_timer(mock_tool)

        # Mock the metrics.record_tool_usage method
        with patch(
            'awslabs.openapi_mcp_server.utils.metrics_provider.metrics.record_tool_usage'
        ) as mock_record:
            # Call the decorated function and expect an exception
            with pytest.raises(ValueError, match='Tool error'):
                await decorated_func()

            # Verify that record_tool_usage was called with the correct arguments
            mock_record.assert_called_once()
            call_args = mock_record.call_args[1]
            assert call_args['tool_name'] == 'test_tool'
            assert isinstance(call_args['duration_ms'], float)
            assert call_args['success'] is False
            assert call_args['error'] == 'Tool error'
