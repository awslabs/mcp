"""Expert guidance prompts for MWAA and Airflow best practices."""

AIRFLOW_BEST_PRACTICES = """
# MWAA and Apache Airflow Best Practices Guide

## Environment Setup and Configuration

### 1. MWAA Environment Sizing
- **Start Small**: Begin with mw1.small and scale up based on actual usage
- **Monitor Metrics**: Use CloudWatch metrics to track worker utilization
- **Auto-scaling**: Configure min/max workers appropriately (typically 1-10 for most workloads)
- **Scheduler Count**: Use 2 schedulers for HA, increase only for very large deployments

### 2. S3 Bucket Organization
```
s3://your-mwaa-bucket/
├── dags/
│   ├── main_workflow.py
│   └── utils/
│       └── helpers.py
├── plugins/
│   └── custom_operators.zip
├── requirements/
│   └── requirements.txt
└── scripts/
    └── startup.sh
```

### 3. Requirements Management
- Pin all package versions in requirements.txt
- Test requirements locally before deploying
- Use constraints files for Airflow providers
- Keep requirements minimal to reduce startup time

## DAG Design Patterns

### 1. Idempotency
- Design tasks to be re-runnable without side effects
- Use upsert operations instead of inserts
- Include date partitioning in data operations

### 2. Task Dependencies
```python
# Good: Clear linear dependencies
extract >> transform >> load

# Better: Parallel where possible
extract >> [transform_a, transform_b] >> load

# Best: Dynamic task mapping (Airflow 2.3+)
@task
def process_file(filename):
    # Process individual file
    pass

filenames = get_files()
process_file.expand(filename=filenames)
```

### 3. Error Handling
```python
# Set appropriate retries
default_args = {
    'retries': 2,
    'retry_delay': timedelta(minutes=5),
    'retry_exponential_backoff': True,
    'max_retry_delay': timedelta(minutes=30),
}

# Use trigger rules for error paths
error_handler = EmptyOperator(
    task_id='handle_errors',
    trigger_rule='one_failed'
)
```

## Performance Optimization

### 1. DAG Loading Time
- Keep DAG files small and focused
- Avoid heavy imports at module level
- Use Jinja templating instead of Python loops for static DAGs
- Limit the number of DAGs per file

### 2. Task Execution
- Use appropriate task concurrency limits
- Implement connection pooling for databases
- Batch operations where possible
- Use XCom sparingly (max 48KB per XCom)

### 3. Sensor Optimization
```python
# Use reschedule mode for long-running sensors
s3_sensor = S3KeySensor(
    task_id='wait_for_file',
    bucket_key='s3://bucket/key',
    mode='reschedule',  # Don't occupy worker slot
    poke_interval=300,  # Check every 5 minutes
    timeout=3600,       # 1 hour timeout
)
```

## Security Best Practices

### 1. IAM Roles
- Use separate execution role with minimal permissions
- Implement role assumption for cross-account access
- Avoid hardcoding credentials

### 2. Secrets Management
```python
# Use Airflow connections and variables
from airflow.models import Variable
from airflow.hooks.base import BaseHook

# Get connection
conn = BaseHook.get_connection('my_db')

# Get variable (with default)
api_key = Variable.get('api_key', default_var='')

# Use AWS Secrets Manager
from airflow.providers.amazon.aws.hooks.secrets_manager import SecretsManagerHook
hook = SecretsManagerHook(conn_id='aws_default')
secret = hook.get_secret('my-secret')
```

### 3. Network Security
- Use private subnets for MWAA
- Implement VPC endpoints for AWS services
- Configure security groups with minimal access

## Monitoring and Alerting

### 1. CloudWatch Integration
- Monitor key metrics: CPU, memory, task duration
- Set up alarms for failed tasks and DAG failures
- Use custom metrics for business KPIs

### 2. Logging Best Practices
```python
import logging

logger = logging.getLogger(__name__)

@task
def process_data():
    logger.info("Starting data processing")
    try:
        # Process data
        logger.info(f"Processed {record_count} records")
    except Exception as e:
        logger.error(f"Processing failed: {str(e)}")
        raise
```

### 3. SLA Management
```python
# Set SLA for critical tasks
critical_task = PythonOperator(
    task_id='critical_process',
    python_callable=process_critical_data,
    sla=timedelta(hours=2),
)

# Define SLA miss callback
def sla_miss_callback(dag, task_list, blocking_task_list, slas, blocking_tis):
    # Send notification
    pass

dag.sla_miss_callback = sla_miss_callback
```

## Cost Optimization

### 1. Environment Management
- Pause environments during non-business hours
- Use smaller environments for dev/test
- Clean up old logs and artifacts

### 2. Task Efficiency
- Minimize task runtime
- Use appropriate instance types
- Batch small tasks together

### 3. Data Transfer
- Process data in the same region
- Use VPC endpoints to avoid NAT gateway costs
- Compress data before transfer

## Common Pitfalls to Avoid

1. **Top-level Code**: Avoid database queries or API calls at DAG parse time
2. **Large XComs**: Don't pass large data through XCom
3. **Dynamic DAGs**: Be careful with dynamic DAG generation performance
4. **Missing Cleanup**: Always clean up temporary resources
5. **Hardcoded Dates**: Use Airflow's execution_date context
6. **Ignoring Idempotency**: Ensure all tasks can be safely re-run
7. **Over-scheduling**: Don't schedule DAGs more frequently than needed
8. **Resource Leaks**: Close connections and clean up resources

## MWAA-Specific Considerations

### 1. Limitations
- No kubectl access to underlying Kubernetes
- Limited pip packages (must be compatible with Amazon Linux)
- Maximum environment size constraints
- No direct database access

### 2. Migration Tips
- Test DAGs in MWAA development environment
- Verify all dependencies are available
- Update connection strings and credentials
- Plan for downtime during migration

### 3. Troubleshooting
- Check CloudWatch logs for detailed errors
- Verify S3 permissions and bucket policies
- Ensure VPC configuration allows internet access (for PyPI)
- Monitor environment health metrics

Remember: Always test changes in a development environment before deploying to production!
"""

