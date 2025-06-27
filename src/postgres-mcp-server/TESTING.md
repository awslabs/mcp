# PostgreSQL MCP Server - Testing Guide

This document describes the test files available for validating the PostgreSQL MCP Server.

## Test Directory Structure

All test files are organized in the `tests/` directory following Python project conventions:

```
tests/
├── test_all_tools_comprehensive.py  # Comprehensive validation of all 10 tools
├── test_type_conversions.py         # Type conversion validation
├── test_server.py                   # Unit tests for server functions
├── test_connection_pool.py          # Connection pool unit tests
└── __init__.py                      # Python package initialization
```

## Test Files

### Primary Test Suite

#### `test_all_tools_comprehensive.py`
- **Purpose**: Comprehensive validation of all 10 PostgreSQL MCP Server tools
- **Type**: Integration test (standalone executable)
- **Coverage**: Tests all tools with real database queries and validates responses
- **Usage**: `python tests/test_all_tools_comprehensive.py`

#### `test_type_conversions.py`
- **Purpose**: Validates type conversion fixes in analysis tools
- **Type**: Integration test with pytest functions
- **Coverage**: Tests fragmentation analysis and slow query tools specifically
- **Usage**: `pytest tests/test_type_conversions.py`

### Unit Test Suite

#### `test_server.py`
- **Purpose**: Unit tests for server utility functions
- **Type**: Pytest unit tests (15 test functions)
- **Coverage**: Tests `extract_cell`, `parse_execute_response`, and other utilities
- **Usage**: `pytest tests/test_server.py`

#### `test_connection_pool.py`
- **Purpose**: Unit tests for connection pool functionality
- **Type**: Pytest unit tests (18 test functions)
- **Coverage**: Tests connection pooling, factory patterns, and error handling
- **Usage**: `pytest tests/test_connection_pool.py`

## Environment Variables

For security, test files use environment variables for credentials:

```bash
export TEST_RESOURCE_ARN="arn:aws:rds:<region>:<account-id>:cluster:<cluster-name>"
export TEST_SECRET_ARN="arn:aws:secretsmanager:<region>:<account-id>:secret:<secret-name>"
```

If not set, tests will fall back to default test values.

## Running Tests

### Run All Tests
```bash
pytest tests/
```

### Run Specific Test Categories
```bash
# Unit tests only
pytest tests/test_server.py tests/test_connection_pool.py

# Integration tests
python tests/test_all_tools_comprehensive.py
pytest tests/test_type_conversions.py
```

### Test Collection
```bash
# See all available tests
pytest --collect-only tests/
```

## Test Results

The test suite includes both passing and intentionally skipped tests:
- **Unit tests**: Most pass with proper mocking
- **Integration tests**: Require real AWS credentials and database access
- **Skipped tests**: Tests for deprecated functionality or missing dependencies

## Security Notes

- Tests use environment variables for credentials (not hardcoded)
- AWS profile-based authentication is recommended
- Test databases should be isolated from production

#### `tests/test_all_tools_comprehensive.py` ⭐ **MAIN TEST**
**Purpose**: Comprehensive validation of all 10 PostgreSQL MCP Server tools
- **Complete Coverage**: Tests all 10 tools with their SQL queries and logic
- **Core Tools**: run_query, get_table_schema, health_check
- **Analysis Tools**: All 7 analysis tools with detailed validation
- **Logic Validation**: Type conversions, error handling, data validation
- **RDS Data API**: Full compatibility testing
- **Usage**: `python tests/test_all_tools_comprehensive.py`
- **Expected Result**: 16/17 tests should pass (1 expected failure for pg_stat_statements view)

### Specialized Tests

#### `tests/test_type_conversions.py`
**Purpose**: Focused validation of critical type conversion fixes
- Tests string to float conversions for bloat percentages
- Validates table fragmentation analysis type handling
- Ensures no "str vs float" comparison errors
- **Usage**: `python tests/test_type_conversions.py`
- **Expected Result**: Type conversion tests should pass

#### `tests/test_connection_pool.py`
**Purpose**: Unit tests for the connection pool implementation
- Tests the `ConnectionPoolManager` class functionality
- Validates connection creation, reuse, and health checks
- Tests pool capacity limits and different connection types
- Tests concurrency handling with multiple connection requests
- Tests the enhanced `DBConnectionSingleton` with pooling support
- Tests resource leak prevention (malloc/free pattern)
- Tests memory leak prevention with proper connection cleanup
- Tests error handling during connection usage
- **Usage**: `pytest tests/test_connection_pool.py -v`
- **Expected Result**: All connection pool unit tests should pass (one test is marked as xfail)

### Legacy Tests

#### `tests/test_server.py`
**Purpose**: Original unit tests from the base implementation
- Legacy test file from the original server
- May not be compatible with current consolidated server
- Kept for reference but not actively maintained

