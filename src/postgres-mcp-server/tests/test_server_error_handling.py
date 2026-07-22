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
    ConnectionValidationError,
    DummyCtx,
    connect_to_database,
    main,
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

        with (
            patch('awslabs.postgres_mcp_server.server.internal_create_connection') as mock_connect,
            patch('awslabs.postgres_mcp_server.server.validate_connection', new=AsyncMock()),
        ):
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

        with (
            patch('awslabs.postgres_mcp_server.server.internal_create_connection') as mock_connect,
            patch('awslabs.postgres_mcp_server.server.validate_connection', new=AsyncMock()),
        ):
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

    @pytest.mark.asyncio
    async def test_connect_to_database_rejects_superuser_and_removes_connection(self):
        """A superuser connection is rejected (enforce) and removed from the map.

        Wiring test for the least-privilege guardrail: connect_to_database must
        run validate_connection, surface the rejection as a Failed response, and
        remove the connection so it is not left cached.
        """
        # Non-pool connection so initialize_pool is skipped; execute_query
        # reports a superuser role, which validate_connection rejects under the
        # default 'enforce' policy.
        mock_connection = MagicMock()
        mock_connection.execute_query = AsyncMock(
            return_value={
                'columnMetadata': [
                    {'name': 'is_superuser'},
                    {'name': 'is_rds_superuser'},
                ],
                'records': [[{'booleanValue': True}, {'booleanValue': False}]],
            }
        )
        mock_response = json.dumps(
            {
                'connection_method': 'rdsapi',
                'cluster_identifier': 'test-cluster',
                'db_endpoint': 'test.endpoint.com',
                'database': 'testdb',
                'port': 5432,
            }
        )

        with (
            patch('awslabs.postgres_mcp_server.server.internal_create_connection') as mock_connect,
            patch('awslabs.postgres_mcp_server.server.db_connection_map') as mock_map,
            patch(
                'awslabs.postgres_mcp_server.server.privilege_check_policy',
                'enforce',
            ),
        ):
            mock_connect.return_value = (mock_connection, mock_response)

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
            assert 'over-privileged' in result_dict['error']
            # The rejected connection must be evicted by object identity (not
            # by a key rebuilt from the caller-supplied args, which can diverge
            # from the resolved key the connection was stored under). See
            # test_rejected_superuser_evicted_despite_key_mismatch for the
            # behavioral (real-map) proof.
            mock_map.remove_connection.assert_called_once_with(mock_connection)

    @pytest.mark.asyncio
    async def test_rejected_superuser_evicted_despite_key_mismatch(self):
        """Behavioral guardrail-bypass regression, exercised against a REAL map.

        internal_create_connection stores the connection under the AWS-resolved
        endpoint/port, which can differ from the caller-supplied db_endpoint/port
        (e.g. an empty db_endpoint that the resolver fills in, or a non-5432
        port). If eviction rebuilt the map key from the caller args, the rejected
        superuser connection would survive under its resolved key and stay
        reachable via run_query — defeating the 'enforce' guardrail. This test
        deliberately stores the connection under a resolved key that does NOT
        match the caller args, then asserts it is gone after rejection.
        """
        from awslabs.postgres_mcp_server.server import db_connection_map

        method = ConnectionMethod.RDS_API
        cluster = 'test-cluster-evict'
        caller_endpoint = ''  # caller passes empty; the resolver would fill this in
        resolved_endpoint = 'writer.resolved.example.com'
        database = 'testdb'

        # execute_query reports a superuser role -> rejected under 'enforce'.
        mock_connection = MagicMock()
        mock_connection.execute_query = AsyncMock(
            return_value={
                'columnMetadata': [{'name': 'is_superuser'}, {'name': 'is_rds_superuser'}],
                'records': [[{'booleanValue': True}, {'booleanValue': False}]],
            }
        )
        mock_response = json.dumps(
            {
                'connection_method': 'rdsapi',
                'cluster_identifier': cluster,
                'db_endpoint': resolved_endpoint,
                'database': database,
                'port': 5432,
            }
        )

        def fake_create(**kwargs):
            # Mimic internal_create_connection: store under the RESOLVED key,
            # which differs from the caller-supplied (empty) endpoint.
            db_connection_map.set(method, cluster, resolved_endpoint, database, mock_connection)
            return (mock_connection, mock_response)

        # Ensure a clean slate in the shared real map.
        db_connection_map.remove_connection(mock_connection)

        try:
            with (
                patch(
                    'awslabs.postgres_mcp_server.server.internal_create_connection',
                    side_effect=fake_create,
                ),
                patch('awslabs.postgres_mcp_server.server.privilege_check_policy', 'enforce'),
            ):
                result = await connect_to_database(
                    region='us-east-1',
                    database_type=DatabaseType.APG,
                    connection_method=method,
                    cluster_identifier=cluster,
                    db_endpoint=caller_endpoint,
                    port=5432,
                    database=database,
                )

            result_dict = json.loads(result)
            assert result_dict['status'] == 'Failed'
            assert 'over-privileged' in result_dict['error']
            # The connection must be gone despite the caller/resolved key
            # mismatch. A key-based remove() rebuilt from caller_endpoint=''
            # would have missed the entry stored under resolved_endpoint.
            assert db_connection_map.get(method, cluster, resolved_endpoint, database) is None
        finally:
            # Defensive cleanup in case the assertion above failed.
            db_connection_map.remove_connection(mock_connection)


