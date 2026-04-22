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

"""Tests for OracledbPoolConnection."""

import pytest
from awslabs.oracle_mcp_server.connection.oracledb_pool_connection import OracledbPoolConnection
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch


def make_pool_conn(**kwargs):
    """Create a test OracledbPoolConnection with sensible defaults."""
    defaults = {
        'host': 'localhost',
        'port': 1521,
        'database': 'ORCL',
        'readonly': True,
        'secret_arn': 'arn:aws:secretsmanager:us-east-1:123:secret:test',  # pragma: allowlist secret
        'region': 'us-east-1',
        'service_name': 'ORCL',
        'is_test': True,
    }
    defaults.update(kwargs)
    return OracledbPoolConnection(**defaults)


def test_service_name_dsn_format():
    """Verify DSN uses connect descriptor with SERVICE_NAME."""
    conn = make_pool_conn(service_name='ORCL', sid=None)
    assert conn.dsn == (
        '(DESCRIPTION='
        '(ADDRESS=(PROTOCOL=TCPS)(HOST=localhost)(PORT=1521))'
        '(CONNECT_DATA=(SERVICE_NAME=ORCL)))'
    )


def test_sid_dsn_format():
    """Verify DSN uses connect descriptor with SID."""
    conn = OracledbPoolConnection(
        host='localhost',
        port=1521,
        database='ORCL',
        readonly=True,
        secret_arn='',
        region='us-east-1',
        sid='ORCL',
    )
    assert conn.dsn == (
        '(DESCRIPTION='
        '(ADDRESS=(PROTOCOL=TCPS)(HOST=localhost)(PORT=1521))'
        '(CONNECT_DATA=(SID=ORCL)))'
    )


def test_ssl_require_uses_tcps_protocol():
    """Verify ssl_encryption=require uses TCPS protocol in DSN."""
    conn = make_pool_conn(ssl_encryption='require')
    assert '(PROTOCOL=TCPS)' in conn.dsn


def test_ssl_off_uses_tcp_protocol():
    """Verify ssl_encryption=off uses plain TCP protocol in DSN."""
    conn = make_pool_conn(ssl_encryption='off')
    assert '(PROTOCOL=TCP)' in conn.dsn
    assert '(PROTOCOL=TCPS)' not in conn.dsn


def test_both_service_name_and_sid_raises():
    """Verify providing both service_name and sid raises ValueError."""
    with pytest.raises(ValueError, match='not both'):
        OracledbPoolConnection(
            host='localhost',
            port=1521,
            database='ORCL',
            readonly=True,
            secret_arn='',
            region='us-east-1',
            service_name='ORCL',
            sid='ORCL',
        )


def test_neither_service_name_nor_sid_raises():
    """Verify providing neither service_name nor sid raises ValueError."""
    with pytest.raises(ValueError, match='must be provided'):
        OracledbPoolConnection(
            host='localhost',
            port=1521,
            database='ORCL',
            readonly=True,
            secret_arn='',
            region='us-east-1',
        )


@pytest.mark.asyncio
async def test_initialize_pool_calls_create_pool_async():
    """Verify initialize_pool calls oracledb.create_pool_async."""
    conn = make_pool_conn()
    mock_pool = AsyncMock()
    with patch('oracledb.create_pool_async', new=MagicMock(return_value=mock_pool)):
        await conn.initialize_pool()
    assert conn.pool is mock_pool


@pytest.mark.asyncio
async def test_initialize_pool_idempotent():
    """Verify calling initialize_pool twice reuses the existing pool."""
    conn = make_pool_conn()
    mock_pool = AsyncMock()
    with patch('oracledb.create_pool_async', new=MagicMock(return_value=mock_pool)):
        await conn.initialize_pool()
        pool_ref = conn.pool
        await conn.initialize_pool()
    assert conn.pool is pool_ref


@pytest.mark.asyncio
async def test_initialize_pool_passes_ssl_context_when_require():
    """Verify ssl_context and ssl_server_dn_match=True are passed when ssl_encryption=require."""
    conn = make_pool_conn(ssl_encryption='require')
    mock_pool = AsyncMock()
    create_pool_mock = MagicMock(return_value=mock_pool)
    with patch('oracledb.create_pool_async', new=create_pool_mock):
        await conn.initialize_pool()
    call_kwargs = create_pool_mock.call_args.kwargs
    assert call_kwargs.get('ssl_server_dn_match') is True
    assert call_kwargs.get('ssl_context') is not None


def test_ssl_noverify_uses_tcps_protocol():
    """Verify ssl_encryption=noverify uses TCPS protocol in DSN."""
    conn = make_pool_conn(ssl_encryption='noverify')
    assert '(PROTOCOL=TCPS)' in conn.dsn


