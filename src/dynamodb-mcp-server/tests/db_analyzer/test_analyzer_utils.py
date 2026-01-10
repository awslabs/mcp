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

"""Tests for analyzer_utils module.

These tests cover utility functions for database analysis workflows including:
- Connection parameter building and validation
- Path resolution and validation
- Query file generation
- Result parsing and analysis generation
- Report building
- File saving operations
"""

import os
import pytest
import tempfile
from awslabs.dynamodb_mcp_server.db_analyzer import analyzer_utils
from awslabs.dynamodb_mcp_server.db_analyzer.mysql import MySQLPlugin


class TestBuildConnectionParams:
    """Test connection parameter building."""

    def test_build_connection_params_mysql(self, tmp_path):
        """Test building MySQL connection parameters."""
        params = analyzer_utils.build_connection_params(
            'mysql',
            aws_cluster_arn='test-cluster',
            aws_secret_arn='test-secret',  # pragma: allowlist secret
            database_name='test_db',
            aws_region='us-east-1',
            max_query_results=1000,
            pattern_analysis_days=30,
            output_dir=str(tmp_path),
        )

        assert params['cluster_arn'] == 'test-cluster'
        assert params['secret_arn'] == 'test-secret'  # pragma: allowlist secret
        assert params['database'] == 'test_db'
        assert params['region'] == 'us-east-1'
        assert params['max_results'] == 1000
        assert params['pattern_analysis_days'] == 30
        assert params['output_dir'] == str(tmp_path)

    def test_build_connection_params_invalid_directory(self):
        """Test build_connection_params with invalid output directory."""
        # Test non-absolute path
        with pytest.raises(ValueError, match='Output directory must be an absolute path'):
            analyzer_utils.build_connection_params('mysql', output_dir='relative/path')

        # Test non-existent directory
        with pytest.raises(ValueError, match='Output directory does not exist or is not writable'):
            analyzer_utils.build_connection_params('mysql', output_dir='/nonexistent/path')

    def test_build_connection_params_unsupported_database(self, tmp_path):
        """Test build_connection_params with unsupported database type."""
        with pytest.raises(ValueError, match='Unsupported database type: postgresql'):
            analyzer_utils.build_connection_params(
                'postgresql',
                database_name='test_db',
                output_dir=str(tmp_path),
            )

    def test_build_connection_params_with_env_vars(self, tmp_path, monkeypatch):
        """Test that environment variables are used as fallback."""
        monkeypatch.setenv('MYSQL_CLUSTER_ARN', 'env-cluster')
        monkeypatch.setenv('MYSQL_SECRET_ARN', 'env-secret')
        monkeypatch.setenv('MYSQL_DATABASE', 'env_db')
        monkeypatch.setenv('AWS_REGION', 'env-region')
        monkeypatch.setenv('MYSQL_MAX_QUERY_RESULTS', '999')

        params = analyzer_utils.build_connection_params(
            'mysql',
            output_dir=str(tmp_path),
        )

        assert params['cluster_arn'] == 'env-cluster'
        assert params['secret_arn'] == 'env-secret'  # pragma: allowlist secret
        assert params['database'] == 'env_db'
        assert params['region'] == 'env-region'
        assert params['max_results'] == 999

    def test_build_connection_params_explicit_overrides_env(self, tmp_path, monkeypatch):
        """Test that explicit parameters override environment variables."""
        monkeypatch.setenv('MYSQL_CLUSTER_ARN', 'env-cluster')
        monkeypatch.setenv('MYSQL_SECRET_ARN', 'env-secret')

        params = analyzer_utils.build_connection_params(
            'mysql',
            aws_cluster_arn='explicit-cluster',
            aws_secret_arn='explicit-secret',  # pragma: allowlist secret
            database_name='explicit_db',
            aws_region='explicit-region',
            output_dir=str(tmp_path),
        )

        assert params['cluster_arn'] == 'explicit-cluster'
        assert params['secret_arn'] == 'explicit-secret'  # pragma: allowlist secret
        assert params['database'] == 'explicit_db'
        assert params['region'] == 'explicit-region'


