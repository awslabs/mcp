from datetime import datetime, timedelta
from airflow import DAG
from airflow.providers.postgres.operators.postgres import PostgresOperator
from airflow.utils.task_group import TaskGroup

default_args = {
    'owner': 'data-team',
    'depends_on_past': False,
    'start_date': datetime(2024, 1, 1),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 3,
    'retry_delay': timedelta(minutes=5)
}

dag = DAG(
    'parallel_data_processing_pipeline',
    default_args=default_args,
    description='Parallel data processing pipeline',
    schedule_interval='@daily',
    catchup=False,
    tags=['etl', 'parallel']
)

# Parallel processing task group
with TaskGroup("parallel_processing", dag=dag) as parallel_group:
    
    process_customers = PostgresOperator(
        task_id='process_customers',
        postgres_conn_id='data_warehouse',
        sql="""
            CREATE TABLE processed.customers AS
            SELECT 
                customer_id, 
                name, 
                email,
                CASE 
                    WHEN last_purchase_date > CURRENT_DATE - INTERVAL '30 days' 
                    THEN 'Active' 
                    ELSE 'Inactive' 
                END as status
            FROM raw.customers
        """
    )
    
    process_orders = PostgresOperator(
        task_id='process_orders',
        postgres_conn_id='data_warehouse',
        sql="""
            CREATE TABLE processed.orders AS
            SELECT 
                order_id,
                customer_id,
                total_amount,
                order_date,
                EXTRACT(MONTH FROM order_date) as order_month
            FROM raw.orders
            WHERE order_date >= CURRENT_DATE - INTERVAL '1 year'
        """
    )
    
    process_products = PostgresOperator(
        task_id='process_products',
        postgres_conn_id='data_warehouse',
        sql="""
            CREATE TABLE processed.products AS
            SELECT 
                product_id,
                name,
                category,
                price,
                CASE 
                    WHEN price > 100 THEN 'Premium'
                    WHEN price > 50 THEN 'Standard'
                    ELSE 'Budget'
                END as product_tier
            FROM raw.products
        """
    )

combine_results = PostgresOperator(
    task_id='combine_results',
    postgres_conn_id='data_warehouse',
    sql="""
        CREATE TABLE analytics.customer_order_summary AS
        SELECT 
            c.customer_id,
            c.name,
            c.status,
            COUNT(o.order_id) as total_orders,
            SUM(o.total_amount) as total_spent
        FROM processed.customers c
        LEFT JOIN processed.orders o ON c.customer_id = o.customer_id
        GROUP BY c.customer_id, c.name, c.status
    """,
    dag=dag
)

# Define dependencies
parallel_group >> combine_results