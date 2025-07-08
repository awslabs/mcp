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

"""Tests for the database module."""

import pytest
from awslabs.s3_tables_mcp_server.database import (
    _get_query_operations,  # Added for direct testing
    append_rows_to_table_resource,
    query_database_resource,
)
from unittest.mock import MagicMock, patch


class TestQueryDatabaseResource:
    """Test the query_database_resource function (PyIceberg)."""

    @pytest.mark.asyncio
    async def test_query_database_resource_success(self):
        """Test successful read-only query execution."""
        warehouse = 's3://my-warehouse/'
        region = 'us-west-2'
        namespace = 'test-namespace'
        query = 'SELECT * FROM test_table'
        expected_result = {'columns': ['id', 'name'], 'rows': [[1, 'test']]}

        with (
            patch('awslabs.s3_tables_mcp_server.database.PyIcebergConfig') as mock_config,
            patch('awslabs.s3_tables_mcp_server.database.PyIcebergEngine') as mock_engine,
        ):
            engine_instance = MagicMock()
            engine_instance.execute_query.return_value = expected_result
            mock_engine.return_value = engine_instance

            result = await query_database_resource(
                warehouse=warehouse,
                region=region,
                namespace=namespace,
                query=query,
            )
            assert result == expected_result
            mock_config.assert_called_once()
            mock_engine.assert_called_once()
            engine_instance.execute_query.assert_called_once_with(query)

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        'write_query',
        [
            'INSERT INTO test_table VALUES (1)',
            'UPDATE test_table SET name = "x"',
            'DELETE FROM test_table WHERE id = 1',
            'DROP TABLE test_table',
        ],
    )
    async def test_query_database_resource_rejects_write(self, write_query):
        """Test that write queries are rejected by query_database_resource."""
        warehouse = 's3://my-warehouse/'
        region = 'us-west-2'
        namespace = 'test-namespace'
        with pytest.raises(ValueError, match='Write operations are not allowed'):
            await query_database_resource(
                warehouse=warehouse,
                region=region,
                namespace=namespace,
                query=write_query,
            )


class TestAppendRowsToTableResource:
    """Test the append_rows_to_table_resource function (PyIceberg)."""

    @pytest.mark.asyncio
    async def test_append_rows_success(self):
        """Test successful appending of rows to a table using append_rows_to_table_resource."""
        warehouse = 's3://my-warehouse/'
        region = 'us-west-2'
        namespace = 'test-namespace'
        table_name = 'test_table'
        rows = [
            {'id': 1, 'name': 'Alice'},
            {'id': 2, 'name': 'Bob'},
        ]
        with (
            patch('awslabs.s3_tables_mcp_server.database.PyIcebergConfig') as mock_config,
            patch('awslabs.s3_tables_mcp_server.database.PyIcebergEngine') as mock_engine,
        ):
            engine_instance = MagicMock()
            mock_engine.return_value = engine_instance

            result = await append_rows_to_table_resource(
                warehouse=warehouse,
                region=region,
                namespace=namespace,
                table_name=table_name,
                rows=rows,
            )
            assert result['status'] == 'success'
            assert result['rows_appended'] == len(rows)
            mock_config.assert_called_once()
            mock_engine.assert_called_once()
            engine_instance.append_rows.assert_called_once_with(table_name, rows)


class TestGetQueryOperations:
    """Test the _get_query_operations function."""

    def test_simple_select(self):
        """Should extract 'SELECT' from a simple SELECT query."""
        query = 'SELECT * FROM table1'
        ops = _get_query_operations(query)
        assert 'SELECT' in ops

    def test_simple_insert(self):
        """Should extract 'INSERT' from a simple INSERT query."""
        query = 'INSERT INTO table1 VALUES (1)'
        ops = _get_query_operations(query)
        assert 'INSERT' in ops

    def test_mixed_case(self):
        """Should extract both 'SELECT' and 'INSERT' from mixed-case queries."""
        query = 'select * from table1; Insert into table2 values (2)'
        ops = _get_query_operations(query)
        # Should be case-insensitive and extract both
        assert 'SELECT' in ops
        assert 'INSERT' in ops

    def test_multiple_statements(self):
        """Should extract all main operations from multiple statements in one query."""
        query = 'SELECT * FROM t1; UPDATE t2 SET x=1; DELETE FROM t3'
        ops = _get_query_operations(query)
        assert 'SELECT' in ops
        assert 'UPDATE' in ops
        assert 'DELETE' in ops

    def test_empty_query(self):
        """Should return an empty set for an empty query string."""
        query = ''
        ops = _get_query_operations(query)
        assert ops == set()

    def test_whitespace_only(self):
        """Should return an empty set for a query with only whitespace."""
        query = '   \n   \t  '
        ops = _get_query_operations(query)
        assert ops == set()

    def test_comment_only(self):
        """Should return an empty set for a query with only comments."""
        query = '-- this is a comment\n'
        ops = _get_query_operations(query)
        assert ops == set()

    def test_complex_query(self):
        """Should extract 'SELECT' and 'INSERT' from a query with comments and multiple statements."""
        query = '/* comment */\nSELECT a FROM t1 WHERE b = 2;\n-- another comment\nINSERT INTO t2 VALUES (3)'
        ops = _get_query_operations(query)
        assert 'SELECT' in ops
        assert 'INSERT' in ops

    def test_punctuation_and_numbers(self):
        """Should ignore punctuation and numbers, not add them as operations."""
        query = '12345 ; , . ( )'
        ops = _get_query_operations(query)
        assert ops == set()

    def test_mixed_tokens(self):
        """Should only add alphabetic tokens as operations, ignore others."""
        query = 'SELECT * FROM t1; 123; -- comment\nINSERT INTO t2; $%^&*()'
        ops = _get_query_operations(query)
        assert 'SELECT' in ops
        assert 'INSERT' in ops
        assert 'FROM' in ops  # FROM is also an alpha token
        # Numbers and symbols should not be present
        assert not any(token in ops for token in ['123', '$', '%', '^', '&', '*', '()'])