class TestValidateConnectionParams:
    """Test connection parameter validation."""

    def test_validate_connection_params_mysql_missing(self):
        """Test MySQL connection parameter validation with missing params."""
        params = {'cluster_arn': 'test'}
        missing, descriptions = analyzer_utils.validate_connection_params('mysql', params)

        assert 'secret_arn' in missing
        assert 'database' in missing
        assert 'region' in missing
        # New validation logic provides descriptions for common required params
        assert 'secret_arn' in descriptions
        assert 'database' in descriptions
        assert 'region' in descriptions

    def test_validate_connection_params_mysql_missing_connection_method(self):
        """Test MySQL validation when neither cluster_arn nor hostname is provided."""
        params = {
            'secret_arn': 'test',  # pragma: allowlist secret
            'database': 'test',
            'region': 'us-east-1',
        }
        missing, descriptions = analyzer_utils.validate_connection_params('mysql', params)

        assert 'cluster_arn OR hostname' in missing
        assert 'cluster_arn OR hostname' in descriptions

    def test_validate_connection_params_mysql_with_hostname(self):
        """Test MySQL validation with hostname (connection-based access)."""
        params = {
            'hostname': 'mydb.example.com',
            'secret_arn': 'test-secret',  # pragma: allowlist secret
            'database': 'test-db',
            'region': 'us-east-1',
        }
        missing, descriptions = analyzer_utils.validate_connection_params('mysql', params)

        assert missing == []

    def test_validate_connection_params_all_valid(self):
        """Test validate_connection_params when all params are valid."""
        connection_params = {
            'cluster_arn': 'test-cluster',
            'secret_arn': 'test-secret',  # pragma: allowlist secret
            'database': 'test-db',
            'region': 'us-east-1',
            'output_dir': '/tmp',
        }

        missing_params, param_descriptions = analyzer_utils.validate_connection_params(
            'mysql', connection_params
        )

        assert missing_params == []
        assert isinstance(param_descriptions, dict)
        assert len(param_descriptions) > 0

    def test_validate_connection_params_unsupported_type(self):
        """Test validate_connection_params with unsupported database type."""
        connection_params = {'some_param': 'value'}

        missing_params, param_descriptions = analyzer_utils.validate_connection_params(
            'postgresql', connection_params
        )

        assert missing_params == []
        assert param_descriptions == {}


