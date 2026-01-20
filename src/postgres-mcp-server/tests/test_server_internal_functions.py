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
"""Tests for server internal functions."""

import json
import pytest
from awslabs.postgres_mcp_server.connection.db_connection_map import ConnectionMethod, DatabaseType
from awslabs.postgres_mcp_server.server import (
    create_cluster_worker,
    internal_connect_to_database,
)
from unittest.mock import MagicMock, patch


class TestInternalConnectToDatabase:
    """Tests for internal_connect_to_database function."""

    def test_missing_region_raises_error(self):
        """Test that missing region raises ValueError."""
        with pytest.raises(ValueError, match="region can't be none or empty"):
            internal_connect_to_database(
                region='',
                database_type=DatabaseType.APG,
                connection_method=ConnectionMethod.RDS_API,
                cluster_identifier='test-cluster',
                db_endpoint='test.endpoint.com',
                port=5432,
                database='testdb',
            )

    def test_missing_connection_method_raises_error(self):
        """Test that missing connection_method raises ValueError."""
        with pytest.raises(ValueError, match="connection_method can't be none or empty"):
            internal_connect_to_database(
                region='us-east-1',
                database_type=DatabaseType.APG,
                connection_method=None,  # type: ignore
                cluster_identifier='test-cluster',
                db_endpoint='test.endpoint.com',
                port=5432,
                database='testdb',
            )

    def test_missing_database_type_raises_error(self):
        """Test that missing database_type raises ValueError."""
        with pytest.raises(ValueError, match="database_type can't be none or empty"):
            internal_connect_to_database(
                region='us-east-1',
                database_type=None,  # type: ignore
                connection_method=ConnectionMethod.RDS_API,
                cluster_identifier='test-cluster',
                db_endpoint='test.endpoint.com',
                port=5432,
                database='testdb',
            )

    def test_apg_missing_cluster_identifier_raises_error(self):
        """Test that APG without cluster_identifier raises ValueError."""
        with pytest.raises(
            ValueError,
            match="cluster_identifier can't be none or empty for Aurora Postgres Database",
        ):
            internal_connect_to_database(
                region='us-east-1',
                database_type=DatabaseType.APG,
                connection_method=ConnectionMethod.RDS_API,
                cluster_identifier='',
                db_endpoint='test.endpoint.com',
                port=5432,
                database='testdb',
            )

    def test_returns_existing_connection(self):
        """Test that existing connection is returned if available."""
        mock_connection = MagicMock()

        with patch('awslabs.postgres_mcp_server.server.db_connection_map') as mock_map:
            mock_map.get.return_value = mock_connection

            conn, response = internal_connect_to_database(
                region='us-east-1',
                database_type=DatabaseType.APG,
                connection_method=ConnectionMethod.RDS_API,
                cluster_identifier='test-cluster',
                db_endpoint='test.endpoint.com',
                port=5432,
                database='testdb',
            )

            assert conn == mock_connection
            response_dict = json.loads(response)
            assert response_dict['cluster_identifier'] == 'test-cluster'
            assert response_dict['connection_method'] == 'rdsapi'

    def test_creates_rds_api_connection(self):
        """Test creating RDS API connection."""
        with (
            patch('awslabs.postgres_mcp_server.server.db_connection_map') as mock_map,
            patch(
                'awslabs.postgres_mcp_server.server.internal_get_cluster_properties'
            ) as mock_props,
            patch('awslabs.postgres_mcp_server.server.RDSDataAPIConnection') as mock_rds_conn,
        ):
            mock_map.get.return_value = None
            mock_props.return_value = {
                'HttpEndpointEnabled': True,
                'MasterUsername': 'postgres',
                'DBClusterArn': 'arn:aws:rds:us-east-1:123456789012:cluster:test',
                'MasterUserSecret': {'SecretArn': 'arn:secret'},
                'Endpoint': 'test.endpoint.com',
                'Port': 5432,
            }
            mock_connection = MagicMock()
            mock_rds_conn.return_value = mock_connection

            conn, response = internal_connect_to_database(
                region='us-east-1',
                database_type=DatabaseType.APG,
                connection_method=ConnectionMethod.RDS_API,
                cluster_identifier='test-cluster',
                db_endpoint='',
                port=5432,
                database='testdb',
            )

            assert conn == mock_connection
            mock_map.set.assert_called_once()

    def test_creates_pgwire_iam_connection(self):
        """Test creating PG Wire IAM connection."""
        with (
            patch('awslabs.postgres_mcp_server.server.db_connection_map') as mock_map,
            patch(
                'awslabs.postgres_mcp_server.server.internal_get_cluster_properties'
            ) as mock_props,
            patch('awslabs.postgres_mcp_server.server.PsycopgPoolConnection') as mock_pg_conn,
        ):
            mock_map.get.return_value = None
            mock_props.return_value = {
                'HttpEndpointEnabled': False,
                'MasterUsername': 'postgres',
                'DBClusterArn': 'arn:aws:rds:us-east-1:123456789012:cluster:test',
                'MasterUserSecret': {'SecretArn': 'arn:secret'},
                'Endpoint': 'test.endpoint.com',
                'Port': 5432,
            }
            mock_connection = MagicMock()
            mock_pg_conn.return_value = mock_connection

            conn, response = internal_connect_to_database(
                region='us-east-1',
                database_type=DatabaseType.APG,
                connection_method=ConnectionMethod.PG_WIRE_IAM_PROTOCOL,
                cluster_identifier='test-cluster',
                db_endpoint='test.endpoint.com',
                port=5432,
                database='testdb',
            )

            assert conn == mock_connection
            mock_pg_conn.assert_called_once()
            call_kwargs = mock_pg_conn.call_args[1]
            assert call_kwargs['is_iam_auth'] is True

    def test_creates_pgwire_connection_with_secrets(self):
        """Test creating PG Wire connection with Secrets Manager."""
        with (
            patch('awslabs.postgres_mcp_server.server.db_connection_map') as mock_map,
            patch(
                'awslabs.postgres_mcp_server.server.internal_get_cluster_properties'
            ) as mock_props,
            patch('awslabs.postgres_mcp_server.server.PsycopgPoolConnection') as mock_pg_conn,
        ):
            mock_map.get.return_value = None
            mock_props.return_value = {
                'HttpEndpointEnabled': False,
                'MasterUsername': 'postgres',
                'DBClusterArn': 'arn:aws:rds:us-east-1:123456789012:cluster:test',
                'MasterUserSecret': {'SecretArn': 'arn:secret'},
                'Endpoint': 'test.endpoint.com',
                'Port': 5432,
            }
            mock_connection = MagicMock()
            mock_pg_conn.return_value = mock_connection

            conn, response = internal_connect_to_database(
                region='us-east-1',
                database_type=DatabaseType.APG,
                connection_method=ConnectionMethod.PG_WIRE_PROTOCOL,
                cluster_identifier='test-cluster',
                db_endpoint='test.endpoint.com',
                port=5432,
                database='testdb',
            )

            assert conn == mock_connection
            mock_pg_conn.assert_called_once()
            call_kwargs = mock_pg_conn.call_args[1]
            assert call_kwargs['is_iam_auth'] is False
            assert call_kwargs['secret_arn'] == 'arn:secret'

    def test_rpg_instance_without_cluster(self):
        """Test connecting to RDS Postgres instance without cluster."""
        with (
            patch('awslabs.postgres_mcp_server.server.db_connection_map') as mock_map,
            patch(
                'awslabs.postgres_mcp_server.server.internal_get_instance_properties'
            ) as mock_props,
            patch('awslabs.postgres_mcp_server.server.PsycopgPoolConnection') as mock_pg_conn,
        ):
            mock_map.get.return_value = None
            mock_props.return_value = {
                'MasterUsername': 'postgres',
                'MasterUserSecret': {'SecretArn': 'arn:secret'},
                'Endpoint': {'Port': 5432},
            }
            mock_connection = MagicMock()
            mock_pg_conn.return_value = mock_connection

            conn, response = internal_connect_to_database(
                region='us-east-1',
                database_type=DatabaseType.RPG,
                connection_method=ConnectionMethod.PG_WIRE_PROTOCOL,
                cluster_identifier='',
                db_endpoint='instance.endpoint.com',
                port=5432,
                database='testdb',
            )

            assert conn == mock_connection
            mock_props.assert_called_once()

    def test_uses_cluster_endpoint_when_not_provided(self):
        """Test that cluster endpoint is used when db_endpoint is not provided."""
        with (
            patch('awslabs.postgres_mcp_server.server.db_connection_map') as mock_map,
            patch(
                'awslabs.postgres_mcp_server.server.internal_get_cluster_properties'
            ) as mock_props,
            patch('awslabs.postgres_mcp_server.server.RDSDataAPIConnection') as mock_rds_conn,
        ):
            mock_map.get.return_value = None
            mock_props.return_value = {
                'HttpEndpointEnabled': True,
                'MasterUsername': 'postgres',
                'DBClusterArn': 'arn:aws:rds:us-east-1:123456789012:cluster:test',
                'MasterUserSecret': {'SecretArn': 'arn:secret'},
                'Endpoint': 'cluster.endpoint.com',
                'Port': 5432,
            }
            mock_connection = MagicMock()
            mock_rds_conn.return_value = mock_connection

            conn, response = internal_connect_to_database(
                region='us-east-1',
                database_type=DatabaseType.APG,
                connection_method=ConnectionMethod.RDS_API,
                cluster_identifier='test-cluster',
                db_endpoint='',  # Empty, should use cluster endpoint
                port=0,  # Should be overridden
                database='testdb',
            )

            response_dict = json.loads(response)
            assert response_dict['db_endpoint'] == 'cluster.endpoint.com'
            assert response_dict['port'] == 5432


