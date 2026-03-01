import json
import os
import pytest
import pytest_asyncio
from awslabs.dynamodb_mcp_server.db_analyzer import analyzer_utils
from awslabs.dynamodb_mcp_server.model_validation_utils import DynamoDBClientConfig
from awslabs.dynamodb_mcp_server.server import (
    _execute_access_patterns,
    _execute_dynamodb_command,
    _load_next_steps_prompt,
    app,
    create_server,
    dynamodb_data_model_schema_converter,
    dynamodb_data_model_schema_validator,
    dynamodb_data_model_validation,
    dynamodb_data_modeling,
    generate_data_access_layer,
    generate_resources,
    source_db_analyzer,
)
from hypothesis import given, settings
from hypothesis import strategies as st
from pathlib import Path
from unittest.mock import Mock, mock_open, patch


@pytest_asyncio.fixture
async def aws_credentials():
    """Mocked AWS Credentials for moto."""
    os.environ['AWS_DEFAULT_REGION'] = 'us-west-2'


@pytest.mark.asyncio
async def test_dynamodb_data_modeling():
    """Test the dynamodb_data_modeling tool directly and MCP integration."""
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


# Tests for _execute_dynamodb_command (private function)
@pytest.mark.asyncio
async def test_execute_dynamodb_command_valid_command():
    """Test _execute_dynamodb_command with valid DynamoDB command."""
    with patch('awslabs.dynamodb_mcp_server.server.call_aws') as mock_call_aws:
        mock_call_aws.return_value = {'Tables': []}

        result = await _execute_dynamodb_command(
            command='aws dynamodb list-tables', endpoint_url='http://localhost:8000'
        )

        assert result == {'Tables': []}
        mock_call_aws.assert_called_once()
        args, kwargs = mock_call_aws.call_args
        assert args[0] == 'aws dynamodb list-tables --endpoint-url http://localhost:8000'


@pytest.mark.asyncio
async def test_execute_dynamodb_command_invalid_command():
    """Test _execute_dynamodb_command with invalid command raises ValueError."""
    with pytest.raises(ValueError, match="Command must start with 'aws dynamodb'"):
        await _execute_dynamodb_command(command='aws s3 ls')


@pytest.mark.asyncio
async def test_execute_dynamodb_command_without_endpoint():
    """Test _execute_dynamodb_command without endpoint URL."""
    with patch('awslabs.dynamodb_mcp_server.server.call_aws') as mock_call_aws:
        mock_call_aws.return_value = {'Tables': ['MyTable']}

        result = await _execute_dynamodb_command(command='aws dynamodb list-tables')

        assert result == {'Tables': ['MyTable']}
        mock_call_aws.assert_called_once()
        args, kwargs = mock_call_aws.call_args
        assert 'aws dynamodb list-tables' in args[0]


@pytest.mark.asyncio
async def test_execute_dynamodb_command_with_endpoint_sets_env_vars():
    """Test that _execute_dynamodb_command sets AWS environment variables when endpoint_url is provided."""
    original_env = os.environ.copy()

    try:
        with patch('awslabs.dynamodb_mcp_server.server.call_aws') as mock_call_aws:
            mock_call_aws.return_value = {'Tables': []}

            await _execute_dynamodb_command(
                command='aws dynamodb list-tables', endpoint_url='http://localhost:8000'
            )

            assert os.environ['AWS_ACCESS_KEY_ID'] == DynamoDBClientConfig.DUMMY_ACCESS_KEY
            assert os.environ['AWS_SECRET_ACCESS_KEY'] == DynamoDBClientConfig.DUMMY_SECRET_KEY
            assert 'AWS_DEFAULT_REGION' in os.environ
    finally:
        os.environ.clear()
        os.environ.update(original_env)


@pytest.mark.asyncio
async def test_execute_dynamodb_command_exception_handling():
    """Test _execute_dynamodb_command exception handling."""
    with patch('awslabs.dynamodb_mcp_server.server.call_aws') as mock_call_aws:
        test_exception = Exception('AWS CLI error')
        mock_call_aws.side_effect = test_exception

        result = await _execute_dynamodb_command(command='aws dynamodb list-tables')

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

    with patch('awslabs.dynamodb_mcp_server.server._execute_dynamodb_command') as mock_execute:
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

    with patch('awslabs.dynamodb_mcp_server.server._execute_dynamodb_command') as mock_execute:
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


@settings(max_examples=100)
@given(
    st.text(min_size=0, max_size=200).filter(lambda s: not s.strip().startswith('aws dynamodb'))
)
def test_property_command_validation_preservation(invalid_command: str):
    """Property test: Command validation preservation.

    *For any* command string that does not start with 'aws dynamodb', calling
    `_execute_dynamodb_command` SHALL raise a `ValueError` with the message
    "Command must start with 'aws dynamodb'".

    This property test verifies that the command validation logic correctly rejects
    all invalid commands regardless of their content.
    """
    import asyncio

    async def check_validation():
        with pytest.raises(ValueError) as exc_info:
            await _execute_dynamodb_command(command=invalid_command)
        return exc_info.value

    # Run the async check
    error = asyncio.get_event_loop().run_until_complete(check_validation())

    # Verify the error message is exactly as specified
    assert str(error) == "Command must start with 'aws dynamodb'", (
        f"Expected error message 'Command must start with 'aws dynamodb'', got '{str(error)}'"
    )


