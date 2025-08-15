from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.dummy import DummyOperator
from airflow.operators.email import EmailOperator
from airflow.operators.python import BranchPythonOperator, PythonOperator
from airflow.providers.postgres.operators.postgres import PostgresOperator
from airflow.sensors.filesystem import FileSensor
from airflow.utils.task_group import TaskGroup
from airflow.utils.trigger_rule import TriggerRule

default_args = {
    'owner': 'data-engineering-team',
    'depends_on_past': False,
    'start_date': datetime(2024, 1, 1),
    'email_on_failure': True,
    'email_on_retry': False,
    'email': ['data-eng@company.com', 'ops@company.com'],
    'retries': 3,
    'retry_delay': timedelta(minutes=10),
}

dag = DAG(
    '02_extremely_complex_pipeline',
    default_args=default_args,
    description='Extremely complex multi-source ETL pipeline with dynamic scaling and monitoring',
    schedule_interval='0 2 * * *',  # Daily at 2 AM
    catchup=False,
    max_active_runs=1,
    tags=['etl', 'complex', 'multi-source', 'production'],
)


def determine_processing_strategy(**context):
    """Determine processing strategy based on data volume and system load"""
    import random

    data_volume = random.randint(100000, 5000000)
    system_load = random.uniform(0.3, 0.9)

    if data_volume > 1000000 and system_load < 0.7:
        return 'high_performance_processing'
    elif data_volume > 500000:
        return 'standard_batch_processing'
    else:
        return 'lightweight_processing'


def monitor_system_resources(**context):
    """Monitor system resources and adjust processing parameters"""
    print('Monitoring system resources and adjusting processing parameters')
    return 'monitoring_complete'


def generate_data_lineage(**context):
    """Generate data lineage and quality metrics"""
    print('Generating data lineage documentation and quality metrics')
    return 'lineage_generated'


# File sensors for different data sources
wait_for_customer_data = FileSensor(
    task_id='wait_for_customer_data',
    filepath='/data/incoming/customers_{{ ds }}.csv',
    fs_conn_id='data_filesystem',
    poke_interval=300,
    timeout=3600,
    dag=dag,
)

wait_for_transaction_data = FileSensor(
    task_id='wait_for_transaction_data',
    filepath='/data/incoming/transactions_{{ ds }}.csv',
    fs_conn_id='data_filesystem',
    poke_interval=300,
    timeout=3600,
    dag=dag,
)

wait_for_product_data = FileSensor(
    task_id='wait_for_product_data',
    filepath='/data/incoming/products_{{ ds }}.csv',
    fs_conn_id='data_filesystem',
    poke_interval=300,
    timeout=3600,
    dag=dag,
)

# Dynamic processing strategy
determine_strategy = BranchPythonOperator(
    task_id='determine_processing_strategy',
    python_callable=determine_processing_strategy,
    dag=dag,
)

# High performance processing path
with TaskGroup('high_performance_processing', dag=dag) as high_perf_group:
    parallel_extract_hp = [
        PostgresOperator(
            task_id='extract_customers_hp',
            postgres_conn_id='source_db_cluster',
            sql="""
                CREATE TABLE staging.customers_hp AS
                SELECT * FROM source.customers
                WHERE last_modified >= CURRENT_DATE - INTERVAL '1 day'
            """,
            pool='high_performance_pool',
        ),
        PostgresOperator(
            task_id='extract_transactions_hp',
            postgres_conn_id='source_db_cluster',
            sql="""
                CREATE TABLE staging.transactions_hp AS
                SELECT * FROM source.transactions
                WHERE transaction_date >= CURRENT_DATE - INTERVAL '1 day'
            """,
            pool='high_performance_pool',
        ),
        PostgresOperator(
            task_id='extract_products_hp',
            postgres_conn_id='source_db_cluster',
            sql="""
                CREATE TABLE staging.products_hp AS
                SELECT * FROM source.products
                WHERE last_updated >= CURRENT_DATE - INTERVAL '1 day'
            """,
            pool='high_performance_pool',
        ),
    ]

# Standard batch processing path
with TaskGroup('standard_batch_processing', dag=dag) as standard_group:
    sequential_extract_std = PostgresOperator(
        task_id='extract_all_data_std',
        postgres_conn_id='source_db',
        sql="""
            CREATE TABLE staging.combined_data_std AS
            SELECT 'customer' as source_type, customer_id as id, name as description
            FROM source.customers
            WHERE last_modified >= CURRENT_DATE - INTERVAL '1 day'
            UNION ALL
            SELECT 'transaction' as source_type, transaction_id as id,
                   CAST(amount AS VARCHAR) as description
            FROM source.transactions
            WHERE transaction_date >= CURRENT_DATE - INTERVAL '1 day'
            UNION ALL
            SELECT 'product' as source_type, product_id as id, product_name as description
            FROM source.products
            WHERE last_updated >= CURRENT_DATE - INTERVAL '1 day'
        """,
    )

# Lightweight processing path
lightweight_processing = PostgresOperator(
    task_id='lightweight_processing',
    postgres_conn_id='source_db',
    sql="""
        CREATE TABLE staging.summary_data AS
        SELECT
            COUNT(DISTINCT customer_id) as customer_count,
            COUNT(DISTINCT transaction_id) as transaction_count,
            COUNT(DISTINCT product_id) as product_count,
            CURRENT_TIMESTAMP as processed_at
        FROM source.daily_summary
        WHERE summary_date = CURRENT_DATE
    """,
    dag=dag,
)

