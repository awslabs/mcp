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
"""Tests for server helper functions."""

from awslabs.postgres_mcp_server.server import extract_cell, parse_execute_response


class TestExtractCell:
    """Tests for the extract_cell helper function."""

    def test_extract_null_cell(self):
        """Test extracting a null cell."""
        cell = {'isNull': True}
        assert extract_cell(cell) is None

    def test_extract_string_value(self):
        """Test extracting a string value."""
        cell = {'stringValue': 'test_string'}
        assert extract_cell(cell) == 'test_string'

    def test_extract_long_value(self):
        """Test extracting a long value."""
        cell = {'longValue': 42}
        assert extract_cell(cell) == 42

    def test_extract_double_value(self):
        """Test extracting a double value."""
        cell = {'doubleValue': 3.14}
        assert extract_cell(cell) == 3.14

    def test_extract_boolean_value(self):
        """Test extracting a boolean value."""
        cell = {'booleanValue': True}
        assert extract_cell(cell) is True

    def test_extract_blob_value(self):
        """Test extracting a blob value."""
        cell = {'blobValue': b'binary_data'}
        assert extract_cell(cell) == b'binary_data'

    def test_extract_array_value(self):
        """Test extracting an array value."""
        cell = {'arrayValue': [1, 2, 3]}
        assert extract_cell(cell) == [1, 2, 3]

    def test_extract_empty_cell(self):
        """Test extracting an empty cell."""
        cell = {}
        assert extract_cell(cell) is None

    def test_extract_cell_with_multiple_keys_prefers_first(self):
        """Test that extract_cell returns the first matching key."""
        # If multiple keys exist, stringValue should be checked first
        cell = {'stringValue': 'string', 'longValue': 42}
        assert extract_cell(cell) == 'string'


class TestParseExecuteResponse:
    """Tests for the parse_execute_response helper function."""

    def test_parse_empty_response(self):
        """Test parsing an empty response."""
        response = {'columnMetadata': [], 'records': []}
        result = parse_execute_response(response)
        assert result == []

    def test_parse_single_row_single_column(self):
        """Test parsing a single row with single column."""
        response = {'columnMetadata': [{'name': 'id'}], 'records': [[{'longValue': 1}]]}
        result = parse_execute_response(response)
        assert len(result) == 1
        assert result[0] == {'id': 1}

    def test_parse_multiple_rows_multiple_columns(self):
        """Test parsing multiple rows with multiple columns."""
        response = {
            'columnMetadata': [{'name': 'id'}, {'name': 'name'}, {'name': 'active'}],
            'records': [
                [{'longValue': 1}, {'stringValue': 'Alice'}, {'booleanValue': True}],
                [{'longValue': 2}, {'stringValue': 'Bob'}, {'booleanValue': False}],
            ],
        }
        result = parse_execute_response(response)
        assert len(result) == 2
        assert result[0] == {'id': 1, 'name': 'Alice', 'active': True}
        assert result[1] == {'id': 2, 'name': 'Bob', 'active': False}

    def test_parse_with_null_values(self):
        """Test parsing response with null values."""
        response = {
            'columnMetadata': [{'name': 'id'}, {'name': 'name'}],
            'records': [[{'longValue': 1}, {'isNull': True}]],
        }
        result = parse_execute_response(response)
        assert len(result) == 1
        assert result[0] == {'id': 1, 'name': None}

    def test_parse_with_various_types(self):
        """Test parsing response with various data types."""
        response = {
            'columnMetadata': [
                {'name': 'str_col'},
                {'name': 'int_col'},
                {'name': 'float_col'},
                {'name': 'bool_col'},
                {'name': 'blob_col'},
                {'name': 'array_col'},
            ],
            'records': [
                [
                    {'stringValue': 'text'},
                    {'longValue': 100},
                    {'doubleValue': 99.99},
                    {'booleanValue': True},
                    {'blobValue': b'data'},
                    {'arrayValue': [1, 2, 3]},
                ]
            ],
        }
        result = parse_execute_response(response)
        assert len(result) == 1
        assert result[0] == {
            'str_col': 'text',
            'int_col': 100,
            'float_col': 99.99,
            'bool_col': True,
            'blob_col': b'data',
            'array_col': [1, 2, 3],
        }

    def test_parse_missing_column_metadata(self):
        """Test parsing response with missing columnMetadata."""
        response = {'records': [[{'longValue': 1}]]}
        result = parse_execute_response(response)
        # When columnMetadata is missing, it returns empty dict for each row
        assert len(result) == 1
        assert result[0] == {}

    def test_parse_missing_records(self):
        """Test parsing response with missing records."""
        response = {'columnMetadata': [{'name': 'id'}]}
        result = parse_execute_response(response)
        # Should handle missing records gracefully
        assert result == []