@settings(max_examples=100)
@given(
    st.text(min_size=1, max_size=100).filter(
        lambda s: s.strip() and not any(c in s for c in [' ', '\n', '\t', '\r'])
    )
)
def test_property_endpoint_url_credential_configuration(endpoint_url: str):
    """Property test: Endpoint URL credential configuration.

    *For any* non-None endpoint_url provided to `_execute_dynamodb_command`, the function
    SHALL set `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, and `AWS_DEFAULT_REGION`
    environment variables before executing the command.

    This property test verifies that when an endpoint URL is provided, the function
    correctly configures fake AWS credentials for DynamoDB Local.
    """
    import asyncio

    # Save original environment
    original_env = os.environ.copy()

    try:
        # Clear relevant env vars to ensure we're testing the function's behavior
        for key in ['AWS_ACCESS_KEY_ID', 'AWS_SECRET_ACCESS_KEY', 'AWS_DEFAULT_REGION']:
            os.environ.pop(key, None)

        async def check_credential_configuration():
            with patch('awslabs.dynamodb_mcp_server.server.call_aws') as mock_call_aws:
                mock_call_aws.return_value = {'Tables': []}

                # Execute with the generated endpoint URL
                await _execute_dynamodb_command(
                    command='aws dynamodb list-tables', endpoint_url=endpoint_url
                )

                # Verify credentials were set
                assert 'AWS_ACCESS_KEY_ID' in os.environ, (
                    'AWS_ACCESS_KEY_ID should be set when endpoint_url is provided'
                )
                assert 'AWS_SECRET_ACCESS_KEY' in os.environ, (
                    'AWS_SECRET_ACCESS_KEY should be set when endpoint_url is provided'
                )
                assert 'AWS_DEFAULT_REGION' in os.environ, (
                    'AWS_DEFAULT_REGION should be set when endpoint_url is provided'
                )

                # Verify the expected fake credential values
                assert (
                    os.environ['AWS_ACCESS_KEY_ID']
                    == DynamoDBClientConfig.DUMMY_ACCESS_KEY  # pragma: allowlist secret
                ), 'AWS_ACCESS_KEY_ID should be set to the expected fake value'
                assert (
                    os.environ['AWS_SECRET_ACCESS_KEY']
                    == DynamoDBClientConfig.DUMMY_SECRET_KEY  # pragma: allowlist secret
                ), 'AWS_SECRET_ACCESS_KEY should be set to the expected fake value'

        # Run the async check
        asyncio.get_event_loop().run_until_complete(check_credential_configuration())

    finally:
        # Restore original environment
        os.environ.clear()
        os.environ.update(original_env)


@settings(max_examples=100)
@given(
    st.text(min_size=1, max_size=100).filter(
        lambda s: s.strip() and not any(c in s for c in [' ', '\n', '\t', '\r'])
    )
)
def test_property_endpoint_url_command_modification(endpoint_url: str):
    """Property test: Endpoint URL command modification.

    *For any* non-None endpoint_url provided to `_execute_dynamodb_command`, the command
    passed to `call_aws` SHALL contain `--endpoint-url {endpoint_url}` appended to the
    original command.

    This property test verifies that when an endpoint URL is provided, the function
    correctly appends the endpoint URL flag to the command before execution.
    """
    import asyncio

    # Save original environment
    original_env = os.environ.copy()

    try:

        async def check_command_modification():
            with patch('awslabs.dynamodb_mcp_server.server.call_aws') as mock_call_aws:
                mock_call_aws.return_value = {'Tables': []}

                original_command = 'aws dynamodb list-tables'

                # Execute with the generated endpoint URL
                await _execute_dynamodb_command(
                    command=original_command, endpoint_url=endpoint_url
                )

                # Verify call_aws was called
                mock_call_aws.assert_called_once()

                # Get the command that was passed to call_aws
                args, kwargs = mock_call_aws.call_args
                actual_command = args[0]

                # Property: The command passed to call_aws SHALL contain --endpoint-url {endpoint_url}
                expected_suffix = f'--endpoint-url {endpoint_url}'
                assert expected_suffix in actual_command, (
                    f"Command should contain '{expected_suffix}', but got: '{actual_command}'"
                )

                # Property: The original command should still be present
                assert original_command in actual_command, (
                    f"Original command '{original_command}' should be preserved in: '{actual_command}'"
                )

                # Property: The endpoint URL should be appended (not prepended)
                assert actual_command.startswith(original_command), (
                    f"Command should start with original command '{original_command}', "
                    f"but got: '{actual_command}'"
                )

        # Run the async check
        asyncio.get_event_loop().run_until_complete(check_command_modification())

    finally:
        # Restore original environment
        os.environ.clear()
        os.environ.update(original_env)


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
    """Test _execute_dynamodb_command edge cases."""
    # Test with whitespace-padded invalid command
    with pytest.raises(ValueError, match="Command must start with 'aws dynamodb'"):
        await _execute_dynamodb_command(command='  aws s3 ls  ')

    # Test with empty command
    with pytest.raises(ValueError, match="Command must start with 'aws dynamodb'"):
        await _execute_dynamodb_command(command='')

    # Test with valid command that returns error response
    with patch('awslabs.dynamodb_mcp_server.server.call_aws') as mock_call_aws:
        mock_call_aws.return_value = {'error': 'Invalid syntax'}

        result = await _execute_dynamodb_command(command='aws dynamodb invalid-operation')
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


