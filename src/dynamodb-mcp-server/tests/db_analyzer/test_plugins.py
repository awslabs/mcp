"""Tests for database analyzer plugins.

Tests core functionality that's not covered by existing tests:
- Plugin query definitions and structure
- SQL generation (write_queries_to_file)
- Result parsing (parse_results_from_file) with markers
- Empty result handling
- Cross-plugin consistency
"""

import os
import pytest
import tempfile
from awslabs.dynamodb_mcp_server.db_analyzer.base_plugin import DatabasePlugin
from awslabs.dynamodb_mcp_server.db_analyzer.mysql import MySQLPlugin
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

        # All plugins must have these schema queries
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
            # Skip internal queries
            if query_info.get('category') == 'internal':
                continue

            assert 'description' in query_info, f"{query_name}: Missing 'description'"
            assert 'category' in query_info, f"{query_name}: Missing 'category'"
            assert 'sql' in query_info, f"{query_name}: Missing 'sql'"
            assert 'parameters' in query_info, f"{query_name}: Missing 'parameters'"

            # Category must be valid
            assert query_info['category'] in [
                'information_schema',
                'performance_schema',
                'internal',
            ], f"{query_name}: Invalid category '{query_info['category']}'"

    @pytest.mark.parametrize('plugin_class', [MySQLPlugin, PostgreSQLPlugin, SQLServerPlugin])
    def test_helper_functions(self, plugin_class):
        """Test that helper functions work correctly."""
        plugin = plugin_class()

        # Test get_queries_by_category
        schema_queries = plugin.get_queries_by_category('information_schema')
        assert len(schema_queries) >= 4, 'Should have at least 4 schema queries'

        # Test get_query_descriptions
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

            assert result == output_file, 'Should return output file path'
            assert os.path.exists(output_file), 'SQL file should be created'

            # Read and validate content
            with open(output_file, 'r') as f:
                content = f.read()

            assert len(content) > 0, 'SQL file should not be empty'
            assert db_name in content or '{target_database}' not in content, (
                'Database name should be substituted'
            )

            # Check for markers (SELECT statements)
            assert "SELECT '-- QUERY_NAME_START:" in content, 'Should have start markers'
            assert "SELECT '-- QUERY_NAME_END:" in content, 'Should have end markers'

            # Check that internal queries are not included
            assert 'internal' not in content.lower() or 'QUERY_NAME_START' not in content, (
                'Internal queries should be skipped'
            )

    def test_mysql_uses_limit(self):
        """Test that MySQL uses LIMIT syntax."""
        plugin = MySQLPlugin()

        with tempfile.TemporaryDirectory() as tmpdir:
            output_file = os.path.join(tmpdir, 'queries.sql')
            plugin.write_queries_to_file('test_db', 100, output_file)

            with open(output_file, 'r') as f:
                content = f.read()

            assert 'LIMIT 100' in content, 'MySQL should use LIMIT'

    def test_sqlserver_uses_top(self):
        """Test that SQL Server uses TOP syntax."""
        plugin = SQLServerPlugin()

        with tempfile.TemporaryDirectory() as tmpdir:
            output_file = os.path.join(tmpdir, 'queries.sql')
            plugin.write_queries_to_file('test_db', 100, output_file)

            with open(output_file, 'r') as f:
                content = f.read()

            assert 'TOP 100' in content, 'SQL Server should use TOP'


