from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import BranchPythonOperator, PythonOperator

default_args = {
    'owner': 'data-team',
    'depends_on_past': False,
    'start_date': datetime(2024, 1, 1),
    'email_on_failure': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

dag = DAG(
    '05_manual_retry_loops',
    default_args=default_args,
    description='Pipeline with manual retry loops - realistic retry patterns',
    schedule_interval='0 2 * * *',
    catchup=False,
    tags=['etl', 'retry', 'loops', 'realistic'],
)


def extract_data(**context):
    """Extract data from source"""
    print('Extracting data from source systems')
    return 'data_extracted'


def validate_data_quality(**context):
    """Check data quality and decide if retry is needed"""
    import random

    quality_score = random.uniform(0.5, 1.0)

    if quality_score >= 0.8:
        print(f'Data quality passed: {quality_score:.2f}')
        return 'process_data_successfully'
    else:
        print(f'Data quality failed: {quality_score:.2f} - retry needed')
        return 'retry_data_processing'


def retry_data_processing(**context):
    """Retry data processing with improved parameters"""
    print('Retrying data processing with improved parameters')
    # Simulate processing improvements
    return 'retry_completed'


def process_data_successfully(**context):
    """Process data after quality check passes"""
    print('Processing data successfully')
    return 'data_processed'


def check_external_system(**context):
    """Check if external system is ready"""
    import random

    system_ready = random.choice([True, False])

    if system_ready:
        print('External system is ready')
        return 'load_to_external_system'
    else:
        print('External system not ready - wait and retry')
        return 'wait_for_system'


def wait_for_system(**context):
    """Wait before retrying external system check"""
    print('Waiting 5 minutes before retrying external system check')
    return 'wait_completed'


def load_to_external_system(**context):
    """Load data to external system"""
    print('Loading data to external system')
    return 'data_loaded'


def finalize_pipeline(**context):
    """Finalize the pipeline"""
    print('Pipeline completed successfully')
    return 'pipeline_complete'


# Define tasks
extract_task = PythonOperator(task_id='extract_data', python_callable=extract_data, dag=dag)

# Quality check with manual retry loop
quality_check = BranchPythonOperator(
    task_id='validate_data_quality', python_callable=validate_data_quality, dag=dag
)

retry_processing = PythonOperator(
    task_id='retry_data_processing', python_callable=retry_data_processing, dag=dag
)

quality_passed = PythonOperator(
    task_id='process_data_successfully',
    python_callable=process_data_successfully,
    dag=dag,
)

# External system check with retry loop
system_check = BranchPythonOperator(
    task_id='check_external_system', python_callable=check_external_system, dag=dag
)

wait_task = PythonOperator(task_id='wait_for_system', python_callable=wait_for_system, dag=dag)

load_task = PythonOperator(
    task_id='load_to_external_system', python_callable=load_to_external_system, dag=dag
)

finalize_task = PythonOperator(
    task_id='finalize_pipeline', python_callable=finalize_pipeline, dag=dag
)

# Define dependencies with proper retry loops
extract_task >> quality_check

# Quality retry loop - PROPER LOOP BACK
quality_check >> [quality_passed, retry_processing]
retry_processing >> quality_check  # LOOPS BACK to retry quality check

quality_passed >> system_check

# External system retry loop - PROPER LOOP BACK
system_check >> [load_task, wait_task]
wait_task >> system_check  # LOOPS BACK to retry system check

load_task >> finalize_task
