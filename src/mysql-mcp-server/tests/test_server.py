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
import pytest
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
        # Exception type name is surfaced to the LLM; the raw message is
        # logged locally only and must NOT appear in the response payload
        # to avoid leaking identity-revealing strings from boto3 / asyncmy /
        # Secrets Manager exceptions.
        assert parsed['error_type'] == 'RuntimeError'
        assert 'see server logs' in parsed['error_message']
        assert 'connection failed' not in result, (
            'Raw exception message must not appear anywhere in the response '
            'returned to the LLM client.'
        )


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


class TestCreateClusterWorker:
    """Tests for create_cluster_worker, the background thread body for create_cluster.

    Exercises the success path that flips async_job_status to 'succeeded' and
    the catch-all exception path that records 'failed' with a redacted result.
    """

    @patch('awslabs.mysql_mcp_server.server.async_job_status', {'job-1': {'state': 'pending'}})
    @patch('awslabs.mysql_mcp_server.server.internal_connect_to_database')
    @patch('awslabs.mysql_mcp_server.server.setup_aurora_iam_policy_for_current_user')
    @patch('awslabs.mysql_mcp_server.server.internal_create_aurora_cluster')
    def test_success_path_marks_job_succeeded(self, mock_create, mock_setup_iam, mock_connect):
        """Happy path: cluster created, IAM policy attached, connection cached."""
        from awslabs.mysql_mcp_server.server import async_job_status, create_cluster_worker

        mock_create.return_value = {
            'MasterUsername': 'admin',
            'DbClusterResourceId': 'cluster-ABCD123',
            'Endpoint': 'cluster-ABCD123.cluster-xyz.us-east-1.rds.amazonaws.com',
        }
        mock_connect.return_value = (MagicMock(), '{}')

        create_cluster_worker(
            job_id='job-1',
            region='us-east-1',
            cluster_identifier='new-cluster',
            engine_version='8.0',
            database='app',
            database_type=DatabaseType.AURORA_MYSQL,
            connection_method=ConnectionMethod.RDS_API,
        )

        assert async_job_status['job-1']['state'] == 'succeeded'
        mock_create.assert_called_once()
        mock_setup_iam.assert_called_once()
        mock_connect.assert_called_once()

    @patch('awslabs.mysql_mcp_server.server.async_job_status', {'job-1': {'state': 'pending'}})
    @patch('awslabs.mysql_mcp_server.server.internal_create_aurora_cluster')
    def test_exception_marks_job_failed_with_redacted_result(self, mock_create):
        """On exception, state -> failed and result reveals only the exception type.

        The async_job_status entry is read by the LLM via get_job_status, so
        it must surface only the exception class name (e.g., ClientError) and
        not raw boto3 messages that may include account ids, ARNs, or other
        identity-revealing strings.
        """
        from awslabs.mysql_mcp_server.server import async_job_status, create_cluster_worker

        mock_create.side_effect = RuntimeError(
            'something with arn:aws:rds:us-east-1:123456789012:cluster:my-cluster'
        )

        create_cluster_worker(
            job_id='job-1',
            region='us-east-1',
            cluster_identifier='new-cluster',
            engine_version='8.0',
            database='app',
            database_type=DatabaseType.AURORA_MYSQL,
            connection_method=ConnectionMethod.RDS_API,
        )

        assert async_job_status['job-1']['state'] == 'failed'
        result = async_job_status['job-1']['result']
        assert 'RuntimeError' in result
        assert 'see server logs' in result
        # The raw boto3-style message must not leak through.
        assert '123456789012' not in result
        assert 'arn:aws:rds' not in result