# Convergence point
join_processing_paths = DummyOperator(
    task_id='join_processing_paths',
    trigger_rule=TriggerRule.NONE_FAILED_OR_SKIPPED,
    dag=dag,
)

# Advanced data transformation with monitoring
with TaskGroup('advanced_transformations', dag=dag) as transform_group:
    monitor_resources = PythonOperator(
        task_id='monitor_system_resources', python_callable=monitor_system_resources
    )

    complex_aggregations = PostgresOperator(
        task_id='complex_aggregations',
        postgres_conn_id='data_warehouse',
        sql="""
            CREATE TABLE analytics.complex_metrics AS
            WITH customer_metrics AS (
                SELECT
                    customer_id,
                    COUNT(*) as transaction_count,
                    SUM(amount) as total_spent,
                    AVG(amount) as avg_transaction,
                    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY amount) as median_transaction
                FROM staging.transactions_hp
                GROUP BY customer_id
            ),
            product_performance AS (
                SELECT
                    product_id,
                    COUNT(*) as sales_count,
                    SUM(quantity * price) as revenue,
                    AVG(rating) as avg_rating
                FROM staging.products_hp p
                JOIN staging.transactions_hp t ON p.product_id = t.product_id
                GROUP BY product_id
            )
            SELECT
                cm.*,
                pp.sales_count,
                pp.revenue,
                pp.avg_rating,
                CASE
                    WHEN cm.total_spent > 10000 THEN 'VIP'
                    WHEN cm.total_spent > 5000 THEN 'Premium'
                    WHEN cm.total_spent > 1000 THEN 'Standard'
                    ELSE 'Basic'
                END as customer_tier
            FROM customer_metrics cm
            LEFT JOIN product_performance pp ON cm.customer_id = pp.product_id
        """,
    )

    generate_lineage = PythonOperator(
        task_id='generate_data_lineage', python_callable=generate_data_lineage
    )

# Data quality and validation
data_quality_checks = PostgresOperator(
    task_id='comprehensive_data_quality_checks',
    postgres_conn_id='data_warehouse',
    sql="""
        CREATE TABLE quality.daily_quality_report AS
        SELECT
            'completeness' as check_type,
            COUNT(*) as total_records,
            COUNT(CASE WHEN customer_id IS NULL THEN 1 END) as null_customers,
            COUNT(CASE WHEN amount IS NULL OR amount <= 0 THEN 1 END) as invalid_amounts,
            CURRENT_TIMESTAMP as check_timestamp
        FROM analytics.complex_metrics
        UNION ALL
        SELECT
            'consistency' as check_type,
            COUNT(*) as total_records,
            COUNT(CASE WHEN customer_tier NOT IN ('VIP', 'Premium', 'Standard', 'Basic') THEN 1 END) as invalid_tiers,
            COUNT(CASE WHEN avg_rating < 0 OR avg_rating > 5 THEN 1 END) as invalid_ratings,
            CURRENT_TIMESTAMP as check_timestamp
        FROM analytics.complex_metrics
    """,
    dag=dag,
)

# Final reporting and notifications
generate_executive_report = PostgresOperator(
    task_id='generate_executive_report',
    postgres_conn_id='data_warehouse',
    sql="""
        CREATE TABLE reports.executive_dashboard AS
        SELECT
            COUNT(DISTINCT customer_id) as total_customers,
            SUM(total_spent) as total_revenue,
            AVG(total_spent) as avg_customer_value,
            COUNT(CASE WHEN customer_tier = 'VIP' THEN 1 END) as vip_customers,
            COUNT(CASE WHEN customer_tier = 'Premium' THEN 1 END) as premium_customers,
            CURRENT_DATE as report_date,
            CURRENT_TIMESTAMP as generated_at
        FROM analytics.complex_metrics
    """,
    dag=dag,
)

send_success_notification = EmailOperator(
    task_id='send_success_notification',
    to=['executives@company.com', 'data-team@company.com'],
    subject='Daily ETL Pipeline - Successful Completion',
    html_content="""
    <h2>Daily ETL Pipeline Completed Successfully</h2>
    <p><strong>Pipeline:</strong> {{ dag.dag_id }}</p>
    <p><strong>Execution Date:</strong> {{ ds }}</p>
    <p><strong>Duration:</strong> {{ dag_run.duration }}</p>
    <p><strong>Records Processed:</strong> Check executive dashboard for details</p>
    <p><strong>Data Quality:</strong> All quality checks passed</p>
    """,
    trigger_rule=TriggerRule.ALL_SUCCESS,
    dag=dag,
)

# Error handling and cleanup
cleanup_on_failure = BashOperator(
    task_id='emergency_cleanup',
    bash_command="""
    echo "Performing emergency cleanup..."
    # Cleanup staging tables
    # Reset system resources
    # Log failure details
    """,
    trigger_rule=TriggerRule.ONE_FAILED,
    dag=dag,
)

# Define complex dependencies
[
    wait_for_customer_data,
    wait_for_transaction_data,
    wait_for_product_data,
] >> determine_strategy

determine_strategy >> [high_perf_group, standard_group, lightweight_processing]

[high_perf_group, standard_group, lightweight_processing] >> join_processing_paths

(join_processing_paths >> transform_group >> data_quality_checks >> generate_executive_report)

generate_executive_report >> send_success_notification

# Error handling for all main tasks
[
    determine_strategy,
    high_perf_group,
    standard_group,
    lightweight_processing,
    transform_group,
    data_quality_checks,
    generate_executive_report,
] >> cleanup_on_failure
