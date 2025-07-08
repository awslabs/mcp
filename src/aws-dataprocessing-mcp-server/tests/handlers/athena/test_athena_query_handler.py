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


import pytest
from awslabs.aws_dataprocessing_mcp_server.handlers.athena.athena_query_handler import (
    AthenaQueryHandler,
)
from botocore.exceptions import ClientError
from mcp.server.fastmcp import Context
from unittest.mock import Mock, patch


@pytest.fixture
def mock_athena_client():
    """Create a mock Athena client instance for testing."""
    return Mock()


@pytest.fixture
def mock_aws_helper():
    """Create a mock AwsHelper instance for testing."""
    with patch(
        'awslabs.aws_dataprocessing_mcp_server.handlers.athena.athena_query_handler.AwsHelper'
    ) as mock:
        mock.create_boto3_client.return_value = Mock()
        yield mock


@pytest.fixture
def handler(mock_aws_helper):
    """Create a mock AthenaQueryHandler instance for testing."""
    mcp = Mock()
    return AthenaQueryHandler(mcp, allow_write=True)


@pytest.fixture
def read_only_handler(mock_aws_helper):
    """Create a mock AthenaQueryHandler instance with read-only access for testing."""
    mcp = Mock()
    return AthenaQueryHandler(mcp, allow_write=False)


@pytest.fixture
def mock_context():
    """Create a mock context instance for testing."""
    return Mock(spec=Context)


# Query Execution Tests


@pytest.mark.asyncio
async def test_batch_get_query_execution_success(handler, mock_athena_client):
    """Test successful batch retrieval of query executions."""
    handler.athena_client = mock_athena_client
    mock_athena_client.batch_get_query_execution.return_value = {
        'QueryExecutions': [{'QueryExecutionId': 'query1'}, {'QueryExecutionId': 'query2'}],
        'UnprocessedQueryExecutionIds': [],
    }

    ctx = Mock()
    response = await handler.manage_aws_athena_queries(
        ctx, operation='batch-get-query-execution', query_execution_ids=['query1', 'query2']
    )

    assert not response.isError
    assert len(response.query_executions) == 2
    assert len(response.unprocessed_query_execution_ids) == 0
    mock_athena_client.batch_get_query_execution.assert_called_once_with(
        QueryExecutionIds=['query1', 'query2']
    )


@pytest.mark.asyncio
async def test_batch_get_query_execution_missing_parameters(handler):
    """Test that batch get query execution fails when query_execution_ids is missing."""
    ctx = Mock()
    with pytest.raises(ValueError):
        await handler.manage_aws_athena_queries(
            ctx, operation='batch-get-query-execution', query_execution_ids=None
        )


@pytest.mark.asyncio
async def test_get_query_execution_success(handler, mock_athena_client):
    """Test successful retrieval of a query execution."""
    handler.athena_client = mock_athena_client
    mock_athena_client.get_query_execution.return_value = {
        'QueryExecution': {'QueryExecutionId': 'query1', 'Status': {'State': 'SUCCEEDED'}}
    }

    ctx = Mock()
    response = await handler.manage_aws_athena_queries(
        ctx, operation='get-query-execution', query_execution_id='query1'
    )

    assert not response.isError
    assert response.query_execution_id == 'query1'
    assert response.query_execution['Status']['State'] == 'SUCCEEDED'
    mock_athena_client.get_query_execution.assert_called_once_with(QueryExecutionId='query1')


@pytest.mark.asyncio
async def test_get_query_execution_missing_parameters(handler):
    """Test that get query execution fails when query_execution_id is missing."""
    ctx = Mock()
    with pytest.raises(ValueError):
        await handler.manage_aws_athena_queries(
            ctx, operation='get-query-execution', query_execution_id=None
        )


