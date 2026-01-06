import json
import os
import pytest
import pytest_asyncio
from awslabs.dynamodb_mcp_server.db_analyzer import analyzer_utils
from awslabs.dynamodb_mcp_server.server import (
    _execute_access_patterns,
    app,
    create_server,
    dynamodb_data_model_validation,
    dynamodb_data_modeling,
    execute_dynamodb_command,
    source_db_analyzer,
)
from unittest.mock import mock_open, patch


@pytest_asyncio.fixture
async def aws_credentials():
    """Mocked AWS Credentials for moto."""
    os.environ['AWS_DEFAULT_REGION'] = 'us-west-2'


@pytest.mark.asyncio
async def test_dynamodb_data_modeling():
    """Test the dynamodb_data_modeling tool directly."""
    result = await dynamodb_data_modeling()

    assert isinstance(result, str), 'Expected string response'
    assert len(result) > 1000, 'Expected substantial content (>1000 characters)'

    expected_sections = [
        'DynamoDB Data Modeling Expert System Prompt',
        'Access Patterns Analysis',
        'Enhanced Aggregate Analysis',
        'Important DynamoDB Context',
    ]

    for section in expected_sections:
        assert section in result, f"Expected section '{section}' not found in content"


@pytest.mark.asyncio
async def test_dynamodb_data_modeling_mcp_integration():
    """Test the dynamodb_data_modeling tool through MCP client."""
    # Verify tool is registered in the MCP server
    tools = await app.list_tools()
    tool_names = [tool.name for tool in tools]
    assert 'dynamodb_data_modeling' in tool_names, (
        'dynamodb_data_modeling tool not found in MCP server'
    )

    # Get tool metadata
    modeling_tool = next((tool for tool in tools if tool.name == 'dynamodb_data_modeling'), None)
    assert modeling_tool is not None, 'dynamodb_data_modeling tool not found'

    assert modeling_tool.description is not None
    assert 'DynamoDB' in modeling_tool.description
    assert 'data modeling' in modeling_tool.description.lower()


@pytest.mark.asyncio
async def test_source_db_analyzer_missing_parameters(tmp_path):
    """Test source_db_analyzer with missing database parameter."""
    result = await source_db_analyzer(
        source_db_type='mysql',
        database_name=None,
        execution_mode='managed',
        pattern_analysis_days=30,
        max_query_results=None,
        aws_secret_arn='test-secret',
        aws_cluster_arn='test-cluster',
        aws_region='us-east-1',
        output_dir=str(tmp_path),
    )

    assert 'Database name to analyze' in result


@pytest.mark.asyncio
async def test_source_db_analyzer_empty_parameters(tmp_path):
    """Test source_db_analyzer with empty string parameters."""
    result = await source_db_analyzer(
        source_db_type='mysql',
        database_name='test',
        execution_mode='managed',
        pattern_analysis_days=30,
        max_query_results=None,
        aws_cluster_arn='  ',  # Empty after strip
        aws_secret_arn='test-secret',
        aws_region='us-east-1',
        output_dir=str(tmp_path),
    )

    assert (
        'Required: Either aws_cluster_arn (for RDS Data API-based access) OR hostname (for connection-based access)'
        in result
    )


@pytest.mark.asyncio
async def test_source_db_analyzer_env_fallback(monkeypatch, tmp_path):
    """Test source_db_analyzer environment variable fallback."""
    # Set only some env vars to trigger fallback for others
    monkeypatch.setenv('MYSQL_SECRET_ARN', 'env-secret')
    monkeypatch.setenv('AWS_REGION', 'env-region')

    result = await source_db_analyzer(
        source_db_type='mysql',
        database_name='test',
        execution_mode='managed',
        pattern_analysis_days=30,
        max_query_results=None,
        aws_cluster_arn=None,  # Will trigger env fallback
        aws_secret_arn=None,  # Will use env var
        aws_region=None,  # Will use env var
        output_dir=str(tmp_path),
    )

    # Should still fail due to missing cluster_arn or hostname, but covers env fallback lines
    assert 'Either aws_cluster_arn' in result or 'I need:' in result


