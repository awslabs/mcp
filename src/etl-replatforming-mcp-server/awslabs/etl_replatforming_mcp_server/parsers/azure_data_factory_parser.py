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

import json
import re
from typing import Any, Dict, List, Optional

from ..models.exceptions import ParsingError
from ..models.flex_workflow import (
    ErrorHandling,
    FlexWorkflow,
    ParsingInfo,
    Schedule,
    Task,
    TaskDependency,
    TaskGroup,
    TaskLoop,
    TriggerConfig,
)
from .base_parser import WorkflowParser


class AzureDataFactoryParser(WorkflowParser):
    """Parser to convert Azure Data Factory pipelines to FLEX format"""

    def parse_code(self, input_code: str) -> FlexWorkflow:
        """Parse raw ADF JSON code to FLEX workflow"""
        try:
            adf_data = json.loads(input_code)
            return self._parse_adf_pipeline(adf_data)
        except json.JSONDecodeError as e:
            raise ParsingError(f'Invalid JSON format: {str(e)}', {'input_code': input_code}) from e

    def _parse_adf_pipeline(self, pipeline_data: Dict[str, Any]) -> FlexWorkflow:
        """Parse ADF pipeline to FLEX format"""
        properties = pipeline_data.get('properties', pipeline_data)

        # Extract basic pipeline info
        name = pipeline_data.get('name', 'adf_pipeline')
        description = properties.get('description', 'Converted from Azure Data Factory pipeline')

        # Parse activities (tasks)
        activities = properties.get('activities', [])
        tasks = self._parse_activities(activities)

        # Parse dependencies
        self._parse_dependencies(activities)

        # Parse parameters and variables
        parameters = properties.get('parameters', {})
        variables = properties.get('variables', {})

        # Extract enhanced orchestration features
        task_groups = self._extract_task_groups(activities)
        connections = self._extract_connections(activities)

        return FlexWorkflow(
            name=name,
            description=description,
            tasks=tasks,
            task_groups=task_groups,
            connections=connections,
            variables=variables,
            metadata={
                'source_framework': 'azure_data_factory',
                'parameters': parameters,
                'variables': variables,
                'original_pipeline': pipeline_data,
            },
            parsing_info=ParsingInfo(
                source_framework='azure_data_factory',
                parsing_completeness=1.0,
                parsing_method='deterministic',
            ),
        )

    def _parse_activities(self, activities: List[Dict[str, Any]]) -> List[Task]:
        """Parse ADF activities to FLEX tasks"""
        tasks = []

        for activity in activities:
            task = self._parse_activity(activity)
            if task:
                tasks.append(task)

        return tasks

    def _parse_activity(self, activity: Dict[str, Any]) -> Task:
        """Parse single ADF activity to FLEX task"""
        activity_name = activity.get('name', 'unknown_activity')
        activity_type = activity.get('type', 'Unknown')

        # Map ADF activity type to FLEX task type
        task_type = self._map_activity_type(activity_type)

        # Extract command/script based on activity type
        command = self._extract_command(activity, activity_type)

        # Extract parameters
        parameters = self._extract_activity_parameters(activity)

        # Extract retry policy
        retry_policy = activity.get('policy', {}).get('retry', 0)
        timeout = activity.get('policy', {}).get('timeout')

        # Extract enhanced task features
        connection_id = self._extract_connection_id(activity)
        batch_size = self._extract_batch_size(activity)

        return Task(
            id=activity_name,
            name=activity.get('description', activity_name),
            type=task_type,
            command=command,
            parameters=parameters,
            timeout=self._parse_timeout(timeout),
            retries=retry_policy,
            connection_id=connection_id,
            batch_size=batch_size,
        )

    def _map_activity_type(self, activity_type: str) -> str:
        """Map ADF activity type to FLEX task type"""
        type_mapping = {
            'Copy': 'copy',  # Data copy operations
            'SqlServerStoredProcedure': 'sql',
            'AzureSqlDatabaseStoredProcedure': 'sql',
            'Lookup': 'sql',
            'Script': 'sql',
            'DataFlow': 'sql',
            'ExecutePipeline': 'pipeline',  # Sub-pipeline execution
            'AzureFunctionActivity': 'python',
            'AzureMLBatchExecution': 'python',
            'DatabricksNotebook': 'notebook',
            'DatabricksSparkJar': 'python',
            'DatabricksSparkPython': 'python',
            'HDInsightHive': 'sql',
            'HDInsightPig': 'sql',
            'HDInsightSpark': 'python',
            'WebActivity': 'http',
            'RestActivity': 'http',
            'Custom': 'bash',
            'ExecuteSSISPackage': 'sql',
        }

        return type_mapping.get(activity_type, 'python')

    def _extract_command(self, activity: Dict[str, Any], activity_type: str) -> str:
        """Extract command/script from ADF activity"""
        type_inputs = activity.get('typeProperties', {})

        if activity_type == 'Copy':
            source = type_inputs.get('source', {})
            sink = type_inputs.get('sink', {})
            return f'# Copy from {source.get("type", "unknown")} to {sink.get("type", "unknown")}'

        elif activity_type in [
            'SqlServerStoredProcedure',
            'AzureSqlDatabaseStoredProcedure',
        ]:
            stored_proc = type_inputs.get('storedProcedureName', '')
            return f'EXEC {stored_proc}'

        elif activity_type == 'Lookup':
            query = type_inputs.get('source', {}).get('query', '')
            return query or 'SELECT * FROM lookup_table'

        elif activity_type == 'Script':
            scripts = type_inputs.get('scripts', [])
            if scripts:
                return scripts[0].get('text', '')

        elif activity_type == 'WebActivity':
            url = type_inputs.get('url', '')
            method = type_inputs.get('method', 'GET')
            return f'{method} {url}'

        elif activity_type == 'DatabricksNotebook':
            notebook_path = type_inputs.get('notebookPath', '')
            return f'# Databricks notebook: {notebook_path}'

        elif activity_type == 'ExecutePipeline':
            pipeline_name = type_inputs.get('pipeline', {}).get('referenceName', '')
            return f'# Execute pipeline: {pipeline_name}'

        return f'# {activity_type} activity'

    def _extract_activity_parameters(self, activity: Dict[str, Any]) -> Dict[str, Any]:
        """Extract parameters from ADF activity"""
        parameters = {}
        type_props = activity.get('typeProperties', {})

        # Add common parameters
        if 'linkedServiceName' in activity:
            parameters['linked_service'] = activity['linkedServiceName'].get('referenceName', '')

        if 'dataset' in type_props:
            parameters['dataset'] = type_props['dataset'].get('referenceName', '')

        # Add type-specific parameters
        parameters.update(type_props)

        return parameters

    def _parse_timeout(self, timeout_str: str) -> Optional[int]:
        """Parse ADF timeout string to seconds"""
        if not timeout_str:
            return None

        # ADF timeout format: "7.00:00:00" (days.hours:minutes:seconds)
        try:
            if '.' in timeout_str:
                days_part, time_part = timeout_str.split('.', 1)
                days = int(days_part)
            else:
                days = 0
                time_part = timeout_str

            time_parts = time_part.split(':')
            hours = int(time_parts[0]) if len(time_parts) > 0 else 0
            minutes = int(time_parts[1]) if len(time_parts) > 1 else 0
            seconds = int(time_parts[2]) if len(time_parts) > 2 else 0

            return days * 86400 + hours * 3600 + minutes * 60 + seconds
        except (ValueError, IndexError):
            return 3600  # Default 1 hour

    def _parse_dependencies(self, activities: List[Dict[str, Any]]) -> List[TaskDependency]:
        """Parse ADF activity dependencies"""
        dependencies = []

        for activity in activities:
            depends_on = activity.get('dependsOn', [])

            for dependency in depends_on:
                upstream_activity = dependency.get('activity')
                dependency_conditions = dependency.get('dependencyConditions', ['Succeeded'])

                # Map ADF conditions to FLEX conditions
                for condition in dependency_conditions:
                    flex_condition = self._map_dependency_condition(condition)
                    dependencies.append(
                        TaskDependency(task_id=upstream_activity, condition=flex_condition)
                    )

        return dependencies

    def _map_dependency_condition(self, adf_condition: str) -> str:
        """Map ADF dependency condition to FLEX condition"""
        condition_mapping = {
            'Succeeded': 'success',
            'Failed': 'failure',
            'Skipped': 'always',
            'Completed': 'always',
        }

        return condition_mapping.get(adf_condition, 'success')

    def _convert_adf_expression(self, adf_expression: str) -> str:
        """Convert ADF expression to FLEX condition format"""
        # Convert common ADF patterns to FLEX
        # @activity('TaskName').output.count > 100
        # becomes: output.count > 100

        # Remove ADF function wrappers
        condition = adf_expression
        condition = re.sub(r"@activity\('[^']+'\.output\.", 'output.', condition)
        condition = re.sub(r"@variables\('[^']+'", 'variables.', condition)
        condition = re.sub(r"@parameters\('[^']+'", 'parameters.', condition)

        return condition

    # Standardized required methods from base class
    def detect_framework(self, input_code: str) -> bool:
        """Detect if input code is Azure Data Factory JSON"""
        try:
            data = json.loads(input_code)
            return 'properties' in data and 'activities' in data.get('properties', {})
        except (json.JSONDecodeError, TypeError):
            return False

    def validate_input(self, input_code: str) -> bool:
        """Validate Azure Data Factory JSON format"""
        try:
            data = json.loads(input_code)
            return isinstance(data, dict) and ('properties' in data or 'activities' in data)
        except (json.JSONDecodeError, TypeError):
            return False

    def parse_metadata(self, source_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract workflow metadata"""
        properties = source_data.get('properties', source_data)
        return {
            'name': source_data.get('name', 'adf_pipeline'),
            'description': properties.get(
                'description', 'Converted from Azure Data Factory pipeline'
            ),
            'parameters': properties.get('parameters', {}),
            'variables': properties.get('variables', {}),
        }

    def parse_tasks(self, source_data: Dict[str, Any]) -> List[Task]:
        """Extract tasks from activities"""
        properties = source_data.get('properties', source_data)
        activities = properties.get('activities', [])
        return self._parse_activities(activities)

    def parse_schedule(self, source_data: Dict[str, Any]) -> Optional[Schedule]:
        """Extract schedule - ADF uses triggers, not in pipeline definition"""
        return None

    def parse_error_handling(self, source_data: Dict[str, Any]) -> Optional[ErrorHandling]:
        """Extract error handling from activity policies"""
        return None  # Would need to analyze policy blocks across activities

    def parse_dependencies(self, source_data: Dict[str, Any]) -> List[TaskDependency]:
        """Extract dependencies from dependsOn"""
        properties = source_data.get('properties', source_data)
        activities = properties.get('activities', [])
        return self._parse_dependencies(activities)

    def parse_loops(self, source_data: Dict[str, Any]) -> Dict[str, TaskLoop]:
        """Extract loops from ForEach activities"""
        return {}  # Would need to analyze ForEach activities

    def parse_conditional_logic(self, source_data: Dict[str, Any]) -> List[Task]:
        """Extract If/Switch activities"""
        return []  # Would need to filter conditional activities

    def parse_parallel_execution(self, source_data: Dict[str, Any]) -> List[Task]:
        """Extract parallel execution patterns"""
        return []  # Would need to analyze dependency patterns

    def get_parsing_completeness(self, flex_workflow: FlexWorkflow) -> float:
        """Calculate ADF parsing completeness"""
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
        """Extract task groups from ADF activities"""
        properties = source_data.get('properties', source_data)
        activities = properties.get('activities', [])
        return self._extract_task_groups(activities)

    def parse_connections(self, source_data: Dict[str, Any]) -> Dict[str, str]:
        """Extract connection references from ADF activities"""
        properties = source_data.get('properties', source_data)
        activities = properties.get('activities', [])
        return self._extract_connections(activities)

    def parse_trigger_rules(self, source_data: Dict[str, Any]) -> Dict[str, str]:
        """Extract trigger rules from ADF dependencies"""
        return {}  # ADF uses dependencyConditions, handled in dependencies

    def parse_data_triggers(self, source_data: Dict[str, Any]) -> List[TriggerConfig]:
        """Extract data triggers - ADF uses external triggers"""
        return []  # ADF triggers are external to pipeline definition

    # Helper methods for enhanced features
    def _extract_task_groups(self, activities: List[Dict[str, Any]]) -> List[TaskGroup]:
        """Extract logical groupings from ForEach activities"""
        task_groups = []

        for activity in activities:
            if activity.get('type') == 'ForEach':
                group_id = f'{activity.get("name", "foreach")}_group'
                task_groups.append(
                    TaskGroup(
                        group_id=group_id,
                        tooltip=f'ForEach loop: {activity.get("name")}',
                    )
                )

        return task_groups

    def _extract_connections(self, activities: List[Dict[str, Any]]) -> Dict[str, str]:
        """Extract connection references from linked services"""
        connections = {}

        for activity in activities:
            connection_id = self._extract_connection_id(activity)
            if connection_id:
                activity_type = activity.get('type', '')
                if 'Sql' in activity_type:
                    connections[connection_id] = 'sql'
                elif 'Copy' in activity_type:
                    connections[connection_id] = 'data_source'
                elif 'Web' in activity_type:
                    connections[connection_id] = 'http'
                else:
                    connections[connection_id] = 'azure_service'

        return connections

    def _extract_connection_id(self, activity: Dict[str, Any]) -> Optional[str]:
        """Extract connection ID from linked service reference"""
        linked_service = activity.get('linkedServiceName')
        if linked_service:
            return linked_service.get('referenceName')

        # Check in typeProperties for dataset references
        type_props = activity.get('typeProperties', {})
        dataset = type_props.get('dataset')
        if dataset:
            return dataset.get('referenceName')

        return None

    def _extract_batch_size(self, activity: Dict[str, Any]) -> Optional[int]:
        """Extract batch size from ForEach activities"""
        if activity.get('type') == 'ForEach':
            type_props = activity.get('typeProperties', {})
            return type_props.get('batchCount')

        return None