@pytest.mark.asyncio
async def test_get_query_results_success(handler, mock_athena_client):
    """Test successful retrieval of query results."""
    handler.athena_client = mock_athena_client
    mock_athena_client.get_query_results.return_value = {
        'ResultSet': {
            'Rows': [{'Data': [{'VarCharValue': 'header1'}, {'VarCharValue': 'header2'}]}],
            'ResultSetMetadata': {'ColumnInfo': []},
        },
        'NextToken': 'next-token',
        'UpdateCount': 0,
    }

    ctx = Mock()
    response = await handler.manage_aws_athena_queries(
        ctx,
        operation='get-query-results',
        query_execution_id='query1',
        max_results=10,
        next_token='token',
        query_result_type='DATA_ROWS',
    )

    assert not response.isError
    assert response.query_execution_id == 'query1'
    assert response.next_token == 'next-token'
    assert response.update_count == 0
    mock_athena_client.get_query_results.assert_called_once_with(
        QueryExecutionId='query1', MaxResults=10, NextToken='token', QueryResultType='DATA_ROWS'
    )


@pytest.mark.asyncio
async def test_get_query_results_missing_parameters(handler):
    """Test that get query results fails when query_execution_id is missing."""
    ctx = Mock()
    with pytest.raises(ValueError):
        await handler.manage_aws_athena_queries(
            ctx, operation='get-query-results', query_execution_id=None
        )


@pytest.mark.asyncio
async def test_get_query_runtime_statistics_success(handler, mock_athena_client):
    """Test successful retrieval of query runtime statistics."""
    handler.athena_client = mock_athena_client
    mock_athena_client.get_query_runtime_statistics.return_value = {
        'QueryRuntimeStatistics': {
            'Timeline': {'QueryQueueTime': 100, 'QueryPlanningTime': 200},
            'Rows': {'InputRows': 1000, 'OutputRows': 500},
        }
    }

    ctx = Mock()
    response = await handler.manage_aws_athena_queries(
        ctx, operation='get-query-runtime-statistics', query_execution_id='query1'
    )

    assert not response.isError
    assert response.query_execution_id == 'query1'
    assert response.statistics['Timeline']['QueryQueueTime'] == 100
    mock_athena_client.get_query_runtime_statistics.assert_called_once_with(
        QueryExecutionId='query1'
    )


@pytest.mark.asyncio
async def test_get_query_runtime_statistics_missing_parameters(handler):
    """Test that get query runtime statistics fails when query_execution_id is missing."""
    ctx = Mock()
    with pytest.raises(ValueError):
        await handler.manage_aws_athena_queries(
            ctx, operation='get-query-runtime-statistics', query_execution_id=None
        )


@pytest.mark.asyncio
async def test_list_query_executions_success(handler, mock_athena_client):
    """Test successful listing of query executions."""
    handler.athena_client = mock_athena_client
    mock_athena_client.list_query_executions.return_value = {
        'QueryExecutionIds': ['query1', 'query2', 'query3'],
        'NextToken': 'next-token',
    }

    ctx = Mock()
    response = await handler.manage_aws_athena_queries(
        ctx,
        operation='list-query-executions',
        max_results=10,
        next_token='token',
        work_group='primary',
    )

    assert not response.isError
    assert len(response.query_execution_ids) == 3
    assert response.count == 3
    assert response.next_token == 'next-token'
    mock_athena_client.list_query_executions.assert_called_once_with(
        MaxResults=10, NextToken='token', WorkGroup='primary'
    )


@pytest.mark.asyncio
async def test_start_query_execution_success(handler, mock_athena_client):
    """Test successful start of a query execution."""
    handler.athena_client = mock_athena_client
    mock_athena_client.start_query_execution.return_value = {'QueryExecutionId': 'query1'}

    ctx = Mock()
    response = await handler.manage_aws_athena_queries(
        ctx,
        operation='start-query-execution',
        query_string='SELECT * FROM table',
        client_request_token='token123',
        query_execution_context={'Database': 'db1'},
        result_configuration={'OutputLocation': 's3://bucket/path'},
        work_group='primary',
        execution_parameters=['param1', 'param2'],
        result_reuse_configuration={'ResultReuseByAgeConfiguration': {'Enabled': True}},
    )

    assert not response.isError
    assert response.query_execution_id == 'query1'
    mock_athena_client.start_query_execution.assert_called_once_with(
        QueryString='SELECT * FROM table',
        ClientRequestToken='token123',
        QueryExecutionContext={'Database': 'db1'},
        ResultConfiguration={'OutputLocation': 's3://bucket/path'},
        WorkGroup='primary',
        ExecutionParameters=['param1', 'param2'],
        ResultReuseConfiguration={'ResultReuseByAgeConfiguration': {'Enabled': True}},
    )


