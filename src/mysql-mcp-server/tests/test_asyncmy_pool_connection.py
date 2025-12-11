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

"""Tests for the asyncmy connector functionality."""

import json
import pytest
from awslabs.mysql_mcp_server.connection.asyncmy_pool_connection import (
    AsyncmyPoolConnection,
    _get_credentials_from_secret,
)
from unittest.mock import AsyncMock, MagicMock, patch


class AsyncContextManagerMock:
    """Helper to mock async context managers."""

    def __init__(self, return_value):
        """Initialize the async context manager mock.

        Args:
            return_value: Value to return on __aenter__.
        """
        self.return_value = return_value

    async def __aenter__(self):
        """Enter the async context manager."""
        return self.return_value

    async def __aexit__(self, exc_type, exc, tb):
        """Exit the async context manager."""
        pass


@pytest.mark.asyncio
async def test_initialize_pool_creates_pool():
    """Test that initialize_pool successfully creates the connection pool."""
    with (
        patch(
            'awslabs.mysql_mcp_server.connection.asyncmy_pool_connection.create_pool',
            new_callable=AsyncMock,
        ) as mock_create_pool,
        patch(
            'awslabs.mysql_mcp_server.connection.asyncmy_pool_connection._get_credentials_from_secret',
            return_value=('user', 'pass'),
        ),
    ):
        conn = AsyncmyPoolConnection(
            hostname='localhost',
            port=3306,
            database='testdb',
            readonly=False,
            secret_arn='arn:test',
            region='us-east-1',
        )
        await conn.initialize_pool()
        mock_create_pool.assert_awaited_once()
        assert conn.pool is not None


@pytest.mark.asyncio
async def test_execute_query_returns_results():
    """Test that execute_query returns structured results from a SELECT query."""
    fake_cursor = AsyncMock()
    fake_cursor.description = [('id',), ('name',)]
    fake_cursor.fetchall = AsyncMock(return_value=[(1, 'Alice'), (2, 'Bob')])

    fake_conn = AsyncMock()
    fake_conn.cursor = MagicMock(return_value=AsyncContextManagerMock(fake_cursor))

    fake_pool = AsyncMock()
    fake_pool.acquire = MagicMock(return_value=AsyncContextManagerMock(fake_conn))

    with patch(
        'awslabs.mysql_mcp_server.connection.asyncmy_pool_connection._get_credentials_from_secret',
        return_value=('user', 'pass'),
    ):
        conn = AsyncmyPoolConnection(
            hostname='localhost',
            port=int(3306),
            database='testdb',
            readonly=False,
            secret_arn='arn:test',
            region='us-east-1',
        )
        conn.pool = fake_pool
        result = await conn.execute_query('SELECT id, name FROM users')

        assert result['columnMetadata'] == [{'label': 'id'}, {'label': 'name'}]
        assert result['records'] == [
            [{'longValue': 1}, {'stringValue': 'Alice'}],
            [{'longValue': 2}, {'stringValue': 'Bob'}],
        ]


@pytest.mark.asyncio
async def test_readonly_mode_set():
    """Test that _set_all_connections_readonly executes the correct SQL command."""
    fake_cursor = AsyncMock()
    fake_cursor.description = None
    fake_cursor.execute = AsyncMock()

    fake_conn = AsyncMock()
    fake_conn.cursor = MagicMock(return_value=AsyncContextManagerMock(fake_cursor))

    fake_pool = AsyncMock()
    fake_pool.acquire = MagicMock(return_value=AsyncContextManagerMock(fake_conn))

    with patch(
        'awslabs.mysql_mcp_server.connection.asyncmy_pool_connection._get_credentials_from_secret',
        return_value=('user', 'pass'),
    ):
        conn = AsyncmyPoolConnection(
            hostname='localhost',
            port=3306,
            database='testdb',
            readonly=True,
            secret_arn='arn:test',
            region='us-east-1',
        )
        conn.pool = fake_pool
        await conn._set_all_connections_readonly()

        fake_cursor.execute.assert_awaited_with('SET SESSION TRANSACTION READ ONLY;')


@pytest.mark.asyncio
async def test_check_connection_health_returns_true():
    """Test that check_connection_health returns True for a healthy connection."""
    with patch(
        'awslabs.mysql_mcp_server.connection.asyncmy_pool_connection._get_credentials_from_secret',
        return_value=('user', 'pass'),
    ):
        conn = AsyncmyPoolConnection(
            hostname='localhost',
            port=3306,
            database='testdb',
            readonly=False,
            secret_arn='arn:test',
            region='us-east-1',
        )
        # Mock execute_query to simulate a healthy connection
        conn.execute_query = AsyncMock(return_value={'records': [[{'longValue': 1}]]})
        assert await conn.check_connection_health() is True