@pytest.mark.asyncio
async def test_source_db_analyzer_connection_method_precedence(mysql_env_setup, tmp_path):
    """Test that explicit connection parameters take precedence over environment variables."""
    # mysql_env_setup fixture sets MYSQL_CLUSTER_ARN, MYSQL_SECRET_ARN, AWS_REGION
    # Pass explicit hostname parameter - this should take precedence over env cluster_arn
    result = await source_db_analyzer(
        source_db_type='mysql',
        database_name='test',
        execution_mode='managed',
        pattern_analysis_days=30,
        max_query_results=None,
        aws_cluster_arn=None,  # No explicit cluster_arn
        hostname='explicit-hostname',  # Explicit hostname should pass
        aws_secret_arn=None,  # Will use env var
        aws_region=None,  # Will use env var
        output_dir=str(tmp_path),
    )

    # The test validates the precedence works: it used Asyncmy connection-based access (hostname)
    # instead of RDS Data API (cluster_arn), even though env had MYSQL_CLUSTER_ARN
    assert 'Analysis failed' in result or 'Database Analysis Failed' in result


@pytest.mark.asyncio
async def test_source_db_analyzer_env_hostname_only_fallback(mysql_env_setup, tmp_path):
    """Test fallback to environment MYSQL_HOSTNAME when cluster_arn is cleared."""
    # mysql_env_setup sets MYSQL_CLUSTER_ARN, but we'll override it to test hostname fallback
    # Temporarily clear cluster_arn and set hostname to test the elif env_hostname branch
    original_cluster = os.environ.pop('MYSQL_CLUSTER_ARN', None)
    os.environ['MYSQL_HOSTNAME'] = 'env-hostname-test'

    try:
        result = await source_db_analyzer(
            source_db_type='mysql',
            database_name='test',
            execution_mode='managed',
            pattern_analysis_days=30,
            max_query_results=None,
            aws_cluster_arn=None,  # No explicit cluster_arn
            hostname=None,  # No explicit hostname - should use env
            aws_secret_arn=None,  # Will use env var from fixture
            aws_region=None,  # Will use env var from fixture
            output_dir=str(tmp_path),
        )
    finally:
        # Restore original state
        if original_cluster:
            os.environ['MYSQL_CLUSTER_ARN'] = original_cluster
        os.environ.pop('MYSQL_HOSTNAME', None)

    assert 'Analysis failed' in result or 'Database Analysis Failed' in result


@pytest.mark.asyncio
async def test_source_db_analyzer_no_env_connection_params(mysql_env_setup, tmp_path):
    """Test when no connection parameters are provided in env or explicit."""
    # Clear all connection-related env vars to test the final else branch
    original_cluster = os.environ.pop('MYSQL_CLUSTER_ARN', None)
    original_hostname = os.environ.pop('MYSQL_HOSTNAME', None)

    try:
        result = await source_db_analyzer(
            source_db_type='mysql',
            database_name='test',
            execution_mode='managed',
            pattern_analysis_days=30,
            max_query_results=None,
            aws_cluster_arn=None,
            hostname=None,
            aws_secret_arn=None,  # Will use env var from fixture
            aws_region=None,  # Will use env var from fixture
            output_dir=str(tmp_path),
        )
    finally:
        # Restore original state
        if original_cluster:
            os.environ['MYSQL_CLUSTER_ARN'] = original_cluster
        if original_hostname:
            os.environ['MYSQL_HOSTNAME'] = original_hostname

    assert 'I need:' in result or 'Either aws_cluster_arn' in result


@pytest.mark.asyncio
async def test_source_db_analyzer_unsupported_database(tmp_path):
    """Test source_db_analyzer with unsupported database type."""
    result = await source_db_analyzer(
        source_db_type='oracle',
        database_name='test_db',
        execution_mode='managed',
        pattern_analysis_days=30,
        output_dir=str(tmp_path),
    )
    assert 'Unsupported database type: oracle' in result

    result = await source_db_analyzer(
        source_db_type='mongodb',
        database_name='test_db',
        execution_mode='managed',
        pattern_analysis_days=30,
        output_dir=str(tmp_path),
    )
    assert 'Unsupported database type: mongodb' in result


@pytest.mark.asyncio
async def test_source_db_analyzer_analysis_exception(tmp_path, monkeypatch):
    """Test source_db_analyzer when analysis raises exception."""

    # Mock execute_managed_mode to raise exception
    async def mock_execute_managed_mode_fail(self, connection_params):
        raise Exception('Database connection failed')

    from awslabs.dynamodb_mcp_server.db_analyzer.mysql import MySQLPlugin

    monkeypatch.setattr(MySQLPlugin, 'execute_managed_mode', mock_execute_managed_mode_fail)

    result = await source_db_analyzer(
        source_db_type='mysql',
        database_name='test_db',
        execution_mode='managed',
        aws_cluster_arn='test-cluster',
        aws_secret_arn='test-secret',
        aws_region='us-east-1',
        pattern_analysis_days=30,
        output_dir=str(tmp_path),
    )

    assert 'Analysis failed: Database connection failed' in result


