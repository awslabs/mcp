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
import unittest.mock as mock
from awslabs.dynamodb_mcp_server.db_analyzer.base_plugin import DatabasePlugin
from awslabs.dynamodb_mcp_server.db_analyzer.mysql import MySQLPlugin
from awslabs.dynamodb_mcp_server.db_analyzer.oracle import OraclePlugin
from awslabs.dynamodb_mcp_server.db_analyzer.plugin_registry import PluginRegistry
from awslabs.dynamodb_mcp_server.db_analyzer.postgresql import PostgreSQLPlugin
from awslabs.dynamodb_mcp_server.db_analyzer.sqlserver import SQLServerPlugin


ALL_PLUGIN_CLASSES = [MySQLPlugin, OraclePlugin, PostgreSQLPlugin, SQLServerPlugin]


class _StubPlugin(DatabasePlugin):
    """Minimal DatabasePlugin for testing base class behavior directly."""

    def __init__(self, queries=None):
        self._queries = queries or {}

    def get_queries(self):
        return self._queries

    def get_database_display_name(self):
        return 'StubDB'

    async def execute_managed_mode(self, connection_params):
        return {}


class TestPluginQueryDefinitions:
    """Test that all plugins have properly structured query definitions."""

    @pytest.mark.parametrize('plugin_class', ALL_PLUGIN_CLASSES)
    def test_query_structure(self, plugin_class):
        """Test that all queries have required fields."""
        plugin = plugin_class()
        queries = plugin.get_queries()

        for query_name, query_info in queries.items():
            if query_info.get('category') == 'internal':
                continue

            assert 'name' in query_info, f"{query_name}: Missing 'name'"
            assert 'description' in query_info, f"{query_name}: Missing 'description'"
            assert 'category' in query_info, f"{query_name}: Missing 'category'"
            assert 'sql' in query_info, f"{query_name}: Missing 'sql'"
            assert 'parameters' in query_info, f"{query_name}: Missing 'parameters'"

            assert query_info['category'] in [
                'information_schema',
                'performance_schema',
                'internal',
            ], f"{query_name}: Invalid category '{query_info['category']}'"


