# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Unit tests for the storage_lens_tools module.

These tests verify the functionality of the S3 Storage Lens query tools, including:
- Running SQL queries against S3 Storage Lens metrics data in Athena
- Creating and updating Athena tables for Storage Lens data
- Handling manifest files and table schema generation
- Error handling for missing or invalid parameters
- Query execution, monitoring, and result processing
"""

import fastmcp
import importlib
import json
import os
import pytest
from awslabs.billing_cost_management_mcp_server.tools.storage_lens_tools import (
    AthenaHandler,
    ColumnDefinition,
    ManifestHandler,
    SchemaFormat,
    SchemaInfo,
    StorageLensQueryTool,
    storage_lens_server,
)
from fastmcp import Context
from tests.tools.fixtures import CSV_MANIFEST, PARQUET_MANIFEST
from unittest.mock import AsyncMock, MagicMock, patch


# Create a mock implementation for testing
async def mock_storage_lens_run_query(ctx, query, **kwargs):
    """Mock implementation of storage_lens_run_query for testing."""
    # Simple mock implementation

    # Log the original query for tests that check for this
    await ctx.info(f'Running Storage Lens query: {query}')

    # Check for manifest location
    manifest_location = kwargs.get('manifest_location')
    if not manifest_location:
        manifest_location = os.environ.get('STORAGE_LENS_MANIFEST_LOCATION')

    if not manifest_location:
        return {
            'status': 'error',
            'message': "Missing manifest location. Please provide 'manifest_location' parameter or set STORAGE_LENS_MANIFEST_LOCATION environment variable.",
        }

    # Return mock results
    return {'status': 'success', 'data': {'columns': ['column1'], 'rows': [{'column1': 'value1'}]}}


@pytest.fixture
def storage_lens_query_tool(mock_context):
    """Create a StorageLensQueryTool instance for testing."""
    with (
        patch(
            'awslabs.billing_cost_management_mcp_server.tools.storage_lens_tools.ManifestHandler'
        ) as mock_manifest_cls,
        patch(
            'awslabs.billing_cost_management_mcp_server.tools.storage_lens_tools.AthenaHandler'
        ) as mock_athena_cls,
    ):
        # Create the tool
        tool = StorageLensQueryTool(mock_context)
        # We'll manually inject mock handlers in tests
        yield tool, mock_manifest_cls, mock_athena_cls


# Using fixtures from fixtures.py


@pytest.fixture
def mock_s3_client():
    """Create a mock S3 client."""
    mock_client = MagicMock()
    mock_client.get_object.return_value = {
        'Body': MagicMock(read=lambda: json.dumps(CSV_MANIFEST).encode('utf-8'))
    }

    # Mock paginator
    mock_paginator = MagicMock()
    mock_client.get_paginator.return_value = mock_paginator

    # Mock paginate response
    mock_paginator.paginate.return_value = [
        {
            'Contents': [
                {
                    'Key': 'path/to/folder/manifest.json',
                    'LastModified': '2020-02-01T00:00:00Z',
                },
            ]
        }
    ]

    return mock_client


@pytest.fixture
def mock_athena_client():
    """Create a mock Athena client."""
    mock_client = MagicMock()

    # Mock responses for different operations
    mock_client.start_query_execution.return_value = {'QueryExecutionId': 'test-execution-id'}

    mock_client.get_query_execution.return_value = {
        'QueryExecution': {
            'Status': {'State': 'SUCCEEDED'},
            'Statistics': {
                'EngineExecutionTimeInMillis': 1000,
                'DataScannedInBytes': 1024,
                'TotalExecutionTimeInMillis': 1500,
            },
            'ResultConfiguration': {
                'OutputLocation': 's3://test-bucket/athena-results/test-execution-id.csv'
            },
        }
    }

    mock_client.get_query_results.return_value = {
        'ResultSet': {
            'ResultSetMetadata': {'ColumnInfo': [{'Label': 'column1'}, {'Label': 'column2'}]},
            'Rows': [
                {'Data': [{'VarCharValue': 'column1'}, {'VarCharValue': 'column2'}]},
                {'Data': [{'VarCharValue': 'value1'}, {'VarCharValue': 'value2'}]},
            ],
        }
    }

    return mock_client


@pytest.fixture
def mock_context():
    """Create a mock MCP context."""
    context = MagicMock(spec=Context)
    context.info = AsyncMock()
    context.error = AsyncMock()
    return context


@pytest.fixture
def manifest_handler(mock_context):
    """Create a ManifestHandler instance for testing."""
    with patch(
        'awslabs.billing_cost_management_mcp_server.tools.storage_lens_tools.create_aws_client'
    ) as mock_client_fn:
        handler = ManifestHandler(mock_context)
        # Replace the real S3 client with our mock
        handler.s3_client = mock_client_fn.return_value
        yield handler


@pytest.fixture
def athena_handler(mock_context):
    """Create an AthenaHandler instance for testing."""
    with patch(
        'awslabs.billing_cost_management_mcp_server.tools.storage_lens_tools.create_aws_client'
    ) as mock_client_fn:
        handler = AthenaHandler(mock_context)
        # Replace the real Athena client with our mock
        handler.athena_client = mock_client_fn.return_value
        yield handler


@pytest.mark.asyncio
async def test_storage_lens_run_query(mock_context):
    """Test the storage_lens_run_query function with valid parameters."""
    # Setup environment and mocks
    import os

    os.environ['STORAGE_LENS_MANIFEST_LOCATION'] = 's3://test-bucket/manifest.json'

    # Use the reload pattern to get the actual function
    stl_mod = _reload_storage_lens_with_identity_decorator()
    real_fn = stl_mod.storage_lens_run_query  # type: ignore

    # Mock the StorageLensQueryTool to avoid real AWS calls
    with patch.object(
        stl_mod.StorageLensQueryTool, 'query_storage_lens', new_callable=AsyncMock
    ) as mock_exec:
        mock_exec.return_value = {'status': 'success', 'data': {'ok': True}}

        # Call the function
        result = await real_fn(  # type: ignore
            mock_context,
            query="SELECT * FROM {table} WHERE metric_name = 'StorageBytes'",
            output_location='s3://test-bucket/athena-results/',
        )

    # Verify function behavior
    mock_context.info.assert_called_with(
        "Running Storage Lens query: SELECT * FROM {table} WHERE metric_name = 'StorageBytes'"
    )

    # Verify the result contains the expected data
    assert result['status'] == 'success'
    assert 'data' in result


@pytest.mark.asyncio
async def test_storage_lens_run_query_missing_manifest(mock_context):
    """Test storage_lens_run_query when manifest location is missing."""
    # Ensure environment variable is not set
    import os

    if 'STORAGE_LENS_MANIFEST_LOCATION' in os.environ:
        del os.environ['STORAGE_LENS_MANIFEST_LOCATION']

    # Use the reload pattern to get the actual function
    stl_mod = _reload_storage_lens_with_identity_decorator()
    real_fn = stl_mod.storage_lens_run_query  # type: ignore

    # Call the function without manifest_location parameter
    result = await real_fn(  # type: ignore
        mock_context,
        query='SELECT * FROM {table}',
    )

    # Verify the result is an error
    assert result['status'] == 'error'
    assert 'Missing manifest location' in result['message']


@pytest.mark.asyncio
async def test_storage_lens_run_query_table_replacement(mock_context):
    """Test the storage_lens_run_query function's table name replacement logic."""
    # Setup environment and mocks
    import os

    os.environ['STORAGE_LENS_MANIFEST_LOCATION'] = 's3://test-bucket/manifest.json'

    # Use the reload pattern to get the actual function
    stl_mod = _reload_storage_lens_with_identity_decorator()
    real_fn = stl_mod.storage_lens_run_query  # type: ignore

    # Mock the StorageLensQueryTool to avoid real AWS calls
    with patch.object(
        stl_mod.StorageLensQueryTool, 'query_storage_lens', new_callable=AsyncMock
    ) as mock_exec:
        mock_exec.return_value = {'status': 'success', 'data': {'ok': True}}

        # Call with {table} placeholder
        result1 = await real_fn(  # type: ignore
            mock_context,
            query='SELECT * FROM {table}',
            database_name='custom_db',
            table_name='custom_table',
        )

    # Verify success
    assert result1['status'] == 'success'

    # Call with explicit FROM clause but no placeholder
    with patch.object(
        stl_mod.StorageLensQueryTool, 'query_storage_lens', new_callable=AsyncMock
    ) as mock_exec2:
        mock_exec2.return_value = {'status': 'success', 'data': {'ok': True}}

        result2 = await real_fn(  # type: ignore
            mock_context,
            query='SELECT * FROM custom_db.custom_table',
        )

    # Verify success
    assert result2['status'] == 'success'


