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

"""Additional tests for the elasticbeanstalk MCP Server."""

import pytest
import sys
from awslabs.elasticbeanstalk_mcp_server.errors import ClientError
from unittest.mock import AsyncMock, MagicMock, patch


class TestGetBeanstalkClientAdditional:
    """Additional test class for the get_beanstalk_client function."""

    def test_get_beanstalk_client_with_region(self):
        """Test that get_beanstalk_client returns the expected client with a specified region."""
        # Arrange
        mock_session = MagicMock()
        mock_client = MagicMock()
        mock_session.client.return_value = mock_client
        region_name = 'us-west-2'

        with patch('boto3.Session', return_value=mock_session) as mock_boto3_session:
            # Import the function inside the test
            from awslabs.elasticbeanstalk_mcp_server.server import get_beanstalk_client

            # Act
            client = get_beanstalk_client(region_name)

            # Assert
            assert client == mock_client
            mock_boto3_session.assert_called_once_with(region_name=region_name)
            mock_session.client.assert_called_once()

    def test_get_beanstalk_client_error(self):
        """Test that get_beanstalk_client handles errors correctly."""
        # Arrange
        mock_session = MagicMock()
        mock_error = Exception('Failed to create client')
        mock_session.client.side_effect = mock_error

        with (
            patch('boto3.Session', return_value=mock_session),
            patch(
                'awslabs.elasticbeanstalk_mcp_server.server.handle_aws_api_error',
                return_value=ClientError('Access denied'),
            ) as mock_handle_error,
        ):
            # Import the function inside the test
            from awslabs.elasticbeanstalk_mcp_server.server import get_beanstalk_client

            # Act & Assert
            with pytest.raises(ClientError) as excinfo:
                get_beanstalk_client()

            assert 'Access denied' in str(excinfo.value)
            mock_handle_error.assert_called_once_with(mock_error)


@pytest.mark.asyncio
class TestDescribeEnvironmentsAdditional:
    """Additional test class for the describe_environments function."""

    async def test_describe_environments_with_version_label(self):
        """Test that describe_environments handles version_label parameter correctly."""
        # Arrange
        mock_ctx = AsyncMock()
        mock_client = MagicMock()
        mock_client.describe_environments.return_value = {
            'Environments': [
                {
                    'EnvironmentName': 'test-env',
                    'EnvironmentId': 'e-12345',
                    'ApplicationName': 'test-app',
                    'VersionLabel': 'v1',
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
                environment_names=None,
                environment_ids=None,
                version_label='v1',
                region_name='us-east-1',
            )

            # Assert
            assert 'Environments' in result
            assert len(result['Environments']) == 1
            assert result['Environments'][0]['VersionLabel'] == 'v1'
            mock_client.describe_environments.assert_called_once_with(
                ApplicationName='test-app', VersionLabel='v1'
            )


@pytest.mark.asyncio
class TestDescribeEventsAdditional:
    """Additional test class for the describe_events function."""

    async def test_describe_events_with_all_parameters(self):
        """Test that describe_events handles all parameters correctly."""
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
            'NextToken': 'next-token',
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
                environment_id='e-12345',
                start_time='2023-01-01T00:00:00Z',
                end_time='2023-01-02T00:00:00Z',
                max_items=10,
                severity='INFO',
                region_name='us-east-1',
            )

            # Assert
            assert 'Events' in result
            assert len(result['Events']) == 1
            assert result['NextToken'] == 'next-token'
            mock_client.describe_events.assert_called_once_with(
                ApplicationName='test-app',
                EnvironmentName='test-env',
                EnvironmentId='e-12345',
                StartTime='2023-01-01T00:00:00Z',
                EndTime='2023-01-02T00:00:00Z',
                MaxRecords=10,
                Severity='INFO',
            )

    async def test_describe_events_with_no_parameters(self):
        """Test that describe_events handles minimal parameters correctly."""
        # Arrange
        mock_ctx = AsyncMock()
        mock_client = MagicMock()
        mock_client.describe_events.return_value = {
            'Events': [],
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
                application_name=None,
                environment_name=None,
                environment_id=None,
                start_time=None,
                end_time=None,
                max_items=None,
                severity=None,
                region_name='us-east-1',
            )

            # Assert
            assert 'Events' in result
            assert len(result['Events']) == 0
            assert result['NextToken'] is None
            mock_client.describe_events.assert_called_once_with()


@pytest.mark.asyncio
class TestDescribeConfigSettingsAdditional:
    """Additional test class for the describe_config_settings function."""

    async def test_describe_config_settings_with_template_name(self):
        """Test that describe_config_settings works with template_name."""
        # Arrange
        mock_ctx = AsyncMock()
        mock_client = MagicMock()
        mock_client.describe_configuration_settings.return_value = {
            'ConfigurationSettings': [
                {
                    'ApplicationName': 'test-app',
                    'TemplateName': 'test-template',
                    'OptionSettings': [],
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
            assert result['ConfigurationSettings'][0]['TemplateName'] == 'test-template'
            mock_client.describe_configuration_settings.assert_called_once_with(
                ApplicationName='test-app', TemplateName='test-template'
            )


class TestMainFunction:
    """Test class for the main function."""

    def test_main_function(self):
        """Test that the main function initializes the server correctly."""
        # Arrange
        mock_args = MagicMock()
        mock_args.readonly = True
        mock_parser = MagicMock()
        mock_parser.parse_args.return_value = mock_args

        with (
            patch('argparse.ArgumentParser', return_value=mock_parser) as mock_arg_parser,
            patch(
                'awslabs.elasticbeanstalk_mcp_server.context.Context.initialize'
            ) as mock_context_init,
            patch('awslabs.elasticbeanstalk_mcp_server.server.mcp.run') as mock_run,
        ):
            # Import the function inside the test
            from awslabs.elasticbeanstalk_mcp_server.server import main

            # Act
            main()

            # Assert
            mock_arg_parser.assert_called_once()
            mock_parser.add_argument.assert_called_with(
                '--readonly',
                type=bool,
                default=False,
                help='Run in read-only mode',
            )
            mock_context_init.assert_called_once_with(readonly_mode=True)
            mock_run.assert_called_once()

    def test_main_function_with_sys_argv(self):
        """Test that the main function handles sys.argv correctly."""
        # Arrange
        original_argv = sys.argv
        sys.argv = ['server.py', '--readonly', 'True']

        with (
            patch(
                'awslabs.elasticbeanstalk_mcp_server.context.Context.initialize'
            ) as mock_context_init,
            patch('awslabs.elasticbeanstalk_mcp_server.server.mcp.run') as mock_run,
        ):
            # Import the function inside the test
            from awslabs.elasticbeanstalk_mcp_server.server import main

            # Act
            main()

            # Assert
            mock_context_init.assert_called_once()
            mock_run.assert_called_once()

        # Restore original sys.argv
        sys.argv = original_argv