@settings(max_examples=100)
@given(
    st.text(min_size=1, max_size=50).filter(lambda s: s.strip()),  # pattern_id
    st.text(min_size=1, max_size=100).filter(lambda s: s.strip()),  # description
    st.sampled_from(
        ['scan', 'query', 'get-item', 'put-item', 'delete-item', 'update-item']
    ),  # dynamodb_operation
)
def test_property_access_pattern_response_format_consistency(
    pattern_id: str,
    description: str,
    dynamodb_operation: str,
):
    """Property test: Access pattern response format consistency.

    *For any* valid access pattern executed through `_execute_access_patterns`, the response
    dictionary SHALL contain keys `pattern_id`, `description`, `dynamodb_operation`, `command`,
    and `response`.

    This property test verifies that regardless of the access pattern content, the response
    format remains consistent with the required keys.
    """
    import asyncio
    import tempfile

    # Build a valid access pattern with the generated values
    command = f'aws dynamodb {dynamodb_operation} --table-name TestTable'
    access_pattern = {
        'pattern': pattern_id,
        'description': description,
        'dynamodb_operation': dynamodb_operation,
        'implementation': command,
    }

    async def check_response_format():
        with patch('awslabs.dynamodb_mcp_server.server._execute_dynamodb_command') as mock_execute:
            with patch('builtins.open', mock_open()):
                # Mock successful command execution
                mock_execute.return_value = {'Items': [], 'Count': 0}

                with tempfile.TemporaryDirectory() as tmp_dir:
                    result = await _execute_access_patterns(
                        tmp_dir, [access_pattern], endpoint_url='http://localhost:8000'
                    )

                    # Verify the response structure
                    assert 'validation_response' in result, (
                        'Response should contain validation_response key'
                    )

                    validation_response = result['validation_response']
                    assert len(validation_response) == 1, (
                        'Should have exactly one response for one access pattern'
                    )

                    pattern_result = validation_response[0]

                    # Property: Response SHALL contain all required keys
                    required_keys = {
                        'pattern_id',
                        'description',
                        'dynamodb_operation',
                        'command',
                        'response',
                    }
                    actual_keys = set(pattern_result.keys())

                    assert required_keys == actual_keys, (
                        f'Response keys mismatch. Expected: {required_keys}, Got: {actual_keys}'
                    )

                    # Verify the values match the input
                    assert pattern_result['pattern_id'] == pattern_id, (
                        f'pattern_id mismatch. Expected: {pattern_id}, Got: {pattern_result["pattern_id"]}'
                    )
                    assert pattern_result['description'] == description, (
                        f'description mismatch. Expected: {description}, Got: {pattern_result["description"]}'
                    )
                    assert pattern_result['dynamodb_operation'] == dynamodb_operation, (
                        f'dynamodb_operation mismatch. Expected: {dynamodb_operation}, Got: {pattern_result["dynamodb_operation"]}'
                    )
                    assert pattern_result['command'] == command, (
                        f'command mismatch. Expected: {command}, Got: {pattern_result["command"]}'
                    )
                    assert 'response' in pattern_result, 'Response should contain response key'

    # Run the async check
    asyncio.get_event_loop().run_until_complete(check_response_format())


@settings(max_examples=100)
@given(
    st.text(min_size=1, max_size=50).filter(lambda s: s.strip()),  # pattern_id
    st.text(min_size=1, max_size=100).filter(lambda s: s.strip()),  # description
    st.sampled_from(
        ['scan', 'query', 'get-item', 'put-item', 'delete-item', 'update-item']
    ),  # dynamodb_operation
    st.text(min_size=1, max_size=100).filter(lambda s: s.strip()),  # error_message
)
def test_property_error_response_format_consistency(
    pattern_id: str,
    description: str,
    dynamodb_operation: str,
    error_message: str,
):
    """Property test: Error response format consistency.

    ** Error Response Format Consistency**

    *For any* access pattern that fails during execution, the error SHALL be captured in the
    `response` field of the result dictionary, maintaining the same format as successful executions.

    This property test verifies that when _execute_dynamodb_command returns an error (exception object
    or error dict), the response format remains consistent with successful executions - containing
    all required keys (pattern_id, description, dynamodb_operation, command, response).
    """
    import asyncio
    import tempfile

    # Build a valid access pattern with the generated values
    command = f'aws dynamodb {dynamodb_operation} --table-name TestTable'
    access_pattern = {
        'pattern': pattern_id,
        'description': description,
        'dynamodb_operation': dynamodb_operation,
        'implementation': command,
    }

    async def check_error_response_format():
        with patch('awslabs.dynamodb_mcp_server.server._execute_dynamodb_command') as mock_execute:
            with patch('builtins.open', mock_open()):
                # Mock command execution returning an error (as exception object converted to string)
                # This simulates what happens when _execute_dynamodb_command catches an exception
                mock_execute.return_value = Exception(error_message)

                with tempfile.TemporaryDirectory() as tmp_dir:
                    result = await _execute_access_patterns(
                        tmp_dir, [access_pattern], endpoint_url='http://localhost:8000'
                    )

                    # Verify the response structure is maintained even for errors
                    assert 'validation_response' in result, (
                        'Response should contain validation_response key even for errors'
                    )

                    validation_response = result['validation_response']
                    assert len(validation_response) == 1, (
                        'Should have exactly one response for one access pattern'
                    )

                    pattern_result = validation_response[0]

                    # Property: Error response SHALL maintain the same format as successful executions
                    required_keys = {
                        'pattern_id',
                        'description',
                        'dynamodb_operation',
                        'command',
                        'response',
                    }
                    actual_keys = set(pattern_result.keys())

                    assert required_keys == actual_keys, (
                        f'Error response keys mismatch. Expected: {required_keys}, Got: {actual_keys}'
                    )

                    # Verify the values match the input (same as successful execution)
                    assert pattern_result['pattern_id'] == pattern_id, (
                        f'pattern_id mismatch. Expected: {pattern_id}, Got: {pattern_result["pattern_id"]}'
                    )
                    assert pattern_result['description'] == description, (
                        f'description mismatch. Expected: {description}, Got: {pattern_result["description"]}'
                    )
                    assert pattern_result['dynamodb_operation'] == dynamodb_operation, (
                        f'dynamodb_operation mismatch. Expected: {dynamodb_operation}, Got: {pattern_result["dynamodb_operation"]}'
                    )
                    assert pattern_result['command'] == command, (
                        f'command mismatch. Expected: {command}, Got: {pattern_result["command"]}'
                    )

                    # Property: Error SHALL be captured in the response field
                    assert 'response' in pattern_result, (
                        'Error response should contain response key'
                    )

                    # The error should be converted to string representation
                    response_value = pattern_result['response']
                    assert isinstance(response_value, str), (
                        f'Error response should be converted to string, got: {type(response_value)}'
                    )
                    assert error_message in response_value, (
                        f'Error message should be captured in response. Expected to contain: {error_message}, Got: {response_value}'
                    )

    # Run the async check
    asyncio.get_event_loop().run_until_complete(check_error_response_format())


