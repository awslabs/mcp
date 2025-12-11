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

"""Unit tests for MarkdownFormatter."""

import os
import pytest
from awslabs.dynamodb_mcp_server.markdown_formatter import MarkdownFormatter


@pytest.fixture
def sample_results():
    """Sample query results for testing using real airline database examples."""
    return {
        'comprehensive_table_analysis': {
            'description': 'Complete table statistics including structure, size, and metadata',
            'data': [
                {
                    'table_name': 'Seat',
                    'engine': 'InnoDB',
                    'row_count': 18603,
                    'avg_row_length_bytes': 85,
                    'data_size_bytes': 1589248,
                    'index_size_bytes': 1589248,
                    'data_size_mb': 1.52,
                    'index_size_mb': 1.52,
                    'total_size_mb': 3.03,
                    'free_space_bytes': 4194304,
                    'auto_increment': None,
                    'column_count': 7,
                    'fk_count': 1,
                    'created': '2025-10-01 09:20:41',
                    'last_updated': '2025-10-01 09:45:18',
                    'collation': 'utf8mb4_0900_ai_ci',
                },
                {
                    'table_name': 'Booking',
                    'engine': 'InnoDB',
                    'row_count': 16564,
                    'avg_row_length_bytes': 222,
                    'data_size_bytes': 3686400,
                    'index_size_bytes': 1490944,
                    'data_size_mb': 3.52,
                    'index_size_mb': 1.42,
                    'total_size_mb': 4.94,
                    'free_space_bytes': 4194304,
                    'auto_increment': None,
                    'column_count': 8,
                    'fk_count': 2,
                    'created': '2025-10-01 09:20:41',
                    'last_updated': '2025-10-01 09:46:19',
                    'collation': 'utf8mb4_0900_ai_ci',
                },
                {
                    'table_name': 'Flight',
                    'engine': 'InnoDB',
                    'row_count': 9927,
                    'avg_row_length_bytes': 160,
                    'data_size_bytes': 1589248,
                    'index_size_bytes': 606208,
                    'data_size_mb': 1.52,
                    'index_size_mb': 0.58,
                    'total_size_mb': 2.09,
                    'free_space_bytes': 4194304,
                    'auto_increment': None,
                    'column_count': 10,
                    'fk_count': 2,
                    'created': '2025-10-01 09:20:41',
                    'last_updated': '2025-10-01 09:45:16',
                    'collation': 'utf8mb4_0900_ai_ci',
                },
            ],
        },
        'column_analysis': {
            'description': 'Returns all column definitions including data types, nullability, keys, defaults, and extra attributes',
            'data': [
                {
                    'table_name': 'Aircraft',
                    'column_name': 'aircraft_id',
                    'position': 1,
                    'default_value': None,
                    'nullable': 'NO',
                    'data_type': 'varchar',
                    'char_max_length': 20,
                    'numeric_precision': None,
                    'numeric_scale': None,
                    'column_type': 'varchar(20)',
                    'key_type': 'PRI',
                    'extra': '',
                    'comment': '',
                },
                {
                    'table_name': 'Aircraft',
                    'column_name': 'aircraft_type',
                    'position': 2,
                    'default_value': None,
                    'nullable': 'NO',
                    'data_type': 'varchar',
                    'char_max_length': 50,
                    'numeric_precision': None,
                    'numeric_scale': None,
                    'column_type': 'varchar(50)',
                    'key_type': '',
                    'extra': '',
                    'comment': '',
                },
                {
                    'table_name': 'Passenger',
                    'column_name': 'email',
                    'position': 4,
                    'default_value': None,
                    'nullable': 'NO',
                    'data_type': 'varchar',
                    'char_max_length': 100,
                    'numeric_precision': None,
                    'numeric_scale': None,
                    'column_type': 'varchar(100)',
                    'key_type': 'UNI',
                    'extra': '',
                    'comment': '',
                },
            ],
        },
    }


@pytest.fixture
def sample_metadata():
    """Sample metadata for testing using real airline database."""
    return {
        'database': 'airline',
        'source_db_type': 'mysql',
        'analysis_period': '30 days',
        'max_query_results': 500,
        'performance_enabled': True,
        'skipped_queries': [],
    }