@pytest.mark.asyncio
async def test_start_query_execution_missing_parameters(handler):
    """Test that start query execution fails when query_string is missing."""
    ctx = Mock()
    with pytest.raises(ValueError):
        await handler.manage_aws_athena_queries(
            ctx, operation='start-query-execution', query_string=None
        )


@pytest.mark.asyncio
async def test_start_query_execution_without_write_permission_non_select(read_only_handler):
    """Test that starting a non-select query execution fails when write access is disabled."""
    ctx = Mock()
    response = await read_only_handler.manage_aws_athena_queries(
        ctx, operation='start-query-execution', query_string='INSERT INTO table VALUES (1, 2, 3)'
    )

    assert response.isError
    assert response.query_execution_id == ''


@pytest.mark.asyncio
async def test_start_query_execution_without_write_permission_select(
    read_only_handler, mock_athena_client
):
    """Test that starting a select query execution succeeds when write access is disabled."""
    read_only_handler.athena_client = mock_athena_client
    mock_athena_client.start_query_execution.return_value = {'QueryExecutionId': 'query1'}

    ctx = Mock()
    response = await read_only_handler.manage_aws_athena_queries(
        ctx, operation='start-query-execution', query_string='SELECT * FROM table'
    )

    assert not response.isError
    assert response.query_execution_id == 'query1'


@pytest.mark.asyncio
async def test_start_query_execution_without_write_permission_ctas(read_only_handler):
    """Test that starting a CTAS query execution fails when write access is disabled."""
    ctx = Mock()
    response = await read_only_handler.manage_aws_athena_queries(
        ctx, operation='start-query-execution', query_string='CREATE TABLE AS SELECT * FROM table'
    )

    assert response.isError
    assert response.query_execution_id == ''


@pytest.mark.asyncio
async def test_stop_query_execution_success(handler, mock_athena_client):
    """Test successful stop of a query execution."""
    handler.athena_client = mock_athena_client

    ctx = Mock()
    response = await handler.manage_aws_athena_queries(
        ctx, operation='stop-query-execution', query_execution_id='query1'
    )

    assert not response.isError
    assert response.query_execution_id == 'query1'
    mock_athena_client.stop_query_execution.assert_called_once_with(QueryExecutionId='query1')


@pytest.mark.asyncio
async def test_stop_query_execution_missing_parameters(handler):
    """Test that stop query execution fails when query_execution_id is missing."""
    ctx = Mock()
    with pytest.raises(ValueError):
        await handler.manage_aws_athena_queries(
            ctx, operation='stop-query-execution', query_execution_id=None
        )


@pytest.mark.asyncio
async def test_invalid_query_operation(handler):
    """Test that running manage_aws_athena_queries with an invalid operation results in an error."""
    ctx = Mock()
    response = await handler.manage_aws_athena_queries(ctx, operation='invalid-operation')

    assert response.isError
    assert 'Invalid operation' in response.content[0].text


@pytest.mark.asyncio
async def test_query_client_error_handling(handler, mock_athena_client):
    """Test error handling when Athena client raises an exception."""
    handler.athena_client = mock_athena_client
    mock_athena_client.get_query_execution.side_effect = ClientError(
        {'Error': {'Code': 'InvalidRequestException', 'Message': 'Invalid request'}},
        'GetQueryExecution',
    )

    ctx = Mock()
    response = await handler.manage_aws_athena_queries(
        ctx, operation='get-query-execution', query_execution_id='query1'
    )

    assert response.isError
    assert 'Error in manage_aws_athena_queries' in response.content[0].text


# Named Query Tests


@pytest.mark.asyncio
async def test_batch_get_named_query_success(handler, mock_athena_client):
    """Test successful batch retrieval of named queries."""
    handler.athena_client = mock_athena_client
    mock_athena_client.batch_get_named_query.return_value = {
        'NamedQueries': [{'Name': 'query1'}, {'Name': 'query2'}],
        'UnprocessedNamedQueryIds': [],
    }

    ctx = Mock()
    response = await handler.manage_aws_athena_named_queries(
        ctx, operation='batch-get-named-query', named_query_ids=['id1', 'id2']
    )

    assert not response.isError
    assert len(response.named_queries) == 2
    assert len(response.unprocessed_named_query_ids) == 0
    mock_athena_client.batch_get_named_query.assert_called_once_with(NamedQueryIds=['id1', 'id2'])


