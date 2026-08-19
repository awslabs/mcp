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
    async_job_status,
    connect_to_database,
    create_cluster,
    create_cluster_worker,
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
        # Eviction now also closes the failed connection to avoid leaking a pool.
        mock_pool_conn.close = AsyncMock()
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
            # And it was closed so the partially-opened pool isn't leaked.
            mock_pool_conn.close.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_connect_to_database_rejects_superuser_and_removes_connection(self):
        """A superuser connection is rejected (enforce) and removed from the map.

        Wiring test for the least-privilege guardrail: connect_to_database must
        run validate_connection, surface the rejection as a Failed response, and
        remove the connection so it is not left cached.
        """
        # Non-pool connection so initialize_pool is skipped; execute_query
        # reports a superuser role, which validate_connection rejects under the
        # 'enforce' policy (patched below, since the default is now 'warn').
        mock_connection = MagicMock()
        mock_connection.execute_query = AsyncMock(
            return_value={
                'columnMetadata': [
                    {'name': 'is_superuser'},
                    {'name': 'is_bypassrls'},
                    {'name': 'is_rds_superuser'},
                ],
                'records': [
                    [
                        {'booleanValue': True},
                        {'booleanValue': False},
                        {'booleanValue': False},
                    ]
                ],
            }
        )
        mock_connection.close = AsyncMock()
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
            # Not a cache hit — empty snapshot forces the fresh path so
            # validation actually runs (was_cached is decided by object identity
            # against the pre-call snapshot).
            mock_map.list_connections.return_value = []

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
            # And the rejected connection is closed, not just unmapped.
            mock_connection.close.assert_awaited_once()

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
                'columnMetadata': [
                    {'name': 'is_superuser'},
                    {'name': 'is_bypassrls'},
                    {'name': 'is_rds_superuser'},
                ],
                'records': [
                    [
                        {'booleanValue': True},
                        {'booleanValue': False},
                        {'booleanValue': False},
                    ]
                ],
            }
        )
        mock_connection.close = AsyncMock()
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
            # And it was closed, not just unmapped.
            mock_connection.close.assert_awaited_once()
        finally:
            # Defensive cleanup in case the assertion above failed.
            db_connection_map.remove_connection(mock_connection)

    @pytest.mark.asyncio
    async def test_rejection_close_failure_is_swallowed(self):
        """If close() raises during cleanup, the rejection is still surfaced.

        Closing a rejected connection is best-effort: a failure there must not
        mask the original rejection or leave the connection reachable.
        """
        mock_connection = MagicMock()
        mock_connection.execute_query = AsyncMock(
            return_value={
                'columnMetadata': [
                    {'name': 'is_superuser'},
                    {'name': 'is_bypassrls'},
                    {'name': 'is_rds_superuser'},
                ],
                'records': [
                    [
                        {'booleanValue': True},
                        {'booleanValue': False},
                        {'booleanValue': False},
                    ]
                ],
            }
        )
        mock_connection.close = AsyncMock(side_effect=RuntimeError('close failed'))
        mock_response = json.dumps({'cluster_identifier': 'test-cluster'})

        with (
            patch('awslabs.postgres_mcp_server.server.internal_create_connection') as mock_connect,
            patch('awslabs.postgres_mcp_server.server.db_connection_map') as mock_map,
            patch('awslabs.postgres_mcp_server.server.privilege_check_policy', 'enforce'),
        ):
            mock_connect.return_value = (mock_connection, mock_response)
            mock_map.list_connections.return_value = []  # fresh path (identity snapshot)

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
        # Eviction and the (failing) close were both attempted.
        mock_map.remove_connection.assert_called_once_with(mock_connection)
        mock_connection.close.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_cached_connection_not_revalidated_or_evicted(self):
        """A cache hit must skip re-validation (and eviction).

        Re-probing a cached connection on every connect is redundant and, worse,
        a transient probe failure would tear a healthy, in-use shared connection
        out of the map. connect_to_database detects the cache hit by object
        identity (the returned connection is already in the pre-call snapshot)
        and returns it without re-running the privilege probe — so a probe that
        WOULD fail is never even called.
        """
        from awslabs.postgres_mcp_server.server import db_connection_map

        method = ConnectionMethod.RDS_API
        cluster = 'test-cluster-cached'
        endpoint = 'writer.cached.example.com'
        database = 'testdb'

        cached_conn = MagicMock()
        # If validation were (wrongly) run on the cached connection, this probe
        # would raise and the except path would evict + close it.
        cached_conn.execute_query = AsyncMock(side_effect=RuntimeError('transient throttle'))
        cached_conn.close = AsyncMock()

        # Seed the map so internal_create_connection returns this via its dedup
        # early-return; connect_to_database's pre-call snapshot then contains it,
        # so the identity check reports a cache hit.
        db_connection_map.remove_connection(cached_conn)
        db_connection_map.set(method, cluster, endpoint, database, cached_conn)

        def fake_create(**kwargs):
            return (cached_conn, '{"cluster_identifier": "test-cluster-cached"}')

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
                    db_endpoint=endpoint,
                    port=5432,
                    database=database,
                )

            # Not a failure, the probe never ran, close never called, and the
            # connection is still cached.
            assert '"status": "Failed"' not in result
            cached_conn.execute_query.assert_not_awaited()
            cached_conn.close.assert_not_awaited()
            assert db_connection_map.get(method, cluster, endpoint, database) is cached_conn
        finally:
            db_connection_map.remove_connection(cached_conn)

    @pytest.mark.asyncio
    async def test_cache_hit_detected_by_identity_despite_key_mismatch(self):
        """A returned pre-existing connection is treated as cached by identity.

        Regression for the was_cached key-divergence: the connection is stored
        under the AWS-resolved endpoint while the caller passes an empty
        endpoint, so a key-based was_cached lookup would report "not cached" and
        wrongly re-validate an already-validated, in-use connection. Detection is
        by object identity against the pre-call snapshot, so when
        internal_create_connection returns the pre-existing connection it is
        recognized as a cache hit regardless of the key mismatch — the probe
        never runs.
        """
        from awslabs.postgres_mcp_server.server import db_connection_map

        method = ConnectionMethod.RDS_API
        cluster = 'test-cluster-identity'
        caller_endpoint = ''  # caller passes empty; stored under the resolved one
        resolved_endpoint = 'writer.identity.example.com'
        database = 'testdb'

        cached_conn = MagicMock()
        # Would raise (and, under enforce, trigger eviction+close) if probed.
        cached_conn.execute_query = AsyncMock(side_effect=RuntimeError('should not run'))
        cached_conn.close = AsyncMock()

        # Pre-seed under the RESOLVED key (differs from the caller's empty one).
        db_connection_map.remove_connection(cached_conn)
        db_connection_map.set(method, cluster, resolved_endpoint, database, cached_conn)

        def fake_create(**kwargs):
            # Simulate a dedup hit: return the pre-existing object without
            # re-storing it (as internal_create_connection's early-return does).
            return (cached_conn, '{"cluster_identifier": "test-cluster-identity"}')

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

            # Recognized as cached despite the key mismatch: no probe, no close,
            # connection retained.
            assert '"status": "Failed"' not in result
            cached_conn.execute_query.assert_not_awaited()
            cached_conn.close.assert_not_awaited()
            assert (
                db_connection_map.get(method, cluster, resolved_endpoint, database) is cached_conn
            )
        finally:
            db_connection_map.remove_connection(cached_conn)

    @pytest.mark.asyncio
    async def test_warn_allows_and_retains_over_privileged_connection(self):
        """Under warn, a fresh over-privileged connection is allowed and retained.

        'warn' relaxes only the privilege check, so connect_to_database must NOT
        evict or close a superuser / rds_superuser / BYPASSRLS connection — it
        logs a warning and leaves the connection cached and usable.
        """
        from awslabs.postgres_mcp_server.server import db_connection_map

        method = ConnectionMethod.RDS_API
        cluster = 'test-cluster-warn'
        caller_endpoint = ''
        resolved_endpoint = 'writer.warn.example.com'
        database = 'testdb'

        mock_connection = MagicMock()
        mock_connection.execute_query = AsyncMock(
            return_value={
                'columnMetadata': [
                    {'name': 'is_superuser'},
                    {'name': 'is_bypassrls'},
                    {'name': 'is_rds_superuser'},
                ],
                'records': [
                    [
                        {'booleanValue': True},
                        {'booleanValue': False},
                        {'booleanValue': False},
                    ]
                ],
            }
        )
        mock_connection.close = AsyncMock()

        def fake_create(**kwargs):
            db_connection_map.set(method, cluster, resolved_endpoint, database, mock_connection)
            return (mock_connection, '{"cluster_identifier": "test-cluster-warn"}')

        db_connection_map.remove_connection(mock_connection)
        try:
            with (
                patch(
                    'awslabs.postgres_mcp_server.server.internal_create_connection',
                    side_effect=fake_create,
                ),
                patch('awslabs.postgres_mcp_server.server.privilege_check_policy', 'warn'),
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

            # Allowed (not a failure); the probe ran; the connection is NOT
            # closed and remains cached.
            assert '"status": "Failed"' not in result
            mock_connection.execute_query.assert_awaited()
            mock_connection.close.assert_not_awaited()
            assert (
                db_connection_map.get(method, cluster, resolved_endpoint, database)
                is mock_connection
            )
            # Recorded as over-privileged for diagnostics.
            assert mock_connection.effective_is_over_privileged is True
        finally:
            db_connection_map.remove_connection(mock_connection)

    @pytest.mark.asyncio
    async def test_clean_role_validated_and_retained_under_enforce(self):
        """A fresh clean role passes the real guardrail under enforce and is retained."""
        from awslabs.postgres_mcp_server.server import db_connection_map

        method = ConnectionMethod.RDS_API
        cluster = 'test-cluster-clean'
        resolved_endpoint = 'writer.clean.example.com'
        database = 'testdb'

        mock_connection = MagicMock()
        mock_connection.execute_query = AsyncMock(
            return_value={
                'columnMetadata': [
                    {'name': 'is_superuser'},
                    {'name': 'is_bypassrls'},
                    {'name': 'is_rds_superuser'},
                ],
                'records': [
                    [
                        {'booleanValue': False},
                        {'booleanValue': False},
                        {'booleanValue': False},
                    ]
                ],
            }
        )
        mock_connection.close = AsyncMock()

        def fake_create(**kwargs):
            db_connection_map.set(method, cluster, resolved_endpoint, database, mock_connection)
            return (mock_connection, '{"cluster_identifier": "test-cluster-clean"}')

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
                    db_endpoint=resolved_endpoint,
                    port=5432,
                    database=database,
                )

            # Passed validation, kept in the map, not closed.
            assert '"status": "Failed"' not in result
            mock_connection.execute_query.assert_awaited()
            mock_connection.close.assert_not_awaited()
            assert (
                db_connection_map.get(method, cluster, resolved_endpoint, database)
                is mock_connection
            )
            assert mock_connection.effective_is_over_privileged is False
        finally:
            db_connection_map.remove_connection(mock_connection)

    @pytest.mark.asyncio
    async def test_warn_over_privileged_response_carries_advisory(self):
        """Under warn, the connect_to_database response includes an advisory.

        The server-side warning log is often invisible to the MCP host, so an
        over-privileged connection must also surface its posture in the tool
        response as a structured, parseable advisory (additive to the existing
        fields).
        """
        from awslabs.postgres_mcp_server.server import db_connection_map

        method = ConnectionMethod.RDS_API
        cluster = 'test-cluster-advisory'
        resolved_endpoint = 'writer.advisory.example.com'
        database = 'testdb'

        mock_connection = MagicMock()
        mock_connection.execute_query = AsyncMock(
            return_value={
                'columnMetadata': [
                    {'name': 'is_superuser'},
                    {'name': 'is_bypassrls'},
                    {'name': 'is_rds_superuser'},
                ],
                # rds_superuser member (the common RDS/Aurora master case).
                'records': [
                    [
                        {'booleanValue': False},
                        {'booleanValue': False},
                        {'booleanValue': True},
                    ]
                ],
            }
        )
        mock_connection.close = AsyncMock()

        def fake_create(**kwargs):
            db_connection_map.set(method, cluster, resolved_endpoint, database, mock_connection)
            return (mock_connection, '{"cluster_identifier": "test-cluster-advisory"}')

        db_connection_map.remove_connection(mock_connection)
        try:
            with (
                patch(
                    'awslabs.postgres_mcp_server.server.internal_create_connection',
                    side_effect=fake_create,
                ),
                patch('awslabs.postgres_mcp_server.server.privilege_check_policy', 'warn'),
            ):
                result = await connect_to_database(
                    region='us-east-1',
                    database_type=DatabaseType.APG,
                    connection_method=method,
                    cluster_identifier=cluster,
                    db_endpoint=resolved_endpoint,
                    port=5432,
                    database=database,
                )

            # Allowed, and the response is valid JSON carrying the advisory
            # alongside the original fields.
            assert '"status": "Failed"' not in result
            payload = json.loads(result)
            assert payload['cluster_identifier'] == 'test-cluster-advisory'
            assert 'advisories' in payload
            codes = [a['code'] for a in payload['advisories']]
            assert 'over_privileged_role' in codes
            advisory = next(
                a for a in payload['advisories'] if a['code'] == 'over_privileged_role'
            )
            assert advisory['severity'] == 'warning'
            assert 'least-privilege' in advisory['message']
        finally:
            db_connection_map.remove_connection(mock_connection)

    @pytest.mark.asyncio
    async def test_clean_role_response_has_no_advisory(self):
        """A clean (least-privilege) role produces no advisory in the response."""
        from awslabs.postgres_mcp_server.server import db_connection_map

        method = ConnectionMethod.RDS_API
        cluster = 'test-cluster-noadvisory'
        resolved_endpoint = 'writer.noadvisory.example.com'
        database = 'testdb'

        mock_connection = MagicMock()
        mock_connection.execute_query = AsyncMock(
            return_value={
                'columnMetadata': [
                    {'name': 'is_superuser'},
                    {'name': 'is_bypassrls'},
                    {'name': 'is_rds_superuser'},
                ],
                'records': [
                    [
                        {'booleanValue': False},
                        {'booleanValue': False},
                        {'booleanValue': False},
                    ]
                ],
            }
        )
        mock_connection.close = AsyncMock()

        def fake_create(**kwargs):
            db_connection_map.set(method, cluster, resolved_endpoint, database, mock_connection)
            return (mock_connection, '{"cluster_identifier": "test-cluster-noadvisory"}')

        db_connection_map.remove_connection(mock_connection)
        try:
            with (
                patch(
                    'awslabs.postgres_mcp_server.server.internal_create_connection',
                    side_effect=fake_create,
                ),
                patch('awslabs.postgres_mcp_server.server.privilege_check_policy', 'warn'),
            ):
                result = await connect_to_database(
                    region='us-east-1',
                    database_type=DatabaseType.APG,
                    connection_method=method,
                    cluster_identifier=cluster,
                    db_endpoint=resolved_endpoint,
                    port=5432,
                    database=database,
                )

            payload = json.loads(result)
            assert payload['cluster_identifier'] == 'test-cluster-noadvisory'
            assert 'advisories' not in payload
            assert mock_connection.effective_is_over_privileged is False
        finally:
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


