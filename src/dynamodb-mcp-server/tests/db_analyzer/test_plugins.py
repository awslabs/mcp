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

"""Tests for database analyzer plugins.

Tests core functionality including:
- Plugin query definitions and structure
- SQL generation (write_queries_to_file)
- Result parsing (parse_results_from_file) with markers
- Plugin registry operations
- Cross-plugin consistency
"""

import os
import pytest
import tempfile
from awslabs.dynamodb_mcp_server.db_analyzer.base_plugin import DatabasePlugin
from awslabs.dynamodb_mcp_server.db_analyzer.mysql import MySQLPlugin
from awslabs.dynamodb_mcp_server.db_analyzer.plugin_registry import PluginRegistry
from awslabs.dynamodb_mcp_server.db_analyzer.postgresql import PostgreSQLPlugin
from awslabs.dynamodb_mcp_server.db_analyzer.sqlserver import SQLServerPlugin


class TestPluginQueryDefinitions:
    """Test that all plugins have properly structured query definitions."""

    @pytest.mark.parametrize(
        'plugin_class,plugin_name',
        [
            (MySQLPlugin, 'MySQL'),
            (PostgreSQLPlugin, 'PostgreSQL'),
            (SQLServerPlugin, 'SQLServer'),
        ],
    )
    def test_plugin_has_required_queries(self, plugin_class, plugin_name):
        """Test that each plugin defines required schema queries."""
        plugin = plugin_class()
        queries = plugin.get_queries()

        required_queries = [
            'comprehensive_table_analysis',
            'comprehensive_index_analysis',
            'column_analysis',
            'foreign_key_analysis',
        ]

        for query_name in required_queries:
            assert query_name in queries, f"{plugin_name}: Missing required query '{query_name}'"

    @pytest.mark.parametrize('plugin_class', [MySQLPlugin, PostgreSQLPlugin, SQLServerPlugin])
    def test_query_structure(self, plugin_class):
        """Test that all queries have required fields."""
        plugin = plugin_class()
        queries = plugin.get_queries()

        for query_name, query_info in queries.items():
            if query_info.get('category') == 'internal':
                continue

            assert 'description' in query_info, f"{query_name}: Missing 'description'"
            assert 'category' in query_info, f"{query_name}: Missing 'category'"
            assert 'sql' in query_info, f"{query_name}: Missing 'sql'"
            assert 'parameters' in query_info, f"{query_name}: Missing 'parameters'"

            assert query_info['category'] in [
                'information_schema',
                'performance_schema',
                'internal',
            ], f"{query_name}: Invalid category '{query_info['category']}'"

    @pytest.mark.parametrize('plugin_class', [MySQLPlugin, PostgreSQLPlugin, SQLServerPlugin])
    def test_helper_functions(self, plugin_class):
        """Test that helper functions work correctly."""
        plugin = plugin_class()

        schema_queries = plugin.get_queries_by_category('information_schema')
        assert len(schema_queries) >= 4, 'Should have at least 4 schema queries'

        descriptions = plugin.get_query_descriptions()
        assert len(descriptions) > 0, 'Should have query descriptions'
        for query_name, desc in descriptions.items():
            assert isinstance(desc, str), f'{query_name}: Description must be string'
            assert len(desc) > 0, f'{query_name}: Description cannot be empty'


class TestSQLGeneration:
    """Test SQL file generation with markers."""

    @pytest.mark.parametrize(
        'plugin_class,db_name',
        [
            (MySQLPlugin, 'test_db'),
            (PostgreSQLPlugin, 'test_db'),
            (SQLServerPlugin, 'test_db'),
        ],
    )
    def test_write_queries_to_file(self, plugin_class, db_name):
        """Test that SQL files are generated with proper markers."""
        plugin = plugin_class()

        with tempfile.TemporaryDirectory() as tmpdir:
            output_file = os.path.join(tmpdir, 'queries.sql')
            result = plugin.write_queries_to_file(db_name, 500, output_file)

            assert result == output_file
            assert os.path.exists(output_file)

            with open(output_file, 'r', encoding='utf-8') as f:
                content = f.read()

            assert len(content) > 0
            assert "SELECT '-- QUERY_NAME_START:" in content
            assert "SELECT '-- QUERY_NAME_END:" in content

    def test_mysql_uses_limit(self, mysql_plugin):
        """Test that MySQL uses LIMIT syntax."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_file = os.path.join(tmpdir, 'queries.sql')
            mysql_plugin.write_queries_to_file('test_db', 100, output_file)

            with open(output_file, 'r', encoding='utf-8') as f:
                content = f.read()

            assert 'LIMIT 100' in content

    def test_sqlserver_uses_top(self, sqlserver_plugin):
        """Test that SQL Server uses TOP syntax."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_file = os.path.join(tmpdir, 'queries.sql')
            sqlserver_plugin.write_queries_to_file('test_db', 100, output_file)

            with open(output_file, 'r', encoding='utf-8') as f:
                content = f.read()

            assert 'TOP 100' in content


