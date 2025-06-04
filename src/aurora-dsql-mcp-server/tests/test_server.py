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
"""Tests for the functions in server.py."""

import pytest
from awslabs.aurora_dsql_mcp_server.consts import (
    DSQL_DB_NAME,
    DSQL_DB_PORT,
    DSQL_MCP_SERVER_APPLICATION_NAME,
    ERROR_EMPTY_SQL_LIST_PASSED_TO_TRANSACT,
    ERROR_EMPTY_SQL_PASSED_TO_READONLY_QUERY,
    ERROR_EMPTY_TABLE_NAME_PASSED_TO_SCHEMA,
    ERROR_TRANSACT_INVOKED_IN_READ_ONLY_MODE,
    BEGIN_READ_ONLY_TRANSACTION_SQL,
    COMMIT_TRANSACTION_SQL,
    ROLLBACK_TRANSACTION_SQL,
    BEGIN_TRANSACTION_SQL,
    GET_SCHEMA_SQL,
    INTERNAL_ERROR,
    READ_ONLY_QUERY_WRITE_ERROR,
    ERROR_BEGIN_TRANSACTION
)
from awslabs.aurora_dsql_mcp_server.server import (
    get_connection,
    get_password_token,
    readonly_query,
    get_schema,
    transact,
)
from unittest.mock import AsyncMock, MagicMock, call, patch
from psycopg.errors import ReadOnlySqlTransaction


ctx = AsyncMock()


def create_mock_connection():
    """Create a mock connection with cursor context manager."""
    mock_conn = AsyncMock()
    mock_cursor = AsyncMock()
    mock_cursor.__aenter__ = AsyncMock(return_value=mock_cursor)
    mock_cursor.__aexit__ = AsyncMock(return_value=None)
    mock_cursor.execute = AsyncMock()
    mock_conn.cursor = MagicMock(return_value=mock_cursor)
    mock_conn.closed = False
    return mock_conn, mock_cursor


@pytest.fixture
async def reset_persistent_connection():
    """Reset the persistent connection before and after each test."""
    import awslabs.aurora_dsql_mcp_server.server as server
    server.persistent_connection = None
    yield
    server.persistent_connection = None


async def test_readonly_query_throws_exception_on_empty_input():
    with pytest.raises(ValueError) as excinfo:
        await readonly_query('', ctx)
    assert str(excinfo.value) == ERROR_EMPTY_SQL_PASSED_TO_READONLY_QUERY


@patch('awslabs.aurora_dsql_mcp_server.server.read_only', False)
async def test_transact_throws_exception_on_empty_input():
    with pytest.raises(ValueError) as excinfo:
        await transact([], ctx)
    assert str(excinfo.value) == ERROR_EMPTY_SQL_LIST_PASSED_TO_TRANSACT


@patch('awslabs.aurora_dsql_mcp_server.server.read_only', True)
async def test_transact_throws_exception_when_read_only():
    with pytest.raises(Exception) as excinfo:
        await transact(['select 1'], ctx)
    assert str(excinfo.value) == ERROR_TRANSACT_INVOKED_IN_READ_ONLY_MODE


async def test_get_schema_throws_exception_on_empty_input():
    with pytest.raises(ValueError) as excinfo:
        await get_schema('', ctx)
    assert str(excinfo.value) == ERROR_EMPTY_TABLE_NAME_PASSED_TO_SCHEMA


@patch('awslabs.aurora_dsql_mcp_server.server.database_user', 'admin')
@patch('awslabs.aurora_dsql_mcp_server.server.region', 'us-west-2')
@patch('awslabs.aurora_dsql_mcp_server.server.cluster_endpoint', 'test_ce')
async def test_get_password_token_for_admin_user(mocker):
    mock_client = mocker.patch('awslabs.aurora_dsql_mcp_server.server.dsql_client')
    mock_client.generate_db_connect_admin_auth_token.return_value = 'admin_token'

    result = await get_password_token()

    assert result == 'admin_token'

    mock_client.generate_db_connect_admin_auth_token.assert_called_once_with('test_ce', 'us-west-2')


@patch('awslabs.aurora_dsql_mcp_server.server.database_user', 'nonadmin')
@patch('awslabs.aurora_dsql_mcp_server.server.region', 'us-west-2')
@patch('awslabs.aurora_dsql_mcp_server.server.cluster_endpoint', 'test_ce')
async def test_get_password_token_for_non_admin_user(mocker):
    mock_client = mocker.patch('awslabs.aurora_dsql_mcp_server.server.dsql_client')
    mock_client.generate_db_connect_auth_token.return_value = 'non_admin_token'

    result = await get_password_token()

    assert result == 'non_admin_token'

    mock_client.generate_db_connect_auth_token.assert_called_once_with('test_ce', 'us-west-2')


