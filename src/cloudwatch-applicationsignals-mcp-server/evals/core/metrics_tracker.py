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

"""Metrics tracking for MCP tool evaluation.

Tracks tool calls, success rates, hit rates, and task duration.
"""

import time
from .file_tools import FILE_TOOL_LIST_FILES, FILE_TOOL_READ_FILE, FILE_TOOL_WRITE_FILE
from typing import Any, Dict, List, Optional


class MetricsTracker:
    """Tracks metrics for tool calls and task execution."""

    def __init__(self):
        """Initialize metrics tracker."""
        # TODO: Create ToolCall dataclass/TypedDict to replace Dict[str, Any]
        self.tool_calls: List[Dict[str, Any]] = []
        self.task_start_time: Optional[float] = None
        self.task_end_time: Optional[float] = None
        self.turn_count: int = 0

    def start_task(self):
        """Mark task start time."""
        self.task_start_time = time.time()

    def end_task(self):
        """Mark task end time."""
        self.task_end_time = time.time()

    def record_turn_count(self, turn_count: int):
        """Record the number of agent loop turns.

        Args:
            turn_count: Number of turns used in agent loop
        """
        self.turn_count = turn_count

    def record_tool_call(
        self,
        tool_name: str,
        parameters: Dict[str, Any],
        duration: float,
        success: bool,
        error: Optional[str] = None,
    ):
        """Record a tool call."""
        self.tool_calls.append(
            {
                'tool_name': tool_name,
                'parameters': parameters,
                'duration': duration,
                'success': success,
                'error': error,
                'timestamp': time.time(),
            }
        )

    @property
    def success_rate(self) -> float:
        """Calculate success rate of tool calls."""
        if not self.tool_calls:
            return 0.0
        return sum(1 for c in self.tool_calls if c['success']) / len(self.tool_calls)

    @property
    def tool_call_count(self) -> int:
        """Return total number of tool calls."""
        return len(self.tool_calls)

    @property
    def unique_tools_count(self) -> int:
        """Return number of unique tools called."""
        return len({c['tool_name'] for c in self.tool_calls})

    @property
    def task_duration(self) -> float:
        """Calculate task duration in seconds."""
        if self.task_start_time and self.task_end_time:
            return self.task_end_time - self.task_start_time
        return 0.0

    @property
    def tool_breakdown(self) -> Dict[str, Dict[str, int]]:
        """Calculate per-tool call statistics."""
        breakdown = {}
        for call in self.tool_calls:
            tool_name = call['tool_name']
            if tool_name not in breakdown:
                breakdown[tool_name] = {'count': 0, 'success': 0, 'failed': 0}
            breakdown[tool_name]['count'] += 1
            if call['success']:
                breakdown[tool_name]['success'] += 1
            else:
                breakdown[tool_name]['failed'] += 1
        return breakdown

    @property
    def file_operation_count(self) -> int:
        """Return count of file operation tool calls."""
        return len(self._get_file_operation_calls())

    @property
    def file_read_count(self) -> int:
        """Return count of read_file calls."""
        return len(
            [c for c in self._get_file_operation_calls() if c['tool_name'] == FILE_TOOL_READ_FILE]
        )

    @property
    def file_write_count(self) -> int:
        """Return count of write_file calls."""
        return len(
            [c for c in self._get_file_operation_calls() if c['tool_name'] == FILE_TOOL_WRITE_FILE]
        )

    def _get_file_operation_calls(self) -> List[Dict[str, Any]]:
        """Get all file operation tool calls."""
        return [
            c
            for c in self.tool_calls
            if c['tool_name'] in [FILE_TOOL_LIST_FILES, FILE_TOOL_READ_FILE, FILE_TOOL_WRITE_FILE]
        ]

    def _compare_expected_tools(self, expected_tools: List[str]) -> Dict[str, Any]:
        """Compare called tools against expected tools.

        Args:
            expected_tools: List of MCP tools expected to be used

        Returns:
            Dictionary with hit_rate, expected_tools_called, missing_expected_tools, unexpected_tools_called
        """
        expected_tool_set = set(expected_tools)
        called_tool_names = {c['tool_name'] for c in self.tool_calls}
        called_expected = called_tool_names & expected_tool_set
        missing = expected_tool_set - called_tool_names
        unexpected = called_tool_names - expected_tool_set

        return {
            'hit_rate': len(called_expected) / len(expected_tool_set)
            if expected_tool_set
            else 0.0,
            'expected_tools_called': sorted(called_expected),
            'missing_expected_tools': sorted(missing),
            'unexpected_tools_called': sorted(unexpected),
        }

    def get_metrics_report(self, expected_tools: Optional[List[str]] = None) -> Dict[str, Any]:
        """Collect all metrics into a dictionary for reporting.

        This is a convenience method for serialization (e.g., TaskResult).
        Prefer accessing individual properties directly for programmatic use.

        Args:
            expected_tools: List of MCP tools expected to be used

        Returns:
            Dictionary containing all metrics
        """
        metrics = {
            'success_rate': self.success_rate,
            'tool_call_count': self.tool_call_count,
            'unique_tools_count': self.unique_tools_count,
            'turn_count': self.turn_count,
            'tool_breakdown': self.tool_breakdown,
            'task_duration': self.task_duration,
            'tool_calls_detail': self.tool_calls,
            'file_operation_count': self.file_operation_count,
            'file_read_count': self.file_read_count,
            'file_write_count': self.file_write_count,
        }

        if expected_tools:
            metrics.update(self._compare_expected_tools(expected_tools))

        return metrics
