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

"""Tests for pool exhaustion timeout and connection expiry leak fix."""

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


# ─── pool exhaustion timeout ────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_pool_exhaustion_raises_timeout():
    """When all connections are checked out, _get_connection times out."""
    conn = make_pool_conn(max_size=1, pool_expiry_min=60)
    conn._pool = asyncio.Queue(maxsize=1)
    # Pool is empty (all connections checked out)
    # Don't put anything in the queue

    with pytest.raises(asyncio.TimeoutError):
        async with conn._get_connection():
            pass  # pragma: no cover


@pytest.mark.asyncio
async def test_pool_get_timeout_is_15_seconds(mocker):
    """The pool timeout value passed to asyncio.wait_for is 15 seconds."""
    conn = make_pool_conn(max_size=1, pool_expiry_min=60)
    conn._pool = asyncio.Queue(maxsize=1)

    captured_timeout = {}

    async def mock_wait_for(coro, *, timeout=None):
        captured_timeout['value'] = timeout
        raise asyncio.TimeoutError()

    mocker.patch('asyncio.wait_for', side_effect=mock_wait_for)

    with pytest.raises(asyncio.TimeoutError):
        async with conn._get_connection():
            pass  # pragma: no cover

    assert captured_timeout['value'] == 15.0


# ─── connection leak fix on pool expiry ──────────────────────────────────────────


@pytest.mark.asyncio
async def test_connection_closed_on_pool_replacement():
    """Connection from old pool is closed (not returned) when pool was replaced."""
    conn = make_pool_conn(max_size=2, pool_expiry_min=60)

    old_pool = asyncio.Queue(maxsize=2)
    mock_old_conn = MagicMock()
    old_pool.put_nowait(mock_old_conn)
    conn._pool = old_pool

    # Simulate: we get a connection, then pool is replaced during our work
    new_pool = asyncio.Queue(maxsize=2)
    mock_new_conn = MagicMock()
    new_pool.put_nowait(mock_new_conn)

    async with conn._get_connection() as checked_out:
        assert checked_out is mock_old_conn
        # Replace the pool (as check_expiry would do)
        conn._pool = new_pool

    # The old connection should have been closed, not returned to new pool
    mock_old_conn.close.assert_called_once()
    # New pool should still have its connection untouched
    assert new_pool.qsize() == 1


@pytest.mark.asyncio
async def test_connection_returned_when_pool_not_replaced():
    """Connection is returned to pool when the pool has not been replaced."""
    conn = make_pool_conn(max_size=2, pool_expiry_min=60)

    pool = asyncio.Queue(maxsize=2)
    mock_conn = MagicMock()
    pool.put_nowait(mock_conn)
    conn._pool = pool

    async with conn._get_connection() as checked_out:
        assert checked_out is mock_conn
        # Pool stays the same

    # Connection should be returned to the same pool
    assert pool.qsize() == 1
    returned = pool.get_nowait()
    assert returned is mock_conn
    mock_conn.close.assert_not_called()


# ─── describe_db_instances failures ──────────────────────────────────────────────


# ─── pool-None during replacement ──────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_connection_closes_conn_when_pool_becomes_none():
    """When pool becomes None between checkout and return, connection is closed."""
    conn = make_pool_conn(max_size=2, pool_expiry_min=60)

    pool = asyncio.Queue(maxsize=2)
    mock_db_conn = MagicMock()
    pool.put_nowait(mock_db_conn)
    conn._pool = pool

    async with conn._get_connection() as checked_out:
        assert checked_out is mock_db_conn
        conn._pool = None

    mock_db_conn.close.assert_called_once()


# ─── QueueFull path ────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_replacement_conn_closed_on_queue_full():
    """Surplus replacement connections are closed when the pool queue is full."""
    conn = make_pool_conn(max_size=1, pool_expiry_min=60)

    pool = asyncio.Queue(maxsize=1)
    mock_db_conn = MagicMock()
    pool.put_nowait(mock_db_conn)
    conn._pool = pool

    mock_new_conn = MagicMock()
    with (
        patch.object(conn, '_create_raw_connection', return_value=mock_new_conn),
        patch.object(conn, '_get_credentials_from_secret', return_value=('user', 'pass')),
    ):
        try:
            async with conn._get_connection() as _:
                # Fill the pool back up so put_nowait will raise QueueFull
                filler = MagicMock()
                pool.put_nowait(filler)
                raise RuntimeError('simulated failure')
        except RuntimeError:
            pass

    mock_db_conn.close.assert_called_once()
    mock_new_conn.close.assert_called_once()


# ─── close_all_async ───────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_close_all_async():
    """close_all_async closes all connections and clears the map."""
    from awslabs.mssql_mcp_server.connection.db_connection_map import (
        ConnectionMethod,
        DBConnectionMap,
    )

    conn_map = DBConnectionMap()
    mock_conn = AsyncMock()
    conn_map.set(ConnectionMethod.MSSQL_PASSWORD, 'i1', 'e1', 'db1', mock_conn, 1433)

    await conn_map.close_all_async()

    assert len(conn_map.map) == 0
    mock_conn.close.assert_awaited_once()


# ─── check_expiry with pool=None ───────────────────────────────────────────────


@pytest.mark.asyncio
async def test_check_expiry_reinitializes_when_pool_is_none():
    """check_expiry re-initializes the pool when it is None."""
    conn = make_pool_conn(max_size=1, pool_expiry_min=60)
    conn._pool = None

    mock_raw = MagicMock()
    with patch.object(conn, '_create_raw_connection', return_value=mock_raw):
        await conn.check_expiry()

    assert conn._pool is not None
    assert not conn._pool.empty()


# ─── describe_db_instances failures ──────────────────────────────────────────────


def test_describe_db_instances_access_denied(mocker):
    """AccessDenied error from describe_db_instances propagates as ClientError."""
    from awslabs.mssql_mcp_server.server import internal_get_instance_valid_endpoints
    from botocore.exceptions import ClientError

    mock_rds = MagicMock()
    mock_rds.describe_db_instances.side_effect = ClientError(
        {'Error': {'Code': 'AccessDenied', 'Message': 'not authorized'}},
        'DescribeDBInstances',
    )
    mocker.patch('awslabs.mssql_mcp_server.server.boto3.client', return_value=mock_rds)

    with pytest.raises(ClientError) as exc_info:
        internal_get_instance_valid_endpoints('my-instance', 'us-east-1')
    assert exc_info.value.response['Error']['Code'] == 'AccessDenied'


def test_describe_db_instances_not_found(mocker):
    """DBInstanceNotFound error from describe_db_instances propagates."""
    from awslabs.mssql_mcp_server.server import internal_get_instance_valid_endpoints
    from botocore.exceptions import ClientError

    mock_rds = MagicMock()
    mock_rds.describe_db_instances.side_effect = ClientError(
        {'Error': {'Code': 'DBInstanceNotFound', 'Message': 'instance not found'}},
        'DescribeDBInstances',
    )
    mocker.patch('awslabs.mssql_mcp_server.server.boto3.client', return_value=mock_rds)

    with pytest.raises(ClientError) as exc_info:
        internal_get_instance_valid_endpoints('nonexistent', 'us-east-1')
    assert exc_info.value.response['Error']['Code'] == 'DBInstanceNotFound'
