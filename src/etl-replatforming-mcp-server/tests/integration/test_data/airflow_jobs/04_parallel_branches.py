from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import BranchPythonOperator, PythonOperator
from airflow.providers.postgres.operators.postgres import PostgresOperator
from airflow.utils.task_group import TaskGroup

default_args = {
    'owner': 'data-team',
    'depends_on_past': False,
    'start_date': datetime(2024, 1, 1),
    'email_on_failure': False,
    'retries': 2,
    'retry_delay': timedelta(minutes=5),
}

dag = DAG(
    '04_parallel_branches_with_loops',
    default_args=default_args,
    description='Pipeline with parallel branches and loop complexity',
    schedule_interval='@daily',
    catchup=False,
    tags=['etl', 'parallel', 'branches', 'loops'],
)


def extract_data(**context):
    """Extract data from source"""
    print('Extracting data from source systems')
    return 'data_extracted'


def validate_customers(**context):
    """Validate customer data"""
    print('Validating customer data')
    return 'customers_validated'


def validate_orders(**context):
    """Validate order data"""
    print('Validating order data')
    return 'orders_validated'


def transform_customers(**context):
    """Transform customer data"""
    print('Transforming customer data')
    return 'customers_transformed'


def transform_orders(**context):
    """Transform order data"""
    print('Transforming order data')
    return 'orders_transformed'


def generate_report(**context):
    """Generate final report"""
    print('Generating final report')
    return 'report_generated'


def send_notification(**context):
    """Send completion notification"""
    print('Sending completion notification')
    return 'notification_sent'


def process_batch(batch_id, **context):
    """Process individual batch in loop"""
    print(f'Processing batch {batch_id}')
    return f'batch_{batch_id}_processed'


def check_quality_and_retry(**context):
    """Check data quality and decide if retry is needed"""
    import random

    quality_score = random.uniform(0.6, 1.0)

    if quality_score >= 0.9:
        print(f'Quality check passed: {quality_score:.2f}')
        return 'quality_passed'
    else:
        print(f'Quality check failed: {quality_score:.2f} - retry needed')
        return 'retry_processing'


def retry_failed_processing(**context):
    """Retry processing with improved parameters"""
    print('Retrying processing with improved parameters')
    return 'retry_completed'


def check_processing_complete(**context):
    """Check if all batches are processed (while loop condition)"""
    import random

    completion_rate = random.uniform(0.7, 1.0)

    if completion_rate >= 0.95:
        print(f'All processing complete: {completion_rate:.2%}')
        return 'processing_complete'
    else:
        print(f'Processing incomplete: {completion_rate:.2%} - continue')
        return 'continue_processing'


def continue_batch_processing(**context):
    """Continue processing next batch (while loop body)"""
    print('Processing next batch of data...')
    return 'next_batch_processed'


def quality_passed_func(**context):
    """Quality check passed - proceeding"""
    print('Quality check passed - proceeding')
    return 'quality_passed'


def processing_complete_func(**context):
    """All processing completed"""
    print('All processing completed')
    return 'processing_complete'


# Define tasks
extract_task = PythonOperator(task_id='extract_data', python_callable=extract_data, dag=dag)

validate_customers_task = PythonOperator(
    task_id='validate_customers', python_callable=validate_customers, dag=dag
)

validate_orders_task = PythonOperator(
    task_id='validate_orders', python_callable=validate_orders, dag=dag
)

transform_customers_task = PythonOperator(
    task_id='transform_customers', python_callable=transform_customers, dag=dag
)

transform_orders_task = PythonOperator(
    task_id='transform_orders', python_callable=transform_orders, dag=dag
)

load_data_task = PostgresOperator(
    task_id='load_data',
    postgres_conn_id='data_warehouse',
    sql="""
        INSERT INTO processed.final_data
        SELECT * FROM staging.transformed_customers
        UNION ALL
        SELECT * FROM staging.transformed_orders
    """,
    dag=dag,
)

generate_report_task = PythonOperator(
    task_id='generate_report', python_callable=generate_report, dag=dag
)

send_notification_task = PythonOperator(
    task_id='send_notification', python_callable=send_notification, dag=dag
)

# Dynamic loop - simulate for-each processing
with TaskGroup('batch_processing_loop', dag=dag) as batch_loop_group:
    batch_tasks = []

    # Create multiple batch processing tasks (simulating for-each loop)
    for batch_id in range(1, 4):  # Process 3 batches
        batch_task = PythonOperator(
            task_id=f'process_batch_{batch_id}',
            python_callable=process_batch,
            op_kwargs={'batch_id': batch_id},
            dag=dag,
        )
        batch_tasks.append(batch_task)

# Quality check with retry loop
quality_check = BranchPythonOperator(
    task_id='check_quality_and_retry', python_callable=check_quality_and_retry, dag=dag
)

retry_task = PythonOperator(
    task_id='retry_processing', python_callable=retry_failed_processing, dag=dag
)

quality_passed = PythonOperator(
    task_id='quality_passed', python_callable=quality_passed_func, dag=dag
)

# While loop simulation
check_completion = BranchPythonOperator(
    task_id='check_processing_complete',
    python_callable=check_processing_complete,
    dag=dag,
)

continue_processing = PythonOperator(
    task_id='continue_processing', python_callable=continue_batch_processing, dag=dag
)

processing_complete = PythonOperator(
    task_id='processing_complete', python_callable=processing_complete_func, dag=dag
)

# Define complex dependencies with loops
extract_task >> batch_loop_group

batch_loop_group >> [validate_customers_task, validate_orders_task]

validate_customers_task >> transform_customers_task
validate_orders_task >> transform_orders_task

[transform_customers_task, transform_orders_task] >> quality_check

# Quality check branches
quality_check >> [quality_passed, retry_task]

# Remove cyclic dependency - retry goes to quality_passed instead
retry_task >> quality_passed

quality_passed >> load_data_task

load_data_task >> check_completion

# While loop branches - proper while loop implementation
check_completion >> [processing_complete, continue_processing]

# Proper while loop - continue goes back to check condition
continue_processing >> check_completion

processing_complete >> [generate_report_task, send_notification_task]
