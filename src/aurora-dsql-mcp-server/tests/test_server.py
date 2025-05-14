# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance
# with the License. A copy of the License is located at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES
# OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions
# and limitations under the License.
"""Tests for the functions in server.py."""

import pytest
from awslabs.aurora_dsql_mcp_server.consts import (
    DSQL_DB_NAME,
    DSQL_DB_PORT,
    DSQL_MCP_SERVER_APPLICATION_NAME,
    ERROR_EMPTY_SQL_LIST_PASSED_TO_TRANSACT,
    ERROR_EMPTY_SQL_PASSED_TO_EXPLAIN,
    ERROR_EMPTY_SQL_PASSED_TO_QUERY,
    ERROR_EMPTY_TABLE_NAME_PASSED_TO_SCHEMA,
    ERROR_TRANSACT_INVOKED_IN_READ_ONLY_MODE,
)
from awslabs.aurora_dsql_mcp_server.server import (
    create_connection,
    explain,
    get_password_token,
    query,
    schema,
    transact,
)
from unittest.mock import AsyncMock, MagicMock, call, patch


ctx = AsyncMock()


async def test_query_throws_exception_on_empty_input():
    with pytest.raises(ValueError) as excinfo:
        await query('', ctx)
    assert str(excinfo.value) == ERROR_EMPTY_SQL_PASSED_TO_QUERY


async def test_transact_throws_exception_on_empty_input():
    with pytest.raises(ValueError) as excinfo:
        await transact([], ctx)
    assert str(excinfo.value) == ERROR_EMPTY_SQL_LIST_PASSED_TO_TRANSACT


@patch('awslabs.aurora_dsql_mcp_server.server.read_only', True)
async def test_transact_throws_exception_when_read_only():
    with pytest.raises(Exception) as excinfo:
        await transact(['select 1'], ctx)
    assert str(excinfo.value) == ERROR_TRANSACT_INVOKED_IN_READ_ONLY_MODE


async def test_schema_throws_exception_on_empty_input():
    with pytest.raises(ValueError) as excinfo:
        await schema('', ctx)
    assert str(excinfo.value) == ERROR_EMPTY_TABLE_NAME_PASSED_TO_SCHEMA


async def test_explain_throws_exception_on_empty_input():
    with pytest.raises(ValueError) as excinfo:
        await explain('', ctx)
    assert str(excinfo.value) == ERROR_EMPTY_SQL_PASSED_TO_EXPLAIN


@patch('awslabs.aurora_dsql_mcp_server.server.database_user', 'admin')
@patch('awslabs.aurora_dsql_mcp_server.server.region', 'us-west-2')
@patch('awslabs.aurora_dsql_mcp_server.server.cluster_endpoint', 'foo')
async def test_get_password_token_for_admin_user(mocker):
    mock_boto = mocker.patch('boto3.client')
    mock_client = MagicMock()
    mock_boto.return_value = mock_client
    mock_client.generate_db_connect_admin_auth_token.return_value = 'admin_token'

    result = await get_password_token()

    assert result == 'admin_token'

    mock_boto.assert_called_once_with('dsql', region_name='us-west-2')
    mock_client.generate_db_connect_admin_auth_token.assert_called_once_with('foo', 'us-west-2')


@patch('awslabs.aurora_dsql_mcp_server.server.database_user', 'nonadmin')
@patch('awslabs.aurora_dsql_mcp_server.server.region', 'us-west-2')
@patch('awslabs.aurora_dsql_mcp_server.server.cluster_endpoint', 'foo')
async def test_get_password_token_for_non_admin_user(mocker):
    mock_boto = mocker.patch('boto3.client')
    mock_client = MagicMock()
    mock_boto.return_value = mock_client
    mock_client.generate_db_connect_auth_token.return_value = 'non_admin_token'

    result = await get_password_token()

    assert result == 'non_admin_token'

    mock_boto.assert_called_once_with('dsql', region_name='us-west-2')
    mock_client.generate_db_connect_auth_token.assert_called_once_with('foo', 'us-west-2')


@patch('awslabs.aurora_dsql_mcp_server.server.database_user', 'admin')
@patch('awslabs.aurora_dsql_mcp_server.server.cluster_endpoint', 'foo')
async def test_create_connection(mocker):
    mock_auth = mocker.patch('awslabs.aurora_dsql_mcp_server.server.get_password_token')
    mock_auth.return_value = 'auth_token'
    mock_connect = mocker.patch('psycopg.AsyncConnection.connect')
    mock_conn = AsyncMock()
    mock_connect.return_value = mock_conn

    result = await create_connection(ctx)
    assert result == mock_conn

    conn_params = {
        'dbname': DSQL_DB_NAME,
        'user': 'admin',
        'host': 'foo',
        'port': DSQL_DB_PORT,
        'password': 'auth_token', # pragma: allowlist secret - test credential for unit tests only
        'application_name': DSQL_MCP_SERVER_APPLICATION_NAME,
        'sslmode': 'require'
    }

    mock_connect.assert_called_once_with(**conn_params, autocommit=True)


@patch('awslabs.aurora_dsql_mcp_server.server.database_user', 'admin')
@patch('awslabs.aurora_dsql_mcp_server.server.cluster_endpoint', 'foo')
async def test_create_connection_failure(mocker):
    mock_auth = mocker.patch('awslabs.aurora_dsql_mcp_server.server.get_password_token')
    mock_auth.return_value = 'auth_token'
    mock_connect = mocker.patch('psycopg.AsyncConnection.connect')
    mock_connect.side_effect = Exception('Failed to create connection')

    with pytest.raises(Exception) as excinfo:
        await create_connection(ctx)
    assert str(excinfo.value) == 'Failed to create connection'


