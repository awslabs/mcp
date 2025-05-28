"""Tests for the Prometheus metrics provider.

Note: These tests are skipped if the prometheus_client package is not installed.
This is expected behavior and not a test failure. To run these tests:
1. Install the prometheus_client package: pip install prometheus_client
2. Run the tests: pytest tests/utils/test_metrics_provider_prometheus.py -v
"""

import pytest
import time
from awslabs.openapi_mcp_server.utils.metrics_provider import (
    PROMETHEUS_AVAILABLE,
    PrometheusMetricsProvider,
    create_metrics_provider,
)
from unittest.mock import MagicMock, patch


@pytest.mark.skipif(not PROMETHEUS_AVAILABLE, reason='Prometheus client not available')
class TestPrometheusMetricsProvider:
    """Tests for the PrometheusMetricsProvider class."""

    @patch('prometheus_client.start_http_server')
    def test_init(self, mock_start_server):
        """Test initialization of the Prometheus metrics provider."""
        with patch('awslabs.openapi_mcp_server.utils.metrics_provider.PROMETHEUS_PORT', 9090):
            provider = PrometheusMetricsProvider()

            # Check that the server was started
            mock_start_server.assert_called_once_with(9090)

            # Check that metrics were created
            assert hasattr(provider, '_api_requests')
            assert hasattr(provider, '_api_errors')
            assert hasattr(provider, '_api_duration')
            assert hasattr(provider, '_tool_calls')
            assert hasattr(provider, '_tool_errors')
            assert hasattr(provider, '_tool_duration')

            # Check that recent errors buffer was initialized
            assert provider._recent_errors == []
            assert provider._max_errors == 100

    @patch('prometheus_client.start_http_server')
    def test_record_api_call_success(self, mock_start_server):
        """Test recording a successful API call with Prometheus."""
        with patch('awslabs.openapi_mcp_server.utils.metrics_provider.PROMETHEUS_PORT', 0):
            provider = PrometheusMetricsProvider()

            # Mock the Prometheus metrics
            provider._api_requests = MagicMock()
            provider._api_requests.labels.return_value = MagicMock()
            provider._api_duration = MagicMock()
            provider._api_duration.labels.return_value = MagicMock()
            provider._api_errors = MagicMock()

            # Record an API call
            provider.record_api_call(
                path='/test',
                method='GET',
                status_code=200,
                duration_ms=10.5,
            )

            # Check that metrics were updated
            provider._api_requests.labels.assert_called_once_with(
                method='GET', path='/test', status='success'
            )
            provider._api_requests.labels.return_value.inc.assert_called_once()
            provider._api_duration.labels.assert_called_once_with(method='GET', path='/test')
            provider._api_duration.labels.return_value.observe.assert_called_once_with(
                10.5 / 1000.0
            )
            provider._api_errors.labels.assert_not_called()

            # Check that no error was recorded
            assert len(provider._recent_errors) == 0

    @patch('prometheus_client.start_http_server')
    def test_record_api_call_error(self, mock_start_server):
        """Test recording an API call with an error."""
        with patch('awslabs.openapi_mcp_server.utils.metrics_provider.PROMETHEUS_PORT', 0):
            provider = PrometheusMetricsProvider()

            # Mock the Prometheus metrics
            provider._api_requests = MagicMock()
            provider._api_requests.labels.return_value = MagicMock()
            provider._api_duration = MagicMock()
            provider._api_duration.labels.return_value = MagicMock()
            provider._api_errors = MagicMock()
            provider._api_errors.labels.return_value = MagicMock()

            # Record an API call with error
            provider.record_api_call(
                path='/test',
                method='POST',
                status_code=500,
                duration_ms=20.3,
                error='Internal Server Error',
            )

            # Check that metrics were updated
            provider._api_requests.labels.assert_called_once_with(
                method='POST', path='/test', status='error'
            )
            provider._api_requests.labels.return_value.inc.assert_called_once()
            provider._api_duration.labels.assert_called_once_with(method='POST', path='/test')
            provider._api_duration.labels.return_value.observe.assert_called_once_with(
                20.3 / 1000.0
            )
            provider._api_errors.labels.assert_called_once_with(method='POST', path='/test')
            provider._api_errors.labels.return_value.inc.assert_called_once()

            # Check that error was recorded
            assert len(provider._recent_errors) == 1
            assert provider._recent_errors[0]['path'] == '/test'
            assert provider._recent_errors[0]['method'] == 'POST'
            assert provider._recent_errors[0]['status_code'] == 500
            assert provider._recent_errors[0]['error'] == 'Internal Server Error'
            assert provider._recent_errors[0]['duration_ms'] == 20.3
            assert 'timestamp' in provider._recent_errors[0]

    @patch('prometheus_client.start_http_server')
    def test_record_tool_usage_success(self, mock_start_server):
        """Test recording successful tool usage with Prometheus."""
        with patch('awslabs.openapi_mcp_server.utils.metrics_provider.PROMETHEUS_PORT', 0):
            provider = PrometheusMetricsProvider()

            # Mock the Prometheus metrics
            provider._tool_calls = MagicMock()
            provider._tool_calls.labels.return_value = MagicMock()
            provider._tool_duration = MagicMock()
            provider._tool_duration.labels.return_value = MagicMock()
            provider._tool_errors = MagicMock()

            # Record tool usage
            provider.record_tool_usage(
                tool_name='test_tool',
                duration_ms=15.2,
                success=True,
            )

            # Check that metrics were updated
            provider._tool_calls.labels.assert_called_once_with(tool='test_tool', status='success')
            provider._tool_calls.labels.return_value.inc.assert_called_once()
            provider._tool_duration.labels.assert_called_once_with(tool='test_tool')
            provider._tool_duration.labels.return_value.observe.assert_called_once_with(
                15.2 / 1000.0
            )
            provider._tool_errors.labels.assert_not_called()

    @patch('prometheus_client.start_http_server')
    def test_record_tool_usage_error(self, mock_start_server):
        """Test recording tool usage with an error."""
        with patch('awslabs.openapi_mcp_server.utils.metrics_provider.PROMETHEUS_PORT', 0):
            provider = PrometheusMetricsProvider()

            # Mock the Prometheus metrics
            provider._tool_calls = MagicMock()
            provider._tool_calls.labels.return_value = MagicMock()
            provider._tool_duration = MagicMock()
            provider._tool_duration.labels.return_value = MagicMock()
            provider._tool_errors = MagicMock()
            provider._tool_errors.labels.return_value = MagicMock()

            # Record tool usage with error
            provider.record_tool_usage(
                tool_name='test_tool',
                duration_ms=25.7,
                success=False,
                error='Tool execution failed',
            )

            # Check that metrics were updated
            provider._tool_calls.labels.assert_called_once_with(tool='test_tool', status='error')
            provider._tool_calls.labels.return_value.inc.assert_called_once()
            provider._tool_duration.labels.assert_called_once_with(tool='test_tool')
            provider._tool_duration.labels.return_value.observe.assert_called_once_with(
                25.7 / 1000.0
            )
            provider._tool_errors.labels.assert_called_once_with(tool='test_tool')
            provider._tool_errors.labels.return_value.inc.assert_called_once()

    @patch('prometheus_client.start_http_server')
    def test_get_api_stats(self, mock_start_server):
        """Test getting API stats from Prometheus provider."""
        with patch('awslabs.openapi_mcp_server.utils.metrics_provider.PROMETHEUS_PORT', 0):
            provider = PrometheusMetricsProvider()

            # Get stats - should return empty dict
            stats = provider.get_api_stats()
            assert stats == {}

    @patch('prometheus_client.start_http_server')
    def test_get_tool_stats(self, mock_start_server):
        """Test getting tool stats from Prometheus provider."""
        with patch('awslabs.openapi_mcp_server.utils.metrics_provider.PROMETHEUS_PORT', 0):
            provider = PrometheusMetricsProvider()

            # Get stats - should return defaultdict with default values
            stats = provider.get_tool_stats()

            # Test that it returns default values for any key
            assert stats['nonexistent_tool']['count'] == 0
            assert stats['nonexistent_tool']['errors'] == 0
            assert stats['nonexistent_tool']['error_rate'] == 0.0
            assert stats['nonexistent_tool']['avg_duration_ms'] == 0.0

    @patch('prometheus_client.start_http_server')
    def test_get_recent_errors(self, mock_start_server):
        """Test getting recent errors from Prometheus provider."""
        with patch('awslabs.openapi_mcp_server.utils.metrics_provider.PROMETHEUS_PORT', 0):
            provider = PrometheusMetricsProvider()

            # Initially should be empty
            assert provider.get_recent_errors() == []

            # Add some errors
            provider._recent_errors = [
                {
                    'path': '/test1',
                    'method': 'GET',
                    'status_code': 500,
                    'error': 'Error 1',
                    'timestamp': time.time(),
                },
                {
                    'path': '/test2',
                    'method': 'POST',
                    'status_code': 400,
                    'error': 'Error 2',
                    'timestamp': time.time(),
                },
            ]

            # Get all errors
            errors = provider.get_recent_errors()
            assert len(errors) == 2

            # Get limited errors
            errors = provider.get_recent_errors(limit=1)
            assert len(errors) == 1
            assert errors[0]['path'] == '/test2'  # Most recent first

    @patch('prometheus_client.start_http_server')
    def test_get_summary(self, mock_start_server):
        """Test getting summary from Prometheus provider."""
        with patch('awslabs.openapi_mcp_server.utils.metrics_provider.PROMETHEUS_PORT', 9090):
            provider = PrometheusMetricsProvider()

            # Get summary
            summary = provider.get_summary()

            # Check that it contains the expected keys with placeholder values
            assert summary['api_calls']['total'] == 'Available in Prometheus'
            assert summary['api_calls']['errors'] == 'Available in Prometheus'
            assert summary['api_calls']['paths'] == 'Available in Prometheus'

            assert summary['tool_usage']['total'] == 'Available in Prometheus'
            assert summary['tool_usage']['errors'] == 'Available in Prometheus'
            assert summary['tool_usage']['tools'] == 'Available in Prometheus'

            assert summary['prometheus_enabled'] is True
            assert summary['prometheus_port'] == 9090


