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

"""Tests for the elasticbeanstalk MCP Server."""

import pytest
from awslabs.elasticbeanstalk_mcp_server.errors import ClientError
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.mark.asyncio
class TestDescribeEnvironments:
    """Test class for the describe_environments function."""

    async def test_describe_environments_success(self):
        """Test that describe_environments returns the expected result on success."""
        # Arrange
        mock_ctx = AsyncMock()
        mock_client = MagicMock()
        mock_client.describe_environments.return_value = {
            'Environments': [
                {
                    'EnvironmentName': 'test-env',
                    'EnvironmentId': 'e-12345',
                    'ApplicationName': 'test-app',
                    'Status': 'Ready',
                }
            ],
            'NextToken': None,
        }

        with patch(
            'awslabs.elasticbeanstalk_mcp_server.server.get_beanstalk_client',
            return_value=mock_client,
        ):
            # Import the function inside the test
            from awslabs.elasticbeanstalk_mcp_server.server import describe_environments

            # Act
            result = await describe_environments(
                ctx=mock_ctx,
                application_name='test-app',
                environment_names=['test-env'],
                environment_ids=None,
                version_label=None,
                region_name='us-east-1',
            )

            # Assert
            assert 'Environments' in result
            assert len(result['Environments']) == 1
            assert result['Environments'][0]['EnvironmentName'] == 'test-env'
            assert result['Environments'][0]['ApplicationName'] == 'test-app'
            mock_client.describe_environments.assert_called_once()

    async def test_describe_environments_error(self):
        """Test that describe_environments handles errors correctly."""
        # Arrange
        mock_ctx = AsyncMock()
        error_message = 'Access denied'
        mock_error = ClientError(error_message)

        with patch(
            'awslabs.elasticbeanstalk_mcp_server.server.get_beanstalk_client',
            side_effect=mock_error,
        ):
            # Import the function inside the test
            from awslabs.elasticbeanstalk_mcp_server.server import describe_environments

            # Act
            result = await describe_environments(
                ctx=mock_ctx,
                application_name='test-app',
                environment_names=None,
                environment_ids=None,
                version_label=None,
                region_name='us-east-1',
            )

            # Assert - handle_exceptions decorator transforms exceptions into error dictionaries
            assert result['error'] is True
            assert error_message in result['error_message']
            # Note: The handle_exceptions decorator doesn't call ctx.error, it just returns an error dict


@pytest.mark.asyncio
class TestDescribeApplications:
    """Test class for the describe_applications function."""

    async def test_describe_applications_success(self):
        """Test that describe_applications returns the expected result on success."""
        # Arrange
        mock_ctx = AsyncMock()
        mock_client = MagicMock()
        mock_client.describe_applications.return_value = {
            'Applications': [
                {
                    'ApplicationName': 'test-app',
                    'Description': 'Test application',
                    'DateCreated': '2023-01-01T00:00:00Z',
                    'DateUpdated': '2023-01-02T00:00:00Z',
                    'Versions': ['v1', 'v2'],
                    'ConfigurationTemplates': [],
                }
            ]
        }

        with patch(
            'awslabs.elasticbeanstalk_mcp_server.server.get_beanstalk_client',
            return_value=mock_client,
        ):
            # Import the function inside the test
            from awslabs.elasticbeanstalk_mcp_server.server import describe_applications

            # Act
            result = await describe_applications(
                ctx=mock_ctx, application_names=['test-app'], region_name='us-east-1'
            )

            # Assert
            assert 'Applications' in result
            assert len(result['Applications']) == 1
            assert result['Applications'][0]['ApplicationName'] == 'test-app'
            mock_client.describe_applications.assert_called_once()

    async def test_describe_applications_error(self):
        """Test that describe_applications handles errors correctly."""
        # Arrange
        mock_ctx = AsyncMock()
        error_message = 'Resource not found'
        mock_error = ClientError(error_message)

        with patch(
            'awslabs.elasticbeanstalk_mcp_server.server.get_beanstalk_client',
            side_effect=mock_error,
        ):
            # Import the function inside the test
            from awslabs.elasticbeanstalk_mcp_server.server import describe_applications

            # Act
            result = await describe_applications(
                ctx=mock_ctx, application_names=['non-existent-app'], region_name='us-east-1'
            )

            # Assert - handle_exceptions decorator transforms exceptions into error dictionaries
            assert result['error'] is True
            assert error_message in result['error_message']
            # Note: The handle_exceptions decorator doesn't call ctx.error, it just returns an error dict


