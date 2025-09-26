from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator
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
    '03_advanced_loops_and_conditions',
    default_args=default_args,
    description='Advanced pipeline with for-each loops, while loops, and case-when logic',
    schedule_interval='@daily',
    catchup=False,
    tags=['etl', 'loops', 'conditions', 'advanced'],
)


def get_file_list(**context):
    """Get list of files to process"""
    # Simulate getting list of files
    files = [
        'customers_2024_01.csv',
        'customers_2024_02.csv',
        'customers_2024_03.csv',
        'transactions_2024_01.csv',
        'transactions_2024_02.csv',
        'transactions_2024_03.csv',
    ]
    return files


def process_file_batch(file_name, **context):
    """Process individual file in batch"""
    print(f'Processing file: {file_name}')

    # Simulate file processing logic
    if 'customers' in file_name:
        return f'Processed customer file: {file_name}'
    elif 'transactions' in file_name:
        return f'Processed transaction file: {file_name}'
    else:
        return f'Processed unknown file: {file_name}'


def check_data_quality(**context):
    """Check data quality and return retry decision"""
    import random

    quality_score = random.uniform(0.7, 1.0)

    if quality_score >= 0.95:
        return 'quality_passed'
    else:
        return 'quality_failed'


def retry_processing(**context):
    """Retry processing with improved parameters"""
    print('Retrying processing with improved parameters')
    return 'retry_complete'


# Get list of files to process
get_files = PythonOperator(task_id='get_file_list', python_callable=get_file_list, dag=dag)

# For-each loop simulation using TaskGroup
with TaskGroup('process_files_loop', dag=dag) as process_files_group:
    # Simulate for-each loop by creating multiple tasks
    file_processing_tasks = []

    for i, file_name in enumerate(
        ['customers_2024_01.csv', 'customers_2024_02.csv', 'transactions_2024_01.csv']
    ):
        process_task = PythonOperator(
            task_id=f'process_file_{i}',
            python_callable=process_file_batch,
            op_kwargs={'file_name': file_name},
            dag=dag,
        )

        file_processing_tasks.append(process_task)

# Complex case-when logic in SQL
complex_case_when_transform = PostgresOperator(
    task_id='complex_case_when_transform',
    postgres_conn_id='data_warehouse',
    sql="""
        CREATE TABLE processed.customer_segments AS
        SELECT
            customer_id,
            name,
            total_spent,
            transaction_count,
            last_purchase_date,

            -- Complex case-when for customer segmentation
            CASE
                WHEN total_spent > 50000 AND transaction_count > 100 THEN 'VIP_FREQUENT'
                WHEN total_spent > 50000 AND transaction_count <= 100 THEN 'VIP_OCCASIONAL'
                WHEN total_spent > 20000 AND transaction_count > 50 THEN 'PREMIUM_FREQUENT'
                WHEN total_spent > 20000 AND transaction_count <= 50 THEN 'PREMIUM_OCCASIONAL'
                WHEN total_spent > 5000 AND transaction_count > 20 THEN 'STANDARD_FREQUENT'
                WHEN total_spent > 5000 AND transaction_count <= 20 THEN 'STANDARD_OCCASIONAL'
                WHEN total_spent > 1000 THEN 'BASIC_ACTIVE'
                WHEN last_purchase_date > CURRENT_DATE - INTERVAL '30 days' THEN 'BASIC_RECENT'
                ELSE 'INACTIVE'
            END as customer_segment,

            -- Nested case-when for risk assessment
            CASE
                WHEN customer_segment IN ('VIP_FREQUENT', 'VIP_OCCASIONAL') THEN
                    CASE
                        WHEN last_purchase_date > CURRENT_DATE - INTERVAL '7 days' THEN 'LOW_RISK'
                        WHEN last_purchase_date > CURRENT_DATE - INTERVAL '30 days' THEN 'MEDIUM_RISK'
                        ELSE 'HIGH_RISK'
                    END
                WHEN customer_segment IN ('PREMIUM_FREQUENT', 'PREMIUM_OCCASIONAL') THEN
                    CASE
                        WHEN last_purchase_date > CURRENT_DATE - INTERVAL '14 days' THEN 'LOW_RISK'
                        WHEN last_purchase_date > CURRENT_DATE - INTERVAL '60 days' THEN 'MEDIUM_RISK'
                        ELSE 'HIGH_RISK'
                    END
                ELSE 'STANDARD_RISK'
            END as churn_risk,

            -- Case-when for recommended actions
            CASE
                WHEN customer_segment = 'VIP_FREQUENT' AND churn_risk = 'HIGH_RISK' THEN 'URGENT_RETENTION'
                WHEN customer_segment LIKE 'VIP_%' THEN 'VIP_ENGAGEMENT'
                WHEN customer_segment LIKE 'PREMIUM_%' THEN 'PREMIUM_UPSELL'
                WHEN customer_segment LIKE 'STANDARD_%' THEN 'STANDARD_NURTURE'
                WHEN customer_segment = 'BASIC_ACTIVE' THEN 'BASIC_UPGRADE'
                WHEN customer_segment = 'BASIC_RECENT' THEN 'REACTIVATION'
                ELSE 'NO_ACTION'
            END as recommended_action

        FROM staging.customer_metrics
        WHERE processing_date = CURRENT_DATE
    """,
    dag=dag,
)


