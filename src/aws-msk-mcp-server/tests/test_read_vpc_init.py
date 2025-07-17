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

"""Tests for the read_vpc/__init__.py module."""

from awslabs.aws_msk_mcp_server.tools.read_vpc import register_module
from unittest.mock import MagicMock, patch


class TestReadVpcInit:
    """Tests for the read_vpc/__init__.py module."""

    def test_register_module(self):
        """Test the register_module function."""
        # Arrange
        mock_mcp = MagicMock()

        # Configure the tool decorator to capture the decorated function
        tool_functions = {}

        def mock_tool_decorator(**kwargs):
            def capture_function(func):
                tool_functions[kwargs.get('name')] = func
                return func

            return capture_function

        mock_mcp.tool.side_effect = mock_tool_decorator

        # Act
        register_module(mock_mcp)

        # Assert
        # Verify that the tool decorators were called with the expected names
        assert len(tool_functions) == 1
        assert 'describe_vpc_connection' in tool_functions

    @patch('boto3.client')
    @patch('awslabs.aws_msk_mcp_server.tools.read_vpc.describe_vpc_connection')
    @patch('awslabs.aws_msk_mcp_server.tools.read_vpc.Config')
    @patch('awslabs.aws_msk_mcp_server.tools.read_vpc.__version__', '1.0.0')
    def test_describe_vpc_connection_tool(
        self, mock_config, mock_describe_vpc_connection, mock_boto3_client
    ):
        """Test the describe_vpc_connection_tool function."""
        # Arrange
        mock_mcp = MagicMock()

        # Configure the tool decorator to capture the decorated function
        tool_functions = {}

        def mock_tool_decorator(**kwargs):
            def capture_function(func):
                tool_functions[kwargs.get('name')] = func
                return func

            return capture_function

        mock_mcp.tool.side_effect = mock_tool_decorator

        # Register the module to capture the tool functions
        register_module(mock_mcp)

        # Get the describe_vpc_connection_tool function
        describe_vpc_connection_tool = tool_functions['describe_vpc_connection']

        # Mock the boto3 client
        mock_client = MagicMock()
        mock_boto3_client.return_value = mock_client

        # Mock the Config class
        mock_config_instance = MagicMock()
        mock_config.return_value = mock_config_instance

        # Mock the describe_vpc_connection function
        expected_response = {
            'VpcConnectionArn': 'arn:aws:kafka:us-east-1:123456789012:vpc-connection/test-cluster/abcdef',
            'VpcConnectionState': 'ACTIVE',
            'ClusterArn': 'arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef',
            'Authentication': {'Sasl': {'Scram': {'Enabled': True}}},
            'CreationTime': '2025-06-20T10:00:00.000Z',
            'VpcId': 'vpc-12345678',
            'SubnetIds': ['subnet-1', 'subnet-2', 'subnet-3'],
            'SecurityGroups': ['sg-1'],
            'ClientSubnets': ['subnet-4', 'subnet-5', 'subnet-6'],
            'Tags': {'Environment': 'Test'},
        }
        mock_describe_vpc_connection.return_value = expected_response

        # Act
        vpc_connection_arn = (
            'arn:aws:kafka:us-east-1:123456789012:vpc-connection/test-cluster/abcdef'
        )

        result = describe_vpc_connection_tool(
            region='us-east-1', vpc_connection_arn=vpc_connection_arn
        )

        # Assert
        mock_config.assert_called_once_with(
            user_agent_extra='awslabs/mcp/aws-msk-mcp-server/1.0.0'
        )
        mock_boto3_client.assert_called_once_with(
            'kafka', region_name='us-east-1', config=mock_config_instance
        )
        mock_describe_vpc_connection.assert_called_once_with(vpc_connection_arn, mock_client)
        assert result == expected_response
