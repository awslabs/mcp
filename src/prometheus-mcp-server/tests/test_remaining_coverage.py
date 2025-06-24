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

"""Tests for remaining coverage in the Prometheus MCP Server."""

import pytest
from unittest.mock import MagicMock, patch


def test_load_config_file_json_error():
    """Test loading configuration with JSON parsing error."""
    import argparse
    from awslabs.prometheus_mcp_server.server import load_config

    # Setup
    args = argparse.Namespace(
        config='config.json', profile=None, region=None, url=None, debug=False
    )

    # Execute
    with (
        patch('os.path.exists', return_value=True),
        patch('builtins.open', MagicMock()),
        patch('json.load', side_effect=ValueError('Invalid JSON')),
        patch('awslabs.prometheus_mcp_server.server.logger') as mock_logger,
        patch('awslabs.prometheus_mcp_server.server.load_dotenv'),
    ):
        config = load_config(args)

    # Assert
    mock_logger.error.assert_called_once()
    assert config['aws_profile'] is None
    assert config['prometheus_url'] is None  # Changed from '' to None to match our implementation


def test_setup_environment_non_aws_url():
    """Test setup environment with non-AWS URL."""
    from awslabs.prometheus_mcp_server.server import setup_environment

    # Setup
    config = {
        'prometheus_url': 'https://example.com/prometheus',
        'aws_region': 'us-east-1',
        'aws_profile': 'test-profile',
    }

    # Execute
    with (
        patch('awslabs.prometheus_mcp_server.server.logger') as mock_logger,
        patch('awslabs.prometheus_mcp_server.server.boto3.Session') as mock_session,
    ):
        # Setup boto3 session mock
        mock_session_instance = mock_session.return_value
        mock_credentials = MagicMock()
        mock_session_instance.get_credentials.return_value = mock_credentials

        mock_sts = MagicMock()
        mock_sts.get_caller_identity.return_value = {
            'Arn': 'arn:aws:iam::123456789012:user/test-user'
        }
        mock_session_instance.client.return_value = mock_sts

        result = setup_environment(config)

    # Assert
    assert result is True  # Non-AWS URLs are allowed with a warning
    mock_logger.warning.assert_called()
    assert any(
        "doesn't appear to be an AWS Managed Prometheus endpoint" in str(args)
        for args in mock_logger.warning.call_args_list
    )


@pytest.mark.asyncio
async def test_make_prometheus_request_retry_delay_none():
    """Test make_prometheus_request with retry_delay=None."""
    with (
        patch('awslabs.prometheus_mcp_server.server.boto3.Session') as mock_session,
        patch('awslabs.prometheus_mcp_server.server.SigV4Auth'),
        patch('awslabs.prometheus_mcp_server.server.requests.Request') as mock_request,
        patch('awslabs.prometheus_mcp_server.server.requests.Session') as mock_requests_session,
        patch('awslabs.prometheus_mcp_server.server.config') as mock_config,
        patch('awslabs.prometheus_mcp_server.server.time.sleep') as mock_sleep,
    ):
        import requests
        from awslabs.prometheus_mcp_server.server import make_prometheus_request

        # Setup mocks
        mock_config.prometheus_url = (
            'https://aps-workspaces.us-east-1.amazonaws.com/workspaces/ws-123'
        )
        mock_config.aws_region = 'us-east-1'
        mock_config.aws_profile = 'test-profile'
        mock_config.service_name = 'aps'
        mock_config.retry_delay = None  # Set retry_delay to None

        mock_session_instance = mock_session.return_value
        mock_session_instance.get_credentials.return_value = MagicMock()

        mock_prepared_request = MagicMock()
        mock_request.return_value.prepare.return_value = mock_prepared_request

        # First call raises exception, second call succeeds
        mock_send = mock_requests_session.return_value.__enter__.return_value.send
        mock_send.side_effect = [
            requests.RequestException('Connection error'),
            MagicMock(json=lambda: {'status': 'success', 'data': {'result': 'test_data'}}),
        ]

        # Execute
        result = await make_prometheus_request('query', {'query': 'up'}, 2)

        # Assert
        assert result == {'result': 'test_data'}
        assert mock_send.call_count == 2
        mock_sleep.assert_called_once_with(1)  # Should use default delay of 1
