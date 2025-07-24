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

"""Unit tests for the read_vpc register_module."""

import unittest
from awslabs.aws_msk_mcp_server.tools.read_vpc.register_module import register_module
from unittest.mock import Mock, call, patch


class TestReadVpcRegisterModule(unittest.TestCase):
    """Tests for the read_vpc register_module."""

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
            call(name='describe_vpc_connection'),
        ]
        mock_mcp.tool.assert_has_calls(expected_tool_calls, any_order=True)
        self.assertEqual(mock_mcp.tool.call_count, len(expected_tool_calls))

    @patch('boto3.client')
    def test_describe_vpc_connection_tool(self, mock_boto3_client):
        """Test the describe_vpc_connection_tool function."""
        # Setup
        mock_mcp = Mock()
        mock_tool_decorator = Mock()
        mock_mcp.tool.return_value = mock_tool_decorator
        mock_client = Mock()
        mock_boto3_client.return_value = mock_client
        mock_client.describe_vpc_connection.return_value = {
            'VpcConnectionArn': 'test-vpc-connection-arn',
            'VpcConnectionState': 'ACTIVE',
        }

        # Register the module
        register_module(mock_mcp)

        # Get the tool function
        tool_func = mock_tool_decorator.call_args_list[0][0][0]

        # Call the tool function
        result = tool_func(region='us-west-2', vpc_connection_arn='test-vpc-connection-arn')

        # Verify boto3 client was created correctly
        mock_boto3_client.assert_called_once()
        self.assertEqual(mock_boto3_client.call_args[0][0], 'kafka')
        self.assertEqual(mock_boto3_client.call_args[1]['region_name'], 'us-west-2')
        self.assertIn('config', mock_boto3_client.call_args[1])

        # Verify describe_vpc_connection was called correctly
        mock_client.describe_vpc_connection.assert_called_once_with(
            VpcConnectionArn='test-vpc-connection-arn'
        )

        # Verify the result
        self.assertEqual(
            result,
            {
                'VpcConnectionArn': 'test-vpc-connection-arn',
                'VpcConnectionState': 'ACTIVE',
            },
        )


if __name__ == '__main__':
    unittest.main()
