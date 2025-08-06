from datetime import datetime, timedelta
from airflow import DAG
from airflow.providers.postgres.operators.postgres import PostgresOperator

default_args = {
    'owner': 'data-team',
    'depends_on_past': False,
    'start_date': datetime(2024, 1, 1),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 3,
    'retry_delay': timedelta(seconds=30)
}

dag = DAG(
    'simple_sql_extract',
    default_args=default_args,
    description='Simple SQL data extraction pipeline',
    schedule_interval='@daily',
    catchup=False,
    tags=['etl', 'simple']
)

extract_customers = PostgresOperator(
    task_id='extract_customers',
    postgres_conn_id='data_warehouse',
    sql="""
        SELECT customer_id, name, email, created_date 
        FROM customers 
        WHERE created_date >= CURRENT_DATE - INTERVAL '1 day'
    """,
    dag=dag
)