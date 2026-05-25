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

"""Tests for AsyncmyPoolConnection with mocked asyncmy."""

import pytest
from awslabs.mysql_mcp_server.connection.asyncmy_pool_connection import AsyncmyPoolConnection
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch


def _async_return(value):
    """Create a coroutine function that returns the given value (for patching async functions)."""

    async def _coro(*args, **kwargs):
        return value

    return _coro


class TestAsyncmyPoolConnectionInit:
    """Tests for AsyncmyPoolConnection initialization."""

    def test_basic_init(self):
        """Should initialize with basic parameters."""
        conn = AsyncmyPoolConnection(
            host='localhost',
            port=3306,
            database='testdb',
            readonly=True,
            secret_arn='arn:aws:secretsmanager:us-east-1:123456789012:secret:test',
            db_user='',
            region='us-east-1',
            is_iam_auth=False,
            is_test=True,
        )
        assert conn.host == 'localhost'
        assert conn.port == 3306
        assert conn.database == 'testdb'
        assert conn.readonly_query is True
        assert conn.is_iam_auth is False
        assert conn.pool is None

    def test_iam_auth_init(self):
        """Should initialize with IAM auth and set pool_expiry_min to 14."""
        conn = AsyncmyPoolConnection(
            host='mydb.cluster-xyz.us-east-1.rds.amazonaws.com',
            port=3306,
            database='testdb',
            readonly=False,
            secret_arn='',
            db_user='admin',
            region='us-east-1',
            is_iam_auth=True,
            is_test=True,
        )
        assert conn.is_iam_auth is True
        assert conn.pool_expiry_min == 14
        assert conn.user == 'admin'

    def test_iam_auth_requires_db_user(self):
        """Should raise ValueError if is_iam_auth=True but db_user is empty."""
        with pytest.raises(ValueError, match='db_user must be set when is_iam_auth is True'):
            AsyncmyPoolConnection(
                host='localhost',
                port=3306,
                database='testdb',
                readonly=True,
                secret_arn='',
                db_user='',
                region='us-east-1',
                is_iam_auth=True,
                is_test=True,
            )

    def test_custom_pool_sizes(self):
        """Should accept custom min_size and max_size."""
        conn = AsyncmyPoolConnection(
            host='localhost',
            port=3306,
            database='testdb',
            readonly=True,
            secret_arn='arn:secret',
            db_user='',
            region='us-east-1',
            is_iam_auth=False,
            min_size=2,
            max_size=20,
            is_test=True,
        )
        assert conn.min_size == 2
        assert conn.max_size == 20

    def test_default_port_3306(self):
        """Default port should be 3306."""
        conn = AsyncmyPoolConnection(
            host='localhost',
            port=3306,
            database='testdb',
            readonly=True,
            secret_arn='arn:secret',
            db_user='',
            region='us-east-1',
            is_test=True,
        )
        assert conn.port == 3306


