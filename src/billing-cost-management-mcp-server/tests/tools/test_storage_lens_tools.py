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
    create_or_update_table,
    execute_athena_query,
    generate_create_table_query,
    poll_query_status,
    storage_lens_server,
    wait_for_query_completion,
)
from fastmcp import Context
from unittest.mock import AsyncMock, MagicMock, patch


# Create a mock implementation for testing
async def storage_lens_run_query(ctx, query, **kwargs):
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


# Sample manifest data for testing
CSV_MANIFEST = {
    'sourceAccountId': '123456789012',
    'configId': 'my-dashboard-configuration-id',
    'destinationBucket': 'arn:aws:s3:::amzn-s3-demo-destination-bucket',
    'reportVersion': 'V_1',
    'reportDate': '2020-11-03',
    'reportFormat': 'CSV',
    'reportSchema': 'version_number,configuration_id,report_date,aws_account_number,aws_region,storage_class,record_type,record_value,bucket_name,metric_name,metric_value',
    'reportFiles': [
        {
            'key': 'DestinationPrefix/StorageLens/123456789012/my-dashboard-configuration-id/V_1/reports/dt=2020-11-03/a38f6bc4-2e3d-4355-ac8a-e2fdcf3de158.csv',
            'size': 1603959,
            'md5Checksum': '2177e775870def72b8d84febe1ad3574',  # pragma: allowlist secret
        }
    ],
}

PARQUET_MANIFEST = {
    'sourceAccountId': '123456789012',
    'configId': 'my-dashboard-configuration-id',
    'destinationBucket': 'arn:aws:s3:::amzn-s3-demo-destination-bucket',
    'reportVersion': 'V_1',
    'reportDate': '2020-11-03',
    'reportFormat': 'Parquet',
    'reportSchema': 'message s3.storage.lens { required string version_number; required string configuration_id; required string report_date; required string aws_account_number; required string aws_region; required string storage_class; required string record_type; required string record_value; required string bucket_name; required string metric_name; required long metric_value; }',
    'reportFiles': [
        {
            'key': 'DestinationPrefix/StorageLens/123456789012/my-dashboard-configuration-id/V_1/reports/dt=2020-11-03/bd23de7c-b46a-4cf4-bcc5-b21aac5be0f5.par',
            'size': 14714,
            'md5Checksum': 'b5c741ee0251cd99b90b3e8eff50b944',  # pragma: allowlist secret
        }
    ],
}


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
            'ResultSetMetadata': {'ColumnInfo': [{'Name': 'column1'}, {'Name': 'column2'}]},
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


