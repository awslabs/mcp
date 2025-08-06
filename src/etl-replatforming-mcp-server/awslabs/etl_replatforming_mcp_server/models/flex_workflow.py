#!/usr/bin/env python3

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from enum import Enum
import json



@dataclass
class Schedule:
    """Generic schedule representation"""
    type: str  # Free-form string
    expression: str  # cron expression or rate expression
    timezone: Optional[str] = "UTC"
    start_date: Optional[str] = None
    end_date: Optional[str] = None


@dataclass
class DataSource:
    """Data source/sink configuration"""
    type: str  # e.g., "sql_server", "blob_storage", "s3", "redshift"
    connection_string: Optional[str] = None
    dataset: Optional[str] = None
    table: Optional[str] = None
    query: Optional[str] = None
    parameters: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TaskDependency:
    """Task dependency representation"""
    task_id: str
    condition: str = "success"  # success, failure, always


@dataclass
class Task:
    """Generic task representation"""
    id: str
    name: str
    type: str  # Free-form string, not restricted to enum
    command: Optional[str] = None
    script: Optional[str] = None
    parameters: Dict[str, Any] = field(default_factory=dict)
    timeout: Optional[int] = None
    retries: int = 0
    retry_delay: int = 300
    depends_on: List['TaskDependency'] = field(default_factory=list)
    # Enhanced attributes for better framework support
    source: Optional[DataSource] = None  # For copy/data movement tasks
    sink: Optional[DataSource] = None    # For copy/data movement tasks
    linked_service: Optional[str] = None  # ADF linked services
    compute_target: Optional[str] = None  # Execution environment
    resource_requirements: Dict[str, Any] = field(default_factory=dict)  # CPU, memory, etc.
    
    def __post_init__(self):
        """Auto-generate ID if not provided"""
        if not self.id:
            # Generate ID from name, sanitized
            self.id = self.name.lower().replace(' ', '_').replace('-', '_')
            # Remove special characters
            import re
            self.id = re.sub(r'[^a-zA-Z0-9_]', '', self.id)





@dataclass
class ErrorHandling:
    """Error handling configuration"""
    on_failure: str = "fail"  # fail, continue, retry
    notification_emails: List[str] = field(default_factory=list)
    max_retries: int = 0
    retry_delay: int = 300
    # Enhanced error handling
    notification_webhooks: List[str] = field(default_factory=list)
    escalation_policy: Optional[str] = None
    custom_error_handlers: Dict[str, str] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'on_failure': self.on_failure,
            'notification_emails': self.notification_emails,
            'max_retries': self.max_retries,
            'retry_delay': self.retry_delay,
            'notification_webhooks': self.notification_webhooks,
            'escalation_policy': self.escalation_policy,
            'custom_error_handlers': self.custom_error_handlers
        }


