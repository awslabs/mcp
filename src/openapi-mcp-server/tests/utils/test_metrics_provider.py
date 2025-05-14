"""Tests for the metrics provider module."""

from awslabs.openapi_mcp_server.utils.metrics_provider import (
    ApiCallMetrics,
    InMemoryMetricsProvider,
    ToolMetrics,
    create_metrics_provider,
)
from unittest.mock import patch


def test_api_call_metrics_dataclass():
    """Test the ApiCallMetrics dataclass."""
    metrics = ApiCallMetrics(
        path='/test',
        method='GET',
        status_code=200,
        duration_ms=100.0,
        timestamp=1234567890.0,
        error=None,
    )

    assert metrics.path == '/test'
    assert metrics.method == 'GET'
    assert metrics.status_code == 200
    assert metrics.duration_ms == 100.0
    assert metrics.timestamp == 1234567890.0
    assert metrics.error is None


def test_tool_metrics_dataclass():
    """Test the ToolMetrics dataclass."""
    metrics = ToolMetrics(
        tool_name='test_tool',
        duration_ms=50.0,
        timestamp=1234567890.0,
        success=True,
        error=None,
    )

    assert metrics.tool_name == 'test_tool'
    assert metrics.duration_ms == 50.0
    assert metrics.timestamp == 1234567890.0
    assert metrics.success is True
    assert metrics.error is None


def test_in_memory_metrics_provider_init():
    """Test initializing the InMemoryMetricsProvider."""
    provider = InMemoryMetricsProvider(max_history=100)
    assert provider._max_history == 100

    # Test with default max_history
    with patch('awslabs.openapi_mcp_server.utils.metrics_provider.METRICS_MAX_HISTORY', 500):
        provider = InMemoryMetricsProvider()
        assert provider._max_history == 500


def test_in_memory_metrics_provider_record_api_call():
    """Test recording API calls in the InMemoryMetricsProvider."""
    provider = InMemoryMetricsProvider(max_history=5)

    # Record a successful API call
    provider.record_api_call(
        path='/test',
        method='GET',
        status_code=200,
        duration_ms=100.0,
    )

    assert len(provider._api_calls) == 1
    assert provider._api_calls[0].path == '/test'
    assert provider._api_calls[0].method == 'GET'
    assert provider._api_calls[0].status_code == 200
    assert provider._api_calls[0].duration_ms == 100.0
    assert provider._api_calls[0].error is None

    # Check path stats - note the key format is "METHOD path"
    path_key = 'GET /test'
    assert provider._path_stats[path_key]['count'] == 1
    assert provider._path_stats[path_key]['errors'] == 0
    assert provider._path_stats[path_key]['total_duration_ms'] == 100.0

    # Record an error API call
    provider.record_api_call(
        path='/test',
        method='GET',
        status_code=500,
        duration_ms=150.0,
        error='Internal Server Error',
    )

    assert len(provider._api_calls) == 2
    assert provider._api_calls[1].error == 'Internal Server Error'

    # Check updated path stats
    assert provider._path_stats[path_key]['count'] == 2
    assert provider._path_stats[path_key]['errors'] == 1
    assert provider._path_stats[path_key]['total_duration_ms'] == 250.0

    # Test max history limit
    for i in range(5):
        provider.record_api_call(
            path=f'/test{i}',
            method='GET',
            status_code=200,
            duration_ms=100.0,
        )

    # Should only keep the 5 most recent calls
    assert len(provider._api_calls) == 5
    # The first two calls should have been removed
    assert '/test' not in [call.path for call in provider._api_calls]


def test_in_memory_metrics_provider_record_tool_usage():
    """Test recording tool usage in the InMemoryMetricsProvider."""
    provider = InMemoryMetricsProvider(max_history=5)

    # Record successful tool usage
    provider.record_tool_usage(
        tool_name='test_tool',
        duration_ms=50.0,
        success=True,
    )

    assert len(provider._tool_usage) == 1
    assert provider._tool_usage[0].tool_name == 'test_tool'
    assert provider._tool_usage[0].duration_ms == 50.0
    assert provider._tool_usage[0].success is True
    assert provider._tool_usage[0].error is None

    # Check tool stats
    assert provider._tool_stats['test_tool']['count'] == 1
    assert provider._tool_stats['test_tool']['errors'] == 0
    assert provider._tool_stats['test_tool']['total_duration_ms'] == 50.0

    # Record failed tool usage
    provider.record_tool_usage(
        tool_name='test_tool',
        duration_ms=75.0,
        success=False,
        error='Tool execution failed',
    )

    assert len(provider._tool_usage) == 2
    assert provider._tool_usage[1].success is False
    assert provider._tool_usage[1].error == 'Tool execution failed'

    # Check updated tool stats
    assert provider._tool_stats['test_tool']['count'] == 2
    assert provider._tool_stats['test_tool']['errors'] == 1
    assert provider._tool_stats['test_tool']['total_duration_ms'] == 125.0

    # Test max history limit
    for i in range(5):
        provider.record_tool_usage(
            tool_name=f'test_tool{i}',
            duration_ms=100.0,
            success=True,
        )

    # Should only keep the 5 most recent tool usages
    assert len(provider._tool_usage) == 5
    # The first two tool usages should have been removed
    assert provider._tool_usage[0].tool_name == 'test_tool0'


