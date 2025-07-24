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

"""Unit tests for the client_manager module used by logs_and_telemetry."""

import unittest
from awslabs.aws_msk_mcp_server import __version__
from awslabs.aws_msk_mcp_server.tools.common_functions.client_manager import AWSClientManager
from botocore.config import Config
from unittest.mock import MagicMock, patch


class TestAWSClientManager(unittest.TestCase):
    """Tests for the AWSClientManager class used by logs_and_telemetry."""

    @patch('awslabs.aws_msk_mcp_server.tools.common_functions.client_manager.boto3')
    def test_get_client_new_client(self, mock_boto3):
        """Test the get_client method when creating a new client."""
        # Setup
        mock_session = MagicMock()
        mock_boto3.Session.return_value = mock_session
        mock_client = MagicMock()
        mock_session.client.return_value = mock_client

        # Test
        client_manager = AWSClientManager()
        region = 'us-west-2'
        service_name = 'kafka'
        result = client_manager.get_client(region, service_name)

        # Verify
        mock_boto3.Session.assert_called_once_with(profile_name='default', region_name=region)
        mock_session.client.assert_called_once()

        # Check that the client was created with the correct parameters
        client_args = mock_session.client.call_args
        self.assertEqual(client_args[0][0], service_name)
        self.assertIsInstance(client_args[1]['config'], Config)
        self.assertIn(
            f'awslabs/mcp/aws-msk-mcp-server/{__version__}',
            client_args[1]['config'].user_agent_extra,
        )

        # Check that the result is the mock client
        self.assertEqual(result, mock_client)

        # Check that the client was cached
        self.assertIn(f'{service_name}_{region}', client_manager.clients)
        self.assertEqual(client_manager.clients[f'{service_name}_{region}'], mock_client)

    @patch('awslabs.aws_msk_mcp_server.tools.common_functions.client_manager.boto3')
    def test_get_client_cached_client(self, mock_boto3):
        """Test the get_client method when using a cached client."""
        # Setup
        mock_session = MagicMock()
        mock_boto3.Session.return_value = mock_session
        mock_client = MagicMock()
        mock_session.client.return_value = mock_client

        # Test
        client_manager = AWSClientManager()
        region = 'us-west-2'
        service_name = 'kafka'

        # First call should create a new client
        first_result = client_manager.get_client(region, service_name)

        # Reset the mocks
        mock_boto3.Session.reset_mock()
        mock_session.client.reset_mock()

        # Second call should use the cached client
        second_result = client_manager.get_client(region, service_name)

        # Verify
        mock_boto3.Session.assert_not_called()
        mock_session.client.assert_not_called()

        # Check that both results are the same client
        self.assertEqual(first_result, second_result)

        # Check that the client was cached
        self.assertIn(f'{service_name}_{region}', client_manager.clients)
        self.assertEqual(client_manager.clients[f'{service_name}_{region}'], mock_client)

    @patch('awslabs.aws_msk_mcp_server.tools.common_functions.client_manager.boto3')
    def test_get_client_different_services(self, mock_boto3):
        """Test the get_client method with different services."""
        # Setup
        mock_session = MagicMock()
        mock_boto3.Session.return_value = mock_session
        mock_kafka_client = MagicMock()
        mock_cloudwatch_client = MagicMock()

        # Configure client.return_value to return different clients based on service name
        def get_client_side_effect(*args, **kwargs):
            if args[0] == 'kafka':
                return mock_kafka_client
            elif args[0] == 'cloudwatch':
                return mock_cloudwatch_client
            return MagicMock()

        mock_session.client.side_effect = get_client_side_effect

        # Test
        client_manager = AWSClientManager()
        region = 'us-west-2'

        # Get kafka client
        kafka_result = client_manager.get_client(region, 'kafka')

        # Get cloudwatch client
        cloudwatch_result = client_manager.get_client(region, 'cloudwatch')

        # Verify
        self.assertEqual(mock_session.client.call_count, 2)

        # Check that the results are the correct clients
        self.assertEqual(kafka_result, mock_kafka_client)
        self.assertEqual(cloudwatch_result, mock_cloudwatch_client)

        # Check that both clients were cached
        self.assertIn('kafka_us-west-2', client_manager.clients)
        self.assertEqual(client_manager.clients['kafka_us-west-2'], mock_kafka_client)
        self.assertIn('cloudwatch_us-west-2', client_manager.clients)
        self.assertEqual(client_manager.clients['cloudwatch_us-west-2'], mock_cloudwatch_client)

    @patch('awslabs.aws_msk_mcp_server.tools.common_functions.client_manager.boto3')
    @patch('awslabs.aws_msk_mcp_server.tools.common_functions.client_manager.os')
    def test_get_client_with_aws_profile(self, mock_os, mock_boto3):
        """Test the get_client method with a custom AWS profile."""
        # Setup
        mock_os.environ.get.return_value = 'custom-profile'
        mock_session = MagicMock()
        mock_boto3.Session.return_value = mock_session
        mock_client = MagicMock()
        mock_session.client.return_value = mock_client

        # Test
        client_manager = AWSClientManager()
        region = 'us-west-2'
        service_name = 'kafka'
        result = client_manager.get_client(region, service_name)

        # Verify
        mock_os.environ.get.assert_called_once_with('AWS_PROFILE', 'default')
        mock_boto3.Session.assert_called_once_with(
            profile_name='custom-profile', region_name=region
        )
        mock_session.client.assert_called_once()

        # Check that the result is the mock client
        self.assertEqual(result, mock_client)

    @patch('awslabs.aws_msk_mcp_server.tools.common_functions.client_manager.boto3')
    def test_get_client_different_regions(self, mock_boto3):
        """Test the get_client method with different regions."""
        # Setup
        mock_session_us_west = MagicMock()
        mock_session_us_east = MagicMock()

        # Configure Session.return_value to return different sessions based on region
        def get_session_side_effect(*args, **kwargs):
            if kwargs['region_name'] == 'us-west-2':
                return mock_session_us_west
            elif kwargs['region_name'] == 'us-east-1':
                return mock_session_us_east
            return MagicMock()

        mock_boto3.Session.side_effect = get_session_side_effect

        mock_client_us_west = MagicMock()
        mock_client_us_east = MagicMock()
        mock_session_us_west.client.return_value = mock_client_us_west
        mock_session_us_east.client.return_value = mock_client_us_east

        # Test
        client_manager = AWSClientManager()
        service_name = 'kafka'

        # Get client for us-west-2
        us_west_result = client_manager.get_client('us-west-2', service_name)

        # Get client for us-east-1
        us_east_result = client_manager.get_client('us-east-1', service_name)

        # Verify
        self.assertEqual(mock_boto3.Session.call_count, 2)

        # Check that the results are the correct clients
        self.assertEqual(us_west_result, mock_client_us_west)
        self.assertEqual(us_east_result, mock_client_us_east)

        # Check that both clients were cached
        self.assertIn('kafka_us-west-2', client_manager.clients)
        self.assertEqual(client_manager.clients['kafka_us-west-2'], mock_client_us_west)
        self.assertIn('kafka_us-east-1', client_manager.clients)
        self.assertEqual(client_manager.clients['kafka_us-east-1'], mock_client_us_east)


if __name__ == '__main__':
    unittest.main()
