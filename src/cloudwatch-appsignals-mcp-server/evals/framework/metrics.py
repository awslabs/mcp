"""Metrics tracking for MCP tool evaluation.

Tracks tool calls, success rates, hit rates, and task duration.
"""

import time
from typing import Any, Dict, List, Optional


class MetricsTracker:
    """Tracks metrics for tool calls and task execution."""

    def __init__(self):
        """Initialize metrics tracker."""
        self.tool_calls: List[Dict[str, Any]] = []
        self.task_start_time: Optional[float] = None
        self.task_end_time: Optional[float] = None

    def start_task(self):
        """Mark task start time."""
        self.task_start_time = time.time()

    def end_task(self):
        """Mark task end time."""
        self.task_end_time = time.time()

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

    def get_metrics(self, expected_tools: Optional[List[str]] = None) -> Dict[str, Any]:
        """Calculate metrics.

        Args:
            expected_tools: List of MCP tools expected to be used
        """
        metrics = {
            'success_rate': (
                sum(1 for c in self.tool_calls if c['success']) / len(self.tool_calls)
                if self.tool_calls
                else 0.0
            ),
            'tool_call_count': len(self.tool_calls),
            'task_duration': (
                self.task_end_time - self.task_start_time
                if self.task_start_time and self.task_end_time
                else 0.0
            ),
            'tool_calls_detail': self.tool_calls,
        }

        file_ops = ['read_file', 'write_file', 'list_files']
        file_op_calls = [c for c in self.tool_calls if c['tool_name'] in file_ops]

        metrics.update(
            {
                'file_operation_count': len(file_op_calls),
                'file_read_count': len(
                    [c for c in file_op_calls if c['tool_name'] == 'read_file']
                ),
                'file_write_count': len(
                    [c for c in file_op_calls if c['tool_name'] == 'write_file']
                ),
            }
        )

        if expected_tools:
            expected_tool_set = set(expected_tools)
            called_tool_names = {c['tool_name'] for c in self.tool_calls}
            called_expected = called_tool_names & expected_tool_set
            missing = expected_tool_set - called_tool_names
            unexpected = called_tool_names - expected_tool_set

            metrics.update(
                {
                    'hit_rate': len(called_expected) / len(expected_tool_set)
                    if expected_tool_set
                    else 0.0,
                    'expected_tools_called': sorted(called_expected),
                    'missing_expected_tools': sorted(missing),
                    'unexpected_tools_called': sorted(unexpected),
                }
            )

        return metrics