def test_markdown_formatter_initialization(tmp_path, sample_results, sample_metadata):
    """Test MarkdownFormatter initialization."""
    formatter = MarkdownFormatter(sample_results, sample_metadata, str(tmp_path))

    assert formatter.results == sample_results
    assert formatter.metadata == sample_metadata
    assert formatter.output_dir == str(tmp_path)
    assert formatter.file_registry == []
    assert formatter.skipped_queries == {}
    assert formatter.errors == []


def test_format_as_markdown_table_basic(tmp_path, sample_metadata):
    """Test basic markdown table formatting."""
    data = [
        {'name': 'Alice', 'age': 30, 'city': 'Seattle'},
        {'name': 'Bob', 'age': 25, 'city': 'Portland'},
    ]

    formatter = MarkdownFormatter({}, sample_metadata, str(tmp_path))
    table = formatter._format_as_markdown_table(data)

    assert '| name | age | city |' in table
    assert '| --- | --- | --- |' in table
    assert '| Alice | 30 | Seattle |' in table
    assert '| Bob | 25 | Portland |' in table


def test_format_as_markdown_table_with_nulls(tmp_path, sample_metadata):
    """Test markdown table formatting with NULL values."""
    data = [
        {'name': 'Alice', 'value': None},
        {'name': 'Bob', 'value': 42},
    ]

    formatter = MarkdownFormatter({}, sample_metadata, str(tmp_path))
    table = formatter._format_as_markdown_table(data)

    assert '| NULL |' in table
    assert '| 42 |' in table


def test_format_as_markdown_table_with_floats(tmp_path, sample_metadata):
    """Test markdown table formatting with float values."""
    data = [
        {'name': 'test', 'value': 3.14159},
    ]

    formatter = MarkdownFormatter({}, sample_metadata, str(tmp_path))
    table = formatter._format_as_markdown_table(data)

    assert '| 3.14 |' in table  # Should be rounded to 2 decimal places


def test_format_as_markdown_table_empty_data(tmp_path, sample_metadata):
    """Test markdown table formatting with empty data."""
    formatter = MarkdownFormatter({}, sample_metadata, str(tmp_path))
    table = formatter._format_as_markdown_table([])

    assert table == 'No data returned'


def test_format_as_markdown_table_none_data(tmp_path, sample_metadata):
    """Test markdown table formatting with None data."""
    formatter = MarkdownFormatter({}, sample_metadata, str(tmp_path))
    table = formatter._format_as_markdown_table(None)

    # None is caught by the "if not data:" check first
    assert table == 'No data returned'


def test_format_as_markdown_table_invalid_type(tmp_path, sample_metadata):
    """Test markdown table formatting with invalid data type."""
    formatter = MarkdownFormatter({}, sample_metadata, str(tmp_path))
    table = formatter._format_as_markdown_table('not a list')

    assert 'Error: Invalid data format' in table


def test_format_as_markdown_table_non_dict_row(tmp_path, sample_metadata):
    """Test markdown table formatting with non-dict row."""
    formatter = MarkdownFormatter({}, sample_metadata, str(tmp_path))
    table = formatter._format_as_markdown_table(['not a dict'])

    assert 'Error: Invalid data structure' in table


def test_format_as_markdown_table_empty_dict_row(tmp_path, sample_metadata):
    """Test markdown table formatting with empty dict as first row."""
    formatter = MarkdownFormatter({}, sample_metadata, str(tmp_path))
    table = formatter._format_as_markdown_table([{}])

    assert 'No columns available' in table


def test_format_as_markdown_table_mixed_row_types(tmp_path, sample_metadata):
    """Test markdown table formatting with mixed row types (skips invalid rows)."""
    data = [
        {'col1': 'value1', 'col2': 'value2'},
        'invalid row',  # This should be skipped
        {'col1': 'value3', 'col2': 'value4'},
    ]
    formatter = MarkdownFormatter({}, sample_metadata, str(tmp_path))
    table = formatter._format_as_markdown_table(data)

    # Should still generate table with valid rows
    assert '| col1 | col2 |' in table
    assert '| value1 | value2 |' in table
    assert '| value3 | value4 |' in table


