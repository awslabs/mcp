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

"""Tests for the bounds on the SQL-offload handle's preview and schema."""

import json
import pytest
import sqlite3
from awslabs.billing_cost_management_mcp_server.utilities.sql_utils import (
    PREVIEW_BUDGET_BYTES,
    PREVIEW_CELL_MAX_CHARS,
    SCHEMA_BUDGET_BYTES,
    SCHEMA_COLUMN_LIMIT,
    _bounded_preview,
    _bounded_schema,
    _truncate_preview_value,
    _unserializable_preview_value,
    convert_api_response_to_table,
)
from fastmcp import Context
from unittest.mock import AsyncMock, MagicMock


OPERATION = 'compute_optimizer_automation_list_automation_rules'


@pytest.fixture
def session_db(tmp_path, monkeypatch):
    """Point convert_api_response_to_table at a file database the test can reopen.

    Patches that function's own module globals: other tests re-import sql_utils
    via sys.modules, so a fresh ``import sql_utils`` here can be a different
    module instance.
    """
    path = tmp_path / 'session.db'
    monkeypatch.setitem(
        convert_api_response_to_table.__globals__, 'get_session_db_path', lambda: str(path)
    )
    return path


@pytest.fixture
def ctx():
    """Create a mock MCP context."""
    context = MagicMock(spec=Context)
    context.info = AsyncMock()
    context.debug = AsyncMock()
    context.warning = AsyncMock()
    context.error = AsyncMock()
    return context


def _stored_columns(session_db, table_name):
    conn = sqlite3.connect(str(session_db))
    try:
        return [row[1] for row in conn.execute(f'PRAGMA table_info("{table_name}")')]
    finally:
        conn.close()


def _stored_value(session_db, table_name, column):
    conn = sqlite3.connect(str(session_db))
    try:
        return conn.execute(f'SELECT "{column}" FROM "{table_name}"').fetchone()[0]
    finally:
        conn.close()


def _row_costing(total_bytes, columns=None):
    """Build string cells under the per-cell cap whose JSON costs sum to ``total_bytes``."""
    columns = columns or [f'c{i:02d}' for i in range(40)]
    overheads = [len(json.dumps({column: ''}).encode('utf-8')) for column in columns]
    remaining = total_bytes - sum(overheads)
    row = []
    for _ in columns:
        length = min(remaining, 150)
        row.append('v' * length)
        remaining -= length
    assert remaining == 0
    return columns, tuple(row)


class _BadStr:
    def __str__(self):
        raise RuntimeError('no text form')


class TestTruncatePreviewValue:
    """Tests for _truncate_preview_value."""

    def test_long_string_gets_marker(self):
        """A string over the cap keeps its first PREVIEW_CELL_MAX_CHARS characters and a marker."""
        value = 'a' * 500
        assert _truncate_preview_value(value) == (
            f'{"a" * PREVIEW_CELL_MAX_CHARS}... [500 chars total, query the table for the full value]'
        )

    def test_short_and_non_string_values_unchanged(self):
        """Strings at or under the cap and non-strings pass through."""
        assert (
            _truncate_preview_value('a' * PREVIEW_CELL_MAX_CHARS) == 'a' * PREVIEW_CELL_MAX_CHARS
        )
        assert _truncate_preview_value('short') == 'short'
        assert _truncate_preview_value(12345) == 12345
        assert _truncate_preview_value(None) is None


class TestBoundedSchema:
    """Tests for _bounded_schema."""

    def test_narrow_schema_unchanged(self):
        """A schema within both bounds is returned whole with no count."""
        columns = ['a', 'b', 'c']
        assert _bounded_schema(columns) == (columns, None)

    def test_count_bound(self):
        """More than SCHEMA_COLUMN_LIMIT short names keeps the first 60."""
        columns = [f'c{i}' for i in range(100)]
        kept, count = _bounded_schema(columns)
        assert kept == columns[:SCHEMA_COLUMN_LIMIT]
        assert count == 100

    def test_byte_bound(self):
        """Long names stop at the byte budget before the count limit."""
        columns = [f'{"n" * 100}{i:02d}' for i in range(SCHEMA_COLUMN_LIMIT)]
        kept, count = _bounded_schema(columns)
        assert len(kept) < SCHEMA_COLUMN_LIMIT
        assert kept == columns[: len(kept)]
        assert len(json.dumps(kept).encode('utf-8')) <= SCHEMA_BUDGET_BYTES
        assert count == SCHEMA_COLUMN_LIMIT


