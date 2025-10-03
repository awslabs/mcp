from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.email import EmailOperator
from airflow.operators.python import PythonOperator
from airflow.providers.postgres.operators.postgres import PostgresOperator
from airflow.utils.trigger_rule import TriggerRule

default_args = {
    'owner': 'data-team',
    'depends_on_past': False,
    'start_date': datetime(2024, 1, 1),
    'email_on_failure': True,
    'email_on_retry': False,
    'email': ['data-team@company.com'],
    'retries': 3,
    'retry_delay': timedelta(minutes=5),
}

dag = DAG(
    '01_error_handling_complex',
    default_args=default_args,
    description='Complex ETL pipeline with comprehensive error handling',
    schedule_interval='@daily',
    catchup=False,
    tags=['etl', 'error-handling', 'complex'],
)


def log_pipeline_start(**context):
    """Log pipeline execution start"""
    print(f'Starting ETL pipeline at {datetime.now()}')
    return 'pipeline_started'


def handle_data_quality_issues(**context):
    """Handle data quality issues and log details"""
    print('Handling data quality issues and creating error report')
    # Error handling logic
    return 'quality_issues_handled'


def cleanup_staging_tables(**context):
    """Cleanup staging tables after processing"""
    print('Cleaning up staging tables and temporary data')
    return 'cleanup_complete'


start_logging = PythonOperator(
    task_id='log_pipeline_start', python_callable=log_pipeline_start, dag=dag
)

extract_source_data = PostgresOperator(
    task_id='extract_source_data',
    postgres_conn_id='source_db',
    sql="""
        CREATE TABLE staging.raw_transactions AS
        SELECT
            transaction_id,
            customer_id,
            amount,
            transaction_date,
            status,
            payment_method
        FROM source.transactions
        WHERE transaction_date >= CURRENT_DATE - INTERVAL '1 day'
    """,
    retries=5,
    retry_delay=timedelta(minutes=2),
    dag=dag,
)

validate_data_quality = PostgresOperator(
    task_id='validate_data_quality',
    postgres_conn_id='data_warehouse',
    sql="""
        CREATE TABLE staging.quality_check AS
        SELECT
            COUNT(*) as total_records,
            COUNT(CASE WHEN amount <= 0 THEN 1 END) as invalid_amounts,
            COUNT(CASE WHEN customer_id IS NULL THEN 1 END) as missing_customers,
            COUNT(CASE WHEN transaction_date IS NULL THEN 1 END) as missing_dates
        FROM staging.raw_transactions
    """,
    dag=dag,
)

transform_clean_data = PostgresOperator(
    task_id='transform_clean_data',
    postgres_conn_id='data_warehouse',
    sql="""
        CREATE TABLE staging.clean_transactions AS
        SELECT
            transaction_id,
            customer_id,
            CASE
                WHEN amount <= 0 THEN 0.01
                ELSE amount
            END as amount,
            COALESCE(transaction_date, CURRENT_DATE) as transaction_date,
            UPPER(TRIM(status)) as status,
            LOWER(TRIM(payment_method)) as payment_method
        FROM staging.raw_transactions
        WHERE customer_id IS NOT NULL
    """,
    dag=dag,
)

load_to_warehouse = PostgresOperator(
    task_id='load_to_warehouse',
    postgres_conn_id='data_warehouse',
    sql="""
        INSERT INTO warehouse.transactions
        SELECT * FROM staging.clean_transactions
        ON CONFLICT (transaction_id) DO UPDATE SET
            amount = EXCLUDED.amount,
            status = EXCLUDED.status,
            payment_method = EXCLUDED.payment_method
    """,
    dag=dag,
)

# Error handling tasks
handle_quality_issues = PythonOperator(
    task_id='handle_data_quality_issues',
    python_callable=handle_data_quality_issues,
    trigger_rule=TriggerRule.ONE_FAILED,
    dag=dag,
)

send_error_notification = EmailOperator(
    task_id='send_error_notification',
    to=['data-team@company.com', 'ops-team@company.com'],
    subject='ETL Pipeline Error - Immediate Attention Required',
    html_content="""
    <h3>ETL Pipeline Failure Alert</h3>
    <p>The daily ETL pipeline has encountered errors and requires immediate attention.</p>
    <p><strong>Pipeline:</strong> {{ dag.dag_id }}</p>
    <p><strong>Execution Date:</strong> {{ ds }}</p>
    <p><strong>Failed Tasks:</strong> Please check Airflow UI for details</p>
    """,
    trigger_rule=TriggerRule.ONE_FAILED,
    dag=dag,
)

# Cleanup tasks
cleanup_on_success = PythonOperator(
    task_id='cleanup_staging_success',
    python_callable=cleanup_staging_tables,
    trigger_rule=TriggerRule.ALL_SUCCESS,
    dag=dag,
)

cleanup_on_failure = BashOperator(
    task_id='cleanup_staging_failure',
    bash_command='echo "Performing emergency cleanup after pipeline failure"',
    trigger_rule=TriggerRule.ONE_FAILED,
    dag=dag,
)

# Define dependencies
(
    start_logging
    >> extract_source_data
    >> validate_data_quality
    >> transform_clean_data
    >> load_to_warehouse
)

# Success path
load_to_warehouse >> cleanup_on_success

# Error handling paths
[
    extract_source_data,
    validate_data_quality,
    transform_clean_data,
    load_to_warehouse,
] >> handle_quality_issues
[
    extract_source_data,
    validate_data_quality,
    transform_clean_data,
    load_to_warehouse,
] >> send_error_notification
[
    extract_source_data,
    validate_data_quality,
    transform_clean_data,
    load_to_warehouse,
] >> cleanup_on_failure
