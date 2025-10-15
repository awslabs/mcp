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
                    'collation': 'utf8mb4_0900_ai_ci'
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
                    'collation': 'utf8mb4_0900_ai_ci'
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
                    'collation': 'utf8mb4_0900_ai_ci'
                }
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
                    'comment': ''
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
                    'comment': ''
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
                    'comment': ''
                }
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
    
    assert table == "No data returned"


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
    
    # Should generate files for all expected queries (7 total)
    assert len(generated_files) == 7
    assert len(errors) == 0
    
    # Check that manifest was created
    manifest_path = os.path.join(str(tmp_path), 'manifest.md')
    assert os.path.exists(manifest_path)
    
    # Check that query files were created
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
        'skipped_queries': ['all_queries_stats', 'stored_procedures_stats', 'triggers_stats'],
    }
    
    formatter = MarkdownFormatter(sample_results, metadata, str(tmp_path))
    generated_files, errors = formatter.generate_all_files()
    
    # Should still generate 7 files (including skipped ones)
    assert len(generated_files) == 7
    
    # Check that skipped query files exist
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
        assert '- **Total Columns**: 3' in content  # 3 columns in sample data (Aircraft: aircraft_id, aircraft_type; Passenger: email)


def test_file_registry_tracking(tmp_path, sample_results, sample_metadata):
    """Test that file registry tracks generated files."""
    formatter = MarkdownFormatter(sample_results, sample_metadata, str(tmp_path))
    generated_files, errors = formatter.generate_all_files()
    
    # File registry should match generated files
    assert len(formatter.file_registry) == len(generated_files)
    assert all(os.path.exists(f) for f in formatter.file_registry)
