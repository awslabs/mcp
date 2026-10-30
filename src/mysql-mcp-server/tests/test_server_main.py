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

"""Tests for the server.main() CLI entry point.

These tests exercise the argv-parsing + connect + validate dance that
runs at process start. Everything below internal_connect_to_database is
mocked so the tests don't reach boto3 or asyncmy.
"""

import json
import pytest
import sys
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.fixture
def base_argv():
    """Argv list for a typical Aurora MySQL launch via Data API."""
    return [
        'awslabs.mysql-mcp-server',
        '--connection_method',
        'RDS_API',
        '--db_cluster_arn',
        'arn:aws:rds:us-east-1:123456789012:cluster:my-cluster',
        '--db_type',
        'aurora-mysql',
        '--db_endpoint',
        'my-cluster.cluster-xyz.us-east-1.rds.amazonaws.com',
        '--region',
        'us-east-1',
        '--database',
        'app',
        '--port',
        '3306',
    ]


class TestMainArgvParsing:
    """Argument parsing and globals propagation."""

    @patch('awslabs.mysql_mcp_server.server.mcp.run_stdio_async', new_callable=AsyncMock)
    @patch('awslabs.mysql_mcp_server.server.db_connection_map')
    @patch('awslabs.mysql_mcp_server.server.run_query', new_callable=AsyncMock)
    @patch('awslabs.mysql_mcp_server.server.internal_connect_to_database')
    def test_parses_valid_aurora_mysql_args(
        self, mock_connect, mock_run_query, mock_map, mock_mcp_run, base_argv
    ):
        """Valid argv should reach internal_connect_to_database with the parsed values."""
        from awslabs.mysql_mcp_server import server

        mock_conn = MagicMock()
        mock_connect.return_value = (mock_conn, json.dumps({'connection_method': 'rdsapi'}))
        mock_run_query.return_value = [{'columnMetadata': [], 'records': []}]

        with patch.object(sys, 'argv', base_argv):
            server.main()

        # internal_connect_to_database is called with the cluster_identifier
        # parsed off the ARN's last colon segment.
        kwargs = mock_connect.call_args.kwargs
        assert kwargs['region'] == 'us-east-1'
        assert kwargs['cluster_identifier'] == 'my-cluster'
        assert kwargs['database'] == 'app'
        assert kwargs['port'] == 3306
        mock_mcp_run.assert_called_once()
        mock_map.close_all_sync.assert_called_once()

    @patch('awslabs.mysql_mcp_server.server.mcp.run_stdio_async', new_callable=AsyncMock)
    @patch('awslabs.mysql_mcp_server.server.db_connection_map')
    def test_invalid_db_type_exits_nonzero(self, mock_map, mock_mcp_run, base_argv):
        """Unknown --db_type values must exit(1) with a clear log line."""
        from awslabs.mysql_mcp_server import server

        argv = list(base_argv)
        argv[argv.index('--db_type') + 1] = 'postgres'

        with patch.object(sys, 'argv', argv), pytest.raises(SystemExit) as exc:
            server.main()
        assert exc.value.code == 1
        # mcp.run() must NOT be invoked when arg validation fails.
        mock_mcp_run.assert_not_called()
        # close_all_sync still runs in the finally block, by design.
        mock_map.close_all_sync.assert_called_once()

    @patch('awslabs.mysql_mcp_server.server.mcp.run_stdio_async', new_callable=AsyncMock)
    @patch('awslabs.mysql_mcp_server.server.db_connection_map')
    @patch('awslabs.mysql_mcp_server.server.run_query', new_callable=AsyncMock)
    @patch('awslabs.mysql_mcp_server.server.internal_connect_to_database')
    def test_validation_query_failure_exits_nonzero(
        self, mock_connect, mock_run_query, mock_map, mock_mcp_run, base_argv
    ):
        """If the SELECT 1 validation returns an error dict, main() exits(1)."""
        from awslabs.mysql_mcp_server import server

        mock_connect.return_value = (MagicMock(), json.dumps({}))
        mock_run_query.return_value = [{'error': 'Connection refused by server'}]

        with patch.object(sys, 'argv', base_argv), pytest.raises(SystemExit) as exc:
            server.main()
        assert exc.value.code == 1
        mock_mcp_run.assert_not_called()

    @patch('awslabs.mysql_mcp_server.server.mcp.run_stdio_async', new_callable=AsyncMock)
    @patch('awslabs.mysql_mcp_server.server.db_connection_map')
    def test_no_db_type_skips_validation_and_runs_mcp(self, mock_map, mock_mcp_run):
        """Without --db_type, main() skips the connect/validate path and just runs the MCP server."""
        from awslabs.mysql_mcp_server import server

        # Only --connection_method (which is allowed to be None too); no db_type.
        argv = ['awslabs.mysql-mcp-server']
        with patch.object(sys, 'argv', argv):
            server.main()

        mock_mcp_run.assert_called_once()
        mock_map.close_all_sync.assert_called_once()

    @patch('awslabs.mysql_mcp_server.server.mcp.run_stdio_async', new_callable=AsyncMock)
    @patch('awslabs.mysql_mcp_server.server.db_connection_map')
    @patch('awslabs.mysql_mcp_server.server.run_query', new_callable=AsyncMock)
    @patch('awslabs.mysql_mcp_server.server.internal_connect_to_database')
    def test_allow_write_query_flag_disables_readonly(
        self, mock_connect, mock_run_query, mock_map, mock_mcp_run, base_argv
    ):
        """--allow_write_query should set the global readonly_query to False."""
        from awslabs.mysql_mcp_server import server

        mock_connect.return_value = (MagicMock(), json.dumps({}))
        mock_run_query.return_value = [{'columnMetadata': [], 'records': []}]
        argv = list(base_argv) + ['--allow_write_query']

        with patch.object(sys, 'argv', argv):
            server.main()

        assert server.readonly_query is False

    @patch('awslabs.mysql_mcp_server.server.mcp.run_stdio_async', new_callable=AsyncMock)
    @patch('awslabs.mysql_mcp_server.server.db_connection_map')
    @patch('awslabs.mysql_mcp_server.server.run_query', new_callable=AsyncMock)
    @patch('awslabs.mysql_mcp_server.server.internal_connect_to_database')
    def test_ca_bundle_flag_propagates_to_global(
        self, mock_connect, mock_run_query, mock_map, mock_mcp_run, base_argv
    ):
        """--ca_bundle should propagate to the module-level ca_bundle_path."""
        from awslabs.mysql_mcp_server import server

        mock_connect.return_value = (MagicMock(), json.dumps({}))
        mock_run_query.return_value = [{'columnMetadata': [], 'records': []}]
        argv = list(base_argv) + ['--ca_bundle', '/etc/ssl/myca.pem']

        with patch.object(sys, 'argv', argv):
            server.main()

        assert server.ca_bundle_path == '/etc/ssl/myca.pem'

    @patch('awslabs.mysql_mcp_server.server.mcp.run_stdio_async', new_callable=AsyncMock)
    @patch('awslabs.mysql_mcp_server.server.db_connection_map')
    @patch('awslabs.mysql_mcp_server.server.run_query', new_callable=AsyncMock)
    @patch('awslabs.mysql_mcp_server.server.internal_connect_to_database')
    def test_close_all_sync_runs_even_when_mcp_run_raises(
        self, mock_connect, mock_run_query, mock_map, mock_mcp_run, base_argv
    ):
        """The finally: close_all_sync() must run even when mcp.run() blows up."""
        from awslabs.mysql_mcp_server import server

        mock_connect.return_value = (MagicMock(), json.dumps({}))
        mock_run_query.return_value = [{'columnMetadata': [], 'records': []}]
        mock_mcp_run.side_effect = KeyboardInterrupt('user pressed ctrl-c')

        with patch.object(sys, 'argv', base_argv), pytest.raises(KeyboardInterrupt):
            server.main()

        mock_map.close_all_sync.assert_called_once()