# Tests for generate_resources function
@pytest.mark.asyncio
async def test_generate_resources_cdk_success(tmp_path):
    """Test generate_resources with successful CDK generation."""
    json_file = tmp_path / 'dynamodb_data_model.json'
    json_file.write_text('{}')

    with patch('awslabs.dynamodb_mcp_server.server.CdkGenerator') as mock_generator_class:
        mock_generator = mock_generator_class.return_value
        mock_generator.generate.return_value = None

        result = await generate_resources(
            dynamodb_data_model_json_file=str(json_file), resource_type='cdk'
        )

        assert 'Successfully generated CDK project' in result
        assert str(tmp_path / 'cdk') in result
        mock_generator_class.assert_called_once()
        mock_generator.generate.assert_called_once_with(json_file)


@pytest.mark.asyncio
async def test_generate_resources_unsupported_resource_type(tmp_path):
    """Test generate_resources with unsupported resource type."""
    json_file = tmp_path / 'dynamodb_data_model.json'
    json_file.write_text('{}')

    result = await generate_resources(
        dynamodb_data_model_json_file=str(json_file), resource_type='terraform'
    )

    assert "Error: Unknown resource type 'terraform'" in result
    assert 'Supported types: cdk' in result


@pytest.mark.asyncio
async def test_generate_resources_cdk_generator_exception(tmp_path):
    """Test generate_resources when CdkGenerator raises an exception."""
    json_file = tmp_path / 'dynamodb_data_model.json'
    json_file.write_text('{}')

    with patch('awslabs.dynamodb_mcp_server.server.CdkGenerator') as mock_generator_class:
        mock_generator = mock_generator_class.return_value
        mock_generator.generate.side_effect = Exception('CDK generation failed')

        result = await generate_resources(
            dynamodb_data_model_json_file=str(json_file), resource_type='cdk'
        )

        # The @handle_exceptions decorator catches exceptions and returns them as {'error': str(e)}
        assert isinstance(result, dict)
        assert 'error' in result
        assert 'CDK generation failed' in result['error']


@pytest.mark.asyncio
async def test_generate_resources_mcp_integration():
    """Test generate_resources tool through MCP client."""
    tools = await app.list_tools()
    generate_tool = next((tool for tool in tools if tool.name == 'generate_resources'), None)

    assert generate_tool is not None
    assert generate_tool.description is not None
    assert 'generates resources from a dynamodb data model' in generate_tool.description.lower()
    assert 'cdk' in generate_tool.description.lower()


# Tests for compute_performances_and_costs function
@pytest.mark.asyncio
async def test_compute_performances_and_costs_basic(tmp_path):
    """Test compute_performances_and_costs with basic access patterns."""
    from awslabs.dynamodb_mcp_server.server import compute_performances_and_costs

    access_patterns = [
        {
            'operation': 'GetItem',
            'pattern': 'get-user',
            'description': 'Get user by ID',
            'table': 'users',
            'rps': 100,
            'item_size_bytes': 1024,
        }
    ]

    table_list = [
        {
            'name': 'users',
            'item_size_bytes': 2048,
            'item_count': 1000000,
            'gsi_list': [],
        }
    ]

    result = await compute_performances_and_costs(
        access_pattern_list=access_patterns,
        table_list=table_list,
        workspace_dir=str(tmp_path),
    )

    assert result['status'] == 'success'
    assert '1 access patterns' in result['message']
    assert '1 tables' in result['message']
    assert 'written to' in result['message']


@pytest.mark.asyncio
async def test_compute_performances_and_costs_appends_to_md_file(tmp_path):
    """Test compute_performances_and_costs appends to dynamodb_data_model.md when workspace_dir provided."""
    from awslabs.dynamodb_mcp_server.server import compute_performances_and_costs

    # Create the dynamodb_data_model.md file
    md_file = tmp_path / 'dynamodb_data_model.md'
    md_file.write_text('# DynamoDB Data Model\n\nExisting content here.\n')

    access_patterns = [
        {
            'operation': 'GetItem',
            'pattern': 'get-user',
            'description': 'Get user by ID',
            'table': 'users',
            'rps': 100,
            'item_size_bytes': 1024,
        }
    ]

    table_list = [
        {
            'name': 'users',
            'item_size_bytes': 2048,
            'item_count': 1000000,
            'gsi_list': [],
        }
    ]

    result = await compute_performances_and_costs(
        access_pattern_list=access_patterns,
        table_list=table_list,
        workspace_dir=str(tmp_path),
    )

    assert result['status'] == 'success'
    assert 'written to' in result['message']

    # Verify the file was appended
    content = md_file.read_text()
    assert 'Existing content here.' in content
    assert '## Cost Report' in content
    assert '### Read and Write Request Costs' in content


@pytest.mark.asyncio
async def test_compute_performances_and_costs_md_file_not_found(tmp_path):
    """Test compute_performances_and_costs when dynamodb_data_model.md doesn't exist - creates new file."""
    from awslabs.dynamodb_mcp_server.server import compute_performances_and_costs

    # Don't create the md file - it should be created by the tool

    access_patterns = [
        {
            'operation': 'GetItem',
            'pattern': 'get-user',
            'description': 'Get user by ID',
            'table': 'users',
            'rps': 100,
            'item_size_bytes': 1024,
        }
    ]

    table_list = [
        {
            'name': 'users',
            'item_size_bytes': 2048,
            'item_count': 1000000,
            'gsi_list': [],
        }
    ]

    result = await compute_performances_and_costs(
        access_pattern_list=access_patterns,
        table_list=table_list,
        workspace_dir=str(tmp_path),
    )

    # Should succeed and create the file
    assert result['status'] == 'success'
    assert 'written to' in result['message']

    # Verify the file was created
    md_file = tmp_path / 'dynamodb_data_model.md'
    assert md_file.exists()
    content = md_file.read_text()
    assert '## Cost Report' in content