@pytest.mark.asyncio
async def test_get_connection_pool_none_raises():
    """Test that _get_connection raises ValueError if pool initialization fails."""
    with patch(
        'awslabs.mysql_mcp_server.connection.asyncmy_pool_connection._get_credentials_from_secret',
        return_value=('user', 'pass'),
    ):
        conn = AsyncmyPoolConnection(
            hostname='localhost',
            port=3306,
            database='testdb',
            readonly=False,
            secret_arn='arn:test',
            region='us-east-1',
        )
        conn.pool = None
        # Force initialize_pool to fail by patching it
        conn.initialize_pool = AsyncMock(return_value=None)
        with pytest.raises(ValueError, match='Failed to initialize connection pool'):
            await conn._get_connection()


@pytest.mark.asyncio
async def test_execute_query_with_parameters_and_exception():
    """Test that execute_query raises exceptions when cursor.execute fails."""
    fake_cursor = AsyncMock()
    fake_cursor.description = [('id',)]
    fake_cursor.execute = AsyncMock(side_effect=Exception('db fail'))
    fake_conn = AsyncMock()
    fake_conn.cursor = MagicMock(return_value=AsyncContextManagerMock(fake_cursor))
    fake_pool = AsyncMock()
    fake_pool.acquire = MagicMock(return_value=AsyncContextManagerMock(fake_conn))

    with patch(
        'awslabs.mysql_mcp_server.connection.asyncmy_pool_connection._get_credentials_from_secret',
        return_value=('user', 'pass'),
    ):
        conn = AsyncmyPoolConnection(
            hostname='localhost',
            port=3306,
            database='testdb',
            readonly=False,
            secret_arn='arn:test',
            region='us-east-1',
        )
        conn.pool = fake_pool
        with pytest.raises(Exception, match='db fail'):
            await conn.execute_query(
                'SELECT * FROM table WHERE id=%(id)s',
                parameters=[{'name': 'id', 'value': {'longValue': 5}}],
            )


@pytest.mark.asyncio
async def test_close_closes_pool():
    """Test that close properly closes the connection pool and resets pool to None."""
    fake_pool = AsyncMock()
    fake_pool.close = AsyncMock()
    with patch(
        'awslabs.mysql_mcp_server.connection.asyncmy_pool_connection._get_credentials_from_secret',
        return_value=('user', 'pass'),
    ):
        conn = AsyncmyPoolConnection(
            hostname='localhost',
            port=3306,
            database='testdb',
            readonly=False,
            secret_arn='arn:test',
            region='us-east-1',
        )
        conn.pool = fake_pool
        await conn.close()
        fake_pool.close.assert_awaited()
        assert conn.pool is None


def test_get_credentials_from_secret():
    """Test that _get_credentials_from_secret returns correct username and password from AWS Secrets Manager."""
    mock_client = MagicMock()
    mock_client.get_secret_value.return_value = {
        'SecretString': '{"username": "testuser", "password": "testpass"}'
    }

    with patch(
        'awslabs.mysql_mcp_server.connection.asyncmy_pool_connection.boto3.Session'
    ) as mock_session:
        mock_session.return_value.client.return_value = mock_client
        username, password = _get_credentials_from_secret(
            'arn:test',
            'us-east-1',
        )
        assert username == 'testuser'
        assert password == 'testpass'


@pytest.mark.asyncio
async def test_initialize_pool_calls_set_readonly_when_flag_true():
    """initialize_pool triggers _set_all_connections_readonly when readonly=True."""
    with (
        patch(
            'awslabs.mysql_mcp_server.connection.asyncmy_pool_connection.create_pool',
            new_callable=AsyncMock,
        ) as mock_create_pool,
        patch(
            'awslabs.mysql_mcp_server.connection.asyncmy_pool_connection._get_credentials_from_secret',
            return_value=('user', 'pass'),
        ),
    ):
        mock_pool = AsyncMock()
        mock_create_pool.return_value = mock_pool
        conn = AsyncmyPoolConnection(
            hostname='localhost',
            port=3306,
            database='db',
            readonly=True,
            secret_arn='arn:test',
            region='us-east-1',
        )
        conn._set_all_connections_readonly = AsyncMock()
        await conn.initialize_pool()
        conn._set_all_connections_readonly.assert_awaited_once()