class TestInternalConnectToDatabaseRouting:
    """Tests for internal_connect_to_database's connection-method routing."""

    @patch('awslabs.mysql_mcp_server.server.db_connection_map')
    @patch('awslabs.mysql_mcp_server.server.internal_get_cluster_properties')
    @patch('awslabs.mysql_mcp_server.server.AsyncmyPoolConnection')
    def test_mysql_wire_iam_protocol_builds_iam_pool(
        self, mock_pool_cls, mock_get_props, mock_map
    ):
        """MYSQL_WIRE_IAM_PROTOCOL routes to AsyncmyPoolConnection with is_iam_auth=True."""
        from awslabs.mysql_mcp_server.server import internal_connect_to_database

        mock_map.get.return_value = None
        mock_get_props.return_value = {
            'MasterUsername': 'admin',
            'DBClusterArn': 'arn:aws:rds:us-east-1:123:cluster:my-cluster',
            'MasterUserSecret': {'SecretArn': 'arn:secret'},
            'Endpoint': 'ep.rds.amazonaws.com',
            'Port': '3306',
            'HttpEndpointEnabled': False,
        }

        internal_connect_to_database(
            region='us-east-1',
            database_type=DatabaseType.AURORA_MYSQL,
            connection_method=ConnectionMethod.MYSQL_WIRE_IAM_PROTOCOL,
            cluster_identifier='my-cluster',
            db_endpoint='ep.rds.amazonaws.com',
            port=3306,
            database='app',
        )

        kwargs = mock_pool_cls.call_args.kwargs
        assert kwargs['is_iam_auth'] is True
        assert kwargs['db_user'] == 'admin'
        assert kwargs['secret_arn'] == ''

    @patch('awslabs.mysql_mcp_server.server.db_connection_map')
    @patch('awslabs.mysql_mcp_server.server.internal_get_cluster_properties')
    @patch('awslabs.mysql_mcp_server.server.AsyncmyPoolConnection')
    def test_mysql_wire_protocol_builds_secret_pool(self, mock_pool_cls, mock_get_props, mock_map):
        """MYSQL_WIRE_PROTOCOL routes to AsyncmyPoolConnection with is_iam_auth=False."""
        from awslabs.mysql_mcp_server.server import internal_connect_to_database

        mock_map.get.return_value = None
        mock_get_props.return_value = {
            'MasterUsername': 'admin',
            'DBClusterArn': 'arn:aws:rds:us-east-1:123:cluster:my-cluster',
            'MasterUserSecret': {'SecretArn': 'arn:secret'},
            'Endpoint': 'ep.rds.amazonaws.com',
            'Port': '3306',
            'HttpEndpointEnabled': False,
        }

        internal_connect_to_database(
            region='us-east-1',
            database_type=DatabaseType.AURORA_MYSQL,
            connection_method=ConnectionMethod.MYSQL_WIRE_PROTOCOL,
            cluster_identifier='my-cluster',
            db_endpoint='ep.rds.amazonaws.com',
            port=3306,
            database='app',
        )

        kwargs = mock_pool_cls.call_args.kwargs
        assert kwargs['is_iam_auth'] is False
        assert kwargs['secret_arn'] == 'arn:secret'

    @patch('awslabs.mysql_mcp_server.server.db_connection_map')
    @patch('awslabs.mysql_mcp_server.server.internal_get_instance_properties')
    @patch('awslabs.mysql_mcp_server.server.AsyncmyPoolConnection')
    def test_endpoint_only_path_for_rds_mysql(self, mock_pool_cls, mock_get_instance, mock_map):
        """RDS MySQL with only db_endpoint (no cluster_identifier) uses get_instance_properties."""
        from awslabs.mysql_mcp_server.server import internal_connect_to_database

        mock_map.get.return_value = None
        mock_get_instance.return_value = {
            'MasterUsername': 'admin',
            'MasterUserSecret': {'SecretArn': 'arn:secret'},
            'Endpoint': {'Port': 3306},
        }

        internal_connect_to_database(
            region='us-east-1',
            database_type=DatabaseType.RDS_MYSQL,
            connection_method=ConnectionMethod.MYSQL_WIRE_PROTOCOL,
            cluster_identifier='',
            db_endpoint='instance-1.xyz.rds.amazonaws.com',
            port=3306,
            database='app',
        )

        mock_get_instance.assert_called_once()

    def test_aurora_mysql_requires_cluster_identifier(self):
        """Aurora MySQL must always have cluster_identifier; endpoint alone is not enough."""
        from awslabs.mysql_mcp_server.server import internal_connect_to_database

        with pytest.raises(ValueError, match="cluster_identifier can't be none or empty"):
            internal_connect_to_database(
                region='us-east-1',
                database_type=DatabaseType.AURORA_MYSQL,
                connection_method=ConnectionMethod.MYSQL_WIRE_PROTOCOL,
                cluster_identifier='',
                db_endpoint='ep.rds.amazonaws.com',
                port=3306,
                database='app',
            )

    def test_neither_cluster_id_nor_endpoint_raises(self):
        """Standalone RDS path also requires at least db_endpoint."""
        from awslabs.mysql_mcp_server.server import internal_connect_to_database

        with pytest.raises(ValueError, match='Either cluster_identifier or db_endpoint'):
            internal_connect_to_database(
                region='us-east-1',
                database_type=DatabaseType.RDS_MYSQL,
                connection_method=ConnectionMethod.MYSQL_WIRE_PROTOCOL,
                cluster_identifier='',
                db_endpoint='',
                port=3306,
                database='app',
            )

    @patch('awslabs.mysql_mcp_server.server.db_connection_map')
    def test_returns_existing_connection_without_recreating(self, mock_map):
        """If a cached connection exists for the key, reuse it."""
        from awslabs.mysql_mcp_server.server import internal_connect_to_database

        existing = MagicMock()
        mock_map.get.return_value = existing

        conn, llm_response = internal_connect_to_database(
            region='us-east-1',
            database_type=DatabaseType.AURORA_MYSQL,
            connection_method=ConnectionMethod.RDS_API,
            cluster_identifier='cluster-1',
            db_endpoint='ep.rds.amazonaws.com',
            port=3306,
            database='app',
        )

        assert conn is existing


class TestGetTableSchema:
    """Tests for the get_table_schema MCP tool."""

    async def test_builds_information_schema_query_with_params(self):
        """Should call run_query with INFORMATION_SCHEMA.COLUMNS SQL and named parameters."""
        from awslabs.mysql_mcp_server.server import get_table_schema
        from unittest.mock import AsyncMock, patch

        ctx = MagicMock()

        with patch(
            'awslabs.mysql_mcp_server.server.run_query', new_callable=AsyncMock
        ) as mock_run_query:
            mock_run_query.return_value = [{'columnMetadata': [], 'records': []}]
            await get_table_schema(
                table_name='users',
                ctx=ctx,
                connection_method=ConnectionMethod.RDS_API,
                cluster_identifier='cluster-1',
                db_endpoint='ep.rds.amazonaws.com',
                database='app',
            )

        kwargs = mock_run_query.call_args.kwargs
        assert 'INFORMATION_SCHEMA.COLUMNS' in kwargs['sql']
        assert 'IS_NULLABLE' in kwargs['sql']
        assert 'COLUMN_KEY' in kwargs['sql']
        assert 'EXTRA' in kwargs['sql']
        # Named parameters should pass table_schema and table_name explicitly
        # so the MySQL prepared statement substitutes them safely.
        param_names = {p['name'] for p in kwargs['query_parameters']}
        assert param_names == {'table_schema', 'table_name'}