@pytest.mark.asyncio
async def test_compute_performances_and_costs_with_query_pattern(tmp_path):
    """Test compute_performances_and_costs with Query access pattern."""
    from awslabs.dynamodb_mcp_server.server import compute_performances_and_costs

    md_file = tmp_path / 'dynamodb_data_model.md'
    md_file.write_text('# DynamoDB Data Model\n')

    access_patterns = [
        {
            'operation': 'Query',
            'pattern': 'query-orders',
            'description': 'Query user orders',
            'table': 'orders',
            'rps': 50,
            'item_size_bytes': 512,
            'item_count': 10,
            'gsi': None,
        }
    ]

    table_list = [
        {
            'name': 'orders',
            'item_size_bytes': 1024,
            'item_count': 5000000,
            'gsi_list': [],
        }
    ]

    result = await compute_performances_and_costs(
        access_pattern_list=access_patterns,
        table_list=table_list,
        workspace_dir=str(tmp_path),
    )

    assert result['status'] == 'success'
    content = md_file.read_text()
    assert '## Cost Report' in content


@pytest.mark.asyncio
async def test_compute_performances_and_costs_validation_error(tmp_path):
    """Test compute_performances_and_costs with invalid input."""
    from awslabs.dynamodb_mcp_server.server import compute_performances_and_costs

    # Invalid access pattern - missing required fields
    access_patterns = [
        {
            'operation': 'GetItem',
            'pattern': 'get-user',
            'description': 'Get user by ID',
            'table': 'users',
            'rps': 0,  # Invalid: must be > 0
            'item_size_bytes': 1024,
        }
    ]

    table_list = [
        {
            'name': 'users',
            'item_size_bytes': 2048,
            'item_count': 1000000,
            'gsi_list': [],
        }
    ]

    result = await compute_performances_and_costs(
        access_pattern_list=access_patterns,
        table_list=table_list,
        workspace_dir=str(tmp_path),
    )

    assert result['status'] == 'error'
    assert 'rps' in result['message'].lower()


@pytest.mark.asyncio
async def test_compute_performances_and_costs_mcp_integration():
    """Test compute_performances_and_costs tool through MCP client."""
    tools = await app.list_tools()
    cost_tool = next(
        (tool for tool in tools if tool.name == 'compute_performances_and_costs'), None
    )

    assert cost_tool is not None
    assert cost_tool.description is not None
    assert 'capacity' in cost_tool.description.lower()
    assert 'cost' in cost_tool.description.lower()


@pytest.mark.asyncio
async def test_dynamodb_data_model_schema_converter():
    """Test the dynamodb_data_model_schema_converter tool directly and MCP integration."""
    result = await dynamodb_data_model_schema_converter()

    assert isinstance(result, str), 'Expected string response'
    assert len(result) > 1000, 'Expected substantial content (>1000 characters)'

    expected_sections = [
        'DynamoDB Schema Generator Expert System Prompt',
        'Schema Structure',
        'Type System Overview',
        'Field Type Mappings',
        'Operation Mappings',
        'Return Type Mappings',
        'Template Syntax Rules',
        'Conversion Guidelines',
        'Validation and Iteration',
    ]

    for section in expected_sections:
        assert section in result, f"Expected section '{section}' not found in content"

    # Verify tool is registered in the MCP server
    tools = await app.list_tools()
    tool_names = [tool.name for tool in tools]
    assert 'dynamodb_data_model_schema_converter' in tool_names, (
        'dynamodb_data_model_schema_converter tool not found in MCP server'
    )

    # Get tool metadata
    converter_tool = next(
        (tool for tool in tools if tool.name == 'dynamodb_data_model_schema_converter'), None
    )
    assert converter_tool is not None, 'dynamodb_data_model_schema_converter tool not found'

    assert converter_tool.description is not None
    assert 'schema' in converter_tool.description.lower()
    assert 'convert' in converter_tool.description.lower()

    # Check for critical type mappings
    assert 'string' in result
    assert 'integer' in result
    assert 'decimal' in result
    assert 'boolean' in result
    assert 'array' in result
    assert 'object' in result
    assert 'uuid' in result

    # Check for operation types
    assert 'GetItem' in result
    assert 'PutItem' in result
    assert 'Query' in result
    assert 'UpdateItem' in result

    # Check for return types
    assert 'single_entity' in result
    assert 'entity_list' in result
    assert 'success_flag' in result

    # Check for validation tool reference
    assert 'dynamodb_data_model_schema_validator' in result


@pytest.mark.asyncio
async def test_dynamodb_data_model_schema_validator_valid_schema():
    """Test schema validator with a valid schema and MCP integration."""
    # Use a known valid schema from test fixtures
    schema_path = str(
        Path(__file__).parent
        / 'repo_generation_tool'
        / 'fixtures'
        / 'valid_schemas'
        / 'user_analytics'
        / 'user_analytics_schema.json'
    )

    result = await dynamodb_data_model_schema_validator(schema_path, None)

    assert isinstance(result, str), 'Expected string response'
    assert '✅ Schema validation passed!' in result
    assert '🎉 Validation completed successfully!' in result

    # Verify tool is registered in the MCP server
    tools = await app.list_tools()
    tool_names = [tool.name for tool in tools]
    assert 'dynamodb_data_model_schema_validator' in tool_names, (
        'dynamodb_data_model_schema_validator tool not found in MCP server'
    )

    # Get tool metadata
    validator_tool = next(
        (tool for tool in tools if tool.name == 'dynamodb_data_model_schema_validator'), None
    )
    assert validator_tool is not None, 'dynamodb_data_model_schema_validator tool not found'

    assert validator_tool.description is not None
    assert 'schema' in validator_tool.description.lower()
    assert 'validat' in validator_tool.description.lower()

    # Check that it has the required parameter
    assert validator_tool.inputSchema is not None
    assert 'properties' in validator_tool.inputSchema
    assert 'schema_path' in validator_tool.inputSchema['properties']