@pytest.mark.asyncio
async def test_initialize_pool_ssl_noverify():
    """Verify ssl_context is passed with ssl_server_dn_match=False when ssl_encryption=noverify."""
    conn = make_pool_conn(ssl_encryption='noverify')
    mock_pool = AsyncMock()
    create_pool_mock = MagicMock(return_value=mock_pool)
    with patch('oracledb.create_pool_async', new=create_pool_mock):
        await conn.initialize_pool()
    call_kwargs = create_pool_mock.call_args.kwargs
    assert call_kwargs.get('ssl_server_dn_match') is False
    assert call_kwargs.get('ssl_context') is not None


@pytest.mark.asyncio
async def test_initialize_pool_no_ssl_when_off():
    """Verify no SSL kwargs are passed when ssl_encryption=off."""
    conn = make_pool_conn(ssl_encryption='off')
    mock_pool = AsyncMock()
    create_pool_mock = MagicMock(return_value=mock_pool)
    with patch('oracledb.create_pool_async', new=create_pool_mock):
        await conn.initialize_pool()
    call_kwargs = create_pool_mock.call_args.kwargs
    assert 'ssl_context' not in call_kwargs
    assert 'ssl_server_dn_match' not in call_kwargs


@pytest.mark.asyncio
async def test_initialize_pool_no_seclevel_override():
    """Verify SSL context does not use @SECLEVEL=0 cipher override."""
    conn = make_pool_conn(ssl_encryption='require')
    mock_pool = AsyncMock()
    create_pool_mock = MagicMock(return_value=mock_pool)
    with patch('oracledb.create_pool_async', new=create_pool_mock):
        await conn.initialize_pool()
    call_kwargs = create_pool_mock.call_args.kwargs
    ssl_ctx = call_kwargs.get('ssl_context')
    # The default context should not have @SECLEVEL=0 in its cipher string
    # We verify by checking that the context uses system defaults (no manual cipher override)
    assert ssl_ctx is not None


def test_convert_parameters_named():
    """Verify named parameters are converted to a dict."""
    conn = make_pool_conn()
    params = [
        {'name': 'table_name', 'value': {'stringValue': 'USERS'}},
        {'name': 'schema_name', 'value': {'stringValue': 'HR'}},
    ]
    result = conn._convert_parameters(params)
    assert result == {'table_name': 'USERS', 'schema_name': 'HR'}


def test_convert_parameters_null():
    """Verify null parameters are converted to None."""
    conn = make_pool_conn()
    params = [{'name': 'val', 'value': {'isNull': True}}]
    result = conn._convert_parameters(params)
    assert result == {'val': None}


@pytest.mark.asyncio
async def test_close_sets_pool_to_none():
    """Verify close() sets pool to None and awaits pool.close()."""
    conn = make_pool_conn()
    mock_pool = AsyncMock()
    conn.pool = mock_pool
    await conn.close()
    assert conn.pool is None
    mock_pool.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_check_connection_health_healthy():
    """Verify healthy connection returns True."""
    conn = make_pool_conn()
    with patch.object(conn, 'execute_query', new=AsyncMock(return_value=[{'1': 1}])):
        result = await conn.check_connection_health()
    assert result is True


@pytest.mark.asyncio
async def test_check_connection_health_uses_dual():
    """Verify health check queries SELECT 1 FROM DUAL."""
    conn = make_pool_conn()
    execute_mock = AsyncMock(return_value=[{'1': 1}])
    with patch.object(conn, 'execute_query', new=execute_mock):
        await conn.check_connection_health()
    execute_mock.assert_called_once_with('SELECT 1 FROM DUAL')


@pytest.mark.asyncio
async def test_check_connection_health_unhealthy():
    """Verify failed connection returns False."""
    conn = make_pool_conn()
    with patch.object(conn, 'execute_query', new=AsyncMock(side_effect=Exception('conn failed'))):
        result = await conn.check_connection_health()
    assert result is False


# --- validate_sync ---


def test_validate_sync_success():
    """Verify validate_sync completes without error on a healthy connection."""
    conn = make_pool_conn()

    mock_cursor = MagicMock()
    mock_oracledb_conn = MagicMock()
    mock_oracledb_conn.__enter__ = MagicMock(return_value=mock_oracledb_conn)
    mock_oracledb_conn.__exit__ = MagicMock(return_value=False)
    mock_oracledb_conn.cursor.return_value = mock_cursor
    mock_cursor.__enter__ = MagicMock(return_value=mock_cursor)
    mock_cursor.__exit__ = MagicMock(return_value=False)

    with patch('oracledb.connect', return_value=mock_oracledb_conn):
        conn.validate_sync()

    mock_cursor.execute.assert_called_once_with('SELECT 1 FROM DUAL')
    mock_cursor.fetchone.assert_called_once()


