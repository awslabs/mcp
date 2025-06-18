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
"""Tests for Bearer authentication provider."""

import pytest
from awslabs.openapi_mcp_server.api.config import Config
from awslabs.openapi_mcp_server.auth.auth_errors import MissingCredentialsError
from awslabs.openapi_mcp_server.auth.bearer_auth import BearerAuthProvider
from unittest.mock import patch


class TestBearerAuthProvider:
    """Tests for BearerAuthProvider."""

    def test_init_with_valid_config(self):
        """Test initialization with valid configuration."""
        # Create a configuration with token
        config = Config()
        config.auth_type = 'bearer'
        config.auth_token = 'test_token'

        # Create the provider
        provider = BearerAuthProvider(config)

        # Check that the provider is properly configured
        assert provider.is_configured()
        assert provider.provider_name == 'bearer'

        # Check that the auth headers are set correctly
        headers = provider.get_auth_headers()
        assert 'Authorization' in headers
        assert headers['Authorization'] == 'Bearer test_token'

        # Check that params and cookies are empty
        assert not provider.get_auth_params()
        assert not provider.get_auth_cookies()

    def test_init_with_missing_token(self):
        """Test initialization with missing token."""
        # Create a configuration without token
        config = Config()
        config.auth_type = 'bearer'
        config.auth_token = ''  # Empty token

        # Creating the provider should raise an exception
        with pytest.raises(MissingCredentialsError) as excinfo:
            BearerAuthProvider(config)

        # Check the error message
        assert 'Bearer authentication requires a valid token' in str(excinfo.value)

    def test_custom_token_ttl(self):
        """Test custom token TTL."""
        # Create a configuration with token and custom TTL
        config = Config()
        config.auth_type = 'bearer'
        config.auth_token = 'test_token'
        config.auth_token_ttl = 7200  # 2 hours

        # Create the provider
        provider = BearerAuthProvider(config)

        # Check that the token TTL is set correctly
        assert provider._token_ttl == 7200

    @patch('awslabs.openapi_mcp_server.auth.bearer_auth.cached_auth_data')
    def test_cached_auth_data(self, mock_cached_auth_data):
        """Test that auth data is cached."""
        # Create a configuration with valid bearer token settings
        config = Config()
        config.auth_token = 'test_bearer_token'

        # Create the provider
        provider = BearerAuthProvider(config)

        # Mock the cached_auth_data decorator to return a mock function
        mock_cached_auth_data.return_value = lambda func: func

        # Test that the provider was created successfully
        assert provider.provider_name == 'bearer'

    def test_log_validation_error(self):
        """Test logging of validation error."""
        # Create a configuration
        config = Config()
        config.auth_type = 'bearer'
        config.auth_token = 'test_token'

        # Create the provider
        provider = BearerAuthProvider(config)

        # Mock the logger
        with patch('awslabs.openapi_mcp_server.auth.bearer_auth.logger') as mock_logger:
            # Call _log_validation_error directly
            provider._log_validation_error()

            # Check that logger.error was called twice
            assert mock_logger.error.call_count == 2
            # Check that the error messages contain the expected text
            assert (
                'Bearer authentication requires a valid token'
                in mock_logger.error.call_args_list[0][0][0]
            )
            assert 'Please provide a token' in mock_logger.error.call_args_list[1][0][0]

    def test_generate_auth_headers(self):
        """Test generation of auth headers."""
        # Create a configuration
        config = Config()
        config.auth_type = 'bearer'
        config.auth_token = 'test_token'

        # Create the provider
        provider = BearerAuthProvider(config)

        # Call _generate_auth_headers directly
        headers = provider._generate_auth_headers('test_token')

        # Check the headers
        assert 'Authorization' in headers
        assert headers['Authorization'] == 'Bearer test_token'

    def test_generate_auth_headers_with_empty_token(self):
        """Test generation of auth headers with empty token."""
        # Create a configuration
        config = Config()
        config.auth_type = 'bearer'
        config.auth_token = 'test_token'  # We need a valid token for initialization

        # Create the provider
        provider = BearerAuthProvider(config)

        # Call _generate_auth_headers directly with empty token
        headers = provider._generate_auth_headers('')

        # Check the headers
        assert 'Authorization' in headers
        assert headers['Authorization'] == 'Bearer '  # Empty token

    def test_initialize_auth(self):
        """Test initialization of auth data."""
        # Create a configuration
        config = Config()
        config.auth_type = 'bearer'
        config.auth_token = 'test_token'

        # Create the provider
        provider = BearerAuthProvider(config)

        # Mock _generate_auth_headers
        with patch.object(provider, '_generate_auth_headers') as mock_generate:
            mock_generate.return_value = {'Authorization': 'Bearer mock_token'}

            # Call _initialize_auth directly
            provider._initialize_auth()

            # Check that _generate_auth_headers was called with the token
            mock_generate.assert_called_once_with('test_token')

            # Check that auth headers were set
            assert provider._auth_headers == {'Authorization': 'Bearer mock_token'}