@pytest.mark.asyncio
async def test_dynamodb_data_model_schema_validator_invalid_schema():
    """Test schema validator with an invalid schema."""
    # Use a known invalid schema from test fixtures
    schema_path = str(
        Path(__file__).parent
        / 'repo_generation_tool'
        / 'fixtures'
        / 'invalid_schemas'
        / 'comprehensive_invalid_schema.json'
    )

    result = await dynamodb_data_model_schema_validator(schema_path, None)

    assert isinstance(result, str), 'Expected string response'
    assert '❌ Schema validation failed:' in result
    # Check for specific validation error format
    assert '•' in result  # Bullet points for errors
    assert '💡' in result  # Suggestions


@pytest.mark.asyncio
async def test_dynamodb_data_model_schema_validator_file_not_found(tmp_path, monkeypatch):
    """Test schema validator with non-existent file."""
    # Change to tmp_path to ensure we're testing within allowed directory
    monkeypatch.chdir(tmp_path)

    schema_path = 'nonexistent_schema.json'  # Relative path within CWD

    result = await dynamodb_data_model_schema_validator(schema_path, None)

    assert isinstance(result, str), 'Expected string response'
    assert 'Error: Schema file not found' in result
    assert 'nonexistent_schema.json' in result


@pytest.mark.asyncio
async def test_dynamodb_data_model_schema_validator_multiple_valid_schemas():
    """Test schema validator with multiple different valid schemas."""
    valid_schema_dirs = [
        'user_analytics',
        'ecommerce_app',
        'saas_app',
    ]

    fixtures_base = Path(__file__).parent / 'repo_generation_tool' / 'fixtures' / 'valid_schemas'

    for schema_dir in valid_schema_dirs:
        # Find the schema file in the directory
        schema_dir_path = fixtures_base / schema_dir
        if not schema_dir_path.exists():
            continue

        # Look for *schema.json files only (not usage_data.json)
        schema_files = list(schema_dir_path.glob('*schema.json'))
        if not schema_files:
            continue

        schema_path = str(schema_files[0])
        result = await dynamodb_data_model_schema_validator(schema_path, None)

        assert '✅ Schema validation passed!' in result, (
            f'Expected validation to pass for {schema_dir}'
        )
        assert '🎉 Validation completed successfully!' in result


@pytest.mark.asyncio
async def test_schema_validator_allows_any_directory(tmp_path):
    """Test that schema validator allows files in any directory (user's working directory)."""
    # Create a valid schema file in any directory (simulating user working in /tmp/t1, etc.)
    user_dir = tmp_path / 'user_workspace' / 'dynamodb_schema_123'
    user_dir.mkdir(parents=True, exist_ok=True)
    schema_file = user_dir / 'schema.json'

    # Write a valid minimal schema
    schema_file.write_text("""{
        "tables": [{
            "table_config": {
                "table_name": "TestTable",
                "partition_key": "pk",
                "sort_key": "sk"
            },
            "entities": {
                "TestEntity": {
                    "entity_type": "TestTable",
                    "pk_template": "TEST#{{id}}",
                    "sk_template": "META",
                    "fields": [
                        {"name": "id", "type": "string", "required": true}
                    ],
                    "access_patterns": []
                }
            }
        }]
    }""")

    result = await dynamodb_data_model_schema_validator(str(schema_file), None)

    # Should succeed - we allow any directory where the schema file exists
    # Should not have security error and should have validation result
    assert 'Security Error' not in result
    assert '✅' in result or '❌' in result


@pytest.mark.asyncio
async def test_generate_python_data_access_layer_success():
    """Test generate_data_access_layer with default and custom language parameter."""
    guide_content = '# Python DynamoDB Data Access Layer Implementation Expert System Prompt'

    mock_result = Mock()
    mock_result.success = True

    captured_calls = []

    def mock_generate(*args, **kwargs):
        captured_calls.append(kwargs)
        # Verify that output_dir is set to the default path (generated_dal in schema's parent dir)
        assert 'output_dir' in kwargs
        expected_default = str(Path('/path/to').resolve() / 'generated_dal')
        assert kwargs['output_dir'] == expected_default
        return mock_result

    with (
        patch('awslabs.dynamodb_mcp_server.server.Path.exists', return_value=True),
        patch('awslabs.dynamodb_mcp_server.server.Path.read_text', return_value=guide_content),
        patch('awslabs.dynamodb_mcp_server.server.generate', mock_generate),
    ):
        # Test without explicit language (default)
        result = await generate_data_access_layer(
            schema_path='/path/to/schema.json', usage_data_path=None
        )
        assert 'Code generation completed successfully in:' in result
        assert guide_content in result

        # Test with explicit language parameter
        result = await generate_data_access_layer(
            schema_path='/path/to/schema.json', language='python', usage_data_path=None
        )
        assert 'Code generation completed successfully in:' in result
        assert captured_calls[-1]['language'] == 'python'

    # Verify tool is registered in the MCP server
    tools = await app.list_tools()
    tool_names = [tool.name for tool in tools]
    assert 'generate_data_access_layer' in tool_names

    dal_tool = next((tool for tool in tools if tool.name == 'generate_data_access_layer'), None)
    assert dal_tool is not None
    assert dal_tool.description is not None
    assert 'Generate Python code for a data access layer' in dal_tool.description
    assert dal_tool.inputSchema is not None
    assert 'schema_path' in dal_tool.inputSchema['properties']


