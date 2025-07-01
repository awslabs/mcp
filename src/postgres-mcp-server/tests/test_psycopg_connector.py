#!/usr/bin/env python3
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

"""Tests for the PostgreSQL MCP Server psycopg connector with connection pool."""

import asyncio
import os
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from awslabs.postgres_mcp_server.connection.psycopg_connector import PsycopgConnector


@pytest.fixture
def mock_env_vars():
    """Set up environment variables for testing."""
    original_env = {}
    test_vars = {
        'POSTGRES_POOL_MIN_SIZE': '3',
        'POSTGRES_POOL_MAX_SIZE': '10',
        'POSTGRES_POOL_TIMEOUT': '15.0'
    }

    # Save original values
    for key in test_vars:
        if key in os.environ:
            original_env[key] = os.environ[key]

    # Set test values
    for key, value in test_vars.items():
        os.environ[key] = value

    yield test_vars

    # Restore original values
    for key in test_vars:
        if key in original_env:
            os.environ[key] = original_env[key]
        else:
            del os.environ[key]


@pytest.fixture
def mock_psycopg():
    """Mock psycopg and psycopg_pool modules."""
    with patch('awslabs.postgres_mcp_server.connection.psycopg_connector.psycopg') as mock_psycopg, \
         patch('awslabs.postgres_mcp_server.connection.psycopg_connector.ConnectionPool') as mock_pool, \
         patch('awslabs.postgres_mcp_server.connection.psycopg_connector.NullConnectionPool') as mock_null_pool:
        
        # Mock connection and cursor
        mock_cursor = MagicMock()
        mock_cursor.description = [MagicMock(name='id', type_code=23)]
        mock_cursor.fetchall.return_value = [{'id': 1}]
        mock_cursor.rowcount = 1
        
        mock_conn = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        
        # Mock connection pool
        mock_pool_instance = MagicMock()
        mock_pool_instance.getconn.return_value = mock_conn
        mock_pool_instance.putconn = MagicMock()
        mock_pool_instance.open = MagicMock()
        mock_pool_instance.close = MagicMock()
        mock_pool_instance.check = MagicMock()
        mock_pool_instance.get_stats.return_value = {
            'pool_size': 3,
            'available': 2,
            'requests': 5,
            'requests_waiting': 0
        }
        
        mock_pool.return_value = mock_pool_instance
        
        # Set up psycopg module
        mock_psycopg.rows.dict_row = MagicMock()
        mock_psycopg.OperationalError = type('OperationalError', (Exception,), {})
        mock_psycopg.InterfaceError = type('InterfaceError', (Exception,), {})
        mock_psycopg.Error = type('Error', (Exception,), {})
        
        yield {
            'psycopg': mock_psycopg,
            'pool': mock_pool,
            'pool_instance': mock_pool_instance,
            'conn': mock_conn,
            'cursor': mock_cursor
        }


@pytest.fixture
def mock_boto3():
    """Mock boto3 for AWS Secrets Manager."""
    with patch('awslabs.postgres_mcp_server.connection.psycopg_connector.boto3') as mock_boto3:
        mock_client = MagicMock()
        mock_client.get_secret_value.return_value = {
            'SecretString': '{"username": "test_user", "password": "test_password"}' # pragma: allowlist secret
        }
        mock_boto3.client.return_value = mock_client
        yield mock_boto3


@pytest.fixture
def connector(mock_psycopg, mock_boto3, mock_env_vars):
    """Create a PsycopgConnector instance for testing."""
    connector = PsycopgConnector(
        hostname='test-host',
        database='test-db',
        secret_arn='test-secret-arn',
        region_name='us-west-2',
        port=5432,
        readonly=True
    )
    yield connector