class TestSQLGeneration:
    """Test SQL file generation with markers."""

    @pytest.mark.parametrize('plugin_class', ALL_PLUGIN_CLASSES)
    def test_write_queries_to_file(self, plugin_class):
        """Test that SQL files are generated with proper markers."""
        plugin = plugin_class()

        with tempfile.TemporaryDirectory() as tmpdir:
            output_file = os.path.join(tmpdir, 'queries.sql')
            result = plugin.write_queries_to_file('test_db', 500, output_file)

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

    def test_oracle_uses_fetch_first(self, oracle_plugin):
        """Test that Oracle uses FETCH FIRST syntax."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_file = os.path.join(tmpdir, 'queries.sql')
            oracle_plugin.write_queries_to_file('test_db', 100, output_file)

            with open(output_file, 'r', encoding='utf-8') as f:
                content = f.read()

            assert 'FETCH FIRST 100 ROWS ONLY' in content

    def test_oracle_write_queries_prerequisites(self, oracle_plugin):
        """Test that Oracle generated SQL includes prerequisites section."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_file = os.path.join(tmpdir, 'queries.sql')
            oracle_plugin.write_queries_to_file('test_db', 500, output_file)

            with open(output_file, 'r', encoding='utf-8') as f:
                content = f.read()

            # Prerequisites check is present
            assert 'QUERY_NAME_START: prerequisites_check' in content
            assert 'QUERY_NAME_END: prerequisites_check' in content
            # Flush block is present
            assert 'DBMS_STATS.FLUSH_DATABASE_MONITORING_INFO' in content
            # AWR access check warning is present
            assert 'AWR (ENTERPRISE EDITION ONLY)' in content

    def test_oracle_write_queries_uses_from_dual(self, oracle_plugin):
        """Test that Oracle markers use FROM DUAL syntax."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_file = os.path.join(tmpdir, 'queries.sql')
            oracle_plugin.write_queries_to_file('test_db', 500, output_file)

            with open(output_file, 'r', encoding='utf-8') as f:
                content = f.read()

            assert 'AS marker FROM DUAL' in content
            # Should NOT have bare marker selects without FROM DUAL
            assert 'AS marker;' not in content.replace('AS marker FROM DUAL;', '')

    def test_oracle_write_queries_ordering(self, oracle_plugin):
        """Test that Oracle puts performance queries last, with V$SQL before AWR."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_file = os.path.join(tmpdir, 'queries.sql')
            oracle_plugin.write_queries_to_file('test_db', 500, output_file)

            with open(output_file, 'r', encoding='utf-8') as f:
                content = f.read()

            # Both performance queries should appear after all schema queries
            vsql_pos = content.index('QUERY_NAME_START: query_performance_stats_vsql')
            # Use the quote-terminated form to avoid matching the _vsql variant
            awr_pos = content.index("QUERY_NAME_START: query_performance_stats'")
            for query in [
                'comprehensive_table_analysis',
                'comprehensive_index_analysis',
                'column_analysis',
                'constraint_analysis',
                'foreign_key_analysis',
            ]:
                schema_pos = content.index(f'QUERY_NAME_START: {query}')
                assert schema_pos < vsql_pos, (
                    f'{query} should appear before query_performance_stats_vsql'
                )
                assert schema_pos < awr_pos, (
                    f'{query} should appear before query_performance_stats'
                )

            # V$SQL should come before AWR query so data is captured even if AWR errors
            assert vsql_pos < awr_pos, (
                'query_performance_stats_vsql (V$SQL) should appear before query_performance_stats (AWR)'
            )

    def test_oracle_write_queries_uses_dba_segments(self, oracle_plugin):
        """Test that Oracle uses DBA_SEGMENTS for enterprise mode."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_file = os.path.join(tmpdir, 'queries.sql')
            oracle_plugin.write_queries_to_file('test_db', 500, output_file)

            with open(output_file, 'r', encoding='utf-8') as f:
                content = f.read()

            assert 'DBA_SEGMENTS' in content
            assert 'USER_SEGMENTS' not in content


class TestResultParsing:
    """Test parsing of query results with markers."""

    @pytest.mark.parametrize('plugin_class', ALL_PLUGIN_CLASSES)
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

    @pytest.mark.parametrize('plugin_class', ALL_PLUGIN_CLASSES)
    def test_parse_with_tab_separated_format(self, plugin_class):
        """Test parsing tab-separated format."""
        plugin = plugin_class()
        sample_data = """-- QUERY_NAME_START: test_query
col1\tcol2
val1\t123
-- QUERY_NAME_END: test_query
"""

        with tempfile.TemporaryDirectory() as tmpdir:
            result_file = os.path.join(tmpdir, 'results.txt')
            with open(result_file, 'w', encoding='utf-8') as f:
                f.write(sample_data)

            results = plugin.parse_results_from_file(result_file)

            assert 'test_query' in results
            assert len(results['test_query']['data']) == 1
            assert results['test_query']['data'][0]['col1'] == 'val1'

    @pytest.mark.parametrize('plugin_class', ALL_PLUGIN_CLASSES)
    def test_parse_empty_result(self, plugin_class):
        """Test parsing query with 0 rows."""
        plugin = plugin_class()
        sample_data = """| marker |