@pytest.mark.asyncio
async def test_athena_handler_execute_query_integration(mock_context, mock_athena_client):
    """Test the AthenaHandler execute_query method integration."""
    with patch(
        'awslabs.billing_cost_management_mcp_server.tools.storage_lens_tools.create_aws_client',
        return_value=mock_athena_client,
    ):
        athena_handler = AthenaHandler(mock_context)

        # Call the method
        result = await athena_handler.execute_query(
            'SELECT * FROM storage_lens_db.storage_lens_metrics',
            'storage_lens_db',
            's3://test-bucket/athena-results/',
        )

    # Verify function behavior
    mock_athena_client.start_query_execution.assert_called_once()
    assert result['query_execution_id'] == 'test-execution-id'
    assert result['status'] == 'STARTED'


@pytest.mark.asyncio
async def test_athena_handler_setup_table_integration(mock_context, mock_athena_client):
    """Test the AthenaHandler setup_table method integration."""
    with patch(
        'awslabs.billing_cost_management_mcp_server.tools.storage_lens_tools.create_aws_client',
        return_value=mock_athena_client,
    ):
        athena_handler = AthenaHandler(mock_context)

        # Create schema info for test
        schema_info = SchemaInfo(
            format=SchemaFormat.CSV,
            columns=[ColumnDefinition(name='test_column', type='STRING')],
            skip_header=True,
        )

        # Call the method
        await athena_handler.setup_table(
            'test_db',
            'test_table',
            schema_info,
            's3://test-bucket/data/',
            's3://test-bucket/athena-results/',
        )

    # Verify function behavior
    assert mock_athena_client.start_query_execution.call_count == 2  # Once for DB, once for table


