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
"""Tests for the HTTP client utilities."""

import httpx
import pytest
from awslabs.openapi_mcp_server.utils.http_client import (
    HttpClientFactory,
    make_request,
    make_request_with_retry,
)
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.mark.asyncio
async def test_http_client_factory():
    """Test creating an HTTP client using the factory."""
    # Test with default parameters
    client = HttpClientFactory.create_client('https://example.com')
    assert isinstance(client, httpx.AsyncClient)
    assert client._base_url == httpx.URL('https://example.com')
    await client.aclose()

    # Test with auth
    auth = httpx.BasicAuth(username='test', password='test')
    client = HttpClientFactory.create_client('https://example.com', auth=auth)
    assert isinstance(client, httpx.AsyncClient)
    assert client._auth == auth
    await client.aclose()

    # Test with headers
    headers = {'X-Test': 'test'}
    client = HttpClientFactory.create_client('https://example.com', headers=headers)
    assert isinstance(client, httpx.AsyncClient)
    assert 'X-Test' in client._headers
    assert client._headers['X-Test'] == 'test'
    await client.aclose()


@pytest.mark.asyncio
@patch('httpx.AsyncClient.request')
async def test_make_request(mock_request):
    """Test making a request."""
    # Setup mock
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {'test': 'data'}
    mock_response.raise_for_status = MagicMock()
    mock_request.return_value = mock_response

    # Test with default parameters
    client = HttpClientFactory.create_client('https://example.com')
    response = await make_request(client, 'GET', '/test')
    assert response.status_code == 200
    assert response.json() == {'test': 'data'}
    mock_request.assert_called_once()
    await client.aclose()


@pytest.mark.asyncio
@patch('httpx.AsyncClient.request')
async def test_make_request_with_params(mock_request):
    """Test making a request with parameters."""
    # Setup mock
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {'test': 'data'}
    mock_response.raise_for_status = MagicMock()
    mock_request.return_value = mock_response

    # Test with parameters
    client = HttpClientFactory.create_client('https://example.com')
    params = {'param1': 'value1', 'param2': 'value2'}
    response = await make_request(client, 'GET', '/test', params=params)
    assert response.status_code == 200
    assert response.json() == {'test': 'data'}
    mock_request.assert_called_once_with('GET', '/test', params=params)
    await client.aclose()


@pytest.mark.asyncio
@patch('httpx.AsyncClient.request')
async def test_make_request_with_json(mock_request):
    """Test making a request with JSON data."""
    # Setup mock
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {'test': 'data'}
    mock_response.raise_for_status = MagicMock()
    mock_request.return_value = mock_response

    # Test with JSON data
    client = HttpClientFactory.create_client('https://example.com')
    json_data = {'key1': 'value1', 'key2': 'value2'}
    response = await make_request(client, 'POST', '/test', json=json_data)
    assert response.status_code == 200
    assert response.json() == {'test': 'data'}
    mock_request.assert_called_once_with('POST', '/test', json=json_data)
    await client.aclose()


@pytest.mark.asyncio
async def test_make_request_with_retry():
    """Test making a request with retry."""
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

    # Set USE_TENACITY to False for this test
    with patch('awslabs.openapi_mcp_server.utils.http_client.USE_TENACITY', False):
        with patch('awslabs.openapi_mcp_server.utils.http_client.TENACITY_AVAILABLE', False):
            response = await make_request_with_retry(mock_client, 'GET', '/test')

            # Verify the response
            assert response.status_code == 200
            assert response.json() == {'test': 'data'}
            mock_client.request.assert_called_once()


@pytest.mark.asyncio
async def test_make_request_with_retry_and_error():
    """Test making a request with retry when there's an error."""
    # Create a mock client
    mock_client = MagicMock()
    mock_client.request = AsyncMock()

    # Create a mock response for the successful attempt
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {'test': 'data'}
    mock_response.raise_for_status = MagicMock()

    # Set up the mock to fail first, then succeed
    mock_client.request.side_effect = [httpx.ConnectError('Connection error'), mock_response]

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