class TestDummyCtx:
    """Tests for DummyCtx class."""

    @pytest.mark.asyncio
    async def test_dummy_ctx_error_does_nothing(self):
        """Test that DummyCtx.error() completes without raising."""
        ctx = DummyCtx()
        # Should not raise any exception
        await ctx.error('Test error message')
        # If we get here, test passes


class TestMainStartupValidation:
    """Startup-path wiring for the least-privilege guardrail in main().

    Drives server.main() with mocked argv and a mocked internal_create_connection
    so the startup connection-validation block runs without touching AWS. Covers
    all three branches: validation passes (server proceeds to mcp.run), a
    least-privilege violation (ConnectionValidationError -> exit 1), and an
    unexpected validation error (generic Exception -> exit 1).
    """

    def _argv(self):
        """CLI args sufficient to reach the startup db-connection validation block."""
        return [
            'server.py',
            '--region',
            'us-east-1',
            '--db_type',
            'APG',
            '--connection_method',
            'RDS_API',
            '--db_cluster_arn',
            'arn:aws:rds:us-east-1:123456789012:cluster:test-cluster',
            '--db_endpoint',
            'test.endpoint.com',
            '--database',
            'testdb',
        ]

    def test_main_starts_when_validation_passes(self):
        """A clean validation lets startup proceed to mcp.run()."""
        mock_conn = MagicMock()
        with (
            patch('sys.argv', self._argv()),
            patch(
                'awslabs.postgres_mcp_server.server.internal_create_connection',
                return_value=(mock_conn, '{}'),
            ),
            patch(
                'awslabs.postgres_mcp_server.server.validate_connection', new=AsyncMock()
            ) as mock_validate,
            patch('awslabs.postgres_mcp_server.server.mcp.run') as mock_run,
        ):
            main()

        mock_validate.assert_awaited_once()
        mock_run.assert_called_once()

    def test_main_exits_on_privilege_violation(self):
        """A ConnectionValidationError (over-privileged role) aborts startup with exit 1."""
        mock_conn = MagicMock()
        with (
            patch('sys.argv', self._argv()),
            patch(
                'awslabs.postgres_mcp_server.server.internal_create_connection',
                return_value=(mock_conn, '{}'),
            ),
            patch(
                'awslabs.postgres_mcp_server.server.validate_connection',
                new=AsyncMock(side_effect=ConnectionValidationError('over-privileged role')),
            ),
            patch('awslabs.postgres_mcp_server.server.mcp.run') as mock_run,
        ):
            with pytest.raises(SystemExit) as exc:
                main()

        assert exc.value.code == 1
        # Startup must abort before the server is run.
        mock_run.assert_not_called()

    def test_main_exits_on_unexpected_validation_error(self):
        """A non-ConnectionValidationError during validation also aborts startup with exit 1."""
        mock_conn = MagicMock()
        with (
            patch('sys.argv', self._argv()),
            patch(
                'awslabs.postgres_mcp_server.server.internal_create_connection',
                return_value=(mock_conn, '{}'),
            ),
            patch(
                'awslabs.postgres_mcp_server.server.validate_connection',
                new=AsyncMock(side_effect=RuntimeError('connection reset')),
            ),
            patch('awslabs.postgres_mcp_server.server.mcp.run') as mock_run,
        ):
            with pytest.raises(SystemExit) as exc:
                main()

        assert exc.value.code == 1
        mock_run.assert_not_called()
