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

import asyncio
import fastmcp
import importlib
import json
import os
import pytest
import re
from awslabs.billing_cost_management_mcp_server.tools.storage_lens_tools import (
    AthenaHandler,
    ColumnDefinition,
    ManifestHandler,
    SchemaFormat,
    SchemaInfo,
    StorageLensQueryTool,
    references_qualified_table,
    storage_lens_server,
    validate_athena_name,
    validate_query_is_readonly_select,
)
from awslabs.billing_cost_management_mcp_server.utilities.aws_service_base import handle_aws_error
from awslabs.billing_cost_management_mcp_server.utilities.error_contract import add_retry_guidance
from botocore.exceptions import ClientError
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
        _athena_ddl_succeeds(handler.athena_client)
        yield handler


def _athena_ddl_succeeds(athena_client, table_location=None):
    """Make a mock Athena client report every query SUCCEEDED and the table at table_location."""
    athena_client.get_query_execution.return_value = {
        'QueryExecution': {'Status': {'State': 'SUCCEEDED'}}
    }
    athena_client.get_table_metadata.return_value = {
        'TableMetadata': {'Parameters': {'location': table_location}}
    }


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
        mock_athena_client.get_table_metadata.return_value = {
            'TableMetadata': {'Parameters': {'location': 's3://test-bucket/data/'}}
        }

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


@pytest.fixture(scope='module', autouse=True)
def _restore_real_tool_module():
    """Reload the module with the real FastMCP.tool after this file's tests.

    _reload_storage_lens_with_identity_decorator() leaves the module's server with no registered tools;
    restoring it keeps later test files from seeing that state.
    """
    yield
    from awslabs.billing_cost_management_mcp_server.tools import storage_lens_tools as module

    importlib.reload(module)


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
async def test_storage_lens_real_unreferenced_table_rejected_reload_identity_decorator(
    mock_context,
):
    """Test storage_lens_run_query rejects a FROM clause naming another table."""
    os.environ['STORAGE_LENS_MANIFEST_LOCATION'] = 's3://bucket/prefix/'

    stl_mod = _reload_storage_lens_with_identity_decorator()
    real_fn = stl_mod.storage_lens_run_query  # type: ignore

    with patch.object(
        stl_mod.ManifestHandler, 'get_manifest', new_callable=AsyncMock
    ) as mock_get_manifest:
        # No {table} and no qualified name -> rejected, not rewritten
        q = "SELECT * from something WHERE region='us-east-1'"
        res = await real_fn(mock_context, query=q)  # type: ignore
        assert res['status'] == 'error'
        assert res['error_type'] == 'validation_error'
        assert '{table}' in res['message']
        mock_get_manifest.assert_not_awaited()


@pytest.mark.asyncio
async def test_storage_lens_real_query_missing_table_reference_error_reload_identity_decorator(
    mock_context,
):
    """Test storage_lens_run_query missing table reference error with identity decorator."""
    os.environ['STORAGE_LENS_MANIFEST_LOCATION'] = 's3://bucket/prefix/'

    stl_mod = _reload_storage_lens_with_identity_decorator()
    real_fn = stl_mod.storage_lens_run_query  # type: ignore

    with patch.object(
        stl_mod.ManifestHandler, 'get_manifest', new_callable=AsyncMock
    ) as mock_get_manifest:
        res = await real_fn(mock_context, query='SELECT 42')  # type: ignore
        assert res['status'] == 'error'
        assert 'must reference the table with the {table} placeholder' in res.get('message', '')
        assert res['error_type'] == 'validation_error'
        # The table reference is checked before the manifest is read
        mock_get_manifest.assert_not_awaited()


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
        error = ClientError(
            {'Error': {'Code': 'TooManyRequestsException', 'Message': 'oops db'}},
            'StartQueryExecution',
        )
        mock_athena_client.start_query_execution.side_effect = error
        mock_create_client.return_value = mock_athena_client

        athena_handler = AthenaHandler(mock_context)

        # Re-raised unwrapped so handle_aws_error keeps the AWS error code
        with pytest.raises(ClientError) as excinfo:
            await athena_handler.execute_query(
                'SELECT 1',
                'test_db',
                's3://test-bucket/athena-results/',
            )

        assert excinfo.value is error

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
    error = ClientError(
        {'Error': {'Code': 'AccessDenied', 'Message': 'Access denied'}}, 'GetObject'
    )
    manifest_handler.s3_client.get_object.side_effect = error

    # Call the method and expect the original exception, unwrapped
    with pytest.raises(ClientError) as excinfo:
        await manifest_handler._read_manifest_file('my-bucket', 'path/to/manifest.json')

    assert excinfo.value is error


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
async def test_athena_handler_wait_for_query_completion_timeout_is_retryable(
    mock_context, athena_handler
):
    """A poll timeout raises TimeoutError, which the error contract maps to a retry."""
    athena_handler.athena_client.get_query_execution.return_value = {
        'QueryExecution': {'Status': {'State': 'RUNNING'}}
    }

    with patch(
        'awslabs.billing_cost_management_mcp_server.tools.storage_lens_tools.asyncio.sleep',
        new_callable=AsyncMock,
    ):
        with pytest.raises(TimeoutError) as excinfo:
            await athena_handler.wait_for_query_completion('test-execution-id', max_retries=2)

    result = add_retry_guidance(await handle_aws_error(mock_context, excinfo.value, 'q', 'S3'))
    assert result['error_type'] == 'unknown_timeouterror'
    assert result['retry_strategy'] == 'retry_same_request'


@pytest.mark.asyncio
async def test_athena_handler_wait_for_query_completion_failed_query_is_validation(
    mock_context, athena_handler
):
    """A FAILED Athena query raises ValueError, so the caller is told to change the query."""
    athena_handler.athena_client.get_query_execution.return_value = {
        'QueryExecution': {'Status': {'State': 'FAILED', 'StateChangeReason': 'COLUMN_NOT_FOUND'}}
    }

    with pytest.raises(ValueError, match='Query failed: COLUMN_NOT_FOUND'):
        await athena_handler.wait_for_query_completion('test-execution-id')


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
    _athena_ddl_succeeds(athena_handler.athena_client, 's3://test-bucket/data/')

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

            # Test case 2: Query naming a table other than the configured one
            mock_execute_query.reset_mock()
            result = await query_tool.query_storage_lens(
                query='SELECT * FROM custom_db.custom_table',
                manifest_location='s3://test-bucket/manifest.json',
                database_name='storage_lens_db',
                table_name='storage_lens_metrics',
            )

            # Rejected rather than rewritten
            assert result['error_type'] == 'validation_error'
            mock_execute_query.assert_not_awaited()

            # Test case 3: Query with no placeholder and lowercase from clause
            result = await query_tool.query_storage_lens(
                query='SELECT * from something',
                manifest_location='s3://test-bucket/manifest.json',
            )

            assert result['error_type'] == 'validation_error'
            mock_execute_query.assert_not_awaited()


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


# --- Query validation (security hardening: reject DDL/DML in user queries) ---