def test_in_memory_metrics_provider_get_api_stats():
    """Test getting API stats from the InMemoryMetricsProvider."""
    provider = InMemoryMetricsProvider()

    # Record some API calls
    provider.record_api_call(path='/test1', method='GET', status_code=200, duration_ms=100.0)
    provider.record_api_call(
        path='/test1', method='GET', status_code=500, duration_ms=150.0, error='Error'
    )
    provider.record_api_call(path='/test2', method='POST', status_code=201, duration_ms=75.0)

    # Get API stats
    stats = provider.get_api_stats()

    # Check stats for /test1 - note the key format is "METHOD path"
    assert stats['GET /test1']['count'] == 2
    assert stats['GET /test1']['errors'] == 1
    assert stats['GET /test1']['error_rate'] == 0.5
    assert stats['GET /test1']['avg_duration_ms'] == 125.0

    # Check stats for /test2
    assert stats['POST /test2']['count'] == 1
    assert stats['POST /test2']['errors'] == 0
    assert stats['POST /test2']['error_rate'] == 0.0
    assert stats['POST /test2']['avg_duration_ms'] == 75.0


def test_in_memory_metrics_provider_get_tool_stats():
    """Test getting tool stats from the InMemoryMetricsProvider."""
    provider = InMemoryMetricsProvider()

    # Record some tool usage
    provider.record_tool_usage(tool_name='tool1', duration_ms=50.0, success=True)
    provider.record_tool_usage(tool_name='tool1', duration_ms=75.0, success=False, error='Error')
    provider.record_tool_usage(tool_name='tool2', duration_ms=100.0, success=True)

    # Get tool stats
    stats = provider.get_tool_stats()

    # Check stats for tool1
    assert stats['tool1']['count'] == 2
    assert stats['tool1']['errors'] == 1
    assert stats['tool1']['error_rate'] == 0.5
    assert stats['tool1']['avg_duration_ms'] == 62.5

    # Check stats for tool2
    assert stats['tool2']['count'] == 1
    assert stats['tool2']['errors'] == 0
    assert stats['tool2']['error_rate'] == 0.0
    assert stats['tool2']['avg_duration_ms'] == 100.0


def test_in_memory_metrics_provider_get_recent_errors():
    """Test getting recent errors from the InMemoryMetricsProvider."""
    provider = InMemoryMetricsProvider()

    # Record some API calls with errors
    provider.record_api_call(
        path='/test1', method='GET', status_code=500, duration_ms=100.0, error='Error 1'
    )
    provider.record_api_call(
        path='/test2', method='POST', status_code=400, duration_ms=150.0, error='Error 2'
    )
    provider.record_api_call(
        path='/test3', method='PUT', status_code=200, duration_ms=75.0
    )  # No error

    # Get recent errors
    errors = provider.get_recent_errors(limit=2)

    # Should have 2 errors, most recent first
    assert len(errors) == 2
    assert errors[0]['path'] == '/test2'
    assert errors[0]['error'] == 'Error 2'
    assert errors[1]['path'] == '/test1'
    assert errors[1]['error'] == 'Error 1'

    # Test with a smaller limit
    errors = provider.get_recent_errors(limit=1)
    assert len(errors) == 1
    assert errors[0]['path'] == '/test2'


def test_in_memory_metrics_provider_get_summary():
    """Test getting a summary from the InMemoryMetricsProvider."""
    provider = InMemoryMetricsProvider()

    # Record some API calls and tool usage
    provider.record_api_call(path='/test1', method='GET', status_code=200, duration_ms=100.0)
    provider.record_api_call(
        path='/test2', method='POST', status_code=500, duration_ms=150.0, error='Error'
    )
    provider.record_tool_usage(tool_name='tool1', duration_ms=50.0, success=True)
    provider.record_tool_usage(
        tool_name='tool2', duration_ms=75.0, success=False, error='Tool Error'
    )

    # Get summary
    summary = provider.get_summary()

    # Check API calls summary
    assert summary['api_calls']['total'] == 2
    assert summary['api_calls']['errors'] == 1
    assert summary['api_calls']['error_rate'] == 0.5
    assert summary['api_calls']['paths'] == 2

    # Check tool usage summary
    assert summary['tool_usage']['total'] == 2
    assert summary['tool_usage']['errors'] == 1
    assert summary['tool_usage']['error_rate'] == 0.5
    assert summary['tool_usage']['tools'] == 2


@patch('awslabs.openapi_mcp_server.utils.metrics_provider.USE_PROMETHEUS', False)
def test_create_metrics_provider():
    """Test creating the metrics provider."""
    provider = create_metrics_provider()
    assert isinstance(provider, InMemoryMetricsProvider)
