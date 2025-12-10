# tests/test_db_connection_map.py

"""Unit tests for DBConnectionMap class."""

import json
import pytest
import threading
import time
from awslabs.postgres_mcp_server.connection.db_connection_map import (
    ConnectionMethod,
    DBConnectionMap,
)
from unittest.mock import MagicMock, patch


class TestDBConnectionMap:
    """Test suite for DBConnectionMap class."""

    @pytest.fixture
    def connection_map(self):
        """Provide a fresh DBConnectionMap instance for each test."""
        return DBConnectionMap()

    @pytest.fixture
    def mock_connection(self):
        """Provide a mock database connection."""
        mock_conn = MagicMock()
        mock_conn.close = MagicMock()
        return mock_conn

    # ==================== Initialization Tests ====================

    def test_initialization(self, connection_map):
        """Test DBConnectionMap initializes with empty map and lock."""
        assert connection_map.map == {}
        assert isinstance(connection_map._lock, type(threading.Lock()))

    # ==================== Get Method Tests ====================

    def test_get_nonexistent_connection_returns_none(self, connection_map):
        """Test get() returns None when connection doesn't exist."""
        result = connection_map.get(
            ConnectionMethod.RDS_API, 'test-cluster', 'test-endpoint', 'test-db'
        )
        assert result is None

    def test_get_existing_connection(self, connection_map, mock_connection):
        """Test get() retrieves an existing connection."""
        # Setup
        connection_map.set(
            ConnectionMethod.RDS_API, 'test-cluster', 'test-endpoint', 'test-db', mock_connection
        )

        # Test
        result = connection_map.get(
            ConnectionMethod.RDS_API, 'test-cluster', 'test-endpoint', 'test-db'
        )

        assert result is mock_connection

    def test_get_with_none_method_raises_error(self, connection_map):
        """Test get() raises ValueError when method is None."""
        with pytest.raises(ValueError, match='method cannot be None'):
            connection_map.get(None, 'test-cluster', 'test-endpoint', 'test-db')

    def test_get_with_empty_cluster_allows(self, connection_map):
        """Test get() allows empty cluster identifier (returns None if not found)."""
        result = connection_map.get(ConnectionMethod.RDS_API, '', 'test-endpoint', 'test-db')
        assert result is None

    def test_get_with_none_cluster_allows(self, connection_map):
        """Test get() allows None cluster identifier (returns None if not found)."""
        result = connection_map.get(ConnectionMethod.RDS_API, None, 'test-endpoint', 'test-db')
        assert result is None

    def test_get_with_none_database_raises_error(self, connection_map):
        """Test get() raises ValueError when database is None or empty."""
        with pytest.raises(ValueError, match='database cannot be None or empty'):
            connection_map.get(ConnectionMethod.RDS_API, 'test-cluster', 'test-endpoint', None)

    # ==================== Set Method Tests ====================

    def test_set_new_connection(self, connection_map, mock_connection):
        """Test set() stores a new connection."""
        connection_map.set(
            ConnectionMethod.RDS_API, 'test-cluster', 'test-endpoint', 'test-db', mock_connection
        )

        # Verify it was stored
        result = connection_map.get(
            ConnectionMethod.RDS_API, 'test-cluster', 'test-endpoint', 'test-db'
        )
        assert result is mock_connection

    def test_set_overwrites_existing_connection(self, connection_map):
        """Test set() overwrites an existing connection."""
        old_conn = MagicMock()
        old_conn.close = MagicMock()
        new_conn = MagicMock()
        new_conn.close = MagicMock()

        # Set initial connection
        connection_map.set(
            ConnectionMethod.RDS_API, 'test-cluster', 'test-endpoint', 'test-db', old_conn
        )

        # Overwrite with new connection
        connection_map.set(
            ConnectionMethod.RDS_API, 'test-cluster', 'test-endpoint', 'test-db', new_conn
        )

        # Verify new connection is stored
        result = connection_map.get(
            ConnectionMethod.RDS_API, 'test-cluster', 'test-endpoint', 'test-db'
        )
        assert result is new_conn
        assert result is not old_conn

    def test_set_with_empty_cluster_allows(self, connection_map, mock_connection):
        """Test set() allows empty cluster identifier."""
        connection_map.set(
            ConnectionMethod.RDS_API, '', 'test-endpoint', 'test-db', mock_connection
        )
        result = connection_map.get(ConnectionMethod.RDS_API, '', 'test-endpoint', 'test-db')
        assert result is mock_connection

    def test_set_with_none_cluster_allows(self, connection_map, mock_connection):
        """Test set() allows None cluster identifier."""
        connection_map.set(
            ConnectionMethod.RDS_API, None, 'test-endpoint', 'test-db', mock_connection
        )
        result = connection_map.get(ConnectionMethod.RDS_API, None, 'test-endpoint', 'test-db')
        assert result is mock_connection

    def test_set_with_none_database_raises_error(self, connection_map, mock_connection):
        """Test set() raises ValueError when database is None or empty."""
        with pytest.raises(ValueError, match='database cannot be None or empty'):
            connection_map.set(
                ConnectionMethod.RDS_API, 'test-cluster', 'test-endpoint', None, mock_connection
            )

    def test_set_with_none_connection_raises_error(self, connection_map):
        """Test set() raises ValueError when connection is None."""
        with pytest.raises(ValueError, match='conn cannot be None'):
            connection_map.set(
                ConnectionMethod.RDS_API, 'test-cluster', 'test-endpoint', 'test-db', None
            )

    # ==================== Remove Method Tests ====================

    def test_remove_existing_connection(self, connection_map, mock_connection):
        """Test remove() deletes an existing connection."""
        # Setup
        connection_map.set(
            ConnectionMethod.RDS_API, 'test-cluster', 'test-endpoint', 'test-db', mock_connection
        )

        # Remove
        connection_map.remove(ConnectionMethod.RDS_API, 'test-cluster', 'test-endpoint', 'test-db')

        # Verify it's gone
        result = connection_map.get(
            ConnectionMethod.RDS_API, 'test-cluster', 'test-endpoint', 'test-db'
        )
        assert result is None

    @patch('awslabs.postgres_mcp_server.connection.db_connection_map.logger')
    def test_remove_nonexistent_connection_logs_info(self, mock_logger, connection_map):
        """Test remove() logs info when trying to remove non-existent connection."""
        connection_map.remove(
            ConnectionMethod.RDS_API,
            'nonexistent-cluster',
            'nonexistent-endpoint',
            'nonexistent-db',
        )

        # Verify log was called
        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args[0][0]
        assert 'Try to remove a non-existing connection' in call_args
        assert 'nonexistent-cluster' in call_args
        assert 'nonexistent-endpoint' in call_args
        assert 'nonexistent-db' in call_args

    def test_remove_with_empty_cluster_allows(self, connection_map):
        """Test remove() allows empty cluster identifier (logs if not found)."""
        # Should not raise an error, just log
        connection_map.remove(ConnectionMethod.RDS_API, '', 'test-endpoint', 'test-db')

    def test_remove_with_none_cluster_allows(self, connection_map):
        """Test remove() allows None cluster identifier (logs if not found)."""
        # Should not raise an error, just log
        connection_map.remove(ConnectionMethod.RDS_API, None, 'test-endpoint', 'test-db')

    def test_remove_with_none_database_raises_error(self, connection_map):
        """Test remove() raises ValueError when database is None or empty."""
        with pytest.raises(ValueError, match='database cannot be None or empty'):
            connection_map.remove(ConnectionMethod.RDS_API, 'test-cluster', 'test-endpoint', None)

    # ==================== Get Keys Method Tests ====================

    def test_get_keys_empty_map(self, connection_map):
        """Test get_keys_json() returns empty JSON array when map is empty."""
        keys_json = connection_map.get_keys_json()
        keys = json.loads(keys_json)
        assert keys == []

    def test_get_keys_single_connection(self, connection_map, mock_connection):
        """Test get_keys_json() returns single key."""
        connection_map.set(
            ConnectionMethod.RDS_API, 'test-cluster', 'test-endpoint', 'test-db', mock_connection
        )

        keys_json = connection_map.get_keys_json()
        keys = json.loads(keys_json)
        assert len(keys) == 1
        assert keys[0]['connection_method'] == ConnectionMethod.RDS_API
        assert keys[0]['cluster_identifier'] == 'test-cluster'
        assert keys[0]['db_endpoint'] == 'test-endpoint'
        assert keys[0]['database'] == 'test-db'

    def test_get_keys_multiple_connections(self, connection_map):
        """Test get_keys_json() returns all keys."""
        conn1 = MagicMock()
        conn1.close = MagicMock()
        conn2 = MagicMock()
        conn2.close = MagicMock()
        conn3 = MagicMock()
        conn3.close = MagicMock()

        connection_map.set(ConnectionMethod.RDS_API, 'cluster1', 'endpoint1', 'db1', conn1)
        connection_map.set(ConnectionMethod.RDS_API, 'cluster2', 'endpoint2', 'db2', conn2)
        connection_map.set(
            ConnectionMethod.PG_WIRE_PROTOCOL, 'cluster1', 'endpoint1', 'db1', conn3
        )

        keys_json = connection_map.get_keys_json()
        keys = json.loads(keys_json)
        assert len(keys) == 3

        key_tuples = [
            (k['connection_method'], k['cluster_identifier'], k['db_endpoint'], k['database'])
            for k in keys
        ]
        assert (ConnectionMethod.RDS_API, 'cluster1', 'endpoint1', 'db1') in key_tuples
        assert (ConnectionMethod.RDS_API, 'cluster2', 'endpoint2', 'db2') in key_tuples
        assert (ConnectionMethod.PG_WIRE_PROTOCOL, 'cluster1', 'endpoint1', 'db1') in key_tuples

    def test_get_keys_returns_copy(self, connection_map, mock_connection):
        """Test get_keys_json() returns a new JSON string each time."""
        connection_map.set(
            ConnectionMethod.RDS_API, 'test-cluster', 'test-endpoint', 'test-db', mock_connection
        )

        keys1 = connection_map.get_keys_json()
        keys2 = connection_map.get_keys_json()

        # Should be equal but not the same object
        assert keys1 == keys2
        assert keys1 is not keys2

    # ==================== Close All Method Tests ====================

    def test_close_all_closes_all_connections(self, connection_map):
        """Test close_all() calls close() on all connections."""
        conn1 = MagicMock()
        conn1.close = MagicMock()
        conn2 = MagicMock()
        conn2.close = MagicMock()
        conn3 = MagicMock()
        conn3.close = MagicMock()

        connection_map.set(ConnectionMethod.RDS_API, 'cluster1', 'endpoint1', 'db1', conn1)
        connection_map.set(ConnectionMethod.RDS_API, 'cluster2', 'endpoint2', 'db2', conn2)
        connection_map.set(
            ConnectionMethod.PG_WIRE_PROTOCOL, 'cluster1', 'endpoint1', 'db1', conn3
        )

        connection_map.close_all()

        # Verify all connections were closed
        conn1.close.assert_called_once()
        conn2.close.assert_called_once()
        conn3.close.assert_called_once()

    def test_close_all_clears_map(self, connection_map, mock_connection):
        """Test close_all() clears the connection map."""
        connection_map.set(
            ConnectionMethod.RDS_API, 'test-cluster', 'test-endpoint', 'test-db', mock_connection
        )

        connection_map.close_all()

        keys_json = connection_map.get_keys_json()
        keys = json.loads(keys_json)
        assert keys == []
        assert connection_map.map == {}

    def test_close_all_handles_close_exception(self, connection_map):
        """Test close_all() handles exceptions during close() gracefully."""
        conn1 = MagicMock()
        conn2 = MagicMock()
        conn3 = MagicMock()

        # Make close() synchronous
        conn1.close = MagicMock()
        conn2.close = MagicMock(side_effect=Exception('Connection close failed'))
        conn3.close = MagicMock()

        connection_map.set(ConnectionMethod.RDS_API, 'cluster1', 'endpoint1', 'db1', conn1)
        connection_map.set(ConnectionMethod.RDS_API, 'cluster2', 'endpoint2', 'db2', conn2)
        connection_map.set(ConnectionMethod.RDS_API, 'cluster3', 'endpoint3', 'db3', conn3)

        # Should not raise exception despite conn2 failing
        connection_map.close_all()

        # Verify all close() were attempted (this is the important behavior)
        conn1.close.assert_called_once()
        conn2.close.assert_called_once()
        conn3.close.assert_called_once()

        # Map should still be cleared (this is the important behavior)
        assert connection_map.map == {}

    def test_close_all_continues_after_exception(self, connection_map):
        """Test close_all() continues closing other connections after one fails."""
        conn1 = MagicMock()
        conn2 = MagicMock()
        conn3 = MagicMock()

        # Make close() synchronous and make conn1 and conn3 raise exceptions
        conn1.close = MagicMock(side_effect=Exception('First failure'))
        conn2.close = MagicMock()
        conn3.close = MagicMock(side_effect=Exception('Third failure'))

        connection_map.set(ConnectionMethod.RDS_API, 'cluster1', 'endpoint1', 'db1', conn1)
        connection_map.set(ConnectionMethod.RDS_API, 'cluster2', 'endpoint2', 'db2', conn2)
        connection_map.set(ConnectionMethod.RDS_API, 'cluster3', 'endpoint3', 'db3', conn3)

        # Should not raise exception despite conn1 and conn3 failing
        connection_map.close_all()

        # All connections should have been attempted (this is the important behavior)
        conn1.close.assert_called_once()
        conn2.close.assert_called_once()  # Should succeed
        conn3.close.assert_called_once()

        # Map should be cleared (this is the important behavior)
        assert connection_map.map == {}

    # ==================== Connection Method Differentiation Tests ====================

    def test_different_methods_different_connections(self, connection_map):
        """Test same cluster/db but different methods store separately."""
        conn_rds = MagicMock()
        conn_rds.close = MagicMock()
        conn_pg = MagicMock()
        conn_pg.close = MagicMock()

        connection_map.set(
            ConnectionMethod.RDS_API, 'test-cluster', 'test-endpoint', 'test-db', conn_rds
        )
        connection_map.set(
            ConnectionMethod.PG_WIRE_PROTOCOL, 'test-cluster', 'test-endpoint', 'test-db', conn_pg
        )

        # Should retrieve different connections
        result_rds = connection_map.get(
            ConnectionMethod.RDS_API, 'test-cluster', 'test-endpoint', 'test-db'
        )
        result_pg = connection_map.get(
            ConnectionMethod.PG_WIRE_PROTOCOL, 'test-cluster', 'test-endpoint', 'test-db'
        )

        assert result_rds is conn_rds
        assert result_pg is conn_pg
        assert result_rds is not result_pg

    # ==================== Endpoint Differentiation Tests ====================

    def test_different_endpoints_different_connections(self, connection_map):
        """Test same cluster/db but different endpoints store separately."""
        conn_endpoint_a = MagicMock()
        conn_endpoint_a.close = MagicMock()
        conn_endpoint_b = MagicMock()
        conn_endpoint_b.close = MagicMock()

        connection_map.set(
            ConnectionMethod.RDS_API,
            'test-cluster',
            'endpoint-a.rds.amazonaws.com',
            'test-db',
            conn_endpoint_a,
        )
        connection_map.set(
            ConnectionMethod.RDS_API,
            'test-cluster',
            'endpoint-b.rds.amazonaws.com',
            'test-db',
            conn_endpoint_b,
        )

        # Should retrieve different connections
        result_a = connection_map.get(
            ConnectionMethod.RDS_API, 'test-cluster', 'endpoint-a.rds.amazonaws.com', 'test-db'
        )
        result_b = connection_map.get(
            ConnectionMethod.RDS_API, 'test-cluster', 'endpoint-b.rds.amazonaws.com', 'test-db'
        )

        assert result_a is conn_endpoint_a
        assert result_b is conn_endpoint_b
        assert result_a is not result_b

    def test_get_with_none_endpoint_allows(self, connection_map):
        """Test get() allows None endpoint (returns None if not found)."""
        result = connection_map.get(ConnectionMethod.RDS_API, 'test-cluster', None, 'test-db')
        assert result is None

    def test_set_with_none_endpoint_allows(self, connection_map, mock_connection):
        """Test set() allows None endpoint."""
        connection_map.set(
            ConnectionMethod.RDS_API, 'test-cluster', None, 'test-db', mock_connection
        )
        result = connection_map.get(ConnectionMethod.RDS_API, 'test-cluster', None, 'test-db')
        assert result is mock_connection

    # ==================== Port Differentiation Tests ====================

    def test_different_ports_different_connections(self, connection_map):
        """Test same cluster/db/endpoint but different ports store separately."""
        conn_5432 = MagicMock()
        conn_5432.close = MagicMock()
        conn_5433 = MagicMock()
        conn_5433.close = MagicMock()

        connection_map.set(
            ConnectionMethod.RDS_API,
            'test-cluster',
            'test-endpoint',
            'test-db',
            conn_5432,
            port=5432,
        )
        connection_map.set(
            ConnectionMethod.RDS_API,
            'test-cluster',
            'test-endpoint',
            'test-db',
            conn_5433,
            port=5433,
        )

        # Should retrieve different connections
        result_5432 = connection_map.get(
            ConnectionMethod.RDS_API, 'test-cluster', 'test-endpoint', 'test-db', port=5432
        )
        result_5433 = connection_map.get(
            ConnectionMethod.RDS_API, 'test-cluster', 'test-endpoint', 'test-db', port=5433
        )

        assert result_5432 is conn_5432
        assert result_5433 is conn_5433
        assert result_5432 is not result_5433

    def test_default_port_5432(self, connection_map, mock_connection):
        """Test that default port is 5432."""
        # Set with explicit port=5432
        connection_map.set(
            ConnectionMethod.RDS_API,
            'test-cluster',
            'test-endpoint',
            'test-db',
            mock_connection,
            port=5432,
        )

        # Get without specifying port (should default to 5432)
        result = connection_map.get(
            ConnectionMethod.RDS_API, 'test-cluster', 'test-endpoint', 'test-db'
        )

        assert result is mock_connection

    # ==================== Thread Safety Tests ====================

    def test_concurrent_set_operations(self, connection_map):
        """Test multiple threads can safely set connections concurrently."""
        num_threads = 10
        connections = []
        for _ in range(num_threads):
            conn = MagicMock()
            conn.close = MagicMock()
            connections.append(conn)
        threads = []

        def set_connection(index):
            connection_map.set(
                ConnectionMethod.RDS_API,
                f'cluster-{index}',
                f'endpoint-{index}',
                f'db-{index}',
                connections[index],
            )

        # Start all threads
        for i in range(num_threads):
            thread = threading.Thread(target=set_connection, args=(i,))
            threads.append(thread)
            thread.start()

        # Wait for all to complete
        for thread in threads:
            thread.join()

        # Verify all connections were stored
        keys_json = connection_map.get_keys_json()
        keys = json.loads(keys_json)
        assert len(keys) == num_threads

        for i in range(num_threads):
            result = connection_map.get(
                ConnectionMethod.RDS_API, f'cluster-{i}', f'endpoint-{i}', f'db-{i}'
            )
            assert result is connections[i]

    def test_concurrent_get_operations(self, connection_map, mock_connection):
        """Test multiple threads can safely get connections concurrently."""
        connection_map.set(
            ConnectionMethod.RDS_API, 'test-cluster', 'test-endpoint', 'test-db', mock_connection
        )

        num_threads = 20
        results = [None] * num_threads
        threads = []

        def get_connection(index):
            results[index] = connection_map.get(
                ConnectionMethod.RDS_API, 'test-cluster', 'test-endpoint', 'test-db'
            )

        # Start all threads
        for i in range(num_threads):
            thread = threading.Thread(target=get_connection, args=(i,))
            threads.append(thread)
            thread.start()

        # Wait for all to complete
        for thread in threads:
            thread.join()

        # Verify all got the same connection
        assert all(result is mock_connection for result in results)

    def test_concurrent_set_and_get_operations(self, connection_map):
        """Test concurrent set and get operations don't cause race conditions."""
        num_operations = 50
        threads = []
        results = {}

        def set_and_get(index):
            conn = MagicMock()
            conn.close = MagicMock()
            connection_map.set(
                ConnectionMethod.RDS_API, f'cluster-{index}', 'test-endpoint', 'test-db', conn
            )
            # Small delay to increase chance of race conditions
            time.sleep(0.001)
            result = connection_map.get(
                ConnectionMethod.RDS_API, f'cluster-{index}', 'test-endpoint', 'test-db'
            )
            results[index] = (conn, result)

        # Start all threads
        for i in range(num_operations):
            thread = threading.Thread(target=set_and_get, args=(i,))
            threads.append(thread)
            thread.start()

        # Wait for all to complete
        for thread in threads:
            thread.join()

        # Verify each thread got back its own connection
        for i in range(num_operations):
            original_conn, retrieved_conn = results[i]
            assert retrieved_conn is original_conn

    def test_concurrent_remove_operations(self, connection_map):
        """Test concurrent remove operations are thread-safe."""
        # Setup multiple connections
        num_connections = 10
        for i in range(num_connections):
            conn = MagicMock()
            conn.close = MagicMock()
            connection_map.set(
                ConnectionMethod.RDS_API, f'cluster-{i}', 'test-endpoint', 'test-db', conn
            )

        threads = []

        def remove_connection(index):
            connection_map.remove(
                ConnectionMethod.RDS_API, f'cluster-{index}', 'test-endpoint', 'test-db'
            )

        # Start all threads
        for i in range(num_connections):
            thread = threading.Thread(target=remove_connection, args=(i,))
            threads.append(thread)
            thread.start()

        # Wait for all to complete
        for thread in threads:
            thread.join()

        # Verify all connections were removed
        keys_json = connection_map.get_keys_json()
        keys = json.loads(keys_json)
        assert keys == []

    @patch('awslabs.postgres_mcp_server.connection.db_connection_map.logger')
    def test_concurrent_remove_same_connection(self, mock_logger, connection_map, mock_connection):
        """Test multiple threads removing same connection is safe."""
        connection_map.set(
            ConnectionMethod.RDS_API, 'test-cluster', 'test-endpoint', 'test-db', mock_connection
        )

        num_threads = 5
        threads = []

        def remove_connection():
            connection_map.remove(
                ConnectionMethod.RDS_API, 'test-cluster', 'test-endpoint', 'test-db'
            )

        # Start all threads trying to remove the same connection
        for _ in range(num_threads):
            thread = threading.Thread(target=remove_connection)
            threads.append(thread)
            thread.start()

        # Wait for all to complete
        for thread in threads:
            thread.join()

        # Connection should be gone
        assert (
            connection_map.get(
                ConnectionMethod.RDS_API, 'test-cluster', 'test-endpoint', 'test-db'
            )
            is None
        )

        # At least one thread should have logged about non-existent connection
        # (the ones that tried to remove after it was already gone)
        assert mock_logger.info.call_count >= 1


