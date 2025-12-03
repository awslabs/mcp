from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import BranchPythonOperator, PythonOperator

default_args = {
    'owner': 'data-team',
    'depends_on_past': False,
    'start_date': datetime(2024, 1, 1),
    'email_on_failure': False,
    'retries': 2,
    'retry_delay': timedelta(minutes=10),
}

dag = DAG(
    '06_sensor_retry_loops',
    default_args=default_args,
    description='Pipeline with sensor-based retry loops - realistic sensor patterns',
    schedule_interval='0 3 * * *',
    catchup=False,
    tags=['etl', 'sensors', 'retry', 'realistic'],
)


def check_file_availability(**context):
    """Check if required files are available"""
    import random

    files_ready = random.choice([True, False])

    if files_ready:
        print('All required files are available')
        return 'files_ready'
    else:
        print('Files not ready - wait and retry')
        return 'wait_for_files'


def wait_for_files(**context):
    """Wait before checking files again"""
    print('Waiting 10 minutes for files to arrive')
    return 'wait_completed'


def process_files(**context):
    """Process the available files"""
    print('Processing available files')
    return 'files_processed'


def check_database_connection(**context):
    """Check if database is accessible"""
    import random

    db_ready = random.choice([True, False])

    if db_ready:
        print('Database connection successful')
        return 'database_ready'
    else:
        print('Database connection failed - retry')
        return 'retry_database_connection'


def retry_database_setup(**context):
    """Retry database connection setup"""
    print('Retrying database connection with different parameters')
    return 'retry_completed'


def load_to_database(**context):
    """Load processed data to database"""
    print('Loading data to database')
    return 'data_loaded'


def check_downstream_system(**context):
    """Check if downstream system is ready for data"""
    import random

    downstream_ready = random.choice([True, False])

    if downstream_ready:
        print('Downstream system ready')
        return 'downstream_ready'
    else:
        print('Downstream system busy - wait and retry')
        return 'wait_for_downstream'


def wait_for_downstream(**context):
    """Wait for downstream system to be ready"""
    print('Waiting for downstream system to be available')
    return 'wait_completed'


def trigger_downstream(**context):
    """Trigger downstream processing"""
    print('Triggering downstream system processing')
    return 'downstream_triggered'


def validate_end_to_end(**context):
    """Validate the entire pipeline end-to-end"""
    import random

    validation_passed = random.choice([True, False])

    if validation_passed:
        print('End-to-end validation passed')
        return 'validation_passed'
    else:
        print('End-to-end validation failed - restart pipeline')
        return 'restart_pipeline'


def restart_pipeline(**context):
    """Restart the entire pipeline from file check"""
    print('Restarting pipeline due to validation failure')
    return 'restart_initiated'


def complete_pipeline(**context):
    """Complete the pipeline successfully"""
    print('Pipeline completed successfully')
    return 'pipeline_complete'


# Define tasks
file_check = BranchPythonOperator(
    task_id='check_file_availability', python_callable=check_file_availability, dag=dag
)

wait_files = PythonOperator(task_id='wait_for_files', python_callable=wait_for_files, dag=dag)

process_task = PythonOperator(task_id='process_files', python_callable=process_files, dag=dag)

db_check = BranchPythonOperator(
    task_id='check_database_connection',
    python_callable=check_database_connection,
    dag=dag,
)

retry_db = PythonOperator(
    task_id='retry_database_setup', python_callable=retry_database_setup, dag=dag
)

load_task = PythonOperator(task_id='load_to_database', python_callable=load_to_database, dag=dag)

downstream_check = BranchPythonOperator(
    task_id='check_downstream_system', python_callable=check_downstream_system, dag=dag
)

wait_downstream = PythonOperator(
    task_id='wait_for_downstream', python_callable=wait_for_downstream, dag=dag
)

trigger_task = PythonOperator(
    task_id='trigger_downstream', python_callable=trigger_downstream, dag=dag
)

validation_check = BranchPythonOperator(
    task_id='validate_end_to_end', python_callable=validate_end_to_end, dag=dag
)

restart_task = PythonOperator(
    task_id='restart_pipeline', python_callable=restart_pipeline, dag=dag
)

complete_task = PythonOperator(
    task_id='complete_pipeline', python_callable=complete_pipeline, dag=dag
)

# Define dependencies with multiple retry loops

# File availability retry loop
file_check >> [process_task, wait_files]
wait_files >> file_check  # LOOPS BACK to check files again

process_task >> db_check

# Database connection retry loop
db_check >> [load_task, retry_db]
retry_db >> db_check  # LOOPS BACK to retry database connection

load_task >> downstream_check

# Downstream system retry loop
downstream_check >> [trigger_task, wait_downstream]
wait_downstream >> downstream_check  # LOOPS BACK to check downstream again

trigger_task >> validation_check

# End-to-end validation retry loop (restarts entire pipeline)
validation_check >> [complete_task, restart_task]
restart_task >> file_check  # LOOPS BACK to beginning of pipeline
