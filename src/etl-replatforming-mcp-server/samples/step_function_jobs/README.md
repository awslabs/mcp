# Sample Step Functions ETL Pipelines

This directory contains a series of Step Functions definitions ranging from simple to extremely complex, all focused on data pipeline use cases.

## Pipeline Complexity Levels

### 01_simple_sql_extract.json
**Complexity: Basic**
- Single SQL extraction task
- Basic retry configuration
- Minimal error handling
- **Use Case**: Daily customer data extraction

### 02_sequential_etl.json
**Complexity: Intermediate**
- Sequential Extract → Transform → Load pattern
- Multiple task types (Redshift + Lambda)
- Task chaining with dependencies
- **Use Case**: Daily sales data processing

### 03_parallel_processing.json
**Complexity: Intermediate-Advanced**
- Parallel execution branches
- Multiple data sources processed simultaneously
- Result aggregation after parallel processing
- **Use Case**: Multi-table data processing with final join

### 04_conditional_branching.json
**Complexity: Advanced**
- Dynamic branching based on data volume
- Choice states with numeric comparisons
- Different processing strategies per volume
- **Use Case**: Adaptive processing based on daily transaction volume

### 05_error_handling_complex.json
**Complexity: Advanced**
- Comprehensive error handling with Catch blocks
- Multiple retry strategies with backoff
- Timeout handling
- Failure notifications and cleanup
- **Use Case**: Production ETL with robust error recovery

### 06_extremely_complex_pipeline.json
**Complexity: Expert**
- Multi-source health checking
- Dynamic processing strategy selection
- Map states for parallel partition processing
- Multiple AWS services (Batch, ECS, Lambda, Redshift, SNS, CloudWatch)
- Comprehensive monitoring and metrics
- **Use Case**: Enterprise-grade ETL with auto-scaling and monitoring

## Testing These Pipelines

These pipelines are tested automatically by the integration test suite:

```bash
# Run bidirectional conversion tests
python tests/integration/test_all_conversions.py
```

Each pipeline tests the MCP server's ability to parse Step Functions → FLEX → Airflow conversions.

## Key Step Functions Features Demonstrated

- **Task Types**: Task, Parallel, Choice, Map
- **Integrations**: Redshift Data API, Lambda, Batch, ECS, SNS, CloudWatch
- **Error Handling**: Retry, Catch, Timeout
- **Control Flow**: Sequential, Parallel, Conditional
- **Data Patterns**: ETL, ELT, Stream Processing
- **Monitoring**: Metrics, Notifications, Health Checks

## Expected Conversion Challenges

1. **Schedule Information**: Step Functions don't include scheduling - will need user input
2. **Resource Configuration**: Batch job definitions, ECS task definitions need mapping
3. **Error Handling**: Complex catch/retry logic needs Airflow equivalent patterns
4. **Parallel Processing**: Map states and Parallel branches need careful conversion
5. **Dynamic Choices**: Choice states based on data need conditional logic in target frameworks