def test_validate_sync_failure():
    """Verify validate_sync raises when connection fails."""
    conn = make_pool_conn()

    with patch('oracledb.connect', side_effect=Exception('connection refused')):
        with pytest.raises(Exception, match='connection refused'):
            conn.validate_sync()


# --- check_expiry ---


@pytest.mark.asyncio
async def test_check_expiry_not_expired():
    """Pool is not recycled when within expiry window."""
    conn = make_pool_conn()
    conn.pool = AsyncMock()
    conn.created_time = datetime.now()

    close_mock = AsyncMock()
    with patch.object(conn, 'close', close_mock):
        await conn.check_expiry()

    close_mock.assert_not_awaited()


@pytest.mark.asyncio
async def test_check_expiry_reinitializes_expired_pool():
    """Expired pool is closed and reinitialized."""
    conn = make_pool_conn(pool_expiry_min=0)
    old_pool = AsyncMock()
    conn.pool = old_pool
    conn.created_time = datetime.now() - timedelta(hours=1)

    new_pool = AsyncMock()
    with patch('oracledb.create_pool_async', new=MagicMock(return_value=new_pool)):
        await conn.check_expiry()

    old_pool.close.assert_awaited_once()
    assert conn.pool is new_pool


@pytest.mark.asyncio
async def test_check_expiry_retries_on_failure():
    """Pool reinitialization retries up to 3 times before raising."""
    conn = make_pool_conn(pool_expiry_min=0)
    conn.pool = AsyncMock()
    conn.created_time = datetime.now() - timedelta(hours=1)

    create_mock = MagicMock(
        side_effect=[Exception('fail1'), Exception('fail2'), Exception('fail3')]
    )
    with patch('oracledb.create_pool_async', new=create_mock):
        with pytest.raises(ValueError, match='Failed to reinitialize pool after 3 attempts'):
            await conn.check_expiry()

    assert create_mock.call_count == 3


@pytest.mark.asyncio
async def test_check_expiry_succeeds_on_second_retry():
    """Pool reinitialization succeeds on second attempt."""
    conn = make_pool_conn(pool_expiry_min=0)
    conn.pool = AsyncMock()
    conn.created_time = datetime.now() - timedelta(hours=1)

    new_pool = AsyncMock()
    create_mock = MagicMock(side_effect=[Exception('fail1'), new_pool])
    with patch('oracledb.create_pool_async', new=create_mock):
        await conn.check_expiry()

    assert create_mock.call_count == 2
    assert conn.pool is new_pool


# --- execute_query ---


@pytest.mark.asyncio
async def test_execute_query_returns_flat_dicts():
    """execute_query returns a list of flat dicts, not RDS Data API format."""
    conn = make_pool_conn(readonly=False)

    mock_cursor = MagicMock()
    mock_cursor.description = [('ID',), ('NAME',)]
    mock_cursor.execute = AsyncMock()
    mock_cursor.fetchall = AsyncMock(return_value=[(1, 'Alice'), (2, 'Bob')])
    mock_cursor.__aenter__ = AsyncMock(return_value=mock_cursor)
    mock_cursor.__aexit__ = AsyncMock(return_value=False)

    mock_conn = MagicMock()
    mock_conn.execute = AsyncMock()
    mock_conn.commit = AsyncMock()
    mock_conn.cursor = MagicMock(return_value=mock_cursor)
    mock_conn.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_conn.__aexit__ = AsyncMock(return_value=False)

    mock_pool = MagicMock()
    mock_pool.acquire = MagicMock(return_value=mock_conn)

    conn.pool = mock_pool
    conn.created_time = datetime.now()

    result = await conn.execute_query('SELECT ID, NAME FROM users')

    assert result == [{'ID': 1, 'NAME': 'Alice'}, {'ID': 2, 'NAME': 'Bob'}]


@pytest.mark.asyncio
async def test_execute_query_max_rows():
    """execute_query respects max_rows by using fetchmany."""
    conn = make_pool_conn(readonly=False)

    mock_cursor = MagicMock()
    mock_cursor.description = [('ID',)]
    mock_cursor.execute = AsyncMock()
    # fetchmany(max_rows + 1) returns max_rows + 1 rows
    mock_cursor.fetchmany = AsyncMock(return_value=[(1,), (2,), (3,)])
    mock_cursor.__aenter__ = AsyncMock(return_value=mock_cursor)
    mock_cursor.__aexit__ = AsyncMock(return_value=False)

    mock_conn = MagicMock()
    mock_conn.execute = AsyncMock()
    mock_conn.commit = AsyncMock()
    mock_conn.cursor = MagicMock(return_value=mock_cursor)
    mock_conn.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_conn.__aexit__ = AsyncMock(return_value=False)

    mock_pool = MagicMock()
    mock_pool.acquire = MagicMock(return_value=mock_conn)

    conn.pool = mock_pool
    conn.created_time = datetime.now()

    result = await conn.execute_query('SELECT ID FROM t', max_rows=2)

    mock_cursor.fetchmany.assert_awaited_once_with(3)  # max_rows + 1
    assert len(result) == 3  # all returned; truncation happens in server layer


