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
"""Tests for the metrics provider module."""

import time
from awslabs.openapi_mcp_server.utils.metrics_provider import (
    ApiCallMetrics,
    InMemoryMetricsProvider,
    ToolMetrics,
)


def test_api_call_metrics_dataclass():
    """Test the ApiCallMetrics dataclass."""
    timestamp = time.time()
    metrics = ApiCallMetrics(
        path='/test',
        method='GET',
        status_code=200,
        duration_ms=10.5,
        timestamp=timestamp,
        error=None,
    )

    assert metrics.path == '/test'
    assert metrics.method == 'GET'
    assert metrics.status_code == 200
    assert metrics.duration_ms == 10.5
    assert metrics.timestamp == timestamp
    assert metrics.error is None


def test_tool_metrics_dataclass():
    """Test the ToolMetrics dataclass."""
    timestamp = time.time()
    metrics = ToolMetrics(
        tool_name='test_tool',
        duration_ms=15.2,
        timestamp=timestamp,
        success=True,
        error=None,
    )

    assert metrics.tool_name == 'test_tool'
    assert metrics.duration_ms == 15.2
    assert metrics.timestamp == timestamp
    assert metrics.success is True
    assert metrics.error is None


class TestInMemoryMetricsProvider:
    """Tests for the InMemoryMetricsProvider class."""

    def test_init(self):
        """Test initialization with default and custom max_history."""
        # Default max_history
        provider = InMemoryMetricsProvider()
        assert provider._max_history == 100  # Default from config

        # Custom max_history
        provider = InMemoryMetricsProvider(max_history=500)
        assert provider._max_history == 500

    def test_record_api_call_success(self):
        """Test recording a successful API call."""
        provider = InMemoryMetricsProvider()
        provider.record_api_call(
            path='/test',
            method='GET',
            status_code=200,
            duration_ms=10.5,
        )

        # Check that the call was recorded
        assert len(provider._api_calls) == 1
        assert provider._api_calls[0].path == '/test'
        assert provider._api_calls[0].method == 'GET'
        assert provider._api_calls[0].status_code == 200
        assert provider._api_calls[0].duration_ms == 10.5
        assert provider._api_calls[0].error is None

        # Check path stats
        path_key = 'GET /test'
        assert provider._path_stats[path_key]['count'] == 1
        assert provider._path_stats[path_key]['errors'] == 0
        assert provider._path_stats[path_key]['total_duration_ms'] == 10.5

    def test_record_api_call_error(self):
        """Test recording an API call with an error."""
        provider = InMemoryMetricsProvider()
        provider.record_api_call(
            path='/test',
            method='POST',
            status_code=500,
            duration_ms=20.3,
            error='Internal Server Error',
        )

        # Check that the call was recorded
        assert len(provider._api_calls) == 1
        assert provider._api_calls[0].path == '/test'
        assert provider._api_calls[0].method == 'POST'
        assert provider._api_calls[0].status_code == 500
        assert provider._api_calls[0].duration_ms == 20.3
        assert provider._api_calls[0].error == 'Internal Server Error'

        # Check path stats
        path_key = 'POST /test'
        assert provider._path_stats[path_key]['count'] == 1
        assert provider._path_stats[path_key]['errors'] == 1
        assert provider._path_stats[path_key]['total_duration_ms'] == 20.3

    def test_record_api_call_max_history(self):
        """Test that max_history is respected for API calls."""
        provider = InMemoryMetricsProvider(max_history=2)

        # Record 3 calls
        provider.record_api_call(path='/test1', method='GET', status_code=200, duration_ms=10)
        provider.record_api_call(path='/test2', method='GET', status_code=200, duration_ms=20)
        provider.record_api_call(path='/test3', method='GET', status_code=200, duration_ms=30)

        # Check that only the last 2 calls are kept
        assert len(provider._api_calls) == 2
        assert provider._api_calls[0].path == '/test2'
        assert provider._api_calls[1].path == '/test3'

    def test_record_tool_usage_success(self):
        """Test recording successful tool usage."""
        provider = InMemoryMetricsProvider()
        provider.record_tool_usage(
            tool_name='test_tool',
            duration_ms=15.2,
            success=True,
        )

        # Check that the usage was recorded
        assert len(provider._tool_usage) == 1
        assert provider._tool_usage[0].tool_name == 'test_tool'
        assert provider._tool_usage[0].duration_ms == 15.2
        assert provider._tool_usage[0].success is True
        assert provider._tool_usage[0].error is None

        # Check tool stats
        assert provider._tool_stats['test_tool']['count'] == 1
        assert provider._tool_stats['test_tool']['errors'] == 0
        assert provider._tool_stats['test_tool']['total_duration_ms'] == 15.2

    def test_record_tool_usage_error(self):
        """Test recording tool usage with an error."""
        provider = InMemoryMetricsProvider()
        provider.record_tool_usage(
            tool_name='test_tool',
            duration_ms=25.7,
            success=False,
            error='Tool execution failed',
        )

        # Check that the usage was recorded
        assert len(provider._tool_usage) == 1
        assert provider._tool_usage[0].tool_name == 'test_tool'
        assert provider._tool_usage[0].duration_ms == 25.7
        assert provider._tool_usage[0].success is False
        assert provider._tool_usage[0].error == 'Tool execution failed'

        # Check tool stats
        assert provider._tool_stats['test_tool']['count'] == 1
        assert provider._tool_stats['test_tool']['errors'] == 1
        assert provider._tool_stats['test_tool']['total_duration_ms'] == 25.7

    def test_record_tool_usage_max_history(self):
        """Test that max_history is respected for tool usage."""
        provider = InMemoryMetricsProvider(max_history=2)

        # Record 3 tool usages
        provider.record_tool_usage(tool_name='tool1', duration_ms=10, success=True)
        provider.record_tool_usage(tool_name='tool2', duration_ms=20, success=True)
        provider.record_tool_usage(tool_name='tool3', duration_ms=30, success=True)

        # Check that only the last 2 usages are kept
        assert len(provider._tool_usage) == 2
        assert provider._tool_usage[0].tool_name == 'tool2'
        assert provider._tool_usage[1].tool_name == 'tool3'

    def test_get_api_stats(self):
        """Test getting API stats."""
        provider = InMemoryMetricsProvider()

        # Record some API calls
        provider.record_api_call(path='/test1', method='GET', status_code=200, duration_ms=10)
        provider.record_api_call(path='/test1', method='GET', status_code=200, duration_ms=20)
        provider.record_api_call(
            path='/test1', method='GET', status_code=500, duration_ms=30, error='Error'
        )
        provider.record_api_call(path='/test2', method='POST', status_code=201, duration_ms=15)

        # Get stats
        stats = provider.get_api_stats()

        # Check stats for first path
        assert stats['GET /test1']['count'] == 3
        assert stats['GET /test1']['errors'] == 1
        assert stats['GET /test1']['error_rate'] == 1 / 3
        assert stats['GET /test1']['avg_duration_ms'] == 20  # (10 + 20 + 30) / 3

        # Check stats for second path
        assert stats['POST /test2']['count'] == 1
        assert stats['POST /test2']['errors'] == 0
        assert stats['POST /test2']['error_rate'] == 0
        assert stats['POST /test2']['avg_duration_ms'] == 15

    def test_get_tool_stats(self):
        """Test getting tool stats."""
        provider = InMemoryMetricsProvider()

        # Record some tool usages
        provider.record_tool_usage(tool_name='tool1', duration_ms=10, success=True)
        provider.record_tool_usage(tool_name='tool1', duration_ms=20, success=True)
        provider.record_tool_usage(tool_name='tool1', duration_ms=30, success=False, error='Error')
        provider.record_tool_usage(tool_name='tool2', duration_ms=15, success=True)

        # Get stats
        stats = provider.get_tool_stats()

        # Check stats for first tool
        assert stats['tool1']['count'] == 3
        assert stats['tool1']['errors'] == 1
        assert stats['tool1']['error_rate'] == 1 / 3
        assert stats['tool1']['avg_duration_ms'] == 20  # (10 + 20 + 30) / 3

        # Check stats for second tool
        assert stats['tool2']['count'] == 1
        assert stats['tool2']['errors'] == 0
        assert stats['tool2']['error_rate'] == 0
        assert stats['tool2']['avg_duration_ms'] == 15

    def test_get_recent_errors(self):
        """Test getting recent errors."""
        provider = InMemoryMetricsProvider()

        # Record some API calls with and without errors
        provider.record_api_call(path='/test1', method='GET', status_code=200, duration_ms=10)
        provider.record_api_call(
            path='/test2', method='GET', status_code=500, duration_ms=20, error='Error 1'
        )
        provider.record_api_call(
            path='/test3', method='POST', status_code=400, duration_ms=30, error='Error 2'
        )
        provider.record_api_call(path='/test4', method='PUT', status_code=200, duration_ms=40)

        # Get recent errors with default limit
        errors = provider.get_recent_errors()

        # Check that only errors are returned
        assert len(errors) == 2
        assert errors[0]['path'] == '/test3'
        assert errors[0]['method'] == 'POST'
        assert errors[0]['status_code'] == 400
        assert errors[0]['error'] == 'Error 2'

        assert errors[1]['path'] == '/test2'
        assert errors[1]['method'] == 'GET'
        assert errors[1]['status_code'] == 500
        assert errors[1]['error'] == 'Error 1'

        # Test with a limit
        errors = provider.get_recent_errors(limit=1)
        assert len(errors) == 1
        assert errors[0]['path'] == '/test3'

    def test_get_summary(self):
        """Test getting a metrics summary."""
        provider = InMemoryMetricsProvider()

        # Record some API calls and tool usages
        provider.record_api_call(path='/test1', method='GET', status_code=200, duration_ms=10)
        provider.record_api_call(
            path='/test2', method='POST', status_code=500, duration_ms=20, error='Error'
        )
        provider.record_tool_usage(tool_name='tool1', duration_ms=15, success=True)
        provider.record_tool_usage(
            tool_name='tool2', duration_ms=25, success=False, error='Tool Error'
        )

        # Get summary
        summary = provider.get_summary()

        # Check API call summary
        assert summary['api_calls']['total'] == 2
        assert summary['api_calls']['errors'] == 1
        assert summary['api_calls']['error_rate'] == 0.5
        assert summary['api_calls']['paths'] == 2

        # Check tool usage summary
        assert summary['tool_usage']['total'] == 2
        assert summary['tool_usage']['errors'] == 1
        assert summary['tool_usage']['error_rate'] == 0.5
        assert summary['tool_usage']['tools'] == 2