@pytest.mark.asyncio
class TestDescribeEvents:
    """Test class for the describe_events function."""

    async def test_describe_events_success(self):
        """Test that describe_events returns the expected result on success."""
        # Arrange
        mock_ctx = AsyncMock()
        mock_client = MagicMock()
        mock_client.describe_events.return_value = {
            'Events': [
                {
                    'EventDate': '2023-01-01T00:00:00Z',
                    'Message': 'Environment created',
                    'ApplicationName': 'test-app',
                    'EnvironmentName': 'test-env',
                    'Severity': 'INFO',
                }
            ],
            'NextToken': None,
        }

        with patch(
            'awslabs.elasticbeanstalk_mcp_server.server.get_beanstalk_client',
            return_value=mock_client,
        ):
            # Import the function inside the test
            from awslabs.elasticbeanstalk_mcp_server.server import describe_events

            # Act
            result = await describe_events(
                ctx=mock_ctx,
                application_name='test-app',
                environment_name='test-env',
                environment_id=None,
                start_time=None,
                end_time=None,
                max_items=None,
                severity=None,
                region_name='us-east-1',
            )

            # Assert
            assert 'Events' in result
            assert len(result['Events']) == 1
            assert result['Events'][0]['ApplicationName'] == 'test-app'
            assert result['Events'][0]['EnvironmentName'] == 'test-env'
            mock_client.describe_events.assert_called_once()

    async def test_describe_events_error(self):
        """Test that describe_events handles errors correctly."""
        # Arrange
        mock_ctx = AsyncMock()
        error_message = 'Invalid parameter'
        mock_error = ClientError(error_message)

        with patch(
            'awslabs.elasticbeanstalk_mcp_server.server.get_beanstalk_client',
            side_effect=mock_error,
        ):
            # Import the function inside the test
            from awslabs.elasticbeanstalk_mcp_server.server import describe_events

            # Act
            result = await describe_events(
                ctx=mock_ctx,
                application_name='test-app',
                environment_name='test-env',
                environment_id=None,
                start_time=None,
                end_time=None,
                max_items=None,
                severity=None,
                region_name='us-east-1',
            )

            # Assert - handle_exceptions decorator transforms exceptions into error dictionaries
            assert result['error'] is True
            assert error_message in result['error_message']
            # Note: The handle_exceptions decorator doesn't call ctx.error, it just returns an error dict