class TestBoundedPreview:
    """Tests for _bounded_preview."""

    def test_unserializable_cell_does_not_drop_preview(self):
        """A cell whose str() raises becomes a placeholder; the row is kept."""
        preview, truncated = _bounded_preview([(1, _BadStr())], ['id', 'obj'])
        assert preview == [{'id': 1, 'obj': '<unserializable _BadStr>'}]
        assert truncated is False

    def test_unserializable_fallback_truncates_text(self):
        """The fallback text form is shortened like any other cell."""
        assert _unserializable_preview_value('x' * 300).startswith(
            'x' * PREVIEW_CELL_MAX_CHARS + '... [300 chars'
        )

    def test_empty_rows(self):
        """No rows gives an empty, untruncated preview."""
        assert _bounded_preview([], ['a', 'b']) == ([], False)

    def test_large_bytes_cell_is_shortened_not_dropped(self):
        """A large BLOB is shortened via its text form and the row is kept."""
        blob = b'\x00' * 10_000
        preview, truncated = _bounded_preview([(1, blob)], ['id', 'blob'])
        assert truncated is False
        assert len(preview) == 1
        assert preview[0]['id'] == 1
        assert preview[0]['blob'] == _truncate_preview_value(str(blob))
        assert f'[{len(str(blob))} chars total' in preview[0]['blob']

    def test_row_costing_exactly_the_budget_is_kept(self):
        """A single row whose cells cost exactly PREVIEW_BUDGET_BYTES is kept whole."""
        columns, row = _row_costing(PREVIEW_BUDGET_BYTES)
        preview, truncated = _bounded_preview([row], columns)
        assert truncated is False
        assert preview == [dict(zip(columns, row))]

    def test_second_row_one_byte_over_the_budget_is_dropped(self):
        """Two rows filling the budget exactly are kept; one byte more drops the second."""
        columns, first = _row_costing(PREVIEW_BUDGET_BYTES // 2)
        _, second = _row_costing(PREVIEW_BUDGET_BYTES - PREVIEW_BUDGET_BYTES // 2, columns)
        _, second_over = _row_costing(
            PREVIEW_BUDGET_BYTES - PREVIEW_BUDGET_BYTES // 2 + 1, columns
        )

        preview, truncated = _bounded_preview([first, second], columns)
        assert truncated is False
        assert len(preview) == 2

        preview, truncated = _bounded_preview([first, second_over], columns)
        assert truncated is True
        assert preview == [dict(zip(columns, first))]

    def test_rows_are_all_or_nothing(self):
        """A row that does not fit whole is dropped, not cut mid-row."""
        columns = [f'c{i}' for i in range(6)]
        rows = [tuple('v' * 150 for _ in columns) for _ in range(5)]
        preview, truncated = _bounded_preview(rows, columns)
        assert truncated is True
        assert 1 < len(preview) < 5
        assert all(list(item) == columns for item in preview)
        # Cells are costed per row; the list adds only its brackets and separators.
        assert len(json.dumps(preview).encode('utf-8')) <= PREVIEW_BUDGET_BYTES + 2 * len(preview)

    def test_first_row_wider_than_budget_keeps_leading_cells(self):
        """A first row over the budget alone yields one partial row."""
        columns = [f'c{i}' for i in range(40)]
        rows = [tuple('v' * 150 for _ in columns), tuple('w' for _ in columns)]
        preview, truncated = _bounded_preview(rows, columns)
        assert truncated is True
        assert len(preview) == 1
        assert 0 < len(preview[0]) < len(columns)
        assert list(preview[0]) == columns[: len(preview[0])]

    def test_first_cell_wider_than_budget_gives_empty_preview(self):
        """When not even one cell fits, the preview is empty and marked truncated."""
        column = 'k' * (PREVIEW_BUDGET_BYTES + 1)
        assert _bounded_preview([('v',)], [column]) == ([], True)


class TestConvertApiResponseHandleBounds:
    """End-to-end bounds on the handle returned by convert_api_response_to_table."""

    @pytest.mark.asyncio
    async def test_small_response_handle_unchanged(self, ctx, session_db):
        """A narrow response's handle has no bound fields and a full preview and schema."""
        response = {
            'automation_rules': [{'rule_id': f'r-{i}', 'name': f'RULE-{i}'} for i in range(3)],
            'count': 3,
        }
        result = await convert_api_response_to_table(ctx, response, OPERATION)

        assert result['schema'] == ['rule_id', 'name']
        assert result['preview'] == [
            {'rule_id': 'r-0', 'name': 'RULE-0'},
            {'rule_id': 'r-1', 'name': 'RULE-1'},
            {'rule_id': 'r-2', 'name': 'RULE-2'},
        ]
        assert 'preview_truncated' not in result
        assert 'schema_column_count' not in result

    @pytest.mark.asyncio
    async def test_long_cell_truncated_in_preview_only(self, ctx, session_db):
        """A long cell is shortened in the preview but stored in full."""
        description = 'd' * 1000
        response = {'automation_rules': [{'rule_id': 'r-1', 'description': description}]}
        result = await convert_api_response_to_table(ctx, response, OPERATION)

        assert result['preview'][0]['description'] == _truncate_preview_value(description)
        assert 'preview_truncated' not in result
        assert _stored_value(session_db, result['table_name'], 'description') == description

    @pytest.mark.asyncio
    async def test_wide_record_bounds_schema_and_preview(self, ctx, session_db):
        """200 long-named columns: schema and preview bounded, table keeps every column."""
        names = [f'attribute_with_a_long_flattened_name_{i:03d}' for i in range(200)]
        response = {'automation_rules': [{name: i for i, name in enumerate(names)}] * 3}
        result = await convert_api_response_to_table(ctx, response, OPERATION)

        assert len(result['schema']) <= SCHEMA_COLUMN_LIMIT
        assert result['schema'] == names[: len(result['schema'])]
        assert len(json.dumps(result['schema']).encode('utf-8')) <= SCHEMA_BUDGET_BYTES
        assert result['schema_column_count'] == 200
        # The first row alone exceeds the preview budget, so exactly one
        # partial row is returned.
        assert result['preview_truncated'] is True
        assert len(result['preview']) == 1
        assert _stored_columns(session_db, result['table_name']) == names

    @pytest.mark.asyncio
    async def test_tall_preview_keeps_whole_rows(self, ctx, session_db):
        """A preview over the budget drops whole rows; every kept row has every column."""
        columns = [f'field_{i}' for i in range(6)]
        response = {'automation_rules': [dict.fromkeys(columns, 'v' * 150) for _ in range(5)]}
        result = await convert_api_response_to_table(ctx, response, OPERATION)

        assert result['preview_truncated'] is True
        assert 1 < len(result['preview']) < 5
        assert all(list(item) == columns for item in result['preview'])
        assert 'schema_column_count' not in result

    @pytest.mark.asyncio
    async def test_metadata_cannot_overwrite_bound_fields(self, ctx, session_db):
        """Bound fields are set after caller metadata, so a keyword cannot replace them."""
        names = [f'c{i}' for i in range(100)]
        response = {'automation_rules': [dict.fromkeys(names, 'v' * 150)]}
        result = await convert_api_response_to_table(
            ctx, response, OPERATION, preview_truncated=False, schema_column_count=0
        )

        assert result['preview_truncated'] is True
        assert result['schema_column_count'] == 100
