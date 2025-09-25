import pytest
from awslabs.dynamodb_mcp_server.database_analysis_queries import get_query_resource
from awslabs.dynamodb_mcp_server.server import mysql_run_query


@pytest.mark.asyncio
async def test_mysql_connection_and_query(mysql_env_setup, mock_mysql_functions, monkeypatch):
    """Test MySQL connection initialization and query execution."""
    monkeypatch.setenv('MYSQL_READONLY', 'true')

    result = await mysql_run_query('SELECT * FROM users')

    assert result == [{'id': 1, 'name': 'test'}]


@pytest.mark.asyncio
async def test_mysql_missing_config(monkeypatch):
    """Test MySQL query when configuration is missing."""
    # Clear MySQL env vars using monkeypatch
    monkeypatch.delenv('MYSQL_CLUSTER_ARN', raising=False)
    monkeypatch.delenv('MYSQL_SECRET_ARN', raising=False)
    monkeypatch.delenv('MYSQL_DATABASE', raising=False)

    result = await mysql_run_query('SELECT * FROM users')
    assert 'error' in result[0]
    assert 'MySQL integration requires these environment variables' in result[0]['error']


@pytest.mark.asyncio
async def test_mysql_aws_region_fallback(mysql_env_setup, monkeypatch):
    """Test MYSQL_AWS_REGION fallback to AWS_REGION."""
    monkeypatch.setenv('AWS_REGION', 'us-east-1')  # Should fallback to this
    monkeypatch.delenv('MYSQL_AWS_REGION', raising=False)

    # Mock the MySQL functions
    def mock_initialize(*args, **kwargs):
        return True

    async def mock_query(*args, **kwargs):
        return [{'region': 'us-east-1'}]

    monkeypatch.setattr(
        'awslabs.dynamodb_mcp_server.server.DBConnectionSingleton.initialize', mock_initialize
    )
    monkeypatch.setattr('awslabs.dynamodb_mcp_server.server.mysql_query', mock_query)

    result = await mysql_run_query("SELECT 'us-east-1' as region")
    assert result == [{'region': 'us-east-1'}]


def test_query_resource_functions():
    """Test query resource utility functions."""
    # Test getting a query resource
    query = get_query_resource('performance_schema_check')
    assert 'sql' in query
    assert 'SHOW VARIABLES LIKE' in query['sql']

    # Test parameter substitution
    query = get_query_resource('pattern_analysis', target_database='employees', analysis_days=30)
    assert 'employees' in query['sql']
    assert '30' in query['sql']

    # Test invalid query name
    with pytest.raises(ValueError, match="Query 'invalid_query' not found"):
        get_query_resource('invalid_query')


def test_mysql_max_query_results_limit(monkeypatch):
    """Test LIMIT clause addition for codecov coverage."""
    # Test custom limit
    monkeypatch.setenv('MYSQL_MAX_QUERY_RESULTS', '100')
    query = get_query_resource('pattern_analysis', target_database='test', analysis_days=30)
    assert 'LIMIT 100' in query['sql']

    # Test query without semicolon (covers the endswith check)
    query = get_query_resource('column_analysis', target_database='test')
    assert 'LIMIT 100' in query['sql']


@pytest.mark.asyncio
async def test_mysql_initialization_exception(mysql_env_setup, monkeypatch):
    """Test MySQL initialization exception handling for codecov coverage."""

    # Mock DBConnectionSingleton.initialize to raise an exception
    def mock_initialize_fail(*args, **kwargs):
        raise Exception('Connection failed')

    monkeypatch.setattr(
        'awslabs.dynamodb_mcp_server.server.DBConnectionSingleton.initialize', mock_initialize_fail
    )

    result = await mysql_run_query('SELECT * FROM users')
    assert 'error' in result[0]
    assert 'MySQL initialization failed' in result[0]['error']


@pytest.mark.asyncio
async def test_mysql_query_execution_exception(mysql_env_setup, monkeypatch):
    """Test MySQL query execution exception handling for codecov coverage."""

    # Mock successful initialization but failing query
    def mock_initialize(*args, **kwargs):
        return True

    async def mock_query_fail(*args, **kwargs):
        raise Exception('Query execution failed')

    monkeypatch.setattr(
        'awslabs.dynamodb_mcp_server.server.DBConnectionSingleton.initialize', mock_initialize
    )
    monkeypatch.setattr('awslabs.dynamodb_mcp_server.server.mysql_query', mock_query_fail)

    result = await mysql_run_query('SELECT * FROM users')
    assert 'error' in result[0]
    assert 'MySQL query failed' in result[0]['error']