class TestAsyncmyPoolConnectionInitializePool:
    """Tests for pool initialization."""

    @patch(
        'awslabs.mysql_mcp_server.connection.asyncmy_pool_connection.asyncmy.create_pool',
        new_callable=AsyncMock,
    )
    async def test_initialize_pool_with_secret(self, mock_create_pool):
        """Should initialize pool using credentials from Secrets Manager."""
        mock_pool = MagicMock()
        mock_create_pool.return_value = mock_pool

        conn = AsyncmyPoolConnection(
            host='localhost',
            port=3306,
            database='testdb',
            readonly=True,
            secret_arn='arn:secret',
            db_user='',
            region='us-east-1',
            is_iam_auth=False,
            is_test=True,
        )

        await conn.initialize_pool()

        mock_create_pool.assert_called_once()
        call_kwargs = mock_create_pool.call_args[1]
        assert call_kwargs['host'] == 'localhost'
        assert call_kwargs['port'] == 3306
        assert call_kwargs['db'] == 'testdb'
        assert call_kwargs['user'] == 'test_user'
        assert call_kwargs['password'] == 'test_password'
        assert call_kwargs['ssl'] is None
        assert conn.pool is mock_pool

    @patch(
        'awslabs.mysql_mcp_server.connection.asyncmy_pool_connection.asyncmy.create_pool',
        new_callable=AsyncMock,
    )
    @patch('awslabs.mysql_mcp_server.connection.asyncmy_pool_connection.boto3.client')
    async def test_initialize_pool_with_iam(self, mock_boto_client, mock_create_pool):
        """Should initialize pool using IAM auth token."""
        mock_pool = MagicMock()
        mock_create_pool.return_value = mock_pool

        mock_rds = MagicMock()
        mock_rds.generate_db_auth_token.return_value = 'iam-token-123'
        mock_boto_client.return_value = mock_rds

        conn = AsyncmyPoolConnection(
            host='mydb.cluster-xyz.us-east-1.rds.amazonaws.com',
            port=3306,
            database='testdb',
            readonly=True,
            secret_arn='',
            db_user='admin',
            region='us-east-1',
            is_iam_auth=True,
            is_test=True,
        )

        await conn.initialize_pool()

        mock_create_pool.assert_called_once()
        call_kwargs = mock_create_pool.call_args[1]
        assert call_kwargs['password'] == 'iam-token-123'
        assert call_kwargs['user'] == 'admin'
        assert call_kwargs['ssl'] is not None  # SSL context for IAM

    @patch(
        'awslabs.mysql_mcp_server.connection.asyncmy_pool_connection.asyncmy.create_pool',
        new_callable=AsyncMock,
    )
    async def test_initialize_pool_idempotent(self, mock_create_pool):
        """Calling initialize_pool twice should only create pool once."""
        mock_pool = MagicMock()
        mock_create_pool.return_value = mock_pool

        conn = AsyncmyPoolConnection(
            host='localhost',
            port=3306,
            database='testdb',
            readonly=True,
            secret_arn='arn:secret',
            db_user='',
            region='us-east-1',
            is_iam_auth=False,
            is_test=True,
        )

        await conn.initialize_pool()
        await conn.initialize_pool()

        mock_create_pool.assert_called_once()


class TestAsyncmyPoolConnectionExecuteQuery:
    """Tests for query execution."""

    def _make_conn_with_pool(self):
        """Create a connection with a mocked pool."""
        conn = AsyncmyPoolConnection(
            host='localhost',
            port=3306,
            database='testdb',
            readonly=False,
            secret_arn='arn:secret',
            db_user='',
            region='us-east-1',
            is_iam_auth=False,
            is_test=True,
        )
        return conn

    @patch(
        'awslabs.mysql_mcp_server.connection.asyncmy_pool_connection.asyncmy.create_pool',
        new_callable=AsyncMock,
    )
    async def test_execute_query_simple(self, mock_create_pool):
        """Should execute a simple query and return structured results."""
        # Set up mock cursor
        mock_cursor = MagicMock()
        mock_cursor.description = [('id',), ('name',)]
        mock_cursor.fetchall = AsyncMock(
            return_value=[{'id': 1, 'name': 'Alice'}, {'id': 2, 'name': 'Bob'}]
        )
        mock_cursor.execute = AsyncMock()

        # Set up mock connection with proper cursor context managers
        mock_conn = MagicMock()

        def cursor_side_effect(*args, **kwargs):
            cm = MagicMock()
            cm.__aenter__ = AsyncMock(return_value=mock_cursor)
            cm.__aexit__ = AsyncMock(return_value=False)
            return cm

        mock_conn.cursor = MagicMock(side_effect=cursor_side_effect)

        # Set up mock pool with proper acquire context manager
        mock_pool = MagicMock()
        acquire_cm = MagicMock()
        acquire_cm.__aenter__ = AsyncMock(return_value=mock_conn)
        acquire_cm.__aexit__ = AsyncMock(return_value=False)
        mock_pool.acquire.return_value = acquire_cm
        mock_create_pool.return_value = mock_pool

        conn = self._make_conn_with_pool()
        await conn.initialize_pool()

        result = await conn.execute_query('SELECT id, name FROM users')

        assert 'columnMetadata' in result
        assert 'records' in result

    @patch(
        'awslabs.mysql_mcp_server.connection.asyncmy_pool_connection.asyncmy.create_pool',
        new_callable=AsyncMock,
    )
    async def test_execute_query_readonly_sets_transaction(self, mock_create_pool):
        """Should start a read-only transaction when readonly is True."""
        mock_readonly_cursor = AsyncMock()
        mock_readonly_cursor.execute = AsyncMock()

        mock_dict_cursor = AsyncMock()
        mock_dict_cursor.description = None
        mock_dict_cursor.fetchall = AsyncMock(return_value=[])

        mock_conn = AsyncMock()
        mock_conn.autocommit = AsyncMock()
        mock_conn.rollback = AsyncMock()

        # Track cursor calls
        cursor_calls = []

        def cursor_side_effect(*args, **kwargs):
            cm = AsyncMock()
            if 'cursor' in kwargs:
                cm.__aenter__ = AsyncMock(return_value=mock_dict_cursor)
            else:
                cm.__aenter__ = AsyncMock(return_value=mock_readonly_cursor)
            cm.__aexit__ = AsyncMock(return_value=False)
            cursor_calls.append(kwargs)
            return cm

        mock_conn.cursor = MagicMock(side_effect=cursor_side_effect)

        mock_pool = MagicMock()
        mock_pool.acquire.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_pool.acquire.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_create_pool.return_value = mock_pool

        conn = AsyncmyPoolConnection(
            host='localhost',
            port=3306,
            database='testdb',
            readonly=True,
            secret_arn='arn:secret',
            db_user='',
            region='us-east-1',
            is_iam_auth=False,
            is_test=True,
        )
        await conn.initialize_pool()

        await conn.execute_query('SELECT 1')

        # Should have disabled autocommit and started read-only transaction
        mock_conn.autocommit.assert_any_call(False)
        calls = mock_readonly_cursor.execute.call_args_list
        assert any('SET TRANSACTION READ ONLY' in str(c) for c in calls)
        assert any('START TRANSACTION' in str(c) for c in calls)
        # Should rollback and re-enable autocommit after query (in finally block)
        mock_conn.rollback.assert_called_once()
        mock_conn.autocommit.assert_any_call(True)

    @patch(
        'awslabs.mysql_mcp_server.connection.asyncmy_pool_connection.asyncmy.create_pool',
        new_callable=AsyncMock,
    )
    async def test_execute_query_raises_without_pool(self, mock_create_pool):
        """Should raise ValueError if pool is not initialized."""
        # Make create_pool return None to simulate failed initialization
        mock_create_pool.return_value = None

        conn = AsyncmyPoolConnection(
            host='localhost',
            port=3306,
            database='testdb',
            readonly=True,
            secret_arn='arn:secret',
            db_user='',
            region='us-east-1',
            is_iam_auth=False,
            is_test=True,
        )
        # Pool will be None after initialize_pool sets it to None
        # _get_connection checks pool is None and raises
        with pytest.raises(ValueError, match='Failed to initialize connection pool'):
            await conn.execute_query('SELECT 1')


