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

"""Tests for server tool registration and mock connections."""

import json
from awslabs.mysql_mcp_server.connection.db_connection_map import (
    ConnectionMethod,
    DatabaseType,
)
from awslabs.mysql_mcp_server.server import (
    connect_to_database,
    create_cluster,
    get_database_connection_info,
    get_job_status,
    is_database_connected,
    mcp,
    run_query,
)
from unittest.mock import MagicMock, patch


class TestMCPToolRegistration:
    """Tests for MCP tool registration."""

    def test_mcp_server_exists(self):
        """MCP server should be created."""
        assert mcp is not None

    def test_run_query_is_registered(self):
        """run_query should be a registered tool."""
        assert callable(run_query)

    def test_connect_to_database_is_registered(self):
        """connect_to_database should be a registered tool."""
        assert callable(connect_to_database)

    def test_is_database_connected_is_registered(self):
        """is_database_connected should be a registered tool."""
        assert callable(is_database_connected)

    def test_get_database_connection_info_is_registered(self):
        """get_database_connection_info should be a registered tool."""
        assert callable(get_database_connection_info)

    def test_create_cluster_is_registered(self):
        """create_cluster should be a registered tool."""
        assert callable(create_cluster)

    def test_get_job_status_is_registered(self):
        """get_job_status should be a registered tool."""
        assert callable(get_job_status)


class TestIsDatabaseConnected:
    """Tests for is_database_connected."""

    @patch('awslabs.mysql_mcp_server.server.db_connection_map')
    def test_returns_true_when_cluster_has_connection(self, mock_map):
        """Should return True when any connection exists for the cluster."""
        mock_map.has_connection_for_cluster.return_value = True

        result = is_database_connected('cluster-1')
        assert result is True
        mock_map.has_connection_for_cluster.assert_called_once_with('cluster-1')

    @patch('awslabs.mysql_mcp_server.server.db_connection_map')
    def test_returns_false_when_no_connection_for_cluster(self, mock_map):
        """Should return False when the cluster has no cached connections."""
        mock_map.has_connection_for_cluster.return_value = False

        result = is_database_connected('cluster-1')
        assert result is False

    @patch('awslabs.mysql_mcp_server.server.db_connection_map')
    def test_scan_matches_any_endpoint_or_database(self, mock_map):
        """Lookup is by cluster_identifier only, not by endpoint/database/method.

        Regression test for the bug where is_database_connected required the
        caller to pass the exact db_endpoint and database used at connect
        time, which the agent usually does not know.
        """
        mock_map.has_connection_for_cluster.return_value = True

        # Only the cluster_identifier is passed — no endpoint or database.
        result = is_database_connected('cluster-1')
        assert result is True


class TestGetDatabaseConnectionInfo:
    """Tests for get_database_connection_info."""

    @patch('awslabs.mysql_mcp_server.server.db_connection_map')
    def test_returns_json(self, mock_map):
        """Should return JSON string from connection map."""
        mock_map.get_keys_json.return_value = '[]'
        result = get_database_connection_info()
        assert result == '[]'


class TestGetJobStatus:
    """Tests for get_job_status."""

    @patch('awslabs.mysql_mcp_server.server.async_job_status', {'job-1': {'state': 'succeeded'}})
    def test_existing_job(self):
        """Should return status for existing job."""
        result = get_job_status('job-1')
        assert result['state'] == 'succeeded'

    @patch('awslabs.mysql_mcp_server.server.async_job_status', {})
    def test_nonexistent_job(self):
        """Should return not_found for nonexistent job."""
        result = get_job_status('nonexistent')
        assert result == {'state': 'not_found'}


class TestConnectToDatabase:
    """Tests for connect_to_database."""

    @patch('awslabs.mysql_mcp_server.server.internal_connect_to_database')
    def test_successful_connection(self, mock_internal):
        """Should return success response on successful connection."""
        mock_conn = MagicMock()
        llm_response = json.dumps({'connection_method': 'rdsapi', 'database': 'testdb'})
        mock_internal.return_value = (mock_conn, llm_response)

        result = connect_to_database(
            region='us-east-1',
            database_type=DatabaseType.AURORA_MYSQL,
            connection_method=ConnectionMethod.RDS_API,
            cluster_identifier='cluster-1',
            db_endpoint='ep.rds.amazonaws.com',
            port=3306,
            database='testdb',
        )

        assert 'rdsapi' in result

    @patch('awslabs.mysql_mcp_server.server.internal_connect_to_database')
    def test_connection_failure(self, mock_internal):
        """Should return error response on failure."""
        mock_internal.side_effect = RuntimeError('connection failed')

        result = connect_to_database(
            region='us-east-1',
            database_type=DatabaseType.AURORA_MYSQL,
            connection_method=ConnectionMethod.RDS_API,
            cluster_identifier='cluster-1',
            db_endpoint='ep.rds.amazonaws.com',
            port=3306,
            database='testdb',
        )

        parsed = json.loads(result)
        assert parsed['status'] == 'Failed'
        assert 'connection failed' in parsed['error']


class TestCreateCluster:
    """Tests for create_cluster."""

    @patch('awslabs.mysql_mcp_server.server.threading.Thread')
    def test_returns_pending_status(self, mock_thread_cls):
        """Should return pending status with job_id."""
        mock_thread = MagicMock()
        mock_thread_cls.return_value = mock_thread

        result = create_cluster(
            region='us-east-1',
            cluster_identifier='new-cluster',
            database='testdb',
            engine_version='8.0',
        )

        parsed = json.loads(result)
        assert parsed['status'] == 'Pending'
        assert 'job_id' in parsed
        assert parsed['cluster_identifier'] == 'new-cluster'
        mock_thread.start.assert_called_once()
