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
    ERROR_WRITE_QUERY_PROHIBITED,
    ERROR_QUERY_INJECTION_RISK,
    BEGIN_READ_ONLY_TRANSACTION_SQL,
    COMMIT_TRANSACTION_SQL,
    ROLLBACK_TRANSACTION_SQL,
    BEGIN_TRANSACTION_SQL,
    GET_SCHEMA_SQL,
    GET_QUALIFIED_SCHEMA_SQL,
    INTERNAL_ERROR,
    READ_ONLY_QUERY_WRITE_ERROR,
    RESET_SESSION_STATE_SQL,
    ERROR_BEGIN_TRANSACTION,
    ERROR_BEGIN_READ_ONLY_TRANSACTION,
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
async def test_transact_uses_read_only_transaction(mocker):
    """Test that transact uses BEGIN READ ONLY TRANSACTION in read-only mode."""
    mock_execute_query = mocker.patch('awslabs.aurora_dsql_mcp_server.server.execute_query')
    mock_execute_query.return_value = {'column': 1}

    mock_get_connection = mocker.patch(
        'awslabs.aurora_dsql_mcp_server.server.get_connection'
    )
    mock_conn = AsyncMock()
    mock_get_connection.return_value = mock_conn

    sql_list = ['SELECT * FROM orders']
    result = await transact(sql_list, ctx)

    assert result == {'column': 1}

    # Verify it uses BEGIN READ ONLY TRANSACTION
    from awslabs.aurora_dsql_mcp_server.consts import BEGIN_READ_ONLY_TRANSACTION_SQL
    mock_execute_query.assert_any_call(ctx, mock_conn, BEGIN_READ_ONLY_TRANSACTION_SQL)


@patch('awslabs.aurora_dsql_mcp_server.server.read_only', True)
async def test_transact_error_on_failed_begin_read_only(mocker):
    """Test that transact handles BEGIN READ ONLY TRANSACTION failures."""
    mock_execute_query = mocker.patch('awslabs.aurora_dsql_mcp_server.server.execute_query')
    mock_execute_query.side_effect = Exception('Connection error')

    mock_get_connection = mocker.patch(
        'awslabs.aurora_dsql_mcp_server.server.get_connection'
    )
    mock_conn = AsyncMock()
    mock_get_connection.return_value = mock_conn

    sql_list = ['SELECT 1']
    with pytest.raises(Exception) as excinfo:
        await transact(sql_list, ctx)

    from awslabs.aurora_dsql_mcp_server.consts import ERROR_BEGIN_READ_ONLY_TRANSACTION
    assert ERROR_BEGIN_READ_ONLY_TRANSACTION in str(excinfo.value)

    from awslabs.aurora_dsql_mcp_server.consts import BEGIN_READ_ONLY_TRANSACTION_SQL
    mock_execute_query.assert_called_once_with(ctx, mock_conn, BEGIN_READ_ONLY_TRANSACTION_SQL)


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


async def test_get_schema_with_schema_qualified_name(mocker):
    mock_get_connection = mocker.patch(
        'awslabs.aurora_dsql_mcp_server.server.get_connection'
    )
    mock_conn = AsyncMock()
    mock_get_connection.return_value = mock_conn
    mock_execute_query = mocker.patch('awslabs.aurora_dsql_mcp_server.server.execute_query')
    mock_execute_query.return_value = {'col1': 'integer'}

    result = await get_schema('data.Associate', ctx)

    assert result == {'col1': 'integer'}

    mock_execute_query.assert_called_once_with(
        ctx,
        mock_conn,
        GET_QUALIFIED_SCHEMA_SQL,
        ['data', 'Associate'],
    )


