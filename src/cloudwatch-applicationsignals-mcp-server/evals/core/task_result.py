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

"""Result types for task execution."""

from .validator import ValidationResult
from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class TaskResult:
    """Result from running a single evaluation task.

    Attributes:
        task_id: ID of the task that was evaluated
        success: Whether the task passed all validation criteria
        prompt: The prompt that was executed
        validation_results: List of validation results from validators
        metrics: Dictionary of metrics (duration, turns, tool calls, etc.)
        captured_data: Data captured by captors during execution
        error: Error message if the task failed to execute (None if successful)
    """

    task_id: str
    success: bool
    prompt: Optional[str] = None
    validation_results: Optional[List[ValidationResult]] = None
    metrics: Optional[Dict[str, Any]] = None
    captured_data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

    @classmethod
    def from_execution(
        cls,
        task_id: str,
        prompt: str,
        success: bool,
        validation_results: List[ValidationResult],
        metrics: Dict[str, Any],
        captured_data: Dict[str, Any],
    ) -> 'TaskResult':
        """Create result from completed task execution.

        Use this for tasks that executed successfully (no exceptions), regardless of
        whether validation passed or failed. Use from_error() for execution failures.

        Args:
            task_id: ID of the task
            prompt: The prompt that was executed
            success: Whether all validations passed
            validation_results: List of validation results
            metrics: Metrics dictionary
            captured_data: Captured data dictionary

        Returns:
            TaskResult instance
        """
        return cls(
            task_id=task_id,
            success=success,
            prompt=prompt,
            validation_results=validation_results,
            metrics=metrics,
            captured_data=captured_data,
            error=None,
        )

    @classmethod
    def from_error(cls, task_id: str, error: str) -> 'TaskResult':
        """Create an error result instance.

        Args:
            task_id: ID of the task
            error: Error message

        Returns:
            TaskResult instance with error
        """
        return cls(
            task_id=task_id,
            success=False,
            error=error,
        )

    def get_captured_data_str(self) -> str:
        """Get string representation of captured_data for debug reporting.

        Returns:
            Formatted string representation of all captured data
        """
        import json

        if not self.captured_data:
            return 'No captured data'

        lines = ['Captured Data:', '=' * 40]

        for key, value in self.captured_data.items():
            lines.append(f'\n{key}:')
            lines.append('-' * 40)
            try:
                if isinstance(value, (dict, list)):
                    lines.append(json.dumps(value, indent=2, default=str))
                else:
                    lines.append(str(value))
            except Exception as e:
                lines.append(f'<Error formatting data: {e}>')

        return '\n'.join(lines)

    def __str__(self) -> str:
        """Format result as a human-readable string."""
        lines = [
            '=' * 60,
            f'EVALUATION RESULT: {self.task_id}',
            '=' * 60,
        ]

        if self.error:
            lines.extend(
                [
                    'Status: ❌ ERROR',
                    f'Error: {self.error}',
                    '=' * 60,
                ]
            )
            return '\n'.join(lines)

        if self.metrics:
            lines.extend(
                [
                    f'Duration: {self.metrics.get("task_duration", 0):.2f}s',
                    f'Turns: {self.metrics.get("turn_count", 0)}',
                    f'Tool Calls: {self.metrics.get("tool_call_count", 0)} '
                    f'({self.metrics.get("unique_tools_count", 0)} unique)',
                    f'Hit Rate: {self.metrics.get("hit_rate", 0):.1%}',
                    f'Success Rate: {self.metrics.get("success_rate", 0):.1%}',
                    f'File Operations: {self.metrics.get("file_operation_count", 0)}',
                ]
            )

            if self.metrics.get('tool_breakdown'):
                lines.extend(['', 'Tool Breakdown:'])
                for tool_name, stats in sorted(self.metrics['tool_breakdown'].items()):
                    lines.append(
                        f'  - {tool_name}: {stats["count"]} calls '
                        f'({stats["success"]} success, {stats["failed"]} failed)'
                    )

        if self.validation_results:
            lines.extend(['', 'Validation Results:'])
            for validation_result in self.validation_results:
                validator_name = validation_result.get('validator_name', 'Unknown')
                if validation_result.get('error'):
                    lines.extend(
                        [
                            f'  {validator_name}: ❌ ERROR',
                            f'    {validation_result.get("error", "")}',
                        ]
                    )
                else:
                    criteria_results = validation_result.get('criteria_results', [])
                    passed = sum(1 for r in criteria_results if r['status'] == 'PASS')
                    total = len(criteria_results)
                    status = (
                        '✅ PASS' if validation_result.get('overall_pass', False) else '❌ FAIL'
                    )
                    lines.append(f'  {validator_name}: {status} ({passed}/{total} criteria met)')

                    for criterion_result in criteria_results:
                        status_text = criterion_result['status']
                        lines.append(f'    [{status_text}] {criterion_result["criterion"]}')
                        if criterion_result.get('reasoning'):
                            lines.append(f'      Reasoning: {criterion_result["reasoning"]}')

        status = '✅ PASS' if self.success else '❌ FAIL'
        lines.extend(
            [
                '',
                f'Overall Task Status: {status}',
                '=' * 60,
            ]
        )

        return '\n'.join(lines)