@pytest.mark.asyncio
async def test_source_db_analyzer_successful_analysis(tmp_path, monkeypatch):
    """Test source_db_analyzer with successful analysis."""

    # Mock successful analysis
    async def mock_execute_managed_mode_success(self, connection_params):
        return {
            'results': {'table_analysis': [{'table': 'users', 'rows': 100}]},
            'performance_enabled': True,
            'performance_feature': 'Performance Schema',
            'errors': ['Query 1 failed'],
        }

    def mock_save_files(*args, **kwargs):
        return ['/tmp/file1.json'], ['Error saving file2']

    from awslabs.dynamodb_mcp_server.db_analyzer.mysql import MySQLPlugin

    monkeypatch.setattr(MySQLPlugin, 'execute_managed_mode', mock_execute_managed_mode_success)
    monkeypatch.setattr(analyzer_utils, 'save_analysis_files', mock_save_files)

    result = await source_db_analyzer(
        source_db_type='mysql',
        database_name='test_db',
        execution_mode='managed',
        aws_cluster_arn='test-cluster',
        aws_secret_arn='test-secret',
        aws_region='us-east-1',
        pattern_analysis_days=30,
        output_dir=str(tmp_path),
    )

    assert 'Database Analysis Complete' in result
    assert 'Generated Analysis Files (Read All):' in result
    assert 'File Save Errors:' in result


@pytest.mark.asyncio
async def test_source_db_analyzer_exception_handling(tmp_path, monkeypatch):
    """Test exception handling in source_db_analyzer."""

    async def mock_execute_managed_mode_exception(self, connection_params):
        raise Exception('Test exception')

    from awslabs.dynamodb_mcp_server.db_analyzer.mysql import MySQLPlugin

    monkeypatch.setattr(MySQLPlugin, 'execute_managed_mode', mock_execute_managed_mode_exception)

    result = await source_db_analyzer(
        source_db_type='mysql',
        database_name='test_db',
        execution_mode='managed',
        aws_cluster_arn='test-cluster',
        aws_secret_arn='test-secret',
        aws_region='us-east-1',
        output_dir=str(tmp_path),
    )

    assert 'Analysis failed: Test exception' in result


@pytest.mark.asyncio
async def test_source_db_analyzer_all_queries_failed(tmp_path, monkeypatch):
    """Test source_db_analyzer when all queries fail."""

    # Mock analysis that returns empty results with errors
    async def mock_execute_managed_mode_all_failed(self, connection_params):
        return {
            'results': {},  # Empty results
            'performance_enabled': True,
            'errors': ['Query 1 failed', 'Query 2 failed', 'Query 3 failed'],
        }

    def mock_save_files(*args, **kwargs):
        return [], []

    from awslabs.dynamodb_mcp_server.db_analyzer.mysql import MySQLPlugin

    monkeypatch.setattr(MySQLPlugin, 'execute_managed_mode', mock_execute_managed_mode_all_failed)
    monkeypatch.setattr(analyzer_utils, 'save_analysis_files', mock_save_files)

    result = await source_db_analyzer(
        source_db_type='mysql',
        database_name='test_db',
        execution_mode='managed',
        aws_cluster_arn='test-cluster',
        aws_secret_arn='test-secret',
        aws_region='us-east-1',
        pattern_analysis_days=30,
        output_dir=str(tmp_path),
    )

    assert 'Database Analysis Failed' in result
    assert 'All 3 queries failed:' in result
    assert '1. Query 1 failed' in result
    assert '2. Query 2 failed' in result
    assert '3. Query 3 failed' in result


@pytest.mark.asyncio
async def test_source_db_analyzer_no_files_saved(tmp_path, monkeypatch):
    """Test source_db_analyzer when no files are saved."""

    # Mock successful analysis but no files saved
    async def mock_execute_managed_mode_success(self, connection_params):
        return {
            'results': {'table_analysis': [{'table': 'users', 'rows': 100}]},
            'performance_enabled': True,
            'errors': [],
        }

    def mock_save_files_empty(*args, **kwargs):
        return [], []  # No files saved, no errors

    from awslabs.dynamodb_mcp_server.db_analyzer.mysql import MySQLPlugin

    monkeypatch.setattr(MySQLPlugin, 'execute_managed_mode', mock_execute_managed_mode_success)
    monkeypatch.setattr(analyzer_utils, 'save_analysis_files', mock_save_files_empty)

    result = await source_db_analyzer(
        source_db_type='mysql',
        database_name='test_db',
        execution_mode='managed',
        aws_cluster_arn='test-cluster',
        aws_secret_arn='test-secret',
        aws_region='us-east-1',
        pattern_analysis_days=30,
        output_dir=str(tmp_path),
    )

    assert 'Database Analysis Complete' in result
    # Should not have "Generated Analysis Files" section when no files
    assert 'Generated Analysis Files (Read All):' not in result
    # Should not have "File Save Errors" section when no errors
    assert 'File Save Errors:' not in result


