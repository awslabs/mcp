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
"""Tests for SSH tunnel support and connection parameter handling."""

import pytest
from awslabs.postgres_mcp_server.connection.db_connection_map import (
    ConnectionMethod,
    DatabaseType,
)
from awslabs.postgres_mcp_server.server import internal_connect_to_database
from unittest.mock import MagicMock, patch


class TestSSHTunnelSupport:
    """Test suite for SSH tunnel support features."""

    @pytest.fixture
    def mock_cluster_properties(self):
        """Mock cluster properties."""
        return {
            'MasterUsername': 'postgres',
            'Endpoint': 'actual-db.rds.amazonaws.com',
            'Port': '5432',
            'HttpEndpointEnabled': False,
        }

    @pytest.mark.asyncio
    @patch('awslabs.postgres_mcp_server.server.db_connection_map')
    @patch('awslabs.postgres_mcp_server.server.PsycopgPoolConnection')
    @patch('awslabs.postgres_mcp_server.server.internal_get_cluster_properties')
    async def test_connection_host_override(
        self,
        mock_get_cluster_properties,
        mock_psycopg_class,
        mock_conn_map,
        mock_cluster_properties,
    ):
        """Test connection_host parameter overrides db_endpoint for connection."""
        mock_get_cluster_properties.return_value = mock_cluster_properties
        mock_conn = MagicMock()
        mock_psycopg_class.return_value = mock_conn
        mock_conn_map.get.return_value = None  # No existing connection

        db_connection, _ = internal_connect_to_database(
            region='us-west-2',
            database_type=DatabaseType.APG,
            connection_method=ConnectionMethod.PG_WIRE_IAM_PROTOCOL,
            cluster_identifier='test-cluster',
            db_endpoint='actual-db.rds.amazonaws.com',
            port=5432,
            database='postgres',
            db_user='ops_ro_iam',
            connection_host='127.0.0.1',
            connection_port=8192,
        )

        call_kwargs = mock_psycopg_class.call_args[1]
        assert call_kwargs['host'] == '127.0.0.1'
        assert call_kwargs['port'] == 8192

    @pytest.mark.asyncio
    @patch('awslabs.postgres_mcp_server.server.db_connection_map')
    @patch('awslabs.postgres_mcp_server.server.PsycopgPoolConnection')
    @patch('awslabs.postgres_mcp_server.server.internal_get_cluster_properties')
    async def test_iam_endpoint_for_token_generation(
        self,
        mock_get_cluster_properties,
        mock_psycopg_class,
        mock_conn_map,
        mock_cluster_properties,
    ):
        """Test IAM token uses db_endpoint, not connection_host."""
        mock_get_cluster_properties.return_value = mock_cluster_properties
        mock_conn = MagicMock()
        mock_psycopg_class.return_value = mock_conn
        mock_conn_map.get.return_value = None  # No existing connection

        db_connection, _ = internal_connect_to_database(
            region='us-west-2',
            database_type=DatabaseType.APG,
            connection_method=ConnectionMethod.PG_WIRE_IAM_PROTOCOL,
            cluster_identifier='test-cluster',
            db_endpoint='actual-db.rds.amazonaws.com',
            port=5432,
            database='postgres',
            db_user='ops_ro_iam',
            connection_host='127.0.0.1',
            connection_port=8192,
        )

        call_kwargs = mock_psycopg_class.call_args[1]
        assert call_kwargs['iam_host'] == 'actual-db.rds.amazonaws.com'
        assert call_kwargs['iam_port'] == 5432

    @pytest.mark.asyncio
    @patch('awslabs.postgres_mcp_server.server.db_connection_map')
    @patch('awslabs.postgres_mcp_server.server.PsycopgPoolConnection')
    @patch('awslabs.postgres_mcp_server.server.internal_get_cluster_properties')
    async def test_custom_db_user_for_iam_auth(
        self,
        mock_get_cluster_properties,
        mock_psycopg_class,
        mock_conn_map,
        mock_cluster_properties,
    ):
        """Test db_user parameter is used instead of master username."""
        mock_get_cluster_properties.return_value = mock_cluster_properties
        mock_conn = MagicMock()
        mock_psycopg_class.return_value = mock_conn
        mock_conn_map.get.return_value = None  # No existing connection

        db_connection, _ = internal_connect_to_database(
            region='us-west-2',
            database_type=DatabaseType.APG,
            connection_method=ConnectionMethod.PG_WIRE_IAM_PROTOCOL,
            cluster_identifier='test-cluster',
            db_endpoint='actual-db.rds.amazonaws.com',
            port=5432,
            database='postgres',
            db_user='ops_ro_iam',
        )

        call_kwargs = mock_psycopg_class.call_args[1]
        assert call_kwargs['db_user'] == 'ops_ro_iam'
