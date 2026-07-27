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

"""Extended coverage tests for PymssqlPoolConnection.

Covers: _get_connection broken-connection replacement, check_expiry rotation,
execute_query typed value mapping, parameter binding paths, and
_get_credentials_from_secret AWS Secrets Manager interactions.
"""

import asyncio
import json
import pytest
from awslabs.mssql_mcp_server.connection.pymssql_pool_connection import PymssqlPoolConnection
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch


def make_pool_conn(**kwargs):
    """Create a PymssqlPoolConnection configured for testing."""
    defaults = {
        'host': 'localhost',
        'port': 1433,
        'database': 'testdb',
        'readonly': True,
        'secret_arn': 'arn:aws:secretsmanager:us-east-1:123:secret:test',  # pragma: allowlist secret
        'region': 'us-east-1',
        'is_test': True,
    }
    defaults.update(kwargs)
    return PymssqlPoolConnection(**defaults)


# ─── initialize_pool error paths ─────────────────────────────────────────────


@pytest.mark.asyncio
async def test_initialize_pool_raises_when_all_connections_fail():
    """If every pre-fill attempt fails, initialize_pool raises and resets pool to None."""
    conn = make_pool_conn(min_size=2)
    with patch.object(conn, '_create_raw_connection', side_effect=Exception('network down')):
        with pytest.raises(Exception, match='network down'):
            await conn.initialize_pool()
    assert conn._pool is None


# ─── _get_connection broken-connection replacement ───────────────────────────


@pytest.mark.asyncio
async def test_get_connection_replaces_broken(mocker):
    """When the yielded connection raises, a fresh connection is put back in the pool."""
    conn = make_pool_conn()

    broken = MagicMock()
    replacement = MagicMock()

    conn._pool = asyncio.Queue(maxsize=10)
    conn._pool.put_nowait(broken)

    # Bypass expiry so the reader lock check passes
    mocker.patch.object(conn, 'check_expiry', new=AsyncMock())
    mocker.patch.object(
        conn,
        '_get_credentials_from_secret',
        return_value=('u', 'p'),
    )
    mocker.patch.object(conn, '_create_raw_connection', return_value=replacement)

    with pytest.raises(RuntimeError, match='boom'):
        async with conn._get_connection() as c:
            assert c is broken
            raise RuntimeError('boom')

    # Broken was closed, replacement was put back
    broken.close.assert_called_once()
    assert conn._pool.qsize() == 1
    assert await conn._pool.get() is replacement


@pytest.mark.asyncio
async def test_get_connection_pool_none_raises(mocker):
    """If pool was never initialized, _get_connection raises ValueError."""
    conn = make_pool_conn()
    conn._pool = None
    mocker.patch.object(conn, 'check_expiry', new=AsyncMock())

    with pytest.raises(ValueError, match='Failed to initialize'):
        async with conn._get_connection():
            pass


@pytest.mark.asyncio
async def test_get_connection_replacement_also_fails(mocker):
    """If replacement connection can't be created, the original error still propagates."""
    conn = make_pool_conn()

    broken = MagicMock()
    conn._pool = asyncio.Queue(maxsize=10)
    conn._pool.put_nowait(broken)

    mocker.patch.object(conn, 'check_expiry', new=AsyncMock())
    mocker.patch.object(
        conn,
        '_get_credentials_from_secret',
        side_effect=Exception('secrets down'),
    )

    with pytest.raises(RuntimeError, match='work failed'):
        async with conn._get_connection():
            raise RuntimeError('work failed')


# ─── check_expiry rotation ───────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_check_expiry_recreates_expired_pool(mocker):
    """An expired pool is closed inline and re-initialized."""
    conn = make_pool_conn(pool_expiry_min=1)
    conn._pool = asyncio.Queue(maxsize=10)
    # Force the pool to be older than the expiry window
    conn.created_time = datetime.now() - timedelta(minutes=5)

    init_mock = mocker.patch.object(conn, 'initialize_pool', new=AsyncMock())

    await conn.check_expiry()

    # Pool is closed inline under the writer lock (set to None)
    assert conn._pool is None
    init_mock.assert_awaited_once()


@pytest.mark.asyncio
async def test_check_expiry_fresh_pool_noop(mocker):
    """A fresh pool skips close/initialize."""
    conn = make_pool_conn(pool_expiry_min=30)
    conn._pool = asyncio.Queue(maxsize=10)
    conn.created_time = datetime.now()  # fresh

    close_mock = mocker.patch.object(conn, 'close', new=AsyncMock())
    init_mock = mocker.patch.object(conn, 'initialize_pool', new=AsyncMock())

    await conn.check_expiry()

    close_mock.assert_not_called()
    init_mock.assert_not_called()