def test_server_initialization():
    """Test that the storage_lens_server is properly initialized."""
    # Verify the server name
    assert storage_lens_server.name == 'storage-lens-tools'

    # Verify the server instructions
    instructions = storage_lens_server.instructions
    assert instructions is not None
    assert (
        'Tools for working with AWS S3 Storage Lens data' in instructions
        if instructions
        else False
    )


def _reload_storage_lens_with_identity_decorator():
    """Reload storage_lens_tools with FastMCP.tool patched to return the original function unchanged (identity decorator).

    This exposes a callable 'storage_lens_run_query' we can invoke directly.
    """
    from awslabs.billing_cost_management_mcp_server.tools import storage_lens_tools as stl_mod

    def _identity_tool(self, *args, **kwargs):
        def _decorator(fn):
            return fn

        return _decorator

    with patch.object(fastmcp.FastMCP, 'tool', _identity_tool):
        importlib.reload(stl_mod)
        return stl_mod


@pytest.mark.asyncio
async def test_storage_lens_real_missing_manifest_reload_identity_decorator(mock_context):
    """Test storage_lens_run_query missing manifest with identity decorator."""
    # Ensure no env var leaks in
    os.environ.pop('STORAGE_LENS_MANIFEST_LOCATION', None)

    stl_mod = _reload_storage_lens_with_identity_decorator()
    real_fn = stl_mod.storage_lens_run_query  # type: ignore

    res = await real_fn(mock_context, query='SELECT 1')  # type: ignore
    assert res['status'] == 'error'
    assert 'Missing manifest location' in res.get('message', '')


@pytest.mark.asyncio
async def test_storage_lens_real_placeholder_replacement_reload_identity_decorator(mock_context):
    """Test storage_lens_run_query placeholder replacement with identity decorator."""
    os.environ['STORAGE_LENS_MANIFEST_LOCATION'] = 's3://bucket/prefix/'

    stl_mod = _reload_storage_lens_with_identity_decorator()
    real_fn = stl_mod.storage_lens_run_query  # type: ignore

    with patch.object(
        stl_mod.StorageLensQueryTool, 'query_storage_lens', new_callable=AsyncMock
    ) as mock_exec:
        mock_exec.return_value = {'status': 'success', 'data': {'ok': True}}
        q = "SELECT * FROM {table} WHERE metric_name='StorageBytes'"
        res = await real_fn(mock_context, query=q)  # type: ignore
        assert res['status'] == 'success'

        # Check that the query tool was called
        assert mock_exec.await_args is not None


@pytest.mark.asyncio
async def test_storage_lens_real_from_insertion_reload_identity_decorator(mock_context):
    """Test storage_lens_run_query from insertion with identity decorator."""
    os.environ['STORAGE_LENS_MANIFEST_LOCATION'] = 's3://bucket/prefix/'

    stl_mod = _reload_storage_lens_with_identity_decorator()
    real_fn = stl_mod.storage_lens_run_query  # type: ignore

    with patch.object(
        stl_mod.StorageLensQueryTool, 'query_storage_lens', new_callable=AsyncMock
    ) as mock_exec:
        mock_exec.return_value = {'status': 'success', 'data': {'ok': True}}
        # No {table}, but has a FROM clause -> tool injects db.table
        q = "SELECT * from something WHERE region='us-east-1'"
        res = await real_fn(mock_context, query=q)  # type: ignore
        assert res['status'] == 'success'

        # Check that the query tool was called
        assert mock_exec.await_args is not None


@pytest.mark.asyncio
async def test_storage_lens_real_query_missing_table_reference_error_reload_identity_decorator(
    mock_context,
):
    """Test storage_lens_run_query missing table reference error with identity decorator."""
    os.environ['STORAGE_LENS_MANIFEST_LOCATION'] = 's3://bucket/prefix/'

    stl_mod = _reload_storage_lens_with_identity_decorator()
    real_fn = stl_mod.storage_lens_run_query  # type: ignore

    # Mock the ManifestHandler to avoid real S3 calls and allow the test to reach table validation
    with patch.object(
        stl_mod.ManifestHandler, 'get_manifest', new_callable=AsyncMock
    ) as mock_get_manifest:
        mock_get_manifest.return_value = {
            'reportFiles': [{'key': 'test/data/file.csv'}],
            'destinationBucket': 'test-bucket',
            'reportFormat': 'CSV',
            'reportSchema': 'col1,col2',
        }

        with patch.object(stl_mod.ManifestHandler, 'extract_data_location') as mock_extract:
            mock_extract.return_value = 's3://test-bucket/data/'

            with patch.object(stl_mod.ManifestHandler, 'parse_schema') as mock_parse:
                mock_parse.return_value = {
                    'format': stl_mod.SchemaFormat.CSV,
                    'columns': [{'name': 'col1', 'type': 'STRING'}],
                    'skip_header': True,
                }

                # Mock the AthenaHandler to avoid real Athena calls
                with patch.object(stl_mod.AthenaHandler, 'setup_table', new_callable=AsyncMock):
                    res = await real_fn(mock_context, query='SELECT 42')  # type: ignore
                    assert res['status'] == 'error'
                    assert 'must either contain {table} placeholder' in res.get('message', '')


