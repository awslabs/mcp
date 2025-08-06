#!/usr/bin/env python3

import ast
import re
from typing import Dict, Any
from ..models.flex_workflow import FlexWorkflow, Task, Schedule, TaskDependency
from ..models.exceptions import ParsingError
from .base_parser import WorkflowParser


class AirflowParser(WorkflowParser):
    """Parser to convert Airflow DAGs to FLEX format"""
    
    @property
    def framework_name(self) -> str:
        return "airflow"
    
    def can_parse(self, source_data: Dict[str, Any]) -> bool:
        """Check if source data is valid Airflow format"""
        return 'dag_code' in source_data or 'python_code' in source_data
    
    def parse(self, source_data: Dict[str, Any]) -> FlexWorkflow:
        """Parse Airflow source data to FLEX workflow"""
        if not self.can_parse(source_data):
            raise ParsingError("Invalid Airflow source data format", {"source_data": source_data})
        
        dag_code = source_data.get('dag_code') or source_data.get('python_code', '')
        return self._parse_airflow_code(dag_code)
    
    def parse_code(self, input_code: str) -> FlexWorkflow:
        """Parse raw Airflow Python code to FLEX workflow"""
        return self._parse_airflow_code(input_code)
    
    def _parse_airflow_code(self, dag_code: str) -> FlexWorkflow:
        """Parse Airflow DAG Python code to FLEX format"""
        try:
            # Parse the Python code into AST
            tree = ast.parse(dag_code)
            
            # Extract DAG information
            dag_info = self._extract_dag_info(tree, dag_code)
            tasks = self._extract_tasks(tree, dag_code)
            dependencies = self._extract_dependencies(dag_code)
            
            # Apply dependencies to tasks
            self._apply_dependencies_to_tasks(tasks, dependencies)
            
            return FlexWorkflow(
                name=dag_info.get('dag_id', 'airflow_workflow'),
                description=dag_info.get('description', 'Converted from Airflow DAG'),
                schedule=self._parse_schedule(dag_info.get('schedule_interval')),
                tasks=tasks,
                metadata={
                    "source_framework": "airflow",
                    "original_dag_info": dag_info
                }
            )
            
        except SyntaxError as e:
            # If AST parsing fails, try regex-based extraction
            return self._parse_with_regex(dag_code)
    
    def _extract_dag_info(self, tree: ast.AST, dag_code: str) -> Dict[str, Any]:
        """Extract DAG configuration from AST"""
        dag_info = {}
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                if (isinstance(node.func, ast.Name) and node.func.id == 'DAG') or \
                   (isinstance(node.func, ast.Attribute) and node.func.attr == 'DAG'):
                    
                    # Extract DAG arguments
                    for arg in node.args:
                        if isinstance(arg, ast.Str):
                            dag_info['dag_id'] = arg.s
                    
                    for keyword in node.keywords:
                        if keyword.arg == 'description' and isinstance(keyword.value, ast.Str):
                            dag_info['description'] = keyword.value.s
                        elif keyword.arg == 'schedule_interval':
                            dag_info['schedule_interval'] = self._extract_schedule_value(keyword.value)
        
        return dag_info
    
    def _extract_schedule_value(self, node: ast.AST) -> str:
        """Extract schedule interval value from AST node"""
        if isinstance(node, ast.Str):
            return node.s
        elif isinstance(node, ast.Attribute):
            return f"@{node.attr}"
        elif isinstance(node, ast.Constant):
            return str(node.value)
        return "unknown"
    
    def _extract_tasks(self, tree: ast.AST, dag_code: str) -> list[Task]:
        """Extract tasks from Airflow DAG"""
        tasks = []
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        task_id = target.id
                        
                        if isinstance(node.value, ast.Call):
                            operator_name = self._get_operator_name(node.value)
                            
                            # Skip DAG assignment itself
                            if task_id != 'dag' and operator_name != 'DAG':
                                task_type = self._map_operator_to_type(operator_name)
                                
                                # Extract task parameters
                                task_params = self._extract_task_params(node.value)
                                
                                # Skip phantom tasks with no meaningful parameters
                                if not task_params or not any(v for v in task_params.values() if v not in ['dag', None, '']):
                                    continue
                                
                                task = Task(
                                    id=task_id,
                                    name=task_params.get('task_id', task_id),
                                    type=task_type,
                                    command=self._extract_command(operator_name, task_params),
                                    parameters=task_params,
                                    timeout=task_params.get('execution_timeout'),
                                    retries=task_params.get('retries', 0)
                                )
                                tasks.append(task)
        
        return tasks
    
    def _get_operator_name(self, call_node: ast.Call) -> str:
        """Get operator name from call node"""
        if isinstance(call_node.func, ast.Name):
            return call_node.func.id
        elif isinstance(call_node.func, ast.Attribute):
            return call_node.func.attr
        return "unknown"
    
    def _map_operator_to_type(self, operator_name: str) -> str:
        """Map Airflow operator to FLEX task type"""
        if 'SQL' in operator_name or 'Redshift' in operator_name or 'Postgres' in operator_name or 'MySQL' in operator_name:
            return "sql"
        elif 'Python' in operator_name:
            return "python"
        elif 'Bash' in operator_name:
            return "bash"
        elif 'Email' in operator_name:
            return "email"
        elif 'Http' in operator_name:
            return "http"
        else:
            return "python"  # Default
    
    def _extract_task_params(self, call_node: ast.Call) -> Dict[str, Any]:
        """Extract task parameters from operator call"""
        params = {}
        
        for keyword in call_node.keywords:
            if keyword.arg:
                value = self._extract_value(keyword.value)
                params[keyword.arg] = value
        
        return params
    
    def _extract_value(self, node: ast.AST) -> Any:
        """Extract value from AST node"""
        if isinstance(node, ast.Str):
            return node.s
        elif isinstance(node, ast.Num):
            return node.n
        elif isinstance(node, ast.Constant):
            return node.value
        elif isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.List):
            return [self._extract_value(item) for item in node.elts]
        else:
            return str(node)
    
    def _extract_command(self, operator_name: str, params: Dict[str, Any]) -> str:
        """Extract command/script from task parameters"""
        if 'sql' in params:
            return params['sql']
        elif 'python_callable' in params:
            callable_name = params['python_callable']
            return callable_name if isinstance(callable_name, str) else str(callable_name)
        elif 'bash_command' in params:
            return params['bash_command']
        elif 'DummyOperator' in operator_name:
            return "pass  # Dummy task for workflow control"
        elif 'BranchPythonOperator' in operator_name and 'python_callable' in params:
            callable_name = params['python_callable']
            return callable_name if isinstance(callable_name, str) else str(callable_name)
        return ""
    
    def _extract_dependencies(self, dag_code: str) -> list[tuple[str, str]]:
        """Extract task dependencies using regex"""
        dependencies = []
        
        # Look for >> operators - simple case
        simple_pattern = r'(\w+)\s*>>\s*(\w+)'
        matches = re.findall(simple_pattern, dag_code)
        
        for upstream, downstream in matches:
            # Skip TaskGroup references
            if upstream != 'parallel_group' and downstream != 'parallel_group':
                dependencies.append((upstream, downstream))
        
        # Look for list dependencies: [task1, task2] >> task3
        list_pattern = r'\[([^\]]+)\]\s*>>\s*(\w+)'
        list_matches = re.findall(list_pattern, dag_code)
        
        for task_list, downstream in list_matches:
            # Extract individual task names from the list
            tasks = re.findall(r'\w+', task_list)
            for upstream in tasks:
                dependencies.append((upstream, downstream))
        
        # Look for task >> [task1, task2] pattern
        reverse_list_pattern = r'(\w+)\s*>>\s*\[([^\]]+)\]'
        reverse_matches = re.findall(reverse_list_pattern, dag_code)
        
        for upstream, task_list in reverse_matches:
            tasks = re.findall(r'\w+', task_list)
            for downstream in tasks:
                dependencies.append((upstream, downstream))
        
        # Handle TaskGroup dependencies by finding tasks within groups
        if 'parallel_group >> combine_results' in dag_code:
            # Find all tasks within the TaskGroup
            taskgroup_pattern = r'with TaskGroup\([^)]+\)[^:]*:(.*?)(?=\n\w|\nwith|\n#|$)'
            taskgroup_match = re.search(taskgroup_pattern, dag_code, re.DOTALL)
            if taskgroup_match:
                taskgroup_content = taskgroup_match.group(1)
                # Find task assignments within the group
                task_assignments = re.findall(r'(\w+)\s*=\s*\w+Operator', taskgroup_content)
                # All tasks in the group should depend on combine_results
                for task_name in task_assignments:
                    dependencies.append((task_name, 'combine_results'))
        
        return dependencies
    
    def _apply_dependencies_to_tasks(self, tasks: list[Task], dependencies: list[tuple[str, str]]) -> None:
        """Apply extracted dependencies to tasks"""
        # Create a mapping of task_id to task for quick lookup
        task_map = {task.id: task for task in tasks}
        
        # Apply dependencies
        for upstream_id, downstream_id in dependencies:
            if downstream_id in task_map:
                downstream_task = task_map[downstream_id]
                # Add dependency if not already present
                if not any(dep.task_id == upstream_id for dep in downstream_task.depends_on):
                    downstream_task.depends_on.append(TaskDependency(
                        task_id=upstream_id,
                        condition="success"
                    ))
    
    def _parse_schedule(self, schedule_interval: str) -> Schedule:
        """Convert Airflow schedule to FLEX format"""
        if not schedule_interval or schedule_interval == 'None':
            return Schedule(type="manual", expression="manual")
        
        if schedule_interval.startswith('@'):
            if schedule_interval == '@daily':
                return Schedule(type="rate", expression="rate(1 day)")
            elif schedule_interval == '@hourly':
                return Schedule(type="rate", expression="rate(1 hour)")
            elif schedule_interval == '@weekly':
                return Schedule(type="rate", expression="rate(7 days)")
        
        # Assume cron format
        return Schedule(type="cron", expression=schedule_interval)
    
    def _parse_with_regex(self, dag_code: str) -> FlexWorkflow:
        """Fallback regex-based parsing when AST fails"""
        # Extract DAG ID
        dag_id_match = re.search(r"dag_id\s*=\s*['\"]([^'\"]+)['\"]", dag_code)
        dag_id = dag_id_match.group(1) if dag_id_match else "unknown_dag"
        
        # Extract description
        desc_match = re.search(r"description\s*=\s*['\"]([^'\"]+)['\"]", dag_code)
        description = desc_match.group(1) if desc_match else "Converted from Airflow"
        
        return FlexWorkflow(
            name=dag_id,
            description=description,
            tasks=[],
            metadata={"source_framework": "airflow", "parsing_method": "regex"}
        )