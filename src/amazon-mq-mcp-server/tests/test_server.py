# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance
# with the License. A copy of the License is located at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES
# OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions
# and limitations under the License.
# This file is part of the awslabs namespace.
# It is intentionally minimal to support PEP 420 namespace packages.

import pytest
from unittest.mock import MagicMock, patch


with pytest.MonkeyPatch().context() as CTX:
    CTX.setattr('boto3.Session', MagicMock)
    CTX.setattr('boto3.client', MagicMock)
    from awslabs.amazon_mq_mcp_server.consts import MCP_SERVER_VERSION
    from awslabs.amazon_mq_mcp_server.server import (
        allow_mutative_action_only_on_tagged_resource,
        create_broker_override,
        create_configuration_override,
        main,
        mcp,
    )


class TestCreateBrokerOverride:
    """Tests for the create_broker_override function."""

    def test_create_broker_override_function(self):
        """Test that create_broker_override creates a tool function."""
        mock_mcp = MagicMock()
        mock_client_getter = MagicMock()
        mock_region = 'us-east-1'

        # Call the function
        create_broker_override(mock_mcp, mock_client_getter, mock_region)

        # Check that mcp.tool was called
        mock_mcp.tool.assert_called_once()

        # Get the decorator function
        decorator = mock_mcp.tool()

        # Check that the decorator was applied to a function
        assert callable(decorator)

    @patch('boto3.client')
    def test_handle_create_broker(self, mock_boto3_client):
        """Test the handle_create_broker function created by create_broker_override."""
        # Setup mock MCP
        mock_mcp = MagicMock()
        mock_tool_decorator = MagicMock()
        mock_mcp.tool.return_value = mock_tool_decorator

        # Setup mock client getter
        mock_client = MagicMock()
        mock_client_getter = MagicMock(return_value=mock_client)

        # Call create_broker_override to get the decorated function
        create_broker_override(mock_mcp, mock_client_getter, 'us-east-1')

        # Get the decorated function
        handle_create_broker = mock_tool_decorator.call_args[0][0]

        # Test parameters for the handle_create_broker function
        broker_name = 'test-broker'
        engine_type = 'RABBITMQ'
        engine_version = '3.10.20'
        host_instance_type = 'mq.t3.micro'
        deployment_mode = 'SINGLE_INSTANCE'
        publicly_accessible = False
        auto_minor_version_upgrade = True
        users = [{'Username': 'tu', 'Password': 'tp'}]  # pragma: allowlist secret
        region = 'us-west-2'

        # Call the function
        handle_create_broker(
            broker_name=broker_name,
            engine_type=engine_type,
            engine_version=engine_version,
            host_instance_type=host_instance_type,
            deployment_mode=deployment_mode,
            publicly_accessible=publicly_accessible,
            auto_minor_version_upgrade=auto_minor_version_upgrade,
            users=users,
            region=region,
        )

        # Check that the client getter was called with the correct region
        mock_client_getter.assert_called_once_with(region)

        # Check that create_broker was called with the correct parameters
        mock_client.create_broker.assert_called_once_with(
            BrokerName=broker_name,
            EngineType=engine_type,
            EngineVersion=engine_version,
            HostInstanceType=host_instance_type,
            DeploymentMode=deployment_mode,
            PubliclyAccessible=publicly_accessible,
            AutoMinorVersionUpgrade=auto_minor_version_upgrade,
            Users=users,
            Tags={'mcp_server_version': MCP_SERVER_VERSION},
        )


class TestCreateConfigurationOverride:
    """Tests for the create_configuration_override function."""

    def test_create_configuration_override_function(self):
        """Test that create_configuration_override creates a tool function."""
        mock_mcp = MagicMock()
        mock_client_getter = MagicMock()
        mock_region = 'us-east-1'

        # Call the function
        create_configuration_override(mock_mcp, mock_client_getter, mock_region)

        # Check that mcp.tool was called
        mock_mcp.tool.assert_called_once()

        # Get the decorator function
        decorator = mock_mcp.tool()

        # Check that the decorator was applied to a function
        assert callable(decorator)

    @patch('boto3.client')
    def test_handle_create_configuration(self, mock_boto3_client):
        """Test the handle_create_configuration function created by create_configuration_override."""
        # Setup mock MCP
        mock_mcp = MagicMock()
        mock_tool_decorator = MagicMock()
        mock_mcp.tool.return_value = mock_tool_decorator

        # Setup mock client getter
        mock_client = MagicMock()
        mock_client_getter = MagicMock(return_value=mock_client)

        # Call create_configuration_override to get the decorated function
        create_configuration_override(mock_mcp, mock_client_getter, 'us-east-1')

        # Get the decorated function
        handle_create_configuration = mock_tool_decorator.call_args[0][0]

        # Test parameters for the handle_create_configuration function
        region = 'us-west-2'
        authentication_strategy = 'SIMPLE'
        engine_type = 'RABBITMQ'
        engine_version = '3.10.20'
        name = 'test-configuration'

        # Call the function
        handle_create_configuration(
            region=region,
            authentication_strategy=authentication_strategy,
            engine_type=engine_type,
            engine_version=engine_version,
            name=name,
        )

        # Check that the client getter was called with the correct region
        mock_client_getter.assert_called_once_with(region)

        # Check that create_configuration was called with the correct parameters
        mock_client.create_configuration.assert_called_once_with(
            AuthenticationStrategy=authentication_strategy,
            EngineType=engine_type,
            EngineVersion=engine_version,
            Name=name,
            Tags={'mcp_server_version': MCP_SERVER_VERSION},
        )


