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

"""Tests for extract_cell, parse_execute_response, DummyCtx."""

from awslabs.mysql_mcp_server.server import DummyCtx, extract_cell, parse_execute_response


class TestExtractCell:
    """Tests for extract_cell."""

    def test_null_value(self):
        """Should return None for isNull cells."""
        assert extract_cell({'isNull': True}) is None

    def test_string_value(self):
        """Should extract stringValue."""
        assert extract_cell({'stringValue': 'hello'}) == 'hello'

    def test_long_value(self):
        """Should extract longValue."""
        assert extract_cell({'longValue': 42}) == 42

    def test_double_value(self):
        """Should extract doubleValue."""
        assert extract_cell({'doubleValue': 3.14}) == 3.14

    def test_boolean_value(self):
        """Should extract booleanValue."""
        assert extract_cell({'booleanValue': True}) is True
        assert extract_cell({'booleanValue': False}) is False

    def test_blob_value(self):
        """Should extract blobValue."""
        assert extract_cell({'blobValue': b'\x00\x01'}) == b'\x00\x01'

    def test_array_value(self):
        """Should extract arrayValue."""
        arr = [{'stringValue': 'a'}, {'stringValue': 'b'}]
        assert extract_cell({'arrayValue': arr}) == arr

    def test_empty_cell(self):
        """Should return None for empty cell."""
        assert extract_cell({}) is None

    def test_null_false_not_null(self):
        """Should not treat isNull=False as null."""
        assert extract_cell({'isNull': False, 'stringValue': 'val'}) == 'val'

    def test_string_empty(self):
        """Should return empty string for empty stringValue."""
        assert extract_cell({'stringValue': ''}) == ''

    def test_long_zero(self):
        """Should return 0 for longValue=0."""
        assert extract_cell({'longValue': 0}) == 0

    def test_double_zero(self):
        """Should return 0.0 for doubleValue=0.0."""
        assert extract_cell({'doubleValue': 0.0}) == 0.0


class TestParseExecuteResponse:
    """Tests for parse_execute_response."""

    def test_empty_response(self):
        """Should return empty list for empty response."""
        result = parse_execute_response({})
        assert result == []

    def test_no_records(self):
        """Should return empty list when no records."""
        result = parse_execute_response(
            {
                'columnMetadata': [{'name': 'id'}],
                'records': [],
            }
        )
        assert result == []

    def test_single_row(self):
        """Should parse a single row."""
        result = parse_execute_response(
            {
                'columnMetadata': [{'name': 'id'}, {'name': 'name'}],
                'records': [[{'longValue': 1}, {'stringValue': 'Alice'}]],
            }
        )
        assert len(result) == 1
        assert result[0] == {'id': 1, 'name': 'Alice'}

    def test_multiple_rows(self):
        """Should parse multiple rows."""
        result = parse_execute_response(
            {
                'columnMetadata': [{'name': 'id'}, {'name': 'name'}],
                'records': [
                    [{'longValue': 1}, {'stringValue': 'Alice'}],
                    [{'longValue': 2}, {'stringValue': 'Bob'}],
                ],
            }
        )
        assert len(result) == 2
        assert result[0] == {'id': 1, 'name': 'Alice'}
        assert result[1] == {'id': 2, 'name': 'Bob'}

    def test_null_values(self):
        """Should handle null values in records."""
        result = parse_execute_response(
            {
                'columnMetadata': [{'name': 'id'}, {'name': 'email'}],
                'records': [[{'longValue': 1}, {'isNull': True}]],
            }
        )
        assert result[0] == {'id': 1, 'email': None}

    def test_mixed_types(self):
        """Should handle mixed value types."""
        result = parse_execute_response(
            {
                'columnMetadata': [
                    {'name': 'id'},
                    {'name': 'name'},
                    {'name': 'score'},
                    {'name': 'active'},
                ],
                'records': [
                    [
                        {'longValue': 1},
                        {'stringValue': 'Alice'},
                        {'doubleValue': 95.5},
                        {'booleanValue': True},
                    ]
                ],
            }
        )
        assert result[0] == {'id': 1, 'name': 'Alice', 'score': 95.5, 'active': True}

    def test_no_column_metadata(self):
        """Should handle missing columnMetadata."""
        result = parse_execute_response({'records': []})
        assert result == []


class TestDummyCtx:
    """Tests for DummyCtx."""

    async def test_error_does_not_raise(self):
        """DummyCtx.error should not raise."""
        ctx = DummyCtx()
        await ctx.error('test error message')

    async def test_error_accepts_any_message(self):
        """DummyCtx.error should accept any string."""
        ctx = DummyCtx()
        await ctx.error('')
        await ctx.error('some error')
        await ctx.error(None)

    def test_dummy_ctx_instantiation(self):
        """Should be able to instantiate DummyCtx."""
        ctx = DummyCtx()
        assert ctx is not None