| -- QUERY_NAME_START: triggers_stats |
| marker |
| -- QUERY_NAME_END: triggers_stats |
"""

        with tempfile.TemporaryDirectory() as tmpdir:
            result_file = os.path.join(tmpdir, 'results.txt')
            with open(result_file, 'w', encoding='utf-8') as f:
                f.write(sample_data)

            results = plugin.parse_results_from_file(result_file)

            assert 'triggers_stats' in results
            assert results['triggers_stats']['data'] == []

    @pytest.mark.parametrize('plugin_class', ALL_PLUGIN_CLASSES)
    def test_parse_multiple_queries(self, plugin_class):
        """Test parsing multiple queries in one file."""
        plugin = plugin_class()
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

            results = plugin.parse_results_from_file(result_file)

            assert len(results) == 2
            assert 'query1' in results
            assert 'query2' in results

    @pytest.mark.parametrize('plugin_class', ALL_PLUGIN_CLASSES)
    def test_parse_file_not_found(self, plugin_class):
        """Test parsing non-existent file raises error."""
        plugin = plugin_class()
        with pytest.raises(FileNotFoundError):
            plugin.parse_results_from_file('/nonexistent/file.txt')

    @pytest.mark.parametrize('plugin_class', ALL_PLUGIN_CLASSES)
    def test_data_type_conversion(self, plugin_class):
        """Test that data types are converted correctly."""
        plugin = plugin_class()
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

            results = plugin.parse_results_from_file(result_file)
            row = results['test_query']['data'][0]

            assert isinstance(row['string'], str)
            assert isinstance(row['int'], int)
            assert isinstance(row['float'], float)
            assert row['null'] is None

    @pytest.mark.parametrize('plugin_class', ALL_PLUGIN_CLASSES)
    def test_convert_negative_numbers(self, plugin_class):
        """Test that negative numbers are converted correctly."""
        plugin = plugin_class()
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

            results = plugin.parse_results_from_file(result_file)
            data = results['test_query']['data'][0]

            assert data['int_col'] == -123
            assert data['float_col'] == -45.67

    @pytest.mark.parametrize('plugin_class', ALL_PLUGIN_CLASSES)
    def test_convert_none_values(self, plugin_class):
        """Test that 'none' string is converted to None."""
        plugin = plugin_class()
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

            results = plugin.parse_results_from_file(result_file)
            data = results['test_query']['data'][0]

            assert data['col1'] is None
            assert data['col2'] == 'value'

    @pytest.mark.parametrize('plugin_class', ALL_PLUGIN_CLASSES)
    def test_value_error_during_conversion(self, plugin_class):
        """Test that ValueError during numeric conversion falls back to string."""
        plugin = plugin_class()
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

            results = plugin.parse_results_from_file(result_file)
            data = results['test_query']['data'][0]

            assert data['col1'] == '123.456.789'

    @pytest.mark.parametrize('plugin_class', ALL_PLUGIN_CLASSES)
    def test_skip_row_with_wrong_column_count(self, plugin_class):
        """Test that rows with wrong column count are skipped."""
        plugin = plugin_class()
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

            results = plugin.parse_results_from_file(result_file)

            assert len(results['test_query']['data']) == 2

    @pytest.mark.parametrize('plugin_class', ALL_PLUGIN_CLASSES)
    def test_skip_row_count_line(self, plugin_class):
        """Test that row count lines like '(5 rows)' are skipped."""
        plugin = plugin_class()
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

            results = plugin.parse_results_from_file(result_file)

            assert len(results['test_query']['data']) == 2

    @pytest.mark.parametrize('plugin_class', ALL_PLUGIN_CLASSES)
    def test_save_last_query_without_end_marker(self, plugin_class):
        """Test that last query data is saved at end of file."""
        plugin = plugin_class()
        sample_data = """-- QUERY_NAME_START: test_query
