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
"""Tests for the connection factory functionality."""

import pytest
from unittest.mock import patch, MagicMock
from awslabs.postgres_mcp_server.connection.connection_factory import DBConnectionFactory


class TestConnectionFactory:
    """Tests for the connection factory functionality."""
    
    @patch('awslabs.postgres_mcp_server.connection.rds_connector.RDSDataAPIConnection')
    def test_connection_factory_rds_data_api(self, mock_rds_connection):
        """Test that the connection factory creates an RDS Data API connection when resource_arn is provided."""
        # Setup mock
        mock_conn = MagicMock()
        mock_rds_connection.return_value = mock_conn
        
        # Create connection
        conn = DBConnectionFactory.create_connection(
            resource_arn="test_resource_arn",
            secret_arn="test_secret_arn",
            database="test_db",
            region="us-east-1",
            readonly=True
        )
        
        # Verify RDSDataAPIConnection was created
        mock_rds_connection.assert_called_once()
        args, kwargs = mock_rds_connection.call_args
        assert kwargs['cluster_arn'] == "test_resource_arn"
        assert kwargs['secret_arn'] == "test_secret_arn"
        assert kwargs['database'] == "test_db"
        assert kwargs['region'] == "us-east-1"
        assert kwargs['readonly'] is True
        assert conn == mock_conn
    
    @patch('awslabs.postgres_mcp_server.connection.psycopg_connector.PsycopgPoolConnection')
    def test_connection_factory_psycopg(self, mock_psycopg_connection):
        """Test that the connection factory creates a psycopg connection when hostname is provided."""
        # Setup mock
        mock_conn = MagicMock()
        mock_psycopg_connection.return_value = mock_conn
        
        # Create connection
        conn = DBConnectionFactory.create_connection(
            hostname="localhost",
            port=5432,
            secret_arn="test_secret_arn",
            database="test_db",
            region="us-east-1",
            readonly=True
        )
        
        # Verify PsycopgPoolConnection was created
        mock_psycopg_connection.assert_called_once()
        args, kwargs = mock_psycopg_connection.call_args
        assert kwargs['host'] == "localhost"
        assert kwargs['port'] == 5432
        assert kwargs['secret_arn'] == "test_secret_arn"
        assert kwargs['database'] == "test_db"
        assert kwargs['region'] == "us-east-1"
        assert kwargs['readonly'] is True
        assert conn == mock_conn
    
    def test_connection_factory_validation_missing_params(self):
        """Test that the connection factory validates the parameters correctly when both resource_arn and hostname are missing."""
        # Test missing both resource_arn and hostname
        with pytest.raises(ValueError) as excinfo:
            DBConnectionFactory.create_connection(
                secret_arn="test_secret_arn",
                database="test_db",
                region="us-east-1",
                readonly=True
            )
        assert "Either resource_arn or hostname must be provided" in str(excinfo.value)