class TestAsyncmyPoolConnectionParameterConversion:
    """Tests for parameter conversion methods."""

    def _make_conn(self):
        return AsyncmyPoolConnection(
            host='localhost',
            port=3306,
            database='testdb',
            readonly=True,
            secret_arn='arn:secret',
            db_user='',
            region='us-east-1',
            is_iam_auth=False,
            is_test=True,
        )

    def test_convert_parameters_string(self):
        """Should convert stringValue parameters."""
        conn = self._make_conn()
        params = [{'name': 'col', 'value': {'stringValue': 'hello'}}]
        result = conn._convert_parameters(params)
        assert result == {'col': 'hello'}

    def test_convert_parameters_long(self):
        """Should convert longValue parameters."""
        conn = self._make_conn()
        params = [{'name': 'id', 'value': {'longValue': 42}}]
        result = conn._convert_parameters(params)
        assert result == {'id': 42}

    def test_convert_parameters_double(self):
        """Should convert doubleValue parameters."""
        conn = self._make_conn()
        params = [{'name': 'price', 'value': {'doubleValue': 9.99}}]
        result = conn._convert_parameters(params)
        assert result == {'price': 9.99}

    def test_convert_parameters_boolean(self):
        """Should convert booleanValue parameters."""
        conn = self._make_conn()
        params = [{'name': 'active', 'value': {'booleanValue': True}}]
        result = conn._convert_parameters(params)
        assert result == {'active': True}

    def test_convert_parameters_blob(self):
        """Should convert blobValue parameters."""
        conn = self._make_conn()
        params = [{'name': 'data', 'value': {'blobValue': b'\x00\x01'}}]
        result = conn._convert_parameters(params)
        assert result == {'data': b'\x00\x01'}

    def test_convert_parameters_null(self):
        """Should convert isNull parameters to None."""
        conn = self._make_conn()
        params = [{'name': 'val', 'value': {'isNull': True}}]
        result = conn._convert_parameters(params)
        assert result == {'val': None}

    def test_convert_parameters_multiple(self):
        """Should convert multiple parameters."""
        conn = self._make_conn()
        params = [
            {'name': 'name', 'value': {'stringValue': 'Alice'}},
            {'name': 'age', 'value': {'longValue': 30}},
        ]
        result = conn._convert_parameters(params)
        assert result == {'name': 'Alice', 'age': 30}


