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

"""Tests for the client_manager module."""

import os
from awslabs.aws_msk_mcp_server.tools.common_functions.client_manager import AWSClientManager
from unittest.mock import MagicMock, patch


class TestAWSClientManager:
    """Tests for the AWSClientManager class."""

    def test_init(self):
        """Test initialization of the client manager."""
        # Arrange & Act
        client_manager = AWSClientManager()

        # Assert
        assert client_manager.clients == {}

    @patch('boto3.Session')
    def test_get_client(self, mock_session):
        """Test getting a client for a specific service and region."""
        # Arrange
        client_manager = AWSClientManager()
        mock_client = MagicMock()
        mock_session.return_value.client.return_value = mock_client
        region = 'us-east-1'
        service_name = 'kafka'

        # Act
        client = client_manager.get_client(region, service_name)

        # Assert
        assert client == mock_client
        mock_session.assert_called_once_with(profile_name='default', region_name=region)
        mock_session.return_value.client.assert_called_once_with(service_name)
        assert client_manager.clients[f'{service_name}_{region}'] == mock_client

    @patch('boto3.Session')
    def test_get_client_reuse(self, mock_session):
        """Test reusing an existing client for the same service and region."""
        # Arrange
        client_manager = AWSClientManager()
        mock_client = MagicMock()
        mock_session.return_value.client.return_value = mock_client
        region = 'us-east-1'
        service_name = 'kafka'

        # Act
        # Get the client for the first time
        client1 = client_manager.get_client(region, service_name)
        # Get the client for the second time
        client2 = client_manager.get_client(region, service_name)

        # Assert
        assert client1 == client2
        mock_session.assert_called_once_with(profile_name='default', region_name=region)
        mock_session.return_value.client.assert_called_once_with(service_name)

    @patch('boto3.Session')
    def test_get_client_different_services(self, mock_session):
        """Test getting clients for different services."""
        # Arrange
        client_manager = AWSClientManager()
        mock_kafka_client = MagicMock()
        mock_cloudwatch_client = MagicMock()
        mock_session.return_value.client.side_effect = [mock_kafka_client, mock_cloudwatch_client]
        region = 'us-east-1'
        kafka_service = 'kafka'
        cloudwatch_service = 'cloudwatch'

        # Act
        kafka_client = client_manager.get_client(region, kafka_service)
        cloudwatch_client = client_manager.get_client(region, cloudwatch_service)

        # Assert
        assert kafka_client == mock_kafka_client
        assert cloudwatch_client == mock_cloudwatch_client
        assert mock_session.call_count == 2
        assert mock_session.return_value.client.call_count == 2
        mock_session.return_value.client.assert_any_call(kafka_service)
        mock_session.return_value.client.assert_any_call(cloudwatch_service)

    @patch('boto3.Session')
    def test_get_client_different_regions(self, mock_session):
        """Test getting clients for different regions."""
        # Arrange
        client_manager = AWSClientManager()
        mock_us_east_client = MagicMock()
        mock_us_west_client = MagicMock()
        mock_session.return_value.client.side_effect = [mock_us_east_client, mock_us_west_client]
        us_east_region = 'us-east-1'
        us_west_region = 'us-west-2'
        service_name = 'kafka'

        # Act
        us_east_client = client_manager.get_client(us_east_region, service_name)
        us_west_client = client_manager.get_client(us_west_region, service_name)

        # Assert
        assert us_east_client == mock_us_east_client
        assert us_west_client == mock_us_west_client
        assert mock_session.call_count == 2
        assert mock_session.return_value.client.call_count == 2
        mock_session.assert_any_call(profile_name='default', region_name=us_east_region)
        mock_session.assert_any_call(profile_name='default', region_name=us_west_region)

    @patch.dict(os.environ, {'AWS_PROFILE': 'test-profile'})
    @patch('boto3.Session')
    def test_get_client_custom_profile(self, mock_session):
        """Test getting a client with a custom AWS profile."""
        # Arrange
        client_manager = AWSClientManager()
        mock_client = MagicMock()
        mock_session.return_value.client.return_value = mock_client
        region = 'us-east-1'
        service_name = 'kafka'

        # Act
        client = client_manager.get_client(region, service_name)

        # Assert
        assert client == mock_client
        mock_session.assert_called_once_with(profile_name='test-profile', region_name=region)
        mock_session.return_value.client.assert_called_once_with(service_name)