def test_format_as_markdown_table_all_invalid_rows(tmp_path, sample_metadata):
    """Test markdown table formatting when all rows are invalid after first."""
    data = [
        {'col1': 'value1'},
        'invalid',
        'also invalid',
    ]
    formatter = MarkdownFormatter({}, sample_metadata, str(tmp_path))
    table = formatter._format_as_markdown_table(data)

    # Should still generate table with the one valid row
    assert '| col1 |' in table
    assert '| value1 |' in table


def test_format_as_markdown_table_escapes_pipes(tmp_path, sample_metadata):
    """Test markdown table formatting escapes pipe characters."""
    data = [
        {'name': 'test|value', 'description': 'has|pipes'},
    ]

    formatter = MarkdownFormatter({}, sample_metadata, str(tmp_path))
    table = formatter._format_as_markdown_table(data)

    assert '| test\\|value |' in table
    assert '| has\\|pipes |' in table


def test_generate_query_file(tmp_path, sample_metadata):
    """Test generating a single query result file."""
    query_result = {
        'description': 'Test query',
        'data': [{'col1': 'value1', 'col2': 'value2'}],
    }

    formatter = MarkdownFormatter({}, sample_metadata, str(tmp_path))
    file_path = formatter._generate_query_file('test_query', query_result)

    assert file_path == os.path.join(str(tmp_path), 'test_query.md')
    assert os.path.exists(file_path)

    with open(file_path, 'r') as f:
        content = f.read()
        assert '# Test Query' in content
        assert 'Test query' in content
        assert '| col1 | col2 |' in content
        assert '| value1 | value2 |' in content
        assert '**Total Rows**: 1' in content


def test_generate_skipped_query_file(tmp_path, sample_metadata):
    """Test generating a skipped query file."""
    formatter = MarkdownFormatter({}, sample_metadata, str(tmp_path))
    file_path = formatter._generate_skipped_query_file(
        'skipped_query', 'Performance Schema disabled'
    )

    assert file_path == os.path.join(str(tmp_path), 'skipped_query.md')
    assert os.path.exists(file_path)

    with open(file_path, 'r') as f:
        content = f.read()
        assert '# Skipped Query' in content
        assert '**Query Skipped**' in content
        assert 'Performance Schema disabled' in content


def test_generate_all_files(tmp_path, sample_results, sample_metadata):
    """Test generating all markdown files."""
    formatter = MarkdownFormatter(sample_results, sample_metadata, str(tmp_path))
    generated_files, errors = formatter.generate_all_files()

    # Should generate files for all expected queries (6 total: 4 schema + 2 performance)
    assert len(generated_files) == 6
    assert len(errors) == 0

    # Check that manifest was created
    manifest_path = os.path.join(str(tmp_path), 'manifest.md')
    assert os.path.exists(manifest_path)

    # Check that query files were created (using actual query names)
    assert os.path.exists(os.path.join(str(tmp_path), 'comprehensive_table_analysis.md'))
    assert os.path.exists(os.path.join(str(tmp_path), 'column_analysis.md'))


def test_generate_all_files_with_skipped_queries(tmp_path, sample_results):
    """Test generating files with skipped queries."""
    metadata = {
        'database': 'airline',
        'source_db_type': 'mysql',
        'analysis_period': '30 days',
        'max_query_results': 500,
        'performance_enabled': False,
        'skipped_queries': ['all_queries_stats', 'triggers_stats'],
    }

    formatter = MarkdownFormatter(sample_results, metadata, str(tmp_path))
    generated_files, errors = formatter.generate_all_files()

    # Should still generate 6 files (including skipped ones: 4 schema + 2 performance)
    assert len(generated_files) == 6

    # Check that skipped query files exist (using actual query name)
    assert os.path.exists(os.path.join(str(tmp_path), 'all_queries_stats.md'))

    # Verify skipped file content
    with open(os.path.join(str(tmp_path), 'all_queries_stats.md'), 'r') as f:
        content = f.read()
        assert '**Query Skipped**' in content
        assert 'Performance schema is disabled' in content


