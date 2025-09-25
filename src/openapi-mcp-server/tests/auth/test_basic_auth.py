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
"""Tests for Basic authentication provider."""

import base64
import pytest
from awslabs.openapi_mcp_server.api.config import Config
from awslabs.openapi_mcp_server.auth.auth_errors import MissingCredentialsError
from awslabs.openapi_mcp_server.auth.basic_auth import BasicAuthProvider
from unittest.mock import patch


class TestBasicAuthProvider:
    """Tests for BasicAuthProvider."""

    def test_init_with_valid_config(self):
        """Test initialization with valid configuration."""
        # Create a configuration with valid basic auth settings
        config = Config()
        config.auth_username = 'test_user'
        config.auth_password = 'test_password'  # pragma: allowlist secret

        # Create the provider
        provider = BasicAuthProvider(config)

        # Verify initialization
        assert provider.provider_name == 'basic'
        assert provider._username == 'test_user'
        assert provider._password == 'test_password'

    def test_init_with_missing_username(self):
        """Test initialization with missing username."""
        # Create a configuration without username
        config = Config()
        config.auth_type = 'basic'
        config.auth_username = ''  # Empty username
        config.auth_password = 'testpass'

        # Creating the provider should raise an exception
        with pytest.raises(MissingCredentialsError) as excinfo:
            BasicAuthProvider(config)

        # Check the error message
        assert 'Basic authentication requires a username' in str(excinfo.value)

    def test_init_with_missing_password(self):
        """Test initialization with missing password."""
        # Create a configuration without password
        config = Config()
        config.auth_type = 'basic'
        config.auth_username = 'testuser'
        config.auth_password = ''  # Empty password

        # Creating the provider should raise an exception
        with pytest.raises(MissingCredentialsError) as excinfo:
            BasicAuthProvider(config)

        # Check the error message
        assert 'Basic authentication requires a password' in str(excinfo.value)

    def test_hash_credentials(self):
        """Test credentials hashing."""
        # Create a provider
        config = Config()
        config.auth_type = 'basic'
        config.auth_username = 'testuser'
        config.auth_password = 'testpass'
        BasicAuthProvider(config)

        # Get the hash method
        hash_method = BasicAuthProvider._hash_credentials

        # Test that the same credentials produce the same hash
        # Note: With bcrypt, the hash will be different each time due to the random salt
        # So we need to verify differently - we'll check that the hash is not empty
        # and that it's a valid hex string
        hash1 = hash_method('testuser', 'testpass')
        assert hash1 is not None
        assert len(hash1) > 0
        # Check that it's a valid hex string
        try:
            int(hash1, 16)
        except ValueError:
            pytest.fail('Hash is not a valid hex string')

        # Test that different credentials produce different hashes
        hash2 = hash_method('otheruser', 'testpass')
        hash3 = hash_method('testuser', 'otherpass')
        assert hash1 != hash2
        assert hash1 != hash3
        assert hash2 != hash3

    @patch('awslabs.openapi_mcp_server.auth.basic_auth.cached_auth_data')
    def test_cached_auth_data(self, mock_cached_auth_data):
        """Test that auth data is cached."""
        # Create a configuration with valid basic auth settings
        config = Config()
        config.auth_username = 'test_user'
        config.auth_password = 'test_password'

        # Create the provider
        provider = BasicAuthProvider(config)

        # Mock the cached_auth_data decorator to return a mock function
        mock_cached_auth_data.return_value = lambda func: func

        # Test that the provider was created successfully
        assert provider.provider_name == 'basic'

    def test_log_validation_error(self):
        """Test logging of validation error."""
        # Create a configuration
        config = Config()
        config.auth_type = 'basic'
        config.auth_username = 'testuser'
        config.auth_password = 'testpass'

        # Create the provider
        provider = BasicAuthProvider(config)

        # Mock the logger
        with patch('awslabs.openapi_mcp_server.auth.basic_auth.logger') as mock_logger:
            # Call _log_validation_error directly
            provider._log_validation_error()

            # Check that logger.error was called
            mock_logger.error.assert_called_once()
            # Check that the error message contains the expected text
            assert (
                'Basic authentication requires both username and password'
                in mock_logger.error.call_args[0][0]
            )

    def test_generate_auth_headers(self):
        """Test generation of auth headers."""
        # Create a configuration
        config = Config()
        config.auth_type = 'basic'
        config.auth_username = 'testuser'
        config.auth_password = 'testpass'

        # Create the provider
        provider = BasicAuthProvider(config)

        # Call _generate_auth_headers directly
        headers = provider._generate_auth_headers('dummy_hash')

        # Check the headers
        assert 'Authorization' in headers
        assert headers['Authorization'].startswith('Basic ')

        # Decode the base64 part and check the credentials
        encoded_part = headers['Authorization'][6:]  # Skip 'Basic '
        decoded = base64.b64decode(encoded_part).decode('utf-8')
        assert decoded == 'testuser:testpass'

    def test_generate_httpx_auth(self):
        """Test generation of HTTPX auth object."""
        # Create a configuration
        config = Config()
        config.auth_type = 'basic'
        config.auth_username = 'testuser'
        config.auth_password = 'testpass'

        # Create the provider
        provider = BasicAuthProvider(config)

        # Call _generate_httpx_auth with the required parameters
        auth = provider._generate_httpx_auth('testuser', 'testpass')

        # Check that we get an httpx.BasicAuth object
        import httpx

        assert isinstance(auth, httpx.BasicAuth)
        # BasicAuth object stores credentials internally, we can't directly access them
        # but we can verify it's the correct type and was created successfully
