import os
import pytest
import pytest_asyncio
from awslabs.dynamodb_mcp_server.database_analyzers import DatabaseAnalyzer, MySQLAnalyzer
from awslabs.dynamodb_mcp_server.server import (
    app,
    dynamodb_data_modeling,
    source_db_analyzer,
)


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
