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

"""Tests for MySQL plugin managed mode execution.

These tests cover the execute_managed_mode and _execute_query_batch methods
in the MySQLPlugin class which require mocking the MySQL MCP server connection.
"""

import pytest
from unittest.mock import patch


class TestMySQLManagedMode:
    """Test MySQL managed mode execution."""

    @pytest.mark.asyncio
    async def test_execute_managed_mode_success_with_performance_schema(
        self, mysql_plugin, mysql_connection_params
    ):
        """Test successful managed mode execution with performance schema enabled."""
        with patch('awslabs.dynamodb_mcp_server.db_analyzer.mysql.DBConnection'):
            with patch('awslabs.dynamodb_mcp_server.db_analyzer.mysql.mysql_query') as mock_query:
                mock_query.side_effect = [
                    [{'': '1'}],  # performance_schema_check - enabled
                    [{'table_name': 'users', 'row_count': 100}],  # comprehensive_table_analysis
                    [{'index_name': 'idx_users'}],  # comprehensive_index_analysis
                    [{'column_name': 'id'}],  # column_analysis
                    [{'constraint_name': 'fk_orders'}],  # foreign_key_analysis
                    [{'query_pattern': 'SELECT *'}],  # query_performance_stats
                    [{'trigger_name': 'trg_audit'}],  # triggers_stats
                ]

                result = await mysql_plugin.execute_managed_mode(mysql_connection_params)

                assert 'results' in result
                assert 'errors' in result
                assert result['performance_enabled'] is True
                assert result['performance_feature'] == 'Performance Schema'
                assert len(result['skipped_queries']) == 0

    @pytest.mark.asyncio
    async def test_execute_managed_mode_performance_schema_disabled(
        self, mysql_plugin, mysql_connection_params
    ):
        """Test managed mode when performance schema is disabled."""
        with patch('awslabs.dynamodb_mcp_server.db_analyzer.mysql.DBConnection'):
            with patch('awslabs.dynamodb_mcp_server.db_analyzer.mysql.mysql_query') as mock_query:
                mock_query.side_effect = [
                    [{'': '0'}],  # performance_schema_check - disabled
                    [{'table_name': 'users'}],  # comprehensive_table_analysis
                    [{'index_name': 'idx_users'}],  # comprehensive_index_analysis
                    [{'column_name': 'id'}],  # column_analysis
                    [{'constraint_name': 'fk_orders'}],  # foreign_key_analysis
                ]

                result = await mysql_plugin.execute_managed_mode(mysql_connection_params)

                assert result['performance_enabled'] is False
                assert len(result['skipped_queries']) > 0
                assert 'query_performance_stats' in result['skipped_queries']
                assert 'triggers_stats' in result['skipped_queries']

    @pytest.mark.asyncio
    async def test_execute_managed_mode_query_error(self, mysql_plugin, mysql_connection_params):
        """Test managed mode when a query returns an error."""
        with patch('awslabs.dynamodb_mcp_server.db_analyzer.mysql.DBConnection'):
            with patch('awslabs.dynamodb_mcp_server.db_analyzer.mysql.mysql_query') as mock_query:
                mock_query.side_effect = [
                    [{'': '1'}],  # performance_schema_check - enabled
                    [{'error': 'Access denied'}],  # comprehensive_table_analysis - error
                    [{'index_name': 'idx_users'}],  # comprehensive_index_analysis
                    [{'column_name': 'id'}],  # column_analysis
                    [{'constraint_name': 'fk_orders'}],  # foreign_key_analysis
                    [{'query_pattern': 'SELECT *'}],  # query_performance_stats
                    [{'trigger_name': 'trg_audit'}],  # triggers_stats
                ]

                result = await mysql_plugin.execute_managed_mode(mysql_connection_params)

                assert len(result['errors']) > 0
                assert any('Access denied' in err for err in result['errors'])

    @pytest.mark.asyncio
    async def test_execute_managed_mode_empty_results(self, mysql_plugin, mysql_connection_params):
        """Test managed mode when queries return empty results."""
        with patch('awslabs.dynamodb_mcp_server.db_analyzer.mysql.DBConnection'):
            with patch('awslabs.dynamodb_mcp_server.db_analyzer.mysql.mysql_query') as mock_query:
                mock_query.side_effect = [
                    [{'': '1'}],  # performance_schema_check - enabled
                    [],  # comprehensive_table_analysis - empty
                    [],  # comprehensive_index_analysis - empty
                    [],  # column_analysis - empty
                    [],  # foreign_key_analysis - empty
                    [],  # query_performance_stats - empty
                    [],  # triggers_stats - empty
                ]

                result = await mysql_plugin.execute_managed_mode(mysql_connection_params)

                assert 'results' in result
                for query_name in result['results']:
                    assert result['results'][query_name]['data'] == []

    @pytest.mark.asyncio
    async def test_execute_managed_mode_query_exception(
        self, mysql_plugin, mysql_connection_params
    ):
        """Test managed mode when a query raises an exception."""
        with patch('awslabs.dynamodb_mcp_server.db_analyzer.mysql.DBConnection'):
            with patch('awslabs.dynamodb_mcp_server.db_analyzer.mysql.mysql_query') as mock_query:
                mock_query.side_effect = [
                    [{'': '1'}],  # performance_schema_check - enabled
                    Exception('Connection timeout'),  # comprehensive_table_analysis - exception
                    [{'index_name': 'idx_users'}],  # comprehensive_index_analysis
                    [{'column_name': 'id'}],  # column_analysis
                    [{'constraint_name': 'fk_orders'}],  # foreign_key_analysis
                    [{'query_pattern': 'SELECT *'}],  # query_performance_stats
                    [{'trigger_name': 'trg_audit'}],  # triggers_stats
                ]

                result = await mysql_plugin.execute_managed_mode(mysql_connection_params)

                assert len(result['errors']) > 0
                assert any('Connection timeout' in err for err in result['errors'])

    @pytest.mark.asyncio
    async def test_execute_managed_mode_mysql_query_failure(
        self, mysql_plugin, mysql_connection_params
    ):
        """Test managed mode when mysql_query returns error dict."""
        with patch('awslabs.dynamodb_mcp_server.db_analyzer.mysql.DBConnection'):
            with patch('awslabs.dynamodb_mcp_server.db_analyzer.mysql.mysql_query') as mock_query:

                async def mock_query_with_error(*args, **kwargs):
                    return [{'error': 'MySQL query failed: Connection refused'}]

                mock_query.side_effect = mock_query_with_error

                result = await mysql_plugin.execute_managed_mode(mysql_connection_params)

                assert len(result['errors']) > 0