@pytest.mark.asyncio
async def test_source_db_analyzer_only_saved_files_no_errors(tmp_path, monkeypatch):
    """Test source_db_analyzer with saved files but no errors."""

    # Mock successful analysis
    async def mock_execute_managed_mode_success(self, connection_params):
        return {
            'results': {'table_analysis': [{'table': 'users', 'rows': 100}]},
            'performance_enabled': True,
            'errors': [],
        }

    def mock_save_files_success(*args, **kwargs):
        return ['/tmp/file1.json', '/tmp/file2.json'], []  # Files saved, no errors

    from awslabs.dynamodb_mcp_server.db_analyzer.mysql import MySQLPlugin

    monkeypatch.setattr(MySQLPlugin, 'execute_managed_mode', mock_execute_managed_mode_success)
    monkeypatch.setattr(analyzer_utils, 'save_analysis_files', mock_save_files_success)

    result = await source_db_analyzer(
        source_db_type='mysql',
        database_name='test_db',
        execution_mode='managed',
        aws_cluster_arn='test-cluster',
        aws_secret_arn='test-secret',
        aws_region='us-east-1',
        pattern_analysis_days=30,
        output_dir=str(tmp_path),
    )

    assert 'Database Analysis Complete' in result
    assert 'Generated Analysis Files (Read All):' in result
    assert '/tmp/file1.json' in result
    assert '/tmp/file2.json' in result
    # Should not have "File Save Errors" section when no errors
    assert 'File Save Errors:' not in result


@pytest.mark.asyncio
async def test_self_service_query_generation(tmp_path, monkeypatch):
    """Test self-service mode query generation for different databases."""
    # Test MySQL
    result = await source_db_analyzer(
        source_db_type='mysql',
        database_name='test_db',
        execution_mode='self_service',
        queries_file_path='queries.sql',
        query_result_file_path=None,
        pattern_analysis_days=30,
        output_dir=str(tmp_path),
    )
    assert 'SQL queries have been written to:' in result
    assert 'mysql -u user -p' in result
    assert os.path.exists(os.path.join(tmp_path, 'queries.sql'))

    # Test PostgreSQL
    result = await source_db_analyzer(
        source_db_type='postgresql',
        database_name='test_db',
        execution_mode='self_service',
        queries_file_path='pg_queries.sql',
        query_result_file_path=None,
        pattern_analysis_days=30,
        output_dir=str(tmp_path),
    )
    assert 'psql -d' in result

    # Test SQL Server
    result = await source_db_analyzer(
        source_db_type='sqlserver',
        database_name='test_db',
        execution_mode='self_service',
        queries_file_path='sqlserver_queries.sql',
        query_result_file_path=None,
        pattern_analysis_days=30,
        output_dir=str(tmp_path),
    )
    assert 'sqlcmd -d' in result

    # Test missing database name
    result = await source_db_analyzer(
        source_db_type='mysql',
        database_name=None,
        execution_mode='self_service',
        queries_file_path='queries.sql',
        query_result_file_path=None,
        pattern_analysis_days=30,
        output_dir=str(tmp_path),
    )
    assert 'database_name is required' in result

    # Test exception handling
    def mock_generate_query_file(*args, **kwargs):
        raise RuntimeError('Test error')

    from awslabs.dynamodb_mcp_server.db_analyzer import analyzer_utils

    monkeypatch.setattr(analyzer_utils, 'generate_query_file', mock_generate_query_file)

    result = await source_db_analyzer(
        source_db_type='mysql',
        database_name='test_db',
        execution_mode='self_service',
        queries_file_path='queries.sql',
        query_result_file_path=None,
        pattern_analysis_days=30,
        output_dir=str(tmp_path),
    )
    assert 'Failed to write queries: Test error' in result


