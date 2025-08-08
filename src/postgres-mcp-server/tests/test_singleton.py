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
from awslabs.postgres_mcp_server.connection.db_connection_singleton import DBConnectionSingleton
from unittest.mock import MagicMock, patch


class TestDBConnectionSingleton:
    """Tests for the DBConnectionSingleton class."""

    def test_singleton_initialization(self):
        """Test that the singleton initializes correctly."""
        # Reset singleton
        DBConnectionSingleton._instance = None

        # Setup mock
        with patch(
            'awslabs.postgres_mcp_server.connection.db_connection_singleton.RDSDataAPIConnection'
        ) as mock_rds_connection:
            mock_conn = MagicMock()
            mock_rds_connection.return_value = mock_conn

            # Initialize singleton
            DBConnectionSingleton.initialize(
                resource_arn='test_resource_arn',
                secret_arn='test_secret_arn',  # pragma: allowlist secret
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
            assert kwargs['secret_arn'] == 'test_secret_arn'  # pragma: allowlist secret
            assert kwargs['database'] == 'test_db'
            assert kwargs['region'] == 'us-east-1'
            assert kwargs['readonly'] is True
            assert instance.db_connection == mock_conn

    def test_singleton_validation_missing_params(self):
        """Test that the singleton validates the parameters correctly."""
        # Reset singleton
        DBConnectionSingleton._instance = None

        # Test missing resource_arn
        with pytest.raises(ValueError) as excinfo:
            DBConnectionSingleton.initialize(
                resource_arn='',
                secret_arn='test_secret_arn',  # pragma: allowlist secret
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

    def test_singleton_cleanup(self):
        """Test that cleanup() correctly closes the connection."""
        # Reset singleton
        DBConnectionSingleton._instance = None

        # Setup mock
        with patch(
            'awslabs.postgres_mcp_server.connection.rds_api_connection.RDSDataAPIConnection'
        ) as mock_rds_connection:
            mock_conn = MagicMock()
            mock_rds_connection.return_value = mock_conn

            # Initialize singleton
            DBConnectionSingleton.initialize(
                resource_arn='test_resource_arn',
                secret_arn='test_secret_arn',  # pragma: allowlist secret
                database='test_db',
                region='us-east-1',
                readonly=True,
                is_test=True,
            )

            # Mock asyncio.get_event_loop() and loop.is_running()
            with patch('asyncio.get_event_loop') as mock_get_loop:
                mock_loop = MagicMock()
                mock_loop.is_running.return_value = False
                mock_get_loop.return_value = mock_loop

                # Call cleanup
                DBConnectionSingleton.cleanup()

                # Verify close() was called
                mock_loop.run_until_complete.assert_called_once()