class TestAsyncmyPoolConnectionNamedToPositional:
    """Tests for named-to-positional SQL conversion."""

    def _make_conn(self):
        return AsyncmyPoolConnection(
            host='localhost',
            port=3306,
            database='testdb',
            readonly=True,
            secret_arn='arn:secret',
            db_user='',
            region='us-east-1',
            is_iam_auth=False,
            is_test=True,
        )

    def test_single_param(self):
        """Should convert a single named parameter."""
        conn = self._make_conn()
        sql = 'SELECT * FROM t WHERE id = %(id)s'
        params = {'id': 42}
        converted_sql, positional = conn._convert_named_to_positional(sql, params)
        assert converted_sql == 'SELECT * FROM t WHERE id = %s'
        assert positional == [42]

    def test_multiple_params(self):
        """Should convert multiple named parameters in order."""
        conn = self._make_conn()
        sql = 'SELECT * FROM t WHERE name = %(name)s AND age = %(age)s'
        params = {'name': 'Alice', 'age': 30}
        converted_sql, positional = conn._convert_named_to_positional(sql, params)
        assert converted_sql == 'SELECT * FROM t WHERE name = %s AND age = %s'
        assert positional == ['Alice', 30]

    def test_repeated_param(self):
        """Should handle the same parameter used multiple times."""
        conn = self._make_conn()
        sql = 'SELECT * FROM t WHERE a = %(val)s OR b = %(val)s'
        params = {'val': 'x'}
        converted_sql, positional = conn._convert_named_to_positional(sql, params)
        assert converted_sql == 'SELECT * FROM t WHERE a = %s OR b = %s'
        assert positional == ['x', 'x']

    def test_no_params(self):
        """Should return SQL unchanged if no named parameters."""
        conn = self._make_conn()
        sql = 'SELECT 1'
        params = {}
        converted_sql, positional = conn._convert_named_to_positional(sql, params)
        assert converted_sql == 'SELECT 1'
        assert positional == []

    def test_missing_param_returns_none(self):
        """Should return None for missing parameter keys."""
        conn = self._make_conn()
        sql = 'SELECT * FROM t WHERE id = %(missing)s'
        params = {}
        converted_sql, positional = conn._convert_named_to_positional(sql, params)
        assert converted_sql == 'SELECT * FROM t WHERE id = %s'
        assert positional == [None]


class TestAsyncmyPoolConnectionClose:
    """Tests for pool close."""

    @patch(
        'awslabs.mysql_mcp_server.connection.asyncmy_pool_connection.asyncmy.create_pool',
        new_callable=AsyncMock,
    )
    async def test_close_pool(self, mock_create_pool):
        """Should close the pool and set it to None."""
        mock_pool = MagicMock()
        mock_pool.close = MagicMock()
        mock_pool.wait_closed = AsyncMock()
        mock_create_pool.return_value = mock_pool

        conn = AsyncmyPoolConnection(
            host='localhost',
            port=3306,
            database='testdb',
            readonly=True,
            secret_arn='arn:secret',
            db_user='',
            region='us-east-1',
            is_iam_auth=False,
            is_test=True,
        )
        await conn.initialize_pool()
        assert conn.pool is not None

        await conn.close()
        mock_pool.close.assert_called_once()
        mock_pool.wait_closed.assert_called_once()
        assert conn.pool is None

    async def test_close_when_no_pool(self):
        """Should not raise when pool is already None."""
        conn = AsyncmyPoolConnection(
            host='localhost',
            port=3306,
            database='testdb',
            readonly=True,
            secret_arn='arn:secret',
            db_user='',
            region='us-east-1',
            is_iam_auth=False,
            is_test=True,
        )
        await conn.close()  # Should not raise


