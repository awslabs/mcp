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
"""Extended tests for the HTTP client utilities."""

import httpx
import pytest
from awslabs.openapi_mcp_server.utils.http_client import (
    HttpClientFactory,
    make_request_with_retry,
)
from unittest.mock import AsyncMock, MagicMock, patch


class MockCognitoAuth(httpx.Auth):
    """Mock Cognito auth for testing."""

    def __init__(self, token='mock_token'):
        """Initialize with a mock token."""
        self.token = token
        self.session_manager = MagicMock()
        self.session_manager.is_authenticated = MagicMock(return_value=True)
        self.session_manager.get_access_token = MagicMock(return_value=token)

    def auth_flow(self, request):
        """Auth flow required by httpx.Auth."""
        request.headers['Authorization'] = f'Bearer {self.token}'
        yield request


@pytest.mark.asyncio
async def test_http_client_factory_with_cognito_auth():
    """Test creating an HTTP client with Cognito auth."""
    # Create a mock Cognito auth
    auth = MockCognitoAuth(token='test_token_12345')

    # Test with Cognito auth
    client = HttpClientFactory.create_client('https://example.com', auth=auth)
    assert isinstance(client, httpx.AsyncClient)
    assert client._auth == auth
    await client.aclose()


@pytest.mark.asyncio
async def test_http_client_factory_with_auth_and_headers():
    """Test creating an HTTP client with auth and headers."""
    # Create a mock Cognito auth
    auth = MockCognitoAuth(token='test_token_12345')

    # Test with auth and headers
    headers = {'X-Custom': 'custom_value'}
    client = HttpClientFactory.create_client('https://example.com', auth=auth, headers=headers)
    assert isinstance(client, httpx.AsyncClient)
    assert client._auth == auth
    assert 'X-Custom' in client._headers
    assert client._headers['X-Custom'] == 'custom_value'
    await client.aclose()


@pytest.mark.asyncio
async def test_http_client_factory_with_auth_no_token():
    """Test creating an HTTP client with auth but no token."""
    # Create a mock auth with no token
    auth = MockCognitoAuth()
    auth.session_manager.get_access_token = MagicMock(return_value=None)

    # Test with auth but no token
    client = HttpClientFactory.create_client('https://example.com', auth=auth)
    assert isinstance(client, httpx.AsyncClient)
    assert client._auth == auth
    await client.aclose()


@pytest.mark.asyncio
async def test_http_client_factory_with_auth_and_existing_auth_header():
    """Test creating an HTTP client with auth and existing Authorization header."""
    # Create a mock Cognito auth
    auth = MockCognitoAuth(token='test_token_12345')

    # Test with auth and existing Authorization header
    headers = {'Authorization': 'Bearer existing_token'}
    client = HttpClientFactory.create_client('https://example.com', auth=auth, headers=headers)
    assert isinstance(client, httpx.AsyncClient)
    assert client._auth == auth
    assert 'Authorization' in client._headers
    assert (
        client._headers['Authorization'] == 'Bearer existing_token'
    )  # Header should not be overwritten
    await client.aclose()


@pytest.mark.asyncio
async def test_http_client_factory_with_custom_limits():
    """Test creating an HTTP client with custom connection limits."""
    # Simply verify the client is created successfully with custom limits
    client = HttpClientFactory.create_client(
        'https://example.com', max_connections=50, max_keepalive=25
    )

    # Verify client was created
    assert isinstance(client, httpx.AsyncClient)

    # Close the client
    await client.aclose()


@pytest.mark.asyncio
async def test_make_request_with_retry_max_attempts():
    """Test making a request with retry that fails all attempts."""
    # Create a mock client
    mock_client = MagicMock()
    mock_client.request = AsyncMock()

    # Set up the mock to always fail with a connection error
    mock_client.request.side_effect = httpx.ConnectError('Connection error')

    # Set USE_TENACITY to False and patch asyncio.sleep to avoid actual delays
    with patch('awslabs.openapi_mcp_server.utils.http_client.USE_TENACITY', False):
        with patch('awslabs.openapi_mcp_server.utils.http_client.TENACITY_AVAILABLE', False):
            with patch('asyncio.sleep', AsyncMock()) as mock_sleep:
                # Should raise after max_retries attempts
                with pytest.raises(httpx.ConnectError):
                    await make_request_with_retry(mock_client, 'GET', '/test', max_retries=3)

                # Verify the request was called max_retries times
                assert mock_client.request.call_count == 3
                # Sleep should be called max_retries - 1 times
                assert mock_sleep.call_count == 2


