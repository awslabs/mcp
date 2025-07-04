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
"""Unit tests for the QueryAnalysisService class."""

import unittest
from awslabs.amazon_keyspaces_mcp_server.models import QueryAnalysisResult
from awslabs.amazon_keyspaces_mcp_server.services import QueryAnalysisService, SchemaService
from unittest.mock import Mock, PropertyMock


class TestQueryAnalysisService(unittest.TestCase):
    """Tests for the QueryAnalysisService class."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_client = Mock()
        self.mock_schema_service = Mock(spec=SchemaService)
        self.query_analysis_service = QueryAnalysisService(
            self.mock_client, self.mock_schema_service
        )

    def test_normalize_query(self):
        """Test normalizing a query."""
        query = '  SELECT * FROM users WHERE id = 1  '
        normalized = self.query_analysis_service._normalize_query(query)
        self.assertEqual(normalized, 'select * from users where id = 1')

    def test_extract_table_name_simple(self):
        """Test extracting table name from a simple query."""
        query = 'select * from users where id = 1'
        table_name = self.query_analysis_service._extract_table_name(query)
        self.assertEqual(table_name, 'users')

    def test_extract_table_name_with_keyspace(self):
        """Test extracting table name from a query with keyspace qualifier."""
        query = 'select * from myks.users where id = 1'
        table_name = self.query_analysis_service._extract_table_name(query)
        self.assertEqual(table_name, 'users')

    def test_extract_where_conditions_simple(self):
        """Test extracting WHERE conditions from a simple query."""
        query = 'select * from users where id = 1'
        conditions = self.query_analysis_service._extract_where_conditions(query)
        self.assertEqual(conditions, ['id'])

    def test_extract_where_conditions_multiple(self):
        """Test extracting WHERE conditions from a query with multiple conditions."""
        query = "select * from users where id = 1 and name = 'test'"
        conditions = self.query_analysis_service._extract_where_conditions(query)
        self.assertEqual(conditions, ['id', 'name'])

    def test_extract_where_conditions_with_order_by(self):
        """Test extracting WHERE conditions from a query with ORDER BY clause."""
        query = 'select * from users where id = 1 order by name'
        conditions = self.query_analysis_service._extract_where_conditions(query)
        self.assertEqual(conditions, ['id'])

    def test_extract_where_conditions_with_limit(self):
        """Test extracting WHERE conditions from a query with LIMIT clause."""
        query = 'select * from users where id = 1 limit 10'
        conditions = self.query_analysis_service._extract_where_conditions(query)
        self.assertEqual(conditions, ['id'])

    def test_extract_partition_key_columns(self):
        """Test extracting partition key columns from table details."""
        table_details = {
            'columns': [
                {'name': 'id', 'is_partition_key': True},
                {'name': 'region', 'is_partition_key': True},
                {'name': 'name', 'is_partition_key': False},
            ]
        }
        partition_keys = self.query_analysis_service._extract_partition_key_columns(table_details)
        self.assertEqual(partition_keys, ['id', 'region'])

    def test_extract_clustering_columns(self):
        """Test extracting clustering columns from table details."""
        table_details = {
            'columns': [
                {'name': 'id', 'is_clustering_column': False},
                {'name': 'created_at', 'is_clustering_column': True},
                {'name': 'updated_at', 'is_clustering_column': True},
            ]
        }
        clustering_columns = self.query_analysis_service._extract_clustering_columns(table_details)
        self.assertEqual(clustering_columns, ['created_at', 'updated_at'])

    def test_check_partition_key_usage_all_used(self):
        """Test checking partition key usage when all keys are used."""
        partition_keys = ['id', 'region']
        where_conditions = ['id', 'region', 'name']
        result = self.query_analysis_service._check_partition_key_usage(
            partition_keys, where_conditions
        )
        self.assertTrue(result)

    def test_check_partition_key_usage_not_all_used(self):
        """Test checking partition key usage when not all keys are used."""
        partition_keys = ['id', 'region']
        where_conditions = ['id', 'name']
        result = self.query_analysis_service._check_partition_key_usage(
            partition_keys, where_conditions
        )
        self.assertFalse(result)

    def test_check_clustering_column_usage_used(self):
        """Test checking clustering column usage when at least one is used."""
        clustering_columns = ['created_at', 'updated_at']
        where_conditions = ['id', 'created_at']
        result = self.query_analysis_service._check_clustering_column_usage(
            clustering_columns, where_conditions
        )
        self.assertTrue(result)

    def test_check_clustering_column_usage_not_used(self):
        """Test checking clustering column usage when none are used."""
        clustering_columns = ['created_at', 'updated_at']
        where_conditions = ['id', 'name']
        result = self.query_analysis_service._check_clustering_column_usage(
            clustering_columns, where_conditions
        )
        self.assertFalse(result)

    def test_check_secondary_index_usage_used(self):
        """Test checking secondary index usage when an index is used."""
        table_details = {'indexes': [{'options': {'target': 'name'}}]}
        where_conditions = ['id', 'name']
        result = self.query_analysis_service._check_secondary_index_usage(
            table_details, where_conditions
        )
        self.assertTrue(result)

    def test_check_secondary_index_usage_not_used(self):
        """Test checking secondary index usage when no index is used."""
        table_details = {'indexes': [{'options': {'target': 'email'}}]}
        where_conditions = ['id', 'name']
        result = self.query_analysis_service._check_secondary_index_usage(
            table_details, where_conditions
        )
        self.assertFalse(result)

    def test_check_secondary_index_usage_no_indexes(self):
        """Test checking secondary index usage when no indexes exist."""
        table_details = {'indexes': []}
        where_conditions = ['id', 'name']
        result = self.query_analysis_service._check_secondary_index_usage(
            table_details, where_conditions
        )
        self.assertFalse(result)

    def test_check_secondary_index_usage_with_quotes(self):
        """Test checking secondary index usage with quoted column names."""
        table_details = {'indexes': [{'options': {'target': '"userName"'}}]}
        where_conditions = ['id', 'userName']
        result = self.query_analysis_service._check_secondary_index_usage(
            table_details, where_conditions
        )
        self.assertTrue(result)

    def test_generate_performance_assessment_good_query(self):
        """Test generating performance assessment for a good query."""
        result = QueryAnalysisResult(query='select * from users where id = 1')
        result.uses_partition_key = True
        result.uses_clustering_columns = True
        result.uses_allow_filtering = False
        result.uses_secondary_index = False
        result.is_full_table_scan = False

        self.query_analysis_service._generate_performance_assessment(
            result, ['id'], ['created_at']
        )

        self.assertIn('EFFICIENT PARTITION KEY USAGE', result.performance_assessment)
        self.assertIn('EFFICIENT CLUSTERING COLUMN USAGE', result.performance_assessment)
        self.assertNotIn('ALLOW FILTERING', result.performance_assessment)
        self.assertNotIn('FULL TABLE SCAN', result.performance_assessment)

    def test_generate_performance_assessment_bad_query(self):
        """Test generating performance assessment for a bad query."""
        result = QueryAnalysisResult(query='select * from users')
        result.uses_partition_key = False
        result.uses_clustering_columns = False
        result.uses_allow_filtering = True
        result.uses_secondary_index = False
        result.is_full_table_scan = True

        self.query_analysis_service._generate_performance_assessment(
            result, ['id'], ['created_at']
        )

        self.assertIn('HIGH COST QUERY', result.performance_assessment)
        self.assertIn('ALLOW FILTERING', result.performance_assessment)
        self.assertIn('FULL TABLE SCAN', result.performance_assessment)
        self.assertIn('Include all partition key columns', result.recommendations[0])

    def test_generate_performance_assessment_with_secondary_index(self):
        """Test generating performance assessment for a query using secondary index."""
        result = QueryAnalysisResult(query="select * from users where email = 'test@example.com'")
        result.uses_partition_key = False
        result.uses_clustering_columns = False
        result.uses_allow_filtering = False
        result.uses_secondary_index = True
        result.is_full_table_scan = False

        self.query_analysis_service._generate_performance_assessment(
            result, ['id'], ['created_at']
        )

        self.assertIn('SECONDARY INDEX USAGE', result.performance_assessment)
        self.assertIn('Monitor the performance', ' '.join(result.recommendations))

    def test_analyze_query_integration(self):
        """Test the analyze_query method with a complete integration test."""
        # Mock the schema service responses
        table_info_mock = Mock()
        type(table_info_mock).name = PropertyMock(return_value='users')
        self.mock_schema_service.list_tables.return_value = [table_info_mock]
        self.mock_schema_service.describe_table.return_value = {
            'columns': [
                {'name': 'id', 'is_partition_key': True},
                {'name': 'name', 'is_partition_key': False},
                {'name': 'created_at', 'is_clustering_column': True},
            ],
            'partition_key': ['id'],
            'clustering_columns': ['created_at'],
            'indexes': [],
        }

        # Call the analyze_query method
        result = self.query_analysis_service.analyze_query(
            'myks', "SELECT * FROM users WHERE id = 1 AND name = 'test'"
        )

        # Verify the result
        self.assertEqual(result.table_name, 'users')
        self.assertTrue(result.uses_partition_key)
        self.assertFalse(result.uses_clustering_columns)
        self.assertFalse(result.uses_allow_filtering)
        self.assertFalse(result.uses_secondary_index)
        self.assertFalse(result.is_full_table_scan)
        self.assertIn('EFFICIENT PARTITION KEY USAGE', result.performance_assessment)

    def test_analyze_query_with_error(self):
        """Test the analyze_query method when an error occurs."""
        # Mock the schema service to raise an exception
        self.mock_schema_service.list_tables.side_effect = Exception('Test error')

        # Call the analyze_query method
        result = self.query_analysis_service.analyze_query(
            'myks', 'SELECT * FROM users WHERE id = 1'
        )

        # Verify the result contains the error
        self.assertIn('Error analyzing query', result.performance_assessment)
        self.assertEqual(result.table_name, 'users')

    def test_analyze_query_with_allow_filtering(self):
        """Test analyzing a query with ALLOW FILTERING."""
        # Mock the schema service responses
        table_info_mock = Mock()
        type(table_info_mock).name = PropertyMock(return_value='users')
        self.mock_schema_service.list_tables.return_value = [table_info_mock]
        self.mock_schema_service.describe_table.return_value = {
            'columns': [
                {'name': 'id', 'is_partition_key': True},
                {'name': 'name', 'is_partition_key': False},
            ],
            'partition_key': ['id'],
            'clustering_columns': [],
            'indexes': [],
        }

        # Call the analyze_query method
        result = self.query_analysis_service.analyze_query(
            'myks', "SELECT * FROM users WHERE name = 'test' ALLOW FILTERING"
        )

        # Verify the result
        self.assertTrue(result.uses_allow_filtering)
        self.assertIn('ALLOW FILTERING', result.performance_assessment)
        self.assertIn('Avoid using ALLOW FILTERING', ' '.join(result.recommendations))

    def test_analyze_query_with_secondary_index(self):
        """Test analyzing a query that uses a secondary index."""
        table_info_mock = Mock()
        type(table_info_mock).name = PropertyMock(return_value='users')
        self.mock_schema_service.list_tables.return_value = [table_info_mock]
        self.mock_schema_service.describe_table.return_value = {
            'columns': [
                {'name': 'id', 'is_partition_key': True},
                {'name': 'name', 'is_partition_key': False},
            ],
            'partition_key': ['id'],
            'clustering_columns': [],
            'indexes': [{'options': {'target': 'name'}}],
        }

        # Call the analyze_query method
        result = self.query_analysis_service.analyze_query(
            'myks', "SELECT * FROM users WHERE name = 'test'"
        )

        # Verify the result
        self.assertTrue(result.uses_secondary_index)
        self.assertIn('SECONDARY INDEX USAGE', result.performance_assessment)
        self.assertIn('Monitor the performance', ' '.join(result.recommendations))

    def test_analyze_query_table_not_found(self):
        """Test analyzing a query when the table is not found."""
        # Mock the schema service responses
        self.mock_schema_service.list_tables.return_value = []

        # Call the analyze_query method
        result = self.query_analysis_service.analyze_query(
            'myks', 'SELECT * FROM users WHERE id = 1'
        )

        # Verify the result
        self.assertEqual(result.table_name, 'users')
        self.assertIn("Table 'users' not found", result.performance_assessment)
        self.assertIn('Verify the table name', result.recommendations[0])

    def test_analyze_query_unable_to_determine_table(self):
        """Test analyzing a query when the table name cannot be determined."""
        # Call the analyze_query method with a malformed query
        result = self.query_analysis_service.analyze_query(
            'myks',
            'SELECT * WHERE id = 1',  # Missing FROM clause
        )

        # Verify the result
        self.assertEqual(result.table_name, '')
        self.assertIn('Unable to determine table name', result.performance_assessment)
        self.assertIn('Ensure the query follows standard CQL', result.recommendations[0])


if __name__ == '__main__':
    unittest.main()
