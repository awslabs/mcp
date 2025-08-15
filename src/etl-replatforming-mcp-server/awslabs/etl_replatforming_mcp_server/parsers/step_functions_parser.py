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

"""Step Functions parser for converting to FLEX workflow format."""

import json
from typing import Any, Dict, List, Optional

from ..models.exceptions import ParsingError
from ..models.flex_workflow import (
    ErrorHandling,
    FlexWorkflow,
    LoopItems,
    ParsingInfo,
    Schedule,
    Task,
    TaskDependency,
    TaskGroup,
    TaskLoop,
    TriggerConfig,
)
from .base_parser import WorkflowParser


class StepFunctionsParser(WorkflowParser):
    """Parser to convert Step Functions state machines to FLEX workflow format"""

    def parse_code(self, input_code: str) -> FlexWorkflow:
        """Parse raw Step Functions JSON to FLEX workflow

        Intelligently extracts Step Functions components from raw JSON input.

        Args:
            input_code: Raw Step Functions JSON string

        Returns:
            FlexWorkflow with parsed state machine information
        """
        try:
            # Parse JSON
            state_machine = json.loads(input_code)
            return self._parse_state_machine(state_machine)

        except json.JSONDecodeError as e:
            raise ParsingError(
                f'Invalid JSON format: {str(e)}', {'input_code': input_code[:200]}
            ) from e

    def _parse_state_machine(self, source_data: Dict[str, Any]) -> FlexWorkflow:
        """Parse Step Functions state machine data"""
        name = source_data.get('Comment', 'step_functions_workflow')
        states = source_data.get('States', {})
        # start_at = source_data.get('StartAt')  # Not used

        # First, extract all states including parallel branches
        all_states = self._extract_all_states(states)

        # Convert states to tasks with dependencies
        tasks = []

        for state_name, state_def in all_states.items():
            task = self._convert_state_to_task(state_name, state_def, all_states)
            if task:
                tasks.append(task)

        # Extract enhanced orchestration features
        task_groups = self._extract_task_groups(source_data)
        connections = self._extract_connections(source_data)

        return FlexWorkflow(
            name=name.replace(' ', '_').lower(),
            description=source_data.get('Comment'),
            tasks=tasks,
            task_groups=task_groups,
            connections=connections,
            metadata={'created_from': 'step_functions'},
            parsing_info=ParsingInfo(
                source_framework='step_functions',
                parsing_completeness=1.0,
                parsing_method='deterministic',
            ),
        )

    def _extract_all_states(self, states: Dict[str, Any]) -> Dict[str, Any]:
        """Extract all states including those in parallel branches"""
        all_states = {}

        for state_name, state_def in states.items():
            if state_def.get('Type') == 'Parallel':
                # Add the parallel state itself
                all_states[state_name] = state_def

                # Extract states from each branch
                branches = state_def.get('Branches', [])
                for _i, branch in enumerate(branches):
                    branch_states = branch.get('States', {})
                    for branch_state_name, branch_state_def in branch_states.items():
                        # Use original state name, but ensure uniqueness
                        unique_name = branch_state_name
                        counter = 1
                        while unique_name in all_states:
                            unique_name = f'{branch_state_name}_{counter}'
                            counter += 1
                        all_states[unique_name] = branch_state_def
            else:
                all_states[state_name] = state_def

        return all_states

    def _convert_state_to_task(
        self, state_name: str, state_def: Dict[str, Any], all_states: Dict[str, Any]
    ) -> Task:
        """Convert Step Functions state to generic FLEX task"""
        state_type = state_def.get('Type')

        if state_type == 'Choice':
            # Handle Choice states as branch tasks
            choices = state_def.get('Choices', [])
            branches = []

            for choice in choices:
                next_state = choice.get('Next')
                condition = self._extract_choice_condition(choice)
                if next_state and condition:
                    branches.append({'next_task': next_state, 'condition': condition})

            # Find dependencies
            depends_on = self._find_dependencies(state_name, all_states)

            return Task(
                id=state_name,
                name=state_name.replace('_', ' ').title(),
                type='branch',
                command='evaluate_condition',
                parameters={'branches': branches},
                depends_on=depends_on,
            )

        elif state_type == 'Task':
            resource = state_def.get('Resource', '')
            parameters = state_def.get('Parameters', {})

            # Map AWS resources to generic task types
            if 'redshiftdata:executeStatement' in resource:
                task_type = 'sql'
                command = parameters.get('Sql', '')
            elif 'lambda:invoke' in resource:
                task_type = 'python'
                command = f'invoke_function({parameters.get("FunctionName", "unknown")})'
            elif 'batch:submitJob' in resource:
                task_type = 'container'
                command = f'run_batch_job({parameters.get("JobDefinition", "unknown")})'
            elif 'sns:publish' in resource:
                task_type = 'email'
                command = f"send_notification('{parameters.get('Message', 'notification')}')"
            elif 's3:' in resource:
                task_type = 'file_transfer'
                command = 's3_operation'
            else:
                task_type = 'bash'
                command = 'generic_aws_service_call'

            # Extract retry configuration
            retry_config = state_def.get('Retry', [])
            retries = retry_config[0].get('MaxAttempts', 0) if retry_config else 0
            retry_delay = retry_config[0].get('IntervalSeconds', 300) if retry_config else 300

            # Find dependencies
            depends_on = self._find_dependencies(state_name, all_states)

            # Extract enhanced task features
            connection_id = self._extract_connection_from_resource(resource)
            batch_size = parameters.get('MaxConcurrency') or parameters.get('BatchSize')

            return Task(
                id=state_name,
                name=state_name.replace('_', ' ').title(),
                type=task_type,
                command=command,
                timeout=state_def.get('TimeoutSeconds'),
                retries=retries,
                retry_delay=retry_delay,
                depends_on=depends_on,
                connection_id=connection_id,
                batch_size=batch_size,
            )

        elif state_type == 'Map':
            # Handle Map state by creating a task with loop configuration
            items_path = state_def.get('ItemsPath', '$.items')
            max_concurrency = state_def.get('MaxConcurrency')

            # Determine items source from ItemsPath
            if items_path.startswith('$.static'):
                items = LoopItems(source='static', values=[])
            elif items_path.startswith('$.range'):
                items = LoopItems(source='range', start=0, end=100, step=1)
            else:
                # Task output - extract task reference from path like "$.fileList.files"
                path_parts = items_path.replace('$.', '').split('.')
                if len(path_parts) >= 2:
                    # Assume first part is task output field, rest is path
                    items = LoopItems(
                        source='task_output', path=items_path.replace('$.', 'output.')
                    )
                else:
                    items = LoopItems(source='static', values=[])

            # Create loop configuration
            loop = TaskLoop(
                type='for_each',
                items=items,
                item_variable='item',
                max_concurrency=max_concurrency,
            )

            # Find dependencies
            depends_on = self._find_dependencies(state_name, all_states)

            # For Map states, create a representative task that shows the parallel processing
            return Task(
                id=state_name,
                name=state_name.replace('_', ' ').title(),
                type='for_each',
                command='process_items_in_parallel',
                depends_on=depends_on,
                loop=loop,
            )

        elif state_type == 'Parallel':
            # Handle Parallel state by creating a placeholder task
            # The actual parallel tasks will be extracted from branches
            depends_on = self._find_dependencies(state_name, all_states)

            return Task(
                id=state_name,
                name=state_name.replace('_', ' ').title(),
                type='bash',
                command="echo 'Parallel execution container'",
                depends_on=depends_on,
            )

        elif state_type == 'Pass':
            # Find dependencies for Pass state
            depends_on = self._find_dependencies(state_name, all_states)

            return Task(
                id=state_name,
                name=state_name.replace('_', ' ').title(),
                type='bash',
                command="echo 'Pass state - no operation'",
                depends_on=depends_on,
            )

        # Return a default task if conversion fails
        return Task(
            id=state_name,
            name=state_name.replace('_', ' ').title(),
            type='bash',
            command='echo "Unknown state type"',
            depends_on=[],
        )

    def _find_dependencies(
        self, state_name: str, all_states: Dict[str, Any]
    ) -> list[TaskDependency]:
        """Find dependencies for a state including cyclic dependencies"""
        depends_on = []

        # Find direct dependencies (states that have Next pointing to this state)
        for other_state_name, other_state_def in all_states.items():
            if other_state_def.get('Next') == state_name:
                depends_on.append(TaskDependency(task_id=other_state_name, condition='success'))

            # Check for cyclic dependencies in Choice states
            if other_state_def.get('Type') == 'Choice':
                choices = other_state_def.get('Choices', [])
                for choice in choices:
                    if choice.get('Next') == state_name:
                        # This is a potential cyclic dependency
                        depends_on.append(
                            TaskDependency(task_id=other_state_name, condition='success')
                        )

        return depends_on

    def _extract_choice_condition(self, choice: Dict[str, Any]) -> str:
        """Extract condition from Step Functions Choice rule"""
        # Handle complex And/Or conditions
        if 'And' in choice:
            conditions = choice['And']
            if isinstance(conditions, list) and conditions:
                sub_conditions = []
                for condition in conditions:
                    sub_condition = self._extract_choice_condition(condition)
                    if sub_condition != 'unknown_condition':
                        sub_conditions.append(sub_condition)
                if sub_conditions:
                    return ' AND '.join(sub_conditions)
            return 'complex_and_condition'
        elif 'Or' in choice:
            conditions = choice['Or']
            if isinstance(conditions, list) and conditions:
                sub_conditions = []
                for condition in conditions:
                    sub_condition = self._extract_choice_condition(condition)
                    if sub_condition != 'unknown_condition':
                        sub_conditions.append(sub_condition)
                if sub_conditions:
                    return ' OR '.join(sub_conditions)
            return 'complex_or_condition'
        # Handle simple condition types
        elif 'NumericGreaterThan' in choice:
            variable = choice.get('Variable', '$.unknown')
            value = choice['NumericGreaterThan']
            return f'{variable.replace("$.", "output.")} > {value}'
        elif 'NumericLessThan' in choice:
            variable = choice.get('Variable', '$.unknown')
            value = choice['NumericLessThan']
            return f'{variable.replace("$.", "output.")} < {value}'
        elif 'NumericEquals' in choice:
            variable = choice.get('Variable', '$.unknown')
            value = choice['NumericEquals']
            return f'{variable.replace("$.", "output.")} == {value}'
        elif 'BooleanEquals' in choice:
            variable = choice.get('Variable', '$.unknown')
            value = choice['BooleanEquals']
            return f'{variable.replace("$.", "output.")} == {value}'
        elif 'StringEquals' in choice:
            variable = choice.get('Variable', '$.unknown')
            value = choice['StringEquals']
            return f'{variable.replace("$.", "output.")} == "{value}"'

        return 'unknown_condition'

    # Standardized required methods from base class
    def detect_framework(self, input_code: str) -> bool:
        """Detect if input code is Step Functions JSON"""
        try:
            data = json.loads(input_code)
            return 'States' in data and 'StartAt' in data
        except (json.JSONDecodeError, TypeError):
            return False

    def validate_input(self, input_code: str) -> bool:
        """Validate Step Functions JSON format"""
        try:
            data = json.loads(input_code)
            return isinstance(data, dict) and 'States' in data
        except (json.JSONDecodeError, TypeError):
            return False

    def parse_metadata(self, source_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract workflow metadata"""
        return {
            'name': source_data.get('Comment', 'step_functions_workflow'),
            'description': source_data.get('Comment'),
            'start_at': source_data.get('StartAt'),
        }

    def parse_tasks(self, source_data: Dict[str, Any]) -> List[Task]:
        """Extract tasks from states"""
        states = source_data.get('States', {})
        all_states = self._extract_all_states(states)
        tasks = []
        for state_name, state_def in all_states.items():
            task = self._convert_state_to_task(state_name, state_def, all_states)
            if task:
                tasks.append(task)
        return tasks

    def parse_schedule(self, source_data: Dict[str, Any]) -> Optional[Schedule]:
        """Extract schedule - Step Functions has no built-in scheduling"""
        return None

    def parse_error_handling(self, source_data: Dict[str, Any]) -> Optional[ErrorHandling]:
        """Extract error handling from Catch blocks"""
        return None  # Would need to analyze Catch blocks across states

    def parse_dependencies(self, source_data: Dict[str, Any]) -> List[TaskDependency]:
        """Extract dependencies from Next transitions"""
        deps = []
        states = source_data.get('States', {})
        for state_name, state_def in states.items():
            if 'Next' in state_def:
                deps.append(TaskDependency(task_id=state_name, condition='success'))
        return deps

    def parse_loops(self, source_data: Dict[str, Any]) -> Dict[str, TaskLoop]:
        """Extract loops from Map states"""
        return {}  # Would need to analyze Map states

    def parse_conditional_logic(self, source_data: Dict[str, Any]) -> List[Task]:
        """Extract Choice states"""
        choice_tasks = []
        states = source_data.get('States', {})
        for state_name, state_def in states.items():
            if state_def.get('Type') == 'Choice':
                task = self._convert_state_to_task(state_name, state_def, states)
                if task:
                    choice_tasks.append(task)
        return choice_tasks

    def parse_parallel_execution(self, source_data: Dict[str, Any]) -> List[Task]:
        """Extract Parallel states"""
        parallel_tasks = []
        states = source_data.get('States', {})
        for state_name, state_def in states.items():
            if state_def.get('Type') == 'Parallel':
                task = self._convert_state_to_task(state_name, state_def, states)
                if task:
                    parallel_tasks.append(task)
        return parallel_tasks

    def get_parsing_completeness(self, flex_workflow: FlexWorkflow) -> float:
        """Calculate Step Functions parsing completeness"""
        required_fields = ['name', 'tasks', 'dependencies']
        present_fields = 0
        if flex_workflow.name:
            present_fields += 1
        if flex_workflow.tasks:
            present_fields += 1
        if any(task.depends_on for task in flex_workflow.tasks):
            present_fields += 1
        return present_fields / len(required_fields)

    # New methods for enhanced orchestration features
    def parse_task_groups(self, source_data: Dict[str, Any]) -> List[TaskGroup]:
        """Extract task groups from Step Functions"""
        return self._extract_task_groups(source_data)

    def parse_connections(self, source_data: Dict[str, Any]) -> Dict[str, str]:
        """Extract connection references from Step Functions"""
        return self._extract_connections(source_data)

    def parse_trigger_rules(self, source_data: Dict[str, Any]) -> Dict[str, str]:
        """Extract trigger rules - Step Functions uses Next/End"""
        return {}  # Step Functions doesn't have explicit trigger rules

    def parse_data_triggers(self, source_data: Dict[str, Any]) -> List[TriggerConfig]:
        """Extract data triggers - Step Functions uses external EventBridge"""
        return []  # Step Functions doesn't have built-in data triggers

    # Helper methods for enhanced features
    def _extract_task_groups(self, source_data: Dict[str, Any]) -> List[TaskGroup]:
        """Extract logical groupings from Parallel branches"""
        task_groups = []
        states = source_data.get('States', {})

        for state_name, state_def in states.items():
            if state_def.get('Type') == 'Parallel':
                branches = state_def.get('Branches', [])
                for i, _branch in enumerate(branches):
                    group_id = f'{state_name}_branch_{i}'
                    task_groups.append(
                        TaskGroup(
                            group_id=group_id,
                            tooltip=f'Parallel branch {i} of {state_name}',
                        )
                    )

        return task_groups

    def _extract_connections(self, source_data: Dict[str, Any]) -> Dict[str, str]:
        """Extract connection types from AWS resources"""
        connections = {}
        states = source_data.get('States', {})
        all_states = self._extract_all_states(states)

        for _state_name, state_def in all_states.items():
            if state_def.get('Type') == 'Task':
                resource = state_def.get('Resource', '')
                connection_id = self._extract_connection_from_resource(resource)
                if connection_id:
                    if 'redshift' in resource:
                        connections[connection_id] = 'redshift'
                    elif 'lambda' in resource:
                        connections[connection_id] = 'lambda'
                    elif 'batch' in resource:
                        connections[connection_id] = 'batch'
                    elif 'sns' in resource:
                        connections[connection_id] = 'sns'
                    elif 's3' in resource:
                        connections[connection_id] = 's3'
                    else:
                        connections[connection_id] = 'aws_service'

        return connections

    def _extract_connection_from_resource(self, resource: str) -> Optional[str]:
        """Extract connection identifier from AWS resource ARN"""
        if not resource:
            return None

        # Extract service name from resource ARN
        if 'redshiftdata:executeStatement' in resource:
            return 'redshift_data'
        elif 'lambda:invoke' in resource:
            return 'lambda_service'
        elif 'batch:submitJob' in resource:
            return 'batch_service'
        elif 'sns:publish' in resource:
            return 'sns_service'
        elif 's3:' in resource:
            return 's3_service'

        return None
