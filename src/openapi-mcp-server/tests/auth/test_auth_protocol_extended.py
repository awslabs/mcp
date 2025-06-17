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
"""Extended tests for the auth protocol module."""

import httpx
import unittest
from awslabs.openapi_mcp_server.api.config import Config
from awslabs.openapi_mcp_server.auth.auth_protocol import (
    AuthProviderProtocol,
    T,
)
from typing import Dict, Optional, Type
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

    def get_auth_headers(self) -> Dict[str, str]:
        """Get authentication headers for HTTP requests."""
        return {'Authorization': 'Bearer mock-token'}

    def get_auth_params(self) -> Dict[str, str]:
        """Get authentication query parameters for HTTP requests."""
        return {'api_key': 'mock-api-key'}

    def get_auth_cookies(self) -> Dict[str, str]:
        """Get authentication cookies for HTTP requests."""
        return {'session': 'mock-session-id'}

    def get_httpx_auth(self) -> Optional[httpx.Auth]:
        """Get authentication object for HTTPX."""
        return None


class CustomAuthProvider(MockAuthProvider):
    """Custom auth provider for testing TypeVar."""

    def __init__(self, config: Config):
        """Initialize with config."""
        super().__init__(name='custom_provider')
        self.config = config


def create_custom_provider(config: Config) -> CustomAuthProvider:
    """Create custom auth providers."""
    return CustomAuthProvider(config)


class TestAuthProtocolExtended(unittest.TestCase):
    """Extended test cases for the auth protocol module."""

    def test_auth_provider_protocol_with_custom_implementation(self):
        """Test a different implementation of AuthProviderProtocol."""
        config = MagicMock(spec=Config)
        provider = CustomAuthProvider(config)

        # Test that it implements the protocol
        self.assertIsInstance(provider, AuthProviderProtocol)

        # Test protocol methods
        self.assertEqual(provider.provider_name, 'custom_provider')
        self.assertTrue(provider.is_configured())
        self.assertEqual(provider.get_auth_headers(), {'Authorization': 'Bearer mock-token'})
        self.assertEqual(provider.get_auth_params(), {'api_key': 'mock-api-key'})
        self.assertEqual(provider.get_auth_cookies(), {'session': 'mock-session-id'})
        self.assertIsNone(provider.get_httpx_auth())

    def test_auth_provider_factory_with_custom_implementation(self):
        """Test a custom factory function."""
        # Create a mock config
        config = MagicMock(spec=Config)

        # Verify the factory function works
        provider = create_custom_provider(config)
        self.assertIsInstance(provider, AuthProviderProtocol)
        self.assertEqual(provider.provider_name, 'custom_provider')

        # Verify it's also an instance of CustomAuthProvider
        self.assertIsInstance(provider, CustomAuthProvider)

        # Verify it has the config
        self.assertEqual(provider.config, config)

    def test_type_variable_usage(self):
        """Test the TypeVar T usage with a function that uses it."""

        # Define a function that uses the TypeVar T
        def create_provider_with_type(provider_class: Type[T], config: Config) -> T:
            return provider_class(config)

        # Create a mock config
        config = MagicMock(spec=Config)

        # Use the function to create a provider
        provider = create_provider_with_type(CustomAuthProvider, config)

        # Verify the provider is of the correct type
        self.assertIsInstance(provider, CustomAuthProvider)
        self.assertEqual(provider.provider_name, 'custom_provider')
        self.assertEqual(provider.config, config)

    def test_auth_provider_with_non_none_auth(self):
        """Test an auth provider that returns a non-None auth value."""

        # Create a provider that returns a non-None value
        class AuthProviderWithNonNoneAuth(MockAuthProvider):
            def get_httpx_auth(self) -> Optional[object]:
                return 'auth-value'  # Just return a string instead of an auth object

        # Create an instance and test it
        provider = AuthProviderWithNonNoneAuth()
        self.assertIsInstance(provider, AuthProviderProtocol)
        self.assertEqual(provider.get_httpx_auth(), 'auth-value')

    def test_auth_provider_factory_protocol(self):
        """Test the AuthProviderFactory protocol."""
        # Create a mock factory that implements the protocol
        mock_factory = MagicMock(spec=lambda config: None)
        mock_provider = MagicMock(spec=AuthProviderProtocol)
        mock_factory.return_value = mock_provider

        # Verify it can be used as an AuthProviderFactory
        self.assertTrue(callable(mock_factory))

        # Create a mock config
        config = MagicMock(spec=Config)

        # Call the factory
        provider = mock_factory(config)

        # Verify the factory was called with the config
        mock_factory.assert_called_once_with(config)

        # Verify the provider is the one returned by the factory
        self.assertEqual(provider, mock_provider)


if __name__ == '__main__':
    unittest.main()