# While loop simulation using recursive task pattern
def check_processing_complete(**context):
    """Check if processing is complete (while loop condition)"""
    import random

    # Simulate checking if all data is processed
    completion_rate = random.uniform(0.6, 1.0)

    if completion_rate >= 0.95:
        print(f'Processing complete! Completion rate: {completion_rate:.2%}')
        return 'processing_complete'
    else:
        print(f'Processing incomplete. Completion rate: {completion_rate:.2%}')
        return 'continue_processing'


def continue_batch_processing(**context):
    """Continue processing next batch (while loop body)"""
    print('Processing next batch of data...')

    # Simulate batch processing
    # batch_sql = """
    #     INSERT INTO processed.incremental_data
    #     SELECT * FROM staging.pending_data
    #     WHERE batch_id = (
    #         SELECT MIN(batch_id)
    #         FROM staging.pending_data
    #         WHERE processed = false
    #     )
    # """  # Unused variable

    return 'batch_processed'


# While loop simulation
check_completion = PythonOperator(
    task_id='check_processing_complete',
    python_callable=check_processing_complete,
    dag=dag,
)

continue_processing = PythonOperator(
    task_id='continue_batch_processing',
    python_callable=continue_batch_processing,
    dag=dag,
)

# Quality check with retry loop
quality_check = PythonOperator(
    task_id='check_data_quality', python_callable=check_data_quality, dag=dag
)

retry_task = PythonOperator(task_id='retry_processing', python_callable=retry_processing, dag=dag)

# Advanced conditional SQL with multiple case-when statements
advanced_analytics = PostgresOperator(
    task_id='advanced_analytics_with_case_when',
    postgres_conn_id='data_warehouse',
    sql="""
        CREATE TABLE analytics.advanced_customer_insights AS
        WITH customer_behavior AS (
            SELECT
                customer_id,
                customer_segment,
                churn_risk,
                recommended_action,

                -- Time-based case-when analysis
                CASE
                    WHEN EXTRACT(HOUR FROM last_purchase_time) BETWEEN 9 AND 17 THEN 'BUSINESS_HOURS'
                    WHEN EXTRACT(HOUR FROM last_purchase_time) BETWEEN 18 AND 22 THEN 'EVENING'
                    WHEN EXTRACT(HOUR FROM last_purchase_time) BETWEEN 23 AND 6 THEN 'NIGHT'
                    ELSE 'EARLY_MORNING'
                END as purchase_time_pattern,

                -- Seasonal case-when analysis
                CASE
                    WHEN EXTRACT(MONTH FROM last_purchase_date) IN (12, 1, 2) THEN 'WINTER'
                    WHEN EXTRACT(MONTH FROM last_purchase_date) IN (3, 4, 5) THEN 'SPRING'
                    WHEN EXTRACT(MONTH FROM last_purchase_date) IN (6, 7, 8) THEN 'SUMMER'
                    ELSE 'FALL'
                END as seasonal_pattern,

                -- Geographic case-when analysis
                CASE
                    WHEN customer_region IN ('NY', 'CA', 'TX', 'FL') THEN 'HIGH_POPULATION_STATE'
                    WHEN customer_region IN ('WY', 'VT', 'AK', 'ND') THEN 'LOW_POPULATION_STATE'
                    ELSE 'MEDIUM_POPULATION_STATE'
                END as geographic_segment

            FROM processed.customer_segments
        ),

        behavioral_scoring AS (
            SELECT
                *,
                -- Complex scoring with nested case-when
                (CASE
                    WHEN customer_segment = 'VIP_FREQUENT' THEN 100
                    WHEN customer_segment = 'VIP_OCCASIONAL' THEN 90
                    WHEN customer_segment = 'PREMIUM_FREQUENT' THEN 80
                    WHEN customer_segment = 'PREMIUM_OCCASIONAL' THEN 70
                    WHEN customer_segment = 'STANDARD_FREQUENT' THEN 60
                    WHEN customer_segment = 'STANDARD_OCCASIONAL' THEN 50
                    WHEN customer_segment = 'BASIC_ACTIVE' THEN 40
                    WHEN customer_segment = 'BASIC_RECENT' THEN 30
                    ELSE 10
                END +
                CASE
                    WHEN churn_risk = 'LOW_RISK' THEN 20
                    WHEN churn_risk = 'MEDIUM_RISK' THEN 10
                    WHEN churn_risk = 'HIGH_RISK' THEN -10
                    ELSE 0
                END +
                CASE
                    WHEN purchase_time_pattern = 'BUSINESS_HOURS' THEN 5
                    WHEN purchase_time_pattern = 'EVENING' THEN 3
                    ELSE 0
                END) as customer_score

            FROM customer_behavior
        )

        SELECT
            *,
            -- Final case-when for customer tier based on composite score
            CASE
                WHEN customer_score >= 110 THEN 'PLATINUM'
                WHEN customer_score >= 90 THEN 'GOLD'
                WHEN customer_score >= 70 THEN 'SILVER'
                WHEN customer_score >= 50 THEN 'BRONZE'
                ELSE 'STANDARD'
            END as final_customer_tier

        FROM behavioral_scoring
    """,
    dag=dag,
)

# Define the correct sequential dependencies
(
    get_files
    >> process_files_group
    >> complex_case_when_transform
    >> check_completion
    >> continue_processing
    >> quality_check
    >> retry_task
    >> advanced_analytics
)