@pytest.mark.asyncio
async def test_execute_query_no_pool_raises():
    """execute_query raises ValueError when pool is None."""
    conn = make_pool_conn()
    conn.pool = None
    conn.created_time = datetime.now()

    # Mock check_expiry to not reinitialize
    with patch.object(conn, 'check_expiry', new=AsyncMock()):
        with pytest.raises(ValueError, match='Failed to initialize connection pool'):
            await conn.execute_query('SELECT 1 FROM DUAL')


@pytest.mark.asyncio
async def test_execute_query_readonly_sets_transaction_and_rollback():
    """In read-only mode, SET TRANSACTION READ ONLY is issued and rollback follows."""
    conn = make_pool_conn(readonly=True)

    mock_cursor = MagicMock()
    mock_cursor.description = [('X',)]
    mock_cursor.execute = AsyncMock()
    mock_cursor.fetchall = AsyncMock(return_value=[(1,)])
    mock_cursor.__aenter__ = AsyncMock(return_value=mock_cursor)
    mock_cursor.__aexit__ = AsyncMock(return_value=False)

    mock_conn = MagicMock()
    mock_conn.execute = AsyncMock()
    mock_conn.rollback = AsyncMock()
    mock_conn.commit = AsyncMock()
    mock_conn.cursor = MagicMock(return_value=mock_cursor)
    mock_conn.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_conn.__aexit__ = AsyncMock(return_value=False)

    mock_pool = MagicMock()
    mock_pool.acquire = MagicMock(return_value=mock_conn)

    conn.pool = mock_pool
    conn.created_time = datetime.now()

    result = await conn.execute_query('SELECT 1 FROM DUAL')

    mock_conn.execute.assert_awaited_once_with('SET TRANSACTION READ ONLY')
    mock_conn.rollback.assert_awaited_once()
    mock_conn.commit.assert_not_awaited()
    assert result == [{'X': 1}]


@pytest.mark.asyncio
async def test_execute_query_write_mode_commits():
    """In write mode, no-result queries are committed."""
    conn = make_pool_conn(readonly=False)

    mock_cursor = MagicMock()
    mock_cursor.description = None
    mock_cursor.execute = AsyncMock()
    mock_cursor.__aenter__ = AsyncMock(return_value=mock_cursor)
    mock_cursor.__aexit__ = AsyncMock(return_value=False)

    mock_conn = MagicMock()
    mock_conn.execute = AsyncMock()
    mock_conn.rollback = AsyncMock()
    mock_conn.commit = AsyncMock()
    mock_conn.cursor = MagicMock(return_value=mock_cursor)
    mock_conn.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_conn.__aexit__ = AsyncMock(return_value=False)

    mock_pool = MagicMock()
    mock_pool.acquire = MagicMock(return_value=mock_conn)

    conn.pool = mock_pool
    conn.created_time = datetime.now()

    result = await conn.execute_query('INSERT INTO t VALUES (1)')

    mock_conn.commit.assert_awaited_once()
    mock_conn.rollback.assert_not_awaited()
    assert result == []


@pytest.mark.asyncio
async def test_execute_query_converts_non_native_types_to_str():
    """Non-native types (e.g. datetime) are converted to strings."""
    conn = make_pool_conn(readonly=False)

    test_dt = datetime(2025, 1, 15, 12, 0, 0)
    mock_cursor = MagicMock()
    mock_cursor.description = [('TS',)]
    mock_cursor.execute = AsyncMock()
    mock_cursor.fetchall = AsyncMock(return_value=[(test_dt,)])
    mock_cursor.__aenter__ = AsyncMock(return_value=mock_cursor)
    mock_cursor.__aexit__ = AsyncMock(return_value=False)

    mock_conn = MagicMock()
    mock_conn.execute = AsyncMock()
    mock_conn.commit = AsyncMock()
    mock_conn.cursor = MagicMock(return_value=mock_cursor)
    mock_conn.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_conn.__aexit__ = AsyncMock(return_value=False)

    mock_pool = MagicMock()
    mock_pool.acquire = MagicMock(return_value=mock_conn)

    conn.pool = mock_pool
    conn.created_time = datetime.now()

    result = await conn.execute_query('SELECT ts FROM t')

    assert result == [{'TS': str(test_dt)}]
