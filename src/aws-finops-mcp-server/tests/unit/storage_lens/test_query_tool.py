"""Unit tests for the StorageLensQueryTool class."""

import pytest
from .fixtures import CSV_MANIFEST
from awslabs.aws_finops_mcp_server.models import (
    AthenaQueryExecution,
    ColumnDefinition,
    SchemaFormat,
    SchemaInfo,
    StorageLensQueryRequest,
)
from awslabs.aws_finops_mcp_server.storage_lens.query_tool import StorageLensQueryTool
from unittest.mock import AsyncMock, MagicMock, patch


class TestStorageLensQueryTool:
    """Unit tests for the StorageLensQueryTool class."""

    @pytest.fixture
    def query_tool(self):
        """Create a StorageLensQueryTool instance for testing."""
        return StorageLensQueryTool()

    @pytest.mark.asyncio
    @patch('awslabs.aws_finops_mcp_server.storage_lens.query_tool.ManifestHandler')
    @patch('awslabs.aws_finops_mcp_server.storage_lens.query_tool.AthenaHandler')
    async def test_query_storage_lens(
        self, mock_athena_handler_class, mock_manifest_handler_class, query_tool
    ):
        """Test the query_storage_lens method."""
        # Setup mocks
        mock_manifest_handler = MagicMock()
        mock_athena_handler = MagicMock()

        # Replace the instances in the query_tool with our mocks
        query_tool.manifest_handler = mock_manifest_handler
        query_tool.athena_handler = mock_athena_handler

        # Mock async methods with AsyncMock
        mock_manifest_handler.get_manifest = AsyncMock(return_value=CSV_MANIFEST)
        mock_athena_handler.setup_table = AsyncMock()

        # Create a Pydantic model for the query execution
        mock_athena_handler.execute_query = AsyncMock(
            return_value=AthenaQueryExecution(query_execution_id='test-id', status='STARTED')
        )

        mock_athena_handler.wait_for_query_completion = AsyncMock(
            return_value={
                'Status': {'State': 'SUCCEEDED'},
                'Statistics': {
                    'EngineExecutionTimeInMillis': 1000,
                    'DataScannedInBytes': 1024,
                    'TotalExecutionTimeInMillis': 1500,
                },
            }
        )
        mock_athena_handler.get_query_results = AsyncMock(
            return_value={
                'columns': ['column1', 'column2'],
                'rows': [{'column1': 'value1', 'column2': 'value2'}],
            }
        )

        # Mock regular methods
        mock_manifest_handler.extract_data_location.return_value = 's3://test-bucket/data/'
        mock_manifest_handler.parse_schema.return_value = SchemaInfo(
            format=SchemaFormat.CSV,
            columns=[ColumnDefinition(name='test_column', type='STRING')],
            skip_header=True,
        )
        mock_athena_handler.determine_output_location.return_value = (
            's3://test-bucket/athena-results/'
        )

        # Call the method
        request = StorageLensQueryRequest(
            manifest_location='s3://test-bucket/manifest.json',
            query='SELECT * FROM {table}',
            database_name='test_db',
            table_name='test_table',
        )
        result = await query_tool.query_storage_lens(request)

        # Assertions
        mock_manifest_handler.get_manifest.assert_awaited_once_with(
            's3://test-bucket/manifest.json'
        )
        mock_manifest_handler.extract_data_location.assert_called_once_with(CSV_MANIFEST)
        mock_manifest_handler.parse_schema.assert_called_once_with(CSV_MANIFEST)

        mock_athena_handler.setup_table.assert_awaited_once()
        mock_athena_handler.execute_query.assert_awaited_once_with(
            'SELECT * FROM test_db.test_table', 'test_db', 's3://test-bucket/athena-results/'
        )

        # Check that the result is a QueryResult object with the expected attributes
        assert hasattr(result, 'statistics')
        assert hasattr(result, 'query')
        assert result.query == 'SELECT * FROM test_db.test_table'

    @pytest.mark.asyncio
    @patch('awslabs.aws_finops_mcp_server.storage_lens.query_tool.ManifestHandler')
    @patch('awslabs.aws_finops_mcp_server.storage_lens.query_tool.AthenaHandler')
    async def test_query_storage_lens_with_default_params(
        self, mock_athena_handler_class, mock_manifest_handler_class, query_tool
    ):
        """Test the query_storage_lens method with default parameters."""
        # Setup mocks
        mock_manifest_handler = MagicMock()
        mock_athena_handler = MagicMock()

        # Replace the instances in the query_tool with our mocks
        query_tool.manifest_handler = mock_manifest_handler
        query_tool.athena_handler = mock_athena_handler

        # Mock async methods with AsyncMock
        mock_manifest_handler.get_manifest = AsyncMock(return_value=CSV_MANIFEST)
        mock_athena_handler.setup_table = AsyncMock()

        # Create a Pydantic model for the query execution
        mock_athena_handler.execute_query = AsyncMock(
            return_value=AthenaQueryExecution(query_execution_id='test-id', status='STARTED')
        )

        mock_athena_handler.wait_for_query_completion = AsyncMock(
            return_value={
                'Status': {'State': 'SUCCEEDED'},
                'Statistics': {
                    'EngineExecutionTimeInMillis': 1000,
                    'DataScannedInBytes': 1024,
                    'TotalExecutionTimeInMillis': 1500,
                },
            }
        )
        mock_athena_handler.get_query_results = AsyncMock(
            return_value={
                'columns': ['column1', 'column2'],
                'rows': [{'column1': 'value1', 'column2': 'value2'}],
            }
        )

        # Mock regular methods
        mock_manifest_handler.extract_data_location.return_value = 's3://test-bucket/data/'
        mock_manifest_handler.parse_schema.return_value = SchemaInfo(
            format=SchemaFormat.CSV,
            columns=[ColumnDefinition(name='test_column', type='STRING')],
            skip_header=True,
        )
        mock_athena_handler.determine_output_location.return_value = (
            's3://test-bucket/athena-results/'
        )

        # Call the method with minimal parameters
        request = StorageLensQueryRequest(
            manifest_location='s3://test-bucket/manifest.json', query='SELECT * FROM {table}'
        )
        result = await query_tool.query_storage_lens(request)

        # Assertions
        mock_manifest_handler.get_manifest.assert_awaited_once_with(
            's3://test-bucket/manifest.json'
        )
        mock_athena_handler.setup_table.assert_awaited_once()
        mock_athena_handler.execute_query.assert_awaited_once_with(
            'SELECT * FROM storage_lens_db.storage_lens_metrics',
            'storage_lens_db',
            's3://test-bucket/athena-results/',
        )

        # Check that the result is a QueryResult object with the expected attributes
        assert hasattr(result, 'statistics')
        assert hasattr(result, 'query')
        assert result.query == 'SELECT * FROM storage_lens_db.storage_lens_metrics'