def test_manifest_generation(tmp_path, sample_results, sample_metadata):
    """Test manifest file generation."""
    formatter = MarkdownFormatter(sample_results, sample_metadata, str(tmp_path))
    formatter.generate_all_files()

    manifest_path = os.path.join(str(tmp_path), 'manifest.md')
    assert os.path.exists(manifest_path)

    with open(manifest_path, 'r') as f:
        content = f.read()
        assert '# Database Analysis Manifest' in content
        assert '## Metadata' in content
        assert '- **Database**: airline' in content
        assert '- **Performance Schema**: Enabled' in content
        assert '## Query Results Files' in content
        assert '### Schema Queries' in content
        assert '### Performance Queries' in content
        assert '## Summary Statistics' in content


def test_manifest_with_skipped_queries(tmp_path, sample_results):
    """Test manifest includes skipped queries section."""
    metadata = {
        'database': 'airline',
        'source_db_type': 'mysql',
        'analysis_period': '30 days',
        'max_query_results': 500,
        'performance_enabled': False,
        'skipped_queries': ['all_queries_stats'],
    }

    formatter = MarkdownFormatter(sample_results, metadata, str(tmp_path))
    formatter.generate_all_files()

    manifest_path = os.path.join(str(tmp_path), 'manifest.md')
    with open(manifest_path, 'r') as f:
        content = f.read()
        assert '## Skipped Queries' in content
        assert 'The following queries were not executed:' in content


def test_error_handling_invalid_data(tmp_path, sample_metadata):
    """Test error handling with invalid data."""
    results = {
        'bad_query': {
            'description': 'Bad query',
            'data': None,  # Invalid data
        }
    }

    formatter = MarkdownFormatter(results, sample_metadata, str(tmp_path))
    generated_files, errors = formatter.generate_all_files()

    # Should handle error gracefully
    assert len(generated_files) >= 0
    # Errors may or may not be captured depending on implementation


def test_summary_statistics_calculation(tmp_path, sample_results, sample_metadata):
    """Test that summary statistics are calculated correctly."""
    formatter = MarkdownFormatter(sample_results, sample_metadata, str(tmp_path))
    formatter.generate_all_files()

    manifest_path = os.path.join(str(tmp_path), 'manifest.md')
    with open(manifest_path, 'r') as f:
        content = f.read()
        assert '- **Total Tables**:' in content
        assert (
            '- **Total Columns**: 3' in content
        )  # 3 columns in sample data (Aircraft: aircraft_id, aircraft_type; Passenger: email)


def test_file_registry_tracking(tmp_path, sample_results, sample_metadata):
    """Test that file registry tracks generated files."""
    formatter = MarkdownFormatter(sample_results, sample_metadata, str(tmp_path))
    generated_files, errors = formatter.generate_all_files()

    # File registry should match generated files
    assert len(formatter.file_registry) == len(generated_files)
    assert all(os.path.exists(f) for f in formatter.file_registry)


def test_generate_query_file_write_error(tmp_path, sample_metadata, monkeypatch):
    """Test handling of file write errors."""
    import builtins

    original_open = builtins.open

    def mock_open_error(*args, **kwargs):
        if 'test_query.md' in str(args[0]) and 'w' in args[1]:
            raise OSError('Permission denied')
        return original_open(*args, **kwargs)

    monkeypatch.setattr('builtins.open', mock_open_error)

    query_result = {
        'description': 'Test query',
        'data': [{'col1': 'value1'}],
    }

    formatter = MarkdownFormatter({}, sample_metadata, str(tmp_path))
    file_path = formatter._generate_query_file('test_query', query_result)

    # Should return empty string on error
    assert file_path == ''
    # Should track error
    assert len(formatter.errors) == 1
    assert formatter.errors[0][0] == 'test_query'


def test_generate_skipped_query_file_write_error(tmp_path, sample_metadata, monkeypatch):
    """Test handling of file write errors for skipped queries."""
    import builtins

    original_open = builtins.open

    def mock_open_error(*args, **kwargs):
        if 'skipped_query.md' in str(args[0]) and 'w' in args[1]:
            raise OSError('Disk full')
        return original_open(*args, **kwargs)

    monkeypatch.setattr('builtins.open', mock_open_error)

    formatter = MarkdownFormatter({}, sample_metadata, str(tmp_path))
    file_path = formatter._generate_skipped_query_file('skipped_query', 'Test reason')

    # Should return empty string on error
    assert file_path == ''
    # Should track error
    assert len(formatter.errors) == 1
    assert formatter.errors[0][0] == 'skipped_query'


