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

"""Unit tests for the mutate_vpc register_module."""

import unittest
from awslabs.aws_msk_mcp_server.tools.mutate_vpc.register_module import register_module
from unittest.mock import Mock, call, patch


class TestMutateVpcRegisterModule(unittest.TestCase):
    """Tests for the mutate_vpc register_module."""

    def test_register_module(self):
        """Test that register_module registers the expected tools."""
        # Setup
        mock_mcp = Mock()
        mock_tool = Mock()
        mock_mcp.tool.return_value = mock_tool

        # Call the function
        register_module(mock_mcp)

        # Verify the correct tools were registered
        expected_tool_calls = [
            call(name='create_vpc_connection'),
            call(name='delete_vpc_connection'),
            call(name='reject_client_vpc_connection'),
        ]
        mock_mcp.tool.assert_has_calls(expected_tool_calls, any_order=True)
        self.assertEqual(mock_mcp.tool.call_count, len(expected_tool_calls))

    @patch('boto3.client')
    def test_create_vpc_connection_tool(self, mock_boto3_client):
        """Test the create_vpc_connection_tool function."""
        # Setup
        mock_mcp = Mock()
        mock_tool_decorator = Mock()
        mock_mcp.tool.return_value = mock_tool_decorator
        mock_client = Mock()
        mock_boto3_client.return_value = mock_client

        # Set up mock return value
        expected_result = {
            'VpcConnectionArn': 'arn:aws:kafka:us-west-2:123456789012:vpc-connection/test-connection',
            'VpcConnectionState': 'CREATING',
            'ClusterArn': 'arn:aws:kafka:us-west-2:123456789012:cluster/test-cluster',
            'VpcId': 'vpc-12345',
        }
        mock_client.create_vpc_connection.return_value = expected_result

        # Register the module
        register_module(mock_mcp)

        # Get the tool function (first registered tool)
        tool_func = mock_tool_decorator.call_args_list[0][0][0]

        # Test data
        region = 'us-west-2'
        cluster_arn = 'arn:aws:kafka:us-west-2:123456789012:cluster/test-cluster'
        vpc_id = 'vpc-12345'
        subnet_ids = ['subnet-12345', 'subnet-67890']
        security_groups = ['sg-12345', 'sg-67890']

        # Optional parameters
        authentication_type = 'IAM'
        client_subnets = ['subnet-abcde', 'subnet-fghij']
        tags = {'Environment': 'Test', 'Owner': 'TestTeam'}

        # Call the tool function
        result = tool_func(
            region=region,
            cluster_arn=cluster_arn,
            vpc_id=vpc_id,
            subnet_ids=subnet_ids,
            security_groups=security_groups,
            authentication_type=authentication_type,
            client_subnets=client_subnets,
            tags=tags,
        )

        # Verify boto3 client was created correctly
        mock_boto3_client.assert_called_once()
        self.assertEqual(mock_boto3_client.call_args[0][0], 'kafka')
        self.assertEqual(mock_boto3_client.call_args[1]['region_name'], region)
        self.assertIn('config', mock_boto3_client.call_args[1])

        # Verify create_vpc_connection was called
        mock_client.create_vpc_connection.assert_called_once()

        # Verify the result
        self.assertEqual(result, expected_result)

    @patch('boto3.client')
    def test_delete_vpc_connection_tool_success(self, mock_boto3_client):
        """Test the delete_vpc_connection_tool function with successful tag check."""
        # Setup
        mock_mcp = Mock()
        mock_tool_decorator = Mock()
        mock_mcp.tool.return_value = mock_tool_decorator
        mock_client = Mock()
        mock_boto3_client.return_value = mock_client

        # Set up the mock return value for list_tags_for_resource (used by check_mcp_generated_tag)
        mock_client.list_tags_for_resource.return_value = {'Tags': {'MCP Generated': 'true'}}

        # Set up mock return value
        expected_result = {
            'VpcConnectionArn': 'arn:aws:kafka:us-west-2:123456789012:vpc-connection/test-connection',
            'VpcConnectionState': 'DELETING',
            'ClusterArn': 'arn:aws:kafka:us-west-2:123456789012:cluster/test-cluster',
        }
        mock_client.delete_vpc_connection.return_value = expected_result

        # Register the module
        register_module(mock_mcp)

        # Get the tool function (second registered tool)
        tool_func = mock_tool_decorator.call_args_list[1][0][0]

        # Test data
        region = 'us-west-2'
        vpc_connection_arn = 'arn:aws:kafka:us-west-2:123456789012:vpc-connection/test-connection'

        # Call the tool function
        result = tool_func(region=region, vpc_connection_arn=vpc_connection_arn)

        # Verify boto3 client was created correctly
        mock_boto3_client.assert_called_once()
        self.assertEqual(mock_boto3_client.call_args[0][0], 'kafka')
        self.assertEqual(mock_boto3_client.call_args[1]['region_name'], region)
        self.assertIn('config', mock_boto3_client.call_args[1])

        # Verify list_tags_for_resource was called correctly (for check_mcp_generated_tag)
        mock_client.list_tags_for_resource.assert_called_once_with(ResourceArn=vpc_connection_arn)

        # Verify delete_vpc_connection was called
        mock_client.delete_vpc_connection.assert_called_once()

        # Verify the result
        self.assertEqual(result, expected_result)

    @patch('boto3.client')
    def test_delete_vpc_connection_tool_tag_check_failure(self, mock_boto3_client):
        """Test the delete_vpc_connection_tool function with failed tag check."""
        # Setup
        mock_mcp = Mock()
        mock_tool_decorator = Mock()
        mock_mcp.tool.return_value = mock_tool_decorator
        mock_client = Mock()
        mock_boto3_client.return_value = mock_client

        # Set up the mock return value for list_tags_for_resource (used by check_mcp_generated_tag)
        # Missing the "MCP Generated" tag
        mock_client.list_tags_for_resource.return_value = {'Tags': {'SomeOtherTag': 'value'}}

        # Register the module
        register_module(mock_mcp)

        # Get the tool function (second registered tool)
        tool_func = mock_tool_decorator.call_args_list[1][0][0]

        # Test data
        region = 'us-west-2'
        vpc_connection_arn = 'arn:aws:kafka:us-west-2:123456789012:vpc-connection/test-connection'

        # Call the tool function and expect a ValueError
        with self.assertRaises(ValueError) as context:
            tool_func(region=region, vpc_connection_arn=vpc_connection_arn)

        # Verify the error message
        self.assertIn("does not have the 'MCP Generated' tag", str(context.exception))

        # Verify boto3 client was created correctly
        mock_boto3_client.assert_called_once()
        self.assertEqual(mock_boto3_client.call_args[0][0], 'kafka')
        self.assertEqual(mock_boto3_client.call_args[1]['region_name'], region)
        self.assertIn('config', mock_boto3_client.call_args[1])

        # Verify list_tags_for_resource was called correctly (for check_mcp_generated_tag)
        mock_client.list_tags_for_resource.assert_called_once_with(ResourceArn=vpc_connection_arn)

        # Verify delete_vpc_connection was NOT called
        mock_client.delete_vpc_connection.assert_not_called()

    @patch('boto3.client')
    def test_reject_client_vpc_connection_tool(self, mock_boto3_client):
        """Test the reject_client_vpc_connection_tool function."""
        # Setup
        mock_mcp = Mock()
        mock_tool_decorator = Mock()
        mock_mcp.tool.return_value = mock_tool_decorator
        mock_client = Mock()
        mock_boto3_client.return_value = mock_client

        # Set up mock return value
        expected_result = {
            'VpcConnectionArn': 'arn:aws:kafka:us-west-2:123456789012:vpc-connection/test-connection',
            'VpcConnectionState': 'REJECTED',
            'ClusterArn': 'arn:aws:kafka:us-west-2:123456789012:cluster/test-cluster',
        }
        mock_client.reject_client_vpc_connection.return_value = expected_result

        # Register the module
        register_module(mock_mcp)

        # Get the tool function (third registered tool)
        tool_func = mock_tool_decorator.call_args_list[2][0][0]

        # Test data
        region = 'us-west-2'
        cluster_arn = 'arn:aws:kafka:us-west-2:123456789012:cluster/test-cluster'
        vpc_connection_arn = 'arn:aws:kafka:us-west-2:123456789012:vpc-connection/test-connection'

        # Call the tool function
        result = tool_func(
            region=region, cluster_arn=cluster_arn, vpc_connection_arn=vpc_connection_arn
        )

        # Verify boto3 client was created correctly
        mock_boto3_client.assert_called_once()
        self.assertEqual(mock_boto3_client.call_args[0][0], 'kafka')
        self.assertEqual(mock_boto3_client.call_args[1]['region_name'], region)
        self.assertIn('config', mock_boto3_client.call_args[1])

        # Verify reject_client_vpc_connection was called
        mock_client.reject_client_vpc_connection.assert_called_once()

        # Verify the result
        self.assertEqual(result, expected_result)


if __name__ == '__main__':
    unittest.main()
