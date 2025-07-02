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
"""Tests for API Key authentication provider."""

import pytest
from awslabs.openapi_mcp_server.api.config import Config
from awslabs.openapi_mcp_server.auth.api_key_auth import ApiKeyAuthProvider
from awslabs.openapi_mcp_server.auth.auth_errors import (
    ConfigurationError,
    MissingCredentialsError,
)
from unittest.mock import patch


class TestApiKeyAuthProvider:
    """Tests for ApiKeyAuthProvider."""

    def test_init_with_valid_config(self):
        """Test initialization with valid configuration."""
        # Create a configuration with API key
        config = Config()
        config.auth_type = 'api_key'
        config.auth_api_key = 'test_api_key'
        config.auth_api_key_name = 'X-API-Key'
        config.auth_api_key_in = 'header'

        # Create the provider
        provider = ApiKeyAuthProvider(config)

        # Check that the provider is properly configured
        assert provider.is_configured()
        assert provider.provider_name == 'api_key'

        # Check that the auth headers are set correctly
        headers = provider.get_auth_headers()
        assert 'X-API-Key' in headers
        assert headers['X-API-Key'] == 'test_api_key'

        # Check that params and cookies are empty
        assert not provider.get_auth_params()
        assert not provider.get_auth_cookies()

    def test_init_with_missing_api_key(self):
        """Test initialization with missing API key."""
        # Create a configuration without API key
        config = Config()
        config.auth_type = 'api_key'
        config.auth_api_key = ''  # Empty API key

        # Creating the provider should raise an exception
        with pytest.raises(MissingCredentialsError) as excinfo:
            ApiKeyAuthProvider(config)

        # Check the error message
        assert 'API Key authentication requires a valid API key' in str(excinfo.value)

    def test_init_with_invalid_location(self):
        """Test initialization with invalid API key location."""
        # Create a configuration with invalid API key location
        config = Config()
        config.auth_type = 'api_key'
        config.auth_api_key = 'test_api_key'
        config.auth_api_key_in = 'invalid'  # Invalid location

        # Creating the provider should raise an exception
        with pytest.raises(ConfigurationError) as excinfo:
            ApiKeyAuthProvider(config)

        # Check the error message
        assert 'Invalid API key location: invalid' in str(excinfo.value)

    def test_api_key_in_header(self):
        """Test API key in header."""
        # Create a configuration with API key in header
        config = Config()
        config.auth_type = 'api_key'
        config.auth_api_key = 'test_api_key'
        config.auth_api_key_name = 'X-API-Key'
        config.auth_api_key_in = 'header'

        # Create the provider
        provider = ApiKeyAuthProvider(config)

        # Check that the auth headers are set correctly
        headers = provider.get_auth_headers()
        assert 'X-API-Key' in headers
        assert headers['X-API-Key'] == 'test_api_key'

        # Check that params and cookies are empty
        assert not provider.get_auth_params()
        assert not provider.get_auth_cookies()

    def test_api_key_in_query(self):
        """Test API key in query parameter."""
        # Create a configuration with API key in query
        config = Config()
        config.auth_type = 'api_key'
        config.auth_api_key = 'test_api_key'
        config.auth_api_key_name = 'api_key'
        config.auth_api_key_in = 'query'

        # Create the provider
        provider = ApiKeyAuthProvider(config)

        # Check that the auth params are set correctly
        params = provider.get_auth_params()
        assert 'api_key' in params
        assert params['api_key'] == 'test_api_key'

        # Check that headers and cookies are empty
        assert not provider.get_auth_headers()
        assert not provider.get_auth_cookies()

    def test_api_key_in_cookie(self):
        """Test API key in cookie."""
        # Create a configuration with API key in cookie
        config = Config()
        config.auth_type = 'api_key'
        config.auth_api_key = 'test_api_key'
        config.auth_api_key_name = 'api_key'
        config.auth_api_key_in = 'cookie'

        # Create the provider
        provider = ApiKeyAuthProvider(config)

        # Check that the auth cookies are set correctly
        cookies = provider.get_auth_cookies()
        assert 'api_key' in cookies
        assert cookies['api_key'] == 'test_api_key'

        # Check that headers and params are empty
        assert not provider.get_auth_headers()
        assert not provider.get_auth_params()

    def test_default_values(self):
        """Test default values for API key name and location."""
        # Create a configuration with minimal settings
        config = Config()
        config.auth_type = 'api_key'
        config.auth_api_key = 'test_api_key'
        # No name or location specified, should use defaults

        # Create the provider
        provider = ApiKeyAuthProvider(config)

        # Check that the auth headers are set correctly with default name
        headers = provider.get_auth_headers()
        assert 'api_key' in headers  # Default name
        assert headers['api_key'] == 'test_api_key'

    def test_hash_api_key(self):
        """Test API key hashing."""
        # Create a provider
        config = Config()
        config.auth_type = 'api_key'
        config.auth_api_key = 'test_api_key'
        ApiKeyAuthProvider(config)

        # Get the hash method
        hash_method = ApiKeyAuthProvider._hash_api_key

        # Test that the hash is not empty and is a valid hex string
        hash1 = hash_method('test_api_key')
        assert hash1 is not None
        assert len(hash1) > 0
        # Check that it's a valid hex string
        try:
            int(hash1, 16)
        except ValueError:
            pytest.fail('Hash is not a valid hex string')

        # Test that different keys produce different hashes
        hash2 = hash_method('different_key')
        assert hash1 != hash2

    @patch('awslabs.openapi_mcp_server.auth.api_key_auth.cached_auth_data')
    def test_cached_auth_data(self, mock_cached_auth_data):
        """Test that auth data is cached."""
        # Create a configuration with valid API key settings
        config = Config()
        config.auth_api_key = 'test_api_key'
        config.auth_api_key_name = 'X-API-Key'
        config.auth_api_key_in = 'header'

        # Create the provider
        provider = ApiKeyAuthProvider(config)

        # Mock the cached_auth_data decorator to return a mock function
        mock_cached_auth_data.return_value = lambda func: func

        # Test that the provider was created successfully
        assert provider.provider_name == 'api_key'

    def test_handle_validation_error(self):
        """Test handling of validation error."""
        # Create a configuration
        config = Config()
        config.auth_type = 'api_key'
        config.auth_api_key = 'test_api_key'

        # Create the provider
        provider = ApiKeyAuthProvider(config)

        # Call _handle_validation_error directly
        provider._handle_validation_error()

        # Check that validation_error is set
        assert provider._validation_error is not None
        assert isinstance(provider._validation_error, MissingCredentialsError)
        assert 'API Key authentication requires a valid API key' in str(provider._validation_error)