@pytest.mark.asyncio
async def test_athena_handler_determine_output_location_trailing_slash(mock_context):
    """Test AthenaHandler determine_output_location with trailing slash."""
    athena_handler = AthenaHandler(mock_context)

    # Test with data location ending with '/'
    result = athena_handler.determine_output_location('s3://my-bucket/prefix/')
    assert result == 's3://my-bucket/athena-results/'


@pytest.mark.asyncio
async def test_athena_handler_determine_output_location_no_trailing_slash(mock_context):
    """Test AthenaHandler determine_output_location without trailing slash."""
    athena_handler = AthenaHandler(mock_context)

    # Test with data location not ending with '/'
    result = athena_handler.determine_output_location('s3://my-bucket/manifest.json')
    assert result == 's3://my-bucket/athena-results/'


@pytest.mark.asyncio
async def test_athena_handler_execute_query_exception_logs_and_raises(mock_context):
    """Test AthenaHandler execute_query exception path logs and raises."""
    with patch(
        'awslabs.billing_cost_management_mcp_server.tools.storage_lens_tools.create_aws_client'
    ) as mock_create_client:
        mock_athena_client = MagicMock()
        mock_athena_client.start_query_execution.side_effect = Exception('oops db')
        mock_create_client.return_value = mock_athena_client

        athena_handler = AthenaHandler(mock_context)

        with pytest.raises(Exception, match='Error starting Athena query: oops db'):
            await athena_handler.execute_query(
                'SELECT 1',
                'test_db',
                's3://test-bucket/athena-results/',
            )

    mock_context.error.assert_awaited()
    mock_athena_client.start_query_execution.assert_called()


@pytest.mark.asyncio
async def test_manifest_handler_get_manifest_exact_path(mock_context, manifest_handler):
    """Test getting a manifest from an exact path."""
    # Setup mock
    manifest_handler.s3_client.get_object.return_value = {
        'Body': MagicMock(read=lambda: json.dumps(CSV_MANIFEST).encode('utf-8'))
    }

    # Call the method
    result = await manifest_handler.get_manifest('s3://my-bucket/path/to/manifest.json')

    # Assertions
    manifest_handler.s3_client.get_object.assert_called_once_with(
        Bucket='my-bucket', Key='path/to/manifest.json'
    )
    assert result == CSV_MANIFEST


@pytest.mark.asyncio
async def test_manifest_handler_read_manifest_file_error(mock_context, manifest_handler):
    """Test error handling when reading a manifest file fails."""
    # Setup mock to raise an exception
    manifest_handler.s3_client.get_object.side_effect = Exception('Access denied')

    # Call the method and expect an exception
    with pytest.raises(Exception) as excinfo:
        await manifest_handler._read_manifest_file('my-bucket', 'path/to/manifest.json')

    # Verify the error message
    assert 'Failed to read manifest file' in str(excinfo.value)


@pytest.mark.asyncio
async def test_manifest_handler_find_latest_manifest(mock_context, manifest_handler):
    """Test finding the latest manifest in a folder."""
    # Mock paginator
    mock_paginator = MagicMock()
    manifest_handler.s3_client.get_paginator.return_value = mock_paginator

    # Mock paginate response
    mock_paginator.paginate.return_value = [
        {
            'Contents': [
                {
                    'Key': 'path/to/folder/manifest1.json',
                    'LastModified': '2020-01-01T00:00:00Z',
                },
                {
                    'Key': 'path/to/folder/manifest.json',
                    'LastModified': '2020-02-01T00:00:00Z',
                },
            ]
        }
    ]

    # Mock get_object response
    manifest_handler.s3_client.get_object.return_value = {
        'Body': MagicMock(read=lambda: json.dumps(CSV_MANIFEST).encode('utf-8'))
    }

    # Call the method
    result = await manifest_handler._find_latest_manifest('my-bucket', 'path/to/folder')

    # Assertions
    manifest_handler.s3_client.get_paginator.assert_called_once_with('list_objects_v2')
    mock_paginator.paginate.assert_called_once_with(Bucket='my-bucket', Prefix='path/to/folder/')
    manifest_handler.s3_client.get_object.assert_called_once()
    assert result == CSV_MANIFEST