class TestResultParsing:
    """Test parsing of query results with markers."""

    @pytest.mark.parametrize('plugin_class', [MySQLPlugin, PostgreSQLPlugin, SQLServerPlugin])
    def test_parse_with_pipe_separated_markers(self, plugin_class):
        """Test parsing pipe-separated format."""
        plugin = plugin_class()

        sample_data = """| marker |
| -- QUERY_NAME_START: comprehensive_table_analysis |
+------------+-----------+
| table_name | row_count |
+------------+-----------+
| users      |      1000 |
| orders     |      5000 |
+------------+-----------+
| marker |
| -- QUERY_NAME_END: comprehensive_table_analysis |
"""

        with tempfile.TemporaryDirectory() as tmpdir:
            result_file = os.path.join(tmpdir, 'results.txt')
            with open(result_file, 'w', encoding='utf-8') as f:
                f.write(sample_data)

            results = plugin.parse_results_from_file(result_file)

            assert 'comprehensive_table_analysis' in results
            assert len(results['comprehensive_table_analysis']['data']) == 2
            assert results['comprehensive_table_analysis']['data'][0]['table_name'] == 'users'
            assert results['comprehensive_table_analysis']['data'][0]['row_count'] == 1000

    def test_parse_with_tab_separated_format(self, mysql_plugin):
        """Test parsing tab-separated format."""
        sample_data = """-- QUERY_NAME_START: test_query
col1\tcol2
val1\t123
-- QUERY_NAME_END: test_query
"""

        with tempfile.TemporaryDirectory() as tmpdir:
            result_file = os.path.join(tmpdir, 'results.txt')
            with open(result_file, 'w', encoding='utf-8') as f:
                f.write(sample_data)

            results = mysql_plugin.parse_results_from_file(result_file)

            assert 'test_query' in results
            assert len(results['test_query']['data']) == 1
            assert results['test_query']['data'][0]['col1'] == 'val1'

    def test_parse_comment_style_markers(self, mysql_plugin):
        """Test parsing with comment-style markers (-- QUERY_NAME_START)."""
        sample_data = """-- QUERY_NAME_START: test_query
col1\tcol2
val1\t123
-- QUERY_NAME_END: test_query
"""

        with tempfile.TemporaryDirectory() as tmpdir:
            result_file = os.path.join(tmpdir, 'results.txt')
            with open(result_file, 'w', encoding='utf-8') as f:
                f.write(sample_data)

            results = mysql_plugin.parse_results_from_file(result_file)

            assert 'test_query' in results
            assert len(results['test_query']['data']) == 1

    def test_parse_empty_result(self, mysql_plugin):
        """Test parsing query with 0 rows."""
        sample_data = """| marker |
| -- QUERY_NAME_START: triggers_stats |
| marker |
| -- QUERY_NAME_END: triggers_stats |
"""

        with tempfile.TemporaryDirectory() as tmpdir:
            result_file = os.path.join(tmpdir, 'results.txt')
            with open(result_file, 'w', encoding='utf-8') as f:
                f.write(sample_data)

            results = mysql_plugin.parse_results_from_file(result_file)

            assert 'triggers_stats' in results
            assert results['triggers_stats']['data'] == []

    def test_parse_multiple_queries(self, mysql_plugin):
        """Test parsing multiple queries in one file."""
        sample_data = """| marker |
| -- QUERY_NAME_START: query1 |
| col1 |
| val1 |
| marker |
| -- QUERY_NAME_END: query1 |

| marker |
| -- QUERY_NAME_START: query2 |
| col2 |
| val2 |
| marker |
| -- QUERY_NAME_END: query2 |
"""

        with tempfile.TemporaryDirectory() as tmpdir:
            result_file = os.path.join(tmpdir, 'results.txt')
            with open(result_file, 'w', encoding='utf-8') as f:
                f.write(sample_data)

            results = mysql_plugin.parse_results_from_file(result_file)

            assert len(results) == 2
            assert 'query1' in results
            assert 'query2' in results

    def test_parse_file_not_found(self, mysql_plugin):
        """Test parsing non-existent file raises error."""
        with pytest.raises(FileNotFoundError):
            mysql_plugin.parse_results_from_file('/nonexistent/file.txt')

    def test_data_type_conversion(self, mysql_plugin):
        """Test that data types are converted correctly."""
        sample_data = """| marker |
| -- QUERY_NAME_START: test_query |
| string | int | float | null |
| text | 123 | 45.67 | NULL |
| marker |
| -- QUERY_NAME_END: test_query |
"""

        with tempfile.TemporaryDirectory() as tmpdir:
            result_file = os.path.join(tmpdir, 'results.txt')
            with open(result_file, 'w', encoding='utf-8') as f:
                f.write(sample_data)

            results = mysql_plugin.parse_results_from_file(result_file)
            row = results['test_query']['data'][0]

            assert isinstance(row['string'], str)
            assert isinstance(row['int'], int)
            assert isinstance(row['float'], float)
            assert row['null'] is None

    def test_convert_negative_numbers(self, mysql_plugin):
        """Test that negative numbers are converted correctly."""
        sample_data = """| marker |
| -- QUERY_NAME_START: test_query |
| int_col | float_col |
| -123 | -45.67 |
| marker |
| -- QUERY_NAME_END: test_query |
"""

        with tempfile.TemporaryDirectory() as tmpdir:
            result_file = os.path.join(tmpdir, 'results.txt')
            with open(result_file, 'w', encoding='utf-8') as f:
                f.write(sample_data)

            results = mysql_plugin.parse_results_from_file(result_file)
            data = results['test_query']['data'][0]

            assert data['int_col'] == -123
            assert data['float_col'] == -45.67

    def test_convert_none_values(self, mysql_plugin):
        """Test that 'none' string is converted to None."""
        sample_data = """| marker |
| -- QUERY_NAME_START: test_query |
| col1 | col2 |
| none | value |
| marker |
| -- QUERY_NAME_END: test_query |
"""

        with tempfile.TemporaryDirectory() as tmpdir:
            result_file = os.path.join(tmpdir, 'results.txt')
            with open(result_file, 'w', encoding='utf-8') as f:
                f.write(sample_data)

            results = mysql_plugin.parse_results_from_file(result_file)
            data = results['test_query']['data'][0]

            assert data['col1'] is None
            assert data['col2'] == 'value'

    def test_value_error_during_conversion(self, mysql_plugin):
        """Test that ValueError during numeric conversion falls back to string."""
        sample_data = """| marker |
| -- QUERY_NAME_START: test_query |
| col1 |
| 123.456.789 |
| marker |
| -- QUERY_NAME_END: test_query |
"""

        with tempfile.TemporaryDirectory() as tmpdir:
            result_file = os.path.join(tmpdir, 'results.txt')
            with open(result_file, 'w', encoding='utf-8') as f:
                f.write(sample_data)

            results = mysql_plugin.parse_results_from_file(result_file)
            data = results['test_query']['data'][0]

            assert data['col1'] == '123.456.789'

    def test_skip_row_with_wrong_column_count(self, mysql_plugin):
        """Test that rows with wrong column count are skipped."""
        sample_data = """| marker |
| -- QUERY_NAME_START: test_query |
| col1 | col2 | col3 |
| val1 | val2 | val3 |
| only_one |
| val4 | val5 | val6 |
| marker |
| -- QUERY_NAME_END: test_query |
"""

        with tempfile.TemporaryDirectory() as tmpdir:
            result_file = os.path.join(tmpdir, 'results.txt')
            with open(result_file, 'w', encoding='utf-8') as f:
                f.write(sample_data)

            results = mysql_plugin.parse_results_from_file(result_file)

            assert len(results['test_query']['data']) == 2

    def test_skip_row_count_line(self, mysql_plugin):
        """Test that row count lines like '(5 rows)' are skipped."""
        sample_data = """-- QUERY_NAME_START: test_query
col1\tcol2
val1\t100
val2\t200
(2 rows)
-- QUERY_NAME_END: test_query
"""

        with tempfile.TemporaryDirectory() as tmpdir:
            result_file = os.path.join(tmpdir, 'results.txt')
            with open(result_file, 'w', encoding='utf-8') as f:
                f.write(sample_data)

            results = mysql_plugin.parse_results_from_file(result_file)

            assert len(results['test_query']['data']) == 2

    def test_save_last_query_without_end_marker(self, mysql_plugin):
        """Test that last query data is saved at end of file."""
        sample_data = """-- QUERY_NAME_START: test_query
col1\tcol2
val1\t123
"""

        with tempfile.TemporaryDirectory() as tmpdir:
            result_file = os.path.join(tmpdir, 'results.txt')
            with open(result_file, 'w', encoding='utf-8') as f:
                f.write(sample_data)

            results = mysql_plugin.parse_results_from_file(result_file)

            assert 'test_query' in results
            assert len(results['test_query']['data']) == 1

    def test_skip_line_without_separator(self, mysql_plugin):
        """Test that lines without tab or pipe are skipped."""
        sample_data = """-- QUERY_NAME_START: test_query
col1\tcol2
val1\t123
this line has no separator
val2\t456
-- QUERY_NAME_END: test_query
"""

        with tempfile.TemporaryDirectory() as tmpdir:
            result_file = os.path.join(tmpdir, 'results.txt')
            with open(result_file, 'w', encoding='utf-8') as f:
                f.write(sample_data)

            results = mysql_plugin.parse_results_from_file(result_file)

            assert len(results['test_query']['data']) == 2