class TestResultParsing:
    """Test parsing of query results with markers.

    Since parse_results_from_file is now implemented in the base class,
    we test it once with different format variations rather than per-plugin.
    """

    @pytest.mark.parametrize('plugin_class', [MySQLPlugin, PostgreSQLPlugin, SQLServerPlugin])
    def test_parse_with_pipe_separated_markers(self, plugin_class):
        """Test parsing pipe-separated format (works for all plugins)."""
        plugin = plugin_class()

        # Create sample result file with markers
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
            with open(result_file, 'w') as f:
                f.write(sample_data)

            results = plugin.parse_results_from_file(result_file)

            assert 'comprehensive_table_analysis' in results, 'Should parse query name from marker'
            assert len(results['comprehensive_table_analysis']['data']) == 2, 'Should have 2 rows'
            assert results['comprehensive_table_analysis']['data'][0]['table_name'] == 'users'
            assert results['comprehensive_table_analysis']['data'][0]['row_count'] == 1000

    def test_parse_with_tab_separated_format(self):
        """Test parsing tab-separated format (common in MySQL output)."""
        plugin = MySQLPlugin()

        sample_data = """marker
-- QUERY_NAME_START: test_query
table_name\trow_count
users\t1000
orders\t5000
marker
-- QUERY_NAME_END: test_query
"""

        with tempfile.TemporaryDirectory() as tmpdir:
            result_file = os.path.join(tmpdir, 'results.txt')
            with open(result_file, 'w') as f:
                f.write(sample_data)

            results = plugin.parse_results_from_file(result_file)

            assert 'test_query' in results
            assert len(results['test_query']['data']) == 2
            assert results['test_query']['data'][0]['table_name'] == 'users'
            assert results['test_query']['data'][0]['row_count'] == 1000

    def test_parse_empty_result(self):
        """Test parsing query with 0 rows (empty result)."""
        plugin = MySQLPlugin()

        sample_data = """| marker |
| -- QUERY_NAME_START: triggers_stats |
| marker |
| -- QUERY_NAME_END: triggers_stats |
"""

        with tempfile.TemporaryDirectory() as tmpdir:
            result_file = os.path.join(tmpdir, 'results.txt')
            with open(result_file, 'w') as f:
                f.write(sample_data)

            results = plugin.parse_results_from_file(result_file)

            assert 'triggers_stats' in results, 'Should parse empty results'
            assert results['triggers_stats']['data'] == [], 'Should have empty data array'

    def test_parse_multiple_queries(self):
        """Test parsing multiple queries in one file."""
        plugin = MySQLPlugin()

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
            with open(result_file, 'w') as f:
                f.write(sample_data)

            results = plugin.parse_results_from_file(result_file)

            assert len(results) == 2, 'Should parse both queries'
            assert 'query1' in results
            assert 'query2' in results

    def test_parse_file_not_found(self):
        """Test parsing non-existent file raises error."""
        plugin = MySQLPlugin()

        with pytest.raises(FileNotFoundError):
            plugin.parse_results_from_file('/nonexistent/file.txt')

    def test_data_type_conversion(self):
        """Test that data types are converted correctly."""
        plugin = MySQLPlugin()

        sample_data = """| marker |
| -- QUERY_NAME_START: test_query |
+--------+-------+-------+--------+
| string | int   | float | null   |
+--------+-------+-------+--------+
| text   | 123   | 45.67 | NULL   |
+--------+-------+-------+--------+
| marker |
| -- QUERY_NAME_END: test_query |
"""

        with tempfile.TemporaryDirectory() as tmpdir:
            result_file = os.path.join(tmpdir, 'results.txt')
            with open(result_file, 'w') as f:
                f.write(sample_data)

            results = plugin.parse_results_from_file(result_file)
            row = results['test_query']['data'][0]

            assert isinstance(row['string'], str)
            assert isinstance(row['int'], int)
            assert isinstance(row['float'], float)
            assert row['null'] is None

    def test_parse_with_separator_and_empty_lines(self):
        """Test parsing handles separator lines and empty lines between queries."""
        plugin = MySQLPlugin()

        sample_data = """| marker |
| -- QUERY_NAME_START: query1 |
+-------+
| col1  |
+-------+
| val1  |
+-------+
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
            with open(result_file, 'w') as f:
                f.write(sample_data)

            results = plugin.parse_results_from_file(result_file)

            assert len(results) == 2
            assert 'query1' in results
            assert 'query2' in results

    def test_parse_with_empty_line_saves_previous_query(self):
        """Test parsing saves previous query when encountering empty line."""
        plugin = MySQLPlugin()

        # Empty line between data rows should trigger save of previous query
        sample_data = """-- QUERY_NAME_START: query1
col1	col2
val1	123

-- QUERY_NAME_START: query2
col1	col2
val2	456
-- QUERY_NAME_END: query2
"""

        with tempfile.TemporaryDirectory() as tmpdir:
            result_file = os.path.join(tmpdir, 'results.txt')
            with open(result_file, 'w', encoding='utf-8') as f:
                f.write(sample_data)

            results = plugin.parse_results_from_file(result_file)

            # Both queries should be parsed
            assert 'query1' in results
            assert 'query2' in results
            assert len(results['query1']['data']) == 1
            assert len(results['query2']['data']) == 1

    def test_parse_marker_as_column_value(self):
        """Test parsing when marker appears as a column value in SELECT output."""
        plugin = MySQLPlugin()

        sample_data = """| -- QUERY_NAME_START: test_query |
