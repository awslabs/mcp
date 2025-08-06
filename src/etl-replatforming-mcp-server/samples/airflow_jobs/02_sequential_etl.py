from datetime import datetime, timedelta
from airflow import DAG
from airflow.providers.postgres.operators.postgres import PostgresOperator
from airflow.operators.python import PythonOperator

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
    'sequential_etl_pipeline',
    default_args=default_args,
    description='Sequential ETL pipeline with extract, transform, load',
    schedule_interval='@daily',
    catchup=False,
    tags=['etl', 'sequential']
)

def validate_data(**context):
    """Validate extracted data quality"""
    print("Validating data quality and completeness")
    # Data validation logic here
    return "validation_passed"

extract_raw_data = PostgresOperator(
    task_id='extract_raw_data',
    postgres_conn_id='source_db',
    sql="""
        CREATE TABLE staging.raw_customers AS
        SELECT customer_id, name, email, phone, address, created_date
        FROM source.customers
        WHERE created_date >= CURRENT_DATE - INTERVAL '1 day'
    """,
    dag=dag
)

transform_data = PostgresOperator(
    task_id='transform_data',
    postgres_conn_id='data_warehouse',
    sql="""
        CREATE TABLE staging.clean_customers AS
        SELECT 
            customer_id,
            UPPER(TRIM(name)) as name,
            LOWER(TRIM(email)) as email,
            REGEXP_REPLACE(phone, '[^0-9]', '', 'g') as phone,
            TRIM(address) as address,
            created_date
        FROM staging.raw_customers
        WHERE email IS NOT NULL AND email LIKE '%@%'
    """,
    dag=dag
)

validate_quality = PythonOperator(
    task_id='validate_quality',
    python_callable=validate_data,
    dag=dag
)

load_to_warehouse = PostgresOperator(
    task_id='load_to_warehouse',
    postgres_conn_id='data_warehouse',
    sql="""
        INSERT INTO warehouse.customers
        SELECT * FROM staging.clean_customers
        ON CONFLICT (customer_id) DO UPDATE SET
            name = EXCLUDED.name,
            email = EXCLUDED.email,
            phone = EXCLUDED.phone,
            address = EXCLUDED.address
    """,
    dag=dag
)

# Define dependencies
extract_raw_data >> transform_data >> validate_quality >> load_to_warehouse