class TestPathTraversalDetection:
    """Test path traversal detection in parse_results_from_file."""

    def test_path_traversal_with_double_dots(self, mysql_plugin):
        """Test that path traversal with .. is detected."""
        with pytest.raises(ValueError, match='Path traversal detected'):
            mysql_plugin.parse_results_from_file('../../../etc/passwd')

    def test_path_traversal_in_middle_of_path(self, mysql_plugin):
        """Test that path traversal in middle of path is detected."""
        with pytest.raises(ValueError, match='Path traversal detected'):
            mysql_plugin.parse_results_from_file('/tmp/safe/../../../etc/passwd')


class TestPluginRegistry:
    """Test plugin registry functionality."""

    def test_all_plugins_instantiate(self):
        """Test that all plugins can be instantiated."""
        plugins = [MySQLPlugin(), PostgreSQLPlugin(), SQLServerPlugin()]

        for plugin in plugins:
            assert plugin is not None
            assert hasattr(plugin, 'get_queries')
            assert hasattr(plugin, 'write_queries_to_file')
            assert hasattr(plugin, 'parse_results_from_file')

    def test_plugin_methods_return_correct_types(self, mysql_plugin):
        """Test that plugin methods return expected types."""
        queries = mysql_plugin.get_queries()
        assert isinstance(queries, dict)

        with tempfile.TemporaryDirectory() as tmpdir:
            output_file = os.path.join(tmpdir, 'test.sql')
            result = mysql_plugin.write_queries_to_file('test_db', 100, output_file)
            assert isinstance(result, str)
            assert result == output_file


