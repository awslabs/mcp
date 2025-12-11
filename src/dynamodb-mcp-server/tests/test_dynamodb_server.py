import json
import os
import pytest
import pytest_asyncio
from awslabs.dynamodb_mcp_server.database_analyzers import DatabaseAnalyzer, MySQLAnalyzer
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
        pattern_analysis_days=30,
        max_query_results=None,
        aws_cluster_arn='test-cluster',
        aws_secret_arn='test-secret',
        aws_region='us-east-1',
        output_dir=str(tmp_path),
    )

    assert 'To analyze your mysql database, I need:' in result


@pytest.mark.asyncio
async def test_source_db_analyzer_empty_parameters(tmp_path):
    """Test source_db_analyzer with empty string parameters."""
    result = await source_db_analyzer(
        source_db_type='mysql',
        database_name='test',
        pattern_analysis_days=30,
        max_query_results=None,
        aws_cluster_arn='  ',  # Empty after strip
        aws_secret_arn='test-secret',
        aws_region='us-east-1',
        output_dir=str(tmp_path),
    )

    assert 'To analyze your mysql database, I need:' in result


@pytest.mark.asyncio
async def test_source_db_analyzer_env_fallback(monkeypatch, tmp_path):
    """Test source_db_analyzer environment variable fallback."""
    # Set only some env vars to trigger fallback for others
    monkeypatch.setenv('MYSQL_SECRET_ARN', 'env-secret')
    monkeypatch.setenv('AWS_REGION', 'env-region')

    result = await source_db_analyzer(
        source_db_type='mysql',
        database_name='test',
        pattern_analysis_days=30,
        max_query_results=None,
        aws_cluster_arn=None,  # Will trigger env fallback
        aws_secret_arn=None,  # Will use env var
        aws_region=None,  # Will use env var
        output_dir=str(tmp_path),
    )

    # Should still fail due to missing cluster_arn, but covers env fallback lines
    assert 'To analyze your mysql database, I need:' in result


@pytest.mark.asyncio
async def test_source_db_analyzer_unsupported_database(tmp_path):
    """Test source_db_analyzer with unsupported database type."""
    result = await source_db_analyzer(
        source_db_type='postgresql',
        database_name='test_db',
        pattern_analysis_days=30,
        output_dir=str(tmp_path),
    )
    assert 'Unsupported database type: postgresql' in result

    result = await source_db_analyzer(
        source_db_type='oracle',
        database_name='test_db',
        pattern_analysis_days=30,
        output_dir=str(tmp_path),
    )
    assert 'Unsupported database type: oracle' in result