class TestResolveAndValidatePath:
    """Test path resolution and validation."""

    def test_path_resolution_scenarios(self):
        """Test various path resolution and validation scenarios."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Test 1: Relative path
            output_dir = os.path.join(tmpdir, 'output')
            os.makedirs(output_dir, exist_ok=True)
            result = analyzer_utils.resolve_and_validate_path(
                'output/queries.sql', tmpdir, 'test file'
            )
            assert result.startswith(os.path.realpath(tmpdir))
            assert 'output' in result and 'queries.sql' in result

            # Test 2: Absolute path within base
            file_path = os.path.join(tmpdir, 'queries.sql')
            result = analyzer_utils.resolve_and_validate_path(file_path, tmpdir, 'test file')
            assert result == os.path.normpath(os.path.realpath(file_path))

            # Test 3: Path with ./
            result = analyzer_utils.resolve_and_validate_path(
                './output/queries.sql', tmpdir, 'test file'
            )
            assert result.startswith(os.path.realpath(tmpdir))
            assert 'output' in result

            # Test 4: Path traversal rejected
            with pytest.raises(ValueError, match='Path traversal detected'):
                analyzer_utils.resolve_and_validate_path('/etc/passwd', tmpdir, 'test file')


class TestGenerateQueryFile:
    """Test SQL query file generation."""

    def test_query_file_generation_scenarios(self):
        """Test various query file generation scenarios."""
        plugin = MySQLPlugin()

        with tempfile.TemporaryDirectory() as tmpdir:
            # Test 1: Successful generation
            result = analyzer_utils.generate_query_file(
                plugin, 'test_db', 500, 'queries.sql', tmpdir, 'mysql'
            )
            assert 'SQL queries have been written to:' in result
            assert 'Next Steps:' in result
            assert 'mysql -u user -p' in result
            assert os.path.exists(os.path.join(tmpdir, 'queries.sql'))

            # Test 2: Creates subdirectories
            result = analyzer_utils.generate_query_file(
                plugin, 'test_db', 500, 'output/subdir/queries.sql', tmpdir, 'mysql'
            )
            assert os.path.exists(os.path.join(tmpdir, 'output', 'subdir', 'queries.sql'))

            # Test 3: Missing database name
            result = analyzer_utils.generate_query_file(
                plugin, None, 500, 'queries.sql', tmpdir, 'mysql'
            )
            assert 'database_name is required' in result

            # Test 4: Empty database name
            result = analyzer_utils.generate_query_file(
                plugin, '', 500, 'queries.sql', tmpdir, 'mysql'
            )
            assert 'database_name is required' in result

            # Test 5: Path traversal rejected
            with pytest.raises(ValueError, match='Path traversal detected'):
                analyzer_utils.generate_query_file(
                    plugin, 'test_db', 500, '/etc/passwd', tmpdir, 'mysql'
                )

            # Test 6: Includes proper instructions
            result = analyzer_utils.generate_query_file(
                plugin, 'airline_db', 1000, 'queries.sql', tmpdir, 'mysql'
            )
            assert 'Example commands:' in result
            assert '--table' in result
            assert 'IMPORTANT for MySQL' in result


class TestParseResultsAndGenerateAnalysis:
    """Test result parsing and analysis generation."""

    def test_result_parsing_scenarios(self):
        """Test various result parsing scenarios."""
        plugin = MySQLPlugin()

        with tempfile.TemporaryDirectory() as tmpdir:
            # Test 1: Path traversal - absolute path outside base directory
            with pytest.raises(ValueError, match='Path traversal detected'):
                analyzer_utils.parse_results_and_generate_analysis(
                    plugin, '/nonexistent/file.txt', tmpdir, 'test_db', 30, 500, 'mysql'
                )

            # Test 2: Empty file
            result_file = os.path.join(tmpdir, 'empty.txt')
            with open(result_file, 'w', encoding='utf-8') as f:
                f.write('')
            result = analyzer_utils.parse_results_and_generate_analysis(
                plugin, result_file, tmpdir, 'test_db', 30, 500, 'mysql'
            )
            assert 'No query results found' in result

            # Test 3: Successful parsing
            result_file = os.path.join(tmpdir, 'results.txt')
            with open(result_file, 'w', encoding='utf-8') as f:
                f.write("""| marker |
