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
"""Tests for the auth protocol module."""

import httpx
import unittest
from awslabs.openapi_mcp_server.api.config import Config
from awslabs.openapi_mcp_server.auth.auth_protocol import (
    AuthProviderProtocol,
)
from unittest.mock import MagicMock


class MockAuthProvider:
    """Mock implementation of AuthProviderProtocol for testing."""

    def __init__(self, name='mock_provider'):
        """Initialize the mock auth provider."""
        self._name = name

    @property
    def provider_name(self) -> str:
        """Get the name of the authentication provider."""
        return self._name

    def is_configured(self) -> bool:
        """Check if the authentication provider is properly configured."""
        return True

    def get_auth_headers(self) -> dict[str, str]:
        """Get authentication headers for HTTP requests."""
        return {'Authorization': 'Bearer mock-token'}

    def get_auth_params(self) -> dict[str, str]:
        """Get authentication query parameters for HTTP requests."""
        return {'api_key': 'mock-api-key'}

    def get_auth_cookies(self) -> dict[str, str]:
        """Get authentication cookies for HTTP requests."""
        return {'session': 'mock-session-id'}

    def get_httpx_auth(self) -> httpx.Auth:
        """Get authentication object for HTTPX."""
        return None


def mock_factory(config: Config) -> AuthProviderProtocol:
    """Mock factory function for creating auth providers."""
    return MockAuthProvider()


class TestAuthProtocol(unittest.TestCase):
    """Test cases for the auth protocol module."""

    def test_auth_provider_protocol(self):
        """Test that MockAuthProvider implements AuthProviderProtocol."""
        provider = MockAuthProvider()
        self.assertIsInstance(provider, AuthProviderProtocol)

        # Test all protocol methods
        self.assertEqual(provider.provider_name, 'mock_provider')
        self.assertTrue(provider.is_configured())
        self.assertEqual(provider.get_auth_headers(), {'Authorization': 'Bearer mock-token'})
        self.assertEqual(provider.get_auth_params(), {'api_key': 'mock-api-key'})
        self.assertEqual(provider.get_auth_cookies(), {'session': 'mock-session-id'})
        self.assertIsNone(provider.get_httpx_auth())

    def test_auth_provider_factory(self):
        """Test that mock_factory implements AuthProviderFactory."""
        # Create a mock config
        config = MagicMock(spec=Config)

        # Verify the factory function works
        provider = mock_factory(config)
        self.assertIsInstance(provider, AuthProviderProtocol)
        self.assertEqual(provider.provider_name, 'mock_provider')


if __name__ == '__main__':
    unittest.main()