@patch('awslabs.openapi_mcp_server.utils.metrics_provider.PROMETHEUS_AVAILABLE', True)
@patch('awslabs.openapi_mcp_server.utils.metrics_provider.USE_PROMETHEUS', True)
@patch('awslabs.openapi_mcp_server.utils.metrics_provider.PrometheusMetricsProvider')
def test_create_metrics_provider_prometheus(mock_prometheus_provider):
    """Test creating a Prometheus metrics provider."""
    # Set up the mock
    mock_instance = MagicMock()
    mock_prometheus_provider.return_value = mock_instance

    # Create the provider
    provider = create_metrics_provider()

    # Check that the Prometheus provider was created
    mock_prometheus_provider.assert_called_once()
    assert provider == mock_instance


@patch('awslabs.openapi_mcp_server.utils.metrics_provider.PROMETHEUS_AVAILABLE', True)
@patch('awslabs.openapi_mcp_server.utils.metrics_provider.USE_PROMETHEUS', True)
@patch(
    'awslabs.openapi_mcp_server.utils.metrics_provider.PrometheusMetricsProvider',
    side_effect=Exception('Test error'),
)
@patch('awslabs.openapi_mcp_server.utils.metrics_provider.InMemoryMetricsProvider')
def test_create_metrics_provider_fallback(mock_memory_provider, mock_prometheus_provider):
    """Test fallback to in-memory provider when Prometheus fails."""
    # Set up the mock
    mock_instance = MagicMock()
    mock_memory_provider.return_value = mock_instance

    # Create the provider
    provider = create_metrics_provider()

    # Check that the Prometheus provider was attempted
    mock_prometheus_provider.assert_called_once()

    # Check that it fell back to in-memory provider
    mock_memory_provider.assert_called_once()
    assert provider == mock_instance