@pytest.mark.asyncio
async def test_generate_data_access_layer_generation_failure():
    """Test generate_data_access_layer when generation fails."""
    # Mock failed generation
    mock_result = Mock()
    mock_result.success = False
    mock_result.format_for_mcp.return_value = 'Generation failed: Invalid schema'

    def mock_generate(*args, **kwargs):
        return mock_result

    with (
        patch('pathlib.Path.exists', return_value=True),
        patch('awslabs.dynamodb_mcp_server.server.generate', mock_generate),
    ):
        result = await generate_data_access_layer(
            schema_path='/path/to/invalid_schema.json', usage_data_path=None
        )

        assert result == 'Generation failed: Invalid schema'


@pytest.mark.asyncio
async def test_generate_data_access_layer_file_not_found():
    """Test generate_data_access_layer when schema file doesn't exist."""
    with patch('awslabs.dynamodb_mcp_server.server.Path.exists', return_value=False):
        result = await generate_data_access_layer(
            schema_path='/path/to/nonexistent_schema.json', usage_data_path=None
        )

        # Now returns the full instructional message from MD file
        assert 'Error: schema.json not found at /path/to/nonexistent_schema.json' in result


@pytest.mark.asyncio
@pytest.mark.parametrize(
    'exception_class,exception_msg,expected_result',
    [
        (Exception, 'Test exception', 'Analysis failed: Test exception'),
        (ValueError, 'Path validation failed', 'Security Error: Path validation failed'),
    ],
)
async def test_generate_data_access_layer_exception_handling(
    exception_class, exception_msg, expected_result
):
    """Test generate_data_access_layer exception handling."""

    def mock_generate(*args, **kwargs):
        raise exception_class(exception_msg)

    with (
        patch('awslabs.dynamodb_mcp_server.server.Path.exists', return_value=True),
        patch('awslabs.dynamodb_mcp_server.server.generate', mock_generate),
    ):
        result = await generate_data_access_layer(
            schema_path='/path/to/schema.json', usage_data_path=None
        )

        assert expected_result == result


# Tests for _load_next_steps_prompt helper function
@pytest.mark.parametrize(
    'filename,kwargs,expected_content',
    [
        ('dynamodb_data_modeling_complete.md', {}, ['## Next Steps', 'Data modeling complete!']),
        (
            'generate_data_access_layer_schema_not_found.md',
            {'schema_path': '/test/path/schema.json'},
            ['/test/path/schema.json', 'Error: schema.json not found'],
        ),
    ],
)
def test_load_next_steps_prompt(filename, kwargs, expected_content):
    """Test _load_next_steps_prompt with and without variable substitution."""
    result = _load_next_steps_prompt(filename, **kwargs)

    assert isinstance(result, str)
    assert len(result) > 0
    for content in expected_content:
        assert content in result
    if kwargs:
        assert '{schema_path}' not in result  # Variable should be substituted


# Tests for usage_data_path resolution and path traversal protection
@pytest.mark.asyncio
async def test_usage_data_path_resolved(tmp_path):
    """Test that usage_data_path is resolved to absolute path in both validator and generator."""
    schema_file = tmp_path / 'schema.json'
    usage_data_file = tmp_path / 'usage_data.json'

    schema_content = """{
        "tables": [{
            "table_config": {
                "table_name": "TestTable",
                "partition_key": "pk",
                "sort_key": "sk"
            },
            "entities": {
                "TestEntity": {
                    "entity_type": "TestTable",
                    "pk_template": "TEST#{{id}}",
                    "sk_template": "META",
                    "fields": [
                        {"name": "id", "type": "string", "required": true}
                    ],
                    "access_patterns": []
                }
            }
        }]
    }"""
    schema_file.write_text(schema_content)

    usage_data_file.write_text("""{
        "entities": {
            "TestEntity": {
                "sample_data": {"id": "test-123"},
                "update_data": {"id": "test-456"}
            }
        }
    }""")

    # Test schema validator
    result = await dynamodb_data_model_schema_validator(str(schema_file), str(usage_data_file))
    assert 'expected str, bytes or os.PathLike object' not in result
    assert '✅' in result or '❌' in result

    # Test generate_data_access_layer
    result = await generate_data_access_layer(
        schema_path=str(schema_file), usage_data_path=str(usage_data_file)
    )
    assert 'expected str, bytes or os.PathLike object' not in result
    assert 'Code generation completed' in result or '❌' in result or 'Error' in result


@pytest.mark.asyncio
async def test_usage_data_path_none_handled():
    """Test that None usage_data_path is handled correctly in both validator and generator."""
    # Test schema validator
    schema_path = str(
        Path(__file__).parent
        / 'repo_generation_tool'
        / 'fixtures'
        / 'valid_schemas'
        / 'user_analytics'
        / 'user_analytics_schema.json'
    )

    result = await dynamodb_data_model_schema_validator(schema_path, None)

    # Should not have FieldInfo error
    assert 'FieldInfo' not in result
    assert 'expected str, bytes or os.PathLike object' not in result
    # Should have validation result
    assert '✅' in result or '❌' in result

    # Test generate_data_access_layer
    guide_content = '# Python DynamoDB Data Access Layer Implementation Expert System Prompt'

    mock_result = Mock()
    mock_result.success = True

    captured_kwargs = {}

    def mock_generate(*args, **kwargs):
        captured_kwargs.update(kwargs)
        return mock_result

    with (
        patch('awslabs.dynamodb_mcp_server.server.Path.exists', return_value=True),
        patch('awslabs.dynamodb_mcp_server.server.Path.read_text', return_value=guide_content),
        patch('awslabs.dynamodb_mcp_server.server.generate', mock_generate),
    ):
        result = await generate_data_access_layer(
            schema_path='/path/to/schema.json', usage_data_path=None
        )

        # Verify usage_data_path passed to generate is None
        usage_data_path_value = captured_kwargs.get('usage_data_path')
        assert usage_data_path_value is None, (
            f'Expected None, got {type(usage_data_path_value)}: {usage_data_path_value}'
        )

        # Should not have FieldInfo error in result
        assert 'FieldInfo' not in result
        assert 'expected str, bytes or os.PathLike object' not in result


