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

"""Tests for error paths in run_query."""

import pytest
from awslabs.mysql_mcp_server.connection.db_connection_map import ConnectionMethod
from awslabs.mysql_mcp_server.server import (
    client_error_code_key,
    query_injection_risk_key,
    run_query,
    unexpected_error_key,
    write_query_prohibited_key,
)
from botocore.exceptions import ClientError
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.fixture
def mock_ctx():
    """Create a mock MCP context."""
    ctx = AsyncMock()
    ctx.error = AsyncMock()
    return ctx


class TestRunQueryNoConnection:
    """Tests for run_query when no connection exists."""

    @patch('awslabs.mysql_mcp_server.server.db_connection_map')
    async def test_no_connection_returns_error(self, mock_map, mock_ctx):
        """Should return error when no connection is found."""
        mock_map.get.return_value = None

        result = await run_query(
            sql='SELECT 1',
            ctx=mock_ctx,
            connection_method=ConnectionMethod.RDS_API,
            cluster_identifier='cluster-1',
            db_endpoint='ep',
            database='testdb',
        )

        assert len(result) == 1
        assert 'error' in result[0]
        assert 'No database connection available' in result[0]['error']
        mock_ctx.error.assert_called_once()


class TestRunQueryReadonlyEnforcement:
    """Tests for readonly query enforcement."""

    @patch('awslabs.mysql_mcp_server.server.db_connection_map')
    async def test_rejects_insert_in_readonly(self, mock_map, mock_ctx):
        """Should reject INSERT when readonly is True."""
        mock_conn = MagicMock()
        mock_conn.readonly_query = True
        mock_map.get.return_value = mock_conn

        result = await run_query(
            sql='INSERT INTO users VALUES (1, "test")',
            ctx=mock_ctx,
            connection_method=ConnectionMethod.RDS_API,
            cluster_identifier='cluster-1',
            db_endpoint='ep',
            database='testdb',
        )

        assert result[0]['error'] == write_query_prohibited_key

    @patch('awslabs.mysql_mcp_server.server.db_connection_map')
    async def test_rejects_update_in_readonly(self, mock_map, mock_ctx):
        """Should reject UPDATE when readonly is True."""
        mock_conn = MagicMock()
        mock_conn.readonly_query = True
        mock_map.get.return_value = mock_conn

        result = await run_query(
            sql='UPDATE users SET name = "test" WHERE id = 1',
            ctx=mock_ctx,
            connection_method=ConnectionMethod.RDS_API,
            cluster_identifier='cluster-1',
            db_endpoint='ep',
            database='testdb',
        )

        assert result[0]['error'] == write_query_prohibited_key

    @patch('awslabs.mysql_mcp_server.server.db_connection_map')
    async def test_rejects_delete_in_readonly(self, mock_map, mock_ctx):
        """Should reject DELETE when readonly is True."""
        mock_conn = MagicMock()
        mock_conn.readonly_query = True
        mock_map.get.return_value = mock_conn

        result = await run_query(
            sql='DELETE FROM users WHERE id = 1',
            ctx=mock_ctx,
            connection_method=ConnectionMethod.RDS_API,
            cluster_identifier='cluster-1',
            db_endpoint='ep',
            database='testdb',
        )

        assert result[0]['error'] == write_query_prohibited_key

    @patch('awslabs.mysql_mcp_server.server.db_connection_map')
    async def test_rejects_drop_in_readonly(self, mock_map, mock_ctx):
        """Should reject DROP when readonly is True."""
        mock_conn = MagicMock()
        mock_conn.readonly_query = True
        mock_map.get.return_value = mock_conn

        result = await run_query(
            sql='DROP TABLE users',
            ctx=mock_ctx,
            connection_method=ConnectionMethod.RDS_API,
            cluster_identifier='cluster-1',
            db_endpoint='ep',
            database='testdb',
        )

        assert result[0]['error'] == write_query_prohibited_key

    @patch('awslabs.mysql_mcp_server.server.db_connection_map')
    async def test_allows_select_in_readonly(self, mock_map, mock_ctx):
        """Should allow SELECT when readonly is True."""
        mock_conn = MagicMock()
        mock_conn.readonly_query = True
        mock_conn.execute_query = AsyncMock(
            return_value={'columnMetadata': [{'name': 'id'}], 'records': [[{'longValue': 1}]]}
        )
        mock_map.get.return_value = mock_conn

        result = await run_query(
            sql='SELECT * FROM users',
            ctx=mock_ctx,
            connection_method=ConnectionMethod.RDS_API,
            cluster_identifier='cluster-1',
            db_endpoint='ep',
            database='testdb',
        )

        assert 'error' not in result[0]