@patch('awslabs.aurora_dsql_mcp_server.server.database_user', 'admin')
@patch('awslabs.aurora_dsql_mcp_server.server.cluster_endpoint', 'test_ce')
async def test_get_connection(mocker, reset_persistent_connection):
    mock_auth = mocker.patch('awslabs.aurora_dsql_mcp_server.server.get_password_token')
    mock_auth.return_value = 'auth_token'
    mock_connect = mocker.patch('psycopg.AsyncConnection.connect')

    # Create mock connection with working cursor
    mock_conn, mock_cursor = create_mock_connection()
    mock_connect.return_value = mock_conn

    result = await get_connection(ctx)
    assert result is mock_conn

    conn_params = {
        'dbname': DSQL_DB_NAME,
        'user': 'admin',
        'host': 'test_ce',
        'port': DSQL_DB_PORT,
        'password': 'auth_token', # pragma: allowlist secret - test credential for unit tests only
        'application_name': DSQL_MCP_SERVER_APPLICATION_NAME,
        'sslmode': 'require'
    }

    mock_connect.assert_called_once_with(**conn_params, autocommit=True)


@patch('awslabs.aurora_dsql_mcp_server.server.database_user', 'admin')
@patch('awslabs.aurora_dsql_mcp_server.server.cluster_endpoint', 'test_ce')
async def test_get_connection_failure(mocker, reset_persistent_connection):
    mock_auth = mocker.patch('awslabs.aurora_dsql_mcp_server.server.get_password_token')
    mock_auth.return_value = 'auth_token'
    mock_connect = mocker.patch('psycopg.AsyncConnection.connect')
    mock_connect.side_effect = Exception('Connection error')

    with pytest.raises(Exception) as excinfo:
        await get_connection(ctx)
    assert str(excinfo.value) == 'Connection error'


async def test_get_schema(mocker):
    mock_get_connection = mocker.patch(
        'awslabs.aurora_dsql_mcp_server.server.get_connection'
    )
    mock_conn = AsyncMock()
    mock_get_connection.return_value = mock_conn
    mock_execute_query = mocker.patch('awslabs.aurora_dsql_mcp_server.server.execute_query')
    mock_execute_query.return_value = {'col1': 'integer'}

    result = await get_schema('table1', ctx)

    assert result == {'col1': 'integer'}

    mock_execute_query.assert_called_once_with(
        ctx,
        mock_conn,
        GET_SCHEMA_SQL,
        ['table1'],
    )


async def test_get_schema_failure(mocker):
    mock_get_connection = mocker.patch(
        'awslabs.aurora_dsql_mcp_server.server.get_connection'
    )
    mock_conn = AsyncMock()
    mock_get_connection.return_value = mock_conn
    mock_execute_query = mocker.patch('awslabs.aurora_dsql_mcp_server.server.execute_query')
    mock_execute_query.side_effect = Exception('')

    with pytest.raises(Exception) as excinfo:
        await get_schema('table1', ctx)

    mock_execute_query.assert_called_once_with(
        ctx,
        mock_conn,
        GET_SCHEMA_SQL,
        ['table1'],
    )


async def test_readonly_query_commit_on_success(mocker):
    mock_execute_query = mocker.patch('awslabs.aurora_dsql_mcp_server.server.execute_query')
    mock_execute_query.return_value = {'column': 1}

    mock_get_connection = mocker.patch(
        'awslabs.aurora_dsql_mcp_server.server.get_connection'
    )
    mock_conn = AsyncMock()
    mock_get_connection.return_value = mock_conn

    sql = 'select 1'
    result = await readonly_query(sql, ctx)

    assert result == {'column': 1}

    mock_execute_query.assert_has_calls(
        [
            call(ctx, mock_conn, BEGIN_READ_ONLY_TRANSACTION_SQL),
            call(ctx, mock_conn, sql),
            call(ctx, mock_conn, COMMIT_TRANSACTION_SQL),
        ]
    )


async def test_readonly_query_rollback_on_failure(mocker):
    mock_execute_query = mocker.patch('awslabs.aurora_dsql_mcp_server.server.execute_query')
    mock_execute_query.side_effect = ('', Exception(''), '')

    mock_get_connection = mocker.patch(
        'awslabs.aurora_dsql_mcp_server.server.get_connection'
    )
    mock_conn = AsyncMock()
    mock_get_connection.return_value = mock_conn

    sql = 'select 1'
    with pytest.raises(Exception) as excinfo:
        await readonly_query(sql, ctx)

    mock_execute_query.assert_has_calls(
        [
            call(ctx, mock_conn, BEGIN_READ_ONLY_TRANSACTION_SQL),
            call(ctx, mock_conn, sql),
            call(ctx, mock_conn, ROLLBACK_TRANSACTION_SQL),
        ]
    )