@pytest.mark.asyncio
async def test_self_service_result_parsing(tmp_path, monkeypatch):
    """Test self-service mode result parsing."""
    # Test successful parsing
    result_file = os.path.join(tmp_path, 'results.txt')
    with open(result_file, 'w', encoding='utf-8') as f:
        f.write("""| marker |
| -- QUERY_NAME_START: comprehensive_table_analysis |
| table_name | row_count |
| users      |      1000 |
| marker |
| -- QUERY_NAME_END: comprehensive_table_analysis |
""")
    result = await source_db_analyzer(
        source_db_type='mysql',
        database_name='test_db',
        execution_mode='self_service',
        queries_file_path=None,
        query_result_file_path=result_file,
        pattern_analysis_days=30,
        output_dir=str(tmp_path),
    )
    assert 'Database Analysis Complete' in result
    assert 'Self-Service Mode' in result

    # Test result file not found
    result = await source_db_analyzer(
        source_db_type='mysql',
        database_name='test_db',
        execution_mode='self_service',
        queries_file_path=None,
        query_result_file_path=os.path.join(tmp_path, 'nonexistent_results.txt'),
        pattern_analysis_days=30,
        output_dir=str(tmp_path),
    )
    assert 'Result file not found' in result

    # Test path traversal protection - absolute path outside base directory
    result = await source_db_analyzer(
        source_db_type='mysql',
        database_name='test_db',
        execution_mode='self_service',
        queries_file_path=None,
        query_result_file_path='/nonexistent/results.txt',
        pattern_analysis_days=30,
        output_dir=str(tmp_path),
    )
    assert 'Path traversal detected' in result

    # Test exception handling
    result_file = os.path.join(tmp_path, 'results2.txt')
    with open(result_file, 'w', encoding='utf-8') as f:
        f.write('test data')

    def mock_parse_results(*args, **kwargs):
        raise RuntimeError('Parse error')

    from awslabs.dynamodb_mcp_server.db_analyzer import analyzer_utils

    monkeypatch.setattr(analyzer_utils, 'parse_results_and_generate_analysis', mock_parse_results)

    result = await source_db_analyzer(
        source_db_type='mysql',
        database_name='test_db',
        execution_mode='self_service',
        queries_file_path=None,
        query_result_file_path=result_file,
        pattern_analysis_days=30,
        output_dir=str(tmp_path),
    )
    assert 'Analysis failed: Parse error' in result


@pytest.mark.asyncio
async def test_invalid_execution_modes(tmp_path):
    """Test invalid execution modes and parameter combinations."""
    # Test invalid execution mode
    result = await source_db_analyzer(
        source_db_type='mysql',
        database_name='test_db',
        execution_mode='invalid_mode',
        pattern_analysis_days=30,
        output_dir=str(tmp_path),
    )
    assert 'Invalid execution_mode: invalid_mode' in result

    # Test self-service without query or result file
    result = await source_db_analyzer(
        source_db_type='mysql',
        database_name='test_db',
        execution_mode='self_service',
        queries_file_path=None,
        query_result_file_path=None,
        pattern_analysis_days=30,
        output_dir=str(tmp_path),
    )
    assert 'Invalid parameter combination' in result

    # Test PostgreSQL managed mode not supported
    result = await source_db_analyzer(
        source_db_type='postgresql',
        database_name='test_db',
        execution_mode='managed',
        aws_cluster_arn='test-cluster',
        aws_secret_arn='test-secret',
        aws_region='us-east-1',
        pattern_analysis_days=30,
        output_dir=str(tmp_path),
    )
    result_str = result['error'] if isinstance(result, dict) else result
    assert 'unsupported' in result_str.lower() or 'not supported' in result_str.lower()


# Tests for execute_dynamodb_command
@pytest.mark.asyncio
async def test_execute_dynamodb_command_valid_command():
    """Test execute_dynamodb_command with valid DynamoDB command."""
    with patch('awslabs.dynamodb_mcp_server.server.call_aws') as mock_call_aws:
        mock_call_aws.return_value = {'Tables': []}

        result = await execute_dynamodb_command(
            command='aws dynamodb list-tables', endpoint_url='http://localhost:8000'
        )

        assert result == {'Tables': []}
        mock_call_aws.assert_called_once()
        args, kwargs = mock_call_aws.call_args
        assert args[0] == 'aws dynamodb list-tables --endpoint-url http://localhost:8000'


@pytest.mark.asyncio
async def test_execute_dynamodb_command_invalid_command():
    """Test execute_dynamodb_command with invalid command."""
    result = await execute_dynamodb_command(command='aws s3 ls')
    assert "Command must start with 'aws dynamodb'" in str(result)


@pytest.mark.asyncio
async def test_execute_dynamodb_command_without_endpoint():
    """Test execute_dynamodb_command without endpoint URL."""
    with patch('awslabs.dynamodb_mcp_server.server.call_aws') as mock_call_aws:
        mock_call_aws.return_value = {'Tables': ['MyTable']}

        result = await execute_dynamodb_command(command='aws dynamodb list-tables')

        assert result == {'Tables': ['MyTable']}
        mock_call_aws.assert_called_once()
        args, kwargs = mock_call_aws.call_args
        assert 'aws dynamodb list-tables' in args[0]