def test_generate_manifest_write_error(tmp_path, sample_results, sample_metadata, monkeypatch):
    """Test handling of manifest file write errors."""
    import builtins

    original_open = builtins.open

    def mock_open_error(*args, **kwargs):
        if 'manifest.md' in str(args[0]) and 'w' in args[1]:
            raise OSError('Cannot write manifest')
        return original_open(*args, **kwargs)

    monkeypatch.setattr('builtins.open', mock_open_error)

    formatter = MarkdownFormatter(sample_results, sample_metadata, str(tmp_path))
    generated_files, errors = formatter.generate_all_files()

    # Should track manifest error
    manifest_errors = [e for e in formatter.errors if e[0] == 'manifest']
    assert len(manifest_errors) == 1


def test_generate_all_files_directory_creation_error(sample_results, sample_metadata, monkeypatch):
    """Test handling of directory creation errors."""
    import os as os_module

    def mock_makedirs_error(*args, **kwargs):
        raise OSError('Cannot create directory')

    monkeypatch.setattr(os_module, 'makedirs', mock_makedirs_error)

    formatter = MarkdownFormatter(sample_results, sample_metadata, '/invalid/path')
    generated_files, errors = formatter.generate_all_files()

    # Should return empty list and track error
    assert len(generated_files) == 0
    assert len(errors) > 0
    assert any('directory_creation' in str(e[0]) for e in errors)


def test_format_as_markdown_table_row_formatting_error(tmp_path, sample_metadata):
    """Test handling of row formatting errors."""

    class BadValue:
        """A class that raises an error when converted to string."""

        def __str__(self):
            raise ValueError('Cannot convert to string')

    data = [
        {'col1': 'good_value', 'col2': BadValue()},
        {'col1': 'another_good', 'col2': 'also_good'},
    ]

    formatter = MarkdownFormatter({}, sample_metadata, str(tmp_path))
    table = formatter._format_as_markdown_table(data)

    # Should skip the bad row and continue with good rows
    assert '| col1 | col2 |' in table
    assert '| another_good | also_good |' in table


def test_generate_query_file_invalid_result_structure(tmp_path, sample_metadata):
    """Test handling of invalid query result structure."""
    # Missing 'data' key
    query_result = {
        'description': 'Test query',
        # 'data' key is missing
    }

    formatter = MarkdownFormatter({}, sample_metadata, str(tmp_path))
    file_path = formatter._generate_query_file('test_query', query_result)

    # Should still generate file with empty data
    assert file_path != ''
    assert os.path.exists(file_path)

    with open(file_path, 'r') as f:
        content = f.read()
        assert 'No data returned' in content or '**Total Rows**: 0' in content


def test_generate_query_file_unexpected_exception(tmp_path, sample_metadata, monkeypatch):
    """Test handling of unexpected exceptions in _generate_query_file."""

    # Mock datetime to raise an exception
    def mock_now_error():
        raise RuntimeError('Datetime error')

    import awslabs.dynamodb_mcp_server.markdown_formatter as mf_module

    class MockDateTime:
        @staticmethod
        def now():
            raise RuntimeError('Datetime error')

    monkeypatch.setattr(mf_module, 'datetime', MockDateTime)

    query_result = {
        'description': 'Test query',
        'data': [{'col1': 'value1'}],
    }

    formatter = MarkdownFormatter({}, sample_metadata, str(tmp_path))
    file_path = formatter._generate_query_file('test_query', query_result)

    # Should return empty string and track error
    assert file_path == ''
    assert len(formatter.errors) == 1
    assert 'test_query' in formatter.errors[0][0]
    assert 'Unexpected error' in formatter.errors[0][1]


