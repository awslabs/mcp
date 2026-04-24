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

"""Tests for PymssqlPoolConnection."""

import asyncio
import pytest
from awslabs.mssql_mcp_server.connection.pymssql_pool_connection import PymssqlPoolConnection
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


@pytest.mark.asyncio
async def test_initialize_pool_is_test():
    """With is_test=True, pool initializes using test credentials."""
    conn = make_pool_conn()
    mock_pymssql_conn = MagicMock()
    with patch.object(conn, '_create_raw_connection', return_value=mock_pymssql_conn):
        await conn.initialize_pool()
    assert conn._pool is not None
    assert not conn._pool.empty()


@pytest.mark.asyncio
async def test_initialize_pool_idempotent():
    """Calling initialize_pool twice does not re-initialize."""
    conn = make_pool_conn()
    mock_raw = MagicMock()
    with patch.object(conn, '_create_raw_connection', return_value=mock_raw):
        await conn.initialize_pool()
        pool_ref = conn._pool
        await conn.initialize_pool()
        assert conn._pool is pool_ref


@pytest.mark.asyncio
async def test_execute_query_returns_rows():
    """execute_query returns columnMetadata and records on a successful SELECT."""
    conn = make_pool_conn()
    mock_cursor = MagicMock()
    mock_cursor.description = [('id',), ('name',)]
    mock_cursor.fetchall.return_value = [(1, 'Alice')]
    mock_raw_conn = MagicMock()
    mock_raw_conn.cursor.return_value = mock_cursor

    conn._pool = asyncio.Queue(maxsize=10)
    conn._pool.put_nowait(mock_raw_conn)

    with patch(
        'asyncio.to_thread', new=AsyncMock(return_value=(mock_cursor.description, [(1, 'Alice')]))
    ):
        result = await conn.execute_query('SELECT id, name FROM users')

    assert 'columnMetadata' in result
    assert 'records' in result


@pytest.mark.asyncio
async def test_execute_query_no_results():
    """execute_query returns empty metadata and records for a non-SELECT statement."""
    conn = make_pool_conn()
    mock_cursor = MagicMock()
    mock_cursor.description = None
    mock_cursor.fetchall.return_value = []
    mock_raw_conn = MagicMock()
    mock_raw_conn.cursor.return_value = mock_cursor

    conn._pool = asyncio.Queue(maxsize=10)
    conn._pool.put_nowait(mock_raw_conn)

    with patch('asyncio.to_thread', new=AsyncMock(return_value=(None, []))):
        result = await conn.execute_query('UPDATE foo SET bar=1')

    assert result == {'columnMetadata': [], 'records': []}


def test_convert_parameters_preserves_order():
    """_convert_parameters preserves parameter order and maps typed values correctly."""
    conn = make_pool_conn()
    params = [
        {'name': 'a', 'value': {'stringValue': 'hello'}},
        {'name': 'b', 'value': {'longValue': 42}},
        {'name': 'c', 'value': {'isNull': True}},
    ]
    result = conn._convert_parameters(params)
    values = list(result.values())
    assert values == ['hello', 42, None]


@pytest.mark.asyncio
async def test_close_empties_pool():
    """close() sets the pool to None."""
    conn = make_pool_conn()
    mock_raw = MagicMock()
    conn._pool = asyncio.Queue(maxsize=10)
    conn._pool.put_nowait(mock_raw)
    await conn.close()
    assert conn._pool is None


@pytest.mark.asyncio
async def test_check_connection_health_healthy():
    """check_connection_health returns True when execute_query succeeds."""
    conn = make_pool_conn()
    with patch.object(conn, 'execute_query', new=AsyncMock(return_value={'records': [{'1': 1}]})):
        result = await conn.check_connection_health()
    assert result is True


@pytest.mark.asyncio
async def test_check_connection_health_unhealthy():
    """check_connection_health returns False when execute_query raises."""
    conn = make_pool_conn()
    with patch.object(
        conn, 'execute_query', new=AsyncMock(side_effect=Exception('connection failed'))
    ):
        result = await conn.check_connection_health()
    assert result is False


def test_create_raw_connection_passes_ssl_properties():
    """_create_raw_connection passes encryption and autocommit=False in readonly mode."""
    conn = make_pool_conn()
    mock_connect = MagicMock()
    with patch('pymssql.connect', mock_connect):
        conn._create_raw_connection('user', 'pass')
    call_kwargs = mock_connect.call_args.kwargs
    assert call_kwargs.get('encryption') == 'require'
    assert call_kwargs.get('autocommit') is False


def test_create_raw_connection_autocommit_enabled_in_write_mode():
    """_create_raw_connection sets autocommit=True in write mode."""
    conn = make_pool_conn(readonly=False)
    mock_connect = MagicMock()
    with patch('pymssql.connect', mock_connect):
        conn._create_raw_connection('user', 'pass')
    call_kwargs = mock_connect.call_args.kwargs
    assert call_kwargs.get('autocommit') is True
