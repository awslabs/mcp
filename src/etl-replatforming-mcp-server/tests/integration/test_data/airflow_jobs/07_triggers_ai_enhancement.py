#!/usr/bin/env python3
"""
Airflow DAG that triggers AI enhancement
This DAG has complex patterns that deterministic parsing cannot handle completely
"""

from datetime import datetime

from airflow import DAG
from airflow.operators.bash_operator import BashOperator
from airflow.operators.python_operator import PythonOperator

# DAG with missing schedule_interval - this should trigger AI enhancement
dag = DAG(
    '07_triggers_ai_enhancement',
    description='Pipeline with complex patterns that need AI enhancement',
    start_date=datetime(2024, 1, 1),
    # Intentionally missing schedule_interval
    catchup=False,
    tags=['ai-test', 'integration'],
)


# Complex dynamic task creation that parser cannot handle
def create_dynamic_tasks():
    """Dynamically create tasks - this pattern is too complex for deterministic parsing"""
    tasks = []
    for i in range(3):
        task = PythonOperator(
            task_id=f'dynamic_task_{i}',
            python_callable=lambda i=i: print(f'Processing batch {i}'),
            dag=dag,
        )
        tasks.append(task)
    return tasks


# This will create tasks that the parser cannot detect
dynamic_tasks = create_dynamic_tasks()


# Task with complex conditional logic
def complex_branching_logic(**context):
    """Complex branching that AI needs to understand"""
    import random

    conditions = ['path_a', 'path_b', 'path_c']
    return random.choice(conditions)


# Task with missing command/callable
incomplete_task = PythonOperator(
    task_id='incomplete_task',
    # Missing python_callable - this should trigger AI enhancement
    dag=dag,
)

# Task with placeholder command
placeholder_task = BashOperator(
    task_id='placeholder_task',
    bash_command='?',  # Placeholder that needs AI enhancement
    dag=dag,
)

# Task with generic function call
generic_task = PythonOperator(
    task_id='generic_task',
    python_callable=lambda: None,  # Generic lambda that needs enhancement
    dag=dag,
)

# Complex dependency pattern that's hard to parse
if len(dynamic_tasks) > 0:
    dynamic_tasks[0] >> incomplete_task >> placeholder_task >> generic_task
