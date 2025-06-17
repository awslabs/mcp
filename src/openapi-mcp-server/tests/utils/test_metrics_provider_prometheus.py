"""Tests for the Prometheus metrics provider.

Note: These tests use mocking to simulate prometheus_client functionality
when the package is not installed, ensuring tests always run.
"""

import time
from awslabs.openapi_mcp_server.utils.metrics_provider import (
    PrometheusMetricsProvider,
    create_metrics_provider,
)
from unittest.mock import MagicMock, patch


# Mock prometheus_client for testing
class MockPrometheusClient:
    """Mock implementation of prometheus_client for testing."""

    class Counter:
        """Mock Counter class."""

        def __init__(self, name, description, labelnames=None):
            """Initialize mock counter."""
            self.name = name
            self.description = description
            self.labelnames = labelnames or []

        def labels(self, **kwargs):
            """Return mock metric with labels."""
            mock_metric = MagicMock()
            mock_metric.inc = MagicMock()
            return mock_metric

    class Histogram:
        """Mock Histogram class."""

        def __init__(self, name, description, labelnames=None):
            """Initialize mock histogram."""
            self.name = name
            self.description = description
            self.labelnames = labelnames or []

        def labels(self, **kwargs):
            """Return mock metric with labels."""
            mock_metric = MagicMock()
            mock_metric.observe = MagicMock()
            return mock_metric

    @staticmethod
    def start_http_server(port):
        """Mock HTTP server start method."""
        pass


class TestPrometheusMetricsProvider:
    """Tests for the PrometheusMetricsProvider class."""

    @patch('awslabs.openapi_mcp_server.utils.metrics_provider.PROMETHEUS_AVAILABLE', True)
    @patch(
        'awslabs.openapi_mcp_server.utils.metrics_provider.prometheus_client',
        MockPrometheusClient(),
    )
    def test_init(self):
        """Test initialization of the Prometheus metrics provider."""
        with patch('awslabs.openapi_mcp_server.utils.metrics_provider.PROMETHEUS_PORT', 9090):
            provider = PrometheusMetricsProvider()

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

    @patch('awslabs.openapi_mcp_server.utils.metrics_provider.PROMETHEUS_AVAILABLE', True)
    @patch(
        'awslabs.openapi_mcp_server.utils.metrics_provider.prometheus_client',
        MockPrometheusClient(),
    )
    def test_get_api_stats(self):
        """Test getting API stats from Prometheus provider."""
        with patch('awslabs.openapi_mcp_server.utils.metrics_provider.PROMETHEUS_PORT', 0):
            provider = PrometheusMetricsProvider()

            # Get stats - should return empty dict
            stats = provider.get_api_stats()
            assert stats == {}

    @patch('awslabs.openapi_mcp_server.utils.metrics_provider.PROMETHEUS_AVAILABLE', True)
    @patch(
        'awslabs.openapi_mcp_server.utils.metrics_provider.prometheus_client',
        MockPrometheusClient(),
    )
    def test_get_tool_stats(self):
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

    @patch('awslabs.openapi_mcp_server.utils.metrics_provider.PROMETHEUS_AVAILABLE', True)
    @patch(
        'awslabs.openapi_mcp_server.utils.metrics_provider.prometheus_client',
        MockPrometheusClient(),
    )
    def test_get_recent_errors(self):
        """Test getting recent errors from Prometheus provider."""
        with patch('awslabs.openapi_mcp_server.utils.metrics_provider.PROMETHEUS_PORT', 0):
            provider = PrometheusMetricsProvider()

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

    @patch('awslabs.openapi_mcp_server.utils.metrics_provider.PROMETHEUS_AVAILABLE', True)
    @patch(
        'awslabs.openapi_mcp_server.utils.metrics_provider.prometheus_client',
        MockPrometheusClient(),
    )
    def test_get_summary(self):
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


def test_create_metrics_provider_basic():
    """Test creating a basic metrics provider."""
    provider = create_metrics_provider()
    # Should return some kind of metrics provider
    assert provider is not None
