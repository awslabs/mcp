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

"""Tests for the mutate_config/__init__.py module."""

import pytest
from awslabs.aws_msk_mcp_server.tools.mutate_config import register_module
from unittest.mock import MagicMock, patch


class TestMutateConfigInit:
    """Tests for the mutate_config/__init__.py module."""

    def test_register_module(self):
        """Test the register_module function."""
        # Arrange
        mock_mcp = MagicMock()

        # Act
        register_module(mock_mcp)

        # Assert
        # Verify that the tool decorators were called
        assert mock_mcp.tool.call_count == 4

        # Verify that the expected tools were registered
        mock_mcp.tool.assert_any_call(name='create_configuration')
        mock_mcp.tool.assert_any_call(name='update_configuration')
        mock_mcp.tool.assert_any_call(name='tag_resource')
        mock_mcp.tool.assert_any_call(name='untag_resource')

    @patch('boto3.client')
    @patch('awslabs.aws_msk_mcp_server.tools.mutate_config.create_configuration')
    def test_create_configuration_tool(self, mock_create_configuration, mock_boto3_client):
        """Test the create_configuration_tool function."""
        # Arrange
        # Create a spy that will capture the decorated functions
        decorated_functions = {}

        class MockMCP:
            @staticmethod
            def tool(name=None, **kwargs):
                def decorator(func):
                    decorated_functions[name] = func
                    return func

                return decorator

        # Register the tools with our spy
        register_module(MockMCP())

        # Get the captured function
        create_configuration_func = decorated_functions['create_configuration']
        assert create_configuration_func is not None, (
            'create_configuration tool was not registered'
        )

        # Mock the boto3 client
        mock_client = MagicMock()
        mock_boto3_client.return_value = mock_client

        # Mock the create_configuration function
        expected_response = {
            'Arn': 'arn:aws:kafka:us-east-1:123456789012:configuration/test-config/abcdef',
            'CreationTime': '2025-06-20T10:00:00.000Z',
            'LatestRevision': {
                'CreationTime': '2025-06-20T10:00:00.000Z',
                'Description': 'Initial revision',
                'Revision': 1,
            },
            'Name': 'test-config',
        }
        mock_create_configuration.return_value = expected_response

        # Act
        name = 'test-config'
        server_properties = 'auto.create.topics.enable=true\ndelete.topic.enable=true'
        description = 'Test configuration'
        kafka_versions = ['2.8.1', '3.3.1']

        result = create_configuration_func(
            region='us-east-1',
            name=name,
            server_properties=server_properties,
            description=description,
            kafka_versions=kafka_versions,
        )

        # Assert
        mock_boto3_client.assert_called_once_with('kafka', region_name='us-east-1')
        mock_create_configuration.assert_called_once_with(
            name, server_properties, mock_client, description, kafka_versions
        )
        assert result == expected_response

    @patch('boto3.client')
    @patch('awslabs.aws_msk_mcp_server.tools.common_functions.check_mcp_generated_tag')
    @patch('awslabs.aws_msk_mcp_server.tools.mutate_config.update_configuration')
    def test_update_configuration_tool_not_mcp_generated(
        self, mock_update_configuration, mock_check_mcp_generated_tag, mock_boto3_client
    ):
        """Test the update_configuration_tool function with a resource that is not MCP generated."""
        # Arrange
        # Create a spy that will capture the decorated functions
        decorated_functions = {}

        class MockMCP:
            @staticmethod
            def tool(name=None, **kwargs):
                def decorator(func):
                    decorated_functions[name] = func
                    return func

                return decorator

        # Register the tools with our spy
        register_module(MockMCP())

        # Get the captured function
        update_configuration_func = decorated_functions['update_configuration']
        assert update_configuration_func is not None, (
            'update_configuration tool was not registered'
        )

        # Mock the boto3 client
        mock_client = MagicMock()
        mock_boto3_client.return_value = mock_client

        # Mock the check_mcp_generated_tag function to return False
        mock_check_mcp_generated_tag.return_value = False

        # Act & Assert
        arn = 'arn:aws:kafka:us-east-1:123456789012:configuration/test-config/abcdef'
        server_properties = (
            'auto.create.topics.enable=true\ndelete.topic.enable=true\nlog.retention.hours=168'
        )
        description = 'Updated configuration'

        with pytest.raises(ValueError) as excinfo:
            update_configuration_func(
                region='us-east-1',
                arn=arn,
                server_properties=server_properties,
                description=description,
            )

        # Verify the error message
        assert f"Resource {arn} does not have the 'MCP Generated' tag" in str(excinfo.value)
        assert (
            "This operation can only be performed on resources tagged with 'MCP Generated'"
            in str(excinfo.value)
        )

        # Verify that the boto3 client and check_mcp_generated_tag were called, but update_configuration was not
        mock_boto3_client.assert_called_once_with('kafka', region_name='us-east-1')
        mock_update_configuration.assert_not_called()

    @patch('boto3.client')
    @patch('awslabs.aws_msk_mcp_server.tools.mutate_config.tag_resource')
    def test_tag_resource_tool(self, mock_tag_resource, mock_boto3_client):
        """Test the tag_resource_tool function."""
        # Arrange
        # Create a spy that will capture the decorated functions
        decorated_functions = {}

        class MockMCP:
            @staticmethod
            def tool(name=None, **kwargs):
                def decorator(func):
                    decorated_functions[name] = func
                    return func

                return decorator

        # Register the tools with our spy
        register_module(MockMCP())

        # Get the captured function
        tag_resource_func = decorated_functions['tag_resource']
        assert tag_resource_func is not None, 'tag_resource tool was not registered'

        # Mock the boto3 client
        mock_client = MagicMock()
        mock_boto3_client.return_value = mock_client

        # Mock the tag_resource function
        expected_response = {}
        mock_tag_resource.return_value = expected_response

        # Act
        resource_arn = 'arn:aws:kafka:us-east-1:123456789012:configuration/test-config/abcdef'
        tags = {'Environment': 'Production', 'Owner': 'DataTeam', 'MCP Generated': 'true'}

        result = tag_resource_func(region='us-east-1', resource_arn=resource_arn, tags=tags)

        # Assert
        mock_boto3_client.assert_called_once_with('kafka', region_name='us-east-1')
        mock_tag_resource.assert_called_once_with(resource_arn, tags, mock_client)
        assert result == expected_response

    @patch('boto3.client')
    @patch('awslabs.aws_msk_mcp_server.tools.mutate_config.untag_resource')
    def test_untag_resource_tool(self, mock_untag_resource, mock_boto3_client):
        """Test the untag_resource_tool function."""
        # Arrange
        # Create a spy that will capture the decorated functions
        decorated_functions = {}

        class MockMCP:
            @staticmethod
            def tool(name=None, **kwargs):
                def decorator(func):
                    decorated_functions[name] = func
                    return func

                return decorator

        # Register the tools with our spy
        register_module(MockMCP())

        # Get the captured function
        untag_resource_func = decorated_functions['untag_resource']
        assert untag_resource_func is not None, 'untag_resource tool was not registered'

        # Mock the boto3 client
        mock_client = MagicMock()
        mock_boto3_client.return_value = mock_client

        # Mock the untag_resource function
        expected_response = {}
        mock_untag_resource.return_value = expected_response

        # Act
        resource_arn = 'arn:aws:kafka:us-east-1:123456789012:configuration/test-config/abcdef'
        tag_keys = ['Environment', 'Owner']

        result = untag_resource_func(
            region='us-east-1', resource_arn=resource_arn, tag_keys=tag_keys
        )

        # Assert
        mock_boto3_client.assert_called_once_with('kafka', region_name='us-east-1')
        mock_untag_resource.assert_called_once_with(resource_arn, tag_keys, mock_client)
        assert result == expected_response