class TestQueryValidation:
    """Tests for read-only SELECT validation in storage_lens_run_query."""

    def _get_real_fn(self):
        """Get the real storage_lens_run_query via identity decorator reload."""
        stl_mod = _reload_storage_lens_with_identity_decorator()
        return stl_mod.storage_lens_run_query, stl_mod  # type: ignore

    @pytest.mark.asyncio
    async def test_plain_select_allowed(self, mock_context):
        """A plain SELECT query should pass validation."""
        os.environ['STORAGE_LENS_MANIFEST_LOCATION'] = 's3://bucket/prefix/'
        real_fn, stl_mod = self._get_real_fn()
        with patch.object(stl_mod, 'StorageLensQueryTool') as MockTool:
            mock_instance = MagicMock()
            mock_instance.query_storage_lens = AsyncMock(
                return_value={'status': 'success', 'data': {}}
            )
            MockTool.return_value = mock_instance
            res = await real_fn(  # type: ignore[reportCallIssue]
                mock_context, query='SELECT * FROM {table} LIMIT 10'
            )
            assert res['status'] == 'success'
            mock_instance.query_storage_lens.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_cte_select_allowed(self, mock_context):
        """A WITH...SELECT CTE should pass validation."""
        os.environ['STORAGE_LENS_MANIFEST_LOCATION'] = 's3://bucket/prefix/'
        real_fn, stl_mod = self._get_real_fn()
        with patch.object(stl_mod, 'StorageLensQueryTool') as MockTool:
            mock_instance = MagicMock()
            mock_instance.query_storage_lens = AsyncMock(
                return_value={'status': 'success', 'data': {}}
            )
            MockTool.return_value = mock_instance
            q = 'WITH cte AS (SELECT bucket_name, SUM(storage_bytes) AS total FROM {table} GROUP BY bucket_name) SELECT * FROM cte ORDER BY total DESC'
            res = await real_fn(  # type: ignore[reportCallIssue]
                mock_context, query=q
            )
            assert res['status'] == 'success'
            mock_instance.query_storage_lens.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_complex_select_with_placeholder_allowed(self, mock_context):
        """A complex SELECT with {table}, subqueries, CASE, GROUP BY/HAVING should pass."""
        os.environ['STORAGE_LENS_MANIFEST_LOCATION'] = 's3://bucket/prefix/'
        real_fn, stl_mod = self._get_real_fn()
        with patch.object(stl_mod, 'StorageLensQueryTool') as MockTool:
            mock_instance = MagicMock()
            mock_instance.query_storage_lens = AsyncMock(
                return_value={'status': 'success', 'data': {}}
            )
            MockTool.return_value = mock_instance
            q = """SELECT bucket_name,
                          CASE WHEN CAST(metric_value AS BIGINT) > 1000000 THEN 'large' ELSE 'small' END AS size_cat,
                          SUM(CAST(metric_value AS BIGINT)) AS total
                   FROM {table}
                   WHERE metric_name IN (SELECT DISTINCT metric_name FROM {table} WHERE metric_name = 'StorageBytes')
                   GROUP BY bucket_name, size_cat
                   HAVING SUM(CAST(metric_value AS BIGINT)) > 100
                   ORDER BY total DESC"""
            res = await real_fn(  # type: ignore[reportCallIssue]
                mock_context, query=q
            )
            assert res['status'] == 'success'
            mock_instance.query_storage_lens.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_create_external_table_rejected(self, mock_context):
        """CREATE EXTERNAL TABLE via query should be rejected."""
        os.environ['STORAGE_LENS_MANIFEST_LOCATION'] = 's3://bucket/prefix/'
        real_fn, stl_mod = self._get_real_fn()
        with patch.object(stl_mod, 'StorageLensQueryTool') as MockTool:
            mock_instance = MagicMock()
            mock_instance.query_storage_lens = AsyncMock()
            MockTool.return_value = mock_instance
            q = "CREATE EXTERNAL TABLE evil_db.evil_table (id INT) LOCATION 's3://attacker/'"
            res = await real_fn(  # type: ignore[reportCallIssue]
                mock_context, query=q
            )
            assert res['status'] == 'error'
            assert 'CREATE' in res.get('message', '')
            mock_instance.query_storage_lens.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_drop_table_rejected(self, mock_context):
        """DROP TABLE via query should be rejected."""
        os.environ['STORAGE_LENS_MANIFEST_LOCATION'] = 's3://bucket/prefix/'
        real_fn, stl_mod = self._get_real_fn()
        with patch.object(stl_mod, 'StorageLensQueryTool') as MockTool:
            mock_instance = MagicMock()
            mock_instance.query_storage_lens = AsyncMock()
            MockTool.return_value = mock_instance
            res = await real_fn(  # type: ignore[reportCallIssue]
                mock_context, query='DROP TABLE storage_lens_db.storage_lens_metrics'
            )
            assert res['status'] == 'error'
            assert 'DROP' in res.get('message', '')
            mock_instance.query_storage_lens.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_insert_rejected(self, mock_context):
        """INSERT via query should be rejected."""
        os.environ['STORAGE_LENS_MANIFEST_LOCATION'] = 's3://bucket/prefix/'
        real_fn, stl_mod = self._get_real_fn()
        with patch.object(stl_mod, 'StorageLensQueryTool') as MockTool:
            mock_instance = MagicMock()
            mock_instance.query_storage_lens = AsyncMock()
            MockTool.return_value = mock_instance
            res = await real_fn(  # type: ignore[reportCallIssue]
                mock_context, query="INSERT INTO some_table VALUES (1, 'x')"
            )
            assert res['status'] == 'error'
            assert 'INSERT' in res.get('message', '')
            mock_instance.query_storage_lens.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_update_rejected(self, mock_context):
        """UPDATE via query should be rejected."""
        os.environ['STORAGE_LENS_MANIFEST_LOCATION'] = 's3://bucket/prefix/'
        real_fn, stl_mod = self._get_real_fn()
        with patch.object(stl_mod, 'StorageLensQueryTool') as MockTool:
            mock_instance = MagicMock()
            mock_instance.query_storage_lens = AsyncMock()
            MockTool.return_value = mock_instance
            res = await real_fn(  # type: ignore[reportCallIssue]
                mock_context, query="UPDATE t SET col='x' WHERE id=1"
            )
            assert res['status'] == 'error'
            assert 'UPDATE' in res.get('message', '')
            mock_instance.query_storage_lens.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_delete_rejected(self, mock_context):
        """DELETE via query should be rejected."""
        os.environ['STORAGE_LENS_MANIFEST_LOCATION'] = 's3://bucket/prefix/'
        real_fn, stl_mod = self._get_real_fn()
        with patch.object(stl_mod, 'StorageLensQueryTool') as MockTool:
            mock_instance = MagicMock()
            mock_instance.query_storage_lens = AsyncMock()
            MockTool.return_value = mock_instance
            res = await real_fn(  # type: ignore[reportCallIssue]
                mock_context, query='DELETE FROM some_table WHERE id=1'
            )
            assert res['status'] == 'error'
            assert 'DELETE' in res.get('message', '')
            mock_instance.query_storage_lens.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_multi_statement_rejected(self, mock_context):
        """Multiple statements (SELECT; DROP) should be rejected."""
        os.environ['STORAGE_LENS_MANIFEST_LOCATION'] = 's3://bucket/prefix/'
        real_fn, stl_mod = self._get_real_fn()
        with patch.object(stl_mod, 'StorageLensQueryTool') as MockTool:
            mock_instance = MagicMock()
            mock_instance.query_storage_lens = AsyncMock()
            MockTool.return_value = mock_instance
            res = await real_fn(  # type: ignore[reportCallIssue]
                mock_context, query='SELECT 1; DROP TABLE t'
            )
            assert res['status'] == 'error'
            assert 'multiple statements' in res.get('message', '').lower()
            mock_instance.query_storage_lens.assert_not_awaited()


# --- Local validation errors carry error_type, operation and service ---


@pytest.mark.asyncio
@pytest.mark.parametrize(
    'query',
    [
        'DROP TABLE x',
        'INSERT INTO t VALUES (1)',
        'SELECT 1; DROP TABLE t',
        '',
        'SELECT FROM WHERE (',
    ],
)
async def test_rejected_query_is_validation_error(mock_context, monkeypatch, query):
    """A query rejected by the read-only check is a validation_error the caller must modify."""
    monkeypatch.setenv('STORAGE_LENS_MANIFEST_LOCATION', 's3://bucket/prefix/')
    stl_mod = _reload_storage_lens_with_identity_decorator()
    with patch.object(stl_mod, 'StorageLensQueryTool') as MockTool:
        res = await stl_mod.storage_lens_run_query(mock_context, query=query)  # type: ignore
        MockTool.assert_not_called()
    assert res['status'] == 'error'
    assert res['message'].startswith('Query validation failed')
    assert res['error_type'] == 'validation_error'
    assert res['operation'] == 'storage_lens_run_query'
    assert res['service'] == 'Storage Lens'
    assert add_retry_guidance(res)['retry_strategy'] == 'modify_request'


@pytest.mark.asyncio
async def test_missing_manifest_location_is_validation_error(mock_context, monkeypatch):
    """No manifest_location argument and no environment variable is a validation_error."""
    monkeypatch.delenv('STORAGE_LENS_MANIFEST_LOCATION', raising=False)
    stl_mod = _reload_storage_lens_with_identity_decorator()
    res = await stl_mod.storage_lens_run_query(mock_context, query='SELECT 1')  # type: ignore
    assert res['status'] == 'error'
    assert 'Missing manifest location' in res['message']
    assert res['error_type'] == 'validation_error'
    assert res['operation'] == 'storage_lens_run_query'
    assert res['service'] == 'Storage Lens'
    assert add_retry_guidance(res)['retry_strategy'] == 'modify_request'


@pytest.mark.asyncio
async def test_description_states_dialect_and_csv_string_columns():
    """The served description names the Trino dialect and that CSV export columns are strings."""
    from awslabs.billing_cost_management_mcp_server.tools import storage_lens_tools as stl_mod

    importlib.reload(stl_mod)
    tool = await stl_mod.storage_lens_server.get_tool('storage-lens')
    assert tool is not None
    description = tool.description or ''
    assert 'Athena engine version 3 (Trino SQL)' in description
    assert 'In CSV exports every column is a string' in description
    assert 'SUM(CAST(metric_value AS BIGINT))' in description
    assert 'standard SQL' not in description


def test_module_docstring_has_no_missing_file_pointer():
    """The module docstring does not point at a reference file the package does not ship."""
    from awslabs.billing_cost_management_mcp_server.tools import storage_lens_tools as stl_mod

    assert 'storage_lens_metrics_reference.md' not in (stl_mod.__doc__ or '')


# --- Direct unit tests for validate_query_is_readonly_select ---


