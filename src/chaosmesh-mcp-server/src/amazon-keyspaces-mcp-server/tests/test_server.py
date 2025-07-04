# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance
# with the License. A copy of the License is located at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES
# OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions
# and limitations under the License.
"""Unit tests for the server module."""

import unittest
from awslabs.amazon_keyspaces_mcp_server.consts import MAX_DISPLAY_ROWS
from awslabs.amazon_keyspaces_mcp_server.models import KeyspaceInfo, QueryAnalysisResult, TableInfo
from awslabs.amazon_keyspaces_mcp_server.server import (
    KeyspacesMcpStdioServer,
    analyze_query_performance,
    describe_keyspace,
    describe_table,
    execute_query,
    get_proxy,
    list_keyspaces,
    list_tables,
)
from mcp.server.fastmcp import Context
from unittest.mock import AsyncMock, Mock, patch


class TestServerTools(unittest.TestCase):
    """Tests for the server tool functions."""

    @patch('awslabs.amazon_keyspaces_mcp_server.server.get_proxy')
    def test_list_keyspaces(self, mock_get_proxy):
        """Test the list_keyspaces tool."""
        # Set up the mock
        mock_proxy = Mock()
        mock_proxy.handle_list_keyspaces.return_value = 'Keyspaces list'
        mock_get_proxy.return_value = mock_proxy

        # Call the function
        result = list_keyspaces()

        # Verify the result
        self.assertEqual(result, 'Keyspaces list')
        mock_proxy.handle_list_keyspaces.assert_called_once_with(None)

    @patch('awslabs.amazon_keyspaces_mcp_server.server.get_proxy')
    def test_list_tables(self, mock_get_proxy):
        """Test the list_tables tool."""
        # Set up the mock
        mock_proxy = Mock()
        mock_proxy._handle_list_tables.return_value = 'Tables list'
        mock_get_proxy.return_value = mock_proxy

        # Call the function
        result = list_tables('mykeyspace')

        # Verify the result
        self.assertEqual(result, 'Tables list')
        mock_proxy._handle_list_tables.assert_called_once_with('mykeyspace', None)

    @patch('awslabs.amazon_keyspaces_mcp_server.server.get_proxy')
    def test_describe_keyspace(self, mock_get_proxy):
        """Test the describe_keyspace tool."""
        # Set up the mock
        mock_proxy = Mock()
        mock_proxy._handle_describe_keyspace.return_value = 'Keyspace details'
        mock_get_proxy.return_value = mock_proxy

        # Call the function
        result = describe_keyspace('mykeyspace')

        # Verify the result
        self.assertEqual(result, 'Keyspace details')
        mock_proxy._handle_describe_keyspace.assert_called_once_with('mykeyspace', None)

    @patch('awslabs.amazon_keyspaces_mcp_server.server.get_proxy')
    def test_describe_table(self, mock_get_proxy):
        """Test the describe_table tool."""
        # Set up the mock
        mock_proxy = Mock()
        mock_proxy._handle_describe_table.return_value = 'Table details'
        mock_get_proxy.return_value = mock_proxy

        # Call the function
        result = describe_table('mykeyspace', 'users')

        # Verify the result
        self.assertEqual(result, 'Table details')
        mock_proxy._handle_describe_table.assert_called_once_with('mykeyspace', 'users', None)

    @patch('awslabs.amazon_keyspaces_mcp_server.server.get_proxy')
    def test_execute_query(self, mock_get_proxy):
        """Test the execute_query tool."""
        # Set up the mock
        mock_proxy = Mock()
        mock_proxy._handle_execute_query.return_value = 'Query results'
        mock_get_proxy.return_value = mock_proxy

        # Call the function
        result = execute_query('mykeyspace', 'SELECT * FROM users')

        # Verify the result
        self.assertEqual(result, 'Query results')
        mock_proxy._handle_execute_query.assert_called_once_with(
            'mykeyspace', 'SELECT * FROM users', None
        )

    @patch('awslabs.amazon_keyspaces_mcp_server.server.get_proxy')
    def test_analyze_query_performance(self, mock_get_proxy):
        """Test the analyze_query_performance tool."""
        # Set up the mock
        mock_proxy = Mock()
        mock_proxy._handle_analyze_query_performance.return_value = 'Query analysis'
        mock_get_proxy.return_value = mock_proxy

        # Call the function
        result = analyze_query_performance('mykeyspace', 'SELECT * FROM users')

        # Verify the result
        self.assertEqual(result, 'Query analysis')
        mock_proxy._handle_analyze_query_performance.assert_called_once_with(
            'mykeyspace', 'SELECT * FROM users', None
        )