col1\tcol2
val1\t123
"""

        with tempfile.TemporaryDirectory() as tmpdir:
            result_file = os.path.join(tmpdir, 'results.txt')
            with open(result_file, 'w', encoding='utf-8') as f:
                f.write(sample_data)

            results = plugin.parse_results_from_file(result_file)

            assert 'test_query' in results
            assert len(results['test_query']['data']) == 1

    @pytest.mark.parametrize('plugin_class', ALL_PLUGIN_CLASSES)
    def test_skip_line_without_separator(self, plugin_class):
        """Test that lines without tab or pipe are skipped."""
        plugin = plugin_class()
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

            results = plugin.parse_results_from_file(result_file)

            assert len(results['test_query']['data']) == 2


class TestPathTraversalDetection:
    """Test path traversal detection in parse_results_from_file."""

    @pytest.mark.parametrize('plugin_class', ALL_PLUGIN_CLASSES)
    def test_path_traversal_with_double_dots(self, plugin_class):
        """Test that path traversal with .. is detected."""
        plugin = plugin_class()
        with pytest.raises(ValueError, match='Path traversal detected'):
            plugin.parse_results_from_file('../../../etc/passwd')

    @pytest.mark.parametrize('plugin_class', ALL_PLUGIN_CLASSES)
    def test_path_traversal_in_middle_of_path(self, plugin_class):
        """Test that path traversal in middle of path is detected."""
        plugin = plugin_class()
        with pytest.raises(ValueError, match='Path traversal detected'):
            plugin.parse_results_from_file('/tmp/safe/../../../etc/passwd')


class TestPluginRegistry:
    """Test plugin registry functionality."""

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

    @pytest.mark.parametrize(
        'db_type,expected_class',
        [
            ('mysql', MySQLPlugin),
            ('postgresql', PostgreSQLPlugin),
            ('sqlserver', SQLServerPlugin),
            ('oracle', OraclePlugin),
        ],
    )
    def test_get_plugin(self, db_type, expected_class):
        """Test getting plugin from registry by type."""
        plugin = PluginRegistry.get_plugin(db_type)
        assert isinstance(plugin, expected_class)

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
            PluginRegistry.get_plugin('mongodb')

    def test_get_supported_types(self):
        """Test getting list of supported database types."""
        supported = PluginRegistry.get_supported_types()

        assert isinstance(supported, list)
        assert 'mysql' in supported
        assert 'oracle' in supported
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

    # MySQL excluded — it implements managed mode via RDS Data API / direct connection
    @pytest.mark.asyncio
    @pytest.mark.parametrize('plugin_class', [PostgreSQLPlugin, SQLServerPlugin, OraclePlugin])
    async def test_managed_mode_not_implemented(self, plugin_class):
        """Test that managed mode raises NotImplementedError for unsupported plugins."""
        plugin = plugin_class()
        with pytest.raises(NotImplementedError, match='Managed mode is not yet implemented'):
            await plugin.execute_managed_mode({'database': 'test_db'})


class TestCrossPluginConsistency:
    """Test consistency across different database plugins."""

    @pytest.mark.parametrize('plugin_class', ALL_PLUGIN_CLASSES)
    def test_plugin_has_core_schema_queries(self, plugin_class):
        """Test that each plugin defines the core schema queries."""
        plugin = plugin_class()
        schema_queries = plugin.get_queries_by_category('information_schema')

        core_queries = [
            'comprehensive_table_analysis',
            'comprehensive_index_analysis',
            'column_analysis',
            'foreign_key_analysis',
        ]
        for query in core_queries:
            assert query in schema_queries, (
                f"{plugin.get_database_display_name()}: Missing core query '{query}'"
            )

    @pytest.mark.parametrize('plugin_class', ALL_PLUGIN_CLASSES)
    def test_query_descriptions_not_empty(self, plugin_class):
        """Test that all queries have non-empty descriptions."""
        plugin = plugin_class()
        descriptions = plugin.get_query_descriptions()
        for query_name, desc in descriptions.items():
            assert desc and len(desc) > 0, f'{query_name}: Description should not be empty'


class TestBasePluginHelperMethods:
    """Test base plugin helper methods."""

    @pytest.mark.parametrize('plugin_class', ALL_PLUGIN_CLASSES)
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

    @pytest.mark.parametrize('plugin_class', ALL_PLUGIN_CLASSES)
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

    @pytest.mark.parametrize('plugin_class', ALL_PLUGIN_CLASSES)
    def test_apply_result_limit(self, plugin_class):
        """Test apply_result_limit for different database types."""
        plugin = plugin_class()
        sql = 'SELECT * FROM users'
        result = plugin.apply_result_limit(sql, 100)

        if isinstance(plugin, SQLServerPlugin):
            assert 'TOP 100' in result
        elif isinstance(plugin, OraclePlugin):
            assert 'FETCH FIRST 100 ROWS ONLY' in result
        else:
            assert 'LIMIT 100' in result


class TestRunInstructions:
    """Test get_run_instructions and get_recommended_command across plugins."""

    @pytest.mark.parametrize(
        'plugin_class,expected_cmd',
        [
            (MySQLPlugin, 'mysql'),
            (OraclePlugin, 'sqlplus'),
            (PostgreSQLPlugin, 'psql'),
            (SQLServerPlugin, 'sqlcmd'),
        ],
    )
    def test_get_recommended_command(self, plugin_class, expected_cmd):
        """Test that each plugin returns its database-specific CLI command."""
        plugin = plugin_class()
        cmd = plugin.get_recommended_command('test_db', 'queries.sql')
        assert expected_cmd in cmd

    @pytest.mark.parametrize('plugin_class', ALL_PLUGIN_CLASSES)
    def test_get_run_instructions_contains_common_structure(self, plugin_class):
        """Test that all plugins include the common instruction structure."""
        plugin = plugin_class()
        instructions = plugin.get_run_instructions('test_db', 'queries.sql', 'test')

        assert 'queries.sql' in instructions
        assert 'execution_mode' in instructions
        assert 'query_result_file_path' in instructions

    def test_mysql_instructions_include_table_flag(self, mysql_plugin):
        """Test that MySQL instructions remind about --table flag."""
        instructions = mysql_plugin.get_run_instructions('test_db', 'queries.sql', 'mysql')
        assert '--table' in instructions

    def test_oracle_instructions_include_dba_note(self, oracle_plugin):
        """Test that Oracle instructions include DBA privilege and schema notes."""
        instructions = oracle_plugin.get_run_instructions('test_db', 'queries.sql', 'oracle')
        assert 'DBA' in instructions
        assert 'schema/owner' in instructions
        assert 'AWR' in instructions

    def test_base_get_recommended_command_fallback(self):
        """Test that the base class get_recommended_command provides a generic fallback."""
        plugin = _StubPlugin()
        cmd = plugin.get_recommended_command('mydb', 'queries.sql')
        assert '<client>' in cmd
        assert 'mydb' in cmd
        assert 'queries.sql' in cmd


class TestResultFileParsing:
    """Test parse_results_from_file boundary conditions in base_plugin.py."""

    def test_parse_pipe_marker_start_saves_previous_query(self, mysql_plugin):
        """Test that pipe-separated QUERY_NAME_START marker saves previous query data (lines 283-284)."""
        # No leading newline — first line is the marker header
        sample_data = (
            '| marker |\n'
            '| -- QUERY_NAME_START: query1 |\n'
            '| col1 |\n'
            '| val1 |\n'
            '| -- QUERY_NAME_START: query2 |\n'
            '| col2 |\n'
            '| val2 |\n'
            '| -- QUERY_NAME_END: query2 |\n'
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            result_file = os.path.join(tmpdir, 'results.txt')
            with open(result_file, 'w', encoding='utf-8') as f:
                f.write(sample_data)

            results = mysql_plugin.parse_results_from_file(result_file)

            assert 'query1' in results
            assert len(results['query1']['data']) == 1
            assert results['query1']['data'][0]['col1'] == 'val1'
            assert 'query2' in results
            assert len(results['query2']['data']) == 1

    def test_parse_pipe_marker_end_without_start(self, mysql_plugin):
        """Test that pipe-separated QUERY_NAME_END marker is handled when no query is active (line 290)."""
        sample_data = """| marker |