def test_validate_empty_string():
    """Empty string should be rejected."""
    result = validate_query_is_readonly_select('')
    assert result is not None


def test_validate_parse_error():
    """Unparseable SQL should be rejected."""
    result = validate_query_is_readonly_select('NOT VALID SQL {{{{')
    assert result is not None
    assert 'parse' in result.lower() or 'SELECT' in result


def test_validate_valid_select_returns_none():
    """Valid SELECT should return None (no error)."""
    assert validate_query_is_readonly_select('SELECT 1') is None


def test_validate_ddl_in_cte_subquery():
    """DDL nested in a CTE subquery expression should be caught by the walk."""
    # This tests the _FORBIDDEN walk path — a SELECT wrapping something suspicious
    # In practice sqlglot may not parse this as valid, but we test the walk logic
    # by using a query that IS a top-level select but references forbidden keywords
    # Actually, we can't truly nest DDL inside a CTE in valid SQL.
    # The walk path is defense-in-depth. Let's just verify the function handles it.
    # Instead, test that the top-level gate works for MERGE (exercises stmt.key check)
    result = validate_query_is_readonly_select(
        'MERGE INTO t USING s ON t.id = s.id WHEN MATCHED THEN UPDATE SET t.x = s.x'
    )
    assert result is not None
    assert 'MERGE' in result


def test_validate_empty_statements_list():
    """Cover the 'if not statements' branch via mock."""
    with patch('sqlglot.parse', return_value=[]):
        result = validate_query_is_readonly_select('anything')
        assert result is not None
        assert 'empty' in result.lower()


def test_validate_forbidden_node_in_walk():
    """Cover the _FORBIDDEN walk branch via a mock that injects a forbidden node."""
    mock_create_node = MagicMock()
    mock_create_node.key = 'create'

    mock_stmt = MagicMock()
    mock_stmt.key = 'select'
    mock_stmt.walk.return_value = [mock_stmt, mock_create_node]

    with patch('sqlglot.parse', return_value=[mock_stmt]):
        result = validate_query_is_readonly_select('SELECT 1')
        assert result is not None
        assert 'CREATE' in result


def _query_tool_with_mocked_handlers(query_tool):
    """Give a StorageLensQueryTool mocked manifest and Athena handlers that succeed."""
    manifest_handler = MagicMock()
    athena_handler = MagicMock()
    manifest_handler.get_manifest = AsyncMock(return_value=CSV_MANIFEST)
    manifest_handler.extract_data_location.return_value = 's3://test-bucket/data/'
    manifest_handler.parse_schema.return_value = SchemaInfo(
        format=SchemaFormat.CSV,
        columns=[ColumnDefinition(name='bucket_name', type='STRING')],
        skip_header=True,
    )
    athena_handler.determine_output_location.return_value = 's3://test-bucket/athena-results/'
    athena_handler.setup_table = AsyncMock()
    athena_handler.execute_query = AsyncMock(
        return_value={'query_execution_id': 'test-id', 'status': 'STARTED'}
    )
    athena_handler.wait_for_query_completion = AsyncMock(
        return_value={'Status': {'State': 'SUCCEEDED'}, 'Statistics': {}}
    )
    athena_handler.get_query_results = AsyncMock(return_value={'columns': [], 'rows': []})
    query_tool.manifest_handler = manifest_handler
    query_tool.athena_handler = athena_handler
    return manifest_handler, athena_handler


@pytest.mark.asyncio
@pytest.mark.parametrize(
    'query,expected',
    [
        # Mixed-case literal with the placeholder: only {table} changes.
        (
            "SELECT * FROM {table} WHERE bucket_name = 'MyBucket'",
            "SELECT * FROM storage_lens_db.storage_lens_metrics WHERE bucket_name = 'MyBucket'",
        ),
        # Subquery and EXTRACT(... FROM ...) with the placeholder: no extra FROM rewrite.
        (
            'SELECT EXTRACT(YEAR FROM report_date) AS y FROM (SELECT * FROM {table}) t',
            'SELECT EXTRACT(YEAR FROM report_date) AS y '
            'FROM (SELECT * FROM storage_lens_db.storage_lens_metrics) t',
        ),
        # Qualified name: the query is sent exactly as written.
        (
            "SELECT * FROM storage_lens_db.storage_lens_metrics WHERE bucket_name = 'MyBucket'",
            "SELECT * FROM storage_lens_db.storage_lens_metrics WHERE bucket_name = 'MyBucket'",
        ),
        # Qualified name in another case: matched case-insensitively, sent as written.
        (
            "SELECT * FROM Storage_Lens_DB.Storage_Lens_Metrics WHERE bucket_name = 'MyBucket'",
            "SELECT * FROM Storage_Lens_DB.Storage_Lens_Metrics WHERE bucket_name = 'MyBucket'",
        ),
        # Quoted identifiers and spaces around the dot still name the table.
        (
            'SELECT * FROM "storage_lens_db"."storage_lens_metrics"',
            'SELECT * FROM "storage_lens_db"."storage_lens_metrics"',
        ),
        (
            'SELECT * FROM storage_lens_db . storage_lens_metrics',
            'SELECT * FROM storage_lens_db . storage_lens_metrics',
        ),
        # Athena's default catalog prefix names the same table.
        (
            'SELECT * FROM AwsDataCatalog.storage_lens_db.storage_lens_metrics',
            'SELECT * FROM AwsDataCatalog.storage_lens_db.storage_lens_metrics',
        ),
    ],
)
async def test_query_storage_lens_sends_query_text_unchanged_except_placeholder(
    storage_lens_query_tool, query, expected
):
    """String literals, subqueries and case reach Athena as the caller wrote them."""
    query_tool, _, _ = storage_lens_query_tool
    _, athena_handler = _query_tool_with_mocked_handlers(query_tool)

    result = await query_tool.query_storage_lens(
        query=query, manifest_location='s3://test-bucket/manifest.json'
    )

    assert result['status'] == 'success'
    athena_handler.execute_query.assert_awaited_once_with(
        expected, 'storage_lens_db', 's3://test-bucket/athena-results/'
    )
    assert result['data']['query'] == expected


@pytest.mark.asyncio
@pytest.mark.parametrize(
    'query',
    [
        "SELECT * FROM metrics WHERE bucket_name = 'MyBucket'",
        'SELECT * FROM (SELECT bucket_name FROM metrics) t',
        'SELECT EXTRACT(YEAR FROM report_date) FROM metrics',
        'SELECT 42',
        # Bare table name: the database must be named.
        'SELECT * FROM storage_lens_metrics',
        # The qualified name appears, but not as the table read.
        'SELECT * FROM storage_lens_db.storage_lens_metrics_v2',
        "SELECT * FROM other_db.t WHERE x = 'storage_lens_db.storage_lens_metrics'",
        'SELECT * FROM other_db.t -- storage_lens_db.storage_lens_metrics',
        # {table} only in a comment or string literal: the query still reads another table.
        'SELECT * FROM other_db.t -- {table}',
        "SELECT * FROM other_db.t WHERE x = '{table}'",
        # Same database and table in another catalog.
        'SELECT * FROM othercat.storage_lens_db.storage_lens_metrics',
    ],
)
async def test_query_storage_lens_rejects_query_without_table_reference(
    storage_lens_query_tool, query
):
    """A query naming neither {table} nor the qualified table is rejected, not rewritten."""
    query_tool, _, _ = storage_lens_query_tool
    manifest_handler, athena_handler = _query_tool_with_mocked_handlers(query_tool)

    result = await query_tool.query_storage_lens(
        query=query, manifest_location='s3://test-bucket/manifest.json'
    )

    assert result['status'] == 'error'
    assert result['error_type'] == 'validation_error'
    assert '{table}' in result['message']
    assert 'storage_lens_db.storage_lens_metrics' in result['message']
    # Rejected before any AWS call: no manifest read, no table setup, no query.
    manifest_handler.get_manifest.assert_not_awaited()
    athena_handler.setup_table.assert_not_awaited()
    athena_handler.execute_query.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    'query,accepted',
    [
        ("SELECT * FROM custom_db.custom_table WHERE bucket_name = 'MyBucket'", True),
        ('SELECT * FROM mydb.tbl', False),
        ('SELECT * FROM custom_db.custom_table_2', False),
        ('SELECT * FROM storage_lens_db.storage_lens_metrics', False),
    ],
)
async def test_query_storage_lens_qualified_name_uses_custom_database_and_table(
    storage_lens_query_tool, query, accepted
):
    """The qualified-name check uses the database_name and table_name passed in."""
    query_tool, _, _ = storage_lens_query_tool
    _, athena_handler = _query_tool_with_mocked_handlers(query_tool)

    result = await query_tool.query_storage_lens(
        query=query,
        manifest_location='s3://test-bucket/manifest.json',
        database_name='custom_db',
        table_name='custom_table',
    )

    if accepted:
        assert result['status'] == 'success'
        athena_handler.execute_query.assert_awaited_once_with(
            query, 'custom_db', 's3://test-bucket/athena-results/'
        )
    else:
        assert result['error_type'] == 'validation_error'
        assert 'custom_db.custom_table' in result['message']
        athena_handler.execute_query.assert_not_awaited()


