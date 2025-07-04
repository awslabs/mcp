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
"""Metrics provider for the OpenAPI MCP Server.

This module provides a pluggable metrics system with different backends.
The default is a simple in-memory implementation, but it can be switched
to use Prometheus or other backends via environment variables.
"""

import time
from abc import ABC, abstractmethod
from awslabs.openapi_mcp_server import logger
from awslabs.openapi_mcp_server.utils.config import (
    METRICS_MAX_HISTORY,
    PROMETHEUS_PORT,
    USE_PROMETHEUS,
)
from collections import defaultdict
from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class ApiCallMetrics:
    """Metrics for API calls."""

    path: str
    method: str
    status_code: int
    duration_ms: float
    timestamp: float
    error: Optional[str] = None


@dataclass
class ToolMetrics:
    """Metrics for tool usage."""

    tool_name: str
    duration_ms: float
    timestamp: float
    success: bool
    error: Optional[str] = None


class MetricsProvider(ABC):
    """Abstract base class for metrics providers."""

    @abstractmethod
    def record_api_call(
        self,
        path: str,
        method: str,
        status_code: int,
        duration_ms: float,
        error: Optional[str] = None,
    ) -> None:
        """Record metrics for an API call."""
        pass

    @abstractmethod
    def record_tool_usage(
        self, tool_name: str, duration_ms: float, success: bool, error: Optional[str] = None
    ) -> None:
        """Record metrics for tool usage."""
        pass

    @abstractmethod
    def get_api_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get statistics for API calls."""
        pass

    @abstractmethod
    def get_tool_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get statistics for tool usage."""
        pass

    @abstractmethod
    def get_recent_errors(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent API call errors."""
        pass

    @abstractmethod
    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of all metrics."""
        pass


class InMemoryMetricsProvider(MetricsProvider):
    """Simple in-memory metrics provider."""

    def __init__(self, max_history: Optional[int] = None):
        """Initialize the metrics provider.

        Args:
            max_history: Maximum number of API calls to keep in history (defaults to config value)

        """
        self._api_calls: List[ApiCallMetrics] = []
        self._tool_usage: List[ToolMetrics] = []
        self._max_history = max_history if max_history is not None else METRICS_MAX_HISTORY
        self._path_stats: Dict[str, Dict[str, Any]] = defaultdict(
            lambda: {'count': 0, 'errors': 0, 'total_duration_ms': 0}
        )
        self._tool_stats: Dict[str, Dict[str, Any]] = defaultdict(
            lambda: {'count': 0, 'errors': 0, 'total_duration_ms': 0}
        )
        logger.debug(
            f'Created in-memory metrics provider with max history of {self._max_history} entries'
        )

    def record_api_call(
        self,
        path: str,
        method: str,
        status_code: int,
        duration_ms: float,
        error: Optional[str] = None,
    ) -> None:
        """Record metrics for an API call."""
        # Create metrics object
        metrics = ApiCallMetrics(
            path=path,
            method=method,
            status_code=status_code,
            duration_ms=duration_ms,
            timestamp=time.time(),
            error=error,
        )

        # Add to history, maintaining max size
        self._api_calls.append(metrics)
        if len(self._api_calls) > self._max_history:
            self._api_calls.pop(0)

        # Update path stats
        path_key = f'{method.upper()} {path}'
        self._path_stats[path_key]['count'] += 1
        self._path_stats[path_key]['total_duration_ms'] += duration_ms
        if error or status_code >= 400:
            self._path_stats[path_key]['errors'] += 1

        # Log the API call
        if error or status_code >= 400:
            logger.warning(
                f'API call {method.upper()} {path} failed with status {status_code}: {error or "No error details"} ({duration_ms:.2f}ms)'
            )
        else:
            logger.debug(
                f'API call {method.upper()} {path} succeeded with status {status_code} ({duration_ms:.2f}ms)'
            )

    def record_tool_usage(
        self, tool_name: str, duration_ms: float, success: bool, error: Optional[str] = None
    ) -> None:
        """Record metrics for tool usage."""
        # Create metrics object
        metrics = ToolMetrics(
            tool_name=tool_name,
            duration_ms=duration_ms,
            timestamp=time.time(),
            success=success,
            error=error,
        )

        # Add to history, maintaining max size
        self._tool_usage.append(metrics)
        if len(self._tool_usage) > self._max_history:
            self._tool_usage.pop(0)

        # Update tool stats
        self._tool_stats[tool_name]['count'] += 1
        self._tool_stats[tool_name]['total_duration_ms'] += duration_ms
        if not success:
            self._tool_stats[tool_name]['errors'] += 1

        # Log the tool usage
        if not success:
            logger.warning(
                f'Tool {tool_name} failed: {error or "No error details"} ({duration_ms:.2f}ms)'
            )
        else:
            logger.debug(f'Tool {tool_name} succeeded ({duration_ms:.2f}ms)')

    def get_api_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get statistics for API calls."""
        result = {}
        for path, stats in self._path_stats.items():
            count = stats['count']
            result[path] = {
                'count': count,
                'errors': stats['errors'],
                'error_rate': (stats['errors'] / count) if count > 0 else 0,
                'avg_duration_ms': (stats['total_duration_ms'] / count) if count > 0 else 0,
            }
        return result

    def get_tool_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get statistics for tool usage."""
        result = {}
        for tool, stats in self._tool_stats.items():
            count = stats['count']
            result[tool] = {
                'count': count,
                'errors': stats['errors'],
                'error_rate': (stats['errors'] / count) if count > 0 else 0,
                'avg_duration_ms': (stats['total_duration_ms'] / count) if count > 0 else 0,
            }
        return result

    def get_recent_errors(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent API call errors."""
        errors = []
        for call in reversed(self._api_calls):
            if call.error or call.status_code >= 400:
                errors.append(
                    {
                        'path': call.path,
                        'method': call.method,
                        'status_code': call.status_code,
                        'error': call.error,
                        'duration_ms': call.duration_ms,
                        'timestamp': call.timestamp,
                    }
                )
                if len(errors) >= limit:
                    break
        return errors

    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of all metrics."""
        api_calls = len(self._api_calls)
        tool_calls = len(self._tool_usage)

        api_errors = sum(1 for call in self._api_calls if call.error or call.status_code >= 400)
        tool_errors = sum(1 for usage in self._tool_usage if not usage.success)

        return {
            'api_calls': {
                'total': api_calls,
                'errors': api_errors,
                'error_rate': (api_errors / api_calls) if api_calls > 0 else 0,
                'paths': len(self._path_stats),
            },
            'tool_usage': {
                'total': tool_calls,
                'errors': tool_errors,
                'error_rate': (tool_errors / tool_calls) if tool_calls > 0 else 0,
                'tools': len(self._tool_stats),
            },
        }


# Try to import prometheus_client if enabled
# Note: Tests for PrometheusMetricsProvider will be skipped if prometheus_client
# is not installed. This is expected behavior and not a test failure.
PROMETHEUS_AVAILABLE = False
prometheus_client = None
if USE_PROMETHEUS:
    try:
        import prometheus_client

        PROMETHEUS_AVAILABLE = True
        logger.info('Prometheus metrics enabled')
    except ImportError:
        logger.warning(
            'Prometheus metrics requested but prometheus_client not installed. '
            'Install with: pip install prometheus_client'
        )


class PrometheusMetricsProvider(MetricsProvider):
    """Prometheus metrics provider."""

    def __init__(self):
        """Initialize the Prometheus metrics provider."""
        if not PROMETHEUS_AVAILABLE or prometheus_client is None:
            raise ImportError('prometheus_client not available')

        # Create Prometheus metrics
        self._api_requests = prometheus_client.Counter(
            'mcp_api_requests_total', 'Total API requests', ['method', 'path', 'status']
        )
        self._api_errors = prometheus_client.Counter(
            'mcp_api_errors_total', 'Total API errors', ['method', 'path']
        )
        self._api_duration = prometheus_client.Histogram(
            'mcp_api_request_duration_seconds',
            'API request duration in seconds',
            ['method', 'path'],
        )
        self._tool_calls = prometheus_client.Counter(
            'mcp_tool_calls_total', 'Total tool calls', ['tool', 'status']
        )
        self._tool_errors = prometheus_client.Counter(
            'mcp_tool_errors_total', 'Total tool errors', ['tool']
        )
        self._tool_duration = prometheus_client.Histogram(
            'mcp_tool_duration_seconds', 'Tool execution duration in seconds', ['tool']
        )

        # Start metrics server if port is specified
        if PROMETHEUS_PORT > 0:
            prometheus_client.start_http_server(PROMETHEUS_PORT)
            logger.info(f'Started Prometheus metrics server on port {PROMETHEUS_PORT}')

        # Keep a small in-memory buffer for recent errors
        self._recent_errors = []
        self._max_errors = 100

        logger.info('Created Prometheus metrics provider')

    def record_api_call(
        self,
        path: str,
        method: str,
        status_code: int,
        duration_ms: float,
        error: Optional[str] = None,
    ) -> None:
        """Record metrics for an API call."""
        # Update Prometheus metrics
        status = 'error' if status_code >= 400 or error else 'success'
        self._api_requests.labels(method=method, path=path, status=status).inc()
        self._api_duration.labels(method=method, path=path).observe(duration_ms / 1000.0)

        if error or status_code >= 400:
            self._api_errors.labels(method=method, path=path).inc()

            # Add to recent errors
            self._recent_errors.append(
                {
                    'path': path,
                    'method': method,
                    'status_code': status_code,
                    'error': error,
                    'duration_ms': duration_ms,
                    'timestamp': time.time(),
                }
            )
            if len(self._recent_errors) > self._max_errors:
                self._recent_errors.pop(0)

        # Log the API call
        if error or status_code >= 400:
            logger.warning(
                f'API call {method.upper()} {path} failed with status {status_code}: {error or "No error details"} ({duration_ms:.2f}ms)'
            )
        else:
            logger.debug(
                f'API call {method.upper()} {path} succeeded with status {status_code} ({duration_ms:.2f}ms)'
            )

    def record_tool_usage(
        self, tool_name: str, duration_ms: float, success: bool, error: Optional[str] = None
    ) -> None:
        """Record metrics for tool usage."""
        # Update Prometheus metrics
        status = 'success' if success else 'error'
        self._tool_calls.labels(tool=tool_name, status=status).inc()
        self._tool_duration.labels(tool=tool_name).observe(duration_ms / 1000.0)

        if not success:
            self._tool_errors.labels(tool=tool_name).inc()

        # Log the tool usage
        if not success:
            logger.warning(
                f'Tool {tool_name} failed: {error or "No error details"} ({duration_ms:.2f}ms)'
            )
        else:
            logger.debug(f'Tool {tool_name} succeeded ({duration_ms:.2f}ms)')

    def get_api_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get statistics for API calls.

        Note: This is a limited implementation since Prometheus doesn't provide
        a way to query metrics directly. We return an empty dict.
        """
        logger.warning('API stats not available with Prometheus metrics provider')
        return {}

    def get_tool_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get statistics for tool usage.

        Note: This is a limited implementation since Prometheus doesn't provide
        a way to query metrics directly. We return a default dict with empty values
        to prevent errors in consumers.
        """
        # Instead of just returning an empty dict and logging a warning,
        # return a defaultdict that will provide empty values for any key
        from collections import defaultdict

        # Create a nested defaultdict that returns default values for any key
        def nested_dict():
            return {'count': 0, 'errors': 0, 'error_rate': 0.0, 'avg_duration_ms': 0.0}

        result = defaultdict(nested_dict)

        # Log at debug level instead of warning to avoid filling logs
        logger.debug('Detailed tool stats not available with Prometheus metrics provider')
        return result

    def get_recent_errors(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent API call errors."""
        return self._recent_errors[-limit:] if self._recent_errors else []

    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of all metrics.

        Note: This is a limited implementation since Prometheus doesn't provide
        a way to query metrics directly. We return a minimal summary.
        """
        return {
            'api_calls': {
                'total': 'Available in Prometheus',
                'errors': 'Available in Prometheus',
                'paths': 'Available in Prometheus',
            },
            'tool_usage': {
                'total': 'Available in Prometheus',
                'errors': 'Available in Prometheus',
                'tools': 'Available in Prometheus',
            },
            'prometheus_enabled': True,
            'prometheus_port': PROMETHEUS_PORT,
        }


# Create the appropriate metrics provider based on configuration
def create_metrics_provider() -> MetricsProvider:
    """Create a metrics provider based on configuration."""
    if USE_PROMETHEUS and PROMETHEUS_AVAILABLE:
        try:
            return PrometheusMetricsProvider()
        except Exception as e:
            logger.error(f'Failed to create Prometheus metrics provider: {e}')
            logger.info('Falling back to in-memory metrics provider')

    # Default to in-memory provider
    return InMemoryMetricsProvider()


# Global metrics provider instance
metrics = create_metrics_provider()


def api_call_timer(func):
    """Time API calls and record metrics."""

    async def wrapper(*args, **kwargs):
        start_time = time.time()
        path = kwargs.get('path', 'unknown')
        method = kwargs.get('method', 'unknown')

        try:
            response = await func(*args, **kwargs)
            duration_ms = (time.time() - start_time) * 1000
            metrics.record_api_call(
                path=path, method=method, status_code=response.status_code, duration_ms=duration_ms
            )
            return response
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            metrics.record_api_call(
                path=path, method=method, status_code=500, duration_ms=duration_ms, error=str(e)
            )
            raise

    return wrapper


def tool_usage_timer(func):
    """Time tool usage and record metrics."""

    async def wrapper(*args, **kwargs):
        start_time = time.time()
        tool_name = getattr(func, '__name__', 'unknown')

        try:
            result = await func(*args, **kwargs)
            duration_ms = (time.time() - start_time) * 1000
            metrics.record_tool_usage(tool_name=tool_name, duration_ms=duration_ms, success=True)
            return result
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            metrics.record_tool_usage(
                tool_name=tool_name, duration_ms=duration_ms, success=False, error=str(e)
            )
            raise

    return wrapper