class TestQueryDatabaseResourceEdgeCases:
    """Test edge cases and error handling for query_database_resource."""

    @pytest.mark.asyncio
    async def test_empty_query(self):
        """Should not raise for empty query, just return result from engine."""
        with (
            patch('awslabs.s3_tables_mcp_server.database.PyIcebergEngine') as mock_engine,
        ):
            engine_instance = MagicMock()
            engine_instance.execute_query.return_value = {'columns': [], 'rows': []}
            mock_engine.return_value = engine_instance
            result = await query_database_resource(
                warehouse='s3://w/', region='r', namespace='n', query=''
            )
            assert result == {'columns': [], 'rows': []}

    @pytest.mark.asyncio
    async def test_whitespace_only_query(self):
        """Should not raise for whitespace-only query, just return result from engine."""
        with (
            patch('awslabs.s3_tables_mcp_server.database.PyIcebergEngine') as mock_engine,
        ):
            engine_instance = MagicMock()
            engine_instance.execute_query.return_value = {'columns': [], 'rows': []}
            mock_engine.return_value = engine_instance
            result = await query_database_resource(
                warehouse='s3://w/', region='r', namespace='n', query='   \n  \t  '
            )
            assert result == {'columns': [], 'rows': []}

    @pytest.mark.asyncio
    async def test_comment_only_query(self):
        """Should not raise for comment-only query, just return result from engine."""
        with (
            patch('awslabs.s3_tables_mcp_server.database.PyIcebergEngine') as mock_engine,
        ):
            engine_instance = MagicMock()
            engine_instance.execute_query.return_value = {'columns': [], 'rows': []}
            mock_engine.return_value = engine_instance
            result = await query_database_resource(
                warehouse='s3://w/', region='r', namespace='n', query='-- comment only\n'
            )
            assert result == {'columns': [], 'rows': []}

    @pytest.mark.asyncio
    async def test_engine_execute_query_raises(self):
        """Should propagate exceptions from engine.execute_query."""
        with (
            patch('awslabs.s3_tables_mcp_server.database.PyIcebergConfig'),
            patch('awslabs.s3_tables_mcp_server.database.PyIcebergEngine') as mock_engine,
        ):
            engine_instance = MagicMock()
            engine_instance.execute_query.side_effect = RuntimeError('engine error')
            mock_engine.return_value = engine_instance
            with pytest.raises(RuntimeError, match='engine error'):
                await query_database_resource(
                    warehouse='s3://w/', region='r', namespace='n', query='SELECT 1'
                )


class TestAppendRowsToTableResourceEdgeCases:
    """Test edge cases and error handling for append_rows_to_table_resource."""

    @pytest.mark.asyncio
    async def test_append_empty_rows(self):
        """Should succeed and report 0 rows appended if rows is empty."""
        with (
            patch('awslabs.s3_tables_mcp_server.database.PyIcebergConfig'),
            patch('awslabs.s3_tables_mcp_server.database.PyIcebergEngine') as mock_engine,
        ):
            engine_instance = MagicMock()
            mock_engine.return_value = engine_instance
            result = await append_rows_to_table_resource(
                warehouse='s3://w/', region='r', namespace='n', table_name='t', rows=[]
            )
            assert result['status'] == 'success'
            assert result['rows_appended'] == 0
            engine_instance.append_rows.assert_called_once_with('t', [])

    @pytest.mark.asyncio
    async def test_append_rows_engine_raises(self):
        """Should propagate exceptions from engine.append_rows."""
        with (
            patch('awslabs.s3_tables_mcp_server.database.PyIcebergConfig'),
            patch('awslabs.s3_tables_mcp_server.database.PyIcebergEngine') as mock_engine,
        ):
            engine_instance = MagicMock()
            engine_instance.append_rows.side_effect = RuntimeError('append error')
            mock_engine.return_value = engine_instance
            with pytest.raises(RuntimeError, match='append error'):
                await append_rows_to_table_resource(
                    warehouse='s3://w/',
                    region='r',
                    namespace='n',
                    table_name='t',
                    rows=[{'id': 1}],
                )
