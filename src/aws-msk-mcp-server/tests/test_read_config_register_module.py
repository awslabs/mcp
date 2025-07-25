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

"""Unit tests for the read_config register_module."""

import unittest
from awslabs.aws_msk_mcp_server.tools.read_config.register_module import register_module
from unittest.mock import Mock, call, patch


class TestReadConfigRegisterModule(unittest.TestCase):
    """Tests for the read_config register_module."""

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
            call(name='get_configuration_info'),
            call(name='list_tags_for_resource'),
        ]
        mock_mcp.tool.assert_has_calls(expected_tool_calls, any_order=True)
        self.assertEqual(mock_mcp.tool.call_count, len(expected_tool_calls))

    @patch('boto3.client')
    def test_get_configuration_info_describe(self, mock_boto3_client):
        """Test the get_configuration_info function with action='describe'."""
        # Setup
        mock_mcp = Mock()
        mock_tool_decorator = Mock()
        mock_mcp.tool.return_value = mock_tool_decorator
        mock_client = Mock()
        mock_boto3_client.return_value = mock_client
        mock_client.describe_configuration.return_value = {
            'Arn': 'test-config-arn',
            'Name': 'test-config',
        }

        # Register the module
        register_module(mock_mcp)

        # Get the tool function
        tool_func = mock_tool_decorator.call_args_list[0][0][0]

        # Call the tool function with action='describe'
        result = tool_func(region='us-west-2', action='describe', arn='test-config-arn')

        # Verify boto3 client was created correctly
        mock_boto3_client.assert_called_once()
        self.assertEqual(mock_boto3_client.call_args[0][0], 'kafka')
        self.assertEqual(mock_boto3_client.call_args[1]['region_name'], 'us-west-2')
        self.assertIn('config', mock_boto3_client.call_args[1])

        # Verify describe_configuration was called correctly
        mock_client.describe_configuration.assert_called_once_with(Arn='test-config-arn')

        # Verify the result
        self.assertEqual(result, {'Arn': 'test-config-arn', 'Name': 'test-config'})

    @patch('boto3.client')
    def test_get_configuration_info_revisions(self, mock_boto3_client):
        """Test the get_configuration_info function with action='revisions'."""
        # Setup
        mock_mcp = Mock()
        mock_tool_decorator = Mock()
        mock_mcp.tool.return_value = mock_tool_decorator
        mock_client = Mock()
        mock_boto3_client.return_value = mock_client
        mock_client.list_configuration_revisions.return_value = {
            'Revisions': [{'Revision': 1}, {'Revision': 2}]
        }

        # Register the module
        register_module(mock_mcp)

        # Get the tool function
        tool_func = mock_tool_decorator.call_args_list[0][0][0]

        # Call the tool function with action='revisions'
        result = tool_func(
            region='us-west-2',
            action='revisions',
            arn='test-config-arn',
            kwargs={'max_results': 5, 'next_token': 'token'},
        )

        # Verify boto3 client was created correctly
        mock_boto3_client.assert_called_once()
        self.assertEqual(mock_boto3_client.call_args[0][0], 'kafka')
        self.assertEqual(mock_boto3_client.call_args[1]['region_name'], 'us-west-2')
        self.assertIn('config', mock_boto3_client.call_args[1])

        # Verify list_configuration_revisions was called correctly
        mock_client.list_configuration_revisions.assert_called_once_with(
            Arn='test-config-arn', MaxResults=5, NextToken='token'
        )

        # Verify the result
        self.assertEqual(result, {'Revisions': [{'Revision': 1}, {'Revision': 2}]})

    @patch('boto3.client')
    def test_get_configuration_info_revision_details(self, mock_boto3_client):
        """Test the get_configuration_info function with action='revision_details'."""
        # Setup
        mock_mcp = Mock()
        mock_tool_decorator = Mock()
        mock_mcp.tool.return_value = mock_tool_decorator
        mock_client = Mock()
        mock_boto3_client.return_value = mock_client
        mock_client.describe_configuration_revision.return_value = {
            'Arn': 'test-config-arn',
            'Revision': 1,
            'ServerProperties': 'auto.create.topics.enable=true',
        }

        # Register the module
        register_module(mock_mcp)

        # Get the tool function
        tool_func = mock_tool_decorator.call_args_list[0][0][0]

        # Call the tool function with action='revision_details'
        result = tool_func(
            region='us-west-2',
            action='revision_details',
            arn='test-config-arn',
            kwargs={'revision': 1},
        )

        # Verify boto3 client was created correctly
        mock_boto3_client.assert_called_once()
        self.assertEqual(mock_boto3_client.call_args[0][0], 'kafka')
        self.assertEqual(mock_boto3_client.call_args[1]['region_name'], 'us-west-2')
        self.assertIn('config', mock_boto3_client.call_args[1])

        # Verify the result
        self.assertEqual(
            result,
            {
                'Arn': 'test-config-arn',
                'Revision': 1,
                'ServerProperties': 'auto.create.topics.enable=true',
            },
        )

    @patch('boto3.client')
    def test_get_configuration_info_invalid_action(self, mock_boto3_client):
        """Test the get_configuration_info function with an invalid action."""
        # Setup
        mock_mcp = Mock()
        mock_tool_decorator = Mock()
        mock_mcp.tool.return_value = mock_tool_decorator
        mock_client = Mock()
        mock_boto3_client.return_value = mock_client

        # Register the module
        register_module(mock_mcp)

        # Get the tool function
        tool_func = mock_tool_decorator.call_args_list[0][0][0]

        # Call the tool function with an invalid action
        with self.assertRaises(ValueError) as context:
            tool_func(region='us-west-2', action='invalid', arn='test-config-arn')

        # Verify the error message
        self.assertIn('Unsupported action', str(context.exception))

    @patch('boto3.client')
    def test_get_configuration_info_missing_revision(self, mock_boto3_client):
        """Test the get_configuration_info function with missing revision."""
        # Setup
        mock_mcp = Mock()
        mock_tool_decorator = Mock()
        mock_mcp.tool.return_value = mock_tool_decorator
        mock_client = Mock()
        mock_boto3_client.return_value = mock_client

        # Register the module
        register_module(mock_mcp)

        # Get the tool function
        tool_func = mock_tool_decorator.call_args_list[0][0][0]

        # Call the tool function with action='revision_details' but no revision
        with self.assertRaises(ValueError) as context:
            tool_func(
                region='us-west-2', action='revision_details', arn='test-config-arn', kwargs={}
            )

        # Verify the error message
        self.assertIn('Revision number is required', str(context.exception))

    @patch('boto3.client')
    def test_list_tags_for_resource_tool(self, mock_boto3_client):
        """Test the list_tags_for_resource_tool function."""
        # Setup
        mock_mcp = Mock()
        mock_tool_decorator = Mock()
        mock_mcp.tool.return_value = mock_tool_decorator
        mock_client = Mock()
        mock_boto3_client.return_value = mock_client
        mock_client.list_tags_for_resource.return_value = {
            'Tags': {'Name': 'test-resource', 'Environment': 'test'}
        }

        # Register the module
        register_module(mock_mcp)

        # Get the tool function
        tool_func = mock_tool_decorator.call_args_list[1][0][0]

        # Call the tool function
        result = tool_func(region='us-west-2', arn='test-resource-arn')

        # Verify boto3 client was created correctly
        mock_boto3_client.assert_called_once()
        self.assertEqual(mock_boto3_client.call_args[0][0], 'kafka')
        self.assertEqual(mock_boto3_client.call_args[1]['region_name'], 'us-west-2')
        self.assertIn('config', mock_boto3_client.call_args[1])

        # Verify list_tags_for_resource was called correctly
        mock_client.list_tags_for_resource.assert_called_once_with(ResourceArn='test-resource-arn')

        # Verify the result
        self.assertEqual(result, {'Tags': {'Name': 'test-resource', 'Environment': 'test'}})


if __name__ == '__main__':
    unittest.main()
