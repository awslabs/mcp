# Integration Test Data

This directory contains test workflow files used by integration tests to validate the ETL replatforming MCP server functionality.

## Directory Structure

```
test_data/
├── airflow_jobs/           # Airflow DAG test files
│   ├── 01_simple_sql_extract.py
│   ├── 02_sequential_etl.py
│   ├── 03_parallel_processing.py
│   ├── 04_conditional_branching.py
│   ├── 05_error_handling_complex.py
│   ├── 06_extremely_complex_pipeline.py
│   └── 07_advanced_loops_and_conditions.py
└── step_function_jobs/     # Step Functions state machine test files
    ├── 01_simple_sql_extract.json
    ├── 02_sequential_etl.json
    ├── 03_parallel_processing.json
    ├── 04_conditional_branching.json
    ├── 05_error_handling_complex.json
    ├── 06_extremely_complex_pipeline.json
    └── 07_advanced_loops_and_conditions.json
```

## Test Coverage

These files provide comprehensive test coverage for:

### Basic Patterns
- **01_simple_sql_extract**: Basic SQL extraction tasks
- **02_sequential_etl**: Sequential task execution with dependencies

### Advanced Patterns
- **03_parallel_processing**: Concurrent task execution
- **04_conditional_branching**: Choice states and conditional logic
- **05_error_handling_complex**: Error handling, retries, and failure paths
- **06_extremely_complex_pipeline**: Multi-source ETL with dynamic scaling
- **07_advanced_loops_and_conditions**: For-each loops, while loops, case-when logic

### Framework-Specific Features
- **Airflow**: DAGs, TaskGroups, BranchPythonOperator, FileSensor
- **Step Functions**: State machines, Choice states, Map states, parallel execution

## Usage

These files are automatically used by:
- `test_mcp_integration.py::test_all_tools_with_samples()` - Tests all MCP tools with real workflow files
- Integration tests validate parsing, conversion, and generation across frameworks

## Adding New Test Cases

To add new test cases:
1. Create matching files in both `airflow_jobs/` and `step_function_jobs/` directories
2. Use descriptive naming: `##_feature_description.py/json`
3. Include complex patterns that test edge cases and advanced features
4. Update this README with the new test case description