async def test_get_schema_without_schema_uses_table_name_only(mocker):
    mock_get_connection = mocker.patch(
        'awslabs.aurora_dsql_mcp_server.server.get_connection'
    )
    mock_conn = AsyncMock()
    mock_get_connection.return_value = mock_conn
    mock_execute_query = mocker.patch('awslabs.aurora_dsql_mcp_server.server.execute_query')
    mock_execute_query.return_value = {'col1': 'integer'}

    result = await get_schema('Associate', ctx)

    assert result == {'col1': 'integer'}

    mock_execute_query.assert_called_once_with(
        ctx,
        mock_conn,
        GET_SCHEMA_SQL,
        ['Associate'],
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
            call(ctx, mock_conn, sql, None),
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
            call(ctx, mock_conn, sql, None),
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
    # Now the readonly enforcement catches DELETE before it gets to the database
    from awslabs.aurora_dsql_mcp_server.consts import ERROR_WRITE_QUERY_PROHIBITED
    assert ERROR_WRITE_QUERY_PROHIBITED in str(excinfo.value)

    # The validation catches the issue before any database operations
    mock_get_connection.assert_not_called()
    mock_execute_query.assert_not_called()


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
            call(ctx, mock_conn, sql1, None),
            call(ctx, mock_conn, sql2, None),
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
            call(ctx, mock_conn, sql1, None),
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


@patch('awslabs.aurora_dsql_mcp_server.server.cluster_endpoint', 'test_ce')
async def test_readonly_query_rollback_error_logging(mocker):
    """Test that rollback errors are logged but don't prevent exception propagation."""
    mock_execute_query = mocker.patch('awslabs.aurora_dsql_mcp_server.server.execute_query')
    # BEGIN, query (fails), ROLLBACK (fails), then the session-state scrub
    # statements (which also fail). All post-query steps are best effort and
    # must not suppress the original query exception, and one failing RESET
    # must not skip the others.
    mock_execute_query.side_effect = (
        '',
        Exception('Query failed'),
        Exception('Rollback failed'),
    ) + tuple(Exception('Reset failed') for _ in RESET_SESSION_STATE_SQL)

    mock_get_connection = mocker.patch(
        'awslabs.aurora_dsql_mcp_server.server.get_connection'
    )
    mock_conn = AsyncMock()
    mock_get_connection.return_value = mock_conn

    sql = 'select 1'
    with pytest.raises(Exception):
        await readonly_query(sql, ctx)

    # BEGIN + query + ROLLBACK + one call per reset statement
    assert mock_execute_query.call_count == 3 + len(RESET_SESSION_STATE_SQL)
    # Every reset statement is attempted even though each raises.
    reset_calls = [call(ctx, mock_conn, stmt) for stmt in RESET_SESSION_STATE_SQL]
    assert mock_execute_query.call_args_list[-len(RESET_SESSION_STATE_SQL):] == reset_calls


@patch('awslabs.aurora_dsql_mcp_server.server.read_only', False)
async def test_transact_rollback_error_logging(mocker):
    """Test that rollback errors in transact are logged."""
    mock_execute_query = mocker.patch('awslabs.aurora_dsql_mcp_server.server.execute_query')
    mock_execute_query.side_effect = ('', Exception('Query failed'), Exception('Rollback failed'))

    mock_get_connection = mocker.patch(
        'awslabs.aurora_dsql_mcp_server.server.get_connection'
    )
    mock_conn = AsyncMock()
    mock_get_connection.return_value = mock_conn

    sql_list = ['insert into test values (1)']
    with pytest.raises(Exception):
        await transact(sql_list, ctx)

    assert mock_execute_query.call_count == 3


@patch('awslabs.aurora_dsql_mcp_server.server.cluster_endpoint', 'test_ce')
async def test_readonly_query_resets_session_state_on_success(mocker):
    """readonly_query must scrub session/GUC state after a successful query.

    A SET / set_config() with session scope survives COMMIT and would
    otherwise persist on the pooled connection. The session-state scrub after
    the query prevents that state leak.
    """
    mock_execute_query = mocker.patch('awslabs.aurora_dsql_mcp_server.server.execute_query')
    mock_execute_query.return_value = [{'column': 1}]

    mock_get_connection = mocker.patch(
        'awslabs.aurora_dsql_mcp_server.server.get_connection'
    )
    mock_conn = AsyncMock()
    mock_get_connection.return_value = mock_conn

    sql = 'select 1'
    result = await readonly_query(sql, ctx)

    assert result == [{'column': 1}]
    # The scrub statements run last, after BEGIN / query / COMMIT / ROLLBACK.
    reset_calls = [call(ctx, mock_conn, stmt) for stmt in RESET_SESSION_STATE_SQL]
    mock_execute_query.assert_has_calls(
        [
            call(ctx, mock_conn, BEGIN_READ_ONLY_TRANSACTION_SQL),
            call(ctx, mock_conn, sql, None),
            call(ctx, mock_conn, COMMIT_TRANSACTION_SQL),
            call(ctx, mock_conn, ROLLBACK_TRANSACTION_SQL),
            *reset_calls,
        ]
    )
    assert mock_execute_query.call_args_list[-len(RESET_SESSION_STATE_SQL):] == reset_calls


@patch('awslabs.aurora_dsql_mcp_server.server.cluster_endpoint', 'test_ce')
async def test_readonly_query_reset_failure_does_not_mask_result(mocker):
    """A failing session-state scrub is logged but must not fail a good query."""
    mock_execute_query = mocker.patch('awslabs.aurora_dsql_mcp_server.server.execute_query')
    # BEGIN, query, COMMIT, ROLLBACK all succeed; every reset statement raises.
    mock_execute_query.side_effect = (
        '',
        [{'column': 1}],
        '',
        '',
    ) + tuple(Exception('Reset failed') for _ in RESET_SESSION_STATE_SQL)

    mock_get_connection = mocker.patch(
        'awslabs.aurora_dsql_mcp_server.server.get_connection'
    )
    mock_conn = AsyncMock()
    mock_get_connection.return_value = mock_conn

    # readonly_query returns the query rows immediately on success (before the
    # finally block runs), so a scrub failure cannot affect the result.
    result = await readonly_query('select 1', ctx)
    assert result == [{'column': 1}]
    # The scrub was actually attempted (guards against this test passing even if
    # reset_session_state were removed): all reset statements were issued.
    issued = [c.args[2] for c in mock_execute_query.call_args_list]
    for stmt in RESET_SESSION_STATE_SQL:
        assert stmt in issued


@patch('awslabs.aurora_dsql_mcp_server.server.cluster_endpoint', 'test_ce')
@patch('awslabs.aurora_dsql_mcp_server.server.read_only', True)
async def test_transact_resets_session_state_in_read_only_mode(mocker):
    """transact in read-only mode must scrub session state after execution."""
    mock_execute_query = mocker.patch('awslabs.aurora_dsql_mcp_server.server.execute_query')
    mock_execute_query.return_value = [{'count': 1}]

    mock_get_connection = mocker.patch(
        'awslabs.aurora_dsql_mcp_server.server.get_connection'
    )
    mock_conn = AsyncMock()
    mock_get_connection.return_value = mock_conn

    await transact(['SELECT 1'], ctx)

    reset_calls = [call(ctx, mock_conn, stmt) for stmt in RESET_SESSION_STATE_SQL]
    assert mock_execute_query.call_args_list[-len(RESET_SESSION_STATE_SQL):] == reset_calls


@patch('awslabs.aurora_dsql_mcp_server.server.cluster_endpoint', 'test_ce')
@patch('awslabs.aurora_dsql_mcp_server.server.read_only', False)
async def test_transact_does_not_reset_session_state_in_read_write_mode(mocker):
    """transact in read-write mode must NOT issue RESET ALL.

    In write mode the caller intentionally controls session state (e.g. SET
    statements they issued on purpose), so the server must not scrub it.
    """
    mock_execute_query = mocker.patch('awslabs.aurora_dsql_mcp_server.server.execute_query')
    mock_execute_query.return_value = [{'count': 1}]

    mock_get_connection = mocker.patch(
        'awslabs.aurora_dsql_mcp_server.server.get_connection'
    )
    mock_conn = AsyncMock()
    mock_get_connection.return_value = mock_conn

    await transact(['INSERT INTO t VALUES (1)'], ctx)

    issued = [c.args[2] for c in mock_execute_query.call_args_list]
    for stmt in RESET_SESSION_STATE_SQL:
        assert stmt not in issued


# --------------------------------------------------------------------------
# Tool-level rejection of session mutation (the PR's headline fix, exercised
# through readonly_query / transact rather than the detector directly).
# --------------------------------------------------------------------------


@patch('awslabs.aurora_dsql_mcp_server.server.cluster_endpoint', 'test_ce')
async def test_readonly_query_rejects_session_mutation_at_tool_level(mocker):
    """readonly_query must reject session-mutating SQL before touching the DB."""
    mock_execute_query = mocker.patch('awslabs.aurora_dsql_mcp_server.server.execute_query')
    mock_get_connection = mocker.patch('awslabs.aurora_dsql_mcp_server.server.get_connection')

    session_mutations = [
        'SET search_path = evil',
        'SET ROLE admin',
        "SELECT set_config('search_path', 'pg_temp', false)",
        'RESET ALL',
        "SELECT E'\\'', set_config('search_path', 'pg_temp', false)",
    ]
    for sql in session_mutations:
        with pytest.raises(Exception) as excinfo:
            await readonly_query(sql, ctx)
        assert ERROR_WRITE_QUERY_PROHIBITED in str(excinfo.value), sql
    # Validation happens before any DB work.
    mock_execute_query.assert_not_called()
    mock_get_connection.assert_not_called()


@patch('awslabs.aurora_dsql_mcp_server.server.cluster_endpoint', 'test_ce')
@patch('awslabs.aurora_dsql_mcp_server.server.read_only', True)
async def test_transact_rejects_session_mutation_in_read_only_mode(mocker):
    """Read-only transact must reject session-mutating SQL before executing."""
    mock_execute_query = mocker.patch('awslabs.aurora_dsql_mcp_server.server.execute_query')
    mock_get_connection = mocker.patch('awslabs.aurora_dsql_mcp_server.server.get_connection')

    for sql in ['SET search_path = evil', "SELECT set_config('timezone', 'UTC', true)"]:
        with pytest.raises(Exception) as excinfo:
            await transact([sql], ctx)
        assert ERROR_WRITE_QUERY_PROHIBITED in str(excinfo.value), sql
    mock_execute_query.assert_not_called()
    mock_get_connection.assert_not_called()


@patch('awslabs.aurora_dsql_mcp_server.server.cluster_endpoint', 'test_ce')
@patch('awslabs.aurora_dsql_mcp_server.server.read_only', False)
async def test_transact_blocks_mode_independent_risks_in_write_mode(mocker):
    """Write-mode transact still blocks GUC / COPY PROGRAM / dangerous functions.

    These are the mode-independent checks: in write mode generic SET and
    mutating keywords are allowed, but security GUCs, server-side command
    execution, and high-blast-radius functions must still be rejected.
    """
    mock_execute_query = mocker.patch('awslabs.aurora_dsql_mcp_server.server.execute_query')
    mock_get_connection = mocker.patch('awslabs.aurora_dsql_mcp_server.server.get_connection')

    mode_independent = [
        'SET row_security = off',
        "SELECT set_config('session_replication_role', 'replica', false)",
        "COPY t TO PROGRAM 'curl evil'",
        'SELECT pg_terminate_backend(1)',
        "SELECT dblink_connect('host=169.254.169.254')",
    ]
    for sql in mode_independent:
        with pytest.raises(Exception) as excinfo:
            await transact([sql], ctx)
        assert ERROR_QUERY_INJECTION_RISK in str(excinfo.value), sql
    mock_execute_query.assert_not_called()
    mock_get_connection.assert_not_called()


@patch('awslabs.aurora_dsql_mcp_server.server.cluster_endpoint', 'test_ce')
@patch('awslabs.aurora_dsql_mcp_server.server.read_only', False)
async def test_transact_allows_benign_session_mutation_in_write_mode(mocker):
    """Write-mode transact permits an ordinary SET the caller issued on purpose."""
    mock_execute_query = mocker.patch('awslabs.aurora_dsql_mcp_server.server.execute_query')
    mock_execute_query.return_value = [{'ok': 1}]
    mock_get_connection = mocker.patch('awslabs.aurora_dsql_mcp_server.server.get_connection')
    mock_get_connection.return_value = AsyncMock()

    # Should not raise; the SET reaches execute_query.
    await transact(['SET search_path = myschema'], ctx)
    issued = [c.args[2] for c in mock_execute_query.call_args_list]
    assert 'SET search_path = myschema' in issued


@patch('awslabs.aurora_dsql_mcp_server.server.cluster_endpoint', 'test_ce')
@patch('awslabs.aurora_dsql_mcp_server.server.read_only', True)
async def test_transact_resets_session_state_on_failure(mocker):
    """Read-only transact must still scrub session state when a query raises."""
    mock_execute_query = mocker.patch('awslabs.aurora_dsql_mcp_server.server.execute_query')
    # BEGIN ok, query raises, ROLLBACK ok, then the reset statements.
    mock_execute_query.side_effect = (
        '',
        Exception('boom'),
        '',
    ) + tuple('' for _ in RESET_SESSION_STATE_SQL)
    mock_conn = AsyncMock()
    mocker.patch('awslabs.aurora_dsql_mcp_server.server.get_connection', return_value=mock_conn)

    with pytest.raises(Exception):
        await transact(['SELECT 1'], ctx)

    issued = [c.args[2] for c in mock_execute_query.call_args_list]
    for stmt in RESET_SESSION_STATE_SQL:
        assert stmt in issued


@patch('awslabs.aurora_dsql_mcp_server.server.cluster_endpoint', 'test_ce')
@patch('awslabs.aurora_dsql_mcp_server.server.read_only', True)
async def test_transact_rolls_back_on_readonly_violation(mocker):
    """The ReadOnlySqlTransaction branch must ROLLBACK before the reset scrub.

    Without the ROLLBACK the scrub would run inside an aborted transaction where
    Postgres ignores every command, silently no-opping the state cleanup.
    """
    mock_execute_query = mocker.patch('awslabs.aurora_dsql_mcp_server.server.execute_query')
    # BEGIN ok, query raises ReadOnlySqlTransaction, then ROLLBACK + resets.
    mock_execute_query.side_effect = (
        '',
        ReadOnlySqlTransaction('cannot execute in a read-only transaction'),
        '',
    ) + tuple('' for _ in RESET_SESSION_STATE_SQL)
    mock_conn = AsyncMock()
    mocker.patch('awslabs.aurora_dsql_mcp_server.server.get_connection', return_value=mock_conn)

    # A query the detector allows (plain SELECT) that the DB nonetheless rejects
    # as a read-only violation — the scenario the ROLLBACK branch exists for.
    with pytest.raises(Exception) as excinfo:
        await transact(['SELECT * FROM t'], ctx)
    assert READ_ONLY_QUERY_WRITE_ERROR in str(excinfo.value)

    issued = [c.args[2] for c in mock_execute_query.call_args_list]
    assert ROLLBACK_TRANSACTION_SQL in issued
    # ROLLBACK precedes the scrub statements.
    assert issued.index(ROLLBACK_TRANSACTION_SQL) < issued.index(RESET_SESSION_STATE_SQL[0])


@patch('awslabs.aurora_dsql_mcp_server.server.cluster_endpoint', 'test_ce')
async def test_reset_failure_discards_pooled_connection(mocker, reset_persistent_connection):
    """A failed session scrub must discard the pooled connection (self-heal).

    Otherwise the mutated connection stays pooled and the scrub silently
    no-ops for every later request on it.
    """
    import awslabs.aurora_dsql_mcp_server.server as server

    mock_conn = AsyncMock()
    mock_conn.close = AsyncMock()
    server.persistent_connection = mock_conn

    # Every reset statement fails.
    mock_execute_query = mocker.patch(
        'awslabs.aurora_dsql_mcp_server.server.execute_query',
        side_effect=Exception('reset refused'),
    )

    await server.reset_session_state(ctx, mock_conn)

    # All reset statements were attempted despite each failing...
    assert mock_execute_query.call_count == len(RESET_SESSION_STATE_SQL)
    # ...and the broken connection was discarded so the next request reconnects.
    mock_conn.close.assert_awaited_once()
    assert server.persistent_connection is None


@patch('awslabs.aurora_dsql_mcp_server.server.cluster_endpoint', 'test_ce')
async def test_reset_success_keeps_pooled_connection(mocker, reset_persistent_connection):
    """A successful scrub must NOT discard the pooled connection."""
    import awslabs.aurora_dsql_mcp_server.server as server

    mock_conn = AsyncMock()
    mock_conn.close = AsyncMock()
    server.persistent_connection = mock_conn

    mocker.patch('awslabs.aurora_dsql_mcp_server.server.execute_query', return_value=[])

    await server.reset_session_state(ctx, mock_conn)

    mock_conn.close.assert_not_awaited()
    assert server.persistent_connection is mock_conn


async def test_execute_query_connection_retry(mocker):
    """Test that execute_query retries on connection errors."""
    from awslabs.aurora_dsql_mcp_server.server import execute_query
    from psycopg.errors import OperationalError

    # Mock persistent_connection
    mocker.patch('awslabs.aurora_dsql_mcp_server.server.persistent_connection', None)

    mock_get_connection = mocker.patch(
        'awslabs.aurora_dsql_mcp_server.server.get_connection'
    )

    # First connection fails with OperationalError
    mock_conn1 = AsyncMock()
    mock_cursor1 = AsyncMock()
    mock_cursor1.__aenter__ = AsyncMock(side_effect=OperationalError('Connection lost'))
    mock_cursor1.__aexit__ = AsyncMock(return_value=None)
    mock_conn1.cursor = MagicMock(return_value=mock_cursor1)
    mock_conn1.close = AsyncMock()

    # Second connection succeeds
    mock_conn2 = AsyncMock()
    mock_cursor2 = AsyncMock()
    mock_cursor2.__aenter__ = AsyncMock(return_value=mock_cursor2)
    mock_cursor2.__aexit__ = AsyncMock(return_value=None)
    mock_cursor2.execute = AsyncMock()
    mock_cursor2.rownumber = 1
    mock_cursor2.fetchall = AsyncMock(return_value=[{'result': 1}])
    mock_conn2.cursor = MagicMock(return_value=mock_cursor2)

    mock_get_connection.side_effect = [mock_conn1, mock_conn2]

    result = await execute_query(ctx, None, 'SELECT 1')

    assert result == [{'result': 1}]
    assert mock_get_connection.call_count == 2


async def test_execute_query_returns_empty_on_no_rows(mocker):
    """Test that execute_query returns empty list when rownumber is None."""
    from awslabs.aurora_dsql_mcp_server.server import execute_query

    mock_get_connection = mocker.patch(
        'awslabs.aurora_dsql_mcp_server.server.get_connection'
    )

    mock_conn = AsyncMock()
    mock_cursor = AsyncMock()
    mock_cursor.__aenter__ = AsyncMock(return_value=mock_cursor)
    mock_cursor.__aexit__ = AsyncMock(return_value=None)
    mock_cursor.execute = AsyncMock()
    mock_cursor.rownumber = None
    mock_conn.cursor = MagicMock(return_value=mock_cursor)

    mock_get_connection.return_value = mock_conn

    result = await execute_query(ctx, None, 'SELECT 1 WHERE FALSE')

    assert result == []


# Note: Lines 172-176 (transaction bypass warning) are difficult to test in isolation
# because the SQL injection check (lines 161-167) catches the same patterns first.
# This is acceptable as both checks provide defense-in-depth security.

async def test_execute_query_with_interface_error_retry(mocker):
    """Test that execute_query retries on InterfaceError."""
    from awslabs.aurora_dsql_mcp_server.server import execute_query
    from psycopg.errors import InterfaceError

    mocker.patch('awslabs.aurora_dsql_mcp_server.server.persistent_connection', None)

    mock_get_connection = mocker.patch(
        'awslabs.aurora_dsql_mcp_server.server.get_connection'
    )

    # First connection fails with InterfaceError
    mock_conn1 = AsyncMock()
    mock_cursor1 = AsyncMock()
    mock_cursor1.__aenter__ = AsyncMock(side_effect=InterfaceError('Interface error'))
    mock_cursor1.__aexit__ = AsyncMock(return_value=None)
    mock_conn1.cursor = MagicMock(return_value=mock_cursor1)
    mock_conn1.close = AsyncMock()

    # Second connection succeeds
    mock_conn2 = AsyncMock()
    mock_cursor2 = AsyncMock()
    mock_cursor2.__aenter__ = AsyncMock(return_value=mock_cursor2)
    mock_cursor2.__aexit__ = AsyncMock(return_value=None)
    mock_cursor2.execute = AsyncMock()
    mock_cursor2.rownumber = 1
    mock_cursor2.fetchall = AsyncMock(return_value=[{'result': 1}])
    mock_conn2.cursor = MagicMock(return_value=mock_cursor2)

    mock_get_connection.side_effect = [mock_conn1, mock_conn2]

    result = await execute_query(ctx, None, 'SELECT 1')

    assert result == [{'result': 1}]
    assert mock_get_connection.call_count == 2


async def test_execute_query_retry_returns_empty(mocker):
    """Test that execute_query returns empty list after retry when rownumber is None."""
    from awslabs.aurora_dsql_mcp_server.server import execute_query
    from psycopg.errors import OperationalError

    mocker.patch('awslabs.aurora_dsql_mcp_server.server.persistent_connection', None)

    mock_get_connection = mocker.patch(
        'awslabs.aurora_dsql_mcp_server.server.get_connection'
    )

    # First connection fails
    mock_conn1 = AsyncMock()
    mock_cursor1 = AsyncMock()
    mock_cursor1.__aenter__ = AsyncMock(side_effect=OperationalError('Connection lost'))
    mock_cursor1.__aexit__ = AsyncMock(return_value=None)
    mock_conn1.cursor = MagicMock(return_value=mock_cursor1)
    mock_conn1.close = AsyncMock()

    # Second connection succeeds but returns no rows
    mock_conn2 = AsyncMock()
    mock_cursor2 = AsyncMock()
    mock_cursor2.__aenter__ = AsyncMock(return_value=mock_cursor2)
    mock_cursor2.__aexit__ = AsyncMock(return_value=None)
    mock_cursor2.execute = AsyncMock()
    mock_cursor2.rownumber = None
    mock_conn2.cursor = MagicMock(return_value=mock_cursor2)

    mock_get_connection.side_effect = [mock_conn1, mock_conn2]

    result = await execute_query(ctx, None, 'SELECT 1 WHERE FALSE')

    assert result == []
    assert mock_get_connection.call_count == 2


# --------------------------------------------------------------------------
# Parameterized query support
# --------------------------------------------------------------------------


class TestReadonlyQueryParams:
    """Tests for the optional params argument on readonly_query."""

    @pytest.mark.asyncio
    async def test_params_passed_to_execute_query(self, mocker):
        """When params is provided, it reaches execute_query."""
        mock_eq = mocker.patch(
            'awslabs.aurora_dsql_mcp_server.server.execute_query',
            return_value=[{'id': 1}],
        )
        mocker.patch(
            'awslabs.aurora_dsql_mcp_server.server.get_connection',
            return_value=AsyncMock(),
        )

        sql = 'SELECT * FROM t WHERE tenant_id = %s'
        result = await readonly_query(sql, ctx, params=['acme'])

        assert result == [{'id': 1}]
        # The query call (second) should carry the params list.
        query_call = mock_eq.call_args_list[1]
        assert query_call == call(ctx, mocker.ANY, sql, ['acme'])

    @pytest.mark.asyncio
    async def test_no_params_backwards_compatible(self, mocker):
        """Calling without params still works (None passed through)."""
        mock_eq = mocker.patch(
            'awslabs.aurora_dsql_mcp_server.server.execute_query',
            return_value=[],
        )
        mocker.patch(
            'awslabs.aurora_dsql_mcp_server.server.get_connection',
            return_value=AsyncMock(),
        )

        result = await readonly_query('SELECT 1', ctx)

        assert result == []
        query_call = mock_eq.call_args_list[1]
        assert query_call == call(ctx, mocker.ANY, 'SELECT 1', None)

    @pytest.mark.asyncio
    async def test_params_none_backwards_compatible(self, mocker):
        """Explicit params=None is the same as omitting it."""
        mock_eq = mocker.patch(
            'awslabs.aurora_dsql_mcp_server.server.execute_query',
            return_value=[],
        )
        mocker.patch(
            'awslabs.aurora_dsql_mcp_server.server.get_connection',
            return_value=AsyncMock(),
        )

        result = await readonly_query('SELECT 1', ctx, params=None)

        assert result == []
        query_call = mock_eq.call_args_list[1]
        assert query_call == call(ctx, mocker.ANY, 'SELECT 1', None)

    @pytest.mark.asyncio
    async def test_params_with_multiple_placeholders(self, mocker):
        mock_eq = mocker.patch(
            'awslabs.aurora_dsql_mcp_server.server.execute_query',
            return_value=[{'a': 1, 'b': 2}],
        )
        mocker.patch(
            'awslabs.aurora_dsql_mcp_server.server.get_connection',
            return_value=AsyncMock(),
        )

        sql = 'SELECT * FROM t WHERE a = %s AND b = %s'
        result = await readonly_query(sql, ctx, params=[1, 'two'])

        query_call = mock_eq.call_args_list[1]
        assert query_call == call(ctx, mocker.ANY, sql, [1, 'two'])


@patch('awslabs.aurora_dsql_mcp_server.server.read_only', False)
class TestTransactParamsList:
    """Tests for the optional params_list argument on transact."""

    @pytest.mark.asyncio
    async def test_params_list_passed_per_statement(self, mocker):
        mock_eq = mocker.patch(
            'awslabs.aurora_dsql_mcp_server.server.execute_query',
            return_value=[],
        )
        mocker.patch(
            'awslabs.aurora_dsql_mcp_server.server.get_connection',
            return_value=AsyncMock(),
        )

        sql_list = [
            "INSERT INTO t (id, name) VALUES (%s, %s)",
            "INSERT INTO t (id, name) VALUES (%s, %s)",
        ]
        params_list = [['id1', 'Widget'], ['id2', 'Gadget']]

        await transact(sql_list, ctx, params_list=params_list)

        # Calls: BEGIN, stmt1, stmt2, COMMIT
        stmt1_call = mock_eq.call_args_list[1]
        stmt2_call = mock_eq.call_args_list[2]
        assert stmt1_call == call(ctx, mocker.ANY, sql_list[0], ['id1', 'Widget'])
        assert stmt2_call == call(ctx, mocker.ANY, sql_list[1], ['id2', 'Gadget'])

    @pytest.mark.asyncio
    async def test_params_list_none_entries(self, mocker):
        """A None entry in params_list means no params for that statement."""
        mock_eq = mocker.patch(
            'awslabs.aurora_dsql_mcp_server.server.execute_query',
            return_value=[],
        )
        mocker.patch(
            'awslabs.aurora_dsql_mcp_server.server.get_connection',
            return_value=AsyncMock(),
        )

        sql_list = [
            "CREATE TABLE t (id TEXT PRIMARY KEY)",
            "INSERT INTO t (id) VALUES (%s)",
        ]
        params_list = [None, ['abc']]

        await transact(sql_list, ctx, params_list=params_list)

        stmt1_call = mock_eq.call_args_list[1]
        stmt2_call = mock_eq.call_args_list[2]
        assert stmt1_call == call(ctx, mocker.ANY, sql_list[0], None)
        assert stmt2_call == call(ctx, mocker.ANY, sql_list[1], ['abc'])

    @pytest.mark.asyncio
    async def test_no_params_list_backwards_compatible(self, mocker):
        """Omitting params_list passes None for every statement."""
        mock_eq = mocker.patch(
            'awslabs.aurora_dsql_mcp_server.server.execute_query',
            return_value=[],
        )
        mocker.patch(
            'awslabs.aurora_dsql_mcp_server.server.get_connection',
            return_value=AsyncMock(),
        )

        await transact(['SELECT 1', 'SELECT 2'], ctx)

        stmt1_call = mock_eq.call_args_list[1]
        stmt2_call = mock_eq.call_args_list[2]
        assert stmt1_call == call(ctx, mocker.ANY, 'SELECT 1', None)
        assert stmt2_call == call(ctx, mocker.ANY, 'SELECT 2', None)

    @pytest.mark.asyncio
    async def test_params_list_length_mismatch_raises(self, mocker):
        """params_list must be same length as sql_list."""
        with pytest.raises(ValueError, match='params_list length'):
            await transact(
                ['SELECT 1', 'SELECT 2'],
                ctx,
                params_list=[['a']],
            )

    @pytest.mark.asyncio
    async def test_params_list_none_backwards_compatible(self, mocker):
        """Explicit params_list=None is the same as omitting it."""
        mock_eq = mocker.patch(
            'awslabs.aurora_dsql_mcp_server.server.execute_query',
            return_value=[],
        )
        mocker.patch(
            'awslabs.aurora_dsql_mcp_server.server.get_connection',
            return_value=AsyncMock(),
        )

        await transact(['SELECT 1'], ctx, params_list=None)

        stmt_call = mock_eq.call_args_list[1]
        assert stmt_call == call(ctx, mocker.ANY, 'SELECT 1', None)