@pytest.mark.asyncio
async def test_source_db_analyzer_analysis_exception(tmp_path, monkeypatch):
    """Test source_db_analyzer when analysis raises exception."""

    # Mock analyze to raise exception
    async def mock_analyze_fail(connection_params):
        raise Exception('Database connection failed')

    monkeypatch.setattr(MySQLAnalyzer, 'analyze', mock_analyze_fail)

    result = await source_db_analyzer(
        source_db_type='mysql',
        database_name='test_db',
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
    async def mock_analyze_success(connection_params):
        return {
            'results': {'table_analysis': [{'table': 'users', 'rows': 100}]},
            'performance_enabled': True,
            'performance_feature': 'Performance Schema',
            'errors': ['Query 1 failed'],
        }

    def mock_save_files(*args):
        return ['/tmp/file1.json'], ['Error saving file2']

    monkeypatch.setattr(MySQLAnalyzer, 'analyze', mock_analyze_success)
    monkeypatch.setattr(DatabaseAnalyzer, 'save_analysis_files', mock_save_files)

    result = await source_db_analyzer(
        source_db_type='mysql',
        database_name='test_db',
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

    def mock_analyze(*args, **kwargs):
        raise Exception('Test exception')

    monkeypatch.setattr(
        'awslabs.dynamodb_mcp_server.database_analyzers.MySQLAnalyzer.analyze', mock_analyze
    )

    result = await source_db_analyzer(
        source_db_type='mysql',
        database_name='test_db',
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
    async def mock_analyze_all_failed(connection_params):
        return {
            'results': {},  # Empty results
            'performance_enabled': True,
            'errors': ['Query 1 failed', 'Query 2 failed', 'Query 3 failed'],
        }

    def mock_save_files(*args):
        return [], []

    monkeypatch.setattr(MySQLAnalyzer, 'analyze', mock_analyze_all_failed)
    monkeypatch.setattr(DatabaseAnalyzer, 'save_analysis_files', mock_save_files)

    result = await source_db_analyzer(
        source_db_type='mysql',
        database_name='test_db',
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
    async def mock_analyze_success(connection_params):
        return {
            'results': {'table_analysis': [{'table': 'users', 'rows': 100}]},
            'performance_enabled': True,
            'errors': [],
        }

    def mock_save_files_empty(*args):
        return [], []  # No files saved, no errors

    monkeypatch.setattr(MySQLAnalyzer, 'analyze', mock_analyze_success)
    monkeypatch.setattr(DatabaseAnalyzer, 'save_analysis_files', mock_save_files_empty)

    result = await source_db_analyzer(
        source_db_type='mysql',
        database_name='test_db',
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
    async def mock_analyze_success(connection_params):
        return {
            'results': {'table_analysis': [{'table': 'users', 'rows': 100}]},
            'performance_enabled': True,
            'errors': [],
        }

    def mock_save_files_success(*args):
        return ['/tmp/file1.json', '/tmp/file2.json'], []  # Files saved, no errors

    monkeypatch.setattr(MySQLAnalyzer, 'analyze', mock_analyze_success)
    monkeypatch.setattr(DatabaseAnalyzer, 'save_analysis_files', mock_save_files_success)

    result = await source_db_analyzer(
        source_db_type='mysql',
        database_name='test_db',
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
    # The @handle_exceptions decorator catches the ValueError and returns it as a string
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
        # Restore original environment
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

            # Verify file was written - check that open was called with the right pattern
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
        # The exception happens during execute_dynamodb_command
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

    # Mock all the external dependencies that might cause issues
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

                            # The function may not call all mocks due to AWS config issues
                            # Just verify that we got a result and it's a string
                            assert isinstance(result, str)

                            # Verify that the function at least attempted to process
                            assert 'Validation complete' in result


@pytest.mark.asyncio
async def test_dynamodb_data_model_validation_file_not_found():
    """Test dynamodb_data_model_validation when data model file doesn't exist."""
    with patch('os.path.exists') as mock_exists:
        mock_exists.return_value = False

        result = await dynamodb_data_model_validation(workspace_dir='/tmp')

        # The actual path will be different, so check for the key parts
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
    incomplete_data_model = {'tables': []}  # Missing 'items' and 'access_patterns'

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

                # The function catches all exceptions, so check for failure message
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


# Integration tests
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

                    # The function catches all exceptions, so check for failure message
                    assert 'Table creation failed' in result


# Edge case tests
@pytest.mark.asyncio
async def test_execute_dynamodb_command_edge_cases():
    """Test execute_dynamodb_command edge cases."""
    # Test with whitespace in command - should fail validation
    result = await execute_dynamodb_command(command='  aws s3 ls  ')
    assert "Command must start with 'aws dynamodb'" in str(result)

    # Test with empty command
    result = await execute_dynamodb_command(command='')
    assert "Command must start with 'aws dynamodb'" in str(result)

    # Test with command that starts correctly but has invalid syntax
    with patch('awslabs.dynamodb_mcp_server.server.call_aws') as mock_call_aws:
        mock_call_aws.return_value = {'error': 'Invalid syntax'}

        result = await execute_dynamodb_command(command='aws dynamodb invalid-operation')
        assert result == {'error': 'Invalid syntax'}


@pytest.mark.asyncio
async def test_source_db_analyzer_build_connection_params_exception():
    """Test source_db_analyzer when build_connection_params raises exception."""
    with patch(
        'awslabs.dynamodb_mcp_server.database_analyzers.DatabaseAnalyzer.build_connection_params'
    ) as mock_build:
        mock_build.side_effect = Exception('Connection params error')

        result = await source_db_analyzer(
            source_db_type='mysql', database_name='test_db', output_dir='/tmp'
        )

        # The @handle_exceptions decorator returns the exception as a dict
        assert isinstance(result, dict)
        assert result['error'] == 'Connection params error'


@pytest.mark.asyncio
async def test_source_db_analyzer_validate_connection_params_exception():
    """Test source_db_analyzer when validate_connection_params raises exception."""
    with patch(
        'awslabs.dynamodb_mcp_server.database_analyzers.DatabaseAnalyzer.validate_connection_params'
    ) as mock_validate:
        mock_validate.side_effect = Exception('Validation error')

        result = await source_db_analyzer(
            source_db_type='mysql', database_name='test_db', output_dir='/tmp'
        )

        # The @handle_exceptions decorator returns the exception as a dict
        assert isinstance(result, dict)
        assert result['error'] == 'Validation error'


@pytest.mark.asyncio
async def test_source_db_analyzer_save_analysis_files_exception():
    """Test source_db_analyzer when save_analysis_files raises exception."""

    async def mock_analyze_success(connection_params):
        return {
            'results': {'table_analysis': [{'table': 'users', 'rows': 100}]},
            'performance_enabled': True,
            'errors': [],
        }

    with patch(
        'awslabs.dynamodb_mcp_server.database_analyzers.MySQLAnalyzer.analyze',
        mock_analyze_success,
    ):
        with patch(
            'awslabs.dynamodb_mcp_server.database_analyzers.DatabaseAnalyzer.save_analysis_files'
        ) as mock_save:
            mock_save.side_effect = Exception('Save files error')

            result = await source_db_analyzer(
                source_db_type='mysql',
                database_name='test_db',
                aws_cluster_arn='test-cluster',
                aws_secret_arn='test-secret',
                aws_region='us-east-1',
                output_dir='/tmp',
            )

            assert 'Analysis failed: Save files error' in result


@pytest.mark.asyncio
async def test_dynamodb_data_model_validation_file_permissions():
    """Test dynamodb_data_model_validation with file permission issues."""
    with patch('os.path.exists') as mock_exists:
        with patch('builtins.open') as mock_open_func:
            mock_exists.return_value = True
            mock_open_func.side_effect = PermissionError('Permission denied')

            result = await dynamodb_data_model_validation(workspace_dir='/tmp')

            assert 'Permission denied' in result
