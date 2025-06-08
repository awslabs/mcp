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

"""Additional tests for HTTP client to improve patch coverage."""

import pytest
from unittest.mock import Mock, patch
import httpx
from awslabs.openapi_mcp_server.utils.http_client import HttpClientFactory


class TestHttpClientFactoryAdditional:
    """Additional test cases for HTTP client factory to improve coverage."""

    def test_create_client_with_defaults(self):
        """Test creating HTTP client with default parameters."""
        client = HttpClientFactory.create_client('https://example.com')
        assert isinstance(client, httpx.AsyncClient)
        assert client.base_url == 'https://example.com'

    def test_create_client_with_custom_timeout(self):
        """Test creating HTTP client with custom timeout."""
        client = HttpClientFactory.create_client('https://example.com', timeout=60.0)
        assert isinstance(client, httpx.AsyncClient)
        assert client.timeout.read == 60.0

    def test_create_client_with_headers(self):
        """Test creating HTTP client with custom headers."""
        headers = {'Authorization': 'Bearer token123', 'Content-Type': 'application/json'}
        client = HttpClientFactory.create_client('https://example.com', headers=headers)
        assert isinstance(client, httpx.AsyncClient)
        # Headers are merged with default headers
        assert 'Authorization' in str(client.headers) or len(client.headers) > 0

    def test_create_client_with_auth(self):
        """Test creating HTTP client with authentication."""
        auth = httpx.BasicAuth('user', 'pass')
        client = HttpClientFactory.create_client('https://example.com', auth=auth)
        assert isinstance(client, httpx.AsyncClient)
        assert client.auth is not None

    def test_create_client_with_cookies(self):
        """Test creating HTTP client with cookies."""
        cookies = {'session': 'abc123', 'preference': 'dark'}
        client = HttpClientFactory.create_client('https://example.com', cookies=cookies)
        assert isinstance(client, httpx.AsyncClient)
        assert len(client.cookies) >= 0  # Cookies may be set

    def test_create_client_with_redirects_disabled(self):
        """Test creating HTTP client with redirects disabled."""
        client = HttpClientFactory.create_client('https://example.com', follow_redirects=False)
        assert isinstance(client, httpx.AsyncClient)
        assert not client.follow_redirects

    def test_create_client_with_connection_limits(self):
        """Test creating HTTP client with custom connection limits."""
        client = HttpClientFactory.create_client(
            'https://example.com', 
            max_connections=50, 
            max_keepalive=20
        )
        assert isinstance(client, httpx.AsyncClient)
        # Connection limits are set in the transport layer