| -- QUERY_NAME_START: comprehensive_table_analysis |
+------------+-----------+
| table_name | row_count |
+------------+-----------+
| users      |      1000 |
+------------+-----------+
| marker |
| -- QUERY_NAME_END: comprehensive_table_analysis |
""")
            result = analyzer_utils.parse_results_and_generate_analysis(
                plugin, result_file, tmpdir, 'test_db', 30, 500, 'mysql'
            )
            assert 'Database Analysis Complete' in result
            assert 'Self-Service Mode' in result
            assert 'test_db' in result


class TestSaveAnalysisFiles:
    """Test analysis file saving functionality."""

    def test_save_analysis_files_empty_results(self):
        """Test save_analysis_files with empty results."""
        plugin = MySQLPlugin()
        saved_files, save_errors = analyzer_utils.save_analysis_files(
            {}, 'mysql', 'test_db', 30, 500, '/tmp', plugin
        )

        assert saved_files == []
        assert save_errors == []

    def test_save_analysis_files_with_data(self, tmp_path, monkeypatch):
        """Test save_analysis_files with actual data."""

        class MockDateTime:
            @staticmethod
            def now():
                class MockNow:
                    def strftime(self, fmt):
                        return '20231009_120000'

                return MockNow()

        monkeypatch.setattr(
            'awslabs.dynamodb_mcp_server.db_analyzer.analyzer_utils.datetime', MockDateTime
        )

        results = {
            'comprehensive_table_analysis': {
                'data': [{'table': 'users', 'rows': 100}],
                'description': 'Table analysis',
            },
            'query_performance_stats': {
                'data': [{'pattern': 'SELECT * FROM users', 'frequency': 10}],
                'description': 'Query patterns',
            },
        }

        plugin = MySQLPlugin()
        saved_files, save_errors = analyzer_utils.save_analysis_files(
            results, 'mysql', 'test_db', 30, 500, str(tmp_path), plugin
        )

        # Should generate markdown files for all expected queries
        assert len(saved_files) == 6
        assert len(save_errors) == 0

        for filename in saved_files:
            assert os.path.exists(filename)
            assert filename.endswith('.md')

    def test_save_analysis_files_creation_error(self, tmp_path, monkeypatch):
        """Test save_analysis_files when folder creation fails."""

        def mock_makedirs_fail(*args, **kwargs):
            raise OSError('Permission denied')

        monkeypatch.setattr('os.makedirs', mock_makedirs_fail)

        plugin = MySQLPlugin()
        results = {'table_analysis': {'data': [], 'description': 'Test'}}

        saved_files, save_errors = analyzer_utils.save_analysis_files(
            results, 'mysql', 'test_db', 30, 500, str(tmp_path), plugin
        )

        assert len(saved_files) == 0
        assert len(save_errors) == 1
        assert 'Failed to create folder' in save_errors[0]

    def test_save_analysis_files_with_generation_errors(self, tmp_path, monkeypatch):
        """Test save_analysis_files when there are generation errors."""

        class MockDateTime:
            @staticmethod
            def now():
                class MockNow:
                    def strftime(self, fmt):
                        return '20231009_120000'

                return MockNow()

        monkeypatch.setattr(
            'awslabs.dynamodb_mcp_server.db_analyzer.analyzer_utils.datetime', MockDateTime
        )

        class MockFormatter:
            def __init__(self, *args, **kwargs):
                pass

            def generate_all_files(self):
                return ['/tmp/file1.md'], [
                    ('query1', 'Error message 1'),
                    ('query2', 'Error message 2'),
                ]

        monkeypatch.setattr(
            'awslabs.dynamodb_mcp_server.db_analyzer.analyzer_utils.MarkdownFormatter',
            MockFormatter,
        )

        results = {
            'comprehensive_table_analysis': {
                'data': [{'table': 'users', 'rows': 100}],
                'description': 'Table analysis',
            },
        }

        plugin = MySQLPlugin()
        saved_files, save_errors = analyzer_utils.save_analysis_files(
            results, 'mysql', 'test_db', 30, 500, str(tmp_path), plugin, True, []
        )

        assert len(saved_files) == 1
        assert len(save_errors) == 2
        assert 'query1: Error message 1' in save_errors
        assert 'query2: Error message 2' in save_errors

    def test_save_analysis_files_markdown_error(self, tmp_path, monkeypatch):
        """Test save_analysis_files with Markdown generation error."""
        results = {'test': {'description': 'Test', 'data': []}}

        def mock_markdown_formatter_init(*args, **kwargs):
            raise Exception('Markdown generation failed')

        monkeypatch.setattr(
            'awslabs.dynamodb_mcp_server.db_analyzer.analyzer_utils.MarkdownFormatter',
            mock_markdown_formatter_init,
        )

        plugin = MySQLPlugin()
        saved, errors = analyzer_utils.save_analysis_files(
            results, 'mysql', 'db', 30, 500, str(tmp_path), plugin
        )

        assert len(errors) == 1
        assert 'Markdown generation failed' in errors[0]


class TestExecuteManagedAnalysis:
    """Test managed mode analysis execution."""

    @pytest.mark.asyncio
    async def test_execute_managed_analysis_success(self, monkeypatch):
        """Test successful managed analysis execution."""
        plugin = MySQLPlugin()
        connection_params = {
            'database': 'test_db',
            'pattern_analysis_days': 30,
            'max_results': 500,
            'output_dir': '/tmp',
        }
        source_db_type = 'mysql'

        async def mock_execute_managed_mode(params):
            return {
                'results': {
                    'comprehensive_table_analysis': {
                        'description': 'Test',
                        'data': [{'table': 'users'}],
                    }
                },
                'performance_enabled': True,
                'skipped_queries': [],
                'errors': [],
            }

        monkeypatch.setattr(plugin, 'execute_managed_mode', mock_execute_managed_mode)

        def mock_save_files(*args, **kwargs):
            return ['/tmp/file1.md'], []

        monkeypatch.setattr(analyzer_utils, 'save_analysis_files', mock_save_files)

        result = await analyzer_utils.execute_managed_analysis(
            plugin, connection_params, source_db_type
        )

        assert 'Database Analysis Complete' in result
        assert 'Managed Mode' in result
        assert 'test_db' in result

    @pytest.mark.asyncio
    async def test_execute_managed_analysis_all_queries_failed(self, monkeypatch):
        """Test managed analysis when all queries fail."""
        plugin = MySQLPlugin()
        connection_params = {
            'database': 'test_db',
            'pattern_analysis_days': 30,
            'max_results': 500,
            'output_dir': '/tmp',
        }
        source_db_type = 'mysql'

        async def mock_execute_managed_mode(params):
            return {
                'results': {},
                'performance_enabled': True,
                'skipped_queries': [],
                'errors': ['Query 1 failed', 'Query 2 failed'],
            }

        monkeypatch.setattr(plugin, 'execute_managed_mode', mock_execute_managed_mode)

        result = await analyzer_utils.execute_managed_analysis(
            plugin, connection_params, source_db_type
        )

        assert 'Database Analysis Failed' in result
        assert 'All 2 queries failed' in result
        assert '1. Query 1 failed' in result
        assert '2. Query 2 failed' in result


class TestReportBuilding:
    """Test analysis and failure report building."""

    def test_analysis_report_scenarios(self):
        """Test various analysis report building scenarios."""
        # Test 1: Self-service mode report
        result = analyzer_utils.build_analysis_report(
            ['/tmp/file1.md', '/tmp/file2.md'],
            [],
            'test_db',
            '/tmp/results.txt',
            is_self_service=True,
        )
        assert 'Self-Service Mode' in result
        assert 'test_db' in result
        assert '/tmp/results.txt' in result
        assert '/tmp/file1.md' in result

        # Test 2: Managed mode report
        result = analyzer_utils.build_analysis_report(
            ['/tmp/file1.md'], [], 'prod_db', None, is_self_service=False, analysis_period=30
        )
        assert 'Managed Mode' in result
        assert 'prod_db' in result
        assert '30 days' in result

        # Test 3: Report with errors
        result = analyzer_utils.build_analysis_report(
            ['/tmp/file1.md'], ['Error 1', 'Error 2'], 'test_db', None, is_self_service=False
        )
        assert 'File Save Errors:' in result
        assert 'Error 1' in result

        # Test 4: Report with no files
        result = analyzer_utils.build_analysis_report(
            [], [], 'test_db', None, is_self_service=False
        )
        assert 'Database Analysis Complete' in result
        assert 'Generated Analysis Files (Read All):' not in result

    def test_failure_report_scenarios(self):
        """Test failure report building with various error counts."""
        # Test 1: Single error
        result = analyzer_utils.build_failure_report(['Connection timeout'])
        assert 'Database Analysis Failed' in result
        assert 'All 1 queries failed' in result
        assert '1. Connection timeout' in result

        # Test 2: Multiple errors
        result = analyzer_utils.build_failure_report(['Error 1', 'Error 2', 'Error 3'])
        assert 'All 3 queries failed' in result
        assert '1. Error 1' in result
        assert '2. Error 2' in result
        assert '3. Error 3' in result