@pytest.mark.asyncio
@pytest.mark.parametrize('test_func', ['schema_validator', 'generate_dal'])
async def test_usage_data_path_traversal_blocked(tmp_path, test_func):
    """Test that path traversal in usage_data_path is blocked with security error."""
    schema_file = tmp_path / 'schema.json'

    schema_file.write_text("""{
        "tables": [{
            "table_config": {
                "table_name": "TestTable",
                "partition_key": "pk",
                "sort_key": "sk"
            },
            "entities": {
                "TestEntity": {
                    "entity_type": "TestTable",
                    "pk_template": "TEST#{{id}}",
                    "sk_template": "META",
                    "fields": [
                        {"name": "id", "type": "string", "required": true}
                    ],
                    "access_patterns": []
                }
            }
        }]
    }""")

    # Attempt path traversal - the path gets resolved, then generate() validates it
    traversal_path = str(tmp_path / '..' / '..' / 'etc' / 'passwd')

    if test_func == 'schema_validator':
        result = await dynamodb_data_model_schema_validator(str(schema_file), traversal_path)
    else:
        result = await generate_data_access_layer(
            schema_path=str(schema_file), usage_data_path=traversal_path
        )

    # Path traversal should be blocked - generate() raises ValueError for paths outside allowed_base_dirs
    assert 'Security Error' in result or 'Error' in result


@pytest.mark.asyncio
async def test_dynamodb_data_model_schema_converter_without_usage_data():
    """Test schema converter with generate_usage_data=False."""
    result = await dynamodb_data_model_schema_converter(generate_usage_data=False)

    assert isinstance(result, str), 'Expected string response'
    assert len(result) > 1000, 'Expected substantial content'
    # Should have schema generator content but NOT usage data generator content
    assert 'DynamoDB Schema Generator Expert System Prompt' in result
    # Should NOT have the usage data generation instructions
    assert 'ADDITIONAL TASK: Generate Usage Data' not in result


@pytest.mark.asyncio
async def test_dynamodb_data_model_schema_validator_value_error(tmp_path):
    """Test schema validator ValueError handling."""
    schema_file = tmp_path / 'schema.json'
    schema_file.write_text('{"tables": []}')

    with patch('awslabs.dynamodb_mcp_server.server.generate') as mock_generate:
        mock_generate.side_effect = ValueError('Path outside allowed directories')

        result = await dynamodb_data_model_schema_validator(str(schema_file), None)

        assert 'Security Error' in result
        assert 'Path outside allowed directories' in result


@pytest.mark.asyncio
async def test_dynamodb_data_model_schema_validator_file_not_found_from_generate(tmp_path):
    """Test schema validator FileNotFoundError from generate() function.

    This tests the defensive exception handler (lines 292-293) that catches
    FileNotFoundError from generate() if the early check is bypassed.
    """
    schema_file = tmp_path / 'schema.json'
    schema_file.write_text('{"tables": []}')

    with patch('awslabs.dynamodb_mcp_server.server.generate') as mock_generate:
        mock_generate.side_effect = FileNotFoundError('Schema file not found')

        result = await dynamodb_data_model_schema_validator(str(schema_file), None)

        assert 'Error: Schema file not found' in result
        assert str(schema_file) in result


@pytest.mark.asyncio
async def test_dynamodb_data_model_schema_validator_unexpected_exception(tmp_path):
    """Test schema validator general Exception handling.

    This tests the defensive exception handler (lines 294-295) that catches
    unexpected exceptions from generate() function.
    """
    schema_file = tmp_path / 'schema.json'
    schema_file.write_text('{"tables": []}')

    with patch('awslabs.dynamodb_mcp_server.server.generate') as mock_generate:
        mock_generate.side_effect = RuntimeError('Unexpected internal error')

        result = await dynamodb_data_model_schema_validator(str(schema_file), None)

        assert 'Error during schema validation' in result
        assert 'Unexpected internal error' in result


def test_main_function():
    """Test main() entry point."""
    from awslabs.dynamodb_mcp_server.server import main

    with patch.object(app, 'run') as mock_run:
        main()
        mock_run.assert_called_once()


@pytest.mark.asyncio
async def test_call_tool_formats_validation_errors():
    """Test that call_tool intercepts ValidationError and reformats using format_validation_errors."""
    from mcp.server.fastmcp.exceptions import ToolError

    with pytest.raises(ToolError) as exc_info:
        await app.call_tool(
            'compute_performances_and_costs',
            {
                'access_pattern_list': [
                    {
                        'operation': 'GetItem',
                        'table': 'users',
                        'rps': 100,
                        'item_size_bytes': 1024,
                    }
                ],
                'table_list': [
                    {
                        'name': 'users',
                        'item_size_bytes': 2048,
                        'item_count': 1000000,
                    }
                ],
                'workspace_dir': '/tmp/test',
            },
        )

    error_message = str(exc_info.value)
    # Should use bracket notation from format_validation_errors
    assert 'access_pattern_list[0]' in error_message
    # Should NOT contain raw pydantic error fragments
    assert 'pydantic.dev' not in error_message
    assert '[type=missing' not in error_message


@pytest.mark.asyncio
async def test_call_tool_preserves_non_validation_errors():
    """Test that call_tool does NOT reformat non-ValidationError ToolErrors."""
    from mcp.server.fastmcp.exceptions import ToolError

    with pytest.raises(ToolError) as exc_info:
        await app.call_tool('nonexistent_tool_name', {})

    error_message = str(exc_info.value)
    assert 'Unknown tool' in error_message
