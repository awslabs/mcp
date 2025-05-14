"""Tests for the HTTP client module."""

import httpx
from awslabs.openapi_mcp_server.utils.http_client import (
    HttpClientFactory,
)
from unittest.mock import patch


def test_http_client_factory_create_client():
    """Test creating an HTTP client with default settings."""
    with patch('httpx.AsyncClient') as mock_client:
        # Create a client
        HttpClientFactory.create_client(base_url='https://test.api.com')

        # Check that AsyncClient was called with the right parameters
        mock_client.assert_called_once()
        call_args = mock_client.call_args[1]
        assert call_args['base_url'] == 'https://test.api.com'
        assert isinstance(call_args['timeout'], httpx.Timeout)  # Check type instead of exact value
        assert call_args['follow_redirects'] is True


def test_http_client_factory_create_client_with_custom_settings():
    """Test creating an HTTP client with custom settings."""
    with patch('httpx.AsyncClient') as mock_client:
        # Create headers and auth
        headers = {'X-API-Key': 'test-key'}
        auth = httpx.BasicAuth(username='user', password='pass')
        cookies = {'session': 'test-session'}

        # Create a client with custom settings
        HttpClientFactory.create_client(
            base_url='https://test.api.com',
            headers=headers,
            auth=auth,
            cookies=cookies,
            timeout=10.0,
            follow_redirects=False,
            max_connections=50,
            max_keepalive=25,
        )

        # Check that AsyncClient was called with the right parameters
        mock_client.assert_called_once()
        call_args = mock_client.call_args[1]
        assert call_args['base_url'] == 'https://test.api.com'
        assert call_args['headers'] == headers
        assert call_args['auth'] == auth
        assert call_args['cookies'] == cookies
        assert isinstance(call_args['timeout'], httpx.Timeout)  # Check type instead of exact value
        assert call_args['follow_redirects'] is False
        assert call_args['limits'].max_connections == 50
        assert call_args['limits'].max_keepalive_connections == 25


def test_http_client_factory_create_client_with_default_limits():
    """Test creating an HTTP client with default connection limits."""
    with patch('httpx.AsyncClient') as mock_client:
        with patch('awslabs.openapi_mcp_server.utils.http_client.HTTP_MAX_CONNECTIONS', 100):
            with patch('awslabs.openapi_mcp_server.utils.http_client.HTTP_MAX_KEEPALIVE', 20):
                # Create a client
                HttpClientFactory.create_client(base_url='https://test.api.com')

                # Check that AsyncClient was called with the right parameters
                mock_client.assert_called_once()
                call_args = mock_client.call_args[1]
                assert call_args['limits'].max_connections == 100
                assert call_args['limits'].max_keepalive_connections == 20


@patch('awslabs.openapi_mcp_server.utils.http_client.TENACITY_AVAILABLE', True)
def test_http_client_factory_with_tenacity():
    """Test HTTP client factory when tenacity is available."""
    # This test just verifies that the code path works when tenacity is available
    with patch('httpx.AsyncClient') as mock_client:
        # Create a client
        HttpClientFactory.create_client(base_url='https://test.api.com')

        # Check that AsyncClient was called
        mock_client.assert_called_once()