def test_references_qualified_table_unparseable_query_is_false():
    """An unparseable query does not count as naming the table."""
    assert not references_qualified_table(
        'SELECT * FROM storage_lens_db.storage_lens_metrics WHERE (',
        'storage_lens_db',
        'storage_lens_metrics',
    )
    # The same query without the dangling parenthesis does name it.
    assert references_qualified_table(
        'SELECT * FROM storage_lens_db.storage_lens_metrics',
        'storage_lens_db',
        'storage_lens_metrics',
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    'database_name,table_name,bad_arg',
    [
        ('storage_lens_db; DROP DATABASE x', 'storage_lens_metrics', 'database_name'),
        ('storage_lens_db', 't (x int) --', 'table_name'),
        ('storage-lens-db', 'storage_lens_metrics', 'database_name'),
        ('_db', 'storage_lens_metrics', 'database_name'),
        ('storage_lens_db', '1metrics', 'table_name'),
        ('storage_lens_db', '', 'table_name'),
        ('a' * 256, 'storage_lens_metrics', 'database_name'),
        ('storage_lens_db\n', 'storage_lens_metrics', 'database_name'),
        ('storage_lens_db', 'm\u00e9trics', 'table_name'),
        (None, 'storage_lens_metrics', 'database_name'),
    ],
)
async def test_query_storage_lens_rejects_unsafe_database_or_table_name(
    storage_lens_query_tool, database_name, table_name, bad_arg
):
    """Names are written unquoted into DDL and the query, so anything but a plain identifier is rejected."""
    query_tool, _, _ = storage_lens_query_tool
    manifest_handler, athena_handler = _query_tool_with_mocked_handlers(query_tool)

    result = await query_tool.query_storage_lens(
        query='SELECT * FROM {table}',
        manifest_location='s3://test-bucket/manifest.json',
        database_name=database_name,
        table_name=table_name,
    )

    assert result['status'] == 'error'
    assert result['error_type'] == 'validation_error'
    assert bad_arg in result['message']
    manifest_handler.get_manifest.assert_not_awaited()
    athena_handler.setup_table.assert_not_awaited()
    athena_handler.execute_query.assert_not_awaited()


@pytest.mark.asyncio
async def test_query_storage_lens_accepts_longest_plain_identifier(storage_lens_query_tool):
    """A 255-character identifier of letters, digits and underscores is accepted."""
    query_tool, _, _ = storage_lens_query_tool
    _, athena_handler = _query_tool_with_mocked_handlers(query_tool)
    database_name = 'Db_1' + 'a' * 251

    result = await query_tool.query_storage_lens(
        query='SELECT * FROM {table}',
        manifest_location='s3://test-bucket/manifest.json',
        database_name=database_name,
        table_name='t',
    )

    assert result['status'] == 'success'
    athena_handler.execute_query.assert_awaited_once()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    'database_name,table_name,bad_arg',
    [
        ('db; DROP DATABASE x', 't', 'database_name'),
        ('db', 't (x int) --', 'table_name'),
    ],
)
async def test_athena_handler_setup_table_rejects_unsafe_name_before_ddl(
    mock_context, database_name, table_name, bad_arg
):
    """setup_table checks the names before any CREATE DATABASE / CREATE TABLE is sent."""
    with patch(
        'awslabs.billing_cost_management_mcp_server.tools.storage_lens_tools.create_aws_client'
    ):
        athena_handler = AthenaHandler(mock_context)
    athena_handler.execute_query = AsyncMock()

    with pytest.raises(ValueError, match=bad_arg):
        await athena_handler.setup_table(
            database_name,
            table_name,
            SchemaInfo(format=SchemaFormat.CSV, columns=[], skip_header=True),
            's3://test-bucket/data/',
            's3://test-bucket/athena-results/',
        )
    athena_handler.execute_query.assert_not_awaited()


@pytest.mark.asyncio
async def test_query_storage_lens_accepts_uppercase_names(storage_lens_query_tool):
    """Uppercase letters are accepted; Athena lowercases names itself."""
    query_tool, _, _ = storage_lens_query_tool
    _, athena_handler = _query_tool_with_mocked_handlers(query_tool)

    result = await query_tool.query_storage_lens(
        query='SELECT * FROM {table}',
        manifest_location='s3://test-bucket/manifest.json',
        database_name='My_DB',
        table_name='Metrics_2',
    )

    assert result['status'] == 'success'
    athena_handler.execute_query.assert_awaited_once_with(
        'SELECT * FROM My_DB.Metrics_2', 'My_DB', 's3://test-bucket/athena-results/'
    )


def test_validate_athena_name_truncates_echoed_value():
    """A long rejected value is not echoed back in full."""
    with pytest.raises(ValueError) as excinfo:
        validate_athena_name('table_name', 'x;' * 500)
    assert len(str(excinfo.value)) < 200


@pytest.mark.asyncio
@pytest.mark.parametrize(
    'method,args',
    [
        ('create_database', ('db; DROP DATABASE x', 's3://b/out/')),
        (
            'create_table_for_csv',
            (
                'db',
                't (x int) --',
                SchemaInfo(format=SchemaFormat.CSV, columns=[], skip_header=True),
                's3://b/d/',
                's3://b/out/',
            ),
        ),
        (
            'create_table_for_parquet',
            (
                'db--',
                't',
                SchemaInfo(format=SchemaFormat.PARQUET, columns=[], skip_header=False),
                's3://b/d/',
                's3://b/out/',
            ),
        ),
        (
            'create_table_for_parquet',
            (
                'db',
                't--',
                SchemaInfo(format=SchemaFormat.PARQUET, columns=[], skip_header=False),
                's3://b/d/',
                's3://b/out/',
            ),
        ),
    ],
)
async def test_athena_handler_ddl_builders_reject_unsafe_names(mock_context, method, args):
    """Each method that writes a name into DDL checks it before sending anything."""
    with patch(
        'awslabs.billing_cost_management_mcp_server.tools.storage_lens_tools.create_aws_client'
    ):
        athena_handler = AthenaHandler(mock_context)
    athena_handler.execute_query = AsyncMock()

    with pytest.raises(ValueError, match='must start with a letter'):
        await getattr(athena_handler, method)(*args)
    athena_handler.execute_query.assert_not_awaited()


@pytest.mark.asyncio
async def test_storage_lens_run_query_rejects_unsafe_table_name(mock_context):
    """Through the MCP tool function, an unsafe table_name is a validation_error before any AWS call."""
    stl_mod = _reload_storage_lens_with_identity_decorator()
    real_fn = stl_mod.storage_lens_run_query  # type: ignore

    with (
        patch.dict(os.environ, {'STORAGE_LENS_MANIFEST_LOCATION': 's3://bucket/prefix/'}),
        patch.object(stl_mod, 'create_aws_client'),
        patch.object(
            stl_mod.ManifestHandler, 'get_manifest', new_callable=AsyncMock
        ) as mock_get_manifest,
    ):
        res = await real_fn(  # type: ignore
            mock_context, query='SELECT * FROM {table}', table_name='t; DROP TABLE x'
        )
        assert res['status'] == 'error'
        assert res['error_type'] == 'validation_error'
        assert 'table_name' in res['message']
        mock_get_manifest.assert_not_awaited()


_CSV_SCHEMA = SchemaInfo(
    format=SchemaFormat.CSV,
    columns=[ColumnDefinition(name='bucket_name', type='STRING')],
    skip_header=True,
)


@pytest.mark.asyncio
@pytest.mark.parametrize('method', ['create_table_for_csv', 'create_table_for_parquet'])
@pytest.mark.parametrize(
    'column_name,data_location,expected',
    [
        ('a` STRING) --', 's3://b/d', 'column names'),
        ('bucket name', 's3://b/d', 'column names'),
        ('bucket_name', "s3://b/d' --", 'data location'),
        ('bucket_name', 's3://b/d' + chr(92), 'data location'),
        ('bucket_name', 'hdfs://b/d', 'data location'),
    ],
)
async def test_athena_handler_ddl_rejects_unsafe_manifest_values(
    mock_context, method, column_name, data_location, expected
):
    """Column names and the data location come from the manifest; unsafe ones never reach DDL."""
    with patch(
        'awslabs.billing_cost_management_mcp_server.tools.storage_lens_tools.create_aws_client'
    ):
        athena_handler = AthenaHandler(mock_context)
    athena_handler.execute_query = AsyncMock()
    schema = SchemaInfo(
        format=SchemaFormat.CSV,
        columns=[ColumnDefinition(name=column_name, type='STRING')],
        skip_header=True,
    )

    with pytest.raises(ValueError, match=expected):
        await getattr(athena_handler, method)('db', 't', schema, data_location, 's3://b/out/')
    athena_handler.execute_query.assert_not_awaited()


