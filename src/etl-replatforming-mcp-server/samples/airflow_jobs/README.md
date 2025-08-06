# Airflow Job Samples

This directory contains 6 Airflow DAG samples with progressively increasing complexity, designed to test the ETL replatforming MCP server's parsing and conversion capabilities.

## Sample Overview

| File | Complexity | Description | Key Features |
|------|------------|-------------|--------------|
| `01_simple_sql_extract.py` | ⭐ | Single SQL task | Basic PostgresOperator, simple retry logic |
| `02_sequential_etl.py` | ⭐⭐ | Sequential ETL pipeline | Extract → Transform → Validate → Load |
| `03_parallel_processing.py` | ⭐⭐⭐ | Parallel data processing | TaskGroup, concurrent processing |
| `04_conditional_branching.py` | ⭐⭐⭐⭐ | Conditional workflows | BranchPythonOperator, conditional logic |
| `05_error_handling_complex.py` | ⭐⭐⭐⭐⭐ | Advanced error handling | Email notifications, trigger rules, cleanup |
| `06_extremely_complex_pipeline.py` | ⭐⭐⭐⭐⭐⭐ | Production-grade pipeline | File sensors, dynamic processing, monitoring |

## Complexity Progression

### Level 1: Simple SQL Extract
- **Single task**: PostgresOperator
- **Basic configuration**: Default args, simple retry
- **Use case**: Basic data extraction

### Level 2: Sequential ETL
- **4 tasks**: Extract → Transform → Validate → Load
- **Mixed operators**: PostgresOperator + PythonOperator
- **Linear dependencies**: Sequential execution

### Level 3: Parallel Processing
- **TaskGroup**: Parallel data processing
- **Concurrent execution**: Multiple tables processed simultaneously
- **Convergence**: Results combined after parallel processing

### Level 4: Conditional Branching
- **BranchPythonOperator**: Dynamic path selection
- **Conditional logic**: Different processing based on data volume
- **Convergence patterns**: Multiple paths joining back together

### Level 5: Complex Error Handling
- **Comprehensive error handling**: Multiple trigger rules
- **Notifications**: Email alerts on failure
- **Cleanup tasks**: Success and failure cleanup paths
- **Advanced retry logic**: Different retry strategies per task

### Level 6: Extremely Complex Pipeline
- **File sensors**: Wait for external data files
- **Dynamic processing**: Strategy selection based on system load
- **Multiple TaskGroups**: High-performance vs standard processing
- **Resource monitoring**: System resource tracking
- **Data lineage**: Comprehensive data tracking
- **Executive reporting**: Business-level reporting
- **Production features**: Pools, max_active_runs, comprehensive monitoring

## Airflow Features Covered

### Operators Used
- `PostgresOperator` - Database operations
- `PythonOperator` - Custom Python functions
- `BranchPythonOperator` - Conditional branching
- `BashOperator` - Shell commands
- `EmailOperator` - Email notifications
- `DummyOperator` - Workflow control
- `FileSensor` - File system monitoring

### Advanced Features
- **TaskGroups** - Logical task grouping
- **Trigger Rules** - Advanced dependency logic
- **Connection Pools** - Resource management
- **Email Notifications** - Alerting system
- **File Sensors** - External dependency monitoring
- **Dynamic Task Generation** - Runtime task creation
- **Resource Monitoring** - System resource tracking

## Testing the Samples

These samples test the MCP server's ability to:

1. **Parse Airflow DAGs** - Extract workflow structure from Python code
2. **Convert to FLEX** - Transform to framework-agnostic format
3. **Generate Step Functions** - Convert FLEX to AWS Step Functions JSON
4. **Handle complexity** - Process increasingly complex workflow patterns
5. **Bidirectional conversion** - Ensure round-trip conversion accuracy

## Testing with MCP Server

These samples are tested automatically by the integration test suite:

```bash
# Run bidirectional conversion tests
python tests/integration/test_all_conversions.py
```

Each sample tests the MCP server's ability to parse Airflow → FLEX → Step Functions conversions.

## Notes

- All samples use PostgreSQL connections (`postgres_conn_id`)
- Email addresses are placeholder values
- File paths in sensors are example paths
- Connection IDs should be configured in your Airflow environment
- Resource pools referenced in complex samples need to be defined in Airflow