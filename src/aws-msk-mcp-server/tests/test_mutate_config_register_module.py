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

"""Unit tests for the mutate_config register_module."""

import unittest
from awslabs.aws_msk_mcp_server.tools.mutate_config.register_module import register_module
from unittest.mock import Mock, call, patch


class TestMutateConfigRegisterModule(unittest.TestCase):
    """Tests for the mutate_config register_module."""

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
            call(name='create_configuration'),
            call(name='update_configuration'),
            call(name='tag_resource'),
            call(name='untag_resource'),
        ]
        mock_mcp.tool.assert_has_calls(expected_tool_calls, any_order=True)
        self.assertEqual(mock_mcp.tool.call_count, len(expected_tool_calls))

    @patch('boto3.client')
    def test_create_configuration_tool(self, mock_boto3_client):
        """Test the create_configuration_tool function."""
        # Setup
        mock_mcp = Mock()
        mock_tool_decorator = Mock()
        mock_mcp.tool.return_value = mock_tool_decorator
        mock_client = Mock()
        mock_boto3_client.return_value = mock_client

        # Set up mock return value
        expected_result = {
            'Arn': 'arn:aws:kafka:us-west-2:123456789012:configuration/test-config/abcd1234',
            'CreationTime': '2023-01-01T12:00:00.000Z',
            'LatestRevision': {
                'CreationTime': '2023-01-01T12:00:00.000Z',
                'Description': 'Test configuration',
                'Revision': 1,
            },
            'Name': 'test-config',
        }
        mock_client.create_configuration.return_value = expected_result

        # Register the module
        register_module(mock_mcp)

        # Get the tool function (first registered tool)
        tool_func = mock_tool_decorator.call_args_list[0][0][0]

        # Test data
        region = 'us-west-2'
        name = 'test-config'
        server_properties = 'auto.create.topics.enable = true\ndelete.topic.enable = true'
        description = 'Test configuration'
        kafka_versions = ['2.8.1', '3.3.1']

        # Call the tool function
        result = tool_func(
            region=region,
            name=name,
            server_properties=server_properties,
            description=description,
            kafka_versions=kafka_versions,
        )

        # Verify boto3 client was created correctly
        mock_boto3_client.assert_called_once()
        self.assertEqual(mock_boto3_client.call_args[0][0], 'kafka')
        self.assertEqual(mock_boto3_client.call_args[1]['region_name'], region)
        self.assertIn('config', mock_boto3_client.call_args[1])

        # Verify create_configuration was called
        mock_client.create_configuration.assert_called_once()

        # Verify the result
        self.assertEqual(result, expected_result)

    @patch('boto3.client')
    def test_update_configuration_tool_success(self, mock_boto3_client):
        """Test the update_configuration_tool function with successful tag check."""
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
            'Arn': 'arn:aws:kafka:us-west-2:123456789012:configuration/test-config/abcd1234-2',
            'LatestRevision': {
                'CreationTime': '2023-01-02T12:00:00.000Z',
                'Description': 'Updated configuration',
                'Revision': 2,
            },
        }
        mock_client.update_configuration.return_value = expected_result

        # Register the module
        register_module(mock_mcp)

        # Get the tool function (second registered tool)
        tool_func = mock_tool_decorator.call_args_list[1][0][0]

        # Test data
        region = 'us-west-2'
        arn = 'arn:aws:kafka:us-west-2:123456789012:configuration/test-config/abcd1234'
        server_properties = 'auto.create.topics.enable = true\ndelete.topic.enable = true\nlog.retention.hours = 168'
        description = 'Updated configuration'

        # Call the tool function
        result = tool_func(
            region=region, arn=arn, server_properties=server_properties, description=description
        )

        # Verify boto3 client was created correctly
        mock_boto3_client.assert_called_once()
        self.assertEqual(mock_boto3_client.call_args[0][0], 'kafka')
        self.assertEqual(mock_boto3_client.call_args[1]['region_name'], region)
        self.assertIn('config', mock_boto3_client.call_args[1])

        # Verify list_tags_for_resource was called correctly (for check_mcp_generated_tag)
        mock_client.list_tags_for_resource.assert_called_once_with(ResourceArn=arn)

        # Verify update_configuration was called
        mock_client.update_configuration.assert_called_once()

        # Verify the result
        self.assertEqual(result, expected_result)

    @patch('boto3.client')
    def test_update_configuration_tool_tag_check_failure(self, mock_boto3_client):
        """Test the update_configuration_tool function with failed tag check."""
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
        arn = 'arn:aws:kafka:us-west-2:123456789012:configuration/test-config/abcd1234'
        server_properties = 'auto.create.topics.enable = true\ndelete.topic.enable = true\nlog.retention.hours = 168'
        description = 'Updated configuration'

        # Call the tool function and expect a ValueError
        with self.assertRaises(ValueError) as context:
            tool_func(
                region=region,
                arn=arn,
                server_properties=server_properties,
                description=description,
            )

        # Verify the error message
        self.assertIn("does not have the 'MCP Generated' tag", str(context.exception))

        # Verify boto3 client was created correctly
        mock_boto3_client.assert_called_once()
        self.assertEqual(mock_boto3_client.call_args[0][0], 'kafka')
        self.assertEqual(mock_boto3_client.call_args[1]['region_name'], region)
        self.assertIn('config', mock_boto3_client.call_args[1])

        # Verify list_tags_for_resource was called correctly (for check_mcp_generated_tag)
        mock_client.list_tags_for_resource.assert_called_once_with(ResourceArn=arn)

        # Verify update_configuration was NOT called
        mock_client.update_configuration.assert_not_called()

    @patch('boto3.client')
    def test_tag_resource_tool(self, mock_boto3_client):
        """Test the tag_resource_tool function."""
        # Setup
        mock_mcp = Mock()
        mock_tool_decorator = Mock()
        mock_mcp.tool.return_value = mock_tool_decorator
        mock_client = Mock()
        mock_boto3_client.return_value = mock_client

        # Set up mock return value (empty response on success)
        expected_result = {}
        mock_client.tag_resource.return_value = expected_result

        # Register the module
        register_module(mock_mcp)

        # Get the tool function (third registered tool)
        tool_func = mock_tool_decorator.call_args_list[2][0][0]

        # Test data
        region = 'us-west-2'
        resource_arn = 'arn:aws:kafka:us-west-2:123456789012:configuration/test-config/abcd1234'
        tags = {'MCP Generated': 'true', 'Environment': 'Test', 'Owner': 'TestTeam'}

        # Call the tool function
        result = tool_func(region=region, resource_arn=resource_arn, tags=tags)

        # Verify boto3 client was created correctly
        mock_boto3_client.assert_called_once()
        self.assertEqual(mock_boto3_client.call_args[0][0], 'kafka')
        self.assertEqual(mock_boto3_client.call_args[1]['region_name'], region)
        self.assertIn('config', mock_boto3_client.call_args[1])

        # Verify tag_resource was called
        mock_client.tag_resource.assert_called_once()

        # Verify the result
        self.assertEqual(result, expected_result)

    @patch('boto3.client')
    def test_untag_resource_tool(self, mock_boto3_client):
        """Test the untag_resource_tool function."""
        # Setup
        mock_mcp = Mock()
        mock_tool_decorator = Mock()
        mock_mcp.tool.return_value = mock_tool_decorator
        mock_client = Mock()
        mock_boto3_client.return_value = mock_client

        # Set up mock return value (empty response on success)
        expected_result = {}
        mock_client.untag_resource.return_value = expected_result

        # Register the module
        register_module(mock_mcp)

        # Get the tool function (fourth registered tool)
        tool_func = mock_tool_decorator.call_args_list[3][0][0]

        # Test data
        region = 'us-west-2'
        resource_arn = 'arn:aws:kafka:us-west-2:123456789012:configuration/test-config/abcd1234'
        tag_keys = ['Environment', 'Owner']

        # Call the tool function
        result = tool_func(region=region, resource_arn=resource_arn, tag_keys=tag_keys)

        # Verify boto3 client was created correctly
        mock_boto3_client.assert_called_once()
        self.assertEqual(mock_boto3_client.call_args[0][0], 'kafka')
        self.assertEqual(mock_boto3_client.call_args[1]['region_name'], region)
        self.assertIn('config', mock_boto3_client.call_args[1])

        # Verify untag_resource was called
        mock_client.untag_resource.assert_called_once()

        # Verify the result
        self.assertEqual(result, expected_result)


if __name__ == '__main__':
    unittest.main()