@pytest.mark.asyncio
async def test_batch_get_named_query_missing_parameters(handler):
    """Test that batch get named query fails when named_query_ids is missing."""
    ctx = Mock()
    with pytest.raises(ValueError):
        await handler.manage_aws_athena_named_queries(
            ctx, operation='batch-get-named-query', named_query_ids=None
        )


@pytest.mark.asyncio
async def test_create_named_query_success(handler, mock_athena_client):
    """Test successful creation of a named query."""
    handler.athena_client = mock_athena_client
    mock_athena_client.create_named_query.return_value = {'NamedQueryId': 'id1'}

    ctx = Mock()
    response = await handler.manage_aws_athena_named_queries(
        ctx,
        operation='create-named-query',
        name='My Query',
        description='Test query',
        database='db1',
        query_string='SELECT * FROM table',
        client_request_token='token123',
        work_group='primary',
    )

    assert not response.isError
    assert response.named_query_id == 'id1'
    mock_athena_client.create_named_query.assert_called_once_with(
        Name='My Query',
        Description='Test query',
        Database='db1',
        QueryString='SELECT * FROM table',
        ClientRequestToken='token123',
        WorkGroup='primary',
    )


@pytest.mark.asyncio
async def test_create_named_query_missing_parameters(handler):
    """Test that create named query fails when required parameters are missing."""
    ctx = Mock()
    with pytest.raises(ValueError):
        await handler.manage_aws_athena_named_queries(
            ctx, operation='create-named-query', name=None, query_string=None, database=None
        )


@pytest.mark.asyncio
async def test_create_named_query_without_write_permission(read_only_handler):
    """Test that creating a named query fails when write access is disabled."""
    ctx = Mock()
    response = await read_only_handler.manage_aws_athena_named_queries(
        ctx,
        operation='create-named-query',
        name='My Query',
        description='Test query',
        database='db1',
        query_string='SELECT * FROM table',
    )

    assert response.isError
    assert 'not allowed without write access' in response.content[0].text


@pytest.mark.asyncio
async def test_delete_named_query_success(handler, mock_athena_client):
    """Test successful deletion of a named query."""
    handler.athena_client = mock_athena_client

    ctx = Mock()
    response = await handler.manage_aws_athena_named_queries(
        ctx, operation='delete-named-query', named_query_id='id1'
    )

    assert not response.isError
    assert response.named_query_id == 'id1'
    mock_athena_client.delete_named_query.assert_called_once_with(NamedQueryId='id1')


@pytest.mark.asyncio
async def test_delete_named_query_missing_parameters(handler):
    """Test that delete named query fails when named_query_id is missing."""
    ctx = Mock()
    with pytest.raises(ValueError):
        await handler.manage_aws_athena_named_queries(
            ctx, operation='delete-named-query', named_query_id=None
        )


@pytest.mark.asyncio
async def test_delete_named_query_without_write_permission(read_only_handler):
    """Test that deleting a named query fails when write access is disabled."""
    ctx = Mock()
    response = await read_only_handler.manage_aws_athena_named_queries(
        ctx, operation='delete-named-query', named_query_id='id1'
    )

    assert response.isError
    assert 'not allowed without write access' in response.content[0].text


@pytest.mark.asyncio
async def test_get_named_query_success(handler, mock_athena_client):
    """Test successful retrieval of a named query."""
    handler.athena_client = mock_athena_client
    mock_athena_client.get_named_query.return_value = {
        'NamedQuery': {
            'Name': 'My Query',
            'Description': 'Test query',
            'Database': 'db1',
            'QueryString': 'SELECT * FROM table',
            'NamedQueryId': 'id1',
        }
    }

    ctx = Mock()
    response = await handler.manage_aws_athena_named_queries(
        ctx, operation='get-named-query', named_query_id='id1'
    )

    assert not response.isError
    assert response.named_query_id == 'id1'
    assert response.named_query['Name'] == 'My Query'
    mock_athena_client.get_named_query.assert_called_once_with(NamedQueryId='id1')