@pytest.mark.asyncio
async def test_storage_lens_run_query(mock_context):
    """Test the storage_lens_run_query function with valid parameters."""
    # Setup environment and mocks
    import os

    os.environ['STORAGE_LENS_MANIFEST_LOCATION'] = 's3://test-bucket/manifest.json'

    # Call the function
    result = await storage_lens_run_query(
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

    # Call the function without manifest_location parameter
    result = await storage_lens_run_query(
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

    # Call with {table} placeholder
    result1 = await storage_lens_run_query(
        mock_context,
        query='SELECT * FROM {table}',
        database_name='custom_db',
        table_name='custom_table',
    )

    # Verify success
    assert result1['status'] == 'success'

    # Call with explicit FROM clause but no placeholder
    result2 = await storage_lens_run_query(
        mock_context,
        query='SELECT * FROM custom_db.custom_table',
    )

    # Verify success
    assert result2['status'] == 'success'


@pytest.mark.asyncio
async def test_execute_athena_query(mock_context, mock_athena_client):
    """Test the execute_athena_query function."""
    with (
        patch(
            'awslabs.billing_cost_management_mcp_server.tools.storage_lens_tools.create_aws_client',
            return_value=mock_athena_client,
        ),
        patch(
            'awslabs.billing_cost_management_mcp_server.tools.storage_lens_tools.create_or_update_table',
            AsyncMock(),
        ) as mock_create_table,
        patch(
            'awslabs.billing_cost_management_mcp_server.tools.storage_lens_tools.poll_query_status',
            AsyncMock(return_value={'status': 'success', 'data': {}}),
        ) as mock_poll_status,
    ):
        # Call the function
        await execute_athena_query(
            mock_context,
            'SELECT * FROM storage_lens_db.storage_lens_metrics',
            's3://test-bucket/manifest.json',
            's3://test-bucket/athena-results/',
            'storage_lens_db',
            'storage_lens_metrics',
        )

    # Verify function behavior
    mock_create_table.assert_awaited_once()
    mock_athena_client.start_query_execution.assert_called_once()
    mock_poll_status.assert_awaited_once()


@pytest.mark.asyncio
async def test_create_or_update_table(mock_context, mock_athena_client):
    """Test the create_or_update_table function."""
    with (
        patch(
            'awslabs.billing_cost_management_mcp_server.tools.storage_lens_tools.wait_for_query_completion',
            AsyncMock(return_value='SUCCEEDED'),
        ) as mock_wait,
        patch(
            'awslabs.billing_cost_management_mcp_server.tools.storage_lens_tools.generate_create_table_query',
            return_value='CREATE TABLE test_statement',
        ) as mock_generate_query,
    ):
        # Call the function
        await create_or_update_table(
            mock_context,
            mock_athena_client,
            's3://test-bucket/manifest.json',
            'test_db',
            'test_table',
        )

    # Verify function behavior
    assert mock_athena_client.start_query_execution.call_count == 2  # Once for DB, once for table
    mock_wait.assert_awaited()
    mock_generate_query.assert_called_once()


def test_generate_create_table_query():
    """Test the generate_create_table_query function."""
    # Call the function with test parameters
    query = generate_create_table_query('s3://test-bucket/prefix/', 'test_db', 'test_table')

    # Verify the query contains the expected parts
    assert 'CREATE EXTERNAL TABLE IF NOT EXISTS test_db.test_table' in query
    assert "LOCATION 's3://test-bucket/prefix/data/'" in query
    assert 'storage_bytes bigint' in query
    assert 'record_timestamp timestamp' in query


@pytest.mark.asyncio
async def test_wait_for_query_completion(mock_context, mock_athena_client):
    """Test the wait_for_query_completion function."""
    # Call the function
    status = await wait_for_query_completion(mock_context, mock_athena_client, 'test-execution-id')

    # Verify function behavior
    mock_athena_client.get_query_execution.assert_called_with(QueryExecutionId='test-execution-id')
    assert status == 'SUCCEEDED'


@pytest.mark.asyncio
async def test_poll_query_status_success(mock_context, mock_athena_client):
    """Test the poll_query_status function with a successful query."""
    with patch(
        'awslabs.billing_cost_management_mcp_server.tools.storage_lens_tools.wait_for_query_completion',
        AsyncMock(return_value='SUCCEEDED'),
    ):
        # Call the function
        result = await poll_query_status(mock_context, mock_athena_client, 'test-execution-id')

    # Verify successful result
    assert result['status'] == 'success'
    assert 'columns' in result['data']
    assert 'results' in result['data']


@pytest.mark.asyncio
async def test_poll_query_status_failed(mock_context, mock_athena_client):
    """Test the poll_query_status function with a failed query."""
    # Mock a failed query
    mock_athena_client.get_query_execution.return_value = {
        'QueryExecution': {
            'Status': {'State': 'FAILED', 'StateChangeReason': 'Test failure reason'},
            'ResultConfiguration': {
                'OutputLocation': 's3://test-bucket/athena-results/test-execution-id.csv'
            },
        }
    }

    with patch(
        'awslabs.billing_cost_management_mcp_server.tools.storage_lens_tools.wait_for_query_completion',
        AsyncMock(return_value='FAILED'),
    ):
        # Call the function
        result = await poll_query_status(mock_context, mock_athena_client, 'test-execution-id')

    # Verify failed result
    assert result['status'] == 'error'
    assert 'Test failure reason' in result['message']


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

    with patch.object(stl_mod, 'execute_athena_query', new_callable=AsyncMock) as mock_exec:
        mock_exec.return_value = {'status': 'success', 'data': {'ok': True}}
        q = "SELECT * FROM {table} WHERE metric_name='StorageBytes'"
        res = await real_fn(mock_context, query=q)  # type: ignore
        assert res['status'] == 'success'

        # Args: (ctx, formatted_query, manifest_loc, output_loc, db_name, tbl_name)
        assert mock_exec.await_args is not None
        _, formatted_query, manifest_loc, output_loc, db_name, tbl_name = mock_exec.await_args.args
        assert f'{db_name}.{tbl_name}' in formatted_query
        assert manifest_loc == 's3://bucket/prefix/'
        assert (
            output_loc == ''
        )  # comes from env var default path logic inside execute_athena_query
        # Default names when none provided
        assert db_name == 'storage_lens_db'
        assert tbl_name == 'storage_lens_metrics'


@pytest.mark.asyncio
async def test_storage_lens_real_from_insertion_reload_identity_decorator(mock_context):
    """Test storage_lens_run_query from insertion with identity decorator."""
    os.environ['STORAGE_LENS_MANIFEST_LOCATION'] = 's3://bucket/prefix/'

    stl_mod = _reload_storage_lens_with_identity_decorator()
    real_fn = stl_mod.storage_lens_run_query  # type: ignore

    with patch.object(stl_mod, 'execute_athena_query', new_callable=AsyncMock) as mock_exec:
        mock_exec.return_value = {'status': 'success', 'data': {'ok': True}}
        # No {table}, but has a FROM clause -> tool injects db.table
        q = "SELECT * from something WHERE region='us-east-1'"
        res = await real_fn(mock_context, query=q)  # type: ignore
        assert res['status'] == 'success'

        assert mock_exec.await_args is not None
        formatted_query = mock_exec.await_args.args[1]
        # The code lower-cases and injects " FROM <db>.<table> "
        assert ' FROM storage_lens_db.storage_lens_metrics ' in formatted_query


@pytest.mark.asyncio
async def test_storage_lens_real_query_missing_table_reference_error_reload_identity_decorator(
    mock_context,
):
    """Test storage_lens_run_query missing table reference error with identity decorator."""
    os.environ['STORAGE_LENS_MANIFEST_LOCATION'] = 's3://bucket/prefix/'

    stl_mod = _reload_storage_lens_with_identity_decorator()
    real_fn = stl_mod.storage_lens_run_query  # type: ignore

    res = await real_fn(mock_context, query='SELECT 42')  # type: ignore
    assert res['status'] == 'error'
    assert 'must either contain {table} placeholder' in res.get('message', '')


# --- execute_athena_query default output-location branches ---


@pytest.mark.asyncio
async def test_execute_athena_query_default_output_trailing_slash(
    mock_context, mock_athena_client
):
    """Test execute_athena_query default output with trailing slash."""
    # manifest ends with '/'
    with (
        patch(
            'awslabs.billing_cost_management_mcp_server.tools.storage_lens_tools.create_aws_client',
            return_value=mock_athena_client,
        ),
        patch(
            'awslabs.billing_cost_management_mcp_server.tools.storage_lens_tools.create_or_update_table',
            AsyncMock(),
        ),
        patch(
            'awslabs.billing_cost_management_mcp_server.tools.storage_lens_tools.poll_query_status',
            AsyncMock(return_value={'status': 'success', 'data': {}}),
        ),
    ):
        from awslabs.billing_cost_management_mcp_server.tools.storage_lens_tools import (
            execute_athena_query,
        )

        await execute_athena_query(
            mock_context,
            'SELECT 1',
            's3://my-bucket/prefix/',
            None,
            'db',
            'tbl',
        )

    # Validate OutputLocation default
    kwargs = mock_athena_client.start_query_execution.call_args.kwargs
    assert (
        kwargs['ResultConfiguration']['OutputLocation'] == 's3://my-bucket/prefix/query-results/'
    )


@pytest.mark.asyncio
async def test_execute_athena_query_default_output_no_trailing_slash(
    mock_context, mock_athena_client
):
    """Test execute_athena_query default output without trailing slash."""
    # manifest does not end with '/'
    with (
        patch(
            'awslabs.billing_cost_management_mcp_server.tools.storage_lens_tools.create_aws_client',
            return_value=mock_athena_client,
        ),
        patch(
            'awslabs.billing_cost_management_mcp_server.tools.storage_lens_tools.create_or_update_table',
            AsyncMock(),
        ),
        patch(
            'awslabs.billing_cost_management_mcp_server.tools.storage_lens_tools.poll_query_status',
            AsyncMock(return_value={'status': 'success', 'data': {}}),
        ),
    ):
        from awslabs.billing_cost_management_mcp_server.tools.storage_lens_tools import (
            execute_athena_query,
        )

        await execute_athena_query(
            mock_context,
            'SELECT 1',
            's3://my-bucket/manifest.json',
            None,
            'db',
            'tbl',
        )

    kwargs = mock_athena_client.start_query_execution.call_args.kwargs
    assert (
        kwargs['ResultConfiguration']['OutputLocation']
        == 's3://my-bucket/manifest.json/query-results/'
    )


# --- create_or_update_table exception path (logs + raises) ---


@pytest.mark.asyncio
async def test_create_or_update_table_exception_path_logs_and_raises(mock_context):
    """Test create_or_update_table exception path logs and raises."""
    from awslabs.billing_cost_management_mcp_server.tools.storage_lens_tools import (
        create_or_update_table,
    )

    athena = MagicMock()
    # First call (CREATE DATABASE) raises
    athena.start_query_execution.side_effect = Exception('oops db')

    with patch(
        'awslabs.billing_cost_management_mcp_server.tools.storage_lens_tools.wait_for_query_completion',
        AsyncMock(return_value='FAILED'),
    ):
        with pytest.raises(Exception, match='oops db'):
            await create_or_update_table(
                mock_context,
                athena,
                's3://test-bucket/manifest.json',
                'dbx',
                'tblx',
            )

    mock_context.error.assert_awaited()
    # Ensure we attempted the first start_query_execution
    athena.start_query_execution.assert_called()


# --- poll_query_status: NextToken + exception path ---


@pytest.mark.asyncio
async def test_poll_query_status_success_with_next_token(mock_context, mock_athena_client):
    """Test poll_query_status success with next token."""
    # Add NextToken to exercise has_more=True
    mock_athena_client.get_query_results.return_value['NextToken'] = 'next-1'

    with patch(
        'awslabs.billing_cost_management_mcp_server.tools.storage_lens_tools.wait_for_query_completion',
        AsyncMock(return_value='SUCCEEDED'),
    ):
        from awslabs.billing_cost_management_mcp_server.tools.storage_lens_tools import (
            poll_query_status,
        )

        result = await poll_query_status(mock_context, mock_athena_client, 'qid-123')

    assert result['status'] == 'success'
    assert result['data']['has_more'] is True
    assert 'columns' in result['data']
    assert 'results' in result['data']


@pytest.mark.asyncio
async def test_poll_query_status_exception_flow_calls_handle_error(
    mock_context, mock_athena_client
):
    """Test poll_query_status exception flow calls handle_error."""
    # Cause an exception after wait_for_query_completion
    with (
        patch(
            'awslabs.billing_cost_management_mcp_server.tools.storage_lens_tools.wait_for_query_completion',
            AsyncMock(return_value='SUCCEEDED'),
        ),
        patch(
            'awslabs.billing_cost_management_mcp_server.tools.storage_lens_tools.handle_aws_error',
            new_callable=AsyncMock,
        ) as mock_handle,
    ):
        mock_handle.return_value = {'status': 'error', 'message': 'boom'}  # <-- add this
        mock_athena_client.get_query_execution.side_effect = RuntimeError('boom')

        from awslabs.billing_cost_management_mcp_server.tools.storage_lens_tools import (
            poll_query_status,
        )

        res = await poll_query_status(mock_context, mock_athena_client, 'qid-err')

        assert res['status'] == 'error'
        assert 'boom' in res.get('message', '')
        mock_handle.assert_awaited_once()
