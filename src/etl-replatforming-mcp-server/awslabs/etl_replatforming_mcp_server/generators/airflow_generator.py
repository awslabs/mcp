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

"""Airflow generator for converting from FLEX workflow format."""

from typing import Any, Dict, List, Optional, Union

from loguru import logger

from ..models.flex_workflow import ErrorHandling, FlexWorkflow, Schedule, Task
from .base_generator import BaseGenerator


class AirflowGenerator(BaseGenerator):
    """Generator to convert FLEX workflow to Airflow DAG format"""

    def generate(
        self,
        workflow: Union[FlexWorkflow, Dict[str, Any]],
        context_document: Optional[str] = None,
        llm_config: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Generate complete Airflow DAG from FLEX workflow using demand-driven approach"""
        # Convert dict to FlexWorkflow if needed
        if isinstance(workflow, dict):
            workflow = FlexWorkflow.from_dict(workflow)

        imports = self._generate_imports(workflow)
        default_args = self.generate_error_handling(workflow.error_handling)
        dag_definition = self._generate_dag_definition(workflow)

        # Use enhanced features if available
        enhanced_sections = []
        if self.use_enhanced_features(workflow):
            task_groups_code = self.generate_task_groups(workflow)
            if task_groups_code:
                enhanced_sections.append(f'# Task Groups\n{task_groups_code}')

        # Use demand-driven approach like Step Functions generator
        tasks_and_deps = self._generate_tasks_and_dependencies(workflow)

        # Combine all sections
        sections = [
            '# Generated Airflow DAG from FLEX workflow',
            imports,
            '# Default arguments',
            default_args,
            '# Define DAG',
            dag_definition,
        ]

        if enhanced_sections:
            sections.extend(enhanced_sections)

        sections.extend(['# Tasks and Dependencies (demand-driven generation)', tasks_and_deps])

        dag_code = '\n\n'.join(sections)

        workflow_name = f'etl_{workflow.name}'
        return {
            'dag_code': dag_code,
            'dag_id': workflow_name,
            'filename': f'{workflow_name}.py',
            'framework': 'airflow',
        }

    def generate_schedule(self, schedule: Optional[Schedule]) -> str:
        """Generate Airflow schedule_interval"""
        if not schedule:
            return "'@daily'"

        if schedule.type == 'rate':
            if schedule.expression and '1 day' in schedule.expression:
                return "'@daily'"
            elif schedule.expression and '1 hour' in schedule.expression:
                return "'@hourly'"
            else:
                return f"'{schedule.expression}'"
        elif schedule.type == 'cron':
            return f"'{schedule.expression}'"
        elif schedule.type == 'manual':
            return 'None'
        elif schedule.type == 'event':
            return 'None'
        return "'@daily'"

    def generate_task(self, task: Task, workflow: FlexWorkflow) -> str:
        """Generate Airflow task definition with enhanced features when available"""
        if task.type == 'for_each':
            return self._generate_for_each_task(task, workflow)
        elif task.type == 'branch':
            return self._generate_branch_task(task, workflow)
        elif task.type == 'sql':
            # Use connection_id if available, fallback to default
            conn_id = task.connection_id or 'redshift_default'
            # Escape single quotes in SQL command to prevent syntax errors
            sql_command = (task.command or 'SELECT 1').replace("'", "''")
            return f"""
{task.id} = RedshiftSQLOperator(
    task_id='{task.id}',
    redshift_conn_id='{conn_id}',
    sql='{sql_command}',
    dag=dag
)"""
        elif task.type == 'python':
            return f"""
def {task.id}_func(**context):
    # {task.name}
    try:
        {task.command or 'pass'}
        return {{"status": "completed", "task_id": "{task.id}"}}
    except Exception as e:
        return {{"status": "failed", "task_id": "{task.id}", "error": str(e)}}

{task.id} = PythonOperator(
    task_id='{task.id}',
    python_callable={task.id}_func,
    dag=dag
)"""
        elif task.type == 'bash':
            # Escape single quotes in bash command to prevent syntax errors
            bash_command = (task.command or "echo 'Task executed'").replace("'", "'\"'\"'")
            return f"""
{task.id} = BashOperator(
    task_id='{task.id}',
    bash_command='{bash_command}',
    dag=dag
)"""
        else:
            return f"""
def {task.id}_func(**context):
    # {task.name} ({task.type})
    try:
        {task.command or 'pass'}
        return {{"status": "completed", "task_id": "{task.id}"}}
    except Exception as e:
        return {{"status": "failed", "task_id": "{task.id}", "error": str(e)}}

{task.id} = PythonOperator(
    task_id='{task.id}',
    python_callable={task.id}_func,
    dag=dag
)"""

    def generate_dependencies(self, tasks: List[Task]) -> str:
        """Generate basic task dependencies"""
        deps = []

        for task in tasks:
            if task.depends_on:
                # Only handle status-based dependencies here
                upstream_tasks = [
                    dep.task_id
                    for dep in task.depends_on
                    if dep.condition_type == 'status' and dep.condition in ['success', None]
                ]
                if upstream_tasks:
                    deps.append(f'[{", ".join(upstream_tasks)}] >> {task.id}')

        return '\n'.join(deps) if deps else '# No basic dependencies'

    def generate_conditional_logic(self, task: Task, workflow: FlexWorkflow) -> str:
        """Generate BranchPythonOperator for conditional logic"""
        # Find upstream tasks with expressions for this task
        upstream_expressions = {}
        for dep in task.depends_on:
            if dep.condition_type == 'expression':
                if dep.task_id not in upstream_expressions:
                    upstream_expressions[dep.task_id] = []
                upstream_expressions[dep.task_id].append((task.id, dep.condition))

        branch_tasks = []
        for upstream_task_id, conditions in upstream_expressions.items():
            branch_task_id = f'{upstream_task_id}_branch'
            branch_func = self._generate_branch_function(branch_task_id, conditions)

            branch_tasks.append(
                f"""
{branch_func}

{branch_task_id} = BranchPythonOperator(
    task_id='{branch_task_id}',
    python_callable={branch_task_id}_func,
    dag=dag
)

# Branch dependencies
{upstream_task_id} >> {branch_task_id}
{branch_task_id} >> {task.id}"""
            )

        return '\n'.join(branch_tasks)

    def generate_error_handling(self, error_handling: Optional[ErrorHandling]) -> str:
        """Generate Airflow default_args with error handling"""
        emails = []
        retries = 2

        if error_handling:
            emails = error_handling.notification_emails or []
            retries = error_handling.max_retries or 2

        return f"""default_args = {{
    'owner': 'data-team',
    'depends_on_past': False,
    'start_date': datetime(2024, 1, 1),
    'email_on_failure': {len(emails) > 0},
    'email_on_retry': False,
    'retries': {retries},
    'retry_delay': timedelta(minutes=5),
    'email': {emails}
}}"""

    def _generate_imports(self, workflow: FlexWorkflow) -> str:
        """Generate import statements based on task types"""
        imports = [
            'from datetime import datetime, timedelta',
            'from airflow import DAG',
        ]

        # Add imports based on task types
        task_types = {task.type for task in workflow.tasks}

        if 'sql' in task_types:
            imports.append(
                'from airflow.providers.amazon.aws.operators.redshift_sql import RedshiftSQLOperator'
            )
        if 'python' in task_types:
            imports.append('from airflow.operators.python import PythonOperator')
        if 'bash' in task_types:
            imports.append('from airflow.operators.bash import BashOperator')
        if 'email' in task_types:
            imports.append('from airflow.operators.email import EmailOperator')

        # Add BranchPythonOperator if conditional logic is used
        if self.has_conditional_logic(workflow.tasks):
            imports.append('from airflow.operators.python import BranchPythonOperator')

        # Add TaskGroup if loops are used OR if task groups are defined
        if (
            self.has_loop_logic(workflow.tasks)
            or any(task.type == 'for_each' for task in workflow.tasks)
            or workflow.task_groups
        ):
            imports.append('from airflow.utils.task_group import TaskGroup')

        # Add PythonSensor if while loops are used
        if any(task.loop and task.loop.type == 'while' for task in workflow.tasks if task.loop):
            imports.append('from airflow.sensors.python import PythonSensor')

        # Add BranchPythonOperator if branch tasks are used
        if any(task.type == 'branch' for task in workflow.tasks):
            imports.append('from airflow.operators.python import BranchPythonOperator')

        return '\n'.join(imports)

    def _generate_dag_definition(self, workflow: FlexWorkflow) -> str:
        """Generate DAG definition"""
        schedule = self.generate_schedule(workflow.schedule)
        workflow_name = f'etl_{workflow.name}'
        return f"""dag = DAG(
    '{workflow_name}',
    default_args=default_args,
    description='{workflow.description or 'Generated from FLEX workflow'}',
    schedule_interval={schedule},
    catchup=False,
    tags=['generated', 'etl']
)"""

    def generate_loop_logic(self, task: Task, workflow: FlexWorkflow) -> str:
        """Generate TaskGroup for loop logic"""
        if not task.loop:
            return ''

        loop = task.loop

        if loop.type == 'for_each':
            return self._generate_for_each_loop(task, workflow)
        elif loop.type == 'range':
            return self._generate_range_loop(task, workflow)
        elif loop.type == 'while':
            return self._generate_while_loop(task, workflow)

        return ''

    def _generate_for_each_loop(self, task: Task, workflow: FlexWorkflow) -> str:
        """Generate for_each loop using TaskGroup"""
        loop = task.loop
        group_id = f'{task.id}_loop_group'

        # Generate items source
        items_code = ''
        if loop and loop.items and loop.items.source == 'static':
            items_code = f'items = {loop.items.values}'
        elif loop and loop.items and loop.items.source == 'task_output':
            items_code = f"""def get_items(**context):
    upstream_output = context['task_instance'].xcom_pull(task_ids='{loop.items.task_id}') or {{}}
    return upstream_output.get('{loop.items.path.replace('output.', '') if loop.items.path else 'items'}', [])

items = get_items()"""
        elif loop and loop.items and loop.items.source == 'range':
            items_code = (
                f'items = list(range({loop.items.start}, {loop.items.end}, {loop.items.step}))'
            )

        # Generate loop task
        task_code = self._generate_loop_task_code(task)

        item_variable = loop.item_variable if loop and loop.item_variable else 'item'
        return f"""
# Loop configuration for {task.id}
{items_code}

with TaskGroup(group_id='{group_id}', dag=dag) as {group_id}:
    for i, {item_variable} in enumerate(items):
        task_id = f"{task.id}_{{i}}"

{task_code}
"""

    def _generate_range_loop(self, task: Task, workflow: FlexWorkflow) -> str:
        """Generate range loop using TaskGroup"""
        loop = task.loop
        group_id = f'{task.id}_loop_group'

        task_code = self._generate_loop_task_code(task)

        item_variable = loop.item_variable if loop and loop.item_variable else 'item'
        start = loop.items.start if loop and loop.items else 0
        end = loop.items.end if loop and loop.items else 1
        step = loop.items.step if loop and loop.items else 1
        return f"""
# Range loop for {task.id}
with TaskGroup(group_id='{group_id}', dag=dag) as {group_id}:
    for {item_variable} in range({start}, {end}, {step}):
        task_id = f"{task.id}_{{{item_variable}}}"

{task_code}
"""

    def _generate_while_loop(self, task: Task, workflow: FlexWorkflow) -> str:
        """Generate while loop using sensor-based approach"""
        loop = task.loop
        sensor_id = f'{task.id}_while_sensor'

        # Convert condition to sensor logic
        condition = loop.condition if loop and loop.condition else 'True'
        item_variable = loop.item_variable if loop and loop.item_variable else 'iteration'

        return f"""
# While loop for {task.id} using sensor approach
def {sensor_id}_func(**context):
    # Check while condition: {condition}
    # This is a simplified implementation - customize based on your condition
    return {condition.replace('output.', 'context.get("task_instance").xcom_pull().get("')}

{sensor_id} = PythonSensor(
    task_id='{sensor_id}',
    python_callable={sensor_id}_func,
    poke_interval=60,
    timeout=3600,
    dag=dag
)

# Main task execution
def {task.id}_func(**context):
    {item_variable} = context.get('params', {{}}).get('{item_variable}', 0)
    # {task.name}
    {task.command or 'pass'}
    return {{"status": "completed", "{item_variable}": {item_variable}}}

{task.id} = PythonOperator(
    task_id='{task.id}',
    python_callable={task.id}_func,
    dag=dag
)

# Connect sensor to task
{sensor_id} >> {task.id}
"""

    def _generate_loop_task_code(self, task: Task) -> str:
        """Generate task code for use within loops"""
        item_variable = (
            task.loop.item_variable if task.loop and task.loop.item_variable else 'item'
        )
        if task.type == 'sql':
            # Escape single quotes in SQL command
            sql_command = (task.command or 'SELECT 1').replace("'", "''")
            return f"""        sql_task = RedshiftSQLOperator(
            task_id=task_id,
            redshift_conn_id='redshift_default',
            sql='{sql_command}'.format({item_variable}={item_variable}),
            dag=dag
        )"""
        elif task.type == 'python':
            return f"""        def loop_func(**context):
            {item_variable} = context['params']['{item_variable}']
            # {task.name}
            {task.command or 'pass'}
            return {{"status": "completed", "item": {item_variable}}}

        python_task = PythonOperator(
            task_id=task_id,
            python_callable=loop_func,
            params={{'{item_variable}': {item_variable}}},
            dag=dag
        )"""
        else:
            return f"""        def loop_func(**context):
            {item_variable} = context['params']['{item_variable}']
            # {task.name} ({task.type})
            {task.command or 'pass'}
            return {{"status": "completed", "item": {item_variable}}}

        task = PythonOperator(
            task_id=task_id,
            python_callable=loop_func,
            params={{'{item_variable}': {item_variable}}},
            dag=dag
        )"""

    def _generate_branch_task(self, task: Task, workflow: FlexWorkflow) -> str:
        """Generate BranchPythonOperator for branch tasks"""
        branches = task.parameters.get('branches', []) if task.parameters else []

        if not branches:
            # No branches defined - create a dummy branch
            return f"""
def {task.id}_func(**context):
    # No branches defined for {task.name}
    return None

{task.id} = PythonOperator(
    task_id='{task.id}',
    python_callable={task.id}_func,
    dag=dag
)"""

        # Generate branch conditions dynamically
        branch_conditions = []
        for i, branch in enumerate(branches):
            next_task = branch.get('next_task', 'default_task')
            condition = branch.get('condition', '')

            # Extract condition value from condition string like "$.result == 'value'"
            condition_value = self._extract_condition_value_for_airflow(condition, next_task)

            if i == 0:
                branch_conditions.append(f"    if result == '{condition_value}':")
            else:
                branch_conditions.append(f"    elif result == '{condition_value}':")
            branch_conditions.append(f"        return '{next_task}'")

        # Add default case
        default_task = branches[0].get('next_task', 'default_task') if branches else 'default_task'
        branch_conditions.append('    else:')
        branch_conditions.append(f"        return '{default_task}'  # Default")

        branch_logic = '\n'.join(branch_conditions)

        # Generate safe function call for branch logic
        command_call = (
            f'{task.command}(**context)' if task.command and task.command.strip() else "'default'"
        )

        branch_func = f"""def {task.id}_func(**context):
    # Branch logic for {task.name}
    result = {command_call}

    # Return the appropriate branch based on result
{branch_logic}
"""

        return f"""{branch_func}

{task.id} = BranchPythonOperator(
    task_id='{task.id}',
    python_callable={task.id}_func,
    dag=dag
)"""

    def _generate_for_each_task(self, task: Task, workflow: FlexWorkflow) -> str:
        """Generate TaskGroup for for_each loops"""
        params = task.parameters or {}
        loop_type = params.get('loop_type', 'range')

        if loop_type == 'range':
            start = params.get('start', 1)
            end = params.get('end', 4)
            loop_var = params.get('loop_var', 'i')

            return f"""
# TaskGroup for range-based loop: {task.name}
with TaskGroup(group_id='{task.id}', dag=dag) as {task.id}:
    for {loop_var} in range({start}, {end}):
        def loop_func_{loop_var}(**context):
            # Process batch {loop_var}
            return {{'batch_id': {loop_var}, 'status': 'completed'}}

        loop_task = PythonOperator(
            task_id=f'process_batch_{{{loop_var}}}',
            python_callable=loop_func_{loop_var},
            op_kwargs={{'batch_id': {loop_var}}},
            dag=dag
        )"""

        elif loop_type == 'enumerate':
            items = params.get('items', [])
            index_var = params.get('index_var', 'i')
            item_var = params.get('item_var', 'item')

            items_str = str(items).replace("'", '"')

            return f"""
# TaskGroup for enumerate-based loop: {task.name}
with TaskGroup(group_id='{task.id}', dag=dag) as {task.id}:
    for {index_var}, {item_var} in enumerate({items_str}):
        def loop_func_{index_var}(**context):
            # Process file {index_var}
            return {{'{item_var}': {item_var}, 'status': 'completed'}}

        loop_task = PythonOperator(
            task_id=f'process_file_{{{index_var}}}',
            python_callable=loop_func_{index_var},
            op_kwargs={{'{item_var}': {item_var}}},
            dag=dag
        )"""

        else:
            return f"""
# TaskGroup for generic loop: {task.name}
with TaskGroup(group_id='{task.id}', dag=dag) as {task.id}:
    def generic_loop_func(**context):
        # Generic loop implementation
        return {{'status': 'completed', 'task_id': '{task.id}'}}

    loop_task = PythonOperator(
        task_id='process_item',
        python_callable=generic_loop_func,
        dag=dag
    )"""

    def _generate_tasks_and_dependencies(self, workflow: FlexWorkflow) -> str:
        """Generate tasks and dependencies using demand-driven approach"""
        generated_tasks = set()
        task_definitions = []
        dependencies = []

        # Find start task (same logic as Step Functions generator)
        start_task_id = self._find_start_task(workflow)

        # Generate task chain from start task
        self._create_task_chain(
            start_task_id, workflow, generated_tasks, task_definitions, dependencies
        )

        # Combine tasks and dependencies
        result = '\n'.join(task_definitions)
        if dependencies:
            result += '\n\n# Dependencies\n' + '\n'.join(dependencies)

        return result

    def _find_start_task(self, workflow: FlexWorkflow) -> str:
        """Find the starting task (task with no upstream dependencies)"""
        tasks_with_deps = {task.id for task in workflow.tasks if task.depends_on}
        for task in workflow.tasks:
            if task.id not in tasks_with_deps:
                return task.id
        return workflow.tasks[0].id if workflow.tasks else 'empty_workflow'

    def _create_task_chain(
        self,
        task_id: str,
        workflow: FlexWorkflow,
        generated_tasks: set,
        task_definitions: list,
        dependencies: list,
    ):
        """Create task and its chain using demand-driven approach"""
        if task_id in generated_tasks:
            return  # Already created

        # Find task in FLEX
        task = self._find_task_in_flex(task_id, workflow)
        if not task:
            logger.error(f'Cannot create task chain for missing task: {task_id}')
            return

        # Generate task definition
        task_def = self.generate_task(task, workflow)
        task_definitions.append(task_def)
        generated_tasks.add(task_id)

        # Get children tasks
        children = self._get_children_tasks(task_id, workflow)

        # Special handling for branch tasks
        if task.type == 'branch':
            # Create all branch target tasks
            for child_id in children:
                self._create_task_chain(
                    child_id, workflow, generated_tasks, task_definitions, dependencies
                )
            # Branch operator handles transitions - no explicit dependencies needed
            return

        # Handle dependencies for non-branch tasks
        if len(children) == 1:
            # Single child - simple dependency
            child_id = children[0]
            dependencies.append(f'{task_id} >> {child_id}')
            self._create_task_chain(
                child_id, workflow, generated_tasks, task_definitions, dependencies
            )
        elif len(children) > 1:
            # Multiple children - parallel execution
            child_list = ', '.join(children)
            dependencies.append(f'{task_id} >> [{child_list}]')
            for child_id in children:
                self._create_task_chain(
                    child_id, workflow, generated_tasks, task_definitions, dependencies
                )

    def _get_children_tasks(self, task_id: str, workflow: FlexWorkflow) -> list:
        """Get all tasks that depend on the given task"""
        children = []

        # For branch tasks, children are defined in branch paths
        task = self._find_task_in_flex(task_id, workflow)
        if task and task.type == 'branch':
            branches = task.parameters.get('branches', []) if task.parameters else []
            return [branch['next_task'] for branch in branches]

        # For regular tasks, find dependents
        for task in workflow.tasks:
            if any(dep.task_id == task_id for dep in task.depends_on):
                children.append(task.id)
        return children

    def _find_task_in_flex(self, task_id: str, workflow: FlexWorkflow):
        """Find task in FLEX workflow with safe error handling"""
        if not workflow.tasks:
            logger.warning(f'No tasks found in workflow when looking for task: {task_id}')
            return None

        task = next((t for t in workflow.tasks if t.id == task_id), None)
        if not task:
            logger.warning(
                f'Task {task_id} referenced but not found in FLEX workflow. Available tasks: {[t.id for t in workflow.tasks]}'
            )
            return None
        return task

    def has_conditional_logic(self, tasks: list) -> bool:
        """Check if workflow contains conditional logic"""
        return any(
            any(dep.condition_type == 'expression' for dep in task.depends_on)
            for task in tasks
            if task.depends_on
        )

    def has_loop_logic(self, tasks: list) -> bool:
        """Check if workflow contains loop logic"""
        return any(task.type == 'for_each' for task in tasks)

    # Required methods from base class
    def get_supported_task_types(self) -> List[str]:
        """Get supported task types for Airflow"""
        from ..models.task_types import get_all_task_types

        return get_all_task_types()

    def supports_feature(self, feature: str) -> bool:
        """Check if Airflow supports specific FLEX feature"""
        supported_features = {
            'loops',
            'conditional_logic',
            'parallel_execution',
            'error_handling',
            'scheduling',
        }
        return feature in supported_features

    def generate_metadata(self, workflow: FlexWorkflow) -> Dict[str, Any]:
        """Generate Airflow DAG metadata"""
        return {
            'dag_id': f'etl_{workflow.name}',
            'description': workflow.description or 'Generated from FLEX workflow',
            'tags': ['generated', 'etl'],
        }

    def format_output(self, generated_content: Any, workflow: FlexWorkflow) -> Dict[str, Any]:
        """Format Airflow output"""
        workflow_name = f'etl_{workflow.name}'
        return {
            'dag_code': generated_content,
            'dag_id': workflow_name,
            'filename': f'{workflow_name}.py',
            'framework': 'airflow',
        }

    def validate_generated_output(self, output: Dict[str, Any]) -> bool:
        """Validate Airflow DAG output"""
        required_keys = ['dag_code', 'dag_id', 'filename', 'framework']
        return all(key in output for key in required_keys) and 'DAG(' in output.get('dag_code', '')

    # Enhanced orchestration features (optional)
    def generate_task_groups(self, workflow: FlexWorkflow) -> Optional[str]:
        """Generate TaskGroup definitions when available"""
        if not workflow.task_groups:
            return None

        task_group_code = []
        for group in workflow.task_groups:
            # Find tasks in this group
            group_tasks = [
                task
                for task in workflow.tasks
                if task.task_group and task.task_group.group_id == group.group_id
            ]

            if group_tasks:
                task_group_code.append(
                    f"""
# Task Group: {group.group_id}
with TaskGroup(group_id='{group.group_id}', tooltip='{group.tooltip or group.group_id}', dag=dag) as {group.group_id}_group:
    # Tasks in this group will be generated with group context
    pass"""
                )

        return '\n'.join(task_group_code) if task_group_code else None

    def generate_enhanced_schedule(self, workflow: FlexWorkflow) -> str:
        """Generate enhanced scheduling with data triggers when available"""
        if not workflow.schedule:
            return "'@daily'"

        # Check for data triggers
        if workflow.schedule.data_triggers:
            # Airflow doesn't support data triggers directly - add comment
            base_schedule = self.generate_schedule(workflow.schedule)
            triggers_comment = (
                '\n    # Data triggers detected - consider using FileSensor or custom sensors:\n'
            )
            for trigger in workflow.schedule.data_triggers:
                triggers_comment += f'    # - {trigger.trigger_type}: {trigger.target}\n'
            return base_schedule + triggers_comment

        return self.generate_schedule(workflow.schedule)

    def generate_parallel_execution(self, tasks: List[Task], workflow: FlexWorkflow) -> Any:
        """Generate parallel execution patterns for Airflow"""
        if not tasks:
            return None

        # Create parallel task list for Airflow >> [task1, task2] syntax
        task_ids = [task.id for task in tasks]
        return f'[{", ".join(task_ids)}]'

    def _extract_condition_value_for_airflow(self, condition: str, fallback: str) -> str:
        """Extract the comparison value from a condition string for Airflow branch logic"""
        import re

        # Handle different condition formats
        if '==' in condition:
            # Format: "$.result == 'value'" or "$.result == \"value\""
            match = re.search(r"==\s*['\"]([^'\"]+)['\"]?", condition)
            if match:
                return match.group(1)

        # Fallback: try to extract quoted string
        match = re.search(r"['\"]([^'\"]+)['\"]?", condition)
        if match:
            return match.group(1)

        # Last resort: use the fallback (usually the task name)
        return fallback

    def _generate_branch_function(self, branch_task_id: str, dependent_tasks: list) -> str:
        """Generate branch function for conditional logic"""
        conditions = []
        for task_id, condition in dependent_tasks:
            # Convert FLEX expression to Python condition
            python_condition = condition.replace('output.', "upstream_output.get('")
            python_condition = python_condition.replace(' AND ', "') and upstream_output.get('")
            python_condition = python_condition.replace(' OR ', "') or upstream_output.get('")
            python_condition += "')"

            conditions.append(f"    if {python_condition}:\n        return '{task_id}'")

        conditions_code = '\n    el'.join(conditions)

        return f"""def {branch_task_id}_func(**context):
    # Get output from upstream task
    upstream_task_id = context['task'].upstream_task_ids[0] if context['task'].upstream_task_ids else None
    upstream_output = context['task_instance'].xcom_pull(task_ids=upstream_task_id) or {{}}

    # Conditional logic
{conditions_code}

    # Default case - no condition met
    return None"""