@pytest.mark.asyncio
async def test_get_named_query_missing_parameters(handler):
    """Test that get named query fails when named_query_id is missing."""
    ctx = Mock()
    with pytest.raises(ValueError):
        await handler.manage_aws_athena_named_queries(
            ctx, operation='get-named-query', named_query_id=None
        )


@pytest.mark.asyncio
async def test_list_named_queries_success(handler, mock_athena_client):
    """Test successful listing of named queries."""
    handler.athena_client = mock_athena_client
    mock_athena_client.list_named_queries.return_value = {
        'NamedQueryIds': ['id1', 'id2', 'id3'],
        'NextToken': 'next-token',
    }

    ctx = Mock()
    response = await handler.manage_aws_athena_named_queries(
        ctx,
        operation='list-named-queries',
        max_results=10,
        next_token='token',
        work_group='primary',
    )

    assert not response.isError
    assert len(response.named_query_ids) == 3
    assert response.count == 3
    assert response.next_token == 'next-token'
    mock_athena_client.list_named_queries.assert_called_once_with(
        MaxResults=10, NextToken='token', WorkGroup='primary'
    )


@pytest.mark.asyncio
async def test_update_named_query_success(handler, mock_athena_client):
    """Test successful update of a named query."""
    handler.athena_client = mock_athena_client

    ctx = Mock()
    response = await handler.manage_aws_athena_named_queries(
        ctx,
        operation='update-named-query',
        named_query_id='id1',
        name='Updated Query',
        description='Updated description',
        database='new_db',
        query_string='SELECT * FROM new_table',
    )

    assert not response.isError
    assert response.named_query_id == 'id1'
    mock_athena_client.update_named_query.assert_called_once_with(
        NamedQueryId='id1',
        Name='Updated Query',
        Description='Updated description',
        Database='new_db',
        QueryString='SELECT * FROM new_table',
    )


@pytest.mark.asyncio
async def test_update_named_query_missing_parameters(handler):
    """Test that update named query fails when named_query_id is missing."""
    ctx = Mock()
    with pytest.raises(ValueError):
        await handler.manage_aws_athena_named_queries(
            ctx, operation='update-named-query', named_query_id=None
        )


@pytest.mark.asyncio
async def test_update_named_query_without_write_permission(read_only_handler):
    """Test that updating a named query fails when write access is disabled."""
    ctx = Mock()
    response = await read_only_handler.manage_aws_athena_named_queries(
        ctx, operation='update-named-query', named_query_id='id1', name='Updated Query'
    )

    assert response.isError
    assert 'not allowed without write access' in response.content[0].text


@pytest.mark.asyncio
async def test_invalid_named_query_operation(handler):
    """Test that running manage_aws_athena_named_queries with an invalid operation results in an error."""
    ctx = Mock()
    response = await handler.manage_aws_athena_named_queries(ctx, operation='invalid-operation')

    assert response.isError
    assert 'Invalid operation' in response.content[0].text


@pytest.mark.asyncio
async def test_named_query_client_error_handling(handler, mock_athena_client):
    """Test error handling when Athena client raises an exception."""
    handler.athena_client = mock_athena_client
    mock_athena_client.get_named_query.side_effect = ClientError(
        {'Error': {'Code': 'InvalidRequestException', 'Message': 'Invalid request'}},
        'GetNamedQuery',
    )

    ctx = Mock()
    response = await handler.manage_aws_athena_named_queries(
        ctx, operation='get-named-query', named_query_id='id1'
    )

    assert response.isError
    assert 'Error in manage_aws_athena_named_queries' in response.content[0].text


# Initialization Tests


@pytest.mark.asyncio
async def test_initialization_parameters(mock_aws_helper):
    """Test initialization of parameters for AthenaQueryHandler object."""
    mcp = Mock()
    handler = AthenaQueryHandler(mcp, allow_write=True, allow_sensitive_data_access=True)

    assert handler.allow_write
    assert handler.allow_sensitive_data_access
    assert handler.mcp == mcp


@pytest.mark.asyncio
async def test_initialization_registers_tools(mock_aws_helper):
    """Test that initialization registers the tools with the MCP server."""
    mcp = Mock()
    AthenaQueryHandler(mcp)

    mcp.tool.assert_any_call(name='manage_aws_athena_query_executions')
    mcp.tool.assert_any_call(name='manage_aws_athena_named_queries')