@pytest.mark.asyncio
async def test_manifest_handler_find_latest_manifest_empty(mock_context, manifest_handler):
    """Test finding the latest manifest when no manifests exist."""
    # Mock paginator
    mock_paginator = MagicMock()
    manifest_handler.s3_client.get_paginator.return_value = mock_paginator

    # Mock empty paginate response
    mock_paginator.paginate.return_value = [{'Contents': []}]

    # Call the method and expect an exception
    with pytest.raises(Exception) as excinfo:
        await manifest_handler._find_latest_manifest('my-bucket', 'path/to/folder')

    # Verify the error message
    assert 'No manifest.json files found' in str(excinfo.value)


@pytest.mark.asyncio
async def test_manifest_handler_find_latest_manifest_no_contents(mock_context, manifest_handler):
    """Test finding the latest manifest when the response has no Contents key."""
    # Mock paginator
    mock_paginator = MagicMock()
    manifest_handler.s3_client.get_paginator.return_value = mock_paginator

    # Mock response with no Contents key
    mock_paginator.paginate.return_value = [{}]

    # Call the method and expect an exception
    with pytest.raises(Exception) as excinfo:
        await manifest_handler._find_latest_manifest('my-bucket', 'path/to/folder')

    # Verify the error message
    assert 'No manifest.json files found' in str(excinfo.value)


def test_manifest_handler_extract_data_location(manifest_handler):
    """Test extracting data location from manifest."""
    # Call the method
    result = manifest_handler.extract_data_location(CSV_MANIFEST)

    # Assertions
    expected = 'DestinationPrefix/StorageLens/123456789012/my-dashboard-configuration-id/V_1/reports/dt=2020-11-03'  # pragma: allowlist secret
    assert result.endswith(expected)


def test_manifest_handler_extract_data_location_empty_report_files(manifest_handler):
    """Test extracting data location when no report files exist."""
    # Create a manifest with no report files
    empty_manifest = {**CSV_MANIFEST, 'reportFiles': []}

    # Call the method and expect an exception
    with pytest.raises(Exception) as excinfo:
        manifest_handler.extract_data_location(empty_manifest)

    # Verify the error message
    assert 'No report files found in manifest' in str(excinfo.value)


def test_manifest_handler_extract_data_location_with_arn(manifest_handler):
    """Test extracting data location with ARN bucket format."""
    # Create a manifest with ARN format bucket
    arn_manifest = {**CSV_MANIFEST, 'destinationBucket': 'arn:aws:s3:::my-bucket'}

    # Call the method
    result = manifest_handler.extract_data_location(arn_manifest)

    # Verify the result starts with the correct bucket name
    assert result.startswith('s3://my-bucket/')


def test_manifest_handler_parse_schema_csv(manifest_handler):
    """Test parsing CSV schema from manifest."""
    # Call the method
    result = manifest_handler.parse_schema(CSV_MANIFEST)

    # Assertions
    assert result['format'].value == 'CSV'  # Compare enum values
    assert len(result['columns']) == 11
    assert result['columns'][0]['name'] == 'version_number'
    assert result['columns'][0]['type'] == 'STRING'


def test_manifest_handler_parse_schema_parquet(manifest_handler):
    """Test parsing Parquet schema from manifest."""
    # Call the method
    result = manifest_handler.parse_schema(PARQUET_MANIFEST)

    # Assertions
    assert result['format'].value == 'PARQUET'  # Compare enum values
    assert len(result['columns']) == 11
    assert result['columns'][0]['name'] == 'version_number'
    assert result['columns'][0]['type'] == 'STRING'
    assert result['columns'][10]['name'] == 'metric_value'
    assert result['columns'][10]['type'] == 'BIGINT'


def test_manifest_handler_parse_schema_parquet_unknown_type(manifest_handler):
    """Test parsing Parquet schema with unknown data types."""
    # Create a manifest with an unknown data type
    schema_with_unknown = {
        **PARQUET_MANIFEST,
        'reportSchema': 'message schema { required unknown_type field_name; }',
    }

    # Call the method
    result = manifest_handler.parse_schema(schema_with_unknown)

    # Verify that unknown types default to STRING
    assert result['columns'][0]['name'] == 'field_name'
    assert result['columns'][0]['type'] == 'STRING'


@pytest.mark.asyncio
async def test_athena_handler_execute_query(mock_context, athena_handler):
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
    assert result['query_execution_id'] == 'test-execution-id'
    assert result['status'] == 'STARTED'


@pytest.mark.asyncio
async def test_athena_handler_wait_for_query_completion(mock_context, athena_handler):
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
async def test_athena_handler_get_query_results(mock_context, athena_handler):
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


def test_athena_handler_determine_output_location(athena_handler):
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
async def test_athena_handler_create_database(mock_context, athena_handler):
    """Test creating a database."""
    with patch.object(
        athena_handler, 'execute_query', new_callable=AsyncMock
    ) as mock_execute_query:
        mock_execute_query.return_value = {'query_execution_id': 'test-id', 'status': 'STARTED'}

        # Call the method
        await athena_handler.create_database('test_db', 's3://test-bucket/athena-results/')

        # Check that execute_query was called with the right arguments
        mock_execute_query.assert_awaited_once_with(
            'CREATE DATABASE IF NOT EXISTS test_db', 'default', 's3://test-bucket/athena-results/'
        )


