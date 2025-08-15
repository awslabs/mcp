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

import ast
import re
from typing import Any, Dict, List, Optional

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


class AirflowParser(WorkflowParser):
    """Parser to convert Airflow DAGs to FLEX format"""

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

            # Extract Python files for Glue/ADF execution
            python_files = self.extract_python_files(dag_code)

            # Extract enhanced orchestration features
            task_groups = self._extract_task_groups(dag_code)
            connections = self._extract_connections(dag_code)
            # trigger_rules = self._extract_trigger_rules(dag_code)  # Unused variable
            data_triggers = self._extract_data_triggers(dag_code)

            # Enhanced schedule with data triggers
            schedule = self._parse_schedule(dag_info.get('schedule_interval', ''))
            if schedule and data_triggers:
                schedule.data_triggers = data_triggers
                if dag_info.get('catchup') is not None:
                    schedule.catchup = bool(dag_info.get('catchup'))
                if dag_info.get('max_active_runs'):
                    schedule.max_active_runs = int(dag_info.get('max_active_runs', 1))

            return FlexWorkflow(
                name=dag_info.get('dag_id', 'airflow_workflow'),
                description=dag_info.get('description', 'Converted from Airflow DAG'),
                schedule=schedule,
                tasks=tasks,
                task_groups=task_groups,
                connections=connections,
                metadata={
                    'source_framework': 'airflow',
                    'original_dag_info': dag_info,
                    'python_files': python_files,  # Include extracted Python files
                },
                parsing_info=ParsingInfo(
                    source_framework='airflow',
                    parsing_completeness=self._calculate_parsing_completeness(tasks, schedule),
                    parsing_method='deterministic',
                ),
            )

        except SyntaxError:
            # If AST parsing fails, try regex-based extraction
            return self._parse_with_regex(dag_code)

    def _extract_dependencies(self, dag_code: str) -> list[tuple[str, str]]:
        """Extract dependencies ONLY from >> operators - the source of truth in Airflow"""
        dependencies = []

        # Build variable to task_id mapping
        try:
            tree = ast.parse(dag_code)
            var_to_task_id = self._build_variable_to_task_id_mapping(tree)
        except Exception:
            var_to_task_id = {}

        # Find TaskGroups and their tasks for expansion
        taskgroup_tasks = self._extract_taskgroup_tasks(dag_code)

        # Extract all lines with >> operators
        dependency_lines = []
        for line in dag_code.split('\n'):
            if '>>' in line and not line.strip().startswith('#'):
                dependency_lines.append(line.strip())

        for line in dependency_lines:
            # Parse dependency chain: A >> B >> C becomes [(A,B), (B,C)]
            parts = [part.strip() for part in line.split('>>')]

            for i in range(len(parts) - 1):
                upstream = parts[i].strip()
                downstream = parts[i + 1].strip()

                # Expand dependencies based on task/taskgroup types
                expanded_deps = self._expand_dependency(
                    upstream, downstream, taskgroup_tasks, var_to_task_id
                )
                dependencies.extend(expanded_deps)

        # Add cyclic dependencies for loops
        cyclic_deps = self._extract_cyclic_dependencies(dag_code, var_to_task_id)
        dependencies.extend(cyclic_deps)

        return dependencies

    def _extract_cyclic_dependencies(
        self, dag_code: str, var_to_task_id: dict
    ) -> list[tuple[str, str]]:
        """Extract cyclic dependencies for retry and while loops - INCLUDE in FLEX for proper retry loops"""
        cyclic_deps = []

        # Look for explicit loop-back patterns in comments or code
        lines = dag_code.split('\n')
        for line in lines:
            # Look for comments indicating loop-back
            if 'LOOPS BACK' in line.upper() or 'LOOP BACK' in line.upper():
                # Extract the dependency from the line
                if '>>' in line:
                    parts = line.split('>>')
                    if len(parts) >= 2:
                        upstream = parts[0].strip().split()[-1]  # Get last word before >>
                        downstream = parts[1].strip().split()[0]  # Get first word after >>

                        # Map variable names to task IDs
                        upstream_id = var_to_task_id.get(upstream, upstream)
                        downstream_id = var_to_task_id.get(downstream, downstream)

                        cyclic_deps.append((upstream_id, downstream_id))

        return cyclic_deps

    def _get_task_definition(self, dag_code: str, var_name: str) -> str:
        """Get the task definition line for a given variable name"""
        pattern = rf'{var_name}\s*=\s*[^\n]*'
        match = re.search(pattern, dag_code)
        return match.group(0) if match else ''

    def _extract_branch_paths(
        self, branch_var_name: str, dag_code: str, var_to_task_id: dict
    ) -> list[dict]:
        """Extract branch paths from BranchPythonOperator dependencies"""
        branches = []

        # Find all >> dependencies from this branch task
        pattern = rf'{branch_var_name}\s*>>\s*\[([^\]]+)\]'
        match = re.search(pattern, dag_code)

        if match:
            # Extract task names from list
            task_list = match.group(1)
            branch_vars = [task.strip() for task in task_list.split(',')]

            for var_name in branch_vars:
                actual_task_id = var_to_task_id.get(var_name, var_name)
                branches.append(
                    {
                        'next_task': actual_task_id,
                        'condition': f"$.result == '{actual_task_id}'",
                    }
                )

        return branches

    def _extract_taskgroup_tasks(self, dag_code: str) -> dict[str, list[str]]:
        """Extract TaskGroup names and their contained tasks"""
        taskgroup_tasks = {}

        # Find TaskGroups with their content
        taskgroup_pattern = r'with TaskGroup\([\'"]([^\'"]+)[\'"][^)]*\)\s*as\s+(\w+):(.*?)(?=\nwith|\n\w+\s*=\s*\w|\ndef|$)'
        matches = re.findall(taskgroup_pattern, dag_code, re.DOTALL)

        for group_name, var_name, content in matches:
            # Find task assignments within the group
            task_assignments = re.findall(r'(\w+)\s*=\s*\w+Operator', content)
            taskgroup_tasks[var_name] = task_assignments
            taskgroup_tasks[group_name] = task_assignments  # Also map by name

        return taskgroup_tasks

    def _extract_taskgroup_loop_tasks(self, dag_code: str) -> list[Task]:
        """Extract TaskGroups as semantic loop tasks"""
        tasks = []

        # Find TaskGroups with loop patterns
        taskgroup_pattern = r'with TaskGroup\(([\'"]?)([^\'"\),]+)\1[^)]*\)\s*as\s+(\w+):(.*?)(?=\nwith|\n\w+\s*=\s*\w|\ndef|$)'
        matches = re.findall(taskgroup_pattern, dag_code, re.DOTALL)

        # Store TaskGroup variable mappings for dependency expansion
        self._taskgroup_vars = {}

        for _quote, group_name, var_name, content in matches:
            # Store the mapping for dependency expansion
            self._taskgroup_vars[var_name] = group_name

            # Check for range pattern: for batch_id in range(1, 4)
            range_match = re.search(r'for\s+(\w+)\s+in\s+range\((\d+),\s*(\d+)\)', content)
            if range_match:
                loop_var, start, end = range_match.groups()
                start_num, end_num = int(start), int(end)

                # Find python_callable
                callable_pattern = r'python_callable\s*=\s*(\w+)'
                callable_match = re.search(callable_pattern, content)

                if callable_match:
                    callable_name = callable_match.group(1)

                    # Create a single loop task that represents the entire TaskGroup
                    loop_task = Task(
                        id=var_name,  # Use the TaskGroup variable name
                        name=group_name,
                        type='for_each',
                        command=callable_name,
                        parameters={
                            'loop_type': 'range',
                            'start': start_num,
                            'end': end_num,
                            'loop_var': loop_var,
                            'python_callable': callable_name,
                            'task_template': f'process_batch_{{{loop_var}}}',
                        },
                        retries=0,
                    )
                    tasks.append(loop_task)

            # Check for enumerate pattern: for i, item in enumerate([...])
            else:
                enum_match = re.search(
                    r'for\s+(\w+),\s*(\w+)\s+in\s+enumerate\(\[([^\]]+)\]\)', content
                )
                if enum_match:
                    index_var, item_var, items_list = enum_match.groups()

                    # Extract items from the list
                    items = [item.strip().strip('"\'') for item in items_list.split(',')]

                    # Find python_callable
                    callable_pattern = r'python_callable\s*=\s*(\w+)'
                    callable_match = re.search(callable_pattern, content)

                    if callable_match:
                        callable_name = callable_match.group(1)

                        # Create a single loop task that represents the entire TaskGroup
                        loop_task = Task(
                            id=var_name,  # Use the TaskGroup variable name
                            name=group_name,
                            type='for_each',
                            command=callable_name,
                            parameters={
                                'loop_type': 'enumerate',
                                'items': items,
                                'index_var': index_var,
                                'item_var': item_var,
                                'python_callable': callable_name,
                                'task_template': f'process_file_{{{index_var}}}',
                            },
                            retries=0,
                        )
                        tasks.append(loop_task)

        return tasks

    def _expand_dependency(
        self,
        upstream: str,
        downstream: str,
        taskgroup_tasks: dict,
        var_to_task_id: Optional[dict] = None,
    ) -> list[tuple[str, str]]:
        """Expand a single dependency into concrete task dependencies"""
        dependencies = []
        if var_to_task_id is None:
            var_to_task_id = {}

        # Handle list notation: [task1, task2] >> task3
        if upstream.startswith('[') and upstream.endswith(']'):
            upstream_tasks = re.findall(r'\w+', upstream)
            for task in upstream_tasks:
                expanded = self._expand_dependency(
                    task, downstream, taskgroup_tasks, var_to_task_id
                )
                dependencies.extend(expanded)
            return dependencies

        # Handle task >> [task1, task2]
        if downstream.startswith('[') and downstream.endswith(']'):
            downstream_tasks = re.findall(r'\w+', downstream)
            for task in downstream_tasks:
                expanded = self._expand_dependency(upstream, task, taskgroup_tasks, var_to_task_id)
                dependencies.extend(expanded)
            return dependencies

        # Handle TaskGroup variables - map to their actual task IDs
        if hasattr(self, '_taskgroup_vars') and upstream in self._taskgroup_vars:
            upstream_tasks = [upstream]  # Keep as single loop task
        elif upstream in taskgroup_tasks and taskgroup_tasks[upstream]:
            upstream_tasks = taskgroup_tasks[upstream]
        else:
            upstream_tasks = [upstream]

        if hasattr(self, '_taskgroup_vars') and downstream in self._taskgroup_vars:
            downstream_tasks = [downstream]  # Keep as single loop task
        elif downstream in taskgroup_tasks and taskgroup_tasks[downstream]:
            downstream_tasks = taskgroup_tasks[downstream]
        else:
            downstream_tasks = [downstream]

        # Create all combinations, mapping variable names to task IDs
        for up_task in upstream_tasks:
            for down_task in downstream_tasks:
                up_id = var_to_task_id.get(up_task, up_task)
                down_id = var_to_task_id.get(down_task, down_task)
                dependencies.append((up_id, down_id))

        return dependencies

    def _extract_dag_info(self, tree: ast.AST, dag_code: str) -> Dict[str, Any]:
        """Extract DAG configuration from AST"""
        dag_info = {}

        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                if (isinstance(node.func, ast.Name) and node.func.id == 'DAG') or (
                    isinstance(node.func, ast.Attribute) and node.func.attr == 'DAG'
                ):
                    # Extract DAG arguments
                    for arg in node.args:
                        if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                            dag_info['dag_id'] = arg.value
                        elif isinstance(arg, ast.Str):
                            dag_info['dag_id'] = arg.s

                    for keyword in node.keywords:
                        if keyword.arg == 'description':
                            if isinstance(keyword.value, ast.Constant) and isinstance(
                                keyword.value.value, str
                            ):
                                dag_info['description'] = keyword.value.value
                            elif isinstance(keyword.value, ast.Str):
                                dag_info['description'] = keyword.value.s
                        elif keyword.arg == 'schedule_interval':
                            dag_info['schedule_interval'] = self._extract_schedule_value(
                                keyword.value
                            )
                        elif keyword.arg == 'catchup':
                            dag_info['catchup'] = self._extract_boolean_value(keyword.value)
                        elif keyword.arg == 'max_active_runs':
                            dag_info['max_active_runs'] = self._extract_numeric_value(
                                keyword.value
                            )

        return dag_info

    def _extract_schedule_value(self, node: ast.AST) -> str:
        """Extract schedule interval value from AST node"""
        if isinstance(node, ast.Constant):
            return str(node.value)
        elif isinstance(node, ast.Str):
            return node.s
        elif isinstance(node, ast.Attribute):
            return f'@{node.attr}'
        return 'unknown'

    def _extract_tasks(self, tree: ast.AST, dag_code: str) -> list[Task]:
        """Extract tasks from Airflow DAG including TaskGroup expansion and dynamic task patterns"""
        tasks = []

        # Find TaskGroup content to exclude from regular parsing
        taskgroup_content = self._get_taskgroup_content(dag_code)

        # Create mapping from variable names to task_id values
        var_to_task_id = self._build_variable_to_task_id_mapping(tree)

        # Dynamic task creation should be handled by AI enhancement, not deterministic parsing

        # First extract regular tasks from AST
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        var_name = target.id

                        if isinstance(node.value, ast.Call):
                            operator_name = self._get_operator_name(node.value)

                            # Skip DAG assignment itself and tasks inside TaskGroups
                            if (
                                var_name != 'dag'
                                and operator_name != 'DAG'
                                and not self._is_task_in_taskgroup(var_name, taskgroup_content)
                            ):
                                task_type = self._map_operator_to_type(operator_name)

                                # Extract task parameters
                                task_params = self._extract_task_params(node.value)

                                # Skip phantom tasks with no meaningful parameters
                                if not task_params or not any(
                                    v
                                    for v in task_params.values()
                                    if v not in ['dag', None, '', 'unknown']
                                ):
                                    continue

                                # Clean up parameters - remove None values and AST objects
                                cleaned_params = {
                                    k: v
                                    for k, v in task_params.items()
                                    if v is not None and not str(v).startswith('<ast.')
                                }
                                task_params = cleaned_params

                                # Use actual task_id from parameters, fallback to variable name
                                actual_task_id = task_params.get('task_id', var_name)

                                # Handle BranchPythonOperator as two separate tasks
                                if task_type == 'branch':
                                    # Create python task for the function execution
                                    python_task = Task(
                                        id=actual_task_id,
                                        name=actual_task_id,
                                        type='python',
                                        command=self._extract_command(operator_name, task_params),
                                        script_file=f'{actual_task_id}.py',
                                        parameters=task_params,
                                        timeout=task_params.get('execution_timeout'),
                                        retries=task_params.get('retries', 0),
                                    )
                                    tasks.append(python_task)

                                    # Create branch task for the decision logic
                                    branches = self._extract_branch_paths(
                                        var_name, dag_code, var_to_task_id
                                    )
                                    branch_task = Task(
                                        id=f'{actual_task_id}_choice',
                                        name=f'{actual_task_id}_choice',
                                        type='branch',
                                        command='',
                                        parameters={'branches': branches},
                                        depends_on=[
                                            TaskDependency(
                                                task_id=actual_task_id,
                                                condition='success',
                                            )
                                        ],
                                        timeout=task_params.get('execution_timeout'),
                                        retries=task_params.get('retries', 0),
                                    )
                                    tasks.append(branch_task)
                                    continue  # Skip the regular task creation
                                else:
                                    # Set script_file for Python tasks that will need external execution
                                    script_file = None
                                    if task_type == 'python' and 'python_callable' in task_params:
                                        script_file = f'{actual_task_id}.py'

                                    # Extract enhanced task features
                                    connection_id = self._extract_connection_id(task_params)
                                    trigger_rule = self._extract_trigger_rule(task_params)
                                    batch_size = task_params.get('batch_size')

                                    task = Task(
                                        id=actual_task_id,
                                        name=actual_task_id,
                                        type=task_type,
                                        command=self._extract_command(operator_name, task_params),
                                        script_file=script_file,
                                        parameters=task_params,
                                        timeout=task_params.get('execution_timeout'),
                                        retries=task_params.get('retries', 0),
                                        connection_id=connection_id,
                                        trigger_rule=trigger_rule,
                                        batch_size=batch_size,
                                    )
                                    tasks.append(task)

        # Extract TaskGroup loop tasks
        taskgroup_loop_tasks = self._extract_taskgroup_loop_tasks(dag_code)
        tasks.extend(taskgroup_loop_tasks)

        return tasks

    def _get_taskgroup_content(self, dag_code: str) -> list[str]:
        """Get all TaskGroup content blocks"""
        taskgroup_pattern = (
            r'with TaskGroup\([^)]*\)\s*as\s+\w+:(.*?)(?=\nwith|\n\w+\s*=\s*\w|\ndef|$)'
        )
        matches = re.findall(taskgroup_pattern, dag_code, re.DOTALL)
        return matches

    def _is_task_in_taskgroup(self, task_id: str, taskgroup_contents: list[str]) -> bool:
        """Check if a task is defined inside a TaskGroup"""
        for content in taskgroup_contents:
            if f'{task_id} =' in content:
                return True
        return False

    def _get_operator_name(self, call_node: ast.Call) -> str:
        """Get operator name from call node"""
        if isinstance(call_node.func, ast.Name):
            return call_node.func.id
        elif isinstance(call_node.func, ast.Attribute):
            return call_node.func.attr
        return 'unknown'

    def _get_function_name(self, call_node: ast.Call) -> str:
        """Get function name from call node"""
        if isinstance(call_node.func, ast.Name):
            return call_node.func.id
        elif isinstance(call_node.func, ast.Attribute):
            return call_node.func.attr
        return 'unknown'

    def _extract_timedelta_seconds(self, call_node: ast.Call) -> int:
        """Extract seconds from timedelta call"""
        seconds = 0
        for keyword in call_node.keywords:
            if keyword.arg == 'seconds':
                if isinstance(keyword.value, ast.Constant) and isinstance(
                    keyword.value.value, (int, float)
                ):
                    seconds = int(keyword.value.value)
                elif isinstance(keyword.value, ast.Num) and isinstance(
                    keyword.value.n, (int, float)
                ):
                    seconds = int(keyword.value.n)
            elif keyword.arg == 'minutes':
                if isinstance(keyword.value, ast.Constant) and isinstance(
                    keyword.value.value, (int, float)
                ):
                    minutes_val = keyword.value.value
                elif isinstance(keyword.value, ast.Num) and isinstance(
                    keyword.value.n, (int, float)
                ):
                    minutes_val = keyword.value.n
                else:
                    minutes_val = 0
                if isinstance(minutes_val, (int, float)):
                    seconds = int(minutes_val * 60)
            elif keyword.arg == 'hours':
                if isinstance(keyword.value, ast.Constant) and isinstance(
                    keyword.value.value, (int, float)
                ):
                    hours_val = keyword.value.value
                elif isinstance(keyword.value, ast.Num) and isinstance(
                    keyword.value.n, (int, float)
                ):
                    hours_val = keyword.value.n
                else:
                    hours_val = 0
                if isinstance(hours_val, (int, float)):
                    seconds = int(hours_val * 3600)
        return seconds

    def _map_operator_to_type(self, operator_name: str) -> str:
        """Map Airflow operator to FLEX task type"""
        if (
            'SQL' in operator_name
            or 'Redshift' in operator_name
            or 'Postgres' in operator_name
            or 'MySQL' in operator_name
        ):
            return 'sql'
        elif 'BranchPython' in operator_name:
            return 'branch'
        elif 'Python' in operator_name:
            return 'python'
        elif 'Bash' in operator_name:
            return 'bash'
        elif 'Email' in operator_name:
            return 'email'
        elif 'Http' in operator_name:
            return 'http'
        else:
            return 'python'  # Default

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
        if isinstance(node, ast.Constant):
            return node.value
        elif isinstance(node, ast.Str):
            return node.s
        elif hasattr(ast, 'Num') and isinstance(node, ast.Num):
            return node.n
        elif isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.List):
            return [self._extract_value(item) for item in node.elts]
        elif isinstance(node, ast.Call):
            # Handle function calls like timedelta(minutes=5)
            func_name = self._get_function_name(node)
            if func_name == 'timedelta':
                return self._extract_timedelta_seconds(node)
            else:
                return f'{func_name}()'  # Generic function call
        elif isinstance(node, ast.Attribute):
            # Handle attribute access like TriggerRule.ONE_SUCCESS
            return f'{self._extract_value(node.value)}.{node.attr}'
        else:
            # Return None for unparseable nodes instead of AST object string
            return None

    def _build_variable_to_task_id_mapping(self, tree: ast.AST) -> dict:
        """Build mapping from Python variable names to actual task_id values"""
        var_to_task_id = {}

        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        var_name = target.id

                        if isinstance(node.value, ast.Call):
                            # Extract task_id from operator parameters
                            task_params = self._extract_task_params(node.value)
                            actual_task_id = task_params.get('task_id', var_name)
                            var_to_task_id[var_name] = actual_task_id

        return var_to_task_id

    def _extract_command(self, operator_name: str, params: Dict[str, Any]) -> str:
        """Extract command/script from task parameters"""
        if 'sql' in params:
            return params['sql']
        elif 'python_callable' in params:
            callable_name = params['python_callable']
            return callable_name if isinstance(callable_name, str) else str(callable_name)
        elif 'bash_command' in params:
            return params['bash_command']
        elif 'Email' in operator_name:
            # Email operators send notifications
            subject = params.get('subject', 'Email notification')
            return f"send_email(subject='{subject}')"
        elif 'Sensor' in operator_name or 'filepath' in params:
            # Sensor operators wait for conditions
            filepath = params.get('filepath', 'unknown_file')
            return f"wait_for_file('{filepath}')"
        elif 'DummyOperator' in operator_name:
            return 'pass  # Dummy task for workflow control'
        elif 'BranchPythonOperator' in operator_name and 'python_callable' in params:
            callable_name = params['python_callable']
            return callable_name if isinstance(callable_name, str) else str(callable_name)
        return ''

    def extract_python_files(self, dag_code: str) -> Dict[str, str]:
        """Extract Python functions and create standalone files for Glue/ADF execution"""
        python_files = {}

        try:
            tree = ast.parse(dag_code)

            # Extract all function definitions
            functions = self._extract_function_definitions(tree, dag_code)

            # Extract imports
            imports = self._extract_imports(tree, dag_code)

            # Create files for each python_callable
            tasks = self._extract_tasks(tree, dag_code)
            for task in tasks:
                if task.type == 'python' and task.command:
                    function_name = task.command
                    if function_name in functions:
                        file_content = self._create_python_file(
                            function_name, functions[function_name], imports, task.id
                        )
                        python_files[f'{task.id}.py'] = file_content

            return python_files

        except Exception:
            # Return empty dict if extraction fails
            return {}

    def _extract_function_definitions(self, tree: ast.AST, dag_code: str) -> Dict[str, str]:
        """Extract function definitions from AST"""
        functions = {}

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                # Get function source code
                func_source = self._get_function_source(node, dag_code)
                functions[node.name] = func_source

        return functions

    def _extract_imports(self, tree: ast.AST, dag_code: str) -> List[str]:
        """Extract import statements from AST"""
        imports = []

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.asname:
                        imports.append(f'import {alias.name} as {alias.asname}')
                    else:
                        imports.append(f'import {alias.name}')
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ''
                names = []
                for alias in node.names:
                    if alias.asname:
                        names.append(f'{alias.name} as {alias.asname}')
                    else:
                        names.append(alias.name)
                imports.append(f'from {module} import {", ".join(names)}')

        # Filter out Airflow-specific imports
        filtered_imports = []
        for imp in imports:
            if not any(
                airflow_module in imp
                for airflow_module in [
                    'airflow',
                    'DAG',
                    'PythonOperator',
                    'BashOperator',
                    'SqlOperator',
                ]
            ):
                filtered_imports.append(imp)

        return filtered_imports

    def _get_function_source(self, func_node: ast.FunctionDef, dag_code: str) -> str:
        """Extract function source code from AST node"""
        lines = dag_code.split('\n')

        # Get function start and end lines
        start_line = func_node.lineno - 1  # AST is 1-indexed

        # Find function end by looking for next function or class at same indentation
        end_line = len(lines)
        func_indent = len(lines[start_line]) - len(lines[start_line].lstrip())

        for i in range(start_line + 1, len(lines)):
            line = lines[i]
            if line.strip():  # Non-empty line
                current_indent = len(line) - len(line.lstrip())
                if current_indent <= func_indent and (
                    line.strip().startswith('def ')
                    or line.strip().startswith('class ')
                    or line.strip().startswith('@')
                ):
                    end_line = i
                    break

        # Extract function lines
        func_lines = lines[start_line:end_line]
        return '\n'.join(func_lines)

    def _create_python_file(
        self, function_name: str, function_code: str, imports: List[str], task_id: str
    ) -> str:
        """Create standalone Python file for Glue/ADF execution"""
        # Standard imports for ETL jobs
        standard_imports = [
            'import sys',
            'import json',
            'import boto3',
            'from datetime import datetime',
        ]

        # Combine imports
        all_imports = standard_imports + imports

        # Create main execution block
        main_block = f"""
if __name__ == "__main__":
    # Parse command line arguments for Glue/ADF
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--task_id', default='{task_id}')
    parser.add_argument('--workflow_name', default='etl_workflow')

    # Add any additional arguments based on function signature
    args = parser.parse_args()

    try:
        # Execute the main function
        result = {function_name}()

        # Log success
        print(f"Task {{args.task_id}} completed successfully")
        print(f"Result: {{result}}")

    except Exception as e:
        print(f"Task {{args.task_id}} failed: {{str(e)}}")
        sys.exit(1)
"""

        # Combine all parts
        file_content = '\n'.join(
            [
                '#!/usr/bin/env python3',
                '"""',
                f'Standalone Python script for task: {task_id}',
                f'Generated from Airflow DAG function: {function_name}',
                'Compatible with AWS Glue Python Shell and Azure Data Factory',
                '"""',
                '',
                '\n'.join(all_imports),
                '',
                function_code,
                '',
                main_block,
            ]
        )

        return file_content

    def _apply_dependencies_to_tasks(
        self, tasks: list[Task], dependencies: list[tuple[str, str]]
    ) -> None:
        """Apply extracted dependencies to tasks"""
        # Create a mapping of task_id to task for quick lookup
        task_map = {task.id: task for task in tasks}

        # Apply dependencies
        for upstream_id, downstream_id in dependencies:
            # Handle BranchPythonOperator split: redirect dependencies FROM choice task to downstream tasks
            if f'{upstream_id}_choice' in task_map:
                upstream_id = f'{upstream_id}_choice'

            if downstream_id in task_map:
                downstream_task = task_map[downstream_id]

                # Add dependency if not already present
                if not any(dep.task_id == upstream_id for dep in downstream_task.depends_on):
                    downstream_task.depends_on.append(
                        TaskDependency(task_id=upstream_id, condition='success')
                    )

    def _parse_schedule(self, schedule_interval: Optional[str]) -> Schedule:
        """Convert Airflow schedule to FLEX format"""
        if not schedule_interval or schedule_interval == 'None':
            return Schedule(type='manual', expression='manual')

        if schedule_interval.startswith('@'):
            if schedule_interval == '@daily':
                return Schedule(type='rate', expression='rate(1 day)')
            elif schedule_interval == '@hourly':
                return Schedule(type='rate', expression='rate(1 hour)')
            elif schedule_interval == '@weekly':
                return Schedule(type='rate', expression='rate(7 days)')

        # Assume cron format
        return Schedule(type='cron', expression=schedule_interval)

    def _parse_with_regex(self, dag_code: str) -> FlexWorkflow:
        """Fallback regex-based parsing when AST fails"""
        # Extract DAG ID
        dag_id_match = re.search(r"dag_id\s*=\s*['\"]([^'\"]+)['\"]", dag_code)
        dag_id = dag_id_match.group(1) if dag_id_match else 'unknown_dag'

        # Extract description
        desc_match = re.search(r"description\s*=\s*['\"]([^'\"]+)['\"]", dag_code)
        description = desc_match.group(1) if desc_match else 'Converted from Airflow'

        return FlexWorkflow(
            name=dag_id,
            description=description,
            tasks=[],
            metadata={'source_framework': 'airflow', 'parsing_method': 'regex'},
            parsing_info=ParsingInfo(
                source_framework='airflow',
                parsing_completeness=0.5,
                parsing_method='regex',
            ),
        )

    # Standardized optional methods from base class
    def detect_framework(self, input_code: str) -> bool:
        """Detect if input code is Airflow DAG"""
        return any(
            pattern in input_code for pattern in ['from airflow', 'import airflow', 'DAG(', '@dag']
        )

    def validate_input(self, input_code: str) -> bool:
        """Validate Airflow DAG syntax"""
        try:
            ast.parse(input_code)
            return True
        except SyntaxError:
            return False

    def parse_metadata(self, source_data: Any) -> Dict[str, Any]:
        """Extract workflow metadata from parsed AST"""
        if isinstance(source_data, ast.AST):
            return self._extract_dag_info(source_data, '')
        return {}

    def parse_tasks(self, source_data: Any) -> List[Task]:
        """Extract tasks from parsed AST"""
        if isinstance(source_data, ast.AST):
            return self._extract_tasks(source_data, '')
        return []

    def parse_schedule(self, source_data: Any) -> Optional[Schedule]:
        """Extract schedule from DAG info"""
        if isinstance(source_data, ast.AST):
            dag_info = self._extract_dag_info(source_data, '')
            return self._parse_schedule(dag_info.get('schedule_interval'))
        return None

    def parse_error_handling(self, source_data: Any) -> Optional[ErrorHandling]:
        """Extract error handling - Airflow uses default_args"""
        return None  # Airflow error handling is in default_args, not easily extractable from AST

    def parse_dependencies(self, source_data: Any) -> List[TaskDependency]:
        """Extract dependencies from >> operators"""
        deps = self._extract_dependencies('')  # Would need dag_code string
        return [TaskDependency(task_id=up, condition='success') for up, down in deps]

    def parse_loops(self, source_data: Any) -> Dict[str, TaskLoop]:
        """Extract TaskGroup loops"""
        return {}  # Would need to extract from TaskGroups

    def parse_conditional_logic(self, source_data: Any) -> List[Task]:
        """Extract BranchPythonOperator tasks"""
        return []  # Would need to filter branch tasks

    def parse_parallel_execution(self, source_data: Any) -> List[Task]:
        """Extract parallel task patterns"""
        return []  # Would need to analyze dependency patterns

    def get_parsing_completeness(self, flex_workflow: FlexWorkflow) -> float:
        """Calculate Airflow parsing completeness"""
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
    def parse_task_groups(self, source_data: Any) -> List[TaskGroup]:
        """Extract TaskGroups from Airflow DAG"""
        return self._extract_task_groups('')  # Would need dag_code

    def parse_connections(self, source_data: Any) -> Dict[str, str]:
        """Extract connection references from Airflow DAG"""
        return self._extract_connections('')  # Would need dag_code

    def parse_trigger_rules(self, source_data: Any) -> Dict[str, str]:
        """Extract trigger rules from Airflow DAG"""
        return self._extract_trigger_rules('')  # Would need dag_code

    def parse_data_triggers(self, source_data: Any) -> List[TriggerConfig]:
        """Extract data triggers from Airflow DAG"""
        return self._extract_data_triggers('')  # Would need dag_code

    # Helper methods for enhanced features
    def _extract_task_groups(self, dag_code: str) -> List[TaskGroup]:
        """Extract TaskGroup definitions"""
        task_groups = []
        pattern = r'with TaskGroup\([\'"]([^\'"]+)[\'"][^)]*\)\s*as\s+(\w+):'
        matches = re.findall(pattern, dag_code)

        for group_name, _var_name in matches:
            task_groups.append(TaskGroup(group_id=group_name, tooltip=f'Task group: {group_name}'))

        return task_groups

    def _extract_connections(self, dag_code: str) -> Dict[str, str]:
        """Extract connection IDs from task parameters"""
        connections = {}

        # Find connection parameters
        conn_patterns = [
            r'postgres_conn_id\s*=\s*[\'"]([^\'"]+)[\'"]',
            r'mysql_conn_id\s*=\s*[\'"]([^\'"]+)[\'"]',
            r'redshift_conn_id\s*=\s*[\'"]([^\'"]+)[\'"]',
            r'fs_conn_id\s*=\s*[\'"]([^\'"]+)[\'"]',
            r'http_conn_id\s*=\s*[\'"]([^\'"]+)[\'"]',
        ]

        for pattern in conn_patterns:
            matches = re.findall(pattern, dag_code)
            for conn_id in matches:
                if 'postgres' in pattern:
                    connections[conn_id] = 'postgres'
                elif 'mysql' in pattern:
                    connections[conn_id] = 'mysql'
                elif 'redshift' in pattern:
                    connections[conn_id] = 'redshift'
                elif 'fs' in pattern:
                    connections[conn_id] = 'filesystem'
                elif 'http' in pattern:
                    connections[conn_id] = 'http'

        return connections

    def _extract_trigger_rules(self, dag_code: str) -> Dict[str, str]:
        """Extract trigger rules from task definitions"""
        trigger_rules = {}
        pattern = r'trigger_rule\s*=\s*TriggerRule\.([A-Z_]+)'
        matches = re.findall(pattern, dag_code)

        # Map TriggerRule enum values to FLEX format
        rule_mapping = {
            'ALL_SUCCESS': 'all_success',
            'ALL_FAILED': 'all_failed',
            'ONE_SUCCESS': 'one_success',
            'ONE_FAILED': 'one_failed',
            'NONE_FAILED': 'none_failed',
            'NONE_FAILED_OR_SKIPPED': 'none_failed',
        }

        for rule in matches:
            if rule in rule_mapping:
                trigger_rules[rule] = rule_mapping[rule]

        return trigger_rules

    def _extract_data_triggers(self, dag_code: str) -> List[TriggerConfig]:
        """Extract FileSensor and other data triggers"""
        triggers = []

        # Find FileSensor tasks
        file_pattern = r'FileSensor\([^)]*filepath\s*=\s*[\'"]([^\'"]+)[\'"][^)]*\)'
        file_matches = re.findall(file_pattern, dag_code)

        for filepath in file_matches:
            triggers.append(
                TriggerConfig(
                    trigger_type='file',
                    target=filepath,
                    poke_interval=300,
                    timeout=3600,
                )
            )

        return triggers

    def _extract_connection_id(self, task_params: Dict[str, Any]) -> Optional[str]:
        """Extract connection ID from task parameters"""
        conn_keys = [
            'postgres_conn_id',
            'mysql_conn_id',
            'redshift_conn_id',
            'fs_conn_id',
            'http_conn_id',
        ]
        for key in conn_keys:
            if key in task_params:
                return task_params[key]
        return None

    def _extract_trigger_rule(self, task_params: Dict[str, Any]) -> str:
        """Extract trigger rule from task parameters"""
        trigger_rule = task_params.get('trigger_rule', 'all_success')
        if isinstance(trigger_rule, str) and 'TriggerRule.' in trigger_rule:
            # Extract enum value
            rule = trigger_rule.split('.')[-1].lower()
            return rule.replace('_', '_')
        return 'all_success'

    def _extract_boolean_value(self, node: ast.AST) -> bool:
        """Extract boolean value from AST node"""
        if isinstance(node, ast.Constant):
            return bool(node.value)
        elif isinstance(node, ast.NameConstant):
            return bool(node.value)
        return True

    def _extract_numeric_value(self, node: ast.AST) -> int:
        """Extract numeric value from AST node"""
        if isinstance(node, ast.Constant):
            if isinstance(node.value, (int, float)):
                return int(node.value)
            # Return default for non-numeric constants
            return 1
        elif (
            hasattr(ast, 'Num')
            and isinstance(node, ast.Num)
            and hasattr(node, 'n')
            and isinstance(node.n, (int, float))
        ):
            return int(node.n)
        return 1

    def _calculate_parsing_completeness(
        self, tasks: List[Task], schedule: Optional[Schedule]
    ) -> float:
        """Calculate actual parsing completeness based on extracted information"""
        total_score = 0.0
        max_score = 0.0

        # Task completeness (70% of total score)
        task_weight = 0.7
        if tasks:
            task_score = 0.0
            for task in tasks:
                # Each task contributes equally
                task_completeness = 0.0

                # Task has valid command/script (most important)
                if (
                    task.command
                    and task.command.strip()
                    and not self._is_placeholder_command(task.command)
                ):
                    task_completeness += 0.8
                elif task.script and task.script.strip():
                    task_completeness += 0.8

                # Task has proper type mapping
                if task.type and task.type != 'unknown':
                    task_completeness += 0.1

                # Task has parameters
                if task.parameters:
                    task_completeness += 0.1

                task_score += task_completeness

            task_score = task_score / len(tasks)  # Average across all tasks
            total_score += task_score * task_weight

        max_score += task_weight

        # Schedule completeness (20% of total score)
        schedule_weight = 0.2
        if schedule and schedule.expression and schedule.expression != 'unknown':
            total_score += schedule_weight
        max_score += schedule_weight

        # Basic workflow structure (10% of total score)
        structure_weight = 0.1
        if tasks:  # Has tasks
            total_score += structure_weight
        max_score += structure_weight

        return total_score / max_score if max_score > 0 else 0.0

    def _is_placeholder_command(self, command: str) -> bool:
        """Check if command is a placeholder that needs AI enhancement"""
        if not command:
            return True

        command = command.strip().lower()

        # Common placeholder patterns
        placeholder_patterns = [
            '?',
            'todo',
            'tbd',
            'placeholder',
            'fill_me',
            'replace_me',
        ]

        return command in placeholder_patterns or len(command) < 2
