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

"""Metrics collection for enterprise monitoring."""

import time
from typing import Optional, Dict, Any, Callable
from contextlib import contextmanager
from functools import wraps
from collections import defaultdict

from .logger import get_logger

logger = get_logger(__name__)


class MetricsCollector:
    """Collect and emit metrics for monitoring."""

    def __init__(self, namespace: str = "AWSLabs/CloudWANMCP/NetworkFirewall"):
        self.namespace = namespace
        self.metrics_buffer: Dict[str, Any] = defaultdict(list)
        self.counters = defaultdict(int)

    def record_count(
        self, metric_name: str, value: int = 1, unit: str = "Count", dimensions: Optional[Dict] = None
    ) -> None:
        """Record a count metric."""
        dimensions = dimensions or {}
        full_metric = f"{self.namespace}.{metric_name}"
        self.counters[full_metric] += value
        logger.debug(f"Metric: {full_metric}={value} {unit}", extra={"dimensions": dimensions})

        # Store for potential emission to monitoring systems
        self.metrics_buffer[full_metric].append(
            {"value": value, "unit": unit, "dimensions": dimensions, "timestamp": time.time()}
        )

    def record_timing(self, metric_name: str, duration_ms: float, dimensions: Optional[Dict] = None) -> None:
        """Record a timing metric."""
        dimensions = dimensions or {}
        full_metric = f"{self.namespace}.{metric_name}"
        logger.debug(f"Timing: {full_metric}={duration_ms}ms", extra={"dimensions": dimensions})

        # Store timing data for analysis
        self.metrics_buffer[full_metric].append(
            {"value": duration_ms, "unit": "Milliseconds", "dimensions": dimensions, "timestamp": time.time()}
        )

    def record_gauge(
        self, metric_name: str, value: float, unit: str = "None", dimensions: Optional[Dict] = None
    ) -> None:
        """Record a gauge metric."""
        dimensions = dimensions or {}
        full_metric = f"{self.namespace}.{metric_name}"
        logger.debug(f"Gauge: {full_metric}={value} {unit}", extra={"dimensions": dimensions})

        self.metrics_buffer[full_metric] = [
            {"value": value, "unit": unit, "dimensions": dimensions, "timestamp": time.time()}
        ]  # Gauges replace previous value

    @contextmanager
    def timer(self, metric_name: str, dimensions: Optional[Dict] = None):
        """Context manager for timing operations."""
        start_time = time.time()
        try:
            yield
        finally:
            duration_ms = (time.time() - start_time) * 1000
            self.record_timing(metric_name, duration_ms, dimensions)

    def track_api_call(self, api_name: str):
        """Decorator to track API call metrics (supports both sync and async)."""

        def decorator(func: Callable) -> Callable:
            if hasattr(func, "__call__"):

                @wraps(func)
                def sync_wrapper(*args, **kwargs):
                    dimensions = {"api": api_name}

                    with self.timer(f"{api_name}.duration", dimensions):
                        try:
                            result = func(*args, **kwargs)
                            self.record_count(f"{api_name}.success", dimensions=dimensions)
                            return result
                        except Exception as e:
                            self.record_count(
                                f"{api_name}.error", dimensions={**dimensions, "error_type": type(e).__name__}
                            )
                            raise

                @wraps(func)
                async def async_wrapper(*args, **kwargs):
                    dimensions = {"api": api_name}

                    with self.timer(f"{api_name}.duration", dimensions):
                        try:
                            result = await func(*args, **kwargs)
                            self.record_count(f"{api_name}.success", dimensions=dimensions)
                            return result
                        except Exception as e:
                            self.record_count(
                                f"{api_name}.error", dimensions={**dimensions, "error_type": type(e).__name__}
                            )
                            raise

                # Return appropriate wrapper based on function type
                import asyncio

                return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper

            return func

        return decorator

    def track_parsing_metrics(self, format_type: str, content_size: int, rule_count: int, duration_ms: float):
        """Track specific metrics for IaC parsing operations."""
        dimensions = {"format": format_type}

        self.record_count("parsing.requests", dimensions=dimensions)
        self.record_timing("parsing.duration", duration_ms, dimensions)
        self.record_gauge("parsing.content_size_bytes", content_size, "Bytes", dimensions)
        self.record_gauge("parsing.rules_extracted", rule_count, "Count", dimensions)

    def track_validation_metrics(self, format_type: str, is_valid: bool, error_count: int = 0):
        """Track validation-specific metrics."""
        dimensions = {"format": format_type, "valid": str(is_valid).lower()}

        self.record_count("validation.requests", dimensions=dimensions)
        if error_count > 0:
            self.record_gauge("validation.errors", error_count, "Count", dimensions)

    def track_simulation_metrics(self, format_type: str, flow_count: int, duration_ms: float):
        """Track traffic simulation metrics."""
        dimensions = {"format": format_type}

        self.record_count("simulation.requests", dimensions=dimensions)
        self.record_timing("simulation.duration", duration_ms, dimensions)
        self.record_gauge("simulation.flows_processed", flow_count, "Count", dimensions)

    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get summary of collected metrics."""
        return {
            "counters": dict(self.counters),
            "buffer_size": len(self.metrics_buffer),
            "namespace": self.namespace,
            "recent_metrics": {
                metric: data[-5:] if isinstance(data, list) else data  # Last 5 entries
                for metric, data in self.metrics_buffer.items()
            },
        }

    def clear_metrics(self):
        """Clear metrics buffer (useful for testing)."""
        self.metrics_buffer.clear()
        self.counters.clear()


# Global metrics instance
metrics = MetricsCollector()


def track_iac_operation(operation_name: str, format_type: Optional[str] = None):
    """Decorator specifically for IaC operations."""

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            dimensions = {"operation": operation_name}
            if format_type:
                dimensions["format"] = format_type

            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                duration_ms = (time.time() - start_time) * 1000

                # Track success
                metrics.record_count("iac.operation.success", dimensions=dimensions)
                metrics.record_timing("iac.operation.duration", duration_ms, dimensions)

                # Extract additional metrics from result if available
                if isinstance(result, str):
                    try:
                        import json

                        result_data = json.loads(result)
                        if result_data.get("status") == "success":
                            # Try to extract rule count or other metrics
                            data = result_data.get("data", {})
                            for format_key in ["terraform_analysis", "cdk_analysis", "cloudformation_analysis"]:
                                if format_key in data:
                                    rule_count = data[format_key].get("total_rules", 0)
                                    metrics.record_gauge("iac.rules.count", rule_count, "Count", dimensions)
                                    break
                    except:
                        pass  # Ignore JSON parsing errors

                return result

            except Exception as e:
                duration_ms = (time.time() - start_time) * 1000
                metrics.record_count("iac.operation.error", dimensions={**dimensions, "error_type": type(e).__name__})
                metrics.record_timing("iac.operation.error_duration", duration_ms, dimensions)
                raise

        return wrapper

    return decorator