class TestMySQLExecuteQueryBatch:
    """Test the _execute_query_batch method."""

    @pytest.mark.asyncio
    async def test_execute_query_batch_success(self, mysql_plugin):
        """Test successful batch query execution."""
        all_results = {}
        all_errors = []

        async def mock_run_query(sql):
            return [{'table_name': 'users', 'row_count': 100}]

        await mysql_plugin._execute_query_batch(
            ['comprehensive_table_analysis'],
            'test_db',
            500,
            mock_run_query,
            all_results,
            all_errors,
        )

        assert 'comprehensive_table_analysis' in all_results
        assert len(all_errors) == 0
        assert all_results['comprehensive_table_analysis']['data'][0]['table_name'] == 'users'

    @pytest.mark.asyncio
    async def test_execute_query_batch_with_error_response(self, mysql_plugin):
        """Test batch execution when query returns error in response."""
        all_results = {}
        all_errors = []

        async def mock_run_query(sql):
            return [{'error': 'Permission denied'}]

        await mysql_plugin._execute_query_batch(
            ['comprehensive_table_analysis'],
            'test_db',
            500,
            mock_run_query,
            all_results,
            all_errors,
        )

        assert 'comprehensive_table_analysis' not in all_results
        assert len(all_errors) == 1
        assert 'Permission denied' in all_errors[0]

    @pytest.mark.asyncio
    async def test_execute_query_batch_with_exception(self, mysql_plugin):
        """Test batch execution when query raises exception."""
        all_results = {}
        all_errors = []

        async def mock_run_query(sql):
            raise Exception('Database connection lost')

        await mysql_plugin._execute_query_batch(
            ['comprehensive_table_analysis'],
            'test_db',
            500,
            mock_run_query,
            all_results,
            all_errors,
        )

        assert 'comprehensive_table_analysis' not in all_results
        assert len(all_errors) == 1
        assert 'Database connection lost' in all_errors[0]

    @pytest.mark.asyncio
    async def test_execute_query_batch_empty_result(self, mysql_plugin):
        """Test batch execution with empty result."""
        all_results = {}
        all_errors = []

        async def mock_run_query(sql):
            return []

        await mysql_plugin._execute_query_batch(
            ['comprehensive_table_analysis'],
            'test_db',
            500,
            mock_run_query,
            all_results,
            all_errors,
        )

        assert 'comprehensive_table_analysis' in all_results
        assert all_results['comprehensive_table_analysis']['data'] == []
        assert len(all_errors) == 0

    @pytest.mark.asyncio
    async def test_execute_query_batch_multiple_queries(self, mysql_plugin):
        """Test batch execution with multiple queries."""
        all_results = {}
        all_errors = []

        async def mock_run_query(sql):
            if 'table_analysis' in sql.lower() or 'TABLES' in sql:
                return [{'table_name': 'users'}]
            elif 'index' in sql.lower() or 'STATISTICS' in sql:
                return [{'index_name': 'idx_pk'}]
            return []

        await mysql_plugin._execute_query_batch(
            ['comprehensive_table_analysis', 'comprehensive_index_analysis'],
            'test_db',
            500,
            mock_run_query,
            all_results,
            all_errors,
        )

        assert len(all_results) == 2
        assert 'comprehensive_table_analysis' in all_results
        assert 'comprehensive_index_analysis' in all_results
        assert len(all_errors) == 0