@pytest.mark.asyncio
async def test_athena_handler_create_table_for_csv(mock_context, athena_handler):
    """Test creating a table for CSV data."""
    with patch.object(
        athena_handler, 'execute_query', new_callable=AsyncMock
    ) as mock_execute_query:
        mock_execute_query.return_value = {'query_execution_id': 'test-id', 'status': 'STARTED'}

        # Create schema info for test
        schema_info = SchemaInfo(
            format=SchemaFormat.CSV,
            columns=[
                ColumnDefinition(name='column1', type='STRING'),
                ColumnDefinition(name='column2', type='BIGINT'),
            ],
            skip_header=True,
        )

        # Call the method
        await athena_handler.create_table_for_csv(
            'test_db',
            'test_table',
            schema_info,
            's3://test-bucket/data/',
            's3://test-bucket/athena-results/',
        )

        # Check that execute_query was called once
        assert mock_execute_query.call_count == 1

        # Check that the SQL contains the expected elements
        call_args = mock_execute_query.call_args[0][0]
        assert 'CREATE EXTERNAL TABLE IF NOT EXISTS test_db.test_table' in call_args
        assert '`column1` STRING' in call_args
        assert '`column2` BIGINT' in call_args
        assert "LOCATION 's3://test-bucket/data/'" in call_args


@pytest.mark.asyncio
async def test_athena_handler_create_table_for_parquet(mock_context, athena_handler):
    """Test creating a table for Parquet data."""
    with patch.object(
        athena_handler, 'execute_query', new_callable=AsyncMock
    ) as mock_execute_query:
        mock_execute_query.return_value = {'query_execution_id': 'test-id', 'status': 'STARTED'}

        # Create schema info for test
        schema_info = SchemaInfo(
            format=SchemaFormat.PARQUET,
            columns=[
                ColumnDefinition(name='column1', type='STRING'),
                ColumnDefinition(name='column2', type='BIGINT'),
            ],
            skip_header=False,
        )

        # Call the method
        await athena_handler.create_table_for_parquet(
            'test_db',
            'test_table',
            schema_info,
            's3://test-bucket/data/',
            's3://test-bucket/athena-results/',
        )

        # Check that execute_query was called once
        assert mock_execute_query.call_count == 1

        # Check that the SQL contains the expected elements
        call_args = mock_execute_query.call_args[0][0]
        assert 'CREATE EXTERNAL TABLE IF NOT EXISTS test_db.test_table' in call_args
        assert '`column1` STRING' in call_args
        assert '`column2` BIGINT' in call_args
        assert 'STORED AS PARQUET' in call_args
        assert "LOCATION 's3://test-bucket/data/'" in call_args


@pytest.mark.asyncio
async def test_athena_handler_setup_table_csv(mock_context):
    """Test setup_table for CSV format."""
    # Create a fresh athena handler instance
    with patch(
        'awslabs.billing_cost_management_mcp_server.tools.storage_lens_tools.create_aws_client'
    ):
        athena_handler = AthenaHandler(mock_context)

    # Track what queries were executed
    executed_queries = []

    # Mock the execute_query method to capture queries
    async def mock_execute_query(query, db_name, output_location):
        executed_queries.append((query, db_name, output_location))
        return {'query_execution_id': 'test-id', 'status': 'STARTED'}

    # Apply the mock
    with patch.object(athena_handler, 'execute_query', side_effect=mock_execute_query):
        # Create schema info for test
        schema_info: SchemaInfo = {
            'format': SchemaFormat.CSV,
            'columns': [
                ColumnDefinition(name='column1', type='STRING'),
                ColumnDefinition(name='column2', type='BIGINT'),
            ],
            'skip_header': True,
        }

        # Call the method
        await athena_handler.setup_table(
            'test_db',
            'test_table',
            schema_info,
            's3://test-bucket/data/',
            's3://test-bucket/athena-results/',
        )

        # Should have two queries: create database and create table
        assert len(executed_queries) == 2

        # First query should be create database
        assert 'CREATE DATABASE IF NOT EXISTS test_db' in executed_queries[0][0]

        # Second query should be create table
        assert 'CREATE EXTERNAL TABLE IF NOT EXISTS test_db.test_table' in executed_queries[1][0]
        # Check for column definitions
        assert '`column1` STRING' in executed_queries[1][0]
        assert '`column2` BIGINT' in executed_queries[1][0]


@pytest.mark.asyncio
async def test_athena_handler_setup_table_parquet(mock_context, athena_handler):
    """Test setup_table for Parquet format."""
    with (
        patch.object(athena_handler, 'create_database', new_callable=AsyncMock) as mock_create_db,
        patch.object(
            athena_handler, 'create_table_for_csv', new_callable=AsyncMock
        ) as mock_create_csv,
        patch.object(
            athena_handler, 'create_table_for_parquet', new_callable=AsyncMock
        ) as mock_create_parquet,
    ):
        # Create schema info for test - use dict format like the implementation expects
        schema_info = {
            'format': 'PARQUET',  # Use string value, not Enum directly
            'columns': [
                {'name': 'column1', 'type': 'STRING'},
                {'name': 'column2', 'type': 'BIGINT'},
            ],
            'skip_header': False,
        }

        # Call the method
        await athena_handler.setup_table(
            'test_db',
            'test_table',
            schema_info,
            's3://test-bucket/data/',
            's3://test-bucket/athena-results/',
        )

        # Check correct methods were called
        mock_create_db.assert_awaited_once()
        mock_create_csv.assert_not_awaited()
        mock_create_parquet.assert_awaited_once()