@pytest.mark.asyncio
class TestDescribeConfigurationSettings:
    """Test class for the describe_config_settings function."""

    async def test_describe_config_settings_with_environment_success(self):
        """Test that describe_config_settings returns the expected result with environment name."""
        # Arrange
        mock_ctx = AsyncMock()
        mock_client = MagicMock()
        mock_client.describe_configuration_settings.return_value = {
            'ConfigurationSettings': [
                {
                    'ApplicationName': 'test-app',
                    'EnvironmentName': 'test-env',
                    'DeploymentStatus': 'deployed',
                    'DateCreated': '2023-01-01T00:00:00Z',
                    'DateUpdated': '2023-01-02T00:00:00Z',
                    'OptionSettings': [
                        {
                            'Namespace': 'aws:elasticbeanstalk:environment',
                            'OptionName': 'EnvironmentType',
                            'Value': 'SingleInstance',
                        },
                        {
                            'Namespace': 'aws:autoscaling:launchconfiguration',
                            'OptionName': 'InstanceType',
                            'Value': 't2.micro',
                        },
                    ],
                }
            ]
        }

        with patch(
            'awslabs.elasticbeanstalk_mcp_server.server.get_beanstalk_client',
            return_value=mock_client,
        ):
            # Import the function inside the test
            from awslabs.elasticbeanstalk_mcp_server.server import describe_config_settings

            # Act
            result = await describe_config_settings(
                ctx=mock_ctx,
                application_name='test-app',
                environment_name='test-env',
                template_name=None,
                region_name='us-east-1',
            )

            # Assert
            assert 'ConfigurationSettings' in result
            assert len(result['ConfigurationSettings']) == 1
            assert result['ConfigurationSettings'][0]['ApplicationName'] == 'test-app'
            assert result['ConfigurationSettings'][0]['EnvironmentName'] == 'test-env'
            assert len(result['ConfigurationSettings'][0]['OptionSettings']) == 2
            mock_client.describe_configuration_settings.assert_called_once()

    async def test_describe_config_settings_with_template_success(self):
        """Test that describe_config_settings returns the expected result with template name."""
        # Arrange
        mock_ctx = AsyncMock()
        mock_client = MagicMock()
        mock_client.describe_configuration_settings.return_value = {
            'ConfigurationSettings': [
                {
                    'ApplicationName': 'test-app',
                    'TemplateName': 'test-template',
                    'DateCreated': '2023-01-01T00:00:00Z',
                    'DateUpdated': '2023-01-02T00:00:00Z',
                    'OptionSettings': [
                        {
                            'Namespace': 'aws:elasticbeanstalk:environment',
                            'OptionName': 'EnvironmentType',
                            'Value': 'LoadBalanced',
                        }
                    ],
                }
            ]
        }

        with patch(
            'awslabs.elasticbeanstalk_mcp_server.server.get_beanstalk_client',
            return_value=mock_client,
        ):
            # Import the function inside the test
            from awslabs.elasticbeanstalk_mcp_server.server import describe_config_settings

            # Act
            result = await describe_config_settings(
                ctx=mock_ctx,
                application_name='test-app',
                environment_name=None,
                template_name='test-template',
                region_name='us-east-1',
            )

            # Assert
            assert 'ConfigurationSettings' in result
            assert len(result['ConfigurationSettings']) == 1
            assert result['ConfigurationSettings'][0]['ApplicationName'] == 'test-app'
            assert result['ConfigurationSettings'][0]['TemplateName'] == 'test-template'
            mock_client.describe_configuration_settings.assert_called_once()

    async def test_describe_config_settings_missing_params(self):
        """Test that describe_config_settings handles missing parameters correctly."""
        # Arrange
        mock_ctx = AsyncMock()
        error_message = 'Either environment_name or template_name must be provided'

        # Import the function inside the test
        from awslabs.elasticbeanstalk_mcp_server.server import describe_config_settings

        # Mock the get_beanstalk_client function to prevent AWS credential errors
        with patch(
            'awslabs.elasticbeanstalk_mcp_server.server.get_beanstalk_client'
        ) as mock_get_client:
            # Act
            result = await describe_config_settings(
                ctx=mock_ctx,
                application_name='test-app',
                environment_name=None,
                template_name=None,
                region_name='us-east-1',
            )

            # Assert - handle_exceptions decorator transforms exceptions into error dictionaries
            assert result['error'] is True
            assert error_message in result['error_message']
            # The error is raised directly in the function before being caught by handle_exceptions
            mock_ctx.error.assert_called_once_with(error_message)

            # Verify that get_beanstalk_client was never called
            mock_get_client.assert_not_called()

    async def test_describe_config_settings_error(self):
        """Test that describe_config_settings handles errors correctly."""
        # Arrange
        mock_ctx = AsyncMock()
        error_message = 'Configuration not found'
        mock_error = ClientError(error_message)

        with patch(
            'awslabs.elasticbeanstalk_mcp_server.server.get_beanstalk_client',
            side_effect=mock_error,
        ):
            # Import the function inside the test
            from awslabs.elasticbeanstalk_mcp_server.server import describe_config_settings

            # Act
            result = await describe_config_settings(
                ctx=mock_ctx,
                application_name='test-app',
                environment_name='non-existent-env',
                template_name=None,
                region_name='us-east-1',
            )

            # Assert - handle_exceptions decorator transforms exceptions into error dictionaries
            assert result['error'] is True
            assert error_message in result['error_message']
            # Note: The handle_exceptions decorator doesn't call ctx.error, it just returns an error dict


class TestGetBeanstalkClient:
    """Test class for the get_beanstalk_client function."""

    def test_get_beanstalk_client_default(self):
        """Test that get_beanstalk_client returns the expected client with default parameters."""
        # Arrange
        mock_session = MagicMock()
        mock_client = MagicMock()
        mock_session.client.return_value = mock_client

        with patch('boto3.Session', return_value=mock_session) as mock_boto3_session:
            # Import the function inside the test
            from awslabs.elasticbeanstalk_mcp_server.server import get_beanstalk_client

            # Act
            client = get_beanstalk_client()

            # Assert
            assert client == mock_client
            mock_boto3_session.assert_called_once_with(region_name='us-east-1')
            mock_session.client.assert_called_once()
