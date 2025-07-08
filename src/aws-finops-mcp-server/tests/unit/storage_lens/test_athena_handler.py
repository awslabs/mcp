"""Unit tests for the AthenaHandler class."""

import pytest
from awslabs.aws_finops_mcp_server.models import ColumnDefinition, SchemaFormat, SchemaInfo
from awslabs.aws_finops_mcp_server.storage_lens.athena_handler import AthenaHandler
from unittest.mock import patch


class TestAthenaHandler:
    """Unit tests for the AthenaHandler class."""

    @pytest.fixture
    def athena_handler(self):
        """Create an AthenaHandler instance for testing."""
        with patch('boto3.client') as mock_boto3:
            handler = AthenaHandler()
            # Replace the real Athena client with our mock
            handler.athena_client = mock_boto3.return_value
            yield handler

    @pytest.mark.asyncio
    async def test_execute_query(self, athena_handler):
        """Test executing an Athena query."""
        # Setup mock
        athena_handler.athena_client.start_query_execution.return_value = {
            'QueryExecutionId': 'test-execution-id'
        }

        # Call the method
        result = await athena_handler.execute_query(
            'SELECT * FROM test_table', 'test_database', 's3://test-bucket/athena-results/'
        )

        # Assertions
        athena_handler.athena_client.start_query_execution.assert_called_once_with(
            QueryString='SELECT * FROM test_table',
            QueryExecutionContext={'Database': 'test_database'},
            ResultConfiguration={'OutputLocation': 's3://test-bucket/athena-results/'},
        )
        assert result.query_execution_id == 'test-execution-id'
        assert result.status == 'STARTED'

    @pytest.mark.asyncio
    async def test_wait_for_query_completion(self, athena_handler):
        """Test waiting for query completion."""
        # Setup mock
        athena_handler.athena_client.get_query_execution.return_value = {
            'QueryExecution': {
                'Status': {'State': 'SUCCEEDED'},
                'Statistics': {
                    'EngineExecutionTimeInMillis': 1000,
                    'DataScannedInBytes': 1024,
                    'TotalExecutionTimeInMillis': 1500,
                },
            }
        }

        # Call the method
        result = await athena_handler.wait_for_query_completion('test-execution-id')

        # Assertions
        athena_handler.athena_client.get_query_execution.assert_called_once_with(
            QueryExecutionId='test-execution-id'
        )
        assert result['Status']['State'] == 'SUCCEEDED'

    @pytest.mark.asyncio
    async def test_get_query_results(self, athena_handler):
        """Test getting query results."""
        # Setup mock
        athena_handler.athena_client.get_query_results.return_value = {
            'ResultSet': {
                'ResultSetMetadata': {'ColumnInfo': [{'Label': 'column1'}, {'Label': 'column2'}]},
                'Rows': [
                    {'Data': [{'VarCharValue': 'column1'}, {'VarCharValue': 'column2'}]},
                    {'Data': [{'VarCharValue': 'value1'}, {'VarCharValue': 'value2'}]},
                ],
            }
        }

        # Call the method
        result = await athena_handler.get_query_results('test-execution-id')

        # Assertions
        athena_handler.athena_client.get_query_results.assert_called_once_with(
            QueryExecutionId='test-execution-id'
        )
        assert result['columns'] == ['column1', 'column2']
        assert len(result['rows']) == 1
        assert result['rows'][0]['column1'] == 'value1'
        assert result['rows'][0]['column2'] == 'value2'

    def test_determine_output_location(self, athena_handler):
        """Test determining output location."""
        # Test with provided output location
        result = athena_handler.determine_output_location(
            's3://data-bucket/data/', 's3://output-bucket/results/'
        )
        assert result == 's3://output-bucket/results/'

        # Test without provided output location
        result = athena_handler.determine_output_location('s3://data-bucket/data/')
        assert result == 's3://data-bucket/athena-results/'

    @pytest.mark.asyncio
    async def test_create_database(self, athena_handler):
        """Test creating a database."""

        # Mock execute_query as an async function
        async def mock_execute_query(*args, **kwargs):
            from awslabs.aws_finops_mcp_server.models import AthenaQueryExecution

            return AthenaQueryExecution(query_execution_id='test-id', status='STARTED')

        # Replace the method with our mock
        athena_handler.execute_query = mock_execute_query

        # Call the method
        await athena_handler.create_database('test_db', 's3://test-bucket/athena-results/')

        # We can't use assert_called_once_with with our async mock function
        # Instead, we'll patch the method and check the call args manually
        with patch.object(
            athena_handler, 'execute_query', side_effect=mock_execute_query
        ) as mock_method:
            await athena_handler.create_database('test_db', 's3://test-bucket/athena-results/')
            mock_method.assert_called_once_with(
                'CREATE DATABASE IF NOT EXISTS test_db',
                'default',
                's3://test-bucket/athena-results/',
            )

    @pytest.mark.asyncio
    async def test_create_table_for_csv(self, athena_handler):
        """Test creating a table for CSV data."""

        # Mock execute_query as an async function
        async def mock_execute_query(*args, **kwargs):
            from awslabs.aws_finops_mcp_server.models import AthenaQueryExecution

            return AthenaQueryExecution(query_execution_id='test-id', status='STARTED')

        # Replace the method with our mock
        athena_handler.execute_query = mock_execute_query

        # Call the method
        schema_info = SchemaInfo(
            format=SchemaFormat.CSV,
            columns=[
                ColumnDefinition(name='column1', type='STRING'),
                ColumnDefinition(name='column2', type='BIGINT'),
            ],
            skip_header=True,
        )

        # We'll patch the method and check if it's called with the right SQL
        with patch.object(
            athena_handler, 'execute_query', side_effect=mock_execute_query
        ) as mock_method:
            await athena_handler.create_table_for_csv(
                'test_db',
                'test_table',
                schema_info,
                's3://test-bucket/data/',
                's3://test-bucket/athena-results/',
            )

            # Check that execute_query was called once
            assert mock_method.call_count == 1

            # Check that the SQL contains the expected elements
            call_args = mock_method.call_args[0][0]
            assert 'CREATE EXTERNAL TABLE IF NOT EXISTS test_db.test_table' in call_args
            assert '`column1` STRING' in call_args
            assert '`column2` BIGINT' in call_args
            assert "LOCATION 's3://test-bucket/data/'" in call_args