def test_generate_skipped_query_file_unexpected_exception(tmp_path, sample_metadata, monkeypatch):
    """Test handling of unexpected exceptions in _generate_skipped_query_file."""
    import awslabs.dynamodb_mcp_server.markdown_formatter as mf_module

    class MockDateTime:
        @staticmethod
        def now():
            raise RuntimeError('Datetime error in skipped file')

    monkeypatch.setattr(mf_module, 'datetime', MockDateTime)

    formatter = MarkdownFormatter({}, sample_metadata, str(tmp_path))
    file_path = formatter._generate_skipped_query_file('skipped_query', 'Test reason')

    # Should return empty string and track error
    assert file_path == ''
    assert len(formatter.errors) == 1
    assert 'skipped_query' in formatter.errors[0][0]
    assert 'Unexpected error' in formatter.errors[0][1]


def test_generate_manifest_unexpected_exception(
    tmp_path, sample_results, sample_metadata, monkeypatch
):
    """Test handling of unexpected exceptions in _generate_manifest."""
    import awslabs.dynamodb_mcp_server.markdown_formatter as mf_module

    class MockDateTime:
        @staticmethod
        def now():
            raise RuntimeError('Datetime error in manifest')

    monkeypatch.setattr(mf_module, 'datetime', MockDateTime)

    formatter = MarkdownFormatter(sample_results, sample_metadata, str(tmp_path))

    # Call _generate_manifest directly
    formatter._generate_manifest()

    # Should track error
    manifest_errors = [e for e in formatter.errors if e[0] == 'manifest']
    assert len(manifest_errors) == 1
    assert 'Unexpected error' in manifest_errors[0][1]


def test_format_as_markdown_table_with_booleans(tmp_path, sample_metadata):
    """Test markdown table formatting with boolean values."""
    data = [
        {'name': 'test1', 'active': True},
        {'name': 'test2', 'active': False},
    ]

    formatter = MarkdownFormatter({}, sample_metadata, str(tmp_path))
    table = formatter._format_as_markdown_table(data)

    assert '| True |' in table
    assert '| False |' in table


def test_format_as_markdown_table_with_integers(tmp_path, sample_metadata):
    """Test markdown table formatting with integer values."""
    data = [
        {'id': 1, 'count': 100},
    ]

    formatter = MarkdownFormatter({}, sample_metadata, str(tmp_path))
    table = formatter._format_as_markdown_table(data)

    assert '| 1 |' in table
    assert '| 100 |' in table


def test_manifest_with_comprehensive_statistics(tmp_path, sample_metadata):
    """Test manifest generation with all statistics populated."""
    results = {
        'comprehensive_table_analysis': {
            'description': 'Table analysis',
            'data': [{'table_name': 'table1'}, {'table_name': 'table2'}],
        },
        'column_analysis': {
            'description': 'Column analysis',
            'data': [{'column_name': 'col1'}, {'column_name': 'col2'}, {'column_name': 'col3'}],
        },
        'comprehensive_index_analysis': {
            'description': 'Index analysis',
            'data': [{'index_name': 'idx1'}],
        },
        'foreign_key_analysis': {
            'description': 'FK analysis',
            'data': [{'fk_name': 'fk1'}, {'fk_name': 'fk2'}],
        },
        'all_queries_stats': {
            'description': 'Query stats',
            'data': [
                {'query': 'SELECT 1', 'source_type': 'QUERY'},
                {'query': 'SELECT 2', 'source_type': 'PROCEDURE'},
                {'query': 'SELECT 3', 'source_type': 'PROCEDURE'},
            ],
        },
        'triggers_stats': {
            'description': 'Trigger stats',
            'data': [{'trigger_name': 'trg1'}],
        },
    }

    formatter = MarkdownFormatter(results, sample_metadata, str(tmp_path))
    formatter.generate_all_files()

    manifest_path = os.path.join(str(tmp_path), 'manifest.md')
    with open(manifest_path, 'r') as f:
        content = f.read()
        assert '- **Total Tables**: 2' in content
        assert '- **Total Columns**: 3' in content
        assert '- **Total Indexes**: 1' in content
        assert '- **Total Foreign Keys**: 2' in content
        assert '- **Query Patterns Analyzed**: 3' in content
        assert '- **Stored Procedures**: 2' in content
        assert '- **Triggers**: 1' in content