class TestRunQuerySQLInjection:
    """Tests for SQL injection detection."""

    @patch('awslabs.mysql_mcp_server.server.db_connection_map')
    async def test_rejects_union_select_injection(self, mock_map, mock_ctx):
        """Should reject UNION SELECT injection."""
        mock_conn = MagicMock()
        mock_conn.readonly_query = False
        mock_map.get.return_value = mock_conn

        result = await run_query(
            sql='SELECT * FROM users WHERE id = 1 UNION SELECT * FROM passwords',
            ctx=mock_ctx,
            connection_method=ConnectionMethod.RDS_API,
            cluster_identifier='cluster-1',
            db_endpoint='ep',
            database='testdb',
        )

        assert result[0]['error'] == query_injection_risk_key

    @patch('awslabs.mysql_mcp_server.server.db_connection_map')
    async def test_rejects_sleep_injection(self, mock_map, mock_ctx):
        """Should reject SLEEP() injection."""
        mock_conn = MagicMock()
        mock_conn.readonly_query = False
        mock_map.get.return_value = mock_conn

        result = await run_query(
            sql='SELECT * FROM users WHERE id = 1 AND sleep(5)',
            ctx=mock_ctx,
            connection_method=ConnectionMethod.RDS_API,
            cluster_identifier='cluster-1',
            db_endpoint='ep',
            database='testdb',
        )

        assert result[0]['error'] == query_injection_risk_key

    @patch('awslabs.mysql_mcp_server.server.db_connection_map')
    async def test_rejects_stacked_queries(self, mock_map, mock_ctx):
        """Should reject stacked queries."""
        mock_conn = MagicMock()
        mock_conn.readonly_query = False
        mock_map.get.return_value = mock_conn

        result = await run_query(
            sql='SELECT 1; DROP TABLE users',
            ctx=mock_ctx,
            connection_method=ConnectionMethod.RDS_API,
            cluster_identifier='cluster-1',
            db_endpoint='ep',
            database='testdb',
        )

        assert result[0]['error'] == query_injection_risk_key


class TestRunQueryClientError:
    """Tests for ClientError handling."""

    @patch('awslabs.mysql_mcp_server.server.db_connection_map')
    async def test_handles_client_error(self, mock_map, mock_ctx):
        """Should handle ClientError and return error response."""
        mock_conn = MagicMock()
        mock_conn.readonly_query = False
        mock_conn.execute_query = AsyncMock(
            side_effect=ClientError(
                {'Error': {'Code': 'BadRequestException', 'Message': 'Invalid SQL'}},
                'ExecuteStatement',
            )
        )
        mock_map.get.return_value = mock_conn

        result = await run_query(
            sql='SELECT 1',
            ctx=mock_ctx,
            connection_method=ConnectionMethod.RDS_API,
            cluster_identifier='cluster-1',
            db_endpoint='ep',
            database='testdb',
        )

        assert result[0]['error'] == client_error_code_key
        mock_ctx.error.assert_called_once()


class TestRunQueryUnexpectedError:
    """Tests for unexpected error handling."""

    @patch('awslabs.mysql_mcp_server.server.db_connection_map')
    async def test_handles_unexpected_error(self, mock_map, mock_ctx):
        """Should handle unexpected exceptions and return error response."""
        mock_conn = MagicMock()
        mock_conn.readonly_query = False
        mock_conn.execute_query = AsyncMock(side_effect=RuntimeError('something broke'))
        mock_map.get.return_value = mock_conn

        result = await run_query(
            sql='SELECT 1',
            ctx=mock_ctx,
            connection_method=ConnectionMethod.RDS_API,
            cluster_identifier='cluster-1',
            db_endpoint='ep',
            database='testdb',
        )

        assert result[0]['error'] == unexpected_error_key
        mock_ctx.error.assert_called_once()


class TestRunQuerySuccess:
    """Tests for successful query execution."""

    @patch('awslabs.mysql_mcp_server.server.db_connection_map')
    async def test_successful_query(self, mock_map, mock_ctx):
        """Should return parsed results on success."""
        mock_conn = MagicMock()
        mock_conn.readonly_query = False
        mock_conn.execute_query = AsyncMock(
            return_value={
                'columnMetadata': [{'name': 'id'}, {'name': 'name'}],
                'records': [
                    [{'longValue': 1}, {'stringValue': 'Alice'}],
                    [{'longValue': 2}, {'stringValue': 'Bob'}],
                ],
            }
        )
        mock_map.get.return_value = mock_conn

        result = await run_query(
            sql='SELECT id, name FROM users',
            ctx=mock_ctx,
            connection_method=ConnectionMethod.RDS_API,
            cluster_identifier='cluster-1',
            db_endpoint='ep',
            database='testdb',
        )

        assert len(result) == 2
        assert result[0]['id'] == 1
        assert result[0]['name'] == 'Alice'
        assert result[1]['id'] == 2
        assert result[1]['name'] == 'Bob'

    @patch('awslabs.mysql_mcp_server.server.db_connection_map')
    async def test_successful_query_with_parameters(self, mock_map, mock_ctx):
        """Should pass parameters to execute_query."""
        mock_conn = MagicMock()
        mock_conn.readonly_query = False
        mock_conn.execute_query = AsyncMock(
            return_value={'columnMetadata': [{'name': 'id'}], 'records': [[{'longValue': 42}]]}
        )
        mock_map.get.return_value = mock_conn

        params = [{'name': 'id', 'value': {'longValue': 42}}]
        result = await run_query(
            sql='SELECT * FROM users WHERE id = :id',
            ctx=mock_ctx,
            connection_method=ConnectionMethod.RDS_API,
            cluster_identifier='cluster-1',
            db_endpoint='ep',
            database='testdb',
            query_parameters=params,
        )

        mock_conn.execute_query.assert_called_once_with(
            'SELECT * FROM users WHERE id = :id', params
        )
        assert result[0]['id'] == 42