# ─── execute_query typed value mapping ───────────────────────────────────────


@pytest.mark.asyncio
async def test_execute_query_maps_all_value_types(mocker):
    """execute_query produces the correct per-type dict for each cell."""
    conn = make_pool_conn()
    raw_conn = MagicMock()
    conn._pool = asyncio.Queue(maxsize=10)
    conn._pool.put_nowait(raw_conn)

    mocker.patch.object(conn, 'check_expiry', new=AsyncMock())

    # Inside execute_query, asyncio.to_thread runs _run_sync(). Return a mix of
    # every supported type plus a fallback object (datetime) to hit the str() branch.
    class MyDate:
        """Object to trigger the str() fallback branch."""

        def __str__(self):
            """Stringify for fallback cell handling."""
            return '2026-01-01'

    description = [
        ('s',),
        ('i',),
        ('f',),
        ('b',),
        ('bl',),
        ('n',),
        ('o',),
        ('bool',),
    ]
    # Note: bool MUST come before int in isinstance checks (server code matches that order)
    rows = [('hi', 42, 1.5, True, b'bytes', None, MyDate(), False)]

    async def fake_to_thread(func, *args, **kwargs):
        return func(*args, **kwargs)

    mocker.patch(
        'awslabs.mssql_mcp_server.connection.pymssql_pool_connection.asyncio.to_thread',
        new=fake_to_thread,
    )
    cursor = MagicMock()
    cursor.description = description
    cursor.fetchall.return_value = rows
    raw_conn.cursor.return_value = cursor

    result = await conn.execute_query('SELECT whatever')

    records = result['records']
    assert records[0][0] == {'stringValue': 'hi'}
    # bool is checked before int, so True/False come through booleanValue
    assert records[0][3] == {'booleanValue': True}
    assert records[0][7] == {'booleanValue': False}
    # isNull cell
    assert records[0][5] == {'isNull': True}
    assert records[0][4] == {'blobValue': b'bytes'}
    assert records[0][2] == {'doubleValue': 1.5}
    # The fallback object should be stringified
    assert records[0][6] == {'stringValue': '2026-01-01'}


@pytest.mark.asyncio
async def test_execute_query_with_tuple_parameters(mocker):
    """Tuple parameters are forwarded directly to cursor.execute."""
    conn = make_pool_conn()
    raw_conn = MagicMock()
    conn._pool = asyncio.Queue(maxsize=10)
    conn._pool.put_nowait(raw_conn)
    mocker.patch.object(conn, 'check_expiry', new=AsyncMock())

    cursor = MagicMock()
    cursor.description = [('id',)]
    cursor.fetchall.return_value = [(1,)]
    raw_conn.cursor.return_value = cursor

    async def fake_to_thread(func, *args, **kwargs):
        return func(*args, **kwargs)

    mocker.patch(
        'awslabs.mssql_mcp_server.connection.pymssql_pool_connection.asyncio.to_thread',
        new=fake_to_thread,
    )

    result = await conn.execute_query('SELECT * FROM t WHERE id = %s', (1,))

    assert result['records'] == [[{'longValue': 1}]]
    # cursor.execute is called with the tuple as the second positional arg (besides the isolation pragma)
    calls = cursor.execute.call_args_list
    assert any(c.args[0].startswith('SELECT * FROM t') and c.args[1] == (1,) for c in calls)


@pytest.mark.asyncio
async def test_execute_query_with_dict_parameters(mocker):
    """Data API-style dict parameters are converted and forwarded as a list."""
    conn = make_pool_conn()
    raw_conn = MagicMock()
    conn._pool = asyncio.Queue(maxsize=10)
    conn._pool.put_nowait(raw_conn)
    mocker.patch.object(conn, 'check_expiry', new=AsyncMock())

    cursor = MagicMock()
    cursor.description = None
    cursor.fetchall.return_value = []
    raw_conn.cursor.return_value = cursor

    async def fake_to_thread(func, *args, **kwargs):
        return func(*args, **kwargs)

    mocker.patch(
        'awslabs.mssql_mcp_server.connection.pymssql_pool_connection.asyncio.to_thread',
        new=fake_to_thread,
    )

    params = [
        {'name': 'a', 'value': {'stringValue': 'x'}},
        {'name': 'b', 'value': {'longValue': 9}},
    ]
    await conn.execute_query('INSERT INTO t VALUES (%s, %s)', params)

    # The INSERT was executed with the converted positional list
    insert_call = next(c for c in cursor.execute.call_args_list if c.args[0].startswith('INSERT'))
    assert insert_call.args[1] == ['x', 9]