async def test_schema(mocker):
    mock_execute_query = mocker.patch('awslabs.aurora_dsql_mcp_server.server.execute_query')
    mock_execute_query.return_value = {'col1': 'integer'}

    result = await schema('table1', ctx)

    assert result == {'col1': 'integer'}

    mock_execute_query.assert_called_once_with(
        ctx,
        None,
        'SELECT column_name, data_type FROM information_schema.columns WHERE table_name = %s',
        ['table1'],
    )


async def test_schema_failure(mocker):
    mock_execute_query = mocker.patch('awslabs.aurora_dsql_mcp_server.server.execute_query')
    mock_execute_query.side_effect = Exception('')

    with pytest.raises(Exception) as excinfo:
        await schema('table1', ctx)

    mock_execute_query.assert_called_once_with(
        ctx,
        None,
        'SELECT column_name, data_type FROM information_schema.columns WHERE table_name = %s',
        ['table1'],
    )


async def test_explain(mocker):
    mock_execute_query = mocker.patch('awslabs.aurora_dsql_mcp_server.server.execute_query')
    mock_execute_query.side_effect = Exception('')
    sql = 'select * from table1'

    with pytest.raises(Exception) as excinfo:
        await explain(sql, ctx)

    mock_execute_query.assert_called_once_with(ctx, None, f'EXPLAIN ANALYZE {sql}')


async def test_explain_failure(mocker):
    mock_execute_query = mocker.patch('awslabs.aurora_dsql_mcp_server.server.execute_query')
    mock_execute_query.return_value = 'Explain plan'
    sql = 'select * from table1'

    result = await explain(sql, ctx)

    assert result == 'Explain plan'

    mock_execute_query.assert_called_once_with(ctx, None, f'EXPLAIN ANALYZE {sql}')


async def test_query_commit_on_success(mocker):
    mock_execute_query = mocker.patch('awslabs.aurora_dsql_mcp_server.server.execute_query')
    mock_execute_query.return_value = {'column': 1}

    mock_create_connection = mocker.patch(
        'awslabs.aurora_dsql_mcp_server.server.create_connection'
    )
    mock_conn = AsyncMock()
    mock_create_connection.return_value = mock_conn

    sql = 'select 1'
    result = await query(sql, ctx)

    assert result == {'column': 1}

    mock_execute_query.assert_has_calls(
        [
            call(ctx, mock_conn, 'BEGIN TRANSACTION READ ONLY'),
            call(ctx, mock_conn, sql),
            call(ctx, mock_conn, 'COMMIT'),
        ]
    )


async def test_query_rollback_on_failure(mocker):
    mock_execute_query = mocker.patch('awslabs.aurora_dsql_mcp_server.server.execute_query')
    mock_execute_query.side_effect = ('', Exception(''), '')

    mock_create_connection = mocker.patch(
        'awslabs.aurora_dsql_mcp_server.server.create_connection'
    )
    mock_conn = AsyncMock()
    mock_create_connection.return_value = mock_conn

    sql = 'select 1'
    with pytest.raises(Exception) as excinfo:
        await query(sql, ctx)

    mock_execute_query.assert_has_calls(
        [
            call(ctx, mock_conn, 'BEGIN TRANSACTION READ ONLY'),
            call(ctx, mock_conn, sql),
            call(ctx, mock_conn, 'ROLLBACK'),
        ]
    )


@patch('awslabs.aurora_dsql_mcp_server.server.read_only', False)
async def test_transact_commit_on_success(mocker):
    mock_execute_query = mocker.patch('awslabs.aurora_dsql_mcp_server.server.execute_query')
    mock_execute_query.return_value = {'column': 2}

    mock_create_connection = mocker.patch(
        'awslabs.aurora_dsql_mcp_server.server.create_connection'
    )
    mock_conn = AsyncMock()
    mock_create_connection.return_value = mock_conn

    sql1 = 'select 1'
    sql2 = 'select 2'
    sql_list = (sql1, sql2)

    result = await transact(sql_list, ctx)

    assert result == {'column': 2}

    mock_execute_query.assert_has_calls(
        [
            call(ctx, mock_conn, 'BEGIN'),
            call(ctx, mock_conn, sql1),
            call(ctx, mock_conn, sql2),
            call(ctx, mock_conn, 'COMMIT'),
        ]
    )


@patch('awslabs.aurora_dsql_mcp_server.server.read_only', False)
async def test_transact_rollback_on_failure(mocker):
    mock_execute_query = mocker.patch('awslabs.aurora_dsql_mcp_server.server.execute_query')
    mock_execute_query.side_effect = ('', Exception(''), '')

    mock_create_connection = mocker.patch(
        'awslabs.aurora_dsql_mcp_server.server.create_connection'
    )
    mock_conn = AsyncMock()
    mock_create_connection.return_value = mock_conn

    sql1 = 'select 1'
    sql2 = 'select 2'
    sql_list = (sql1, sql2)

    with pytest.raises(Exception) as excinfo:
        await transact(sql_list, ctx)

    mock_execute_query.assert_has_calls(
        [
            call(ctx, mock_conn, 'BEGIN'),
            call(ctx, mock_conn, sql1),
            call(ctx, mock_conn, 'ROLLBACK'),
        ]
    )