class TestAllowMutativeActionOnlyOnTaggedResource:
    """Tests for the allow_mutative_action_only_on_tagged_resource function."""

    def test_missing_broker_id(self):
        """Test with missing broker ID."""
        mock_mcp = MagicMock()
        mock_client = MagicMock()
        kwargs = {}

        result, message = allow_mutative_action_only_on_tagged_resource(
            mock_mcp, mock_client, kwargs
        )

        assert result is False
        assert message == 'BrokerId is not passed to the tool'

    def test_empty_broker_id(self):
        """Test with empty broker ID."""
        mock_mcp = MagicMock()
        mock_client = MagicMock()
        kwargs = {'BrokerId': ''}

        result, message = allow_mutative_action_only_on_tagged_resource(
            mock_mcp, mock_client, kwargs
        )

        assert result is False
        assert message == 'BrokerId is not passed to the tool'

    def test_broker_with_mcp_tag(self):
        """Test with broker that has the mcp_server_version tag."""
        mock_mcp = MagicMock()
        mock_client = MagicMock()
        mock_client.describe_broker.return_value = {
            'Tags': {'mcp_server_version': MCP_SERVER_VERSION}
        }
        kwargs = {'BrokerId': 'test-broker-id'}

        result, message = allow_mutative_action_only_on_tagged_resource(
            mock_mcp, mock_client, kwargs
        )

        assert result is True
        assert message == ''
        mock_client.describe_broker.assert_called_once_with(BrokerId='test-broker-id')

    def test_broker_without_mcp_tag(self):
        """Test with broker that doesn't have the mcp_server_version tag."""
        mock_mcp = MagicMock()
        mock_client = MagicMock()
        mock_client.describe_broker.return_value = {'Tags': {'some-other-tag': 'value'}}
        kwargs = {'BrokerId': 'test-broker-id'}

        result, message = allow_mutative_action_only_on_tagged_resource(
            mock_mcp, mock_client, kwargs
        )

        assert result is False
        assert message == 'mutating a resource without the mcp_server_version tag is not allowed'
        mock_client.describe_broker.assert_called_once_with(BrokerId='test-broker-id')

    def test_exception_handling(self):
        """Test exception handling."""
        mock_mcp = MagicMock()
        mock_client = MagicMock()
        mock_client.describe_broker.side_effect = Exception('Test exception')
        kwargs = {'BrokerId': 'test-broker-id'}

        result, message = allow_mutative_action_only_on_tagged_resource(
            mock_mcp, mock_client, kwargs
        )

        assert result is False
        assert message == 'Test exception'
        mock_client.describe_broker.assert_called_once_with(BrokerId='test-broker-id')


class TestMain:
    """Tests for the main function."""

    @patch('boto3.Session')
    @patch('awslabs.amazon_mq_mcp_server.server.mcp')
    @patch('argparse.ArgumentParser.parse_args')
    def test_main_sse(self, mock_parse_args, mock_mcp, mock_session):
        """Test main function with SSE transport."""
        # Set up the mock
        mock_parse_args.return_value = MagicMock(sse=True, port=8888)

        # Call the function
        main()

        # Check that mcp.run was called with the correct transport
        mock_mcp.run.assert_called_once_with(transport='sse')

        # Check that mcp.settings.port was set
        assert mock_mcp.settings.port == 8888

    @patch('boto3.Session')
    @patch('awslabs.amazon_mq_mcp_server.server.mcp')
    @patch('argparse.ArgumentParser.parse_args')
    def test_main_stdio(self, mock_parse_args, mock_mcp, mock_session):
        """Test main function with stdio transport."""
        # Set up the mock
        mock_parse_args.return_value = MagicMock(sse=False, port=8888)

        # Call the function
        main()

        # Check that mcp.run was called with no transport
        mock_mcp.run.assert_called_once_with()


class TestAWSToolGenerator:
    """Tests for the AWSToolGenerator integration."""

    def test_generator_configuration(self):
        """Test that the generator is configured correctly."""
        # Instead of trying to mock the import, we'll test the actual configuration
        # that was already set up when the module was imported at the top of the test file

        # Test the MCP server configuration
        assert mcp.name == 'awslabs.amazon-mq-mcp-server'
        assert 'Manage RabbitMQ and ActiveMQ message brokers on AmazonMQ.' == mcp.instructions

        # Test that the create_broker_override function is properly defined
        # by checking if it's a callable function
        assert callable(create_broker_override)

        # Test that the validator function is properly defined
        assert callable(allow_mutative_action_only_on_tagged_resource)