@dataclass
class FlexWorkflow:
    """FLEX workflow representation for conversion between frameworks"""
    name: str
    description: Optional[str] = None
    schedule: Optional[Schedule] = None
    tasks: List[Task] = field(default_factory=list)

    error_handling: Optional[ErrorHandling] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    # Enhanced workflow attributes
    parameters: Dict[str, Any] = field(default_factory=dict)  # Workflow parameters
    variables: Dict[str, Any] = field(default_factory=dict)   # Workflow variables
    triggers: List[Dict[str, Any]] = field(default_factory=list)  # Event triggers
    concurrency: Optional[int] = None  # Max concurrent executions
    tags: List[str] = field(default_factory=list)  # Workflow tags/labels
    
    def get_missing_fields(self) -> List[str]:
        """Return list of missing REQUIRED fields only"""
        missing = []
        
        # Required workflow fields
        if not self.name:
            missing.append("name")
            
        if not self.tasks:
            missing.append("tasks")
            
        # Required schedule fields (if schedule exists)
        if self.schedule:
            if not self.schedule.type:
                missing.append("schedule.type")
            if not self.schedule.expression:
                missing.append("schedule.expression")
                
        # Required task fields
        for i, task in enumerate(self.tasks):
            if not task.name:
                missing.append(f"tasks[{i}].name")
            if not task.type:
                missing.append(f"tasks[{i}].type")
            if not task.command and not task.script:
                missing.append(f"tasks[{i}].command_or_script")
                
        # Validate dependency references (required if depends_on exists)
        task_ids = {task.id for task in self.tasks}
        for i, task in enumerate(self.tasks):
            for j, dep in enumerate(task.depends_on):
                if not dep.task_id:
                    missing.append(f"tasks[{i}].depends_on[{j}].task_id")
                elif dep.task_id not in task_ids:
                    missing.append(f"tasks[{i}].depends_on[{j}].task_id_reference")
                
        return missing
    
    def is_complete(self) -> bool:
        """Check if workflow has all required information for conversion"""
        return len(self.get_missing_fields()) == 0
    
    def get_task_by_id(self, task_id: str) -> Optional[Task]:
        """Get task by ID"""
        return next((task for task in self.tasks if task.id == task_id), None)
    
    def to_dict_with_placeholders(self, missing_fields: List[str], target_framework: Optional[str] = None) -> Dict[str, Any]:
        """Convert FlexWorkflow to dictionary with '?' placeholders and descriptions for missing fields"""
        result = self.to_dict()
        
        # Add placeholders with descriptions for missing fields
        for field in missing_fields:
            if field == "schedule_configuration":
                result['schedule'] = {
                    'type': 'cron',
                    'expression': '? # REQUIRED: Cron expression (e.g., "0 9 * * *" for daily at 9 AM, "0 */6 * * *" for every 6 hours)',
                    'timezone': 'UTC',
                    '_description': 'Schedule defines when this workflow runs. Use standard cron format: minute hour day month weekday'
                }
            elif field.startswith("tasks[") and "].command_or_script" in field:
                # Extract task index from "tasks[3].command_or_script"
                import re
                match = re.search(r'tasks\[(\d+)\]\.command_or_script', field)
                if match:
                    task_index = int(match.group(1))
                    if task_index < len(result.get('tasks', [])):
                        task = result['tasks'][task_index]
                        task_type = task.get('type', 'unknown')
                        task['command'] = self._get_target_aware_placeholder(task_type, target_framework)
            elif field.startswith("task_") and field.endswith("_execution_details"):
                task_id = field.split("_")[1]
                # Find the task and add placeholder
                for task in result.get('tasks', []):
                    if task['id'] == task_id:
                        task['command'] = self._get_target_aware_placeholder(task['type'], target_framework)
            elif field.startswith("task_") and field.endswith("_sql_query"):
                task_id = field.split("_")[1]
                for task in result.get('tasks', []):
                    if task['id'] == task_id:
                        task['command'] = self._get_target_aware_placeholder(task['type'], target_framework)
        
        return result
    
    def _get_target_aware_placeholder(self, task_type: str, target_framework: Optional[str]) -> str:
        """Generate target-framework-aware placeholder for missing task commands"""
        base_msg = "See FLEX_SPECIFICATION.md for framework mapping details"
        
        if target_framework == 'airflow':
            if task_type == 'sql':
                return f'? # REQUIRED: SQL query for RedshiftSQLOperator or PostgreSQLOperator. {base_msg}'
            elif task_type == 'python':
                return f'? # REQUIRED: Python function name for PythonOperator. {base_msg}'
            elif task_type == 'bash':
                return f'? # REQUIRED: Shell command for BashOperator. {base_msg}'
            elif task_type == 'ParallelTaskOperator':
                return f'? # REQUIRED: Not directly supported in Airflow - use task groups or parallel task dependencies instead. {base_msg}'
            else:
                return f'? # REQUIRED: Command/script for {task_type} (will map to PythonOperator in Airflow). {base_msg}'
        elif target_framework == 'step_functions':
            if task_type == 'sql':
                return f'? # REQUIRED: SQL query for Lambda function or Batch job. {base_msg}'
            elif task_type == 'python':
                return f'? # REQUIRED: Python code for Lambda function. {base_msg}'
            elif task_type == 'bash':
                return f'? # REQUIRED: Shell command for Batch job or ECS task. {base_msg}'
            else:
                return f'? # REQUIRED: Command/script for {task_type} (will map to Lambda or Batch in Step Functions). {base_msg}'
        else:
            # Generic placeholder when target framework is unknown
            if task_type == 'sql':
                return f'? # REQUIRED: SQL query or statement to execute. {base_msg}'
            elif task_type == 'python':
                return f'? # REQUIRED: Python script or function call. {base_msg}'
            elif task_type == 'bash':
                return f'? # REQUIRED: Shell command or script to execute. {base_msg}'
            else:
                return f'? # REQUIRED: Command/script for {task_type} task. {base_msg}'
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert FlexWorkflow to dictionary for JSON serialization"""
        result = {
            'name': self.name,
            'description': self.description,
            'metadata': self.metadata,
            'parameters': self.parameters,
            'variables': self.variables,
            'triggers': self.triggers,
            'concurrency': self.concurrency,
            'tags': self.tags
        }
        
        # Handle schedule
        if self.schedule:
            result['schedule'] = {
                'type': self.schedule.type,
                'expression': self.schedule.expression,
                'timezone': self.schedule.timezone,
                'start_date': self.schedule.start_date,
                'end_date': self.schedule.end_date
            }
        
        # Handle tasks
        result['tasks'] = []
        for task in self.tasks:
            task_dict = {
                'id': task.id,
                'name': task.name,
                'type': task.type,
                'command': task.command,
                'script': task.script,
                'parameters': task.parameters,
                'timeout': task.timeout,
                'retries': task.retries,
                'retry_delay': task.retry_delay,
                'depends_on': [{'task_id': dep.task_id, 'condition': dep.condition} for dep in task.depends_on],
                'linked_service': task.linked_service,
                'compute_target': task.compute_target,
                'resource_requirements': task.resource_requirements
            }
            
            if task.source:
                task_dict['source'] = {
                    'type': task.source.type,
                    'connection_string': task.source.connection_string,
                    'dataset': task.source.dataset,
                    'table': task.source.table,
                    'query': task.source.query,
                    'parameters': task.source.parameters
                }
            
            if task.sink:
                task_dict['sink'] = {
                    'type': task.sink.type,
                    'connection_string': task.sink.connection_string,
                    'dataset': task.sink.dataset,
                    'table': task.sink.table,
                    'query': task.sink.query,
                    'parameters': task.sink.parameters
                }
            
            result['tasks'].append(task_dict)
        

        
        # Handle error handling
        if self.error_handling:
            result['error_handling'] = {
                'on_failure': self.error_handling.on_failure,
                'notification_emails': self.error_handling.notification_emails,
                'max_retries': self.error_handling.max_retries,
                'retry_delay': self.error_handling.retry_delay,
                'notification_webhooks': self.error_handling.notification_webhooks,
                'escalation_policy': self.error_handling.escalation_policy,
                'custom_error_handlers': self.error_handling.custom_error_handlers
            }
        
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'FlexWorkflow':
        """Create FlexWorkflow from dictionary with proper deserialization"""
        # Handle schedule
        schedule = None
        if data.get('schedule'):
            schedule_data = data['schedule']
            schedule = Schedule(
                type=schedule_data['type'],  # Free-form string
                expression=schedule_data['expression'],
                timezone=schedule_data.get('timezone', 'UTC'),
                start_date=schedule_data.get('start_date'),
                end_date=schedule_data.get('end_date')
            )
        
        # Handle tasks
        tasks = []
        for task_data in data.get('tasks', []):
            # Handle data source/sink
            source = None
            if task_data.get('source'):
                source_data = task_data['source']
                source = DataSource(
                    type=source_data['type'],
                    connection_string=source_data.get('connection_string'),
                    dataset=source_data.get('dataset'),
                    table=source_data.get('table'),
                    query=source_data.get('query'),
                    parameters=source_data.get('parameters', {})
                )
            
            sink = None
            if task_data.get('sink'):
                sink_data = task_data['sink']
                sink = DataSource(
                    type=sink_data['type'],
                    connection_string=sink_data.get('connection_string'),
                    dataset=sink_data.get('dataset'),
                    table=sink_data.get('table'),
                    query=sink_data.get('query'),
                    parameters=sink_data.get('parameters', {})
                )
            
            # Handle dependencies
            depends_on = []
            for dep_data in task_data.get('depends_on', []):
                depends_on.append(TaskDependency(
                    task_id=dep_data['task_id'],
                    condition=dep_data.get('condition', 'success')
                ))
            
            task = Task(
                id=task_data['id'],
                name=task_data['name'],
                type=task_data['type'],  # Free-form string
                command=task_data.get('command'),
                script=task_data.get('script'),
                parameters=task_data.get('parameters', {}),
                timeout=task_data.get('timeout'),
                retries=task_data.get('retries', 0),
                retry_delay=task_data.get('retry_delay', 300),
                depends_on=depends_on,
                source=source,
                sink=sink,
                linked_service=task_data.get('linked_service'),
                compute_target=task_data.get('compute_target'),
                resource_requirements=task_data.get('resource_requirements', {})
            )
            tasks.append(task)
        

        
        # Handle error handling
        error_handling = None
        if data.get('error_handling'):
            eh_data = data['error_handling']
            error_handling = ErrorHandling(
                on_failure=eh_data.get('on_failure', 'fail'),
                notification_emails=eh_data.get('notification_emails', []),
                max_retries=eh_data.get('max_retries', 0),
                retry_delay=eh_data.get('retry_delay', 300),
                notification_webhooks=eh_data.get('notification_webhooks', []),
                escalation_policy=eh_data.get('escalation_policy'),
                custom_error_handlers=eh_data.get('custom_error_handlers', {})
            )
        
        return cls(
            name=data['name'],
            description=data.get('description'),
            schedule=schedule,
            tasks=tasks,
            error_handling=error_handling,
            metadata=data.get('metadata', {}),
            parameters=data.get('parameters', {}),
            variables=data.get('variables', {}),
            triggers=data.get('triggers', []),
            concurrency=data.get('concurrency'),
            tags=data.get('tags', [])
        )