@pytest.mark.asyncio
async def test_set_all_connections_readonly_no_pool_returns():
    """_set_all_connections_readonly returns early when pool is None."""
    with patch(
        'awslabs.mysql_mcp_server.connection.asyncmy_pool_connection._get_credentials_from_secret',
        return_value=('user', 'pass'),
    ):
        conn = AsyncmyPoolConnection(
            hostname='h',
            port=3306,
            database='db',
            readonly=True,
            secret_arn='arn:test',
            region='us-east-1',
        )
        conn.pool = None
        await conn._set_all_connections_readonly()  # should not raise


@pytest.mark.asyncio
async def test_set_all_connections_readonly_handles_exception():
    """_set_all_connections_readonly swallows exceptions and continues."""
    fake_cursor = AsyncMock()
    fake_cursor.execute = AsyncMock(side_effect=Exception('readonly fail'))
    fake_conn = AsyncMock()
    fake_conn.cursor = MagicMock(return_value=AsyncContextManagerMock(fake_cursor))
    fake_pool = AsyncMock()
    fake_pool.acquire = MagicMock(return_value=AsyncContextManagerMock(fake_conn))

    with patch(
        'awslabs.mysql_mcp_server.connection.asyncmy_pool_connection._get_credentials_from_secret',
        return_value=('user', 'pass'),
    ):
        conn = AsyncmyPoolConnection(
            hostname='h',
            port=3306,
            database='db',
            readonly=True,
            secret_arn='arn:test',
            region='us-east-1',
        )
        conn.pool = fake_pool
        await conn._set_all_connections_readonly()
        fake_cursor.execute.assert_awaited()


@pytest.mark.asyncio
async def test_get_connection_initializes_and_returns_acquire_callable():
    """_get_connection initializes pool and returns the acquire context manager."""
    with (
        patch(
            'awslabs.mysql_mcp_server.connection.asyncmy_pool_connection.create_pool',
            new_callable=AsyncMock,
        ) as mock_create_pool,
        patch(
            'awslabs.mysql_mcp_server.connection.asyncmy_pool_connection._get_credentials_from_secret',
            return_value=('user', 'pass'),
        ),
    ):
        fake_pool = AsyncMock()
        # Return a concrete async context manager instance to avoid coroutine comparison
        acquire_cm = AsyncContextManagerMock('conn')
        fake_pool.acquire = MagicMock(return_value=acquire_cm)
        mock_create_pool.return_value = fake_pool

        conn = AsyncmyPoolConnection(
            hostname='h',
            port=3306,
            database='db',
            readonly=False,
            secret_arn='arn:test',
            region='us-east-1',
        )
        result = await conn._get_connection()
        assert result is acquire_cm  # exact object returned


async def test_execute_query_readonly_and_parameter_types_mapped_boolean_as_long():
    """execute_query maps bool via int branch (bool is subclass of int)."""

    class Odd:
        def __str__(self):
            return 'ODD'

    row = (None, 's', 7, 3.14, True, b'bin', Odd())
    fake_cursor = AsyncMock()
    fake_cursor.description = [('n',), ('s',), ('i',), ('f',), ('b',), ('blob',), ('odd',)]
    fake_cursor.fetchall = AsyncMock(return_value=[row])
    fake_cursor.execute = AsyncMock()

    fake_conn = AsyncMock()
    fake_conn.cursor = MagicMock(return_value=AsyncContextManagerMock(fake_cursor))

    fake_pool = AsyncMock()
    fake_pool.acquire = MagicMock(return_value=AsyncContextManagerMock(fake_conn))

    with patch(
        'awslabs.mysql_mcp_server.connection.asyncmy_pool_connection._get_credentials_from_secret',
        return_value=('user', 'pass'),
    ):
        conn = AsyncmyPoolConnection(
            hostname='h',
            port=3306,
            database='db',
            readonly=True,
            secret_arn='arn:test',
            region='us-east-1',
        )
        conn.pool = fake_pool

        params = [
            {'name': 'p1', 'value': {'stringValue': 'a'}},
            {'name': 'p2', 'value': {'longValue': 1}},
            {'name': 'p3', 'value': {'doubleValue': 2.5}},
            {'name': 'p4', 'value': {'booleanValue': False}},
            {'name': 'p5', 'value': {'blobValue': b'x'}},
            {'name': 'p6', 'value': {'isNull': True}},
        ]
        result = await conn.execute_query('SELECT * FROM t WHERE a=%s', parameters=params)

        fake_cursor.execute.assert_any_await('SET TRANSACTION READ ONLY')
        assert result['columnMetadata'] == [
            {'label': 'n'},
            {'label': 's'},
            {'label': 'i'},
            {'label': 'f'},
            {'label': 'b'},
            {'label': 'blob'},
            {'label': 'odd'},
        ]
        # Note: bool mapped via int branch -> {'longValue': True}
        assert result['records'] == [
            [
                {'isNull': True},
                {'stringValue': 's'},
                {'longValue': 7},
                {'doubleValue': 3.14},
                {'longValue': True},
                {'blobValue': b'bin'},
                {'stringValue': 'ODD'},
            ]
        ]