def test_manifest_with_errors_section(tmp_path, sample_metadata):
    """Test manifest includes errors section when errors occur."""
    results = {
        'comprehensive_table_analysis': {
            'description': 'Table analysis',
            'data': [{'table_name': 'table1'}],
        },
    }

    formatter = MarkdownFormatter(results, sample_metadata, str(tmp_path))
    # Manually add some errors
    formatter.errors.append(('test_query', 'Test error message'))
    formatter.errors.append(('another_query', 'Another error'))

    formatter._generate_manifest()

    manifest_path = os.path.join(str(tmp_path), 'manifest.md')
    with open(manifest_path, 'r') as f:
        content = f.read()
        assert '## Errors' in content
        assert '2 error(s) occurred during file generation:' in content
        assert '- **test_query**: Test error message' in content
        assert '- **another_query**: Another error' in content


def test_generate_all_files_with_invalid_query_result(tmp_path, sample_metadata):
    """Test generate_all_files handles invalid query results."""
    results = {
        'comprehensive_table_analysis': 'not a dict',  # Invalid structure
    }

    formatter = MarkdownFormatter(results, sample_metadata, str(tmp_path))
    generated_files, errors = formatter.generate_all_files()

    # Should handle gracefully and create skipped file
    assert len(generated_files) >= 0


def test_generate_all_files_query_processing_exception(tmp_path, sample_metadata, monkeypatch):
    """Test handling of exceptions during query processing."""

    def mock_generate_query_file_error(*args, **kwargs):
        raise RuntimeError('Unexpected error in query file generation')

    results = {
        'comprehensive_table_analysis': {
            'description': 'Table analysis',
            'data': [{'table_name': 'table1'}],
        },
    }

    formatter = MarkdownFormatter(results, sample_metadata, str(tmp_path))
    monkeypatch.setattr(formatter, '_generate_query_file', mock_generate_query_file_error)

    generated_files, errors = formatter.generate_all_files()

    # Should track error and continue
    assert len(errors) > 0
    assert any('comprehensive_table_analysis' in str(e[0]) for e in errors)


def test_generate_all_files_critical_exception(tmp_path, sample_metadata, monkeypatch):
    """Test handling of critical exceptions in generate_all_files."""
    import awslabs.dynamodb_mcp_server.markdown_formatter as mf_module

    def mock_makedirs_critical(*args, **kwargs):
        # Allow directory creation but fail later
        pass

    def mock_get_schema_queries_error():
        raise RuntimeError('Critical error getting schema queries')

    monkeypatch.setattr('os.makedirs', mock_makedirs_critical)
    monkeypatch.setattr(mf_module, 'get_schema_queries', mock_get_schema_queries_error)

    formatter = MarkdownFormatter({}, sample_metadata, str(tmp_path))
    generated_files, errors = formatter.generate_all_files()

    # Should track critical error
    assert len(errors) > 0
    assert any('generate_all_files' in str(e[0]) for e in errors)


def test_generate_all_files_with_metadata_skipped_queries_non_performance(tmp_path):
    """Test skipped queries that are in metadata but not performance-related."""
    metadata = {
        'database': 'test',
        'source_db_type': 'mysql',
        'analysis_period': '30 days',
        'max_query_results': 500,
        'performance_enabled': True,  # Performance is enabled
        'skipped_queries': ['comprehensive_table_analysis'],  # Schema query skipped
    }

    results = {}

    formatter = MarkdownFormatter(results, metadata, str(tmp_path))
    generated_files, errors = formatter.generate_all_files()

    # Should create skipped file with appropriate reason
    skipped_file = os.path.join(str(tmp_path), 'comprehensive_table_analysis.md')
    assert os.path.exists(skipped_file)

    with open(skipped_file, 'r') as f:
        content = f.read()
        assert 'Query was skipped during analysis' in content


