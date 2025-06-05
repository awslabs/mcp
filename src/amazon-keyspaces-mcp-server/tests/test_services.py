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
"""Unit tests for the services module."""

import unittest
from awslabs.amazon_keyspaces_mcp_server.models import (
    KeyspaceInfo,
    TableInfo,
)
from awslabs.amazon_keyspaces_mcp_server.services import (
    DataService,
    SchemaService,
)
from unittest.mock import Mock


class TestDataService(unittest.TestCase):
    """Tests for the DataService class."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_client = Mock()
        self.mock_client.is_using_keyspaces.return_value = True
        self.mock_client.execute_read_only_query.return_value = {
            'columns': ['id', 'name', 'value'],
            'rows': [{'id': 1, 'name': 'test', 'value': 100}],
            'row_count': 1,
        }
        self.data_service = DataService(self.mock_client)

    def test_execute_read_only_query_without_keyspace_qualifier(self):
        """Test executing a query without a keyspace qualifier."""
        keyspace_name = 'my_keyspace'
        query = 'SELECT * FROM my_table'

        result = self.data_service.execute_read_only_query(keyspace_name, query)

        # Verify the client was called with the qualified query
        self.mock_client.execute_read_only_query.assert_called_once()
        call_args = self.mock_client.execute_read_only_query.call_args[0][0]
        self.assertEqual(call_args, 'SELECT * FROM my_keyspace.my_table')

        # Verify the result is returned correctly
        self.assertEqual(result['row_count'], 1)
        self.assertEqual(result['columns'], ['id', 'name', 'value'])
        self.assertEqual(len(result['rows']), 1)

    def test_execute_read_only_query_with_keyspace_qualifier(self):
        """Test executing a query that already has a keyspace qualifier."""
        keyspace_name = 'my_keyspace'
        query = 'SELECT * FROM my_keyspace.my_table'

        result = self.data_service.execute_read_only_query(keyspace_name, query)

        # Verify the client was called with the original query
        self.mock_client.execute_read_only_query.assert_called_once_with(query)

        # Verify the result is returned correctly
        self.assertEqual(result['row_count'], 1)

    def test_execute_read_only_query_with_complex_query(self):
        """Test executing a more complex query."""
        keyspace_name = 'my_keyspace'
        query = 'SELECT id, name FROM my_table WHERE id = 1 ORDER BY name'

        self.data_service.execute_read_only_query(keyspace_name, query)

        # Verify the client was called with the qualified query
        self.mock_client.execute_read_only_query.assert_called_once()
        call_args = self.mock_client.execute_read_only_query.call_args[0][0]
        self.assertEqual(
            call_args, 'SELECT id, name FROM my_keyspace.my_table WHERE id = 1 ORDER BY name'
        )


class TestSchemaService(unittest.TestCase):
    """Tests for the SchemaService class."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_client = Mock()
        self.mock_client.is_using_keyspaces.return_value = True
        self.schema_service = SchemaService(self.mock_client)

    def test_list_keyspaces(self):
        """Test listing keyspaces."""
        # Set up mock return value
        mock_keyspaces = [KeyspaceInfo(name='system'), KeyspaceInfo(name='my_keyspace')]
        self.mock_client.list_keyspaces.return_value = mock_keyspaces

        # Call the method
        result = self.schema_service.list_keyspaces()

        # Verify the client was called
        self.mock_client.list_keyspaces.assert_called_once()

        # Verify the result
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0].name, 'system')
        self.assertEqual(result[1].name, 'my_keyspace')

    def test_list_tables(self):
        """Test listing tables in a keyspace."""
        # Set up mock return value
        mock_tables = [
            TableInfo(name='users', keyspace='my_keyspace'),
            TableInfo(name='products', keyspace='my_keyspace'),
        ]
        self.mock_client.list_tables.return_value = mock_tables

        # Call the method
        result = self.schema_service.list_tables('my_keyspace')

        # Verify the client was called with the correct keyspace
        self.mock_client.list_tables.assert_called_once_with('my_keyspace')

        # Verify the result
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0].name, 'users')
        self.assertEqual(result[1].name, 'products')

    def test_describe_keyspace(self):
        """Test describing a keyspace."""
        # Set up mock return value
        mock_keyspace_details = {
            'name': 'my_keyspace',
            'replication': {'class': 'NetworkTopologyStrategy', 'dc1': '3'},
            'durable_writes': True,
        }
        self.mock_client.describe_keyspace.return_value = mock_keyspace_details

        # Call the method
        result = self.schema_service.describe_keyspace('my_keyspace')

        # Verify the client was called with the correct keyspace
        self.mock_client.describe_keyspace.assert_called_once_with('my_keyspace')

        # Verify the result
        self.assertEqual(result['name'], 'my_keyspace')
        self.assertEqual(result['replication']['class'], 'NetworkTopologyStrategy')
        self.assertTrue(result['durable_writes'])

    def test_describe_table(self):
        """Test describing a table."""
        # Set up mock return value
        mock_table_details = {
            'name': 'users',
            'keyspace': 'my_keyspace',
            'columns': [
                {'name': 'user_id', 'type': 'uuid', 'kind': 'partition_key'},
                {'name': 'username', 'type': 'text', 'kind': 'regular'},
            ],
            'partition_key': ['user_id'],
            'clustering_columns': [],
        }
        self.mock_client.describe_table.return_value = mock_table_details

        # Call the method
        result = self.schema_service.describe_table('my_keyspace', 'users')

        # Verify the client was called with the correct keyspace and table
        self.mock_client.describe_table.assert_called_once_with('my_keyspace', 'users')

        # Verify the result
        self.assertEqual(result['name'], 'users')
        self.assertEqual(result['keyspace'], 'my_keyspace')
        self.assertEqual(len(result['columns']), 2)
        self.assertEqual(result['columns'][0]['name'], 'user_id')
        self.assertEqual(result['partition_key'], ['user_id'])