@pytest.mark.asyncio
async def test_execute_dynamodb_command_with_endpoint_sets_env_vars():
    """Test that execute_dynamodb_command sets AWS environment variables when endpoint_url is provided."""
    original_env = os.environ.copy()

    try:
        with patch('awslabs.dynamodb_mcp_server.server.call_aws') as mock_call_aws:
            mock_call_aws.return_value = {'Tables': []}

            await execute_dynamodb_command(
                command='aws dynamodb list-tables', endpoint_url='http://localhost:8000'
            )

            assert (
                os.environ['AWS_ACCESS_KEY_ID']
                == 'AKIAIOSFODNN7EXAMPLE'  # pragma: allowlist secret
            )
            assert (
                os.environ['AWS_SECRET_ACCESS_KEY']
                == 'wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY'  # pragma: allowlist secret
            )
            assert 'AWS_DEFAULT_REGION' in os.environ
    finally:
        os.environ.clear()
        os.environ.update(original_env)


@pytest.mark.asyncio
async def test_execute_dynamodb_command_exception_handling():
    """Test execute_dynamodb_command exception handling."""
    with patch('awslabs.dynamodb_mcp_server.server.call_aws') as mock_call_aws:
        test_exception = Exception('AWS CLI error')
        mock_call_aws.side_effect = test_exception

        result = await execute_dynamodb_command(command='aws dynamodb list-tables')

        assert result == test_exception


# Tests for execute_access_patterns function
@pytest.mark.asyncio
async def test_execute_access_patterns_success():
    """Test execute_access_patterns with successful execution."""
    access_patterns = [
        {
            'pattern': 'AP1',
            'description': 'List all users',
            'dynamodb_operation': 'scan',
            'implementation': 'aws dynamodb scan --table-name Users',
        },
        {
            'pattern': 'AP2',
            'description': 'Get user by ID',
            'dynamodb_operation': 'get-item',
            'implementation': 'aws dynamodb get-item --table-name Users --key \'{"id":{"S":"123"}}\'',
        },
    ]

    with patch('awslabs.dynamodb_mcp_server.server.execute_dynamodb_command') as mock_execute:
        with patch('builtins.open', mock_open()) as mock_file:
            mock_execute.side_effect = [{'Items': []}, {'Item': {'id': {'S': '123'}}}]

            result = await _execute_access_patterns(
                '/tmp', access_patterns, endpoint_url='http://localhost:8000'
            )

            assert 'validation_response' in result
            assert len(result['validation_response']) == 2
            assert result['validation_response'][0]['pattern_id'] == 'AP1'
            assert result['validation_response'][1]['pattern_id'] == 'AP2'

            mock_file.assert_called_once()
            args, kwargs = mock_file.call_args
            assert args[0].endswith('dynamodb_model_validation.json')
            assert args[1] == 'w'


@pytest.mark.asyncio
async def test_execute_access_patterns_missing_implementation():
    """Test execute_access_patterns with patterns missing implementation."""
    access_patterns = [{'pattern': 'AP1', 'description': 'Pattern without implementation'}]

    with patch('builtins.open', mock_open()):
        result = await _execute_access_patterns('/tmp', access_patterns)

        assert 'validation_response' in result
        assert len(result['validation_response']) == 1
        assert result['validation_response'][0] == access_patterns[0]


@pytest.mark.asyncio
async def test_execute_access_patterns_exception_handling():
    """Test execute_access_patterns exception handling."""
    access_patterns = [
        {'pattern': 'AP1', 'implementation': 'aws dynamodb scan --table-name Users'}
    ]

    with patch('awslabs.dynamodb_mcp_server.server.execute_dynamodb_command') as mock_execute:
        mock_execute.side_effect = Exception('Command failed')

        result = await _execute_access_patterns('/tmp', access_patterns)

        assert 'validation_response' in result
        assert 'error' in result
        assert 'Command failed' in result['error']


