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

"""Tests for the clients module of the rds-monitoring-mcp-server."""

from awslabs.rds_control_plane_mcp_server.clients import (
    get_pi_client,
    get_rds_client,
)


class TestTypeDefinitions:
    """Tests for type definitions in clients.py."""

    def test_type_definitions(self):
        """Test that the type definitions are properly defined."""
        from awslabs.rds_control_plane_mcp_server import clients

        # Verify that the type aliases are imported
        assert hasattr(clients, 'PIClient')
        assert hasattr(clients, 'RDSClient')


class TestGetRDSClient:
    """Tests for the get_rds_client function."""

    def test_get_rds_client_default(self, mock_boto3):
        """Test getting an RDS client with default parameters."""
        client = get_rds_client()
        mock_boto3['client'].assert_called_once_with('rds', region_name=None)
        assert client == mock_boto3['rds']

    def test_get_rds_client_with_region(self, mock_boto3):
        """Test getting an RDS client with a specific region."""
        client = get_rds_client(region_name='us-east-1')
        mock_boto3['client'].assert_called_once_with('rds', region_name='us-east-1')
        assert client == mock_boto3['rds']

    def test_get_rds_client_with_profile(self, mock_boto3):
        """Test getting an RDS client with a specific profile."""
        client = get_rds_client(profile_name='test-profile')
        mock_boto3['Session'].assert_called_once_with(profile_name='test-profile')
        mock_boto3['Session'].return_value.client.assert_called_once_with('rds', region_name=None)
        assert client == mock_boto3['rds']

    def test_get_rds_client_with_region_and_profile(self, mock_boto3):
        """Test getting an RDS client with a specific region and profile."""
        client = get_rds_client(region_name='us-east-1', profile_name='test-profile')
        mock_boto3['Session'].assert_called_once_with(profile_name='test-profile')
        mock_boto3['Session'].return_value.client.assert_called_once_with(
            'rds', region_name='us-east-1'
        )
        assert client == mock_boto3['rds']

    def test_get_rds_client_with_none_region(self, mock_boto3):
        """Test getting an RDS client with None region."""
        client = get_rds_client(region_name=None)
        mock_boto3['client'].assert_called_once_with('rds', region_name=None)
        assert client == mock_boto3['rds']


class TestGetPIClient:
    """Tests for the get_pi_client function."""

    def test_get_pi_client_default(self, mock_boto3):
        """Test getting a PI client with default parameters."""
        client = get_pi_client()
        mock_boto3['client'].assert_called_once_with('pi', region_name=None)
        assert client == mock_boto3['pi']

    def test_get_pi_client_with_region(self, mock_boto3):
        """Test getting a PI client with a specific region."""
        client = get_pi_client(region_name='us-east-1')
        mock_boto3['client'].assert_called_once_with('pi', region_name='us-east-1')
        assert client == mock_boto3['pi']

    def test_get_pi_client_with_profile(self, mock_boto3):
        """Test getting a PI client with a specific profile."""
        client = get_pi_client(profile_name='test-profile')
        mock_boto3['Session'].assert_called_once_with(profile_name='test-profile')
        mock_boto3['Session'].return_value.client.assert_called_once_with('pi', region_name=None)
        assert client == mock_boto3['pi']

    def test_get_pi_client_with_region_and_profile(self, mock_boto3):
        """Test getting a PI client with a specific region and profile."""
        client = get_pi_client(region_name='us-east-1', profile_name='test-profile')
        mock_boto3['Session'].assert_called_once_with(profile_name='test-profile')
        mock_boto3['Session'].return_value.client.assert_called_once_with(
            'pi', region_name='us-east-1'
        )
        assert client == mock_boto3['pi']

    def test_get_pi_client_with_none_region(self, mock_boto3):
        """Test getting a PI client with None region."""
        client = get_pi_client(region_name=None)
        mock_boto3['client'].assert_called_once_with('pi', region_name=None)
        assert client == mock_boto3['pi']