@pytest.mark.asyncio
async def test_make_request_with_retry_http_status_error():
    """Test making a request with retry that fails with an HTTP status error."""
    # Create a mock client
    mock_client = MagicMock()
    mock_client.request = AsyncMock()

    # Create a mock response for the failed attempt
    mock_response = MagicMock()
    mock_response.status_code = 404
    mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        '404 Not Found', request=MagicMock(), response=mock_response
    )

    # Set up the mock to fail with an HTTP status error
    mock_client.request.return_value = mock_response

    # Set USE_TENACITY to False and patch asyncio.sleep to avoid actual delays
    with patch('awslabs.openapi_mcp_server.utils.http_client.USE_TENACITY', False):
        with patch('awslabs.openapi_mcp_server.utils.http_client.TENACITY_AVAILABLE', False):
            with patch('asyncio.sleep', AsyncMock()) as mock_sleep:
                # Should raise immediately for HTTP status errors (no retry)
                with pytest.raises(httpx.HTTPStatusError):
                    await make_request_with_retry(mock_client, 'GET', '/test', max_retries=3)

                # Verify the request was called only once
                mock_client.request.assert_called_once()
                # Sleep should not be called
                mock_sleep.assert_not_called()


@pytest.mark.asyncio
async def test_make_request_with_retry_timeout_error():
    """Test making a request with retry that fails with a timeout error."""
    # Create a mock client
    mock_client = MagicMock()
    mock_client.request = AsyncMock()

    # Create a mock response for the successful attempt
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {'test': 'data'}
    mock_response.raise_for_status = MagicMock()

    # Set up the mock to fail with a timeout error, then succeed
    mock_client.request.side_effect = [httpx.TimeoutException('Timeout error'), mock_response]

    # Set USE_TENACITY to False and patch asyncio.sleep to avoid actual delays
    with patch('awslabs.openapi_mcp_server.utils.http_client.USE_TENACITY', False):
        with patch('awslabs.openapi_mcp_server.utils.http_client.TENACITY_AVAILABLE', False):
            with patch('asyncio.sleep', AsyncMock()) as mock_sleep:
                response = await make_request_with_retry(mock_client, 'GET', '/test', max_retries=2)

                # Verify the response
                assert response.status_code == 200
                assert response.json() == {'test': 'data'}
                assert mock_client.request.call_count == 2
                mock_sleep.assert_called_once()


@pytest.mark.asyncio
async def test_tenacity_retry_if_available():
    """Test that tenacity is used for retries if available."""
    # Create a mock client
    mock_client = MagicMock()
    mock_client.request = AsyncMock()

    # Create a mock response
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {'test': 'data'}
    mock_response.raise_for_status = MagicMock()

    # Set up the mock to return our response
    mock_client.request.return_value = mock_response

    # Create a real async function that we can await
    async def mock_make_request():
        return mock_response

    # Mock tenacity to test if it's used
    mock_tenacity = MagicMock()
    mock_retry = MagicMock()
    # Make the decorator return our async function
    mock_retry.side_effect = lambda f: mock_make_request
    mock_tenacity.retry.return_value = mock_retry

    # Set USE_TENACITY to True and mock tenacity
    with patch('awslabs.openapi_mcp_server.utils.http_client.USE_TENACITY', True):
        with patch('awslabs.openapi_mcp_server.utils.http_client.TENACITY_AVAILABLE', True):
            with patch('awslabs.openapi_mcp_server.utils.http_client.tenacity', mock_tenacity):
                # Mock api_call_timer decorator to return our async function
                with patch(
                    'awslabs.openapi_mcp_server.utils.http_client.api_call_timer',
                    lambda f: mock_make_request,
                ):
                    response = await make_request_with_retry(mock_client, 'GET', '/test')

                    # Verify the response
                    assert response.status_code == 200
                    assert response.json() == {'test': 'data'}
                    # Verify tenacity was used
                    mock_tenacity.retry.assert_called_once()