@pytest.mark.asyncio
async def test_athena_handler_ddl_writes_safe_manifest_values(mock_context):
    """Plain column names and an s3:// location are written into the DDL as before."""
    with patch(
        'awslabs.billing_cost_management_mcp_server.tools.storage_lens_tools.create_aws_client'
    ):
        athena_handler = AthenaHandler(mock_context)
    _athena_ddl_succeeds(athena_handler.athena_client)
    athena_handler.execute_query = AsyncMock()

    await athena_handler.create_table_for_parquet(
        'db', 't', _CSV_SCHEMA, 's3://b/data/prefix', 's3://b/out/'
    )

    await_args = athena_handler.execute_query.await_args
    assert await_args is not None
    ddl = await_args.args[0]
    assert '`bucket_name` STRING' in ddl
    assert "LOCATION 's3://b/data/prefix'" in ddl


@pytest.mark.parametrize(
    'query', ["SELECT * FROM {table} WHERE x = 'abc", 'SELECT "abc FROM {table}']
)
def test_unbalanced_quote_is_a_validation_failure_not_an_exception(query):
    """An unbalanced quote (a sqlglot TokenError, not a ParseError) fails both checks cleanly."""
    assert not references_qualified_table(query, 'db', 't')
    result = validate_query_is_readonly_select(query)
    assert result is not None
    assert 'unable to parse SQL' in result


@pytest.mark.asyncio
async def test_athena_handler_setup_table_checks_manifest_values_before_any_ddl(mock_context):
    """An unsafe manifest column name stops setup_table before CREATE DATABASE is sent."""
    with patch(
        'awslabs.billing_cost_management_mcp_server.tools.storage_lens_tools.create_aws_client'
    ):
        athena_handler = AthenaHandler(mock_context)
    athena_handler.execute_query = AsyncMock()
    schema = SchemaInfo(
        format=SchemaFormat.CSV,
        columns=[ColumnDefinition(name='a` STRING) --', type='STRING')],
        skip_header=True,
    )

    with pytest.raises(ValueError, match='column names'):
        await athena_handler.setup_table('db', 't', schema, 's3://b/d', 's3://b/out/')
    athena_handler.execute_query.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize('method', ['create_table_for_csv', 'create_table_for_parquet'])
async def test_athena_handler_ddl_rejects_unknown_column_type(mock_context, method):
    """A column type outside STRING/BIGINT/DOUBLE never reaches DDL."""
    with patch(
        'awslabs.billing_cost_management_mcp_server.tools.storage_lens_tools.create_aws_client'
    ):
        athena_handler = AthenaHandler(mock_context)
    athena_handler.execute_query = AsyncMock()
    schema = SchemaInfo(
        format=SchemaFormat.CSV,
        columns=[ColumnDefinition(name='a', type="STRING) LOCATION 's3://x/' --")],
        skip_header=True,
    )

    with pytest.raises(ValueError, match='Column types'):
        await getattr(athena_handler, method)('db', 't', schema, 's3://b/d', 's3://b/out/')
    athena_handler.execute_query.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize('manifest', [CSV_MANIFEST, PARQUET_MANIFEST], ids=['csv', 'parquet'])
async def test_athena_handler_setup_table_accepts_documented_manifests(mock_context, manifest):
    """The documented Storage Lens manifest shapes pass the DDL checks and the DDL is sent."""
    with patch(
        'awslabs.billing_cost_management_mcp_server.tools.storage_lens_tools.create_aws_client'
    ):
        athena_handler = AthenaHandler(mock_context)
        manifest_handler = ManifestHandler(mock_context)
    _athena_ddl_succeeds(
        athena_handler.athena_client, manifest_handler.extract_data_location(manifest)
    )
    athena_handler.execute_query = AsyncMock()

    await athena_handler.setup_table(
        'storage_lens_db',
        'storage_lens_metrics',
        manifest_handler.parse_schema(manifest),
        manifest_handler.extract_data_location(manifest),
        's3://b/out/',
    )

    ddl = athena_handler.execute_query.await_args_list[-1].args[0]
    assert 'CREATE EXTERNAL TABLE IF NOT EXISTS storage_lens_db.storage_lens_metrics' in ddl
    assert '`metric_value`' in ddl
    assert "LOCATION 's3://" in ddl


# --- The table follows the manifest: a stale LOCATION is re-pointed, each DDL completes first ---


def _manifest_for_day(day: str, base: dict = CSV_MANIFEST) -> dict:
    """A manifest whose report files sit in the dt=<day> folder, as Storage Lens writes them."""
    manifest = json.loads(json.dumps(base))
    for report_file in manifest['reportFiles']:
        report_file['key'] = report_file['key'].replace('dt=2020-11-03', f'dt={day}')
    return manifest


def _day_location(day: str) -> str:
    return (
        's3://amzn-s3-demo-destination-bucket/DestinationPrefix/StorageLens/123456789012/'
        f'my-dashboard-configuration-id/V_1/reports/dt={day}'
    )


class _FakeAthena:
    """Athena with one table: DDL takes effect only once polled, and SELECTs record what they read.

    A SELECT started while a DDL has not been seen to complete records 'ddl pending', because
    Athena runs queries concurrently and the SELECT may start before the table exists or moves.
    With instant_ddl, DDL takes effect when it starts, which isolates the LOCATION check.
    """

    def __init__(
        self,
        existing_location=None,
        metadata_has_location=True,
        instant_ddl=False,
        partition_keys=(),
        input_format='org.apache.hadoop.mapred.TextInputFormat',
        serde_lib='',
        polls_before_done=0,
    ):
        self.location = existing_location
        self.input_format = input_format
        self.serde_lib = serde_lib
        self.polls_before_done = polls_before_done
        self._polls: dict[str, int] = {}
        self.partition_keys = [{'Name': name, 'Type': 'string'} for name in partition_keys]
        self.instant_ddl = instant_ddl
        self.metadata_has_location = metadata_has_location
        self.statements: list[str] = []
        self.reads: list[str | None] = []
        self.read_by_id: dict[str, str | None] = {}
        self._pending: dict[str, str] = {}

    def start_query_execution(self, QueryString, QueryExecutionContext, ResultConfiguration):
        execution_id = f'q{len(self.statements)}'
        self.statements.append(QueryString)
        if QueryString.lstrip().upper().startswith(('CREATE', 'ALTER')):
            self._pending[execution_id] = QueryString
            if self.instant_ddl:
                self.get_query_execution(execution_id)
        else:
            read = 'ddl pending' if self._pending else self.location
            self.reads.append(read)
            self.read_by_id[execution_id] = read
        return {'QueryExecutionId': execution_id}

    def get_query_execution(self, QueryExecutionId):
        polls = self._polls[QueryExecutionId] = self._polls.get(QueryExecutionId, 0) + 1
        if polls <= self.polls_before_done:
            return {'QueryExecution': {'Status': {'State': 'RUNNING'}}}
        ddl = self._pending.pop(QueryExecutionId, '')
        location = re.search(r"LOCATION '([^']*)'", ddl)
        if ddl.lstrip().upper().startswith('ALTER') and location:
            self.location = location.group(1)
        elif 'CREATE EXTERNAL TABLE IF NOT EXISTS' in ddl and self.location is None and location:
            self.location = location.group(1)
        return {
            'QueryExecution': {
                'Status': {'State': 'SUCCEEDED'},
                'Statistics': {
                    'TotalExecutionTimeInMillis': 1,
                    'DataScannedInBytes': 1,
                    'EngineExecutionTimeInMillis': 1,
                },
            }
        }

    def get_table_metadata(self, CatalogName, DatabaseName, TableName):
        assert self.location is not None, 'table read before CREATE TABLE completed'
        parameters = {'EXTERNAL': 'TRUE'}
        if self.input_format:
            parameters['inputformat'] = self.input_format
        if self.serde_lib:
            parameters['serde.serialization.lib'] = self.serde_lib
        if self.metadata_has_location:
            parameters['location'] = self.location
        return {
            'TableMetadata': {
                'Name': TableName,
                'PartitionKeys': self.partition_keys,
                'Parameters': parameters,
            }
        }

    def get_query_results(self, QueryExecutionId):
        """A SELECT returns one row naming the folder it read."""
        if QueryExecutionId not in self.read_by_id:
            return {'ResultSet': {'ResultSetMetadata': {'ColumnInfo': []}, 'Rows': []}}
        header = {'Data': [{'VarCharValue': 'read'}]}
        row = {'Data': [{'VarCharValue': str(self.read_by_id[QueryExecutionId])}]}
        return {
            'ResultSet': {
                'ResultSetMetadata': {'ColumnInfo': [{'Label': 'read'}]},
                'Rows': [header, row],
            }
        }