class TestStartupValidationEventLoop:
    """The startup SELECT 1 must run on the event loop that later serves MCP requests."""

    @patch('awslabs.mysql_mcp_server.connection.asyncmy_pool_connection.asyncmy.create_pool')
    @patch('awslabs.mysql_mcp_server.server.internal_connect_to_database')
    def test_first_query_after_startup_validation_succeeds(
        self, mock_connect, mock_create_pool, base_argv
    ):
        """Regression for #4620: the first query after startup validation must not fail.

        With a wire-protocol connection, main() validates the connection with
        SELECT 1, which binds the AsyncmyPoolConnection's aiorwlock.RWLock (and
        creates the asyncmy pool) on the running event loop. If validation runs
        on a throwaway loop, the first real query on the serving loop fails with
        "RWLock ... is bound to a different event loop".
        """
        import asyncio
        from awslabs.mysql_mcp_server import server
        from awslabs.mysql_mcp_server.connection.asyncmy_pool_connection import (
            AsyncmyPoolConnection,
        )
        from awslabs.mysql_mcp_server.connection.db_connection_map import ConnectionMethod

        argv = list(base_argv)
        argv[argv.index('--connection_method') + 1] = 'MYSQL_WIRE_PROTOCOL'
        cluster_identifier = 'my-cluster'
        endpoint = argv[argv.index('--db_endpoint') + 1]

        def make_pool(**kwargs):
            # Like a real asyncmy pool, connections only work on the loop that created it.
            pool_loop = asyncio.get_running_loop()
            cursor = MagicMock()
            cursor.execute = AsyncMock()
            cursor.description = [('1',)]
            cursor.fetchall = AsyncMock(return_value=[{'1': 1}])
            cursor.__aenter__ = AsyncMock(return_value=cursor)
            cursor.__aexit__ = AsyncMock(return_value=False)
            conn = MagicMock()
            conn.cursor = MagicMock(return_value=cursor)
            conn.autocommit = AsyncMock()
            conn.rollback = AsyncMock()

            async def enter(*args):
                assert asyncio.get_running_loop() is pool_loop, (
                    'asyncmy pool used on a different event loop than it was created on'
                )
                return conn

            acquire_cm = MagicMock()
            acquire_cm.__aenter__ = enter
            acquire_cm.__aexit__ = AsyncMock(return_value=False)
            pool = MagicMock()
            pool.acquire = MagicMock(return_value=acquire_cm)
            pool.wait_closed = AsyncMock()
            return pool

        mock_create_pool.side_effect = AsyncMock(side_effect=make_pool)

        def connect(**kwargs):
            db_connection = AsyncmyPoolConnection(
                host=endpoint,
                port=3306,
                database='app',
                readonly=True,
                secret_arn='arn:aws:secretsmanager:us-east-1:123456789012:secret:test',  # pragma: allowlist secret
                db_user='',
                region='us-east-1',
                is_iam_auth=False,
                is_test=True,
            )
            server.db_connection_map.set(
                ConnectionMethod.MYSQL_WIRE_PROTOCOL,
                cluster_identifier,
                endpoint,
                'app',
                db_connection,
            )
            return db_connection, json.dumps({})

        mock_connect.side_effect = connect
        served = []

        async def serve_one_query():
            # Stands in for the stdio server handling the client's first run_query call.
            db_connection = server.db_connection_map.get(
                method=ConnectionMethod.MYSQL_WIRE_PROTOCOL,
                cluster_identifier=cluster_identifier,
                db_endpoint=endpoint,
                database='app',
            )
            assert db_connection is not None
            served.append(await db_connection.execute_query('SELECT 1'))

        with (
            patch.object(sys, 'argv', argv),
            patch('awslabs.mysql_mcp_server.server.mcp.run_stdio_async', serve_one_query),
        ):
            server.main()

        assert served == [{'columnMetadata': [{'name': '1'}], 'records': [[{'longValue': 1}]]}]