@patch('awslabs.openapi_mcp_server.utils.metrics_provider.PROMETHEUS_AVAILABLE', False)
@patch('awslabs.openapi_mcp_server.utils.metrics_provider.USE_PROMETHEUS', True)
@patch('awslabs.openapi_mcp_server.utils.metrics_provider.InMemoryMetricsProvider')
def test_create_metrics_provider_prometheus_not_available(mock_memory_provider):
    """Test fallback when Prometheus is requested but not available."""
    # Set up the mock
    mock_instance = MagicMock()
    mock_memory_provider.return_value = mock_instance

    # Create the provider
    provider = create_metrics_provider()

    # Check that it used in-memory provider
    mock_memory_provider.assert_called_once()
    assert provider == mock_instance


@patch('awslabs.openapi_mcp_server.utils.metrics_provider.PROMETHEUS_AVAILABLE', False)
@patch('awslabs.openapi_mcp_server.utils.metrics_provider.USE_PROMETHEUS', False)
@patch('awslabs.openapi_mcp_server.utils.metrics_provider.InMemoryMetricsProvider')
def test_create_metrics_provider_in_memory(mock_memory_provider):
    """Test creating an in-memory metrics provider."""
    # Set up the mock
    mock_instance = MagicMock()
    mock_memory_provider.return_value = mock_instance

    # Create the provider
    provider = create_metrics_provider()

    # Check that the in-memory provider was created
    mock_memory_provider.assert_called_once()
    assert provider == mock_instance