def _query_tool_over(fake_athena, manifests_by_key, mock_context):
    s3_client = MagicMock()
    s3_client.get_object.side_effect = lambda Bucket, Key: {
        'Body': MagicMock(read=lambda: json.dumps(manifests_by_key[Key]).encode('utf-8'))
    }
    with patch(
        'awslabs.billing_cost_management_mcp_server.tools.storage_lens_tools.create_aws_client',
        side_effect=lambda service: {'s3': s3_client, 'athena': fake_athena}[service],
    ):
        return StorageLensQueryTool(mock_context)


_DAY1_MANIFEST_URI = 's3://b/manifests/dt=2026-10-27/manifest.json'
_DAY2_MANIFEST_URI = 's3://b/manifests/dt=2026-10-28/manifest.json'
_PARQUET_MANIFEST_URI = 's3://b/manifests/dt=2026-10-28/parquet/manifest.json'
_CUSTOM_MANIFEST_URI = 's3://b/manifests/custom/manifest.json'
_CUSTOM_MANIFEST = json.loads(json.dumps(CSV_MANIFEST))
_CUSTOM_MANIFEST['reportFiles'][0]['key'] = 'copies/storage-lens/report.csv'
_MANIFESTS = {
    'manifests/dt=2026-10-27/manifest.json': _manifest_for_day('2026-10-27'),
    'manifests/dt=2026-10-28/manifest.json': _manifest_for_day('2026-10-28'),
    'manifests/dt=2026-10-28/parquet/manifest.json': _manifest_for_day(
        '2026-10-28', PARQUET_MANIFEST
    ),
    'manifests/custom/manifest.json': _CUSTOM_MANIFEST,
}


@pytest.mark.asyncio
@pytest.mark.parametrize('instant_ddl', [False, True], ids=['athena', 'instant-ddl'])
async def test_later_manifest_is_read_not_the_first_days_folder(mock_context, instant_ddl):
    """Day 2's query reads day 2's folder, though the table was created over day 1's."""
    fake = _FakeAthena(instant_ddl=instant_ddl)
    tool = _query_tool_over(fake, _MANIFESTS, mock_context)
    with patch('asyncio.sleep', new_callable=AsyncMock):
        first = await tool.query_storage_lens('SELECT 1 FROM {table}', _DAY1_MANIFEST_URI)
        second = await tool.query_storage_lens('SELECT 1 FROM {table}', _DAY2_MANIFEST_URI)

    assert first['status'] == 'success' and second['status'] == 'success'
    assert fake.reads == [_day_location('2026-10-27'), _day_location('2026-10-28')]
    assert second['data']['data_location'] == fake.reads[1]


@pytest.mark.asyncio
@pytest.mark.parametrize('instant_ddl', [False, True], ids=['athena', 'instant-ddl'])
async def test_table_created_by_an_older_version_is_repointed(mock_context, instant_ddl):
    """An existing table left on an old dt= folder is moved with ALTER TABLE ... SET LOCATION."""
    fake = _FakeAthena(existing_location=_day_location('2026-01-01'), instant_ddl=instant_ddl)
    tool = _query_tool_over(fake, _MANIFESTS, mock_context)
    with patch('asyncio.sleep', new_callable=AsyncMock):
        result = await tool.query_storage_lens('SELECT 1 FROM {table}', _DAY2_MANIFEST_URI)

    assert result['status'] == 'success'
    assert fake.reads == [_day_location('2026-10-28')]
    alters = [s for s in fake.statements if s.lstrip().upper().startswith('ALTER')]
    assert alters == [
        f"ALTER TABLE storage_lens_db.storage_lens_metrics SET LOCATION '{_day_location('2026-10-28')}'"
    ]


@pytest.mark.asyncio
@pytest.mark.parametrize('suffix', ['', '/'])
async def test_table_already_on_the_manifest_folder_is_not_altered(mock_context, suffix):
    """No ALTER is sent when the table already reads the manifest's folder (trailing / or not)."""
    fake = _FakeAthena(existing_location=_day_location('2026-10-28') + suffix)
    tool = _query_tool_over(fake, _MANIFESTS, mock_context)
    with patch('asyncio.sleep', new_callable=AsyncMock):
        result = await tool.query_storage_lens('SELECT 1 FROM {table}', _DAY2_MANIFEST_URI)

    assert result['status'] == 'success'
    assert not [s for s in fake.statements if s.lstrip().upper().startswith('ALTER')]
    assert fake.reads == [_day_location('2026-10-28') + suffix]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    'existing_location,metadata_has_location,partition_keys',
    [
        ('s3://my-bucket/cur/data', True, ()),
        ('s3://my-bucket/StorageLens/1/c/V_1/reports', True, ('dt',)),
        (_day_location('2026-01-01'), True, ('dt',)),
        (_day_location('2026-01-01'), False, ()),
    ],
    ids=['other-folder', 'partitioned-on-reports', 'partitioned-on-a-day', 'no-location'],
)
async def test_table_not_made_by_this_tool_is_left_unchanged(
    mock_context, existing_location, metadata_has_location, partition_keys
):
    """Only an unpartitioned table on a report day folder is moved; another table is queried as is."""
    fake = _FakeAthena(
        existing_location=existing_location,
        metadata_has_location=metadata_has_location,
        partition_keys=partition_keys,
    )
    tool = _query_tool_over(fake, _MANIFESTS, mock_context)
    with patch('asyncio.sleep', new_callable=AsyncMock):
        result = await tool.query_storage_lens('SELECT 1 FROM {table}', _DAY2_MANIFEST_URI)

    assert result['status'] == 'success'
    assert not [s for s in fake.statements if s.lstrip().upper().startswith('ALTER')]
    assert fake.reads == [existing_location]


@pytest.mark.asyncio
async def test_first_query_waits_for_the_table_to_exist(mock_context):
    """The SELECT starts only after CREATE DATABASE and CREATE TABLE have completed."""
    fake = _FakeAthena()
    tool = _query_tool_over(fake, _MANIFESTS, mock_context)
    with patch('asyncio.sleep', new_callable=AsyncMock):
        await tool.query_storage_lens('SELECT 1 FROM {table}', _DAY1_MANIFEST_URI)

    assert fake.reads == [_day_location('2026-10-27')]


@pytest.mark.asyncio
async def test_failed_repoint_stops_before_the_select(mock_context):
    """If ALTER TABLE fails, the error is returned and the stale table is never read."""
    fake = _FakeAthena(existing_location=_day_location('2026-01-01'))
    real_get = fake.get_query_execution

    def get_query_execution(QueryExecutionId):
        if fake._pending.get(QueryExecutionId, '').lstrip().upper().startswith('ALTER'):
            fake._pending.pop(QueryExecutionId)
            return {
                'QueryExecution': {
                    'Status': {'State': 'FAILED', 'StateChangeReason': 'AccessDenied'}
                }
            }
        return real_get(QueryExecutionId)

    fake.get_query_execution = get_query_execution
    tool = _query_tool_over(fake, _MANIFESTS, mock_context)
    with patch('asyncio.sleep', new_callable=AsyncMock):
        result = await tool.query_storage_lens('SELECT 1 FROM {table}', _DAY2_MANIFEST_URI)

    assert result['status'] == 'error'
    assert 'Athena table setup (ALTER TABLE' in result['message']
    assert (
        f"SET LOCATION '{_day_location('2026-10-28')}') failed: AccessDenied" in result['message']
    )
    assert result['error_type'] != 'validation_error'
    assert fake.reads == []


# --- The example queries sum one record_type level ---


async def _storage_lens_description() -> str:
    from awslabs.billing_cost_management_mcp_server.tools import storage_lens_tools as stl_mod

    importlib.reload(stl_mod)
    tool = await stl_mod.storage_lens_server.get_tool('storage-lens')
    assert tool is not None
    return tool.description or ''


def _example_queries(description: str) -> dict[int, str]:
    examples = description.split('Example queries:', 1)[1]
    parts = re.split(r'^(\d+)\. [^\n]*\n', examples, flags=re.MULTILINE)
    return {int(number): query.strip() for number, query in zip(parts[1::2], parts[2::2])}


_EXPECTED_LEVEL = {1: 'BUCKET', 2: 'ACCOUNT', 3: 'BUCKET', 4: 'ACCOUNT', 5: 'ACCOUNT', 6: 'BUCKET'}


@pytest.mark.asyncio
async def test_every_example_query_filters_one_record_type():
    """Each example sums one aggregation level, so ACCOUNT, BUCKET and PREFIX rows are not added up."""
    queries = _example_queries(await _storage_lens_description())
    assert sorted(queries) == sorted(_EXPECTED_LEVEL)
    for number, query in queries.items():
        assert f"record_type = '{_EXPECTED_LEVEL[number]}'" in query, number
        assert query.count('record_type') == 1, number
        assert validate_query_is_readonly_select(query) is None, number
        assert references_qualified_table(
            query.replace('{table}', 'storage_lens_db.storage_lens_metrics'),
            'storage_lens_db',
            'storage_lens_metrics',
        ), number


