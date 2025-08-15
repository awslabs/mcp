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

import re
from typing import Any, Dict, List

from ..models.flex_workflow import FlexWorkflow


class WorkflowValidator:
    """Validator to check workflow completeness and prompt for missing information"""

    def validate(self, workflow: FlexWorkflow) -> Dict[str, Any]:
        """Validate workflow completeness and generate user prompts

        Args:
            workflow: FLEX workflow to validate

        Returns:
            Validation result with missing fields and user prompts
        """
        missing_fields = workflow.get_missing_fields()
        dependency_errors = self.validate_dependencies(workflow)
        task_type_errors = self.validate_task_types(workflow)
        self.validate_schedule_type(workflow)
        condition_errors = self.validate_dependency_conditions(workflow)
        self.validate_error_handling(workflow)

        command_errors = self.validate_task_commands(workflow)
        timeout_errors = self.validate_task_timeouts(workflow)
        retry_errors = self.validate_task_retries(workflow)

        # all_errors = (
        #     missing_fields
        #     + dependency_errors
        #     + task_type_errors
        #     + schedule_errors
        #     + condition_errors
        #     + error_handling_errors
        #     + command_errors
        #     + timeout_errors
        #     + retry_errors
        # )  # Unused variable

        # Only required field errors make workflow incomplete
        required_missing = workflow.get_missing_fields()

        return {
            'is_complete': len(required_missing) == 0
            and len(
                dependency_errors
                + task_type_errors
                + condition_errors
                + command_errors
                + timeout_errors
                + retry_errors
            )
            == 0,
            'missing_fields': missing_fields,
            'dependency_errors': dependency_errors,
            'completion_percentage': self._calculate_completion_percentage(
                workflow, required_missing
            ),
        }

    def _calculate_completion_percentage(
        self, workflow: FlexWorkflow, missing_fields: List[str]
    ) -> float:
        """Calculate workflow completion percentage

        Args:
            workflow: FLEX workflow
            missing_fields: List of missing fields

        Returns:
            Completion percentage (0.0 to 1.0)
        """
        # Only count required fields for completion percentage
        total_fields = ['workflow_name', 'tasks']

        # Add task-specific fields
        for task in workflow.tasks:
            total_fields.append(f'task_{task.id}_execution_details')
            if task.type == 'sql':
                total_fields.append(f'task_{task.id}_sql_query')

        # Add dependency fields
        for task in workflow.tasks:
            for dep in task.depends_on:
                total_fields.append(f'dependency_{dep.task_id}_{task.id}')

        if not total_fields:
            return 1.0

        completed_fields = len(total_fields) - len(missing_fields)
        return max(0.0, completed_fields / len(total_fields))

    def validate_dependencies(self, workflow: FlexWorkflow) -> List[str]:
        """Validate dependency graph for cycles and missing tasks"""
        errors = []
        task_ids = {task.id for task in workflow.tasks}

        # Check for missing tasks in task dependencies - only report as error if task_id is empty or "?"
        for task in workflow.tasks:
            for dep in task.depends_on:
                if not dep.task_id or dep.task_id.strip() == '?':
                    errors.append(f'dependency_missing_task_id_{task.id}')
                # Note: We don't report missing task references as errors since they can be auto-generated
                # The target framework generators should handle missing references gracefully

        # Simple cycle detection - only for existing tasks
        visited = set()
        rec_stack = set()

        def has_cycle(task_id: str) -> bool:
            if task_id not in task_ids:  # Skip non-existent tasks
                return False
            if task_id in rec_stack:
                return True
            if task_id in visited:
                return False

            visited.add(task_id)
            rec_stack.add(task_id)

            # Find tasks that depend on this task
            for task in workflow.tasks:
                for dep in task.depends_on:
                    if dep.task_id == task_id:
                        if has_cycle(task.id):
                            return True

            rec_stack.remove(task_id)
            return False

        for task in workflow.tasks:
            if has_cycle(task.id):
                errors.append(f'dependency_cycle_detected_{task.id}')
                break

        return errors

    def validate_task_commands(self, workflow: FlexWorkflow) -> List[str]:
        """Validate task commands are appropriate for task types"""
        errors = []

        for task in workflow.tasks:
            # Branch tasks don't need commands since they're just routing logic
            if task.type == 'branch':
                continue

            if task.command and task.command.strip() == '?':
                errors.append(f'task_{task.id}_placeholder_command')
            elif task.type == 'sql' and task.command:
                # Basic SQL validation - should contain SELECT, INSERT, UPDATE, DELETE, CREATE, etc.
                sql_keywords = [
                    'SELECT',
                    'INSERT',
                    'UPDATE',
                    'DELETE',
                    'CREATE',
                    'DROP',
                    'ALTER',
                    'CALL',
                ]
                if not any(keyword in task.command.upper() for keyword in sql_keywords):
                    errors.append(f'task_{task.id}_invalid_sql_command')

        return errors

    def validate_task_timeouts(self, workflow: FlexWorkflow) -> List[str]:
        """Validate task timeout values are reasonable"""
        errors = []

        for task in workflow.tasks:
            if task.timeout is not None:
                if task.timeout <= 0 or task.timeout > 86400:  # Max 24 hours
                    errors.append(f'task_{task.id}_invalid_timeout')

        return errors

    def validate_task_retries(self, workflow: FlexWorkflow) -> List[str]:
        """Validate retry configuration"""
        errors = []

        for task in workflow.tasks:
            if task.retries < 0 or task.retries > 10:  # Max 10 retries
                errors.append(f'task_{task.id}_invalid_retries')
            if task.retry_delay < 0 or task.retry_delay > 3600:  # Max 1 hour delay
                errors.append(f'task_{task.id}_invalid_retry_delay')

        return errors

    def validate_task_types(self, workflow: FlexWorkflow) -> List[str]:
        """Validate task types are supported"""
        errors = []
        # Task types are now free-form strings, so no validation needed
        return errors

    def validate_schedule_type(self, workflow: FlexWorkflow) -> List[str]:
        """Validate schedule type and expression compatibility"""
        errors = []

        if workflow.schedule:
            # Validate expression format based on type
            if workflow.schedule.type == 'cron' and workflow.schedule.expression:
                if not self.validate_cron_expression(workflow.schedule.expression):
                    errors.append('schedule_invalid_cron_expression')
            elif workflow.schedule.type == 'rate' and workflow.schedule.expression:
                if not self.validate_rate_expression(workflow.schedule.expression):
                    errors.append('schedule_invalid_rate_expression')

        return errors

    def validate_dependency_conditions(self, workflow: FlexWorkflow) -> List[str]:
        """Validate dependency conditions are valid"""
        errors = []
        valid_status_conditions = {'success', 'failure', 'always', None}

        for task in workflow.tasks:
            for dep in task.depends_on:
                if dep.condition_type == 'status':
                    if dep.condition not in valid_status_conditions:
                        errors.append(f'dependency_invalid_status_condition_{dep.condition}')
                elif dep.condition_type == 'expression':
                    # Basic expression validation - check for common operators
                    if not any(
                        op in dep.condition
                        for op in ['>', '<', '==', '!=', '>=', '<=', 'AND', 'OR']
                    ):
                        errors.append(f'dependency_invalid_expression_{dep.condition}')
                else:
                    errors.append(f'dependency_invalid_condition_type_{dep.condition_type}')

        return errors

    def validate_error_handling(self, workflow: FlexWorkflow) -> List[str]:
        """Validate error handling configuration"""
        errors = []

        if workflow.error_handling:
            valid_failure_actions = {'fail', 'continue', 'retry'}
            if workflow.error_handling.on_failure not in valid_failure_actions:
                errors.append('error_handling_invalid_on_failure')

            # Validate email format
            import re

            email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            for email in workflow.error_handling.notification_emails:
                if not re.match(email_pattern, email):
                    errors.append(f'error_handling_invalid_email_{email}')

        return errors

    def validate_rate_expression(self, rate_expr: str) -> bool:
        """Validate rate expression format (e.g., 'rate(1 day)', 'rate(30 minutes)')"""
        if not rate_expr or rate_expr.strip() == '?':
            return False

        import re

        # Match rate(number unit) format
        pattern = r'^rate\(\s*(\d+)\s+(minute|minutes|hour|hours|day|days)\s*\)$'
        return bool(re.match(pattern, rate_expr.strip(), re.IGNORECASE))

    def validate_cron_expression(self, cron_expr: str) -> bool:
        """Validate cron expression format"""
        if not cron_expr or cron_expr.strip() == '?':
            return False

        # Basic cron validation: 5 fields (minute hour day month weekday)
        parts = cron_expr.strip().split()
        if len(parts) != 5:
            return False

        # Check each field format
        patterns = [
            r'^(\*|[0-5]?\d|\*/\d+|\d+-\d+|\d+(,\d+)*)$',  # minute (0-59)
            r'^(\*|[01]?\d|2[0-3]|\*/\d+|\d+-\d+|\d+(,\d+)*)$',  # hour (0-23)
            r'^(\*|[12]?\d|3[01]|\*/\d+|\d+-\d+|\d+(,\d+)*)$',  # day (1-31)
            r'^(\*|[1-9]|1[0-2]|\*/\d+|\d+-\d+|\d+(,\d+)*)$',  # month (1-12)
            r'^(\*|[0-6]|\*/\d+|\d+-\d+|\d+(,\d+)*)$',  # weekday (0-6)
        ]

        for i, part in enumerate(parts):
            if not re.match(patterns[i], part):
                return False

        return True