class TestAsyncmyPoolConnectionPoolStats:
    """Tests for pool statistics."""

    async def test_pool_stats_no_pool(self):
        """Should return default stats when pool is None."""
        conn = AsyncmyPoolConnection(
            host='localhost',
            port=3306,
            database='testdb',
            readonly=True,
            secret_arn='arn:secret',
            db_user='',
            region='us-east-1',
            is_iam_auth=False,
            is_test=True,
        )
        stats = await conn.get_pool_stats()
        assert stats['size'] == 0
        assert stats['min_size'] == 1
        assert stats['max_size'] == 10
        assert stats['idle'] == 0

    @patch(
        'awslabs.mysql_mcp_server.connection.asyncmy_pool_connection.asyncmy.create_pool',
        new_callable=AsyncMock,
    )
    async def test_pool_stats_with_pool(self, mock_create_pool):
        """Should return pool stats when pool exists."""
        mock_pool = MagicMock()
        mock_pool.size = 5
        mock_pool.minsize = 1
        mock_pool.maxsize = 10
        mock_pool.freesize = 3
        mock_create_pool.return_value = mock_pool

        conn = AsyncmyPoolConnection(
            host='localhost',
            port=3306,
            database='testdb',
            readonly=True,
            secret_arn='arn:secret',
            db_user='',
            region='us-east-1',
            is_iam_auth=False,
            is_test=True,
        )
        await conn.initialize_pool()

        stats = await conn.get_pool_stats()
        assert stats['size'] == 5
        assert stats['min_size'] == 1
        assert stats['max_size'] == 10
        assert stats['idle'] == 3


class TestAsyncmyPoolConnectionCheckExpiry:
    """Tests for pool expiry checking."""

    @patch(
        'awslabs.mysql_mcp_server.connection.asyncmy_pool_connection.asyncmy.create_pool',
        new_callable=AsyncMock,
    )
    async def test_check_expiry_not_expired(self, mock_create_pool):
        """Should not recreate pool if not expired."""
        mock_pool = MagicMock()
        mock_pool.close = MagicMock()
        mock_pool.wait_closed = AsyncMock()
        mock_create_pool.return_value = mock_pool

        conn = AsyncmyPoolConnection(
            host='localhost',
            port=3306,
            database='testdb',
            readonly=True,
            secret_arn='arn:secret',
            db_user='',
            region='us-east-1',
            is_iam_auth=False,
            is_test=True,
        )
        await conn.initialize_pool()
        conn.created_time = datetime.now()

        await conn.check_expiry()
        # Pool should not have been closed and recreated
        mock_create_pool.assert_called_once()

    @patch(
        'awslabs.mysql_mcp_server.connection.asyncmy_pool_connection.asyncmy.create_pool',
        new_callable=AsyncMock,
    )
    async def test_check_expiry_expired(self, mock_create_pool):
        """Should recreate pool if expired."""
        mock_pool = MagicMock()
        mock_pool.close = MagicMock()
        mock_pool.wait_closed = AsyncMock()
        mock_create_pool.return_value = mock_pool

        conn = AsyncmyPoolConnection(
            host='localhost',
            port=3306,
            database='testdb',
            readonly=True,
            secret_arn='arn:secret',
            db_user='',
            region='us-east-1',
            is_iam_auth=False,
            pool_expiry_min=30,
            is_test=True,
        )
        await conn.initialize_pool()
        # Force expiry
        conn.created_time = datetime.now() - timedelta(minutes=31)

        await conn.check_expiry()
        # Pool should have been closed and recreated (called twice total)
        assert mock_create_pool.call_count == 2


