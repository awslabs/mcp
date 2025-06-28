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

"""Tests to improve coverage for server.py."""

import os
import pytest
from awslabs.prometheus_mcp_server.server import (
    AWSCredentials,
    ConfigManager,
    PrometheusConnection,
    extract_workspace_id_from_url,
    get_prometheus_client,
    get_workspace_details,
)
from unittest.mock import AsyncMock, MagicMock, patch


class TestCoverageImprovement:
    """Tests to improve coverage for server.py."""

    def test_extract_workspace_id_from_url(self):
        """Test extract_workspace_id_from_url function."""
        # Test with valid URL
        url = 'https://aps-workspaces.us-east-1.amazonaws.com/workspaces/ws-12345678-abcd-1234-efgh-123456789012'
        assert extract_workspace_id_from_url(url) == 'ws-12345678-abcd-1234-efgh-123456789012'

        # Test with URL without workspace ID
        url = 'https://aps-workspaces.us-east-1.amazonaws.com/api/v1/query'
        assert extract_workspace_id_from_url(url) is None

        # Test with empty URL
        assert extract_workspace_id_from_url('') is None
        assert extract_workspace_id_from_url(None) is None

    def test_config_manager_parse_arguments(self):
        """Test ConfigManager.parse_arguments method."""
        with patch('sys.argv', ['server.py']):
            args = ConfigManager.parse_arguments()
            assert args.profile is None
            assert args.region is None
            assert args.url is None
            assert args.debug is False

        with patch(
            'sys.argv',
            [
                'server.py',
                '--profile',
                'test-profile',
                '--region',
                'us-west-2',
                '--url',
                'https://example.com',
                '--debug',
            ],
        ):
            args = ConfigManager.parse_arguments()
            assert args.profile == 'test-profile'
            assert args.region == 'us-west-2'
            assert args.url == 'https://example.com'
            assert args.debug is True

    def test_config_manager_setup_basic_config(self):
        """Test ConfigManager.setup_basic_config method."""
        # Create mock args
        args = MagicMock()
        args.debug = True
        args.region = 'us-west-2'
        args.profile = 'test-profile'
        args.url = 'https://example.com'

        with (
            patch('awslabs.prometheus_mcp_server.server.load_dotenv'),
            patch('awslabs.prometheus_mcp_server.server.logger'),
        ):
            config = ConfigManager.setup_basic_config(args)
            assert config['region'] == 'us-west-2'
            assert config['profile'] == 'test-profile'
            assert config['url'] == 'https://example.com'

        # Test with environment variables
        args = MagicMock()
        args.debug = False
        args.region = None
        args.profile = None
        args.url = None

        with (
            patch('awslabs.prometheus_mcp_server.server.load_dotenv'),
            patch('awslabs.prometheus_mcp_server.server.logger'),
            patch.dict(
                os.environ,
                {
                    'AWS_REGION': 'us-east-1',
                    'AWS_PROFILE': 'default',
                    'PROMETHEUS_URL': 'https://prometheus.example.com',
                },
            ),
        ):
            config = ConfigManager.setup_basic_config(args)
            assert config['region'] == 'us-east-1'
            assert config['profile'] == 'default'
            assert config['url'] == 'https://prometheus.example.com'

    def test_aws_credentials_validate(self):
        """Test AWSCredentials.validate method."""
        # Test with valid credentials
        mock_session = MagicMock()
        mock_credentials = MagicMock()
        mock_sts_client = MagicMock()
        mock_session.get_credentials.return_value = mock_credentials
        mock_session.client.return_value = mock_sts_client
        mock_sts_client.get_caller_identity.return_value = {
            'Arn': 'arn:aws:iam::123456789012:user/test-user'
        }

        with (
            patch('awslabs.prometheus_mcp_server.server.boto3.Session', return_value=mock_session),
            patch('awslabs.prometheus_mcp_server.server.logger'),
        ):
            assert AWSCredentials.validate('us-east-1') is True
            mock_session.client.assert_called_with('sts', config=MagicMock())

        # Test with profile
        with (
            patch('awslabs.prometheus_mcp_server.server.boto3.Session', return_value=mock_session),
            patch('awslabs.prometheus_mcp_server.server.logger'),
        ):
            assert AWSCredentials.validate('us-east-1', 'test-profile') is True
            mock_session.client.assert_called_with('sts', config=MagicMock())

        # Test with no credentials
        mock_session.get_credentials.return_value = None
        with (
            patch('awslabs.prometheus_mcp_server.server.boto3.Session', return_value=mock_session),
            patch('awslabs.prometheus_mcp_server.server.logger'),
        ):
            assert AWSCredentials.validate('us-east-1') is False

        # Test with client error
        mock_session.get_credentials.return_value = mock_credentials
        mock_sts_client.get_caller_identity.side_effect = Exception('Test error')
        with (
            patch('awslabs.prometheus_mcp_server.server.boto3.Session', return_value=mock_session),
            patch('awslabs.prometheus_mcp_server.server.logger'),
        ):
            assert AWSCredentials.validate('us-east-1') is False

    @pytest.mark.asyncio
    async def test_prometheus_connection_test_connection(self):
        """Test PrometheusConnection.test_connection method."""
        # Test successful connection
        with (
            patch(
                'awslabs.prometheus_mcp_server.server.PrometheusClient.make_request',
                new_callable=AsyncMock,
            ),
            patch('awslabs.prometheus_mcp_server.server.logger'),
        ):
            assert (
                await PrometheusConnection.test_connection('https://example.com', 'us-east-1')
                is True
            )

        # Test with client error - access denied
        mock_error = MagicMock()
        mock_error.response = {'Error': {'Code': 'AccessDeniedException'}}
        with (
            patch(
                'awslabs.prometheus_mcp_server.server.PrometheusClient.make_request',
                new_callable=AsyncMock,
                side_effect=mock_error,
            ),
            patch('awslabs.prometheus_mcp_server.server.logger'),
        ):
            assert (
                await PrometheusConnection.test_connection('https://example.com', 'us-east-1')
                is False
            )

        # Test with client error - resource not found
        mock_error.response = {'Error': {'Code': 'ResourceNotFoundException'}}
        with (
            patch(
                'awslabs.prometheus_mcp_server.server.PrometheusClient.make_request',
                new_callable=AsyncMock,
                side_effect=mock_error,
            ),
            patch('awslabs.prometheus_mcp_server.server.logger'),
        ):
            assert (
                await PrometheusConnection.test_connection('https://example.com', 'us-east-1')
                is False
            )

        # Test with client error - other error
        mock_error.response = {'Error': {'Code': 'OtherError'}}
        with (
            patch(
                'awslabs.prometheus_mcp_server.server.PrometheusClient.make_request',
                new_callable=AsyncMock,
                side_effect=mock_error,
            ),
            patch('awslabs.prometheus_mcp_server.server.logger'),
        ):
            assert (
                await PrometheusConnection.test_connection('https://example.com', 'us-east-1')
                is False
            )

        # Test with request exception
        with (
            patch(
                'awslabs.prometheus_mcp_server.server.PrometheusClient.make_request',
                new_callable=AsyncMock,
                side_effect=Exception('Test error'),
            ),
            patch('awslabs.prometheus_mcp_server.server.logger'),
        ):
            assert (
                await PrometheusConnection.test_connection('https://example.com', 'us-east-1')
                is False
            )

    def test_get_prometheus_client(self):
        """Test get_prometheus_client function."""
        mock_session = MagicMock()
        mock_client = MagicMock()
        mock_session.client.return_value = mock_client

        with patch(
            'awslabs.prometheus_mcp_server.server.boto3.Session', return_value=mock_session
        ):
            # Test with provided region and profile
            client = get_prometheus_client('us-west-2', 'test-profile')
            assert client == mock_client
            mock_session.client.assert_called_with('amp', config=MagicMock())

            # Test with environment variables
            with patch.dict(os.environ, {'AWS_REGION': 'us-east-1'}):
                client = get_prometheus_client()
                assert client == mock_client

    @pytest.mark.asyncio
    async def test_get_workspace_details(self):
        """Test get_workspace_details function."""
        mock_client = MagicMock()
        mock_client.describe_workspace.return_value = {
            'workspace': {
                'workspaceId': 'ws-12345',
                'alias': 'test-workspace',
                'status': {'statusCode': 'ACTIVE'},
                'prometheusEndpoint': 'https://example.com',
            }
        }

        with patch(
            'awslabs.prometheus_mcp_server.server.get_prometheus_client', return_value=mock_client
        ):
            # Test with valid response
            result = await get_workspace_details('ws-12345', 'us-east-1', 'test-profile')
            assert result['workspace_id'] == 'ws-12345'
            assert result['alias'] == 'test-workspace'
            assert result['status'] == 'ACTIVE'
            assert result['prometheus_url'] == 'https://example.com'
            assert result['region'] == 'us-east-1'

            # Test with missing prometheusEndpoint
            mock_client.describe_workspace.return_value = {
                'workspace': {
                    'workspaceId': 'ws-12345',
                    'alias': 'test-workspace',
                    'status': {'statusCode': 'ACTIVE'},
                }
            }
            with pytest.raises(ValueError, match='No prometheusEndpoint found'):
                await get_workspace_details('ws-12345', 'us-east-1', 'test-profile')

            # Test with exception
            mock_client.describe_workspace.side_effect = Exception('Test error')
            with pytest.raises(Exception, match='Test error'):
                await get_workspace_details('ws-12345', 'us-east-1', 'test-profile')
