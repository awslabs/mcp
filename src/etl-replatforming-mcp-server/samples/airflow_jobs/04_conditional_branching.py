from datetime import datetime, timedelta
from airflow import DAG
from airflow.providers.postgres.operators.postgres import PostgresOperator
from airflow.operators.python import PythonOperator, BranchPythonOperator
from airflow.operators.dummy import DummyOperator

default_args = {
    'owner': 'data-team',
    'depends_on_past': False,
    'start_date': datetime(2024, 1, 1),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 2,
    'retry_delay': timedelta(minutes=5)
}

dag = DAG(
    'conditional_data_pipeline',
    default_args=default_args,
    description='Conditional data pipeline with branching logic',
    schedule_interval='@daily',
    catchup=False,
    tags=['etl', 'conditional']
)

def check_data_volume(**context):
    """Check data volume to determine processing path"""
    # Simulate data volume check
    import random
    record_count = random.randint(1000, 50000)
    
    if record_count > 10000:
        return 'high_volume_processing'
    else:
        return 'standard_processing'

def validate_business_rules(**context):
    """Validate business rules and data quality"""
    print("Validating business rules and data quality")
    # Business validation logic
    return "validation_complete"

check_volume = BranchPythonOperator(
    task_id='check_data_volume',
    python_callable=check_data_volume,
    dag=dag
)

standard_processing = PostgresOperator(
    task_id='standard_processing',
    postgres_conn_id='data_warehouse',
    sql="""
        CREATE TABLE processed.standard_customers AS
        SELECT 
            customer_id,
            name,
            email,
            registration_date,
            'standard' as processing_type
        FROM raw.customers
        WHERE registration_date >= CURRENT_DATE - INTERVAL '1 day'
    """,
    dag=dag
)

high_volume_processing = PostgresOperator(
    task_id='high_volume_processing',
    postgres_conn_id='data_warehouse',
    sql="""
        CREATE TABLE processed.batch_customers AS
        SELECT 
            customer_id,
            name,
            email,
            registration_date,
            'batch' as processing_type
        FROM raw.customers
        WHERE registration_date >= CURRENT_DATE - INTERVAL '1 day'
    """,
    dag=dag
)

# Convergence point
join_processing = DummyOperator(
    task_id='join_processing',
    trigger_rule='none_failed_or_skipped',
    dag=dag
)

validate_results = PythonOperator(
    task_id='validate_results',
    python_callable=validate_business_rules,
    dag=dag
)

generate_report = PostgresOperator(
    task_id='generate_report',
    postgres_conn_id='data_warehouse',
    sql="""
        CREATE TABLE reports.daily_customer_report AS
        SELECT 
            processing_type,
            COUNT(*) as customer_count,
            MIN(registration_date) as earliest_registration,
            MAX(registration_date) as latest_registration,
            CURRENT_TIMESTAMP as report_generated
        FROM (
            SELECT * FROM processed.standard_customers
            UNION ALL
            SELECT * FROM processed.batch_customers
        ) combined
        GROUP BY processing_type
    """,
    dag=dag
)

# Define dependencies
check_volume >> [standard_processing, high_volume_processing]
[standard_processing, high_volume_processing] >> join_processing
join_processing >> validate_results >> generate_report