# Tests for dynamodb_data_model_validation
@pytest.mark.asyncio
async def test_dynamodb_data_model_validation_success():
    """Test successful dynamodb_data_model_validation."""
    mock_data_model = {
        'tables': [{'TableName': 'Users'}],
        'items': [{'id': {'S': '123'}}],
        'access_patterns': [
            {'pattern': 'AP1', 'implementation': 'aws dynamodb scan --table-name Users'}
        ],
    }

    with patch('os.path.exists') as mock_exists:
        with patch('builtins.open', mock_open(read_data=json.dumps(mock_data_model))):
            with patch('awslabs.dynamodb_mcp_server.server.setup_dynamodb_local') as mock_setup:
                with patch('awslabs.dynamodb_mcp_server.server.create_validation_resources'):
                    with patch(
                        'awslabs.dynamodb_mcp_server.server._execute_access_patterns'
                    ) as mock_test:
                        with patch(
                            'awslabs.dynamodb_mcp_server.server.get_validation_result_transform_prompt'
                        ) as mock_transform:
                            mock_exists.return_value = True
                            mock_setup.return_value = 'http://localhost:8000'
                            mock_test.return_value = {'validation_response': []}
                            mock_transform.return_value = 'Validation complete'

                            result = await dynamodb_data_model_validation(workspace_dir='/tmp')

                            assert isinstance(result, str)
                            assert 'Validation complete' in result


@pytest.mark.asyncio
async def test_dynamodb_data_model_validation_file_not_found():
    """Test dynamodb_data_model_validation when data model file doesn't exist."""
    with patch('os.path.exists') as mock_exists:
        mock_exists.return_value = False

        result = await dynamodb_data_model_validation(workspace_dir='/tmp')

        assert 'dynamodb_data_model.json not found' in result


@pytest.mark.asyncio
async def test_dynamodb_data_model_validation_invalid_json():
    """Test dynamodb_data_model_validation with invalid JSON."""
    with patch('os.path.exists') as mock_exists:
        with patch('builtins.open', mock_open(read_data='invalid json')):
            mock_exists.return_value = True

            result = await dynamodb_data_model_validation(workspace_dir='/tmp')

            assert 'Error: Invalid JSON' in result


@pytest.mark.asyncio
async def test_dynamodb_data_model_validation_missing_required_keys():
    """Test dynamodb_data_model_validation with missing required keys."""
    incomplete_data_model = {'tables': []}

    with patch('os.path.exists') as mock_exists:
        with patch('builtins.open', mock_open(read_data=json.dumps(incomplete_data_model))):
            mock_exists.return_value = True

            result = await dynamodb_data_model_validation(workspace_dir='/tmp')

            assert 'Error: Missing required keys' in result
            assert 'items' in result
            assert 'access_patterns' in result


@pytest.mark.asyncio
async def test_dynamodb_data_model_validation_setup_exception():
    """Test dynamodb_data_model_validation when setup fails."""
    mock_data_model = {'tables': [], 'items': [], 'access_patterns': []}

    with patch('os.path.exists') as mock_exists:
        with patch('builtins.open', mock_open(read_data=json.dumps(mock_data_model))):
            with patch('awslabs.dynamodb_mcp_server.server.setup_dynamodb_local') as mock_setup:
                mock_exists.return_value = True
                mock_setup.side_effect = Exception('DynamoDB Local setup failed')

                result = await dynamodb_data_model_validation(workspace_dir='/tmp')

                assert 'DynamoDB Local setup failed' in result


# Tests for server configuration and MCP integration
def test_create_server():
    """Test create_server function."""
    server = create_server()

    assert server is not None
    assert hasattr(server, 'name')
    assert server.name == 'awslabs.dynamodb-mcp-server'


@pytest.mark.asyncio
async def test_mcp_server_tools_registration():
    """Test that all tools are properly registered in the MCP server."""
    tools = await app.list_tools()
    tool_names = [tool.name for tool in tools]

    expected_tools = [
        'dynamodb_data_modeling',
        'source_db_analyzer',
        'execute_dynamodb_command',
        'dynamodb_data_model_validation',
    ]

    for tool_name in expected_tools:
        assert tool_name in tool_names, f"Tool '{tool_name}' not found in MCP server"


@pytest.mark.asyncio
async def test_execute_dynamodb_command_mcp_integration():
    """Test execute_dynamodb_command tool through MCP client."""
    tools = await app.list_tools()
    execute_tool = next((tool for tool in tools if tool.name == 'execute_dynamodb_command'), None)

    assert execute_tool is not None
    assert execute_tool.description is not None
    assert 'AWSCLI DynamoDB' in execute_tool.description


@pytest.mark.asyncio
async def test_dynamodb_data_model_validation_mcp_integration():
    """Test dynamodb_data_model_validation tool through MCP client."""
    tools = await app.list_tools()
    validation_tool = next(
        (tool for tool in tools if tool.name == 'dynamodb_data_model_validation'), None
    )

    assert validation_tool is not None
    assert validation_tool.description is not None
    assert 'validates and tests dynamodb data models' in validation_tool.description.lower()