class TestPluginRegistryOperations:
    """Test plugin registry operations."""

    def test_get_plugin_mysql(self):
        """Test getting MySQL plugin from registry."""
        plugin = PluginRegistry.get_plugin('mysql')
        assert isinstance(plugin, MySQLPlugin)

    def test_get_plugin_postgresql(self):
        """Test getting PostgreSQL plugin from registry."""
        plugin = PluginRegistry.get_plugin('postgresql')
        assert isinstance(plugin, PostgreSQLPlugin)

    def test_get_plugin_sqlserver(self):
        """Test getting SQL Server plugin from registry."""
        plugin = PluginRegistry.get_plugin('sqlserver')
        assert isinstance(plugin, SQLServerPlugin)

    def test_get_plugin_case_insensitive(self):
        """Test that plugin lookup is case-insensitive."""
        plugin1 = PluginRegistry.get_plugin('MySQL')
        plugin2 = PluginRegistry.get_plugin('MYSQL')
        plugin3 = PluginRegistry.get_plugin('mysql')

        assert isinstance(plugin1, MySQLPlugin)
        assert isinstance(plugin2, MySQLPlugin)
        assert isinstance(plugin3, MySQLPlugin)

    def test_get_plugin_unsupported_type(self):
        """Test that unsupported database type raises ValueError."""
        with pytest.raises(ValueError, match='Unsupported database type'):
            PluginRegistry.get_plugin('oracle')

    def test_get_supported_types(self):
        """Test getting list of supported database types."""
        supported = PluginRegistry.get_supported_types()

        assert isinstance(supported, list)
        assert 'mysql' in supported
        assert 'postgresql' in supported
        assert 'sqlserver' in supported

    def test_register_plugin(self):
        """Test registering a custom plugin."""

        class MockPlugin(DatabasePlugin):
            """Mock plugin for testing."""

            def get_queries(self):
                return {}

            def get_database_display_name(self):
                return 'MockDB'

            async def execute_managed_mode(self, connection_params):
                return {'results': {}, 'errors': []}

        PluginRegistry.register_plugin('mock_db', MockPlugin)

        assert 'mock_db' in PluginRegistry.get_supported_types()
        plugin = PluginRegistry.get_plugin('mock_db')
        assert isinstance(plugin, MockPlugin)

    def test_register_plugin_invalid_type(self):
        """Test that registering non-DatabasePlugin class raises TypeError."""

        class NotAPlugin:
            pass

        with pytest.raises(TypeError, match='must inherit from DatabasePlugin'):
            PluginRegistry.register_plugin('invalid', NotAPlugin)


