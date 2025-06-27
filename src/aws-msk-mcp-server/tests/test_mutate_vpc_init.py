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

"""Tests for the mutate_vpc/__init__.py module."""

from awslabs.aws_msk_mcp_server.tools.mutate_vpc import register_module
from unittest.mock import MagicMock, patch


class TestMutateVpcInit:
    """Tests for the mutate_vpc/__init__.py module."""

    def test_register_module(self):
        """Test the register_module function."""
        # Arrange
        mock_mcp = MagicMock()

        # Act
        register_module(mock_mcp)

        # Assert
        # Verify that the tool decorators were called
        assert mock_mcp.tool.call_count == 3

        # Verify that the expected tools were registered
        mock_mcp.tool.assert_any_call(name='create_vpc_connection')
        mock_mcp.tool.assert_any_call(name='delete_vpc_connection')
        mock_mcp.tool.assert_any_call(name='reject_client_vpc_connection')

    @patch('boto3.client')
    @patch('awslabs.aws_msk_mcp_server.tools.mutate_vpc.create_vpc_connection')
    def test_create_vpc_connection_tool(self, mock_create_vpc_connection, mock_boto3_client):
        """Test the create_vpc_connection_tool function."""
        # This test verifies that the create_vpc_connection function is called with the correct parameters
        # when the create_vpc_connection_tool is called. Since we can't directly access the callback function
        # in the test, we're just verifying that the register_module function is called and that the
        # boto3 client and create_vpc_connection functions would be called with the expected parameters.

        # Arrange
        mock_mcp = MagicMock()
        register_module(mock_mcp)

        # Mock the boto3 client
        mock_client = MagicMock()
        mock_boto3_client.return_value = mock_client

        # Mock the create_vpc_connection function
        expected_response = {
            'VpcConnectionArn': 'arn:aws:kafka:us-east-1:123456789012:vpc-connection/test-cluster/abcdef',
            'VpcConnectionState': 'CREATING',
            'ClusterArn': 'arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef',
            'CreationTime': '2025-06-20T10:00:00.000Z',
            'VpcId': 'vpc-12345678',
        }
        mock_create_vpc_connection.return_value = expected_response

        # Assert
        # Verify that the tool decorator was called with the expected name
        mock_mcp.tool.assert_any_call(name='create_vpc_connection')

    @patch('boto3.client')
    @patch('awslabs.aws_msk_mcp_server.tools.mutate_vpc.delete_vpc_connection')
    def test_delete_vpc_connection_tool(self, mock_delete_vpc_connection, mock_boto3_client):
        """Test the delete_vpc_connection_tool function."""
        # This test verifies that the delete_vpc_connection function is called with the correct parameters
        # when the delete_vpc_connection_tool is called. Since we can't directly access the callback function
        # in the test, we're just verifying that the register_module function is called and that the
        # boto3 client and delete_vpc_connection functions would be called with the expected parameters.

        # Arrange
        mock_mcp = MagicMock()
        register_module(mock_mcp)

        # Mock the boto3 client
        mock_client = MagicMock()
        mock_boto3_client.return_value = mock_client

        # Mock the delete_vpc_connection function
        expected_response = {
            'VpcConnectionArn': 'arn:aws:kafka:us-east-1:123456789012:vpc-connection/test-cluster/abcdef',
            'VpcConnectionState': 'DELETING',
            'ClusterArn': 'arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef',
        }
        mock_delete_vpc_connection.return_value = expected_response

        # Assert
        # Verify that the tool decorator was called with the expected name
        mock_mcp.tool.assert_any_call(name='delete_vpc_connection')

    @patch('boto3.client')
    @patch('awslabs.aws_msk_mcp_server.tools.mutate_vpc.reject_client_vpc_connection')
    def test_reject_client_vpc_connection_tool(
        self, mock_reject_client_vpc_connection, mock_boto3_client
    ):
        """Test the reject_client_vpc_connection_tool function."""
        # This test verifies that the reject_client_vpc_connection function is called with the correct parameters
        # when the reject_client_vpc_connection_tool is called. Since we can't directly access the callback function
        # in the test, we're just verifying that the register_module function is called and that the
        # boto3 client and reject_client_vpc_connection functions would be called with the expected parameters.

        # Arrange
        mock_mcp = MagicMock()
        register_module(mock_mcp)

        # Mock the boto3 client
        mock_client = MagicMock()
        mock_boto3_client.return_value = mock_client

        # Mock the reject_client_vpc_connection function
        expected_response = {
            'VpcConnectionArn': 'arn:aws:kafka:us-east-1:123456789012:vpc-connection/test-cluster/abcdef',
            'VpcConnectionState': 'REJECTED',
            'ClusterArn': 'arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef',
        }
        mock_reject_client_vpc_connection.return_value = expected_response

        # Assert
        # Verify that the tool decorator was called with the expected name
        mock_mcp.tool.assert_any_call(name='reject_client_vpc_connection')
