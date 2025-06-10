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

"""Tests for the make_prometheus_request function."""

import pytest
import requests
import json
from unittest.mock import AsyncMock, MagicMock, patch, call
from botocore.exceptions import ClientError, NoCredentialsError


@pytest.mark.asyncio
async def test_make_prometheus_request_success():
    """Test successful request to Prometheus API."""
    with (
        patch('awslabs.prometheus_mcp_server.server.boto3.Session') as mock_session,
        patch('awslabs.prometheus_mcp_server.server.SigV4Auth') as mock_auth,
        patch('awslabs.prometheus_mcp_server.server.requests.Request') as mock_request,
        patch('awslabs.prometheus_mcp_server.server.requests.Session') as mock_requests_session,
        patch('awslabs.prometheus_mcp_server.server.config') as mock_config,
    ):
        from awslabs.prometheus_mcp_server.server import make_prometheus_request

        # Setup mocks
        mock_config.prometheus_url = 'https://aps-workspaces.us-east-1.amazonaws.com/workspaces/ws-123'
        mock_config.aws_region = 'us-east-1'
        mock_config.aws_profile = 'test-profile'
        mock_config.service_name = 'aps'
        mock_config.retry_delay = 1

        mock_session_instance = mock_session.return_value
        mock_session_instance.get_credentials.return_value = MagicMock()

        mock_auth_instance = mock_auth.return_value
        
        mock_prepared_request = MagicMock()
        mock_request.return_value.prepare.return_value = mock_prepared_request
        
        mock_response = MagicMock()
        mock_response.json.return_value = {'status': 'success', 'data': {'result': 'test_data'}}
        mock_requests_session.return_value.__enter__.return_value.send.return_value = mock_response

        # Execute
        result = await make_prometheus_request('query', {'query': 'up'}, 3)

        # Assert
        assert result == {'result': 'test_data'}
        mock_session.assert_called_once_with(
            profile_name='test-profile', region_name='us-east-1'
        )
        mock_auth.assert_called_once()
        mock_auth_instance.add_auth.assert_called_once()
        mock_request.assert_called_once()
        mock_requests_session.return_value.__enter__.return_value.send.assert_called_once_with(
            mock_prepared_request
        )


@pytest.mark.asyncio
async def test_make_prometheus_request_error_response():
    """Test handling of error response from Prometheus API."""
    with (
        patch('awslabs.prometheus_mcp_server.server.boto3.Session') as mock_session,
        patch('awslabs.prometheus_mcp_server.server.SigV4Auth') as mock_auth,
        patch('awslabs.prometheus_mcp_server.server.requests.Request') as mock_request,
        patch('awslabs.prometheus_mcp_server.server.requests.Session') as mock_requests_session,
        patch('awslabs.prometheus_mcp_server.server.config') as mock_config,
    ):
        from awslabs.prometheus_mcp_server.server import make_prometheus_request

        # Setup mocks
        mock_config.prometheus_url = 'https://aps-workspaces.us-east-1.amazonaws.com/workspaces/ws-123'
        mock_config.aws_region = 'us-east-1'
        mock_config.aws_profile = 'test-profile'
        mock_config.service_name = 'aps'
        mock_config.retry_delay = 1

        mock_session_instance = mock_session.return_value
        mock_session_instance.get_credentials.return_value = MagicMock()

        mock_prepared_request = MagicMock()
        mock_request.return_value.prepare.return_value = mock_prepared_request
        
        mock_response = MagicMock()
        mock_response.json.return_value = {'status': 'error', 'error': 'Invalid query'}
        mock_requests_session.return_value.__enter__.return_value.send.return_value = mock_response

        # Execute and assert
        with pytest.raises(RuntimeError, match='Prometheus API request failed: Invalid query'):
            await make_prometheus_request('query', {'query': 'invalid'}, 3)


@pytest.mark.asyncio
async def test_make_prometheus_request_network_error_with_retry():
    """Test retry logic when network errors occur."""
    with (
        patch('awslabs.prometheus_mcp_server.server.boto3.Session') as mock_session,
        patch('awslabs.prometheus_mcp_server.server.SigV4Auth') as mock_auth,
        patch('awslabs.prometheus_mcp_server.server.requests.Request') as mock_request,
        patch('awslabs.prometheus_mcp_server.server.requests.Session') as mock_requests_session,
        patch('awslabs.prometheus_mcp_server.server.config') as mock_config,
        patch('awslabs.prometheus_mcp_server.server.time.sleep') as mock_sleep,
    ):
        from awslabs.prometheus_mcp_server.server import make_prometheus_request

        # Setup mocks
        mock_config.prometheus_url = 'https://aps-workspaces.us-east-1.amazonaws.com/workspaces/ws-123'
        mock_config.aws_region = 'us-east-1'
        mock_config.aws_profile = 'test-profile'
        mock_config.service_name = 'aps'
        mock_config.retry_delay = 1

        mock_session_instance = mock_session.return_value
        mock_session_instance.get_credentials.return_value = MagicMock()

        mock_prepared_request = MagicMock()
        mock_request.return_value.prepare.return_value = mock_prepared_request
        
        # First call raises exception, second call succeeds
        mock_send = mock_requests_session.return_value.__enter__.return_value.send
        mock_send.side_effect = [
            requests.RequestException("Connection error"),
            MagicMock(
                json=lambda: {'status': 'success', 'data': {'result': 'test_data'}}
            )
        ]

        # Execute
        result = await make_prometheus_request('query', {'query': 'up'}, 3)

        # Assert
        assert result == {'result': 'test_data'}
        assert mock_send.call_count == 2
        mock_sleep.assert_called_once_with(1)  # Should sleep once between retries