class TestManagedModeNotImplemented:
    """Test managed mode NotImplementedError for unsupported plugins."""

    @pytest.mark.asyncio
    async def test_postgresql_managed_mode_not_implemented(self, postgresql_plugin):
        """Test that PostgreSQL managed mode raises NotImplementedError."""
        with pytest.raises(NotImplementedError, match='Managed mode is not yet implemented'):
            await postgresql_plugin.execute_managed_mode({'database': 'test_db'})

    @pytest.mark.asyncio
    async def test_sqlserver_managed_mode_not_implemented(self, sqlserver_plugin):
        """Test that SQL Server managed mode raises NotImplementedError."""
        with pytest.raises(NotImplementedError, match='Managed mode is not yet implemented'):
            await sqlserver_plugin.execute_managed_mode({'database': 'test_db'})


class TestCrossPluginConsistency:
    """Test consistency across different database plugins."""

    def test_all_plugins_have_schema_queries(self):
        """Test that all plugins define the same core schema queries."""
        plugins = {
            'MySQL': MySQLPlugin(),
            'PostgreSQL': PostgreSQLPlugin(),
            'SQLServer': SQLServerPlugin(),
        }

        core_queries = [
            'comprehensive_table_analysis',
            'comprehensive_index_analysis',
            'column_analysis',
            'foreign_key_analysis',
        ]

        for plugin_name, plugin in plugins.items():
            schema_queries = plugin.get_queries_by_category('information_schema')
            for query in core_queries:
                assert query in schema_queries, f"{plugin_name}: Missing core query '{query}'"

    def test_query_descriptions_not_empty(self):
        """Test that all queries have non-empty descriptions."""
        plugins = [MySQLPlugin(), PostgreSQLPlugin(), SQLServerPlugin()]

        for plugin in plugins:
            descriptions = plugin.get_query_descriptions()
            for query_name, desc in descriptions.items():
                assert desc and len(desc) > 0, f'{query_name}: Description should not be empty'


class TestBasePluginHelperMethods:
    """Test base plugin helper methods."""

    @pytest.mark.parametrize('plugin_class', [MySQLPlugin, PostgreSQLPlugin, SQLServerPlugin])
    def test_get_schema_queries(self, plugin_class):
        """Test get_schema_queries returns only information_schema queries."""
        plugin = plugin_class()
        schema_queries = plugin.get_schema_queries()

        assert isinstance(schema_queries, list)
        assert len(schema_queries) >= 4

        all_queries = plugin.get_queries()
        for query_name in schema_queries:
            assert query_name in all_queries
            assert all_queries[query_name]['category'] == 'information_schema'

    @pytest.mark.parametrize('plugin_class', [MySQLPlugin, PostgreSQLPlugin, SQLServerPlugin])
    def test_get_performance_queries(self, plugin_class):
        """Test get_performance_queries returns only performance_schema queries."""
        plugin = plugin_class()
        perf_queries = plugin.get_performance_queries()

        assert isinstance(perf_queries, list)

        all_queries = plugin.get_queries()
        for query_name in perf_queries:
            assert query_name in all_queries
            assert all_queries[query_name]['category'] == 'performance_schema'

    def test_get_queries_by_category_internal(self, mysql_plugin):
        """Test get_queries_by_category for internal queries."""
        internal_queries = mysql_plugin.get_queries_by_category('internal')

        assert isinstance(internal_queries, list)
        assert 'performance_schema_check' in internal_queries

    def test_get_query_descriptions_excludes_internal(self, mysql_plugin):
        """Test that get_query_descriptions excludes internal queries."""
        descriptions = mysql_plugin.get_query_descriptions()

        assert 'performance_schema_check' not in descriptions
        assert 'comprehensive_table_analysis' in descriptions

    @pytest.mark.parametrize('plugin_class', [MySQLPlugin, PostgreSQLPlugin, SQLServerPlugin])
    def test_apply_result_limit(self, plugin_class):
        """Test apply_result_limit for different database types."""
        plugin = plugin_class()
        sql = 'SELECT * FROM users'
        result = plugin.apply_result_limit(sql, 100)

        if isinstance(plugin, SQLServerPlugin):
            assert 'TOP 100' in result
        else:
            assert 'LIMIT 100' in result