# ==================== Integration Tests ====================


class TestDBConnectionMapIntegration:
    """Integration tests for realistic usage scenarios."""

    @pytest.fixture
    def connection_map(self):
        """Provide a fresh DBConnectionMap instance."""
        return DBConnectionMap()

    def test_typical_connection_lifecycle(self, connection_map):
        """Test a typical connection lifecycle: set, get, use, remove."""
        # Create connection - don't use spec to avoid async issues
        mock_conn = MagicMock()
        mock_conn.execute_query = MagicMock(return_value='query result')
        mock_conn.close = MagicMock()

        # Store connection
        connection_map.set(
            ConnectionMethod.RDS_API,
            'prod-cluster',
            'prod-cluster.cluster-abc123.us-east-1.rds.amazonaws.com',
            'analytics',
            mock_conn,
        )

        # Retrieve and use connection
        conn = connection_map.get(
            ConnectionMethod.RDS_API,
            'prod-cluster',
            'prod-cluster.cluster-abc123.us-east-1.rds.amazonaws.com',
            'analytics',
        )
        assert conn is not None
        result = conn.execute_query('SELECT * FROM users')
        assert result == 'query result'

        # Remove connection
        connection_map.remove(
            ConnectionMethod.RDS_API,
            'prod-cluster',
            'prod-cluster.cluster-abc123.us-east-1.rds.amazonaws.com',
            'analytics',
        )

        # Verify it's gone
        conn = connection_map.get(
            ConnectionMethod.RDS_API,
            'prod-cluster',
            'prod-cluster.cluster-abc123.us-east-1.rds.amazonaws.com',
            'analytics',
        )
        assert conn is None

    def test_multiple_databases_same_cluster(self, connection_map):
        """Test managing multiple databases on the same cluster."""
        conn_analytics = MagicMock()
        conn_analytics.close = MagicMock()
        conn_reporting = MagicMock()
        conn_reporting.close = MagicMock()
        conn_staging = MagicMock()
        conn_staging.close = MagicMock()

        # Add connections to different databases
        connection_map.set(
            ConnectionMethod.RDS_API,
            'prod-cluster',
            'prod-cluster.cluster-abc123.us-east-1.rds.amazonaws.com',
            'analytics',
            conn_analytics,
        )
        connection_map.set(
            ConnectionMethod.RDS_API,
            'prod-cluster',
            'prod-cluster.cluster-abc123.us-east-1.rds.amazonaws.com',
            'reporting',
            conn_reporting,
        )
        connection_map.set(
            ConnectionMethod.RDS_API,
            'prod-cluster',
            'prod-cluster.cluster-abc123.us-east-1.rds.amazonaws.com',
            'staging',
            conn_staging,
        )

        # Verify all are stored separately
        assert (
            connection_map.get(
                ConnectionMethod.RDS_API,
                'prod-cluster',
                'prod-cluster.cluster-abc123.us-east-1.rds.amazonaws.com',
                'analytics',
            )
            is conn_analytics
        )
        assert (
            connection_map.get(
                ConnectionMethod.RDS_API,
                'prod-cluster',
                'prod-cluster.cluster-abc123.us-east-1.rds.amazonaws.com',
                'reporting',
            )
            is conn_reporting
        )
        assert (
            connection_map.get(
                ConnectionMethod.RDS_API,
                'prod-cluster',
                'prod-cluster.cluster-abc123.us-east-1.rds.amazonaws.com',
                'staging',
            )
            is conn_staging
        )

        # Verify keys
        keys_json = connection_map.get_keys_json()
        keys = json.loads(keys_json)
        assert len(keys) == 3

    def test_cleanup_all_connections_on_shutdown(self, connection_map):
        """Test cleaning up all connections during shutdown."""
        # Setup multiple connections
        connections = []
        for i in range(5):
            conn = MagicMock()
            conn.close = MagicMock()
            connections.append(conn)
            connection_map.set(
                ConnectionMethod.RDS_API,
                f'cluster-{i}',
                f'cluster-{i}.cluster-xyz789.us-east-1.rds.amazonaws.com',
                f'db-{i}',
                conn,
            )

        # Simulate shutdown
        connection_map.close_all()

        # Verify all were closed
        for conn in connections:
            conn.close.assert_called_once()

        # Verify map is empty
        keys_json = connection_map.get_keys_json()
        keys = json.loads(keys_json)
        assert keys == []


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
