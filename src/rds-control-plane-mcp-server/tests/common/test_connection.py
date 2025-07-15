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

"""Tests for the connection module in the RDS Control Plane MCP Server."""

import os
from awslabs.rds_control_plane_mcp_server.common.connection import (
    CloudwatchConnectionManager,
    PIConnectionManager,
    RDSConnectionManager,
)
from unittest.mock import patch


class TestRDSConnectionManager:
    """Test RDS connection management."""

    def test_get_connection_default_settings(self, mock_rds_client):
        """Test RDS connection creation with default settings."""
        client = RDSConnectionManager.get_connection()
        assert client == mock_rds_client

    def test_get_connection_custom_settings(self, mock_rds_client):
        """Test RDS connection creation with custom environment settings."""
        env_vars = {
            'AWS_PROFILE': 'test-profile',
            'AWS_REGION': 'us-west-2',
            'RDS_MAX_RETRIES': '5',
            'RDS_RETRY_MODE': 'adaptive',
            'RDS_CONNECT_TIMEOUT': '10',
            'RDS_READ_TIMEOUT': '20',
        }

        with patch.dict(os.environ, env_vars):
            client = RDSConnectionManager.get_connection()
            assert client == mock_rds_client

    def test_connection_reuse(self):
        """Test that the RDS connection is reused rather than recreated."""
        client1 = RDSConnectionManager.get_connection()
        client2 = RDSConnectionManager.get_connection()
        assert client1 == client2

    def test_close_connection(self, mock_rds_client):
        """Test that close_connection properly closes and clears the RDS client."""
        # Set up the client manually since fixture mocks get_connection
        RDSConnectionManager._client = mock_rds_client
        RDSConnectionManager.close_connection()
        mock_rds_client.close.assert_called_once()
        assert RDSConnectionManager._client is None

    def test_get_connection_after_close(self, mock_rds_client):
        """Test getting a new RDS connection after closing the previous one."""
        client1 = RDSConnectionManager.get_connection()
        assert client1 == mock_rds_client

        RDSConnectionManager.close_connection()

        client2 = RDSConnectionManager.get_connection()
        assert client2 == mock_rds_client


class TestPIConnectionManager:
    """Test PI connection management."""

    def test_get_connection_default_settings(self, mock_pi_client):
        """Test PI connection creation with default settings."""
        client = PIConnectionManager.get_connection()
        assert client == mock_pi_client

    def test_get_connection_custom_settings(self, mock_pi_client):
        """Test PI connection creation with custom environment settings."""
        env_vars = {
            'AWS_PROFILE': 'test-profile',
            'AWS_REGION': 'eu-west-1',
            'PI_MAX_RETRIES': '4',
            'PI_RETRY_MODE': 'adaptive',
        }

        with patch.dict(os.environ, env_vars):
            client = PIConnectionManager.get_connection()
            assert client == mock_pi_client


class TestCloudwatchConnectionManager:
    """Test CloudWatch connection management."""

    def test_get_connection_default_settings(self, mock_cloudwatch_client):
        """Test CloudWatch connection creation with default settings."""
        client = CloudwatchConnectionManager.get_connection()
        assert client == mock_cloudwatch_client