class TestKeyspacesMcpStdioServer(unittest.TestCase):
    """Tests for the KeyspacesMcpStdioServer class."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_data_service = Mock()
        self.mock_query_analysis_service = Mock()
        self.mock_schema_service = Mock()
        self.server = KeyspacesMcpStdioServer(
            self.mock_data_service, self.mock_query_analysis_service, self.mock_schema_service
        )
        self.mock_context = AsyncMock(spec=Context)

    def test_handle_list_keyspaces(self):
        """Test the handle_list_keyspaces method."""
        # Set up the mock
        keyspace1 = KeyspaceInfo(name='system')
        keyspace2 = KeyspaceInfo(name='mykeyspace')
        self.mock_schema_service.list_keyspaces.return_value = [keyspace1, keyspace2]

        # Call the method
        result = self.server.handle_list_keyspaces(self.mock_context)

        # Verify the result
        self.assertIn('## Available Keyspaces', result)
        self.assertIn('- `system`', result)
        self.assertIn('- `mykeyspace`', result)
        self.mock_schema_service.list_keyspaces.assert_called_once()
        self.mock_context.info.assert_called_once()

    def test_handle_list_keyspaces_empty(self):
        """Test the handle_list_keyspaces method with no keyspaces."""
        # Set up the mock
        self.mock_schema_service.list_keyspaces.return_value = []

        # Call the method
        result = self.server.handle_list_keyspaces(self.mock_context)

        # Verify the result
        self.assertIn('## Available Keyspaces', result)
        self.assertIn('No keyspaces found.', result)
        self.mock_schema_service.list_keyspaces.assert_called_once()
        self.mock_context.info.assert_called_once()

    def test_handle_list_keyspaces_error(self):
        """Test the handle_list_keyspaces method with an error."""
        # Set up the mock
        self.mock_schema_service.list_keyspaces.side_effect = Exception('Test error')

        # Call the method and verify it raises an exception
        with self.assertRaises(Exception) as context:
            self.server.handle_list_keyspaces(self.mock_context)

        self.assertIn('Error listing keyspaces', str(context.exception))
        self.mock_schema_service.list_keyspaces.assert_called_once()

    def test_handle_list_tables(self):
        """Test the _handle_list_tables method."""
        # Set up the mock
        table1 = TableInfo(name='users', keyspace='mykeyspace')
        table2 = TableInfo(name='products', keyspace='mykeyspace')
        self.mock_schema_service.list_tables.return_value = [table1, table2]

        # Call the method
        result = self.server._handle_list_tables('mykeyspace', self.mock_context)

        # Verify the result
        self.assertIn('## Tables in Keyspace `mykeyspace`', result)
        self.assertIn('- `users`', result)
        self.assertIn('- `products`', result)
        self.mock_schema_service.list_tables.assert_called_once_with('mykeyspace')
        self.mock_context.info.assert_called_once()

    def test_handle_list_tables_empty(self):
        """Test the _handle_list_tables method with no tables."""
        # Set up the mock
        self.mock_schema_service.list_tables.return_value = []

        # Call the method
        result = self.server._handle_list_tables('mykeyspace', self.mock_context)

        # Verify the result
        self.assertIn('## Tables in Keyspace `mykeyspace`', result)
        self.assertIn('No tables found in this keyspace.', result)
        self.mock_schema_service.list_tables.assert_called_once_with('mykeyspace')
        self.mock_context.info.assert_called_once()

    def test_handle_list_tables_error(self):
        """Test the _handle_list_tables method with an error."""
        # Set up the mock
        self.mock_schema_service.list_tables.side_effect = Exception('Test error')

        # Call the method and verify it raises an exception
        with self.assertRaises(Exception) as context:
            self.server._handle_list_tables('mykeyspace', self.mock_context)

        self.assertIn('Error listing tables', str(context.exception))
        self.mock_schema_service.list_tables.assert_called_once_with('mykeyspace')

    def test_handle_describe_keyspace(self):
        """Test the _handle_describe_keyspace method."""
        # Set up the mock
        keyspace_details = {
            'name': 'mykeyspace',
            'replication': {'class': 'NetworkTopologyStrategy', 'dc1': '3'},
            'durable_writes': True,
        }
        self.mock_schema_service.describe_keyspace.return_value = keyspace_details

        # Call the method
        result = self.server._handle_describe_keyspace('mykeyspace', self.mock_context)

        # Verify the result
        self.assertIn('## Keyspace: `mykeyspace`', result)
        self.assertIn('### Replication', result)
        self.assertIn('**Strategy**: `NetworkTopologyStrategy`', result)
        self.assertIn('**Datacenter Replication**:', result)
        self.assertIn('**Durable Writes**: `True`', result)
        self.mock_schema_service.describe_keyspace.assert_called_once_with('mykeyspace')
        self.mock_context.info.assert_called_once()

    def test_handle_describe_keyspace_simple_strategy(self):
        """Test the _handle_describe_keyspace method with SimpleStrategy."""
        # Set up the mock
        keyspace_details = {
            'name': 'mykeyspace',
            'replication': {'class': 'SimpleStrategy', 'replication_factor': '3'},
            'durable_writes': True,
        }
        self.mock_schema_service.describe_keyspace.return_value = keyspace_details

        # Call the method
        result = self.server._handle_describe_keyspace('mykeyspace', self.mock_context)

        # Verify the result
        self.assertIn('## Keyspace: `mykeyspace`', result)
        self.assertIn('### Replication', result)
        self.assertIn('**Strategy**: `SimpleStrategy`', result)
        self.assertIn('**Replication Factor**: `3`', result)
        self.assertIn('**Durable Writes**: `True`', result)
        self.mock_schema_service.describe_keyspace.assert_called_once_with('mykeyspace')
        self.mock_context.info.assert_called_once()

    def test_handle_describe_keyspace_error(self):
        """Test the _handle_describe_keyspace method with an error."""
        # Set up the mock
        self.mock_schema_service.describe_keyspace.side_effect = Exception('Test error')

        # Call the method and verify it raises an exception
        with self.assertRaises(Exception) as context:
            self.server._handle_describe_keyspace('mykeyspace', self.mock_context)

        self.assertIn('Error describing keyspace', str(context.exception))
        self.mock_schema_service.describe_keyspace.assert_called_once_with('mykeyspace')

    def test_handle_describe_table(self):
        """Test the _handle_describe_table method."""
        # Set up the mock
        table_details = {
            'name': 'users',
            'keyspace': 'mykeyspace',
            'columns': [
                {'name': 'id', 'type': 'uuid', 'kind': 'partition_key'},
                {'name': 'name', 'type': 'text', 'kind': 'regular'},
            ],
            'partition_key': ['id'],
            'clustering_columns': [],
            'options': {'comment': 'User table'},
        }
        self.mock_schema_service.describe_table.return_value = table_details

        # Call the method
        result = self.server._handle_describe_table('mykeyspace', 'users', self.mock_context)

        # Verify the result
        self.assertIn('## Table: `mykeyspace.users`', result)
        self.assertIn('### Columns', result)
        self.assertIn('| `id` | `uuid` | `partition_key` |', result)
        self.assertIn('| `name` | `text` | `regular` |', result)
        self.assertIn('### Primary Key', result)
        self.assertIn('**Partition Key**:', result)
        self.assertIn('- `id`', result)
        self.assertIn('### Table Options', result)
        self.assertIn('- **comment**: `User table`', result)
        self.mock_schema_service.describe_table.assert_called_once_with('mykeyspace', 'users')
        self.mock_context.info.assert_called_once()

    def test_handle_describe_table_with_clustering_columns(self):
        """Test the _handle_describe_table method with clustering columns."""
        # Set up the mock
        table_details = {
            'name': 'users',
            'keyspace': 'mykeyspace',
            'columns': [
                {'name': 'id', 'type': 'uuid', 'kind': 'partition_key'},
                {'name': 'created_at', 'type': 'timestamp', 'kind': 'clustering'},
                {'name': 'name', 'type': 'text', 'kind': 'regular'},
            ],
            'partition_key': ['id'],
            'clustering_columns': ['created_at'],
        }
        self.mock_schema_service.describe_table.return_value = table_details

        # Call the method
        result = self.server._handle_describe_table('mykeyspace', 'users', self.mock_context)

        # Verify the result
        self.assertIn('## Table: `mykeyspace.users`', result)
        self.assertIn('### Columns', result)
        self.assertIn('| `id` | `uuid` | `partition_key` |', result)
        self.assertIn('| `created_at` | `timestamp` | `clustering` |', result)
        self.assertIn('| `name` | `text` | `regular` |', result)
        self.assertIn('### Primary Key', result)
        self.assertIn('**Partition Key**:', result)
        self.assertIn('- `id`', result)
        self.assertIn('**Clustering Columns**:', result)
        self.assertIn('- `created_at`', result)
        self.mock_schema_service.describe_table.assert_called_once_with('mykeyspace', 'users')
        self.mock_context.info.assert_called_once()

    def test_handle_describe_table_error(self):
        """Test the _handle_describe_table method with an error."""
        # Set up the mock
        self.mock_schema_service.describe_table.side_effect = Exception('Test error')

        # Call the method and verify it raises an exception
        with self.assertRaises(Exception) as context:
            self.server._handle_describe_table('mykeyspace', 'users', self.mock_context)

        self.assertIn('Error describing table', str(context.exception))
        self.mock_schema_service.describe_table.assert_called_once_with('mykeyspace', 'users')

    def test_handle_execute_query(self):
        """Test the _handle_execute_query method."""
        # Set up the mock
        query_results = {
            'columns': ['id', 'name'],
            'rows': [{'id': 1, 'name': 'test'}],
            'row_count': 1,
        }
        self.mock_data_service.execute_read_only_query.return_value = query_results

        # Call the method
        result = self.server._handle_execute_query(
            'mykeyspace', 'SELECT * FROM users', self.mock_context
        )

        # Verify the result
        self.assertIn('## Query Results', result)
        self.assertIn('**Query:** `SELECT * FROM users`', result)
        self.assertIn('**Row Count:** 1', result)
        self.assertIn('| id | name |', result)
        self.assertIn('| 1 | test |', result)
        self.mock_data_service.execute_read_only_query.assert_called_once_with(
            'mykeyspace', 'SELECT * FROM users'
        )
        self.mock_context.info.assert_called_once()

    def test_handle_execute_query_no_rows(self):
        """Test the _handle_execute_query method with no rows."""
        # Set up the mock
        query_results = {'columns': ['id', 'name'], 'rows': [], 'row_count': 0}
        self.mock_data_service.execute_read_only_query.return_value = query_results

        # Call the method
        result = self.server._handle_execute_query(
            'mykeyspace', 'SELECT * FROM users WHERE id = 999', self.mock_context
        )

        # Verify the result
        self.assertIn('## Query Results', result)
        self.assertIn('**Query:** `SELECT * FROM users WHERE id = 999`', result)
        self.assertIn('**Row Count:** 0', result)
        self.assertIn('No rows returned.', result)
        self.mock_data_service.execute_read_only_query.assert_called_once_with(
            'mykeyspace', 'SELECT * FROM users WHERE id = 999'
        )
        self.mock_context.info.assert_called_once()

    def test_handle_execute_query_many_rows(self):
        """Test the _handle_execute_query method with many rows."""
        # Set up the mock
        rows = []
        for i in range(MAX_DISPLAY_ROWS + 5):  # More than MAX_DISPLAY_ROWS
            rows.append({'id': i, 'name': f'test{i}'})

        query_results = {'columns': ['id', 'name'], 'rows': rows, 'row_count': len(rows)}
        self.mock_data_service.execute_read_only_query.return_value = query_results

        # Call the method
        result = self.server._handle_execute_query(
            'mykeyspace', 'SELECT * FROM users', self.mock_context
        )

        # Verify the result
        self.assertIn('## Query Results', result)
        self.assertIn('**Query:** `SELECT * FROM users`', result)
        self.assertIn(f'**Row Count:** {len(rows)}', result)
        self.assertIn('_Note: Showing', result)  # Truncation message
        self.mock_data_service.execute_read_only_query.assert_called_once_with(
            'mykeyspace', 'SELECT * FROM users'
        )
        self.mock_context.info.assert_called_once()

    def test_handle_execute_query_non_select(self):
        """Test the _handle_execute_query method with a non-SELECT query."""
        # Call the method and verify it raises an exception
        with self.assertRaises(Exception) as context:
            self.server._handle_execute_query(
                'mykeyspace',
                "INSERT INTO users (id, name) VALUES (1, 'test')",
                self.mock_context,
            )

        self.assertIn('Only SELECT queries are allowed', str(context.exception))
        self.mock_data_service.execute_read_only_query.assert_not_called()

    def test_handle_execute_query_unsafe_operations(self):
        """Test the _handle_execute_query method with unsafe operations."""
        # Call the method and verify it raises an exception
        with self.assertRaises(Exception) as context:
            self.server._handle_execute_query(
                'mykeyspace',
                'SELECT * FROM users; DROP TABLE users;',
                self.mock_context,
            )

        self.assertIn('potentially unsafe operations', str(context.exception))
        self.mock_data_service.execute_read_only_query.assert_not_called()

    def test_handle_execute_query_error(self):
        """Test the _handle_execute_query method with an error."""
        # Set up the mock
        self.mock_data_service.execute_read_only_query.side_effect = Exception('Test error')

        # Call the method and verify it raises an exception
        with self.assertRaises(Exception) as context:
            self.server._handle_execute_query(
                'mykeyspace', 'SELECT * FROM users', self.mock_context
            )

        self.assertIn('Error executing query', str(context.exception))
        self.mock_data_service.execute_read_only_query.assert_called_once_with(
            'mykeyspace', 'SELECT * FROM users'
        )

    def test_handle_analyze_query_performance(self):
        """Test the _handle_analyze_query_performance method."""
        # Set up the mock
        analysis_result = QueryAnalysisResult(
            query='SELECT * FROM users WHERE id = 1',
            table_name='users',
            uses_partition_key=True,
            performance_assessment='Good query',
            recommendations=['No recommendations'],
        )
        self.mock_query_analysis_service.analyze_query.return_value = analysis_result

        # Call the method
        result = self.server._handle_analyze_query_performance(
            'mykeyspace',
            'SELECT * FROM users WHERE id = 1',
            self.mock_context,
        )

        # Verify the result
        self.assertIn('## Query Analysis Results', result)
        self.assertIn('**Query:** `SELECT * FROM users WHERE id = 1`', result)
        self.assertIn('**Table:** `users`', result)
        self.assertIn('### Performance Assessment', result)
        self.assertIn('Good query', result)
        self.assertIn('### Recommendations', result)
        self.assertIn('- No recommendations', result)
        self.mock_query_analysis_service.analyze_query.assert_called_once_with(
            'mykeyspace', 'SELECT * FROM users WHERE id = 1'
        )
        self.mock_context.info.assert_called_once()

    def test_handle_analyze_query_performance_no_recommendations(self):
        """Test the _handle_analyze_query_performance method with no recommendations."""
        # Set up the mock
        analysis_result = QueryAnalysisResult(
            query='SELECT * FROM users WHERE id = 1',
            table_name='users',
            uses_partition_key=True,
            performance_assessment='Good query',
            recommendations=[],
        )
        self.mock_query_analysis_service.analyze_query.return_value = analysis_result

        # Call the method
        result = self.server._handle_analyze_query_performance(
            'mykeyspace',
            'SELECT * FROM users WHERE id = 1',
            self.mock_context,
        )

        # Verify the result
        self.assertIn('## Query Analysis Results', result)
        self.assertIn('**Query:** `SELECT * FROM users WHERE id = 1`', result)
        self.assertIn('**Table:** `users`', result)
        self.assertIn('### Performance Assessment', result)
        self.assertIn('Good query', result)
        self.assertNotIn('### Recommendations', result)
        self.mock_query_analysis_service.analyze_query.assert_called_once_with(
            'mykeyspace', 'SELECT * FROM users WHERE id = 1'
        )
        self.mock_context.info.assert_called_once()

    def test_handle_analyze_query_performance_error(self):
        """Test the _handle_analyze_query_performance method with an error."""
        # Set up the mock
        self.mock_query_analysis_service.analyze_query.side_effect = Exception('Test error')

        # Call the method and verify it raises an exception
        with self.assertRaises(Exception) as context:
            self.server._handle_analyze_query_performance(
                'mykeyspace', 'SELECT * FROM users', self.mock_context
            )

        self.assertIn('Error analyzing query', str(context.exception))
        self.mock_query_analysis_service.analyze_query.assert_called_once_with(
            'mykeyspace', 'SELECT * FROM users'
        )


@patch('awslabs.amazon_keyspaces_mcp_server.server.UnifiedCassandraClient')
@patch('awslabs.amazon_keyspaces_mcp_server.server.AppConfig')
def test_get_proxy(mock_app_config, mock_client_class):
    """Test the get_proxy function."""
    # Set up the mocks
    mock_app_config_instance = Mock()
    mock_app_config.from_env.return_value = mock_app_config_instance

    mock_client_instance = Mock()
    mock_client_class.return_value = mock_client_instance

    # Call the function
    proxy = get_proxy()

    # Call it again to test singleton behavior
    proxy2 = get_proxy()

    # Verify the results
    assert proxy is proxy2  # Should return the same instance
    mock_app_config.from_env.assert_called_once()
    mock_client_class.assert_called_once_with(mock_app_config_instance.database_config)


if __name__ == '__main__':
    unittest.main()
