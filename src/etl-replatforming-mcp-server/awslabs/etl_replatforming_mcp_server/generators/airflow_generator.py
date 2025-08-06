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

from typing import Dict, Any, Optional
from ..models.flex_workflow import FlexWorkflow



class AirflowGenerator:
    """Generator to convert FLEX workflow to Airflow DAG format"""
    
    def generate(self, workflow: FlexWorkflow, context_document: Optional[str] = None) -> Dict[str, Any]:
        """Convert FLEX workflow to Airflow DAG Python code
        
        Args:
            workflow: FLEX workflow representation
            naming_conventions: Organizational naming conventions
            
        Returns:
            Dict with generated Airflow DAG code and metadata
        """
        dag_code = self._generate_dag_code(workflow, context_document)
        
        workflow_name = f"etl_{workflow.name}"
        filename = f"{workflow_name}.py"
        
        return {
            "dag_code": dag_code,
            "dag_id": workflow_name,
            "filename": filename,
            "framework": "airflow"
        }
    
    def _generate_dag_code(self, workflow: FlexWorkflow, context_document: Optional[str] = None) -> str:
        """Generate Airflow DAG Python code"""
        imports = self._generate_imports(workflow)
        default_args = self._generate_default_args(workflow)
        dag_definition = self._generate_dag_definition(workflow)
        tasks = self._generate_tasks(workflow)
        dependencies = self._generate_dependencies(workflow)
        
        return f"""# Generated Airflow DAG from FLEX workflow
{imports}

# Default arguments
{default_args}

# Define DAG
{dag_definition}

# Tasks
{tasks}

# Dependencies
{dependencies}
"""
    
    def _generate_imports(self, workflow: FlexWorkflow) -> str:
        """Generate import statements based on task types"""
        imports = [
            "from datetime import datetime, timedelta",
            "from airflow import DAG"
        ]
        
        # Add imports based on task types
        task_types = {task.type for task in workflow.tasks}
        
        if "sql" in task_types:
            imports.append("from airflow.providers.amazon.aws.operators.redshift_sql import RedshiftSQLOperator")
        if "python" in task_types:
            imports.append("from airflow.operators.python import PythonOperator")
        if "bash" in task_types:
            imports.append("from airflow.operators.bash import BashOperator")
        if "email" in task_types:
            imports.append("from airflow.operators.email import EmailOperator")
        
        return "\n".join(imports)
    
    def _generate_default_args(self, workflow: FlexWorkflow) -> str:
        """Generate default arguments"""
        emails = []
        if workflow.error_handling:
            emails = workflow.error_handling.notification_emails
        
        return f"""default_args = {{
    'owner': 'data-team',
    'depends_on_past': False,
    'start_date': datetime(2024, 1, 1),
    'email_on_failure': {len(emails) > 0},
    'email_on_retry': False,
    'retries': {workflow.error_handling.max_retries if workflow.error_handling else 2},
    'retry_delay': timedelta(minutes=5),
    'email': {emails}
}}"""
    
    def _generate_dag_definition(self, workflow: FlexWorkflow) -> str:
        """Generate DAG definition"""
        schedule = "'@daily'"
        if workflow.schedule:
            if workflow.schedule.type == "rate":
                if "1 day" in workflow.schedule.expression:
                    schedule = "'@daily'"
                elif "1 hour" in workflow.schedule.expression:
                    schedule = "'@hourly'"
                else:
                    schedule = f"'{workflow.schedule.expression}'"
            elif workflow.schedule.type == "cron":
                schedule = f"'{workflow.schedule.expression}'"
        
        workflow_name = f"etl_{workflow.name}"
        return f"""dag = DAG(
    '{workflow_name}',
    default_args=default_args,
    description='{workflow.description or "Generated from FLEX workflow"}',
    schedule_interval={schedule},
    catchup=False,
    tags=['generated', 'etl']
)"""
    
    def _generate_tasks(self, workflow: FlexWorkflow) -> str:
        """Generate task definitions"""
        task_code = []
        
        for task in workflow.tasks:
            task_id = task.id
            if task.type == "sql":
                task_code.append(f"""
{task_id} = RedshiftSQLOperator(
    task_id='{task_id}',
    redshift_conn_id='redshift_default',
    sql='''
{task.command}
    ''',
    dag=dag
)""")
            elif task.type == "python":
                task_code.append(f"""
def {task_id}_func(**context):
    # {task.name}
    {task.command or "pass"}

{task_id} = PythonOperator(
    task_id='{task_id}',
    python_callable={task.id}_func,
    dag=dag
)""")
            elif task.type == "bash":
                task_code.append(f"""
{task_id} = BashOperator(
    task_id='{task_id}',
    bash_command='''{task.command or "echo 'Task executed'"}''',
    dag=dag
)""")
            else:
                # Default to Python operator for unknown types
                task_code.append(f"""
def {task_id}_func(**context):
    # {task.name} ({task.type})
    {task.command or "pass"}

{task_id} = PythonOperator(
    task_id='{task_id}',
    python_callable={task.id}_func,
    dag=dag
)""")
        
        return "\n".join(task_code)
    
    def _generate_dependencies(self, workflow: FlexWorkflow) -> str:
        """Generate task dependencies"""
        deps = []
        
        # Generate dependencies from task.depends_on
        for task in workflow.tasks:
            if task.depends_on:
                upstream_tasks = [dep.task_id for dep in task.depends_on]
                if upstream_tasks:
                    deps.append(f"[{', '.join(upstream_tasks)}] >> {task.id}")
        
        return "\n".join(deps) if deps else "# No dependencies defined"
    