@pytest.mark.asyncio
async def test_execute_query_no_results_branch():
    """execute_query returns empty result when cursor.description is falsy."""
    fake_cursor = AsyncMock()
    fake_cursor.description = None
    fake_cursor.execute = AsyncMock()

    fake_conn = AsyncMock()
    fake_conn.cursor = MagicMock(return_value=AsyncContextManagerMock(fake_cursor))
    fake_pool = AsyncMock()
    fake_pool.acquire = MagicMock(return_value=AsyncContextManagerMock(fake_conn))

    with patch(
        'awslabs.mysql_mcp_server.connection.asyncmy_pool_connection._get_credentials_from_secret',
        return_value=('user', 'pass'),
    ):
        conn = AsyncmyPoolConnection(
            hostname='h',
            port=3306,
            database='db',
            readonly=False,
            secret_arn='arn:test',
            region='us-east-1',
        )
        conn.pool = fake_pool
        result = await conn.execute_query('UPDATE t SET a=1')
        assert result == {'columnMetadata': [], 'records': []}


@pytest.mark.asyncio
async def test_check_connection_health_returns_false_on_exception():
    """check_connection_health returns False when execute_query raises."""
    with patch(
        'awslabs.mysql_mcp_server.connection.asyncmy_pool_connection._get_credentials_from_secret',
        return_value=('user', 'pass'),
    ):
        conn = AsyncmyPoolConnection(
            hostname='h',
            port=3306,
            database='db',
            readonly=False,
            secret_arn='arn:test',
            region='us-east-1',
        )
        conn.execute_query = AsyncMock(side_effect=Exception('boom'))
        assert await conn.check_connection_health() is False


def test_get_credentials_from_secret_missing_username_raises():
    """_get_credentials_from_secret raises when username missing."""
    mock_client = MagicMock()
    secret = {'password': 'p'}
    mock_client.get_secret_value.return_value = {'SecretString': json.dumps(secret)}
    with patch(
        'awslabs.mysql_mcp_server.connection.asyncmy_pool_connection.boto3.Session'
    ) as mock_session:
        mock_session.return_value.client.return_value = mock_client
        with pytest.raises(ValueError, match='does not contain username'):
            _get_credentials_from_secret('arn:test', 'us-east-1')


def test_get_credentials_from_secret_missing_password_raises():
    """_get_credentials_from_secret raises when password missing."""
    mock_client = MagicMock()
    secret = {'username': 'u'}
    mock_client.get_secret_value.return_value = {'SecretString': json.dumps(secret)}
    with patch(
        'awslabs.mysql_mcp_server.connection.asyncmy_pool_connection.boto3.Session'
    ) as mock_session:
        mock_session.return_value.client.return_value = mock_client
        with pytest.raises(ValueError, match='does not contain password'):
            _get_credentials_from_secret('arn:test', 'us-east-1')


def test_get_credentials_from_secret_no_secret_string_raises():
    """_get_credentials_from_secret raises when SecretString missing."""
    mock_client = MagicMock()
    mock_client.get_secret_value.return_value = {}
    with patch(
        'awslabs.mysql_mcp_server.connection.asyncmy_pool_connection.boto3.Session'
    ) as mock_session:
        mock_session.return_value.client.return_value = mock_client
        with pytest.raises(ValueError, match='Secret does not contain a SecretString'):
            _get_credentials_from_secret('arn:test', 'us-east-1')


def test_get_credentials_from_secret_boto_exception_wrapped():
    """_get_credentials_from_secret wraps boto exceptions into ValueError."""
    with patch(
        'awslabs.mysql_mcp_server.connection.asyncmy_pool_connection.boto3.Session'
    ) as mock_session:
        mock_session.return_value.client.side_effect = Exception('boto error')
        with pytest.raises(ValueError, match='Failed to retrieve credentials'):
            _get_credentials_from_secret('arn:test', 'us-east-1')
