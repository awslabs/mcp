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
    BEGIN_READ_ONLY_TRANSACTION_SQL,
    COMMIT_TRANSACTION_SQL,
    ROLLBACK_TRANSACTION_SQL,
    BEGIN_TRANSACTION_SQL,
    GET_SCHEMA_SQL,
    GET_QUALIFIED_SCHEMA_SQL,
    INTERNAL_ERROR,
    READ_ONLY_QUERY_WRITE_ERROR,
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


async def test_readonly_query_rollback_error_logging(mocker):
    """Test that rollback errors are logged but don't prevent exception propagation."""
    mock_execute_query = mocker.patch('awslabs.aurora_dsql_mcp_server.server.execute_query')
    mock_execute_query.side_effect = ('', Exception('Query failed'), Exception('Rollback failed'))

    mock_get_connection = mocker.patch(
        'awslabs.aurora_dsql_mcp_server.server.get_connection'
    )
    mock_conn = AsyncMock()
    mock_get_connection.return_value = mock_conn

    sql = 'select 1'
    with pytest.raises(Exception):
        await readonly_query(sql, ctx)

    assert mock_execute_query.call_count == 3


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