@pytest.mark.asyncio
async def test_make_prometheus_request_max_retries_exceeded():
    """Test behavior when maximum retries are exceeded."""
    with (
        patch('awslabs.prometheus_mcp_server.server.boto3.Session') as mock_session,
        patch('awslabs.prometheus_mcp_server.server.SigV4Auth') as mock_auth,
        patch('awslabs.prometheus_mcp_server.server.requests.Request') as mock_request,
        patch('awslabs.prometheus_mcp_server.server.requests.Session') as mock_requests_session,
        patch('awslabs.prometheus_mcp_server.server.config') as mock_config,
        patch('awslabs.prometheus_mcp_server.server.time.sleep') as mock_sleep,
    ):
        from awslabs.prometheus_mcp_server.server import make_prometheus_request

        # Setup mocks
        mock_config.prometheus_url = 'https://aps-workspaces.us-east-1.amazonaws.com/workspaces/ws-123'
        mock_config.aws_region = 'us-east-1'
        mock_config.aws_profile = 'test-profile'
        mock_config.service_name = 'aps'
        mock_config.retry_delay = 1

        mock_session_instance = mock_session.return_value
        mock_session_instance.get_credentials.return_value = MagicMock()

        mock_prepared_request = MagicMock()
        mock_request.return_value.prepare.return_value = mock_prepared_request
        
        # All calls raise exception
        mock_send = mock_requests_session.return_value.__enter__.return_value.send
        exception = requests.RequestException("Connection error")
        mock_send.side_effect = [exception, exception, exception]

        # Execute and assert
        with pytest.raises(requests.RequestException, match="Connection error"):
            await make_prometheus_request('query', {'query': 'up'}, 3)
        
        assert mock_send.call_count == 3
        assert mock_sleep.call_count == 2  # Should sleep between each retry


@pytest.mark.asyncio
async def test_make_prometheus_request_no_credentials():
    """Test behavior when AWS credentials are not available."""
    with (
        patch('awslabs.prometheus_mcp_server.server.boto3.Session') as mock_session,
        patch('awslabs.prometheus_mcp_server.server.config') as mock_config,
    ):
        from awslabs.prometheus_mcp_server.server import make_prometheus_request

        # Setup mocks
        mock_config.prometheus_url = 'https://aps-workspaces.us-east-1.amazonaws.com/workspaces/ws-123'
        mock_config.aws_region = 'us-east-1'
        mock_config.aws_profile = 'test-profile'
        
        mock_session_instance = mock_session.return_value
        mock_session_instance.get_credentials.return_value = None

        # Execute and assert
        with pytest.raises(ValueError, match="AWS credentials not found"):
            await make_prometheus_request('query', {'query': 'up'}, 3)


@pytest.mark.asyncio
async def test_make_prometheus_request_no_url():
    """Test behavior when Prometheus URL is not configured."""
    with patch('awslabs.prometheus_mcp_server.server.config') as mock_config:
        from awslabs.prometheus_mcp_server.server import make_prometheus_request

        # Setup mocks
        mock_config.prometheus_url = None
        
        # Execute and assert
        with pytest.raises(ValueError, match="Prometheus URL not configured"):
            await make_prometheus_request('query', {'query': 'up'}, 3)


@pytest.mark.asyncio
async def test_make_prometheus_request_json_decode_error():
    """Test handling of JSON decode errors."""
    with (
        patch('awslabs.prometheus_mcp_server.server.boto3.Session') as mock_session,
        patch('awslabs.prometheus_mcp_server.server.SigV4Auth') as mock_auth,
        patch('awslabs.prometheus_mcp_server.server.requests.Request') as mock_request,
        patch('awslabs.prometheus_mcp_server.server.requests.Session') as mock_requests_session,
        patch('awslabs.prometheus_mcp_server.server.config') as mock_config,
    ):
        from awslabs.prometheus_mcp_server.server import make_prometheus_request

        # Setup mocks
        mock_config.prometheus_url = 'https://aps-workspaces.us-east-1.amazonaws.com/workspaces/ws-123'
        mock_config.aws_region = 'us-east-1'
        mock_config.aws_profile = 'test-profile'
        mock_config.service_name = 'aps'
        mock_config.retry_delay = 1
        mock_config.max_retries = 1

        mock_session_instance = mock_session.return_value
        mock_session_instance.get_credentials.return_value = MagicMock()

        mock_prepared_request = MagicMock()
        mock_request.return_value.prepare.return_value = mock_prepared_request
        
        mock_response = MagicMock()
        mock_response.json.side_effect = json.JSONDecodeError("Invalid JSON", "", 0)
        mock_requests_session.return_value.__enter__.return_value.send.return_value = mock_response

        # Execute and assert
        with pytest.raises(json.JSONDecodeError):
            await make_prometheus_request('query', {'query': 'up'}, 1)