| -- QUERY_NAME_END: orphan_query |
| marker |
| -- QUERY_NAME_START: real_query |
| col1 |
| val1 |
| marker |
| -- QUERY_NAME_END: real_query |
"""

        with tempfile.TemporaryDirectory() as tmpdir:
            result_file = os.path.join(tmpdir, 'results.txt')
            with open(result_file, 'w', encoding='utf-8') as f:
                f.write(sample_data)

            results = mysql_plugin.parse_results_from_file(result_file)

            assert 'real_query' in results
            assert 'orphan_query' not in results

    def test_parse_blank_line_saves_current_query(self, mysql_plugin):
        """Test that a blank line mid-stream saves current query data (line 222)."""
        sample_data = """-- QUERY_NAME_START: query1
col1\tcol2
val1\t100

-- QUERY_NAME_START: query2
col3\tcol4
val2\t200
-- QUERY_NAME_END: query2
"""

        with tempfile.TemporaryDirectory() as tmpdir:
            result_file = os.path.join(tmpdir, 'results.txt')
            with open(result_file, 'w', encoding='utf-8') as f:
                f.write(sample_data)

            results = mysql_plugin.parse_results_from_file(result_file)

            assert 'query1' in results
            assert len(results['query1']['data']) == 1
            assert results['query1']['data'][0]['col1'] == 'val1'
            assert 'query2' in results

    def test_parse_comment_start_marker_saves_previous_query(self, mysql_plugin):
        """Test that a -- QUERY_NAME_START saves previous query when no END/blank between them (line 237)."""
        sample_data = """-- QUERY_NAME_START: query1
