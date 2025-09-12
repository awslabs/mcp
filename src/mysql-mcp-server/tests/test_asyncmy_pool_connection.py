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
    with patch('awslabs.mysql_mcp_server.connection.asyncmy_pool_connection.create_pool', new_callable=AsyncMock) as mock_create_pool, \
         patch('awslabs.mysql_mcp_server.connection.asyncmy_pool_connection._get_credentials_from_secret', return_value=('user', 'pass')):
        conn = AsyncmyPoolConnection(
            hostname='localhost',
            port=3306,
            database='testdb',
            readonly=False,
            secret_arn='arn:test', # pragma: allowlist secret
            region='us-east-1'
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

    with patch('awslabs.mysql_mcp_server.connection.asyncmy_pool_connection._get_credentials_from_secret', return_value=('user', 'pass')):
        conn = AsyncmyPoolConnection(
            hostname='localhost',
            port=int(3306),
            database='testdb',
            readonly=False,
            secret_arn='arn:test', # pragma: allowlist secret
            region='us-east-1'
        )
        conn.pool = fake_pool
        result = await conn.execute_query('SELECT id, name FROM users')

        assert result['columnMetadata'] == [{'name': 'id'}, {'name': 'name'}]
        assert result['records'] == [
            [{'longValue': 1}, {'stringValue': 'Alice'}],
            [{'longValue': 2}, {'stringValue': 'Bob'}]
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

    with patch('awslabs.mysql_mcp_server.connection.asyncmy_pool_connection._get_credentials_from_secret', return_value=('user', 'pass')):
        conn = AsyncmyPoolConnection(
            hostname='localhost',
            port=3306,
            database='testdb',
            readonly=True,
            secret_arn='arn:test', # pragma: allowlist secret
            region='us-east-1'
        )
        conn.pool = fake_pool
        await conn._set_all_connections_readonly()

        fake_cursor.execute.assert_awaited_with('SET SESSION TRANSACTION READ ONLY;')


@pytest.mark.asyncio
async def test_check_connection_health_returns_true():
    """Test that check_connection_health returns True for a healthy connection."""
    with patch('awslabs.mysql_mcp_server.connection.asyncmy_pool_connection._get_credentials_from_secret', return_value=('user', 'pass')):
        conn = AsyncmyPoolConnection(
            hostname='localhost',
            port=3306,
            database='testdb',
            readonly=False,
            secret_arn='arn:test', # pragma: allowlist secret
            region='us-east-1'
        )
        # Mock execute_query to simulate a healthy connection
        conn.execute_query = AsyncMock(return_value={'records': [[{'longValue': 1}]]})
        assert await conn.check_connection_health() is True


@pytest.mark.asyncio
async def test_get_connection_pool_none_raises():
    """Test that _get_connection raises ValueError if pool initialization fails."""
    with patch('awslabs.mysql_mcp_server.connection.asyncmy_pool_connection._get_credentials_from_secret', return_value=('user', 'pass')):
        conn = AsyncmyPoolConnection(
            hostname='localhost', port=3306, database='testdb',
            readonly=False, secret_arn='arn:test', region='us-east-1' # pragma: allowlist secret
        )
        conn.pool = None
        # Force initialize_pool to fail by patching it
        conn.initialize_pool = AsyncMock(return_value=None)
        with pytest.raises(ValueError, match="Failed to initialize connection pool"):
            await conn._get_connection()


@pytest.mark.asyncio
async def test_execute_query_with_parameters_and_exception():
    """Test that execute_query raises exceptions when cursor.execute fails."""
    fake_cursor = AsyncMock()
    fake_cursor.description = [('id',)]
    fake_cursor.execute = AsyncMock(side_effect=Exception("db fail"))
    fake_conn = AsyncMock()
    fake_conn.cursor = MagicMock(return_value=AsyncContextManagerMock(fake_cursor))
    fake_pool = AsyncMock()
    fake_pool.acquire = MagicMock(return_value=AsyncContextManagerMock(fake_conn))

    with patch('awslabs.mysql_mcp_server.connection.asyncmy_pool_connection._get_credentials_from_secret', return_value=('user', 'pass')):
        conn = AsyncmyPoolConnection(
            hostname='localhost', port=3306, database='testdb',
            readonly=False, secret_arn='arn:test', region='us-east-1' # pragma: allowlist secret
        )
        conn.pool = fake_pool
        with pytest.raises(Exception, match="db fail"):
            await conn.execute_query(
                'SELECT * FROM table WHERE id=%(id)s',
                parameters=[{'name': 'id', 'value': {'longValue': 5}}]
            )


@pytest.mark.asyncio
async def test_close_closes_pool():
    """Test that close properly closes the connection pool and resets pool to None."""
    fake_pool = AsyncMock()
    fake_pool.close = AsyncMock()
    with patch('awslabs.mysql_mcp_server.connection.asyncmy_pool_connection._get_credentials_from_secret', return_value=('user', 'pass')):
        conn = AsyncmyPoolConnection(
            hostname='localhost', port=3306, database='testdb',
            readonly=False, secret_arn='arn:test', region='us-east-1' # pragma: allowlist secret
        )
        conn.pool = fake_pool
        await conn.close()
        fake_pool.close.assert_awaited()
        assert conn.pool is None


def test_get_credentials_from_secret():
    """Test that _get_credentials_from_secret returns correct username and password from AWS Secrets Manager."""
    mock_client = MagicMock()
    mock_client.get_secret_value.return_value = {'SecretString': '{"username": "testuser", "password": "testpass"}'} # pragma: allowlist secret

    with patch('awslabs.mysql_mcp_server.connection.asyncmy_pool_connection.boto3.Session') as mock_session:
        mock_session.return_value.client.return_value = mock_client
        username, password = _get_credentials_from_secret('arn:test', 'us-east-1')
        assert username == 'testuser'
        assert password == 'testpass' # pragma: allowlist secret