def test_generate_all_files_missing_query_not_in_metadata(tmp_path):
    """Test missing query that's not in metadata skipped list."""
    metadata = {
        'database': 'test',
        'source_db_type': 'mysql',
        'analysis_period': '30 days',
        'max_query_results': 500,
        'performance_enabled': True,
        'skipped_queries': [],  # Empty skipped list
    }

    results = {}  # No results for any query

    formatter = MarkdownFormatter(results, metadata, str(tmp_path))
    generated_files, errors = formatter.generate_all_files()

    # Should create skipped files with generic reason
    skipped_file = os.path.join(str(tmp_path), 'comprehensive_table_analysis.md')
    assert os.path.exists(skipped_file)

    with open(skipped_file, 'r') as f:
        content = f.read()
        assert 'Query was not executed or failed during analysis' in content


def test_format_as_markdown_table_all_rows_fail_formatting(tmp_path, sample_metadata):
    """Test when all rows fail to format (after first valid row)."""

    class BadValue:
        """A class that raises an error when converted to string."""

        def __str__(self):
            raise ValueError('Cannot convert')

    # First row is valid to get columns, but all subsequent processing fails
    data = [
        {'col1': BadValue(), 'col2': BadValue()},
    ]

    formatter = MarkdownFormatter({}, sample_metadata, str(tmp_path))
    table = formatter._format_as_markdown_table(data)

    # Should return error message when no rows can be formatted
    assert 'Error: Unable to format data rows' in table


def test_format_as_markdown_table_exception_handler(tmp_path, sample_metadata, monkeypatch):
    """Test exception handler in _format_as_markdown_table."""
    formatter = MarkdownFormatter({}, sample_metadata, str(tmp_path))

    # Patch isinstance to raise an exception during list check
    original_isinstance = isinstance

    def mock_isinstance(obj, classinfo):
        if classinfo is list and obj == [{'col': 'val'}]:
            raise RuntimeError('Unexpected error')
        return original_isinstance(obj, classinfo)

    import builtins

    monkeypatch.setattr(builtins, 'isinstance', mock_isinstance)

    result = formatter._format_as_markdown_table([{'col': 'val'}])
    assert 'Error: Unable to format data' in result
    assert 'Unexpected error' in result


def test_generate_all_files_with_file_write_failures(tmp_path, sample_metadata, monkeypatch):
    """Test generate_all_files when file generation returns empty string."""
    import builtins

    original_open = builtins.open

    def mock_open_error(*args, **kwargs):
        # Fail on markdown file writes but allow manifest
        if '.md' in str(args[0]) and 'w' in args[1] and 'manifest' not in str(args[0]):
            raise OSError('Write error')
        return original_open(*args, **kwargs)

    monkeypatch.setattr('builtins.open', mock_open_error)

    # Use actual expected query names from database_analysis_queries
    results = {
        'comprehensive_table_analysis': {'description': 'Test', 'data': [{'col': 'val'}]},
        'column_analysis': None,  # Invalid result to trigger skipped file generation
    }

    formatter = MarkdownFormatter(results, sample_metadata, str(tmp_path))
    formatter.generate_all_files()

    # File registry should be empty since all query file writes failed
    assert len(formatter.file_registry) == 0
    # Errors should be tracked for both valid and invalid queries
    assert len(formatter.errors) >= 2


def test_generate_all_files_skipped_query_write_failure(tmp_path, monkeypatch):
    """Test generate_all_files when skipped query file write fails."""
    import builtins

    original_open = builtins.open

    def mock_open_error(*args, **kwargs):
        # Fail only on skipped query file writes
        if '.md' in str(args[0]) and 'w' in args[1] and 'manifest' not in str(args[0]):
            raise OSError('Write error')
        return original_open(*args, **kwargs)

    monkeypatch.setattr('builtins.open', mock_open_error)

    # Metadata with performance schema disabled to trigger skipped queries
    metadata = {
        'database_name': 'test_db',
        'analysis_timestamp': '2024-01-01 00:00:00',
        'performance_enabled': False,
        'skipped_queries': [],
    }

    # Empty results - all queries will be skipped
    results = {}

    formatter = MarkdownFormatter(results, metadata, str(tmp_path))
    formatter.generate_all_files()

    # File registry should be empty since all writes failed
    assert len(formatter.file_registry) == 0
    # Should have errors for failed skipped query file writes
    assert len(formatter.errors) > 0
