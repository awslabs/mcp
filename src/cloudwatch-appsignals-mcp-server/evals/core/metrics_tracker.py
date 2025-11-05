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
from typing import Any, Dict, List, Optional


class MetricsTracker:
    """Tracks metrics for tool calls and task execution."""

    def __init__(self):
        """Initialize metrics tracker."""
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

    def get_metrics(self, expected_tools: Optional[List[str]] = None) -> Dict[str, Any]:
        """Calculate metrics.

        Args:
            expected_tools: List of MCP tools expected to be used
        """
        tool_breakdown = {}
        unique_tools = set()
        for call in self.tool_calls:
            tool_name = call['tool_name']
            unique_tools.add(tool_name)
            if tool_name not in tool_breakdown:
                tool_breakdown[tool_name] = {'count': 0, 'success': 0, 'failed': 0}
            tool_breakdown[tool_name]['count'] += 1
            if call['success']:
                tool_breakdown[tool_name]['success'] += 1
            else:
                tool_breakdown[tool_name]['failed'] += 1

        metrics = {
            'success_rate': (
                sum(1 for c in self.tool_calls if c['success']) / len(self.tool_calls)
                if self.tool_calls
                else 0.0
            ),
            'tool_call_count': len(self.tool_calls),
            'unique_tools_count': len(unique_tools),
            'turn_count': self.turn_count,
            'tool_breakdown': tool_breakdown,
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
