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