DAG_DESIGN_GUIDANCE = """
# Airflow DAG Design and Optimization Guide

## DAG Structure Fundamentals

### 1. Basic DAG Anatomy
```python
from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta

# Define default arguments
default_args = {
    'owner': 'data-team',
    'depends_on_past': False,
    'start_date': datetime(2024, 1, 1),
    'email_on_failure': True,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

# Instantiate DAG
dag = DAG(
    'example_dag',
    default_args=default_args,
    description='A simple example DAG',
    schedule_interval='@daily',
    catchup=False,
    max_active_runs=1,
    tags=['example', 'tutorial'],
)
```

### 2. Task Dependencies Patterns

#### Linear Dependencies
```python
# Simple chain
task1 >> task2 >> task3

# Alternative syntax
chain(task1, task2, task3)
```

#### Parallel Processing
```python
# Fan-out/Fan-in pattern
start >> [process_a, process_b, process_c] >> combine_results

# Complex dependencies
extract >> validate
[transform_1, transform_2] >> aggregate
validate >> [transform_1, transform_2]
aggregate >> load
```

#### Dynamic Task Generation
```python
# Airflow 2.3+ Dynamic Task Mapping
@task
def get_files():
    return ['file1.csv', 'file2.csv', 'file3.csv']

@task
def process_file(filename: str):
    # Process individual file
    return f"Processed {filename}"

@task
def combine_results(results: list):
    return f"Combined {len(results)} results"

with DAG('dynamic_tasks', ...) as dag:
    files = get_files()
    processed = process_file.expand(filename=files)
    combine_results(processed)
```

## Advanced Patterns

### 1. Conditional Execution
```python
# Using BranchPythonOperator
from airflow.operators.python import BranchPythonOperator

def choose_branch(**context):
    if context['execution_date'].weekday() == 0:  # Monday
        return 'monday_task'
    return 'other_day_task'

branching = BranchPythonOperator(
    task_id='branching',
    python_callable=choose_branch,
)

monday_task = PythonOperator(task_id='monday_task', ...)
other_day_task = PythonOperator(task_id='other_day_task', ...)
join = PythonOperator(
    task_id='join',
    trigger_rule='none_failed_or_skipped',
    ...
)

branching >> [monday_task, other_day_task] >> join
```

### 2. SubDAGs and Task Groups
```python
# Task Groups (preferred over SubDAGs)
from airflow.utils.task_group import TaskGroup

with TaskGroup('processing_group') as processing:
    extract = PythonOperator(task_id='extract', ...)
    transform = PythonOperator(task_id='transform', ...)
    extract >> transform

start >> processing >> end
```

### 3. Cross-DAG Dependencies
```python
# Using ExternalTaskSensor
from airflow.sensors.external_task import ExternalTaskSensor

wait_for_upstream = ExternalTaskSensor(
    task_id='wait_for_upstream_dag',
    external_dag_id='upstream_dag',
    external_task_id='final_task',
    mode='reschedule',
)

# Using TriggerDagRunOperator
from airflow.operators.trigger_dagrun import TriggerDagRunOperator

trigger_downstream = TriggerDagRunOperator(
    task_id='trigger_downstream',
    trigger_dag_id='downstream_dag',
    conf={'key': 'value'},
    wait_for_completion=True,
)
```

## Sensor Patterns

### 1. Efficient Sensor Usage
```python
# S3 Key Sensor with reschedule mode
from airflow.providers.amazon.aws.sensors.s3 import S3KeySensor

wait_for_file = S3KeySensor(
    task_id='wait_for_s3_file',
    bucket_name='my-bucket',
    bucket_key='data/{{ ds }}/input.csv',
    mode='reschedule',  # Frees up worker slot
    poke_interval=300,
    timeout=3600,
    soft_fail=True,  # Don't fail the DAG if timeout
)

# Custom sensor with exponential backoff
class CustomSensor(BaseSensorOperator):
    def poke(self, context):
        # Custom logic
        return check_condition()
    
    def execute(self, context):
        self.poke_interval = 60  # Start with 1 minute
        super().execute(context)
        # Double interval each time (up to max)
        self.poke_interval = min(self.poke_interval * 2, 1800)
```

### 2. Smart Waiting Patterns
```python
# Date-aware sensor
from airflow.sensors.date_time import DateTimeSensor

wait_for_time = DateTimeSensor(
    task_id='wait_for_0300',
    target_time=time(3, 0),  # 3:00 AM
    mode='reschedule',
)

# Timeout with fallback
wait_with_fallback = S3KeySensor(
    task_id='wait_or_continue',
    bucket_key='optional-file.csv',
    timeout=1800,  # 30 minutes
    soft_fail=True,
)
```

## XCom Best Practices

### 1. Proper XCom Usage
```python
# Pushing to XCom
@task
def push_value():
    # Automatically pushed as return value
    return {'key': 'value', 'count': 42}

# Explicit push
def push_explicit(**context):
    context['task_instance'].xcom_push(key='my_key', value='my_value')

# Pulling from XCom
@task
def pull_value(**context):
    # Pull from specific task
    value = context['task_instance'].xcom_pull(
        task_ids='push_value',
        key='return_value'
    )
    
    # Pull from multiple tasks
    values = context['task_instance'].xcom_pull(
        task_ids=['task1', 'task2']
    )
```

### 2. XCom Alternatives for Large Data
```python
# Store reference in XCom, not data
@task
def process_large_data():
    # Process data and save to S3
    s3_key = f"s3://bucket/processed/{uuid.uuid4()}.parquet"
    # ... save data to s3_key
    
    # Return reference, not data
    return {'s3_key': s3_key, 'record_count': 1000000}

# Use Airflow Variables for shared config
from airflow.models import Variable

@task
def get_config():
    config = Variable.get('etl_config', deserialize_json=True)
    return config
```

## Testing Strategies

### 1. Unit Testing DAGs
```python
import pytest
from airflow.models import DagBag

def test_dag_loaded():
    dagbag = DagBag()
    dag = dagbag.get_dag('my_dag')
    assert dag is not None
    assert len(dag.tasks) > 0

def test_dag_structure():
    dag = get_dag('my_dag')
    
    # Check task dependencies
    task1 = dag.get_task('task1')
    task2 = dag.get_task('task2')
    
    assert task2 in task1.downstream_list
    
    # Check default args
    assert dag.default_args['retries'] == 2
```

### 2. Testing Individual Tasks
```python
from airflow.models import TaskInstance
from airflow.utils.state import State

def test_task_execution():
    dag = get_dag('my_dag')
    task = dag.get_task('process_data')
    
    ti = TaskInstance(task=task, execution_date=datetime.now())
    ti.run(ignore_task_deps=True, test_mode=True)
    
    assert ti.state == State.SUCCESS
```

## Common Anti-Patterns to Avoid

### 1. ❌ Top-level Operations
```python
# BAD: Executes during DAG parsing
data = fetch_from_database()  # This runs every time DAG is parsed!

with DAG('bad_dag', ...) as dag:
    process = PythonOperator(
        task_id='process',
        python_callable=lambda: process_data(data)
    )
```

### 2. ✅ Proper Pattern
```python
# GOOD: Executes only when task runs
def fetch_and_process():
    data = fetch_from_database()
    return process_data(data)

with DAG('good_dag', ...) as dag:
    process = PythonOperator(
        task_id='process',
        python_callable=fetch_and_process
    )
```

### 3. ❌ Non-Idempotent Tasks
```python
# BAD: Creates duplicate records on retry
def insert_records():
    db.insert(generate_records())
```

### 4. ✅ Idempotent Alternative
```python
# GOOD: Safe to retry
def upsert_records(**context):
    execution_date = context['execution_date']
    records = generate_records(execution_date)
    
    # Delete existing records for this date
    db.delete(date=execution_date)
    # Insert new records
    db.insert(records)
```

## Performance Optimization Tips

1. **Minimize DAG Parsing Time**: Keep imports light, avoid complex logic
2. **Use Task Concurrency**: Set appropriate `max_active_tasks_per_dag`
3. **Batch Operations**: Process multiple records in single task
4. **Leverage Parallelism**: Use `max_active_runs` and parallel task design
5. **Smart Scheduling**: Avoid overlapping schedule intervals
6. **Connection Pooling**: Reuse database connections
7. **Efficient Sensors**: Always use `mode='reschedule'` for long waits

Remember: The goal is to create maintainable, efficient, and reliable workflows that scale with your data needs!
"""