@pytest.mark.asyncio
async def test_description_says_filter_one_record_type_before_sum_and_one_day_per_table():
    """The description warns about nested record_type levels and says which day the table holds."""
    description = await _storage_lens_description()
    assert 'filter to exactly one record_type before SUM' in description
    assert 'The record_value column is URL-encoded' in description
    assert "The table holds one day's report: the one the manifest describes" in description


@pytest.mark.asyncio
async def test_ddl_that_does_not_succeed_raises(mock_context, athena_handler):
    """A DDL statement that ends CANCELLED (not FAILED) still stops setup before the next step."""
    athena_handler.athena_client.start_query_execution.return_value = {'QueryExecutionId': 'q'}
    athena_handler.athena_client.get_query_execution.return_value = {
        'QueryExecution': {'Status': {'State': 'CANCELLED'}}
    }
    with patch('asyncio.sleep', new_callable=AsyncMock):
        with pytest.raises(RuntimeError, match='cancelled: no reason given'):
            await athena_handler.create_database('db', 's3://b/out/')
    athena_handler.athena_client.get_table_metadata.assert_not_called()


@pytest.mark.asyncio
async def test_ddl_that_ends_in_an_unexpected_state_raises(mock_context, athena_handler):
    """A DDL whose wait returns without SUCCEEDED (the timeout fallback) raises, naming the step."""
    athena_handler.athena_client.start_query_execution.return_value = {'QueryExecutionId': 'q'}
    athena_handler.wait_for_query_completion = AsyncMock(return_value={'status': 'ERROR'})
    with pytest.raises(RuntimeError, match=r'setup did not succeed \(CREATE DATABASE'):
        await athena_handler.create_database('db', 's3://b/out/')


@pytest.mark.asyncio
async def test_cancelled_query_raises_with_its_reason(mock_context, athena_handler):
    """A cancelled query raises with Athena's reason instead of returning a status-less dict."""
    athena_handler.athena_client.get_query_execution.return_value = {
        'QueryExecution': {'Status': {'State': 'CANCELLED', 'StateChangeReason': 'by user'}}
    }
    with pytest.raises(RuntimeError, match='Query cancelled: by user'):
        await athena_handler.wait_for_query_completion('q')


@pytest.mark.asyncio
async def test_table_is_not_moved_off_a_report_folder(mock_context):
    """A manifest outside a report day folder is refused, not moved to or read from day 1."""
    fake = _FakeAthena(existing_location=_day_location('2026-10-27'))
    tool = _query_tool_over(fake, _MANIFESTS, mock_context)
    with patch('asyncio.sleep', new_callable=AsyncMock):
        result = await tool.query_storage_lens('SELECT 1 FROM {table}', _CUSTOM_MANIFEST_URI)

    assert result['status'] == 'error'
    assert result['error_type'] == 'validation_error'
    assert 'which is not one' in result['message']
    assert 'Pass a different table_name' in result['message']
    assert not [s for s in fake.statements if s.lstrip().upper().startswith('ALTER')]
    assert fake.reads == []


@pytest.mark.asyncio
async def test_new_table_for_a_custom_folder_is_queried(mock_context):
    """With a fresh table_name, a manifest outside a report folder gets its own table."""
    fake = _FakeAthena()
    tool = _query_tool_over(fake, _MANIFESTS, mock_context)
    with patch('asyncio.sleep', new_callable=AsyncMock):
        result = await tool.query_storage_lens(
            'SELECT 1 FROM {table}', _CUSTOM_MANIFEST_URI, table_name='custom_copy'
        )

    assert result['status'] == 'success'
    assert fake.reads == ['s3://amzn-s3-demo-destination-bucket/copies/storage-lens']


@pytest.mark.parametrize(
    'location,matches',
    [
        (_day_location('2026-10-27'), True),
        (_day_location('2026-10-27') + '/', True),
        ('s3://b/StorageLens/o-abc123/cfg/V_1/reports/dt=2026-10-27', True),
        ('s3://b/StorageLens/1/cfg/reports/dt=2026-10-27', False),
        ('s3://b/prefix/reports/dt=2026-10-27', False),
        ('s3://b/StorageLens/1/cfg/V_1/reports/dt=latest', False),
        ('s3://b/StorageLens/1/cfg/V_1/reports/dt=2026-10-27/sub', False),
        ('s3://b/StorageLens/1/cfg/V_1/manifests/dt=2026-10-27', False),
        ('s3://b/StorageLens/1/cfg/V_1/reports', False),
    ],
)
def test_report_folder_pattern(location, matches):
    """Only a single day's Storage Lens report folder counts as one this tool created."""
    from awslabs.billing_cost_management_mcp_server.tools.storage_lens_tools import (
        _REPORT_FOLDER_PATTERN,
    )

    assert bool(_REPORT_FOLDER_PATTERN.fullmatch(location)) is matches


_TEXT_INPUT_FORMAT = 'org.apache.hadoop.mapred.TextInputFormat'
_PARQUET_INPUT_FORMAT = 'org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat'


@pytest.mark.asyncio
@pytest.mark.parametrize(
    'input_format,manifest_uri,table_format',
    [
        (_TEXT_INPUT_FORMAT, _PARQUET_MANIFEST_URI, 'CSV'),
        (_PARQUET_INPUT_FORMAT, _DAY2_MANIFEST_URI, 'Parquet'),
    ],
    ids=['csv-table-parquet-report', 'parquet-table-csv-report'],
)
@pytest.mark.parametrize('use_serde', [False, True], ids=['inputformat', 'serde-only'])
async def test_table_of_the_other_format_is_not_repointed(
    mock_context, input_format, manifest_uri, table_format, use_serde
):
    """A table is not pointed at files of the other format; the caller is told to use another name."""
    serde = {
        _TEXT_INPUT_FORMAT: 'org.apache.hadoop.hive.serde2.lazy.LazySimpleSerDe',
        _PARQUET_INPUT_FORMAT: 'org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe',
    }[input_format]
    fake = _FakeAthena(
        existing_location=_day_location('2026-10-27'),
        input_format='' if use_serde else input_format,
        serde_lib=serde if use_serde else '',
    )
    tool = _query_tool_over(fake, _MANIFESTS, mock_context)
    with patch('asyncio.sleep', new_callable=AsyncMock):
        result = await tool.query_storage_lens('SELECT 1 FROM {table}', manifest_uri)

    assert result['status'] == 'error'
    assert result['error_type'] == 'validation_error'
    assert f'created for {table_format} report files' in result['message']
    assert 'Pass a different table_name' in result['message']
    assert not [s for s in fake.statements if s.lstrip().upper().startswith('ALTER')]
    assert fake.reads == []


@pytest.mark.asyncio
@pytest.mark.parametrize(
    'input_format,serde_lib',
    [
        (_PARQUET_INPUT_FORMAT, ''),
        ('', 'org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe'),
        (_PARQUET_INPUT_FORMAT, 'org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe'),
    ],
    ids=['inputformat', 'serde-only', 'both-agree'],
)
async def test_table_of_the_same_format_is_repointed(mock_context, input_format, serde_lib):
    """A Parquet table, known by its inputformat or else its SerDe, is re-pointed to Parquet."""
    fake = _FakeAthena(
        existing_location=_day_location('2026-10-27'),
        input_format=input_format,
        serde_lib=serde_lib,
    )
    tool = _query_tool_over(fake, _MANIFESTS, mock_context)
    with patch('asyncio.sleep', new_callable=AsyncMock):
        result = await tool.query_storage_lens('SELECT 1 FROM {table}', _PARQUET_MANIFEST_URI)

    assert result['status'] == 'success'
    assert fake.reads == [_day_location('2026-10-28')]


@pytest.mark.asyncio
@pytest.mark.parametrize('statement', ['CREATE DATABASE', 'CREATE EXTERNAL TABLE'])
async def test_concurrent_create_is_not_an_error(mock_context, statement):
    """IF NOT EXISTS losing a race to another call (AlreadyExists) still runs the query."""
    fake = _FakeAthena()
    real_get = fake.get_query_execution

    def get_query_execution(QueryExecutionId):
        ddl = fake._pending.get(QueryExecutionId, '')
        if ddl.lstrip().startswith(statement):
            real_get(QueryExecutionId)
            return {
                'QueryExecution': {
                    'Status': {
                        'State': 'FAILED',
                        'StateChangeReason': 'AlreadyExistsException: it already exists',
                    }
                }
            }
        return real_get(QueryExecutionId)

    fake.get_query_execution = get_query_execution
    tool = _query_tool_over(fake, _MANIFESTS, mock_context)
    with patch('asyncio.sleep', new_callable=AsyncMock):
        result = await tool.query_storage_lens('SELECT 1 FROM {table}', _DAY1_MANIFEST_URI)

    assert result['status'] == 'success'
    assert fake.reads == [_day_location('2026-10-27')]


