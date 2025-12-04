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

"""Tests for the connection interfaces functionality."""

import pytest
from awslabs.mysql_mcp_server.connection.db_connection_singleton import DBConnectionSingleton
from unittest.mock import MagicMock, patch


class TestDBConnectionSingleton:
    """Tests for the DBConnectionSingleton class."""

    def test_data_api_singleton_initialization(self):
        """Test that the RDS Data API singleton initializes correctly."""
        # Reset singleton
        DBConnectionSingleton._instance = None

        # Setup mock
        with patch(
            'awslabs.mysql_mcp_server.connection.db_connection_singleton.RDSDataAPIConnection'
        ) as mock_rds_connection:
            mock_conn = MagicMock()
            mock_rds_connection.return_value = mock_conn

            # Initialize singleton
            DBConnectionSingleton.initialize(
                resource_arn='test_resource_arn',
                secret_arn='test_secret_arn',
                database='test_db',
                region='us-east-1',
                readonly=True,
            )

            # Get the singleton instance
            instance = DBConnectionSingleton.get()

            # Verify RDSDataAPIConnection was created
            mock_rds_connection.assert_called_once()
            args, kwargs = mock_rds_connection.call_args
            assert kwargs['cluster_arn'] == 'test_resource_arn'
            assert kwargs['secret_arn'] == 'test_secret_arn'
            assert kwargs['database'] == 'test_db'
            assert kwargs['region'] == 'us-east-1'
            assert kwargs['readonly'] is True
            assert instance.db_connection == mock_conn

    def test_asyncmy_singleton_initialization(self):
        """Test that the Asyncmy singleton initializes correctly."""
        # Reset singleton
        DBConnectionSingleton._instance = None

        # Setup mock
        with patch(
            'awslabs.mysql_mcp_server.connection.db_connection_singleton.AsyncmyPoolConnection'
        ) as mock_rds_connection:
            mock_conn = MagicMock()
            mock_rds_connection.return_value = mock_conn

            # Initialize singleton
            DBConnectionSingleton.initialize(
                hostname=str('test_host'),
                port=int(3306),
                secret_arn='test_secret_arn',
                database='test_db',
                region='us-east-1',
                readonly=True,
            )

            # Get the singleton instance
            instance = DBConnectionSingleton.get()

            # Verify AsyncmyPoolConnection was created
            mock_rds_connection.assert_called_once()
            args, kwargs = mock_rds_connection.call_args
            assert kwargs['hostname'] == 'test_host'
            assert kwargs['port'] == 3306
            assert kwargs['secret_arn'] == 'test_secret_arn'
            assert kwargs['database'] == 'test_db'
            assert kwargs['region'] == 'us-east-1'
            assert kwargs['readonly'] is True
            assert instance.db_connection == mock_conn

    def test_data_api_singleton_validation_missing_params(self):
        """Test that the RDS Data API singleton validates the parameters correctly."""
        # Reset singleton
        DBConnectionSingleton._instance = None

        # Test missing resource_arn
        with pytest.raises(ValueError) as excinfo:
            DBConnectionSingleton.initialize(
                resource_arn='test',
                secret_arn='',
                database='test_db',
                region='us-east-1',
                readonly=True,
            )
        assert 'Missing required connection parameters' in str(excinfo.value)

    def test_asyncmy_singleton_validation_missing_params(self):
        """Test that the Asyncmy singleton validates the parameters correctly."""
        # Reset singleton
        DBConnectionSingleton._instance = None

        # Test missing resource_arn
        with pytest.raises(ValueError) as excinfo:
            DBConnectionSingleton.initialize(
                hostname='',
                secret_arn='test',
                database='test_db',
                region='us-east-1',
                readonly=True,
            )
        assert 'Missing required connection parameters' in str(excinfo.value)

    def test_singleton_get_without_initialization(self):
        """Test that get() raises an error if the singleton is not initialized."""
        # Reset singleton
        DBConnectionSingleton._instance = None

        # Test get() without initialization
        with pytest.raises(RuntimeError) as excinfo:
            DBConnectionSingleton.get()
        assert 'DBConnectionSingleton is not initialized' in str(excinfo.value)