col1\tcol2
val1\t100
-- QUERY_NAME_START: query2
col3\tcol4
val2\t200
-- QUERY_NAME_END: query2
"""

        with tempfile.TemporaryDirectory() as tmpdir:
            result_file = os.path.join(tmpdir, 'results.txt')
            with open(result_file, 'w', encoding='utf-8') as f:
                f.write(sample_data)

            results = mysql_plugin.parse_results_from_file(result_file)

            assert 'query1' in results
            assert len(results['query1']['data']) == 1
            assert results['query1']['data'][0]['col1'] == 'val1'
            assert 'query2' in results
            assert len(results['query2']['data']) == 1

    def test_parse_last_query_saved_at_eof_without_blank_line(self, mysql_plugin):
        """Test that last query is saved at EOF without end marker or blank line (lines 334-335)."""
        # No trailing newline — file ends immediately after data
        sample_data = '-- QUERY_NAME_START: test_query\ncol1\tcol2\nval1\t123\nval2\t456'

        with tempfile.TemporaryDirectory() as tmpdir:
            result_file = os.path.join(tmpdir, 'results.txt')
            with open(result_file, 'w', encoding='utf-8') as f:
                f.write(sample_data)

            results = mysql_plugin.parse_results_from_file(result_file)

            assert 'test_query' in results
            assert len(results['test_query']['data']) == 2

    def test_query_description_fallback_when_missing(self):
        """Test get_query_descriptions returns fallback when description is missing (line 361)."""
        plugin = _StubPlugin(
            queries={
                'test_query': {
                    'name': 'Test',
                    'category': 'information_schema',
                    'sql': 'SELECT 1',
                    'parameters': [],
                    # intentionally no 'description' key
                },
            }
        )
        descriptions = plugin.get_query_descriptions()
        assert descriptions['test_query'] == 'No description available'


class TestOracleAWRFallback:
    """Test Oracle AWR/V$SQL fallback logic and query generation."""

    def test_oracle_write_queries_missing_query_name_logs_warning(self, oracle_plugin):
        """Test that a missing query name in query_order logs a warning (oracle.py lines 342-343)."""
        subset = {
            'comprehensive_table_analysis': {
                'name': 'Comprehensive Table Analysis',
                'description': 'Test query',
                'category': 'information_schema',
                'sql': "SELECT 1 FROM DUAL WHERE 1=UPPER('{target_owner}')",
                'parameters': ['target_owner'],
            },
        }
        with mock.patch(
            'awslabs.dynamodb_mcp_server.db_analyzer.oracle._oracle_analysis_queries',
            subset,
        ):
            with mock.patch(
                'awslabs.dynamodb_mcp_server.db_analyzer.oracle.logger'
            ) as mock_logger:
                with tempfile.TemporaryDirectory() as tmpdir:
                    output_file = os.path.join(tmpdir, 'queries.sql')
                    oracle_plugin.write_queries_to_file('test_db', 500, output_file)
                    assert mock_logger.warning.called

    def test_oracle_write_queries_skips_substitution_without_target_owner(self, oracle_plugin):
        """Test that queries without target_owner parameter skip substitution."""
        subset = {
            'comprehensive_table_analysis': {
                'name': 'Static Query',
                'description': 'Query with no target_owner parameter',
                'category': 'information_schema',
                'sql': 'SELECT SYSDATE FROM DUAL',
                'parameters': [],
            },
        }
        with mock.patch(
            'awslabs.dynamodb_mcp_server.db_analyzer.oracle._oracle_analysis_queries',
            subset,
        ):
            with tempfile.TemporaryDirectory() as tmpdir:
                output_file = os.path.join(tmpdir, 'queries.sql')
                oracle_plugin.write_queries_to_file('test_db', 500, output_file)

                with open(output_file, 'r', encoding='utf-8') as f:
                    content = f.read()

                # The original SQL should appear unmodified since no substitution was needed
                assert 'SELECT SYSDATE FROM DUAL' in content

    def test_oracle_parse_results_awr_fallback_prefers_awr(self, oracle_plugin):
        """Test that AWR data is preferred when both AWR and V$SQL have data."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result_file = os.path.join(tmpdir, 'results.txt')
            sample_data = """
-- QUERY_NAME_START: query_performance_stats_vsql
sql_id|query_pattern|total_executions
abc123|SELECT * FROM vsql_table|100
-- QUERY_NAME_END: query_performance_stats_vsql

-- QUERY_NAME_START: query_performance_stats
sql_id|query_pattern|total_executions
def456|SELECT * FROM awr_table|200
-- QUERY_NAME_END: query_performance_stats
"""
            with open(result_file, 'w', encoding='utf-8') as f:
                f.write(sample_data)

            results = oracle_plugin.parse_results_from_file(result_file)

            # Should have query_performance_stats with AWR data
            assert 'query_performance_stats' in results
            assert len(results['query_performance_stats']['data']) == 1
            assert results['query_performance_stats']['data'][0]['sql_id'] == 'def456'
            assert (
                results['query_performance_stats']['data'][0]['query_pattern']
                == 'SELECT * FROM awr_table'
            )

            # V$SQL key should be removed
            assert 'query_performance_stats_vsql' not in results

    def test_oracle_parse_results_awr_fallback_uses_vsql_when_awr_empty(self, oracle_plugin):
        """Test that V$SQL data is used when AWR returns no data."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result_file = os.path.join(tmpdir, 'results.txt')
            sample_data = """
