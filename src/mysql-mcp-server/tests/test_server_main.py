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
from unittest.mock import MagicMock, patch


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

    @patch('awslabs.mysql_mcp_server.server.mcp.run')
    @patch('awslabs.mysql_mcp_server.server.db_connection_map')
    @patch('awslabs.mysql_mcp_server.server.asyncio.run')
    @patch('awslabs.mysql_mcp_server.server.internal_connect_to_database')
    def test_parses_valid_aurora_mysql_args(
        self, mock_connect, mock_asyncio_run, mock_map, mock_mcp_run, base_argv
    ):
        """Valid argv should reach internal_connect_to_database with the parsed values."""
        from awslabs.mysql_mcp_server import server

        mock_conn = MagicMock()
        mock_connect.return_value = (mock_conn, json.dumps({'connection_method': 'rdsapi'}))
        mock_asyncio_run.return_value = [{'columnMetadata': [], 'records': []}]

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

    @patch('awslabs.mysql_mcp_server.server.mcp.run')
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

    @patch('awslabs.mysql_mcp_server.server.mcp.run')
    @patch('awslabs.mysql_mcp_server.server.db_connection_map')
    @patch('awslabs.mysql_mcp_server.server.asyncio.run')
    @patch('awslabs.mysql_mcp_server.server.internal_connect_to_database')
    def test_validation_query_failure_exits_nonzero(
        self, mock_connect, mock_asyncio_run, mock_map, mock_mcp_run, base_argv
    ):
        """If the SELECT 1 validation returns an error dict, main() exits(1)."""
        from awslabs.mysql_mcp_server import server

        mock_connect.return_value = (MagicMock(), json.dumps({}))
        mock_asyncio_run.return_value = [{'error': 'Connection refused by server'}]

        with patch.object(sys, 'argv', base_argv), pytest.raises(SystemExit) as exc:
            server.main()
        assert exc.value.code == 1
        mock_mcp_run.assert_not_called()

    @patch('awslabs.mysql_mcp_server.server.mcp.run')
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

    @patch('awslabs.mysql_mcp_server.server.mcp.run')
    @patch('awslabs.mysql_mcp_server.server.db_connection_map')
    @patch('awslabs.mysql_mcp_server.server.asyncio.run')
    @patch('awslabs.mysql_mcp_server.server.internal_connect_to_database')
    def test_allow_write_query_flag_disables_readonly(
        self, mock_connect, mock_asyncio_run, mock_map, mock_mcp_run, base_argv
    ):
        """--allow_write_query should set the global readonly_query to False."""
        from awslabs.mysql_mcp_server import server

        mock_connect.return_value = (MagicMock(), json.dumps({}))
        mock_asyncio_run.return_value = [{'columnMetadata': [], 'records': []}]
        argv = list(base_argv) + ['--allow_write_query']

        with patch.object(sys, 'argv', argv):
            server.main()

        assert server.readonly_query is False

    @patch('awslabs.mysql_mcp_server.server.mcp.run')
    @patch('awslabs.mysql_mcp_server.server.db_connection_map')
    @patch('awslabs.mysql_mcp_server.server.asyncio.run')
    @patch('awslabs.mysql_mcp_server.server.internal_connect_to_database')
    def test_ca_bundle_flag_propagates_to_global(
        self, mock_connect, mock_asyncio_run, mock_map, mock_mcp_run, base_argv
    ):
        """--ca_bundle should propagate to the module-level ca_bundle_path."""
        from awslabs.mysql_mcp_server import server

        mock_connect.return_value = (MagicMock(), json.dumps({}))
        mock_asyncio_run.return_value = [{'columnMetadata': [], 'records': []}]
        argv = list(base_argv) + ['--ca_bundle', '/etc/ssl/myca.pem']

        with patch.object(sys, 'argv', argv):
            server.main()

        assert server.ca_bundle_path == '/etc/ssl/myca.pem'

    @patch('awslabs.mysql_mcp_server.server.mcp.run')
    @patch('awslabs.mysql_mcp_server.server.db_connection_map')
    @patch('awslabs.mysql_mcp_server.server.asyncio.run')
    @patch('awslabs.mysql_mcp_server.server.internal_connect_to_database')
    def test_close_all_sync_runs_even_when_mcp_run_raises(
        self, mock_connect, mock_asyncio_run, mock_map, mock_mcp_run, base_argv
    ):
        """The finally: close_all_sync() must run even when mcp.run() blows up."""
        from awslabs.mysql_mcp_server import server

        mock_connect.return_value = (MagicMock(), json.dumps({}))
        mock_asyncio_run.return_value = [{'columnMetadata': [], 'records': []}]
        mock_mcp_run.side_effect = KeyboardInterrupt('user pressed ctrl-c')

        with patch.object(sys, 'argv', base_argv), pytest.raises(KeyboardInterrupt):
            server.main()

        mock_map.close_all_sync.assert_called_once()