| col1 |
| val1 |
| -- QUERY_NAME_END: test_query |
"""

        with tempfile.TemporaryDirectory() as tmpdir:
            result_file = os.path.join(tmpdir, 'results.txt')
            with open(result_file, 'w', encoding='utf-8') as f:
                f.write(sample_data)

            results = plugin.parse_results_from_file(result_file)

            assert 'test_query' in results
            assert len(results['test_query']['data']) == 1

    def test_parse_with_float_and_int_conversion(self):
        """Test parsing correctly converts numeric types."""
        plugin = MySQLPlugin()

        sample_data = """| marker |
| -- QUERY_NAME_START: test_query |
| int_col | float_col | string_col |
| 123 | 45.67 | text |
| 0 | 0.0 | 123text |
| marker |
| -- QUERY_NAME_END: test_query |
"""

        with tempfile.TemporaryDirectory() as tmpdir:
            result_file = os.path.join(tmpdir, 'results.txt')
            with open(result_file, 'w', encoding='utf-8') as f:
                f.write(sample_data)

            results = plugin.parse_results_from_file(result_file)

            assert 'test_query' in results
            data = results['test_query']['data']

            # Check first row
            assert isinstance(data[0]['int_col'], int)
            assert isinstance(data[0]['float_col'], float)
            assert isinstance(data[0]['string_col'], str)

            # Check second row
            assert data[1]['int_col'] == 0
            assert data[1]['float_col'] == 0.0
            assert data[1]['string_col'] == '123text'  # Should remain string


class TestPluginRegistry:
    """Test plugin registry functionality."""

    def test_all_plugins_instantiate(self):
        """Test that all plugins can be instantiated."""
        plugins = [
            MySQLPlugin(),
            PostgreSQLPlugin(),
            SQLServerPlugin(),
        ]

        for plugin in plugins:
            assert plugin is not None
            assert hasattr(plugin, 'get_queries')
            assert hasattr(plugin, 'write_queries_to_file')
            assert hasattr(plugin, 'parse_results_from_file')

    def test_plugin_methods_return_correct_types(self):
        """Test that plugin methods return expected types."""
        plugin = MySQLPlugin()

        # get_queries should return dict
        queries = plugin.get_queries()
        assert isinstance(queries, dict)

        # write_queries_to_file should return string (file path)
        with tempfile.TemporaryDirectory() as tmpdir:
            output_file = os.path.join(tmpdir, 'test.sql')
            result = plugin.write_queries_to_file('test_db', 100, output_file)
            assert isinstance(result, str)
            assert result == output_file


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


class TestPluginRegistryFunctionality:
    """Test plugin registry operations."""

    def test_get_plugin_mysql(self):
        """Test getting MySQL plugin from registry."""
        from awslabs.dynamodb_mcp_server.db_analyzer.plugin_registry import PluginRegistry

        plugin = PluginRegistry.get_plugin('mysql')
        assert isinstance(plugin, MySQLPlugin)

    def test_get_plugin_postgresql(self):
        """Test getting PostgreSQL plugin from registry."""
        from awslabs.dynamodb_mcp_server.db_analyzer.plugin_registry import PluginRegistry

        plugin = PluginRegistry.get_plugin('postgresql')
        assert isinstance(plugin, PostgreSQLPlugin)

    def test_get_plugin_sqlserver(self):
        """Test getting SQL Server plugin from registry."""
        from awslabs.dynamodb_mcp_server.db_analyzer.plugin_registry import PluginRegistry

        plugin = PluginRegistry.get_plugin('sqlserver')
        assert isinstance(plugin, SQLServerPlugin)

    def test_get_plugin_case_insensitive(self):
        """Test that plugin lookup is case-insensitive."""
        from awslabs.dynamodb_mcp_server.db_analyzer.plugin_registry import PluginRegistry

        plugin1 = PluginRegistry.get_plugin('MySQL')
        plugin2 = PluginRegistry.get_plugin('MYSQL')
        plugin3 = PluginRegistry.get_plugin('mysql')

        assert isinstance(plugin1, MySQLPlugin)
        assert isinstance(plugin2, MySQLPlugin)
        assert isinstance(plugin3, MySQLPlugin)

    def test_get_plugin_unsupported_type(self):
        """Test that unsupported database type raises ValueError."""
        from awslabs.dynamodb_mcp_server.db_analyzer.plugin_registry import PluginRegistry

        with pytest.raises(ValueError, match='Unsupported database type'):
            PluginRegistry.get_plugin('oracle')

    def test_get_supported_types(self):
        """Test getting list of supported database types."""
        from awslabs.dynamodb_mcp_server.db_analyzer.plugin_registry import PluginRegistry

        supported = PluginRegistry.get_supported_types()

        assert isinstance(supported, list)
        assert 'mysql' in supported
        assert 'postgresql' in supported
        assert 'sqlserver' in supported
        assert len(supported) == 3

    def test_register_plugin(self):
        """Test registering a custom plugin."""
        from awslabs.dynamodb_mcp_server.db_analyzer.plugin_registry import PluginRegistry

        # Create a mock plugin class
        class MockPlugin(DatabasePlugin):
            def get_queries(self):
                return {}

            def get_database_display_name(self):
                return 'MockDB'

            async def execute_managed_mode(self, connection_params):
                return {'results': {}, 'errors': []}

        # Register the mock plugin
        PluginRegistry.register_plugin('mock_db', MockPlugin)

        # Verify it was registered
        assert 'mock_db' in PluginRegistry.get_supported_types()

        # Verify we can get it
        plugin = PluginRegistry.get_plugin('mock_db')
        assert isinstance(plugin, MockPlugin)


class TestBasePluginHelperMethods:
    """Test base plugin helper methods."""

    @pytest.mark.parametrize('plugin_class', [MySQLPlugin, PostgreSQLPlugin, SQLServerPlugin])
    def test_get_schema_queries(self, plugin_class):
        """Test get_schema_queries returns only information_schema queries."""
        plugin = plugin_class()
        schema_queries = plugin.get_schema_queries()

        assert isinstance(schema_queries, list)
        assert len(schema_queries) >= 4, 'Should have at least 4 schema queries'

        # Verify all returned queries are actually schema queries
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

        # Verify all returned queries are actually performance queries
        all_queries = plugin.get_queries()
        for query_name in perf_queries:
            assert query_name in all_queries
            assert all_queries[query_name]['category'] == 'performance_schema'

    def test_get_queries_by_category_information_schema(self):
        """Test get_queries_by_category for information_schema."""
        plugin = MySQLPlugin()

        schema_queries = plugin.get_queries_by_category('information_schema')

        assert isinstance(schema_queries, list)
        assert 'comprehensive_table_analysis' in schema_queries
        assert 'comprehensive_index_analysis' in schema_queries

    def test_get_queries_by_category_performance_schema(self):
        """Test get_queries_by_category for performance_schema."""
        plugin = MySQLPlugin()

        perf_queries = plugin.get_queries_by_category('performance_schema')

        assert isinstance(perf_queries, list)
        # MySQL should have performance queries
        assert len(perf_queries) > 0

    def test_get_queries_by_category_internal(self):
        """Test get_queries_by_category for internal queries."""
        plugin = MySQLPlugin()

        internal_queries = plugin.get_queries_by_category('internal')

        assert isinstance(internal_queries, list)
        # MySQL has performance_schema_check as internal
        assert 'performance_schema_check' in internal_queries

    def test_get_query_descriptions_excludes_internal(self):
        """Test that get_query_descriptions excludes internal queries."""
        plugin = MySQLPlugin()

        descriptions = plugin.get_query_descriptions()

        # Should not include internal queries
        assert 'performance_schema_check' not in descriptions

        # Should include schema queries
        assert 'comprehensive_table_analysis' in descriptions
        assert isinstance(descriptions['comprehensive_table_analysis'], str)

    @pytest.mark.parametrize('plugin_class', [MySQLPlugin, PostgreSQLPlugin, SQLServerPlugin])
    def test_apply_result_limit(self, plugin_class):
        """Test apply_result_limit for different database types."""
        plugin = plugin_class()
        sql = 'SELECT * FROM users'

        result = plugin.apply_result_limit(sql, 100)

        # MySQL and PostgreSQL use LIMIT, SQL Server uses TOP
        if isinstance(plugin, SQLServerPlugin):
            assert 'TOP 100' in result
        else:
            assert 'LIMIT 100' in result