@pytest.mark.asyncio
async def test_execute_query_readonly_rollback(mocker):
    """In readonly mode, the wrapper rollback()s after the SELECT."""
    conn = make_pool_conn(readonly=True)
    raw_conn = MagicMock()
    conn._pool = asyncio.Queue(maxsize=10)
    conn._pool.put_nowait(raw_conn)
    mocker.patch.object(conn, 'check_expiry', new=AsyncMock())

    cursor = MagicMock()
    cursor.description = [('x',)]
    cursor.fetchall.return_value = [(1,)]
    raw_conn.cursor.return_value = cursor

    async def fake_to_thread(func, *args, **kwargs):
        return func(*args, **kwargs)

    mocker.patch(
        'awslabs.mssql_mcp_server.connection.pymssql_pool_connection.asyncio.to_thread',
        new=fake_to_thread,
    )

    await conn.execute_query('SELECT 1 AS x')

    raw_conn.rollback.assert_called_once()
    # Isolation level is set at connection creation, not per-query
    pragma_issued = any(
        c.args[0] == 'SET TRANSACTION ISOLATION LEVEL READ COMMITTED'
        for c in cursor.execute.call_args_list
    )
    assert not pragma_issued


@pytest.mark.asyncio
async def test_execute_query_write_mode_no_rollback(mocker):
    """In write mode, the wrapper does NOT call rollback() (autocommit=True)."""
    conn = make_pool_conn(readonly=False)
    raw_conn = MagicMock()
    conn._pool = asyncio.Queue(maxsize=10)
    conn._pool.put_nowait(raw_conn)
    mocker.patch.object(conn, 'check_expiry', new=AsyncMock())

    cursor = MagicMock()
    cursor.description = None
    cursor.fetchall.return_value = []
    raw_conn.cursor.return_value = cursor

    async def fake_to_thread(func, *args, **kwargs):
        return func(*args, **kwargs)

    mocker.patch(
        'awslabs.mssql_mcp_server.connection.pymssql_pool_connection.asyncio.to_thread',
        new=fake_to_thread,
    )

    await conn.execute_query('INSERT INTO t VALUES (1)')

    raw_conn.rollback.assert_not_called()


@pytest.mark.asyncio
async def test_execute_query_propagates_error(mocker):
    """Exceptions from to_thread propagate to the caller."""
    conn = make_pool_conn()
    raw_conn = MagicMock()
    conn._pool = asyncio.Queue(maxsize=10)
    conn._pool.put_nowait(raw_conn)
    mocker.patch.object(conn, 'check_expiry', new=AsyncMock())

    async def failing_to_thread(func, *args, **kwargs):
        raise RuntimeError('db gone')

    mocker.patch(
        'awslabs.mssql_mcp_server.connection.pymssql_pool_connection.asyncio.to_thread',
        new=failing_to_thread,
    )

    with pytest.raises(RuntimeError, match='db gone'):
        await conn.execute_query('SELECT 1')


# ─── _convert_parameters extended coverage ───────────────────────────────────


def test_convert_parameters_double_blob_bool():
    """_convert_parameters maps double, blob and boolean values."""
    conn = make_pool_conn()
    params = [
        {'name': 'a', 'value': {'doubleValue': 1.25}},
        {'name': 'b', 'value': {'blobValue': b'zz'}},
        {'name': 'c', 'value': {'booleanValue': True}},
    ]
    values = list(conn._convert_parameters(params).values())
    assert values == [1.25, b'zz', True]


def test_convert_parameters_unknown_type_raises():
    """Unknown value types raise ValueError with a clear message."""
    conn = make_pool_conn()
    params = [{'name': 'a', 'value': {'mysteryValue': 1}}]
    with pytest.raises(ValueError, match='unrecognized value format'):
        conn._convert_parameters(params)


# ─── _get_credentials_from_secret (non-test path) ────────────────────────────


def test_get_credentials_uses_test_shortcut():
    """When is_test=True the shortcut returns static credentials."""
    conn = make_pool_conn()
    user, password = conn._get_credentials_from_secret('arn', 'us-east-1', is_test=True)
    assert user == 'test_user'
    assert password == 'test_password'  # pragma: allowlist secret


