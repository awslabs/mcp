#!/usr/bin/env python3

import json
from typing import Dict, Any, List
from ..models.flex_workflow import FlexWorkflow, Task, Schedule, TaskDependency
from ..models.exceptions import ParsingError
from .base_parser import WorkflowParser


class AzureDataFactoryParser(WorkflowParser):
    """Parser to convert Azure Data Factory pipelines to FLEX format"""
    
    @property
    def framework_name(self) -> str:
        return "azure_data_factory"
    
    def can_parse(self, source_data: Dict[str, Any]) -> bool:
        """Check if source data is valid ADF format"""
        return ('pipeline' in source_data or 'properties' in source_data) and \
               ('activities' in source_data.get('properties', {}) or 
                'activities' in source_data.get('pipeline', {}))
    
    def parse(self, source_data: Dict[str, Any]) -> FlexWorkflow:
        """Parse ADF source data to FLEX workflow"""
        if not self.can_parse(source_data):
            raise ParsingError("Invalid Azure Data Factory source data format", {"source_data": source_data})
        
        # Handle both direct pipeline format and wrapped format
        pipeline_data = source_data.get('pipeline', source_data)
        return self._parse_adf_pipeline(pipeline_data)
    
    def parse_code(self, input_code: str) -> FlexWorkflow:
        """Parse raw ADF JSON code to FLEX workflow"""
        try:
            adf_data = json.loads(input_code)
            return self.parse(adf_data)
        except json.JSONDecodeError as e:
            raise ParsingError(f"Invalid JSON format: {str(e)}", {"input_code": input_code})
    
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
        dependencies = self._parse_dependencies(activities)
        
        # Parse parameters and variables
        parameters = properties.get('parameters', {})
        variables = properties.get('variables', {})
        
        return FlexWorkflow(
            name=name,
            description=description,
            tasks=tasks,
            metadata={
                "source_framework": "azure_data_factory",
                "parameters": parameters,
                "variables": variables,
                "original_pipeline": pipeline_data
            }
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
        
        return Task(
            id=activity_name,
            name=activity.get('description', activity_name),
            type=task_type,
            command=command,
            parameters=parameters,
            timeout=self._parse_timeout(timeout),
            retries=retry_policy
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
            'ExecuteSSISPackage': 'sql'
        }
        
        return type_mapping.get(activity_type, 'python')
    
    def _extract_command(self, activity: Dict[str, Any], activity_type: str) -> str:
        """Extract command/script from ADF activity"""
        type_inputs = activity.get('typeProperties', {})
        
        if activity_type == 'Copy':
            source = type_inputs.get('source', {})
            sink = type_inputs.get('sink', {})
            return f"# Copy from {source.get('type', 'unknown')} to {sink.get('type', 'unknown')}"
        
        elif activity_type in ['SqlServerStoredProcedure', 'AzureSqlDatabaseStoredProcedure']:
            stored_proc = type_inputs.get('storedProcedureName', '')
            return f"EXEC {stored_proc}"
        
        elif activity_type == 'Lookup':
            query = type_inputs.get('source', {}).get('query', '')
            return query or "SELECT * FROM lookup_table"
        
        elif activity_type == 'Script':
            scripts = type_inputs.get('scripts', [])
            if scripts:
                return scripts[0].get('text', '')
        
        elif activity_type == 'WebActivity':
            url = type_inputs.get('url', '')
            method = type_inputs.get('method', 'GET')
            return f"{method} {url}"
        
        elif activity_type == 'DatabricksNotebook':
            notebook_path = type_inputs.get('notebookPath', '')
            return f"# Databricks notebook: {notebook_path}"
        
        elif activity_type == 'ExecutePipeline':
            pipeline_name = type_inputs.get('pipeline', {}).get('referenceName', '')
            return f"# Execute pipeline: {pipeline_name}"
        
        return f"# {activity_type} activity"
    
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
    
    def _parse_timeout(self, timeout_str: str) -> int:
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
            activity_name = activity.get('name')
            depends_on = activity.get('dependsOn', [])
            
            for dependency in depends_on:
                upstream_activity = dependency.get('activity')
                dependency_conditions = dependency.get('dependencyConditions', ['Succeeded'])
                
                # Map ADF conditions to FLEX conditions
                for condition in dependency_conditions:
                    flex_condition = self._map_dependency_condition(condition)
                    dependencies.append(TaskDependency(
                        task_id=upstream_activity,
                        condition=flex_condition
                    ))
        
        return dependencies
    
    def _map_dependency_condition(self, adf_condition: str) -> str:
        """Map ADF dependency condition to FLEX condition"""
        condition_mapping = {
            'Succeeded': 'success',
            'Failed': 'failure',
            'Skipped': 'always',
            'Completed': 'always'
        }
        
        return condition_mapping.get(adf_condition, 'success')