@pytest.mark.asyncio
async def test_alter_already_exists_failure_is_not_swallowed(mock_context, athena_handler):
    """Only IF NOT EXISTS statements treat AlreadyExists as done."""
    athena_handler.athena_client.start_query_execution.return_value = {'QueryExecutionId': 'q'}
    athena_handler.athena_client.get_query_execution.return_value = {
        'QueryExecution': {'Status': {'State': 'FAILED', 'StateChangeReason': 'already exists'}}
    }
    with pytest.raises(RuntimeError, match=r'Athena table setup \(ALTER TABLE db.t'):
        await athena_handler.run_ddl("ALTER TABLE db.t SET LOCATION 's3://b/x'", 'db', 's3://o/')


@pytest.mark.asyncio
async def test_cancelled_or_timed_out_setup_names_the_statement(mock_context, athena_handler):
    """A cancelled or timed-out setup statement says which statement it was."""
    athena_handler.athena_client.start_query_execution.return_value = {'QueryExecutionId': 'q'}
    athena_handler.athena_client.get_query_execution.return_value = {
        'QueryExecution': {'Status': {'State': 'CANCELLED', 'StateChangeReason': 'limit'}}
    }
    with pytest.raises(
        RuntimeError, match=r'setup \(CREATE DATABASE IF NOT EXISTS db\) cancelled'
    ):
        await athena_handler.create_database('db', 's3://b/out/')

    athena_handler.athena_client.get_query_execution.return_value = {
        'QueryExecution': {'Status': {'State': 'RUNNING'}}
    }
    with patch('asyncio.sleep', new_callable=AsyncMock):
        with pytest.raises(
            TimeoutError, match=r'setup \(CREATE DATABASE IF NOT EXISTS db\) timed out'
        ):
            await athena_handler.create_database('db', 's3://b/out/')


@pytest.mark.asyncio
@pytest.mark.parametrize(
    'manifest_uri',
    [_DAY2_MANIFEST_URI, _PARQUET_MANIFEST_URI],
    ids=['csv-report', 'parquet-report'],
)
@pytest.mark.parametrize(
    'input_format,serde_lib',
    [
        ('', ''),
        ('org.apache.hadoop.hive.ql.io.orc.OrcInputFormat', ''),
        ('', 'org.openx.data.jsonserde.JsonSerDe'),
        ('org.apache.hadoop.hive.ql.io.SymlinkTextInputFormat', ''),
        (_TEXT_INPUT_FORMAT, 'org.openx.data.jsonserde.JsonSerDe'),
        (_PARQUET_INPUT_FORMAT, 'org.apache.hadoop.hive.serde2.lazy.LazySimpleSerDe'),
    ],
    ids=['none', 'orc', 'json-serde', 'symlink', 'text-input-json-serde', 'formats-disagree'],
)
async def test_table_of_unknown_format_is_not_repointed(
    mock_context, manifest_uri, input_format, serde_lib
):
    """A table that is neither CSV nor Parquet, or records no format, is refused, not re-pointed."""
    fake = _FakeAthena(
        existing_location=_day_location('2026-10-27'),
        input_format=input_format,
        serde_lib=serde_lib,
    )
    tool = _query_tool_over(fake, _MANIFESTS, mock_context)
    with patch('asyncio.sleep', new_callable=AsyncMock):
        result = await tool.query_storage_lens('SELECT 1 FROM {table}', manifest_uri)

    assert result['status'] == 'error'
    assert result['error_type'] == 'validation_error'
    assert 'has no recognised report format' in result['message']
    assert 'Pass a different table_name' in result['message']
    assert not [s for s in fake.statements if s.lstrip().upper().startswith('ALTER')]
    assert fake.reads == []


@pytest.mark.asyncio
async def test_parallel_calls_for_different_days_do_not_mix(mock_context):
    """Two parallel calls on one table each read their own manifest's day, not the other's."""
    # The table starts on a third day, so both calls must ALTER it
    fake = _FakeAthena(existing_location=_day_location('2026-10-26'), polls_before_done=1)
    tool = _query_tool_over(fake, _MANIFESTS, mock_context)
    real_sleep = asyncio.sleep

    async def yield_once(_delay):
        await real_sleep(0)

    with patch('asyncio.sleep', side_effect=yield_once):
        day1, day2 = await asyncio.gather(
            tool.query_storage_lens('SELECT 1 FROM {table}', _DAY1_MANIFEST_URI),
            tool.query_storage_lens('SELECT 1 FROM {table}', _DAY2_MANIFEST_URI),
        )

    assert day1['status'] == 'success' and day2['status'] == 'success'
    assert sorted(str(read) for read in fake.reads) == [
        _day_location('2026-10-27'),
        _day_location('2026-10-28'),
    ]
    # Each call's SELECT read the folder its own response reports
    assert day1['data']['rows'] == [{'read': _day_location('2026-10-27')}]
    assert day2['data']['rows'] == [{'read': _day_location('2026-10-28')}]
    assert day1['data']['data_location'] == _day_location('2026-10-27')
    assert day2['data']['data_location'] == _day_location('2026-10-28')
    assert len([s for s in fake.statements if s.lstrip().upper().startswith('ALTER')]) == 2


@pytest.mark.asyncio
@pytest.mark.parametrize(
    'input_format,serde_lib',
    [
        ('', 'org.apache.hadoop.hive.serde2.lazy.LazySimpleSerDe'),
        ('', 'org.apache.hadoop.hive.serde2.OpenCSVSerde'),
        (_TEXT_INPUT_FORMAT, 'org.apache.hadoop.hive.serde2.lazy.LazySimpleSerDe'),
        (_TEXT_INPUT_FORMAT, 'org.apache.hadoop.hive.serde2.OpenCSVSerde'),
    ],
    ids=['lazy-simple', 'open-csv', 'tool-created-csv', 'open-csv-with-inputformat'],
)
async def test_csv_table_known_by_its_serde_is_repointed(mock_context, input_format, serde_lib):
    """A CSV table, by its SerDe alone or with TextInputFormat as Athena DDL records it, is re-pointed."""
    fake = _FakeAthena(
        existing_location=_day_location('2026-10-27'),
        input_format=input_format,
        serde_lib=serde_lib,
    )
    tool = _query_tool_over(fake, _MANIFESTS, mock_context)
    with patch('asyncio.sleep', new_callable=AsyncMock):
        result = await tool.query_storage_lens('SELECT 1 FROM {table}', _DAY2_MANIFEST_URI)

    assert result['status'] == 'success'
    assert fake.reads == [_day_location('2026-10-28')]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    'input_format,manifest_uri,table_format',
    [
        (_PARQUET_INPUT_FORMAT, _DAY2_MANIFEST_URI, 'Parquet'),
        (_TEXT_INPUT_FORMAT, _PARQUET_MANIFEST_URI, 'CSV'),
    ],
    ids=['parquet-table-csv-report', 'csv-table-parquet-report'],
)
async def test_table_on_the_folder_but_of_the_other_format_is_refused(
    mock_context, input_format, manifest_uri, table_format
):
    """A table already on the manifest's folder but created for the other format is not read."""
    fake = _FakeAthena(existing_location=_day_location('2026-10-28'), input_format=input_format)
    tool = _query_tool_over(fake, _MANIFESTS, mock_context)
    with patch('asyncio.sleep', new_callable=AsyncMock):
        result = await tool.query_storage_lens('SELECT 1 FROM {table}', manifest_uri)

    assert result['status'] == 'error'
    assert result['error_type'] == 'validation_error'
    assert f'created for {table_format} report files' in result['message']
    assert fake.reads == []


@pytest.mark.asyncio
async def test_table_on_the_folder_of_unknown_format_is_queried(mock_context):
    """A table already on the manifest's folder whose format is not recorded is queried as before."""
    fake = _FakeAthena(existing_location=_day_location('2026-10-28'), input_format='')
    tool = _query_tool_over(fake, _MANIFESTS, mock_context)
    with patch('asyncio.sleep', new_callable=AsyncMock):
        result = await tool.query_storage_lens('SELECT 1 FROM {table}', _DAY2_MANIFEST_URI)

    assert result['status'] == 'success'
    assert fake.reads == [_day_location('2026-10-28')]


@pytest.mark.asyncio
async def test_failed_create_is_not_taken_for_a_lost_race(mock_context, athena_handler):
    """'already exists' in the statement text, not Athena's reason, does not hide a failure."""
    athena_handler.athena_client.start_query_execution.return_value = {'QueryExecutionId': 'q'}
    athena_handler.athena_client.get_query_execution.return_value = {
        'QueryExecution': {'Status': {'State': 'FAILED', 'StateChangeReason': 'AccessDenied'}}
    }
    with pytest.raises(RuntimeError, match='failed: AccessDenied'):
        await athena_handler.run_ddl(
            "CREATE EXTERNAL TABLE IF NOT EXISTS db.t (a STRING) LOCATION 's3://b/already exists/'",
            'db',
            's3://o/',
        )