class TestPsycopgConnector:
    """Tests for the PsycopgConnector class."""

    @pytest.mark.asyncio
    async def test_init(self, connector, mock_env_vars):
        """Test initialization with environment variables."""
        assert connector.hostname == 'test-host'
        assert connector.database == 'test-db'
        assert connector.secret_arn == 'test-secret-arn'
        assert connector.region_name == 'us-west-2'
        assert connector.port == 5432
        assert connector.readonly is True
        assert connector.min_size == int(mock_env_vars['POSTGRES_POOL_MIN_SIZE'])
        assert connector.max_size == int(mock_env_vars['POSTGRES_POOL_MAX_SIZE'])
        assert connector.timeout == float(mock_env_vars['POSTGRES_POOL_TIMEOUT'])
        assert connector._pool is None

    @pytest.mark.asyncio
    async def test_ensure_pool(self, connector, mock_psycopg):
        """Test ensuring the connection pool is initialized."""
        # Ensure pool
        await connector._ensure_pool()
        
        # Verify pool was created
        assert connector._pool is not None
        
        # Verify pool was created with correct parameters
        mock_psycopg['pool'].assert_called_once()
        call_kwargs = mock_psycopg['pool'].call_args.kwargs
        assert 'conninfo' in call_kwargs
        assert 'min_size' in call_kwargs
        assert 'max_size' in call_kwargs
        assert 'timeout' in call_kwargs
        assert call_kwargs['min_size'] == connector.min_size
        assert call_kwargs['max_size'] == connector.max_size
        assert call_kwargs['timeout'] == connector.timeout

    @pytest.mark.asyncio
    async def test_is_connected(self, connector, mock_psycopg):
        """Test checking if connected."""
        # Not connected initially
        assert connector.is_connected() is False
        
        # Initialize pool
        await connector._ensure_pool()
        assert connector.is_connected() is True
        
        # Reset pool
        connector._pool = None
        assert connector.is_connected() is False

    @pytest.mark.asyncio
    async def test_execute_query_select(self, connector, mock_psycopg):
        """Test executing a SELECT query."""
        # Execute query
        result = await connector.execute_query("SELECT id FROM test")
        
        # Verify pool was initialized
        assert connector._pool is not None
        
        # Verify connection was obtained from pool
        mock_psycopg['pool_instance'].getconn.assert_called_once()
        
        # Verify query was executed
        mock_psycopg['cursor'].execute.assert_called_once_with("SELECT id FROM test", None)
        
        # Verify results were fetched
        mock_psycopg['cursor'].fetchall.assert_called_once()
        
        # Verify connection was returned to pool
        mock_psycopg['pool_instance'].putconn.assert_called_once_with(mock_psycopg['conn'])
        
        # Verify result format
        assert 'records' in result
        assert 'columnMetadata' in result
        assert len(result['records']) == 1
        assert len(result['columnMetadata']) == 1
        assert result['columnMetadata'][0]['name'] == 'id'

    @pytest.mark.asyncio
    async def test_execute_query_update(self, connector, mock_psycopg):
        """Test executing an UPDATE query."""
        # Set up cursor for UPDATE query
        mock_psycopg['cursor'].description = None
        mock_psycopg['cursor'].rowcount = 5
        
        # Execute query
        result = await connector.execute_query("UPDATE test SET value = 1")
        
        # Verify query was executed
        mock_psycopg['cursor'].execute.assert_called_once_with("UPDATE test SET value = 1", None)
        
        # Verify result format for non-SELECT query
        assert 'numberOfRecordsUpdated' in result
        assert result['numberOfRecordsUpdated'] == 5
        assert 'records' in result
        assert len(result['records']) == 0

    @pytest.mark.asyncio
    async def test_execute_query_with_parameters(self, connector, mock_psycopg):
        """Test executing a query with parameters."""
        # Set up parameters
        params = [
            {'name': 'id', 'value': {'longValue': 1}},
            {'name': 'name', 'value': {'stringValue': 'test'}}
        ]
        
        # Execute query
        await connector.execute_query("SELECT * FROM test WHERE id = :id AND name = :name", params)
        
        # Verify parameters were converted correctly
        mock_psycopg['cursor'].execute.assert_called_once()
        _, kwargs = mock_psycopg['cursor'].execute.call_args
        assert kwargs == {'id': 1, 'name': 'test'}

    @pytest.mark.asyncio
    async def test_execute_query_readonly_mode(self, connector, mock_psycopg):
        """Test executing a query in readonly mode."""
        # Execute query
        await connector.execute_query("SELECT id FROM test")
        
        # Verify SET TRANSACTION READ ONLY was executed
        mock_psycopg['conn'].execute.assert_called_once_with("SET TRANSACTION READ ONLY")

    @pytest.mark.asyncio
    async def test_health_check(self, connector, mock_psycopg):
        """Test health check."""
        # Perform health check
        result = await connector.health_check()
        
        # Verify pool was initialized
        assert connector._pool is not None
        
        # Verify result
        assert result is True

    @pytest.mark.asyncio
    async def test_connection_info(self, connector, mock_psycopg):
        """Test getting connection information."""
        # Initialize pool
        await connector._ensure_pool()
        
        # Get connection info
        info = connector.connection_info
        
        # Verify info structure
        assert info['type'] == 'psycopg_pool'
        assert info['hostname'] == 'test-host'
        assert info['port'] == 5432
        assert info['database'] == 'test-db'
        assert info['readonly'] is True
        assert info['min_size'] == connector.min_size
        assert info['max_size'] == connector.max_size
        
        # Verify pool stats
        assert 'pool_stats' in info
        assert info['pool_stats']['pool_size'] == 3
        assert info['pool_stats']['available'] == 2

    @pytest.mark.asyncio
    async def test_reconnect_on_error(self, connector, mock_psycopg):
        """Test reconnection on error."""
        # Initialize pool
        await connector._ensure_pool()
        
        # Make getconn raise an error the first time
        mock_psycopg['pool_instance'].getconn.side_effect = [
            mock_psycopg['psycopg'].OperationalError("Connection lost"),
            mock_psycopg['conn']  # Second call succeeds
        ]
        
        # Reset the pool to simulate reconnection
        connector._pool = None
        
        # Execute query - should reconnect
        with pytest.raises(Exception):
            await connector.execute_query("SELECT id FROM test")
        
        # Verify reconnection was attempted
        assert connector._pool is None


if __name__ == "__main__":
    pytest.main(["-xvs", __file__])
