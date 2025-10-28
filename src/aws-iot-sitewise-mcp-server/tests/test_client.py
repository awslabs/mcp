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

"""Unit tests for client.py module."""

import unittest
from awslabs.aws_iot_sitewise_mcp_server.client import (
    create_iam_client,
    create_sitewise_client,
    create_twinmaker_client,
)
from unittest.mock import Mock, patch


class TestClient(unittest.TestCase):
    """Test cases for client creation functions."""

    @patch('awslabs.aws_iot_sitewise_mcp_server.client.boto3.client')
    def test_create_sitewise_client_default_region(self, mock_boto_client):
        """Test creating SiteWise client with default region."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client

        result = create_sitewise_client()

        mock_boto_client.assert_called_once()
        args, kwargs = mock_boto_client.call_args
        self.assertEqual(args[0], 'iotsitewise')
        self.assertEqual(kwargs['region_name'], 'us-east-1')
        self.assertIn('config', kwargs)
        self.assertIn('awslabs/mcp/aws-iot-sitewise-mcp-server', kwargs['config'].user_agent_extra)
        self.assertEqual(result, mock_client)

    @patch('awslabs.aws_iot_sitewise_mcp_server.client.boto3.client')
    def test_create_sitewise_client_custom_region(self, mock_boto_client):
        """Test creating SiteWise client with custom region."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client

        result = create_sitewise_client('us-west-2')

        mock_boto_client.assert_called_once()
        args, kwargs = mock_boto_client.call_args
        self.assertEqual(args[0], 'iotsitewise')
        self.assertEqual(kwargs['region_name'], 'us-west-2')
        self.assertEqual(result, mock_client)

    @patch('awslabs.aws_iot_sitewise_mcp_server.client.boto3.client')
    def test_create_iam_client_default_region(self, mock_boto_client):
        """Test creating IAM client with default region."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client

        result = create_iam_client()

        mock_boto_client.assert_called_once()
        args, kwargs = mock_boto_client.call_args
        self.assertEqual(args[0], 'iam')
        self.assertEqual(kwargs['region_name'], 'us-east-1')
        self.assertIn('config', kwargs)
        self.assertIn('awslabs/mcp/aws-iot-sitewise-mcp-server', kwargs['config'].user_agent_extra)
        self.assertEqual(result, mock_client)

    @patch('awslabs.aws_iot_sitewise_mcp_server.client.boto3.client')
    def test_create_iam_client_custom_region(self, mock_boto_client):
        """Test creating IAM client with custom region."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client

        result = create_iam_client('eu-west-1')

        mock_boto_client.assert_called_once()
        args, kwargs = mock_boto_client.call_args
        self.assertEqual(args[0], 'iam')
        self.assertEqual(kwargs['region_name'], 'eu-west-1')
        self.assertEqual(result, mock_client)

    @patch('awslabs.aws_iot_sitewise_mcp_server.client.boto3.client')
    def test_create_twinmaker_client_default_region(self, mock_boto_client):
        """Test creating TwinMaker client with default region."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client

        result = create_twinmaker_client()

        mock_boto_client.assert_called_once()
        args, kwargs = mock_boto_client.call_args
        self.assertEqual(args[0], 'iottwinmaker')
        self.assertEqual(kwargs['region_name'], 'us-east-1')
        self.assertIn('config', kwargs)
        self.assertIn('awslabs/mcp/aws-iot-sitewise-mcp-server', kwargs['config'].user_agent_extra)
        self.assertEqual(result, mock_client)

    @patch('awslabs.aws_iot_sitewise_mcp_server.client.boto3.client')
    def test_create_twinmaker_client_custom_region(self, mock_boto_client):
        """Test creating TwinMaker client with custom region."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client

        result = create_twinmaker_client('ap-southeast-1')

        mock_boto_client.assert_called_once()
        args, kwargs = mock_boto_client.call_args
        self.assertEqual(args[0], 'iottwinmaker')
        self.assertEqual(kwargs['region_name'], 'ap-southeast-1')
        self.assertEqual(result, mock_client)


if __name__ == '__main__':
    unittest.main()
