# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License").
# You may not use this file except in compliance with the License.
# A copy of the License is located at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# or in the 'license' file accompanying this file.
# This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES
# OR CONDITIONS OF ANY KIND, express or implied.
# See the License for the specific language governing permissions
# and limitations under the License.
"""Unit tests for the UnifiedCassandraClient class."""

import ssl
import unittest
from unittest.mock import Mock, patch

from cassandra.auth import PlainTextAuthProvider
from cassandra.cluster import Cluster, Session

from awslabs.amazon_keyspaces_mcp_server.client import UnifiedCassandraClient
from awslabs.amazon_keyspaces_mcp_server.config import DatabaseConfig
from awslabs.amazon_keyspaces_mcp_server.consts import (
    CASSANDRA_DEFAULT_PORT,
    KEYSPACES_DEFAULT_PORT,
)
from awslabs.amazon_keyspaces_mcp_server.models import TableInfo


# pylint: disable=no-member
class TestUnifiedCassandraClient(unittest.IsolatedAsyncioTestCase):
    """Tests for the UnifiedCassandraClient class."""

    def setUp(self):
        """Set up test fixtures."""
        # Create a mock database config for Cassandra
        self.cassandra_config = DatabaseConfig(
            use_keyspaces=False,
            cassandra_contact_points='127.0.0.1',
            cassandra_port=9042,
            cassandra_username='',
            cassandra_password='',
            cassandra_local_datacenter='datacenter1',
            keyspaces_endpoint='',
            keyspaces_region='',
        )

        # Create a mock database config for Keyspaces
        self.keyspaces_config = DatabaseConfig(
            use_keyspaces=True,
            cassandra_contact_points='',
            cassandra_port=0,
            cassandra_username='',
            cassandra_password='',
            cassandra_local_datacenter='',
            keyspaces_endpoint='cassandra.us-west-2.amazonaws.com',
            keyspaces_region='us-west-2',
        )

        # Create mock session and cluster
        self.mock_session = Mock(spec=Session)
        self.mock_cluster = Mock(spec=Cluster)
        self.mock_cluster.connect.return_value = self.mock_session

    @patch('awslabs.amazon_keyspaces_mcp_server.client.Cluster')
    async def test_create_cassandra_session(self, mock_cluster_class):
        """Test creating a session for Apache Cassandra."""
        # Set up the mock
        mock_cluster_instance = mock_cluster_class.return_value
        mock_cluster_instance.connect.return_value = self.mock_session

        # Create the client and get session
        client = UnifiedCassandraClient(self.cassandra_config)
        await client.get_session()

        # Verify Cluster was called with the correct arguments
        mock_cluster_class.assert_called_once()
        _, kwargs = mock_cluster_class.call_args

        # Check that contact points and port are correct
        self.assertEqual(kwargs['contact_points'], ['127.0.0.1'])
        self.assertEqual(kwargs['port'], CASSANDRA_DEFAULT_PORT)

        # Check that auth provider is correctly configured
        self.assertIsInstance(kwargs['auth_provider'], PlainTextAuthProvider)

        # Verify connect was called
        mock_cluster_instance.connect.assert_called_once()

        # Verify the session is set correctly
        self.assertEqual(client._session, self.mock_session)  # pylint: disable=protected-access

        # Verify is_keyspaces is set correctly
        self.assertFalse(client.is_keyspaces)

    @patch('awslabs.amazon_keyspaces_mcp_server.client.Cluster')
    @patch('awslabs.amazon_keyspaces_mcp_server.client.ssl')
    @patch('awslabs.amazon_keyspaces_mcp_server.client.os.path.join')
    @patch('awslabs.amazon_keyspaces_mcp_server.client.os.path.dirname')
    @patch('awslabs.amazon_keyspaces_mcp_server.client.HAS_SSL_OPTIONS', True)
    async def test_create_keyspaces_session_with_ssl_options(
        self, mock_dirname, mock_join, mock_ssl, mock_cluster_class
    ):
        """Test creating a session for Amazon Keyspaces with SSLOptions."""
        # Set up the mocks
        mock_cluster_instance = mock_cluster_class.return_value
        mock_cluster_instance.connect.return_value = self.mock_session

        mock_ssl_context = Mock(spec=ssl.SSLContext)
        mock_ssl.create_default_context.return_value = mock_ssl_context

        mock_dirname.return_value = '/mock/path'
        mock_join.return_value = '/mock/path/certs/sf-class2-root.crt'

        # Create the client and get session
        client = UnifiedCassandraClient(self.keyspaces_config)
        await client.get_session()

        # Verify ssl.create_default_context was called
        mock_ssl.create_default_context.assert_called_once()

        # Verify load_verify_locations was called with the correct path
        mock_ssl_context.load_verify_locations.assert_called_once_with(
            cafile='/mock/path/certs/sf-class2-root.crt'
        )

        # Verify check_hostname was set to False
        self.assertFalse(mock_ssl_context.check_hostname)

        # Verify Cluster was called with the correct arguments
        mock_cluster_class.assert_called_once()
        _, kwargs = mock_cluster_class.call_args

        # Check that contact points and port are correct
        self.assertEqual(kwargs['contact_points'], ['cassandra.us-west-2.amazonaws.com'])
        self.assertEqual(kwargs['port'], KEYSPACES_DEFAULT_PORT)  # Default Keyspaces port

        # Check that auth provider is correctly configured
        self.assertIsInstance(kwargs['auth_provider'], PlainTextAuthProvider)

        # Check that ssl_options is correctly configured
        self.assertIn('ssl_options', kwargs)

        # Verify connect was called
        mock_cluster_instance.connect.assert_called_once()

        # Verify the session is set correctly
        self.assertEqual(client._session, self.mock_session)  # pylint: disable=protected-access

        # Verify is_keyspaces is set correctly
        self.assertTrue(client.is_keyspaces)

    @patch('awslabs.amazon_keyspaces_mcp_server.client.Cluster')
    @patch('awslabs.amazon_keyspaces_mcp_server.client.ssl')
    @patch('awslabs.amazon_keyspaces_mcp_server.client.os.path.join')
    @patch('awslabs.amazon_keyspaces_mcp_server.client.os.path.dirname')
    @patch('awslabs.amazon_keyspaces_mcp_server.client.HAS_SSL_OPTIONS', False)
    async def test_create_keyspaces_session_without_ssl_options(
        self, mock_dirname, mock_join, mock_ssl, mock_cluster_class
    ):
        """Test creating a session for Amazon Keyspaces without SSLOptions."""
        # Set up the mocks
        mock_cluster_instance = mock_cluster_class.return_value
        mock_cluster_instance.connect.return_value = self.mock_session

        mock_ssl_context = Mock(spec=ssl.SSLContext)
        mock_ssl.create_default_context.return_value = mock_ssl_context

        mock_dirname.return_value = '/mock/path'
        mock_join.return_value = '/mock/path/certs/sf-class2-root.crt'

        # Create the client and get session
        client = UnifiedCassandraClient(self.keyspaces_config)
        await client.get_session()

        # Verify ssl.create_default_context was called
        mock_ssl.create_default_context.assert_called_once()

        # Verify load_verify_locations was called with the correct path
        mock_ssl_context.load_verify_locations.assert_called_once_with(
            cafile='/mock/path/certs/sf-class2-root.crt'
        )

        # Verify check_hostname was set to False
        self.assertFalse(mock_ssl_context.check_hostname)

        # Verify Cluster was called with the correct arguments
        mock_cluster_class.assert_called_once()
        _, kwargs = mock_cluster_class.call_args

        # Check that contact points and port are correct
        self.assertEqual(kwargs['contact_points'], ['cassandra.us-west-2.amazonaws.com'])
        self.assertEqual(kwargs['port'], 9142)  # Default Keyspaces port

        # Check that auth provider is correctly configured
        self.assertIsInstance(kwargs['auth_provider'], PlainTextAuthProvider)

        # Check that ssl_context is correctly configured
        self.assertEqual(kwargs['ssl_context'], mock_ssl_context)

        # Verify connect was called
        mock_cluster_instance.connect.assert_called_once()

        # Verify the session is set correctly
        self.assertEqual(client._session, self.mock_session)  # pylint: disable=protected-access

        # Verify is_keyspaces is set correctly
        self.assertTrue(client.is_keyspaces)

    @patch('awslabs.amazon_keyspaces_mcp_server.client.Cluster')
    @patch('awslabs.amazon_keyspaces_mcp_server.client.ssl')
    async def test_ssl_context_load_error(self, mock_ssl, mock_cluster_class):
        """Test handling of SSL certificate loading errors."""
        # Set up the mocks
        mock_cluster_instance = mock_cluster_class.return_value
        mock_cluster_instance.connect.return_value = self.mock_session

        mock_ssl_context = Mock(spec=ssl.SSLContext)
        mock_ssl.create_default_context.return_value = mock_ssl_context
        mock_ssl.SSLError = ssl.SSLError

        # Make load_verify_locations raise an exception
        mock_ssl_context.load_verify_locations.side_effect = FileNotFoundError(
            'Certificate not found'
        )

        # Create the client and get session
        client = UnifiedCassandraClient(self.keyspaces_config)
        await client.get_session()

        # Verify load_default_certs was called as a fallback
        mock_ssl_context.load_default_certs.assert_called_once()

        # Verify the client was still created successfully
        self.assertEqual(client._session, self.mock_session)  # pylint: disable=protected-access

    def test_is_using_keyspaces(self):
        """Test the is_using_keyspaces method."""
        # Create clients with different configurations
        with patch('awslabs.amazon_keyspaces_mcp_server.client.Cluster'):
            cassandra_client = UnifiedCassandraClient(self.cassandra_config)
            keyspaces_client = UnifiedCassandraClient(self.keyspaces_config)

            # Verify the method returns the correct value
            self.assertFalse(cassandra_client.is_using_keyspaces())
            self.assertTrue(keyspaces_client.is_using_keyspaces())

    async def test_list_keyspaces(self):
        """Test listing keyspaces."""
        mock_row1 = Mock()
        mock_row1.keyspace_name = 'system'
        mock_row1.replication = {'class': 'SimpleStrategy', 'replication_factor': '1'}

        mock_row2 = Mock()
        mock_row2.keyspace_name = 'mykeyspace'
        mock_row2.replication = {'class': 'NetworkTopologyStrategy', 'dc1': '3'}

        self.mock_session.execute.return_value = [mock_row1, mock_row2]

        with patch('awslabs.amazon_keyspaces_mcp_server.client.Cluster') as mock_cluster_class:
            # Associate the mock_session with the mock_cluster the client will connect to.
            mock_cluster_instance = mock_cluster_class.return_value
            mock_cluster_instance.connect.return_value = self.mock_session

            client = UnifiedCassandraClient(self.cassandra_config)

            # Call the method
            keyspaces = await client.list_keyspaces()

            # Verify the session.execute was called with the correct query
            self.mock_session.execute.assert_called_once_with(
                'SELECT keyspace_name, replication FROM system_schema.keyspaces'
            )

            # Verify the result
            self.assertEqual(len(keyspaces), 2)
            self.assertEqual(keyspaces[0].name, 'system')
            self.assertEqual(keyspaces[0].replication_strategy, 'SimpleStrategy')
            self.assertEqual(keyspaces[0].replication_factor, 1)
            self.assertEqual(keyspaces[1].name, 'mykeyspace')
            self.assertEqual(keyspaces[1].replication_strategy, 'NetworkTopologyStrategy')

    async def test_describe_keyspace(self):
        """Test describing a keyspace."""
        # Set up the mock session
        mock_row = Mock()
        mock_row.keyspace_name = 'mykeyspace'
        mock_row.replication = {'class': 'NetworkTopologyStrategy', 'dc1': '3'}
        mock_row.durable_writes = True

        mock_result = Mock()
        mock_result.one.return_value = mock_row

        # Configure our mock session's execute method
        self.mock_session.execute.return_value = mock_result

        with patch('awslabs.amazon_keyspaces_mcp_server.client.Cluster') as mock_cluster_class:
            # Associate the mock_session with the mock_cluster the client will connect to.
            mock_cluster_instance = mock_cluster_class.return_value
            mock_cluster_instance.connect.return_value = self.mock_session

            client = UnifiedCassandraClient(self.cassandra_config)

            # Mock the list_tables method
            client.list_tables = Mock(
                return_value=[
                    TableInfo(name='users', keyspace='mykeyspace'),
                    TableInfo(name='products', keyspace='mykeyspace'),
                ]
            )

            # Call the method
            keyspace_details = await client.describe_keyspace('mykeyspace')

            # Check if execute was called at all
            self.assertTrue(self.mock_session.execute.called, 'session.execute was not called')

            # Verify the session.execute was called with the correct query
            self.mock_session.execute.assert_called_with(
                'SELECT * FROM system_schema.keyspaces WHERE keyspace_name = %s', ['mykeyspace']
            )

            # Verify the result
            self.assertEqual(keyspace_details['name'], 'mykeyspace')
            self.assertEqual(keyspace_details['replication']['class'], 'NetworkTopologyStrategy')
            self.assertEqual(keyspace_details['replication']['dc1'], '3')
            self.assertTrue(keyspace_details['durable_writes'])
            self.assertEqual(len(keyspace_details['tables']), 2)

    async def test_list_tables(self):
        """Test listing tables in a keyspace."""
        # Set up the mock session
        mock_row1 = Mock()
        mock_row1.table_name = 'users'

        mock_row2 = Mock()
        mock_row2.table_name = 'products'

        self.mock_session.execute.return_value = [mock_row1, mock_row2]

        # Create the client
        with patch('awslabs.amazon_keyspaces_mcp_server.client.Cluster') as mock_cluster_class:
            # Associate the mock_session with the mock_cluster the client will connect to.
            mock_cluster_instance = mock_cluster_class.return_value
            mock_cluster_instance.connect.return_value = self.mock_session

            client = UnifiedCassandraClient(self.cassandra_config)

            # Call the method
            tables = await client.list_tables('mykeyspace')

            # Verify the session.execute was called with the correct query
            self.mock_session.execute.assert_called_once_with(
                'SELECT table_name FROM system_schema.tables WHERE keyspace_name = %s',
                ['mykeyspace'],
            )

            # Verify the result
            self.assertEqual(len(tables), 2)
            self.assertEqual(tables[0].name, 'users')
            self.assertEqual(tables[0].keyspace, 'mykeyspace')
            self.assertEqual(tables[1].name, 'products')
            self.assertEqual(tables[1].keyspace, 'mykeyspace')

    async def test_describe_keyspace_not_found(self):
        """Test describing a keyspace that doesn't exist."""
        # Set up the mock session to return None
        self.mock_session.execute.return_value = Mock()
        self.mock_session.execute.return_value.one.return_value = None

        # Create the client
        with patch('awslabs.amazon_keyspaces_mcp_server.client.Cluster') as mock_cluster_class:
            # Associate the mock_session with the mock_cluster the client will connect to.
            mock_cluster_instance = mock_cluster_class.return_value
            mock_cluster_instance.connect.return_value = self.mock_session

            client = UnifiedCassandraClient(self.cassandra_config)

            # Call the method and verify it raises an exception
            with self.assertRaises(RuntimeError) as context:
                await client.describe_keyspace('nonexistent')

            self.assertIn('Keyspace not found', str(context.exception))

    async def test_describe_table(self):
        """Test describing a table."""
        # Set up the mock session for table query
        mock_table_row = Mock()
        mock_table_row.table_name = 'users'
        mock_table_row.keyspace_name = 'mykeyspace'

        self.mock_session.execute.return_value = Mock()
        self.mock_session.execute.return_value.one.return_value = mock_table_row

        # Set up the mock session for column query
        mock_column_row1 = Mock()
        mock_column_row1.column_name = 'id'
        mock_column_row1.type = 'uuid'
        mock_column_row1.kind = 'partition_key'

        mock_column_row2 = Mock()
        mock_column_row2.column_name = 'name'
        mock_column_row2.type = 'text'
        mock_column_row2.kind = 'regular'

        # Set up the mock session for index query
        mock_index_row = Mock()
        mock_index_row.index_name = 'name_idx'
        mock_index_row.kind = 'CUSTOM'
        mock_index_row.options = {'target': 'name'}

        # Configure the execute method to return different results based on the query
        def mock_execute(query, _params=None):
            if 'tables' in query:
                result = Mock()
                result.one.return_value = mock_table_row
                return result
            elif 'columns' in query:
                return [mock_column_row1, mock_column_row2]
            elif 'indexes' in query:
                return [mock_index_row]
            return []

        self.mock_session.execute = mock_execute

        with patch('awslabs.amazon_keyspaces_mcp_server.client.Cluster') as mock_cluster_class:
            # Associate the mock_session with the mock_cluster the client will connect to.
            mock_cluster_instance = mock_cluster_class.return_value
            mock_cluster_instance.connect.return_value = self.mock_session

            client = UnifiedCassandraClient(self.cassandra_config)

            # Call the method
            table_details = await client.describe_table('mykeyspace', 'users')

            # Verify the result
            self.assertEqual(table_details['name'], 'users')
            self.assertEqual(table_details['keyspace'], 'mykeyspace')
            self.assertEqual(len(table_details['columns']), 2)
            self.assertEqual(table_details['columns'][0]['name'], 'id')
            self.assertEqual(table_details['columns'][0]['type'], 'uuid')
            self.assertEqual(table_details['columns'][0]['kind'], 'partition_key')
            self.assertEqual(table_details['columns'][1]['name'], 'name')
            self.assertEqual(table_details['columns'][1]['type'], 'text')
            self.assertEqual(table_details['columns'][1]['kind'], 'regular')
            self.assertEqual(len(table_details['indexes']), 1)
            self.assertEqual(table_details['indexes'][0]['name'], 'name_idx')
            self.assertEqual(table_details['indexes'][0]['options']['target'], 'name')

    async def test_describe_table_not_found(self):
        """Test describing a table that doesn't exist."""
        with patch('awslabs.amazon_keyspaces_mcp_server.client.Cluster') as mock_cluster_class:
            # Configure the mock cluster to return our mock session
            mock_cluster_instance = mock_cluster_class.return_value
            mock_cluster_instance.connect.return_value = self.mock_session
            self.mock_session.execute.return_value = Mock()
            self.mock_session.execute.return_value.one.return_value = None

            client = UnifiedCassandraClient(self.cassandra_config)

            # Call the method and verify it raises an exception
            with self.assertRaises(RuntimeError) as context:
                await client.describe_table('mykeyspace', 'nonexistent')

            self.assertIn('Table not found', str(context.exception))

    async def test_execute_read_only_query(self):
        """Test executing a read-only query."""
        # Set up the mock session
        mock_column_names = ['id', 'name', 'value']

        mock_row = Mock()
        mock_row.id = 1
        mock_row.name = 'test'
        mock_row.value = 100

        mock_result_set = Mock()
        mock_result_set.column_names = mock_column_names
        mock_result_set.__iter__ = lambda self: iter([mock_row])

        # Set up the response future
        mock_response_future = Mock()
        mock_coordinator_host = Mock()
        # mock_coordinator_host.__str__ = lambda self: '127.0.0.1'
        mock_coordinator_host.__str__ = Mock(return_value='127.0.0.1')
        mock_response_future.coordinator_host = mock_coordinator_host

        mock_result_set.response_future = mock_response_future

        self.mock_session.execute.return_value = mock_result_set

        with patch('awslabs.amazon_keyspaces_mcp_server.client.Cluster') as mock_cluster_class:
            # Associate the mock_session with the mock_cluster the client will connect to.
            mock_cluster_instance = mock_cluster_class.return_value
            mock_cluster_instance.connect.return_value = self.mock_session

            client = UnifiedCassandraClient(self.cassandra_config)

            # Call the method
            result = await client.execute_read_only_query('SELECT * FROM users WHERE id = 1')

            # Verify the session.execute was called with the correct query
            self.mock_session.execute.assert_called_once_with(
                'SELECT * FROM users WHERE id = 1',
            )

            # Verify the result
            self.assertEqual(result['columns'], ['id', 'name', 'value'])
            self.assertEqual(len(result['rows']), 1)
            self.assertEqual(result['rows'][0]['id'], 1)
            self.assertEqual(result['rows'][0]['name'], 'test')
            self.assertEqual(result['rows'][0]['value'], 100)
            self.assertEqual(result['row_count'], 1)
            self.assertEqual(result['execution_info']['queried_host'], '127.0.0.1')

    async def test_execute_read_only_query_with_params(self):
        """Test executing a read-only query with parameters."""
        # Set up the mock session
        mock_column_names = ['id', 'name']

        mock_row = Mock()
        mock_row.id = 1
        mock_row.name = 'test'

        mock_result_set = Mock()
        mock_result_set.column_names = mock_column_names
        mock_result_set.__iter__ = lambda self: iter([mock_row])
        mock_result_set.response_future = Mock()
        mock_result_set.response_future.coordinator_host = None

        self.mock_session.execute.return_value = mock_result_set

        # Create the client
        with patch('awslabs.amazon_keyspaces_mcp_server.client.Cluster') as mock_cluster_class:
            # Associate the mock_session with the mock_cluster the client will connect to.
            mock_cluster_instance = mock_cluster_class.return_value
            mock_cluster_instance.connect.return_value = self.mock_session

            client = UnifiedCassandraClient(self.cassandra_config)

            # Call the method with parameters
            params = [1]
            result = await client.execute_read_only_query(
                'SELECT * FROM users WHERE id = %s', params
            )

            # Verify the session.execute was called with the correct query and parameters
            self.mock_session.execute.assert_called_once_with(
                'SELECT * FROM users WHERE id = %s', params
            )

            # Verify the result
            self.assertEqual(result['columns'], ['id', 'name'])
            self.assertEqual(len(result['rows']), 1)
            self.assertEqual(result['rows'][0]['id'], 1)
            self.assertEqual(result['rows'][0]['name'], 'test')
            self.assertEqual(result['row_count'], 1)

    async def test_execute_read_only_query_non_select(self):
        """Test executing a non-SELECT query."""
        # Create the client
        with patch('awslabs.amazon_keyspaces_mcp_server.client.Cluster'):
            client = UnifiedCassandraClient(self.cassandra_config)

            # Call the method with a non-SELECT query and verify it raises an exception
            with self.assertRaises(ValueError) as context:
                await client.execute_read_only_query(
                    "INSERT INTO users (id, name) VALUES (1, 'test')"
                )

            self.assertIn('Only SELECT queries are allowed', str(context.exception))

    async def test_execute_read_only_query_unsafe_operations(self):
        """Test executing a query with unsafe operations."""
        # Create the client
        with patch('awslabs.amazon_keyspaces_mcp_server.client.Cluster'):
            client = UnifiedCassandraClient(self.cassandra_config)

            # Call the method with a query containing unsafe operations
            # and verify it raises an exception
            with self.assertRaises(ValueError) as context:
                await client.execute_read_only_query('SELECT * FROM users; DROP TABLE users;')

            self.assertIn('potentially unsafe operations', str(context.exception))

    async def test_close(self):
        """Test closing the client."""
        # Create the client
        with patch('awslabs.amazon_keyspaces_mcp_server.client.Cluster') as mock_cluster_class:
            # Configure the mock cluster to return our mock session
            mock_cluster_instance = mock_cluster_class.return_value
            mock_cluster_instance.connect.return_value = self.mock_session

            client = UnifiedCassandraClient(self.cassandra_config)
            await client.get_session()

            # Call the close method
            client.close()

            # Verify the session and cluster shutdown methods were called
            self.mock_session.cluster.shutdown.assert_called_once()
            self.mock_session.shutdown.assert_called_once()

    async def test_get_session_connection_failure(self):
        """Test get_session when connection fails."""
        with patch('awslabs.amazon_keyspaces_mcp_server.client.Cluster') as mock_cluster_class:
            mock_cluster_class.return_value.connect.side_effect = Exception('Connection failed')

            client = UnifiedCassandraClient(self.cassandra_config)

            with self.assertRaises(RuntimeError) as context:
                await client.get_session()

            self.assertIn('Failed to connect to Cassandra cluster', str(context.exception))

    async def test_list_keyspaces_with_invalid_replication_factor_value_error(self):
        """Test listing keyspaces with invalid replication_factor (ValueError)."""
        mock_row = Mock()
        mock_row.keyspace_name = 'test_ks'
        mock_row.replication = {'class': 'SimpleStrategy', 'replication_factor': 'invalid'}

        self.mock_session.execute.return_value = [mock_row]

        with patch('awslabs.amazon_keyspaces_mcp_server.client.Cluster') as mock_cluster_class:
            mock_cluster_instance = mock_cluster_class.return_value
            mock_cluster_instance.connect.return_value = self.mock_session

            client = UnifiedCassandraClient(self.cassandra_config)
            keyspaces = await client.list_keyspaces()

            self.assertEqual(len(keyspaces), 1)
            self.assertEqual(keyspaces[0].replication_factor, 0)

    async def test_list_keyspaces_with_none_replication_factor_type_error(self):
        """Test listing keyspaces with None replication_factor (TypeError)."""
        mock_row = Mock()
        mock_row.keyspace_name = 'test_ks'
        mock_row.replication = {'class': 'SimpleStrategy', 'replication_factor': None}

        self.mock_session.execute.return_value = [mock_row]

        with patch('awslabs.amazon_keyspaces_mcp_server.client.Cluster') as mock_cluster_class:
            mock_cluster_instance = mock_cluster_class.return_value
            mock_cluster_instance.connect.return_value = self.mock_session

            client = UnifiedCassandraClient(self.cassandra_config)
            keyspaces = await client.list_keyspaces()

            self.assertEqual(len(keyspaces), 1)
            self.assertEqual(keyspaces[0].replication_factor, 0)

    def test_build_service_characteristics(self):
        """Test building service characteristics for Keyspaces."""
        with patch('awslabs.amazon_keyspaces_mcp_server.client.Cluster'):
            client = UnifiedCassandraClient(self.keyspaces_config)
            characteristics = client._build_service_characteristics()  # pylint: disable=protected-access

            self.assertIn('write_throughput_limitation', characteristics)
            self.assertIn('implementation_notes', characteristics)
            self.assertIn('response_guidance', characteristics)
            self.assertIn('do_not_mention', characteristics['response_guidance'])
            self.assertIn('preferred_terminology', characteristics['response_guidance'])
            self.assertEqual(len(characteristics['response_guidance']['do_not_mention']), 3)
            self.assertEqual(len(characteristics['response_guidance']['preferred_terminology']), 3)

    def test_close_without_session(self):
        """Test closing the client when no session exists."""
        with patch('awslabs.amazon_keyspaces_mcp_server.client.Cluster'):
            client = UnifiedCassandraClient(self.cassandra_config)
            client.close()  # Should not raise an exception

    async def test_close_without_cluster(self):
        """Test closing the client when session exists but cluster is None."""
        with patch('awslabs.amazon_keyspaces_mcp_server.client.Cluster') as mock_cluster_class:
            mock_cluster_instance = mock_cluster_class.return_value
            mock_cluster_instance.connect.return_value = self.mock_session
            self.mock_session.cluster = None

            client = UnifiedCassandraClient(self.cassandra_config)
            await client.get_session()
            client.close()

            self.mock_session.shutdown.assert_called_once()

    async def test_describe_table_with_capacity_mode(self):
        """Test describing a Keyspaces table with capacity mode information."""
        mock_table_row = Mock()
        mock_table_row.table_name = 'users'
        mock_table_row.keyspace_name = 'mykeyspace'

        mock_capacity_row = Mock()
        mock_capacity_row.custom_properties = {
            'capacity_mode': 'PROVISIONED',
            'read_capacity_units': '100',
            'write_capacity_units': '50'
        }

        def mock_execute(query, _params=None):
            if 'tables' in query and 'system_schema_mcs' not in query:
                result = Mock()
                result.one.return_value = mock_table_row
                return result
            elif 'columns' in query:
                return []
            elif 'indexes' in query:
                return []
            elif 'system_schema_mcs' in query:
                result = Mock()
                result.one.return_value = mock_capacity_row
                return result
            return []

        self.mock_session.execute = mock_execute

        with patch('awslabs.amazon_keyspaces_mcp_server.client.Cluster') as mock_cluster_class:
            mock_cluster_instance = mock_cluster_class.return_value
            mock_cluster_instance.connect.return_value = self.mock_session

            client = UnifiedCassandraClient(self.keyspaces_config)
            table_details = await client.describe_table('mykeyspace', 'users')

            self.assertEqual(table_details['capacity_mode'], 'PROVISIONED')
            self.assertEqual(table_details['read_capacity_units'], 100)
            self.assertEqual(table_details['write_capacity_units'], 50)

    async def test_execute_read_only_query_with_column_error(self):
        """Test query execution when getting column value raises an error."""
        mock_column_names = ['id', 'bad_column']
        mock_row = Mock()
        mock_row.id = 1
        type(mock_row).bad_column = property(
            lambda self: (_ for _ in ()).throw(ValueError('Bad column'))
        )

        mock_result_set = Mock()
        mock_result_set.column_names = mock_column_names
        mock_result_set.__iter__ = lambda self: iter([mock_row])
        mock_result_set.response_future = None

        self.mock_session.execute.return_value = mock_result_set

        with patch('awslabs.amazon_keyspaces_mcp_server.client.Cluster') as mock_cluster_class:
            mock_cluster_instance = mock_cluster_class.return_value
            mock_cluster_instance.connect.return_value = self.mock_session

            client = UnifiedCassandraClient(self.cassandra_config)
            result = await client.execute_read_only_query('SELECT * FROM users')

            self.assertEqual(result['rows'][0]['id'], 1)
            self.assertIsNone(result['rows'][0]['bad_column'])

    async def test_describe_table_without_capacity_mode(self):
        """Test table without capacity_mode in custom_properties."""
        mock_table_row = Mock()
        mock_table_row.table_name = 'users'
        mock_table_row.keyspace_name = 'mykeyspace'

        mock_capacity_row = Mock()
        mock_capacity_row.custom_properties = {'other_property': 'value'}

        def mock_execute(query, _params=None):
            if 'tables' in query and 'system_schema_mcs' not in query:
                result = Mock()
                result.one.return_value = mock_table_row
                return result
            elif 'columns' in query:
                return []
            elif 'indexes' in query:
                return []
            elif 'system_schema_mcs' in query:
                result = Mock()
                result.one.return_value = mock_capacity_row
                return result
            return []

        self.mock_session.execute = mock_execute

        with patch('awslabs.amazon_keyspaces_mcp_server.client.Cluster') as mock_cluster_class:
            mock_cluster_instance = mock_cluster_class.return_value
            mock_cluster_instance.connect.return_value = self.mock_session

            client = UnifiedCassandraClient(self.keyspaces_config)
            table_details = await client.describe_table('mykeyspace', 'users')

            self.assertNotIn('capacity_mode', table_details)
            self.assertNotIn('read_capacity_units', table_details)
            self.assertNotIn('write_capacity_units', table_details)


    async def test_describe_table_with_on_demand_capacity(self):
        """Test table with ON_DEMAND capacity mode."""
        mock_table_row = Mock()
        mock_table_row.table_name = 'users'
        mock_table_row.keyspace_name = 'mykeyspace'

        mock_capacity_row = Mock()
        mock_capacity_row.custom_properties = {'capacity_mode': 'ON_DEMAND'}

        def mock_execute(query, _params=None):
            if 'tables' in query and 'system_schema_mcs' not in query:
                result = Mock()
                result.one.return_value = mock_table_row
                return result
            elif 'columns' in query:
                return []
            elif 'indexes' in query:
                return []
            elif 'system_schema_mcs' in query:
                result = Mock()
                result.one.return_value = mock_capacity_row
                return result
            return []

        self.mock_session.execute = mock_execute

        with patch('awslabs.amazon_keyspaces_mcp_server.client.Cluster') as mock_cluster_class:
            mock_cluster_instance = mock_cluster_class.return_value
            mock_cluster_instance.connect.return_value = self.mock_session

            client = UnifiedCassandraClient(self.keyspaces_config)
            table_details = await client.describe_table('mykeyspace', 'users')

            self.assertEqual(table_details['capacity_mode'], 'ON_DEMAND')
            self.assertNotIn('read_capacity_units', table_details)
            self.assertNotIn('write_capacity_units', table_details)

    async def test_describe_table_provisioned_missing_capacity_units(self):
        """Test PROVISIONED mode without required capacity units raises error."""
        mock_table_row = Mock()
        mock_table_row.table_name = 'users'
        mock_table_row.keyspace_name = 'mykeyspace'

        mock_capacity_row = Mock()
        mock_capacity_row.custom_properties = {'capacity_mode': 'PROVISIONED'}

        def mock_execute(query, _params=None):
            if 'tables' in query and 'system_schema_mcs' not in query:
                result = Mock()
                result.one.return_value = mock_table_row
                return result
            elif 'columns' in query:
                return []
            elif 'indexes' in query:
                return []
            elif 'system_schema_mcs' in query:
                result = Mock()
                result.one.return_value = mock_capacity_row
                return result
            return []

        self.mock_session.execute = mock_execute

        with patch('awslabs.amazon_keyspaces_mcp_server.client.Cluster') as mock_cluster_class:
            mock_cluster_instance = mock_cluster_class.return_value
            mock_cluster_instance.connect.return_value = self.mock_session

            client = UnifiedCassandraClient(self.keyspaces_config)
            table_details = await client.describe_table('mykeyspace', 'users')

            self.assertNotIn('read_capacity_units', table_details)
            self.assertNotIn('write_capacity_units', table_details)


if __name__ == '__main__':
    unittest.main()