def test_get_credentials_returns_username_password(mocker):
    """Valid secret JSON yields (username, password)."""
    conn = make_pool_conn()
    fake_client = MagicMock()
    fake_client.get_secret_value.return_value = {
        'SecretString': json.dumps({'username': 'alice', 'password': 's3cr3t'})
    }
    fake_session = MagicMock()
    fake_session.client.return_value = fake_client
    mocker.patch(
        'awslabs.mssql_mcp_server.connection.pymssql_pool_connection.boto3.Session',
        return_value=fake_session,
    )
    user, password = conn._get_credentials_from_secret('arn', 'us-east-1', is_test=False)
    assert user == 'alice'
    assert password == 's3cr3t'  # pragma: allowlist secret


def test_get_credentials_alt_keys(mocker):
    """Capitalised/alternate keys are also accepted."""
    conn = make_pool_conn()
    fake_client = MagicMock()
    fake_client.get_secret_value.return_value = {
        'SecretString': json.dumps({'Username': 'bob', 'Password': 'pw'})
    }
    fake_session = MagicMock()
    fake_session.client.return_value = fake_client
    mocker.patch(
        'awslabs.mssql_mcp_server.connection.pymssql_pool_connection.boto3.Session',
        return_value=fake_session,
    )
    user, password = conn._get_credentials_from_secret('arn', 'us-east-1', is_test=False)
    assert user == 'bob'
    assert password == 'pw'  # pragma: allowlist secret


def test_get_credentials_missing_username_raises(mocker):
    """A secret without a username raises ValueError."""
    conn = make_pool_conn()
    fake_client = MagicMock()
    fake_client.get_secret_value.return_value = {'SecretString': json.dumps({'password': 'pw'})}
    fake_session = MagicMock()
    fake_session.client.return_value = fake_client
    mocker.patch(
        'awslabs.mssql_mcp_server.connection.pymssql_pool_connection.boto3.Session',
        return_value=fake_session,
    )
    with pytest.raises(ValueError, match='Failed to retrieve credentials'):
        conn._get_credentials_from_secret('arn', 'us-east-1', is_test=False)


def test_get_credentials_missing_password_raises(mocker):
    """A secret without a password raises ValueError."""
    conn = make_pool_conn()
    fake_client = MagicMock()
    fake_client.get_secret_value.return_value = {'SecretString': json.dumps({'username': 'alice'})}
    fake_session = MagicMock()
    fake_session.client.return_value = fake_client
    mocker.patch(
        'awslabs.mssql_mcp_server.connection.pymssql_pool_connection.boto3.Session',
        return_value=fake_session,
    )
    with pytest.raises(ValueError, match='Failed to retrieve credentials'):
        conn._get_credentials_from_secret('arn', 'us-east-1', is_test=False)


def test_get_credentials_no_secret_string_raises(mocker):
    """A response without a SecretString raises ValueError."""
    conn = make_pool_conn()
    fake_client = MagicMock()
    fake_client.get_secret_value.return_value = {}  # no SecretString
    fake_session = MagicMock()
    fake_session.client.return_value = fake_client
    mocker.patch(
        'awslabs.mssql_mcp_server.connection.pymssql_pool_connection.boto3.Session',
        return_value=fake_session,
    )
    with pytest.raises(ValueError, match='Failed to retrieve credentials'):
        conn._get_credentials_from_secret('arn', 'us-east-1', is_test=False)


def test_get_credentials_client_error_raises(mocker):
    """A Secrets Manager client error is wrapped as ValueError."""
    conn = make_pool_conn()
    fake_client = MagicMock()
    fake_client.get_secret_value.side_effect = Exception('AccessDenied')
    fake_session = MagicMock()
    fake_session.client.return_value = fake_client
    mocker.patch(
        'awslabs.mssql_mcp_server.connection.pymssql_pool_connection.boto3.Session',
        return_value=fake_session,
    )
    with pytest.raises(ValueError, match='Failed to retrieve credentials'):
        conn._get_credentials_from_secret('arn', 'us-east-1', is_test=False)


# ─── close() behaviour ───────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_close_survives_inner_errors(mocker):
    """close() swallows exceptions thrown while closing individual connections."""
    conn = make_pool_conn()
    bad = MagicMock()
    bad.close.side_effect = Exception('nope')

    conn._pool = asyncio.Queue(maxsize=10)
    conn._pool.put_nowait(bad)

    async def fake_to_thread(func, *args, **kwargs):
        return func(*args, **kwargs)

    mocker.patch(
        'awslabs.mssql_mcp_server.connection.pymssql_pool_connection.asyncio.to_thread',
        new=fake_to_thread,
    )

    await conn.close()
    assert conn._pool is None


@pytest.mark.asyncio
async def test_close_when_pool_none_is_noop():
    """close() on an un-initialized pool is a no-op."""
    conn = make_pool_conn()
    conn._pool = None
    await conn.close()  # must not raise
