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
"""Debug helper module for AWS Support MCP Server."""

import time
import traceback
from functools import wraps
from typing import Any, Callable, Dict, ParamSpec, Protocol, TypeVar, Union, cast

from loguru import logger


class DiagnosticsTracker:
    """Helper class for tracking diagnostics information."""

    def __init__(self):
        """Initialize the diagnostics tracker."""
        self._enabled = False
        self._performance_data: Dict[str, Dict[str, Union[int, float]]] = {}
        self._error_counts: Dict[str, int] = {}
        self._request_counts: Dict[str, int] = {}
        self._start_time = time.time()

    @property
    def enabled(self) -> bool:
        """Get the enabled status of diagnostics tracking."""
        return self._enabled

    @property
    def uptime(self) -> float:
        """Get the uptime in seconds since diagnostics was initialized."""
        return time.time() - self._start_time

    def enable(self):
        """Enable diagnostics tracking."""
        self._enabled = True
        self._start_time = time.time()
        logger.debug("Diagnostics tracking enabled")

    def disable(self):
        """Disable diagnostics tracking."""
        self._enabled = False
        logger.debug("Diagnostics tracking disabled")
        self.reset()

    def reset(self):
        """Reset all diagnostics data."""
        self._performance_data.clear()
        self._error_counts.clear()
        self._request_counts.clear()
        logger.debug("Diagnostics data reset")

    def track_performance(self, function_name: str, duration: float):
        """Track performance data for a function."""
        if not self._enabled:
            return

        if function_name not in self._performance_data:
            self._performance_data[function_name] = {
                "count": 0,
                "total_time": 0,
                "min_time": float("inf"),
                "max_time": 0,
                "last_call": 0,
            }

        data = self._performance_data[function_name]
        data["count"] = cast(int, data["count"]) + 1
        data["total_time"] = cast(float, data["total_time"]) + duration
        data["min_time"] = min(cast(float, data["min_time"]), duration)
        data["max_time"] = max(cast(float, data["max_time"]), duration)
        data["last_call"] = time.time()

    def track_error(self, error_type: str):
        """Track error occurrences by type."""
        if not self._enabled:
            return

        if error_type not in self._error_counts:
            self._error_counts[error_type] = 0

        self._error_counts[error_type] += 1

    def track_request(self, request_type: str):
        """Track request counts by type."""
        if not self._enabled:
            return

        if request_type not in self._request_counts:
            self._request_counts[request_type] = 0

        self._request_counts[request_type] += 1

    def get_diagnostics_report(self) -> Dict[str, Any]:
        """Get a report of all diagnostics data."""
        if not self._enabled:
            return {"diagnostics_enabled": False}

        # Calculate averages for performance data
        performance_summary = {}
        for func, data in self._performance_data.items():
            count = cast(int, data["count"])
            if count > 0:
                total_time = cast(float, data["total_time"])
                avg_time = total_time / count
                performance_summary[func] = {
                    "count": count,
                    "avg_time": avg_time,
                    "min_time": data["min_time"],
                    "max_time": data["max_time"],
                    "last_call": data["last_call"],
                    "total_time": total_time,
                }

        return {
            "diagnostics_enabled": True,
            "uptime": self.uptime,
            "start_time": self._start_time,
            "performance": performance_summary,
            "errors": dict(self._error_counts),
            "requests": dict(self._request_counts),
        }


# Create a global diagnostics tracker instance
diagnostics = DiagnosticsTracker()

# Type variable for generic function types
P = ParamSpec("P")
R = TypeVar("R", covariant=True)


class AsyncCallable(Protocol[P, R]):
    async def __call__(self, *args: P.args, **kwargs: P.kwargs) -> R: ...


def track_performance(func: AsyncCallable[P, R]) -> AsyncCallable[P, R]:
    """Decorator to track function performance."""

    @wraps(func)
    async def wrapper(*args, **kwargs):
        func_name = getattr(func, "__name__", str(func))
        start_time = time.time()
        try:
            result = await func(*args, **kwargs)
            return result
        finally:
            duration = time.time() - start_time
            diagnostics.track_performance(func_name, duration)
            if diagnostics.enabled:
                logger.debug(f"Performance: {func_name} took {duration:.4f}s")

    return cast(AsyncCallable[P, R], wrapper)


def track_errors(func: AsyncCallable[P, R]) -> AsyncCallable[P, R]:
    """Decorator to track function errors."""

    @wraps(func)
    async def wrapper(*args, **kwargs):
        func_name = getattr(func, "__name__", str(func))
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            error_type = type(e).__name__
            diagnostics.track_error(error_type)
            if diagnostics.enabled:
                logger.error(f"Error in {func_name}: {error_type} - {str(e)}")
                logger.debug(f"Error traceback: {traceback.format_exc()}")
            raise

    return cast(AsyncCallable[P, R], wrapper)


def track_request(request_type: str) -> Callable[[AsyncCallable[P, R]], AsyncCallable[P, R]]:
    """Decorator to track request counts by type."""

    def decorator(func: AsyncCallable[P, R]) -> AsyncCallable[P, R]:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            diagnostics.track_request(request_type)
            if diagnostics.enabled:
                logger.debug(f"Request: {request_type}")
            return await func(*args, **kwargs)

        return cast(AsyncCallable[P, R], wrapper)

    return decorator


def get_diagnostics_report() -> Dict[str, Any]:
    """Get a report of all diagnostics data."""
    return diagnostics.get_diagnostics_report()