class TestCreateClusterWorker:
    """Tests for create_cluster_worker function."""

    def test_worker_success_updates_job_status(self):
        """Test that worker updates job status on success."""
        with (
            patch(
                'awslabs.postgres_mcp_server.server.internal_create_serverless_cluster'
            ) as mock_create,
            patch('awslabs.postgres_mcp_server.server.setup_aurora_iam_policy_for_current_user'),
            patch('awslabs.postgres_mcp_server.server.internal_connect_to_database'),
            patch('awslabs.postgres_mcp_server.server.async_job_status'),
            patch('awslabs.postgres_mcp_server.server.async_job_status_lock') as mock_lock,
        ):
            mock_create.return_value = {
                'MasterUsername': 'postgres',
                'DbClusterResourceId': 'cluster-123',
                'Endpoint': 'test.endpoint.com',
            }
            mock_lock.acquire = MagicMock()
            mock_lock.release = MagicMock()

            create_cluster_worker(
                job_id='test-job',
                region='us-east-1',
                database_type=DatabaseType.APG,
                connection_method=ConnectionMethod.RDS_API,
                cluster_identifier='test-cluster',
                engine_version='17.5',
                database='testdb',
            )

            # Verify job status was updated
            assert mock_lock.acquire.called
            assert mock_lock.release.called

    def test_worker_failure_updates_job_status(self):
        """Test that worker updates job status on failure."""
        with (
            patch(
                'awslabs.postgres_mcp_server.server.internal_create_serverless_cluster'
            ) as mock_create,
            patch('awslabs.postgres_mcp_server.server.async_job_status'),
            patch('awslabs.postgres_mcp_server.server.async_job_status_lock') as mock_lock,
        ):
            mock_create.side_effect = Exception('Cluster creation failed')
            mock_lock.acquire = MagicMock()
            mock_lock.release = MagicMock()

            create_cluster_worker(
                job_id='test-job',
                region='us-east-1',
                database_type=DatabaseType.APG,
                connection_method=ConnectionMethod.RDS_API,
                cluster_identifier='test-cluster',
                engine_version='17.5',
                database='testdb',
            )

            # Verify job status was updated with failure
            assert mock_lock.acquire.called
            assert mock_lock.release.called
