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


def capture_tool_functions(mcp):
    """Capture the tool functions registered with the MCP."""
    tool_functions = {}

    # Store the original tool decorator
    original_tool = mcp.tool

    # Create a new tool decorator that captures the decorated function
    def mock_tool_decorator(**kwargs):
        def capture_function(func):
            tool_functions[kwargs.get('name')] = func
            return func

        return capture_function

    # Replace the original tool decorator with our mock
    mcp.tool = mock_tool_decorator

    # Register the module to capture the tool functions
    register_module(mcp)

    # Restore the original tool decorator
    mcp.tool = original_tool

    return tool_functions


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

        # Verify that the expected tools were registered (check call names)
        call_names = [call.kwargs.get('name') for call in mock_mcp.tool.call_args_list]
        assert 'create_vpc_connection' in call_names
        assert 'delete_vpc_connection' in call_names
        assert 'reject_client_vpc_connection' in call_names

    def test_create_vpc_connection_tool(self):
        """Test the create_vpc_connection_tool function."""
        # Arrange
        mock_mcp = MagicMock()
        tool_functions = capture_tool_functions(mock_mcp)

        # Get the create_vpc_connection_tool function
        create_vpc_connection_tool = tool_functions.get('create_vpc_connection')
        assert create_vpc_connection_tool is not None, 'create_vpc_connection_tool not found'

        # Use context managers for patching
        with (
            patch('awslabs.aws_msk_mcp_server.tools.mutate_vpc.__version__', '1.0.0'),
            patch(
                'awslabs.aws_msk_mcp_server.tools.mutate_vpc.create_vpc_connection'
            ) as mock_create_vpc_connection,
            patch('boto3.client') as mock_boto3_client,
        ):
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

            # Act
            result = create_vpc_connection_tool(
                region='us-east-1',
                cluster_arn='arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef',
                vpc_id='vpc-12345678',
                subnet_ids=['subnet-1234abcd', 'subnet-5678efgh'],
                security_groups=['sg-1234abcd'],
                authentication_type='IAM',
                client_subnets=['subnet-abcd1234'],
                tags={'Environment': 'Production'},
            )

            # Assert
            mock_boto3_client.assert_called_once()
            args, kwargs = mock_boto3_client.call_args
            assert args[0] == 'kafka'
            assert kwargs['region_name'] == 'us-east-1'
            # Don't check the config object as it's created internally

            mock_create_vpc_connection.assert_called_once_with(
                cluster_arn='arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef',
                vpc_id='vpc-12345678',
                subnet_ids=['subnet-1234abcd', 'subnet-5678efgh'],
                security_groups=['sg-1234abcd'],
                client=mock_client,
                authentication_type='IAM',
                client_subnets=['subnet-abcd1234'],
                tags={'Environment': 'Production'},
            )

            assert result == expected_response

    def test_delete_vpc_connection_tool(self):
        """Test the delete_vpc_connection_tool function."""
        # Arrange
        mock_mcp = MagicMock()
        tool_functions = capture_tool_functions(mock_mcp)

        # Get the delete_vpc_connection_tool function
        delete_vpc_connection_tool = tool_functions.get('delete_vpc_connection')
        assert delete_vpc_connection_tool is not None, 'delete_vpc_connection_tool not found'

        # Use context managers for patching
        with (
            patch('awslabs.aws_msk_mcp_server.tools.mutate_vpc.__version__', '1.0.0'),
            patch(
                'awslabs.aws_msk_mcp_server.tools.mutate_vpc.delete_vpc_connection'
            ) as mock_delete_vpc_connection,
            patch('boto3.client') as mock_boto3_client,
        ):
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

            # Act
            result = delete_vpc_connection_tool(
                region='us-east-1',
                vpc_connection_arn='arn:aws:kafka:us-east-1:123456789012:vpc-connection/test-cluster/abcdef',
            )

            # Assert
            mock_boto3_client.assert_called_once()
            args, kwargs = mock_boto3_client.call_args
            assert args[0] == 'kafka'
            assert kwargs['region_name'] == 'us-east-1'
            # Don't check the config object as it's created internally

            mock_delete_vpc_connection.assert_called_once_with(
                vpc_connection_arn='arn:aws:kafka:us-east-1:123456789012:vpc-connection/test-cluster/abcdef',
                client=mock_client,
            )

            assert result == expected_response

    def test_reject_client_vpc_connection_tool(self):
        """Test the reject_client_vpc_connection_tool function."""
        # Arrange
        mock_mcp = MagicMock()
        tool_functions = capture_tool_functions(mock_mcp)

        # Get the reject_client_vpc_connection_tool function
        reject_client_vpc_connection_tool = tool_functions.get('reject_client_vpc_connection')
        assert reject_client_vpc_connection_tool is not None, (
            'reject_client_vpc_connection_tool not found'
        )

        # Use context managers for patching
        with (
            patch('awslabs.aws_msk_mcp_server.tools.mutate_vpc.__version__', '1.0.0'),
            patch(
                'awslabs.aws_msk_mcp_server.tools.mutate_vpc.reject_client_vpc_connection'
            ) as mock_reject_client_vpc_connection,
            patch('boto3.client') as mock_boto3_client,
        ):
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

            # Act
            result = reject_client_vpc_connection_tool(
                region='us-east-1',
                cluster_arn='arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef',
                vpc_connection_arn='arn:aws:kafka:us-east-1:123456789012:vpc-connection/test-cluster/abcdef',
            )

            # Assert
            mock_boto3_client.assert_called_once()
            args, kwargs = mock_boto3_client.call_args
            assert args[0] == 'kafka'
            assert kwargs['region_name'] == 'us-east-1'
            # Don't check the config object as it's created internally

            mock_reject_client_vpc_connection.assert_called_once_with(
                cluster_arn='arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef',
                vpc_connection_arn='arn:aws:kafka:us-east-1:123456789012:vpc-connection/test-cluster/abcdef',
                client=mock_client,
            )

            assert result == expected_response