## Running Tests

### Prerequisites
```bash
# Activate virtual environment
source .venv/bin/activate

# Set AWS profile
export AWS_PROFILE=mcp_profile
export AWS_REGION=us-west-2
```

### Recommended Testing Workflow

#### 1. Run Main Comprehensive Test (Recommended)
```bash
# This is the primary test - covers all 10 tools comprehensively
python tests/test_all_tools_comprehensive.py
```

#### 2. Run Specialized Tests (Optional)
```bash
# Test type conversions specifically
python tests/test_type_conversions.py

# Run legacy unit tests
python tests/test_server.py

# Run connection pool unit tests
pytest tests/test_connection_pool.py -v
```

#### 3. Run All Tests with pytest (If Available)
```bash
# Run all tests using pytest
pytest tests/

# Run with verbose output
pytest -v tests/

# Run specific test file
pytest tests/test_all_tools_comprehensive.py
```

### Expected Results
- **16/17 tests should pass** in the comprehensive test
- **1 expected failure**: `slow_queries_data` (pg_stat_statements view access issue)
- **All other tests passing** indicates a healthy server

## Test Coverage

### Comprehensive Test Suite Covers:
- ✅ **All 10 MCP tools** (3 core + 7 analysis)
- ✅ **17 SQL queries** with syntax validation
- ✅ **RDS Data API compatibility** (data type handling)
- ✅ **Type conversions** (string ↔ numeric)
- ✅ **Logic validation** (business rules, thresholds)
- ✅ **Error handling** and edge cases
- ✅ **JSON response formatting**
- ✅ **Connection pooling** (unit tests)

### Tool-by-Tool Coverage:
1. **run_query**: Basic + complex query execution
2. **get_table_schema**: Column metadata retrieval
3. **health_check**: Connectivity + logic validation
4. **analyze_database_structure**: Schemas, tables, indexes
5. **show_postgresql_settings**: Filtered + all settings
6. **identify_slow_queries**: Extension check + query analysis
7. **analyze_table_fragmentation**: Bloat analysis + type conversion
8. **analyze_query_performance**: EXPLAIN functionality
9. **analyze_vacuum_stats**: Statistics + settings
10. **recommend_indexes**: Current indexes + statistics analysis

## Advantages of Consolidated Testing

### Why We Consolidated Tests:
1. **No Duplication**: Eliminates redundant SQL query tests
2. **Single Source of Truth**: One comprehensive test file
3. **Easier Maintenance**: Only one file to update when adding tools
4. **Faster Testing**: Single database connection, efficient execution
5. **Better Organization**: All tool tests in logical order
6. **Complete Coverage**: Tests both SQL and business logic

### Previous Structure Issues:
- ❌ **test_all_tools_simple.py**: Only tested SQL queries (incomplete)
- ❌ **test_new_tools.py**: Redundant SQL tests + limited to 3 tools
- ❌ **Maintenance Overhead**: Two files to update for changes
- ❌ **Resource Waste**: Multiple database connections

## Troubleshooting

### Common Issues
1. **AWS Credentials**: Ensure `mcp_profile` is configured
2. **Database Access**: Verify RDS cluster is accessible
3. **Extensions**: `pg_stat_statements` view may not be accessible (expected)
4. **Data Types**: RDS Data API doesn't support PostgreSQL arrays

### Expected Test Failures
- **slow_queries_data**: pg_stat_statements view access (normal for some RDS configurations)

### Unexpected Test Failures
- Review error messages for specific SQL syntax issues
- Check AWS credentials and database connectivity
- Verify RDS Data API permissions and cluster status

## Development Workflow

### Before Committing Changes
```bash
# Run the comprehensive test suite (primary validation)
python tests/test_all_tools_comprehensive.py

# Optionally run type conversion tests
python tests/test_type_conversions.py
```

### Adding New Tools
1. Add SQL query tests to `test_all_tools_comprehensive.py`
2. Include logic validation functions if needed
3. Update this documentation
4. Ensure all tests pass before committing

### Connection Pool Configuration

The connection pool can be configured using environment variables:

```bash
# Set connection pool parameters
export POSTGRES_POOL_MIN_SIZE=10  # Minimum pool size (default: 5)
export POSTGRES_POOL_MAX_SIZE=50  # Maximum pool size (default: 30)
export POSTGRES_POOL_TIMEOUT=60   # Connection timeout in seconds (default: 30)

# Run tests with custom pool configuration
pytest tests/test_connection_pool.py -v
```

### Performance Notes
- **Comprehensive test**: ~30-45 seconds (tests 17 queries)
- **Type conversion test**: ~10-15 seconds (focused testing)
- **Connection pool tests**: ~10-15 seconds (unit tests)
- **Total coverage**: All 10 tools and connection pooling validated efficiently