-- QUERY_NAME_START: query_performance_stats_vsql
sql_id|query_pattern|total_executions
abc123|SELECT * FROM vsql_table|100
-- QUERY_NAME_END: query_performance_stats_vsql

-- QUERY_NAME_START: query_performance_stats
sql_id|query_pattern|total_executions
-- QUERY_NAME_END: query_performance_stats
"""
            with open(result_file, 'w', encoding='utf-8') as f:
                f.write(sample_data)

            results = oracle_plugin.parse_results_from_file(result_file)

            # Should have query_performance_stats with V$SQL data
            assert 'query_performance_stats' in results
            assert len(results['query_performance_stats']['data']) == 1
            assert results['query_performance_stats']['data'][0]['sql_id'] == 'abc123'
            assert (
                results['query_performance_stats']['data'][0]['query_pattern']
                == 'SELECT * FROM vsql_table'
            )
            assert 'V$SQL fallback' in results['query_performance_stats']['description']

            # V$SQL key should be removed
            assert 'query_performance_stats_vsql' not in results

    def test_oracle_parse_results_awr_fallback_handles_missing_awr(self, oracle_plugin):
        """Test that V$SQL data is used when AWR query is missing entirely (error case)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result_file = os.path.join(tmpdir, 'results.txt')
            sample_data = """
-- QUERY_NAME_START: query_performance_stats_vsql
sql_id|query_pattern|total_executions
abc123|SELECT * FROM vsql_table|100
-- QUERY_NAME_END: query_performance_stats_vsql
"""
            with open(result_file, 'w', encoding='utf-8') as f:
                f.write(sample_data)

            results = oracle_plugin.parse_results_from_file(result_file)

            # Should have query_performance_stats with V$SQL data
            assert 'query_performance_stats' in results
            assert len(results['query_performance_stats']['data']) == 1
            assert results['query_performance_stats']['data'][0]['sql_id'] == 'abc123'

            # V$SQL key should be removed
            assert 'query_performance_stats_vsql' not in results

    def test_oracle_parse_results_awr_fallback_both_empty(self, oracle_plugin):
        """Test that empty AWR key is kept when both queries return no data."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result_file = os.path.join(tmpdir, 'results.txt')
            sample_data = """
-- QUERY_NAME_START: query_performance_stats_vsql
sql_id|query_pattern|total_executions
-- QUERY_NAME_END: query_performance_stats_vsql

-- QUERY_NAME_START: query_performance_stats
sql_id|query_pattern|total_executions
-- QUERY_NAME_END: query_performance_stats
"""
            with open(result_file, 'w', encoding='utf-8') as f:
                f.write(sample_data)

            results = oracle_plugin.parse_results_from_file(result_file)

            # Should have query_performance_stats with empty data
            assert 'query_performance_stats' in results
            assert len(results['query_performance_stats']['data']) == 0

            # V$SQL key should be removed
            assert 'query_performance_stats_vsql' not in results