async def test_readonly_query_internal_error_on_failed_begin(mocker):
    mock_execute_query = mocker.patch('awslabs.aurora_dsql_mcp_server.server.execute_query')
    mock_execute_query.side_effect = (Exception(''), '', '')

    mock_get_connection = mocker.patch(
        'awslabs.aurora_dsql_mcp_server.server.get_connection'
    )
    mock_conn = AsyncMock()
    mock_get_connection.return_value = mock_conn

    sql = 'select 1'
    with pytest.raises(Exception) as excinfo:
        await readonly_query(sql, ctx)
    assert INTERNAL_ERROR in str(excinfo.value)

    mock_execute_query.assert_called_once_with(ctx, mock_conn, BEGIN_READ_ONLY_TRANSACTION_SQL)


async def test_readonly_query_error_on_write_sql(mocker):
    mock_execute_query = mocker.patch('awslabs.aurora_dsql_mcp_server.server.execute_query')
    mock_execute_query.side_effect = ('', ReadOnlySqlTransaction(''), '')

    mock_get_connection = mocker.patch(
        'awslabs.aurora_dsql_mcp_server.server.get_connection'
    )
    mock_conn = AsyncMock()
    mock_get_connection.return_value = mock_conn

    sql = 'delete from orders'
    with pytest.raises(Exception) as excinfo:
        await readonly_query(sql, ctx)
    assert READ_ONLY_QUERY_WRITE_ERROR in str(excinfo.value)

    mock_execute_query.assert_has_calls(
        [
            call(ctx, mock_conn, BEGIN_READ_ONLY_TRANSACTION_SQL),
            call(ctx, mock_conn, sql),
        ]
    )


@patch('awslabs.aurora_dsql_mcp_server.server.read_only', False)
async def test_transact_commit_on_success(mocker):
    mock_execute_query = mocker.patch('awslabs.aurora_dsql_mcp_server.server.execute_query')
    mock_execute_query.return_value = {'column': 2}

    mock_get_connection = mocker.patch(
        'awslabs.aurora_dsql_mcp_server.server.get_connection'
    )
    mock_conn = AsyncMock()
    mock_get_connection.return_value = mock_conn

    sql1 = 'select 1'
    sql2 = 'select 2'
    sql_list = (sql1, sql2)

    result = await transact(sql_list, ctx)

    assert result == {'column': 2}

    mock_execute_query.assert_has_calls(
        [
            call(ctx, mock_conn, BEGIN_TRANSACTION_SQL),
            call(ctx, mock_conn, sql1),
            call(ctx, mock_conn, sql2),
            call(ctx, mock_conn, COMMIT_TRANSACTION_SQL),
        ]
    )


@patch('awslabs.aurora_dsql_mcp_server.server.read_only', False)
async def test_transact_rollback_on_failure(mocker):
    mock_execute_query = mocker.patch('awslabs.aurora_dsql_mcp_server.server.execute_query')
    mock_execute_query.side_effect = ('', Exception(''), '')

    mock_get_connection = mocker.patch(
        'awslabs.aurora_dsql_mcp_server.server.get_connection'
    )
    mock_conn = AsyncMock()
    mock_get_connection.return_value = mock_conn

    sql1 = 'select 1'
    sql2 = 'select 2'
    sql_list = (sql1, sql2)

    with pytest.raises(Exception) as excinfo:
        await transact(sql_list, ctx)

    mock_execute_query.assert_has_calls(
        [
            call(ctx, mock_conn, BEGIN_TRANSACTION_SQL),
            call(ctx, mock_conn, sql1),
            call(ctx, mock_conn, ROLLBACK_TRANSACTION_SQL),
        ]
    )

@patch('awslabs.aurora_dsql_mcp_server.server.read_only', False)
async def test_transact_error_on_failed_begin(mocker):
    mock_execute_query = mocker.patch('awslabs.aurora_dsql_mcp_server.server.execute_query')
    mock_execute_query.side_effect = (Exception(''), '', '')

    mock_get_connection = mocker.patch(
        'awslabs.aurora_dsql_mcp_server.server.get_connection'
    )
    mock_conn = AsyncMock()
    mock_get_connection.return_value = mock_conn

    sql = 'select 1'
    with pytest.raises(Exception) as excinfo:
        await transact((sql), ctx)
    assert ERROR_BEGIN_TRANSACTION in str(excinfo.value)

    mock_execute_query.assert_called_once_with(ctx, mock_conn, BEGIN_TRANSACTION_SQL)