class TestCreateClusterBootstrapExemption:
    """Guard the create_cluster bootstrap exemption from the guardrail.

    A cluster the MCP just created must be immediately usable: it only has the
    rds_superuser master and no least-privilege role yet, so create_cluster /
    create_cluster_worker cache that master connection WITHOUT running the
    least-privilege guardrail. These tests pin that behavior so a newly created
    cluster is never auto-rejected (enforce) or auto-warned (warn) — even under
    the strictest policy, validate_connection must not be invoked on the
    bootstrap connection.

    NOTE: this is the current/interim bootstrap behavior. It is expected to
    change with the tracked validate-on-create-with-exemption follow-up; update
    these tests when that lands.
    """

    def test_create_cluster_express_does_not_invoke_guardrail_under_enforce(self):
        """The express create_cluster bootstrap connection is cached unvalidated."""
        mock_conn = MagicMock()
        properties = {
            'MasterUsername': 'postgres',
            'DbClusterResourceId': 'cluster-BOOTSTRAP',
            'Endpoint': 'writer.bootstrap.example.com',
            'Port': 5432,
        }
        with (
            patch('awslabs.postgres_mcp_server.server.internal_create_express_cluster'),
            patch(
                'awslabs.postgres_mcp_server.server.internal_get_cluster_properties',
                return_value=properties,
            ),
            patch('awslabs.postgres_mcp_server.server.setup_aurora_iam_policy_for_current_user'),
            patch(
                'awslabs.postgres_mcp_server.server.internal_create_connection',
                return_value=(mock_conn, '{}'),
            ) as mock_icc,
            patch(
                'awslabs.postgres_mcp_server.server.validate_connection', new=AsyncMock()
            ) as mock_validate,
            # Strictest policy: even here the bootstrap connection must not be
            # validated/rejected.
            patch('awslabs.postgres_mcp_server.server.privilege_check_policy', 'enforce'),
        ):
            result = create_cluster(
                region='us-west-2',
                cluster_identifier='mcp-express-bootstrap',
                with_express_configuration=True,
            )

        result_dict = json.loads(result)
        assert result_dict['status'] == 'Completed'
        # The bootstrap connection was established ...
        mock_icc.assert_called_once()
        # ... but the guardrail was never run on it (no reject, no warn).
        mock_validate.assert_not_called()

    def test_create_cluster_worker_does_not_invoke_guardrail_under_enforce(self):
        """The serverless create_cluster_worker bootstrap connection is unvalidated."""
        job_id = 'job-bootstrap-guard'
        cluster_result = {
            'MasterUsername': 'postgres',
            'DbClusterResourceId': 'cluster-BOOTSTRAP',
            'Endpoint': 'writer.bootstrap.example.com',
        }
        mock_conn = MagicMock()
        # create_cluster_worker updates async_job_status[job_id] in place, so it
        # must be pre-registered (create_cluster does this before spawning it).
        async_job_status[job_id] = {'state': 'pending', 'result': None}
        try:
            with (
                patch(
                    'awslabs.postgres_mcp_server.server.internal_create_serverless_cluster',
                    return_value=cluster_result,
                ),
                patch(
                    'awslabs.postgres_mcp_server.server.setup_aurora_iam_policy_for_current_user'
                ),
                patch(
                    'awslabs.postgres_mcp_server.server.internal_create_connection',
                    return_value=(mock_conn, '{}'),
                ) as mock_icc,
                patch(
                    'awslabs.postgres_mcp_server.server.validate_connection', new=AsyncMock()
                ) as mock_validate,
                patch('awslabs.postgres_mcp_server.server.privilege_check_policy', 'enforce'),
            ):
                create_cluster_worker(
                    job_id=job_id,
                    region='us-west-2',
                    database_type=DatabaseType.APG,
                    connection_method=ConnectionMethod.RDS_API,
                    cluster_identifier='mcp-serverless-bootstrap',
                    engine_version='16.9',
                    database='postgres',
                )

            # Cluster creation succeeded and the bootstrap connection was cached,
            assert async_job_status[job_id]['state'] == 'succeeded'
            mock_icc.assert_called_once()
            # but the guardrail was never run on it (no reject, no warn).
            mock_validate.assert_not_called()
        finally:
            async_job_status.pop(job_id, None)
