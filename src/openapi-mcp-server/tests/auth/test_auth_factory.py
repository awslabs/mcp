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
"""Tests for the authentication factory."""

import pytest
from awslabs.openapi_mcp_server.api.config import Config
from awslabs.openapi_mcp_server.auth.auth_factory import (
    get_auth_provider,
    is_auth_type_available,
    register_auth_provider,
)
from awslabs.openapi_mcp_server.auth.auth_provider import AuthProvider, NullAuthProvider


# Create a mock auth provider for testing
class MockAuthProvider(AuthProvider):
    """Mock authentication provider for testing."""

    def __init__(self, config):
        """Initialize with configuration."""
        self.config = config

    def get_auth_headers(self):
        """Get authentication headers."""
        return {'X-Mock-Auth': 'test_value'}

    def get_auth_params(self):
        """Get authentication query parameters."""
        return {}

    def get_auth_cookies(self):
        """Get authentication cookies."""
        return {}

    def get_httpx_auth(self):
        """Get authentication object for HTTPX."""
        return None

    def is_configured(self):
        """Check if the authentication provider is properly configured."""
        return True

    @property
    def provider_name(self):
        """Get the name of the authentication provider."""
        return 'mock'


class TestAuthFactory:
    """Tests for the authentication factory."""

    def setup_method(self):
        """Set up the test fixture."""
        self.config = Config()
        # Register a mock provider for testing
        if not is_auth_type_available('mock'):
            register_auth_provider('mock', MockAuthProvider)

    def test_register_auth_provider(self):
        """Test registering an auth provider."""

        # Define a new provider class
        class TestProvider(AuthProvider):
            def get_auth_headers(self):
                return {}

            def get_auth_params(self):
                return {}

            def get_auth_cookies(self):
                return {}

            def get_httpx_auth(self):
                return None

            def is_configured(self):
                return True

            @property
            def provider_name(self):
                return 'test'

        # Register the provider
        register_auth_provider('test', TestProvider)

        # Verify it's registered
        assert is_auth_type_available('test') is True

        # Clean up
        from awslabs.openapi_mcp_server.auth.auth_factory import _AUTH_PROVIDERS

        if 'test' in _AUTH_PROVIDERS:
            del _AUTH_PROVIDERS['test']

    def test_register_duplicate_provider(self):
        """Test registering a duplicate provider."""
        with pytest.raises(ValueError):
            register_auth_provider('mock', MockAuthProvider)

    def test_is_auth_type_available(self):
        """Test checking if auth type is available."""
        assert is_auth_type_available('mock') is True
        assert is_auth_type_available('nonexistent') is False
        assert is_auth_type_available('MOCK') is True  # Case insensitive

    def test_get_auth_provider_none(self):
        """Test getting null auth provider."""
        self.config.auth_type = 'none'
        provider = get_auth_provider(self.config)

        assert isinstance(provider, NullAuthProvider)
        assert provider.provider_name == 'none'

    def test_get_auth_provider_mock(self):
        """Test getting a registered auth provider."""
        self.config.auth_type = 'mock'
        provider = get_auth_provider(self.config)

        assert isinstance(provider, MockAuthProvider)
        assert provider.provider_name == 'mock'
        assert provider.config == self.config

    def test_get_auth_provider_unknown(self):
        """Test getting an unknown auth provider."""
        self.config.auth_type = 'unknown'
        provider = get_auth_provider(self.config)

        # Should fall back to NullAuthProvider
        assert isinstance(provider, NullAuthProvider)
        assert provider.provider_name == 'none'