@pytest.mark.asyncio
async def test_storage_lens_query_tool_query_storage_lens(mock_context, storage_lens_query_tool):
    """Test the query_storage_lens method."""
    # Unpack the fixture
    query_tool, mock_manifest_cls, mock_athena_cls = storage_lens_query_tool

    # Setup mocks
    mock_manifest_handler = MagicMock()
    mock_athena_handler = MagicMock()

    # Replace the instances in the query_tool with our mocks
    query_tool.manifest_handler = mock_manifest_handler
    query_tool.athena_handler = mock_athena_handler

    # Mock async methods with AsyncMock
    mock_manifest_handler.get_manifest = AsyncMock(return_value=CSV_MANIFEST)

    # Mock regular methods
    mock_manifest_handler.extract_data_location.return_value = 's3://test-bucket/data/'
    mock_manifest_handler.parse_schema.return_value = SchemaInfo(
        format=SchemaFormat.CSV,
        columns=[ColumnDefinition(name='test_column', type='STRING')],
        skip_header=True,
    )
    mock_athena_handler.determine_output_location.return_value = 's3://test-bucket/athena-results/'

    # Mock async methods with AsyncMock
    mock_athena_handler.setup_table = AsyncMock()
    mock_athena_handler.execute_query = AsyncMock(
        return_value={'query_execution_id': 'test-id', 'status': 'STARTED'}
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

    # Call the method
    result = await query_tool.query_storage_lens(
        query='SELECT * FROM {table}',
        manifest_location='s3://test-bucket/manifest.json',
        database_name='test_db',
        table_name='test_table',
        output_location='s3://test-bucket/athena-results/',
    )

    # Assertions
    mock_manifest_handler.get_manifest.assert_awaited_once_with('s3://test-bucket/manifest.json')
    mock_manifest_handler.extract_data_location.assert_called_once_with(CSV_MANIFEST)
    mock_manifest_handler.parse_schema.assert_called_once_with(CSV_MANIFEST)

    mock_athena_handler.setup_table.assert_awaited_once()
    mock_athena_handler.execute_query.assert_awaited_once_with(
        'SELECT * FROM test_db.test_table', 'test_db', 's3://test-bucket/athena-results/'
    )

    # Check the result has expected fields
    assert result['status'] == 'success'
    assert 'data' in result
    assert 'columns' in result['data']
    assert 'rows' in result['data']
    assert 'query' in result['data']
    assert result['data']['query'] == 'SELECT * FROM test_db.test_table'


@pytest.mark.asyncio
async def test_storage_lens_query_tool_query_storage_lens_with_default_params(
    mock_context, storage_lens_query_tool
):
    """Test the query_storage_lens method with default parameters."""
    # Unpack the fixture
    query_tool, mock_manifest_cls, mock_athena_cls = storage_lens_query_tool

    # Setup mocks
    mock_manifest_handler = MagicMock()
    mock_athena_handler = MagicMock()

    # Replace the instances in the query_tool with our mocks
    query_tool.manifest_handler = mock_manifest_handler
    query_tool.athena_handler = mock_athena_handler

    # Mock async methods with AsyncMock
    mock_manifest_handler.get_manifest = AsyncMock(return_value=CSV_MANIFEST)

    # Mock regular methods
    mock_manifest_handler.extract_data_location.return_value = 's3://test-bucket/data/'
    mock_manifest_handler.parse_schema.return_value = SchemaInfo(
        format=SchemaFormat.CSV,
        columns=[ColumnDefinition(name='test_column', type='STRING')],
        skip_header=True,
    )
    mock_athena_handler.determine_output_location.return_value = 's3://test-bucket/athena-results/'

    # Mock async methods with AsyncMock
    mock_athena_handler.setup_table = AsyncMock()
    mock_athena_handler.execute_query = AsyncMock(
        return_value={'query_execution_id': 'test-id', 'status': 'STARTED'}
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

    # Call the method with minimal parameters
    result = await query_tool.query_storage_lens(
        query='SELECT * FROM {table}',
        manifest_location='s3://test-bucket/manifest.json',
    )

    # Check default params were used
    mock_athena_handler.execute_query.assert_awaited_once_with(
        'SELECT * FROM storage_lens_db.storage_lens_metrics',
        'storage_lens_db',
        's3://test-bucket/athena-results/',
    )

    # Check query replacement
    assert result['data']['query'] == 'SELECT * FROM storage_lens_db.storage_lens_metrics'


@pytest.mark.asyncio
async def test_storage_lens_query_tool_table_placeholder_replacement(
    mock_context, storage_lens_query_tool
):
    """Test the query_storage_lens table name replacement logic."""
    # Unpack the fixture
    query_tool, mock_manifest_cls, mock_athena_cls = storage_lens_query_tool

    # Setup mocks - simplify by patching the query method itself
    with patch.object(query_tool, 'query_storage_lens', side_effect=query_tool.query_storage_lens):
        with (
            patch.object(
                query_tool.manifest_handler, 'get_manifest', new_callable=AsyncMock
            ) as mock_get_manifest,
            patch.object(
                query_tool.manifest_handler, 'extract_data_location'
            ) as mock_extract_location,
            patch.object(query_tool.manifest_handler, 'parse_schema') as mock_parse_schema,
            patch.object(query_tool.athena_handler, 'setup_table', new_callable=AsyncMock),
            patch.object(
                query_tool.athena_handler, 'execute_query', new_callable=AsyncMock
            ) as mock_execute_query,
            patch.object(
                query_tool.athena_handler, 'wait_for_query_completion', new_callable=AsyncMock
            ) as mock_wait,
            patch.object(
                query_tool.athena_handler, 'get_query_results', new_callable=AsyncMock
            ) as mock_get_results,
            patch.object(
                query_tool.athena_handler, 'determine_output_location'
            ) as mock_determine_output,
        ):
            # Set up return values
            mock_get_manifest.return_value = CSV_MANIFEST
            mock_extract_location.return_value = 's3://test-bucket/data/'
            mock_parse_schema.return_value = SchemaInfo(
                format=SchemaFormat.CSV,
                columns=[ColumnDefinition(name='test_column', type='STRING')],
                skip_header=True,
            )
            mock_determine_output.return_value = 's3://test-bucket/athena-results/'
            mock_execute_query.return_value = {
                'query_execution_id': 'test-id',
                'status': 'STARTED',
            }
            mock_wait.return_value = {
                'Status': {'State': 'SUCCEEDED'},
                'Statistics': {
                    'EngineExecutionTimeInMillis': 1000,
                    'DataScannedInBytes': 1024,
                    'TotalExecutionTimeInMillis': 1500,
                },
            }
            mock_get_results.return_value = {
                'columns': ['column1', 'column2'],
                'rows': [{'column1': 'value1', 'column2': 'value2'}],
            }

            # Test case 1: Query with {table} placeholder
            await query_tool.query_storage_lens(
                query='SELECT * FROM {table} WHERE metric_name = "StorageBytes"',
                manifest_location='s3://test-bucket/manifest.json',
                database_name='custom_db',
                table_name='custom_table',
            )

            # Check replacement with table placeholder
            assert (
                mock_execute_query.call_args_list[0][0][0]
                == 'SELECT * FROM custom_db.custom_table WHERE metric_name = "StorageBytes"'
            )

            # Test case 2: Query with explicit FROM clause but no placeholder
            mock_execute_query.reset_mock()
            await query_tool.query_storage_lens(
                query='SELECT * FROM custom_db.custom_table',
                manifest_location='s3://test-bucket/manifest.json',
                database_name='storage_lens_db',
                table_name='storage_lens_metrics',
            )

            expected_query = (
                'select * FROM storage_lens_db.storage_lens_metrics custom_db.custom_table'
            )
            assert mock_execute_query.call_args_list[0][0][0] == expected_query

            # Test case 3: Query with no placeholder and lowercase from clause
            mock_execute_query.reset_mock()
            await query_tool.query_storage_lens(
                query='SELECT * from something',
                manifest_location='s3://test-bucket/manifest.json',
            )

            # Should inject table name after from (implementation converts to lowercase)
            assert (
                mock_execute_query.call_args_list[0][0][0]
                == 'select * FROM storage_lens_db.storage_lens_metrics something'
            )


@pytest.mark.asyncio
async def test_athena_handler_get_query_results_with_next_token(mock_context, mock_athena_client):
    """Test AthenaHandler get_query_results with next token (has_more functionality)."""
    # Add NextToken to mock response
    mock_athena_client.get_query_results.return_value['NextToken'] = 'next-1'

    with patch(
        'awslabs.billing_cost_management_mcp_server.tools.storage_lens_tools.create_aws_client',
        return_value=mock_athena_client,
    ):
        athena_handler = AthenaHandler(mock_context)
        result = await athena_handler.get_query_results('qid-123')

    assert 'columns' in result
    assert 'rows' in result


@pytest.mark.asyncio
async def test_athena_handler_get_query_results_exception_flow(mock_context):
    """Test AthenaHandler get_query_results exception flow."""
    with patch(
        'awslabs.billing_cost_management_mcp_server.tools.storage_lens_tools.create_aws_client'
    ) as mock_create_client:
        mock_athena_client = MagicMock()
        mock_athena_client.get_query_results.side_effect = RuntimeError('boom')
        mock_create_client.return_value = mock_athena_client

        athena_handler = AthenaHandler(mock_context)

        with pytest.raises(RuntimeError, match='boom'):
            await athena_handler.get_query_results('qid-err')

        mock_context.error.assert_awaited()