@pytest.mark.asyncio
async def test_error_propagation_in_validation_chain():
    """Test error propagation through the validation chain."""
    mock_data_model = {
        'tables': [],
        'items': [],
        'access_patterns': [
            {'pattern': 'AP1', 'implementation': 'aws dynamodb scan --table-name NonExistent'}
        ],
    }

    with patch('os.path.exists') as mock_exists:
        with patch('builtins.open', mock_open(read_data=json.dumps(mock_data_model))):
            with patch('awslabs.dynamodb_mcp_server.server.setup_dynamodb_local') as mock_setup:
                with patch(
                    'awslabs.dynamodb_mcp_server.server.create_validation_resources'
                ) as mock_create:
                    mock_exists.return_value = True
                    mock_setup.return_value = 'http://localhost:8000'
                    mock_create.side_effect = Exception('Table creation failed')

                    result = await dynamodb_data_model_validation(workspace_dir='/tmp')

                    assert 'Table creation failed' in result


@pytest.mark.asyncio
async def test_execute_dynamodb_command_edge_cases():
    """Test execute_dynamodb_command edge cases."""
    result = await execute_dynamodb_command(command='  aws s3 ls  ')
    assert "Command must start with 'aws dynamodb'" in str(result)

    result = await execute_dynamodb_command(command='')
    assert "Command must start with 'aws dynamodb'" in str(result)

    with patch('awslabs.dynamodb_mcp_server.server.call_aws') as mock_call_aws:
        mock_call_aws.return_value = {'error': 'Invalid syntax'}

        result = await execute_dynamodb_command(command='aws dynamodb invalid-operation')
        assert result == {'error': 'Invalid syntax'}


@pytest.mark.asyncio
async def test_dynamodb_data_model_validation_file_permissions():
    """Test dynamodb_data_model_validation with file permission issues."""
    with patch('os.path.exists') as mock_exists:
        with patch('builtins.open') as mock_open_func:
            mock_exists.return_value = True
            mock_open_func.side_effect = PermissionError('Permission denied')

            result = await dynamodb_data_model_validation(workspace_dir='/tmp')

            assert 'Permission denied' in result


@pytest.mark.asyncio
async def test_source_db_analyzer_managed_mode_not_implemented(tmp_path):
    """Test source_db_analyzer when managed mode raises NotImplementedError."""
    with patch(
        'awslabs.dynamodb_mcp_server.db_analyzer.analyzer_utils.execute_managed_analysis'
    ) as mock_execute:
        mock_execute.side_effect = NotImplementedError(
            'Managed mode is not yet implemented for PostgreSQL'
        )

        result = await source_db_analyzer(
            source_db_type='mysql',
            database_name='test_db',
            execution_mode='managed',
            aws_cluster_arn='test-cluster',
            aws_secret_arn='test-secret',
            aws_region='us-east-1',
            output_dir=str(tmp_path),
        )

        assert 'Managed mode is not yet implemented' in result


@pytest.mark.asyncio
async def test_source_db_analyzer_invalid_execution_mode(tmp_path):
    """Test source_db_analyzer with invalid execution mode."""
    result = await source_db_analyzer(
        source_db_type='mysql',
        database_name='test_db',
        execution_mode='invalid_mode',
        output_dir=str(tmp_path),
    )

    assert 'Invalid execution_mode' in result


@pytest.mark.asyncio
async def test_dynamodb_data_model_validation_guide_file_not_found():
    """Test dynamodb_data_model_validation when json_generation_guide.md is missing."""
    with patch('os.path.exists') as mock_exists:
        with patch('pathlib.Path.read_text') as mock_read_text:
            mock_exists.return_value = False  # data_model.json doesn't exist
            mock_read_text.side_effect = FileNotFoundError('Guide file not found')

            result = await dynamodb_data_model_validation(workspace_dir='/tmp')

            assert 'dynamodb_data_model.json not found' in result
            assert 'Please generate your data model' in result


@pytest.mark.asyncio
async def test_dynamodb_data_model_validation_file_not_found_exception():
    """Test dynamodb_data_model_validation when FileNotFoundError is raised during validation."""
    mock_data_model = {'tables': [], 'items': [], 'access_patterns': []}

    with patch('os.path.exists') as mock_exists:
        with patch('builtins.open', mock_open(read_data=json.dumps(mock_data_model))):
            with patch('awslabs.dynamodb_mcp_server.server.setup_dynamodb_local') as mock_setup:
                with patch(
                    'awslabs.dynamodb_mcp_server.server.create_validation_resources'
                ) as mock_create:
                    mock_exists.return_value = True
                    mock_setup.return_value = 'http://localhost:8000'
                    mock_create.side_effect = FileNotFoundError('Required file missing')

                    result = await dynamodb_data_model_validation(workspace_dir='/tmp')

                    assert 'Required file not found' in result
