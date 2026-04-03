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
"""Tests for server error handling and edge cases."""

import json
import pytest
from awslabs.postgres_mcp_server.connection.db_connection_map import ConnectionMethod, DatabaseType
from awslabs.postgres_mcp_server.server import (
    DummyCtx,
    connect_to_database,
    run_query,
)
from unittest.mock import AsyncMock, MagicMock, patch


class TestRunQueryErrorHandling:
    """Tests for run_query error handling."""

    @pytest.mark.asyncio
    async def test_run_query_no_connection_available(self):
        """Test run_query when no database connection is available."""
        ctx = DummyCtx()

        with patch('awslabs.postgres_mcp_server.server.db_connection_map') as mock_map:
            mock_map.get.return_value = None

            result = await run_query(
                sql='SELECT 1',
                ctx=ctx,
                connection_method=ConnectionMethod.RDS_API,
                cluster_identifier='test-cluster',
                db_endpoint='test.endpoint.com',
                database='testdb',
            )

            assert isinstance(result, list)
            assert len(result) == 1
            assert 'error' in result[0]
            assert 'No database connection available' in str(result[0]['error'])

    @pytest.mark.asyncio
    async def test_run_query_with_query_parameters(self):
        """Test run_query with query parameters."""
        ctx = DummyCtx()
        mock_connection = AsyncMock()
        mock_connection.readonly_query = False
        mock_connection.execute_query.return_value = {
            'columnMetadata': [{'name': 'result'}],
            'records': [[{'longValue': 42}]],
        }

        with patch('awslabs.postgres_mcp_server.server.db_connection_map') as mock_map:
            mock_map.get.return_value = mock_connection

            parameters = [{'name': 'id', 'value': {'longValue': 1}}]
            result = await run_query(
                sql='SELECT * FROM users WHERE id = :id',
                ctx=ctx,
                connection_method=ConnectionMethod.RDS_API,
                cluster_identifier='test-cluster',
                db_endpoint='test.endpoint.com',
                database='testdb',
                query_parameters=parameters,
            )

            assert len(result) == 1
            assert result[0]['result'] == 42
            mock_connection.execute_query.assert_called_once_with(
                'SELECT * FROM users WHERE id = :id', parameters
            )


class TestConnectToDatabaseErrorHandling:
    """Tests for connect_to_database error handling."""

    @pytest.mark.asyncio
    async def test_connect_to_database_exception_handling(self):
        """Test connect_to_database handles exceptions properly."""
        with patch(
            'awslabs.postgres_mcp_server.server.internal_create_connection'
        ) as mock_connect:
            mock_connect.side_effect = ValueError('Connection failed')

            result = await connect_to_database(
                region='us-east-1',
                database_type=DatabaseType.APG,
                connection_method=ConnectionMethod.RDS_API,
                cluster_identifier='test-cluster',
                db_endpoint='test.endpoint.com',
                port=5432,
                database='testdb',
            )

            result_dict = json.loads(result)
            assert result_dict['status'] == 'Failed'
            assert 'Connection failed' in result_dict['error']

    @pytest.mark.asyncio
    async def test_connect_to_database_success(self):
        """Test connect_to_database success path."""
        mock_connection = MagicMock()
        mock_response = {
            'connection_method': 'rdsapi',
            'cluster_identifier': 'test-cluster',
            'db_endpoint': 'test.endpoint.com',
            'database': 'testdb',
            'port': 5432,
        }

        with patch(
            'awslabs.postgres_mcp_server.server.internal_create_connection'
        ) as mock_connect:
            mock_connect.return_value = (mock_connection, json.dumps(mock_response))

            result = await connect_to_database(
                region='us-east-1',
                database_type=DatabaseType.APG,
                connection_method=ConnectionMethod.RDS_API,
                cluster_identifier='test-cluster',
                db_endpoint='test.endpoint.com',
                port=5432,
                database='testdb',
            )

            assert 'test-cluster' in result
            assert 'rdsapi' in result

    @pytest.mark.asyncio
    async def test_connect_to_database_initializes_pool_for_psycopg(self):
        """Test connect_to_database eagerly initializes pool for PsycopgPoolConnection."""
        from awslabs.postgres_mcp_server.connection.psycopg_pool_connection import (
            PsycopgPoolConnection,
        )

        mock_pool_conn = MagicMock(spec=PsycopgPoolConnection)
        mock_pool_conn.initialize_pool = AsyncMock()
        mock_response = json.dumps(
            {
                'connection_method': 'pgwire_iam',
                'cluster_identifier': 'test-cluster',
                'db_endpoint': 'test.endpoint.com',
                'database': 'testdb',
                'port': 5432,
            }
        )

        with patch(
            'awslabs.postgres_mcp_server.server.internal_create_connection'
        ) as mock_connect:
            mock_connect.return_value = (mock_pool_conn, mock_response)

            result = await connect_to_database(
                region='us-east-1',
                database_type=DatabaseType.APG,
                connection_method=ConnectionMethod.PG_WIRE_IAM_PROTOCOL,
                cluster_identifier='test-cluster',
                db_endpoint='test.endpoint.com',
                port=5432,
                database='testdb',
            )

            mock_pool_conn.initialize_pool.assert_awaited_once()
            assert 'test-cluster' in result

    @pytest.mark.asyncio
    async def test_connect_to_database_pool_init_failure(self):
        """Test connect_to_database returns error and removes connection from map when pool init fails."""
        from awslabs.postgres_mcp_server.connection.psycopg_pool_connection import (
            PsycopgPoolConnection,
        )
        from awslabs.postgres_mcp_server.server import db_connection_map

        mock_pool_conn = MagicMock(spec=PsycopgPoolConnection)
        mock_pool_conn.initialize_pool = AsyncMock(
            side_effect=Exception('pool initialization incomplete after 30 sec')
        )
        mock_response = json.dumps(
            {
                'connection_method': 'pgwire_iam',
                'cluster_identifier': 'test-cluster',
                'db_endpoint': 'test.endpoint.com',
                'database': 'testdb',
                'port': 5432,
            }
        )

        with patch(
            'awslabs.postgres_mcp_server.server.internal_create_connection'
        ) as mock_connect:
            mock_connect.return_value = (mock_pool_conn, mock_response)

            result = await connect_to_database(
                region='us-east-1',
                database_type=DatabaseType.APG,
                connection_method=ConnectionMethod.PG_WIRE_IAM_PROTOCOL,
                cluster_identifier='test-cluster',
                db_endpoint='test.endpoint.com',
                port=5432,
                database='testdb',
            )

            result_dict = json.loads(result)
            assert result_dict['status'] == 'Failed'
            assert 'pool initialization incomplete' in result_dict['error']

            # Verify the broken connection was removed from the map
            conn = db_connection_map.get(
                ConnectionMethod.PG_WIRE_IAM_PROTOCOL,
                'test-cluster',
                'test.endpoint.com',
                'testdb',
                5432,
            )
            assert conn is None


class TestDummyCtx:
    """Tests for DummyCtx class."""

    @pytest.mark.asyncio
    async def test_dummy_ctx_error_does_nothing(self):
        """Test that DummyCtx.error() completes without raising."""
        ctx = DummyCtx()
        # Should not raise any exception
        await ctx.error('Test error message')
        # If we get here, test passes