class TestAsyncmyPoolConnectionGetCredentials:
    """Tests for _get_credentials_from_secret."""

    def test_get_credentials_test_mode(self):
        """In test mode, should return test_user/test_password."""
        conn = AsyncmyPoolConnection(
            host='localhost',
            port=3306,
            database='testdb',
            readonly=True,
            secret_arn='arn:secret',
            db_user='',
            region='us-east-1',
            is_iam_auth=False,
            is_test=True,
        )
        user, password = conn._get_credentials_from_secret('arn:secret', 'us-east-1', is_test=True)
        assert user == 'test_user'
        assert password == 'test_password'

    @patch('awslabs.mysql_mcp_server.connection.asyncmy_pool_connection.boto3.Session')
    def test_get_credentials_from_secret_manager(self, mock_session_cls):
        """Should retrieve credentials from Secrets Manager."""
        mock_client = MagicMock()
        mock_client.get_secret_value.return_value = {
            'SecretString': '{"username": "dbadmin", "password": "s3cret"}'
        }
        mock_session = MagicMock()
        mock_session.client.return_value = mock_client
        mock_session_cls.return_value = mock_session

        conn = AsyncmyPoolConnection(
            host='localhost',
            port=3306,
            database='testdb',
            readonly=True,
            secret_arn='arn:secret',
            db_user='',
            region='us-east-1',
            is_iam_auth=False,
            is_test=True,
        )
        user, password = conn._get_credentials_from_secret(
            'arn:secret', 'us-east-1', is_test=False
        )
        assert user == 'dbadmin'
        assert password == 's3cret'

    @patch('awslabs.mysql_mcp_server.connection.asyncmy_pool_connection.boto3.Session')
    def test_get_credentials_missing_username(self, mock_session_cls):
        """Should raise ValueError if username not in secret."""
        mock_client = MagicMock()
        mock_client.get_secret_value.return_value = {'SecretString': '{"password": "s3cret"}'}
        mock_session = MagicMock()
        mock_session.client.return_value = mock_client
        mock_session_cls.return_value = mock_session

        conn = AsyncmyPoolConnection(
            host='localhost',
            port=3306,
            database='testdb',
            readonly=True,
            secret_arn='arn:secret',
            db_user='',
            region='us-east-1',
            is_iam_auth=False,
            is_test=True,
        )
        with pytest.raises(ValueError, match='Failed to retrieve credentials'):
            conn._get_credentials_from_secret('arn:secret', 'us-east-1', is_test=False)

    @patch('awslabs.mysql_mcp_server.connection.asyncmy_pool_connection.boto3.Session')
    def test_get_credentials_missing_password(self, mock_session_cls):
        """Should raise ValueError if password not in secret."""
        mock_client = MagicMock()
        mock_client.get_secret_value.return_value = {'SecretString': '{"username": "admin"}'}
        mock_session = MagicMock()
        mock_session.client.return_value = mock_client
        mock_session_cls.return_value = mock_session

        conn = AsyncmyPoolConnection(
            host='localhost',
            port=3306,
            database='testdb',
            readonly=True,
            secret_arn='arn:secret',
            db_user='',
            region='us-east-1',
            is_iam_auth=False,
            is_test=True,
        )
        with pytest.raises(ValueError, match='Failed to retrieve credentials'):
            conn._get_credentials_from_secret('arn:secret', 'us-east-1', is_test=False)

    @patch('awslabs.mysql_mcp_server.connection.asyncmy_pool_connection.boto3.Session')
    def test_get_credentials_no_secret_string(self, mock_session_cls):
        """Should raise ValueError if SecretString is missing."""
        mock_client = MagicMock()
        mock_client.get_secret_value.return_value = {'SecretBinary': b'binary'}
        mock_session = MagicMock()
        mock_session.client.return_value = mock_client
        mock_session_cls.return_value = mock_session

        conn = AsyncmyPoolConnection(
            host='localhost',
            port=3306,
            database='testdb',
            readonly=True,
            secret_arn='arn:secret',
            db_user='',
            region='us-east-1',
            is_iam_auth=False,
            is_test=True,
        )
        with pytest.raises(ValueError, match='Failed to retrieve credentials'):
            conn._get_credentials_from_secret('arn:secret', 'us-east-1', is_test=False)


class TestAsyncmyPoolConnectionGetIAMAuthToken:
    """Tests for IAM auth token generation."""

    @patch('awslabs.mysql_mcp_server.connection.asyncmy_pool_connection.boto3.client')
    def test_get_iam_auth_token(self, mock_boto_client):
        """Should call generate_db_auth_token with correct params."""
        mock_rds = MagicMock()
        mock_rds.generate_db_auth_token.return_value = 'token-abc'
        mock_boto_client.return_value = mock_rds

        conn = AsyncmyPoolConnection(
            host='mydb.cluster-xyz.us-east-1.rds.amazonaws.com',
            port=3306,
            database='testdb',
            readonly=True,
            secret_arn='',
            db_user='admin',
            region='us-east-1',
            is_iam_auth=True,
            is_test=True,
        )

        token = conn.get_iam_auth_token()
        assert token == 'token-abc'
        mock_rds.generate_db_auth_token.assert_called_once_with(
            DBHostname='mydb.cluster-xyz.us-east-1.rds.amazonaws.com',
            Port=3306,
            DBUsername='admin',
            Region='us-east-1',
        )
