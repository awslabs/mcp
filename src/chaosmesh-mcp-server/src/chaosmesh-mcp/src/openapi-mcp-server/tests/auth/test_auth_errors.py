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
"""Tests for authentication error handling."""

import unittest
from awslabs.openapi_mcp_server.auth.auth_errors import (
    AuthError,
    AuthErrorType,
    ConfigurationError,
    ExpiredTokenError,
    InsufficientPermissionsError,
    InvalidCredentialsError,
    MissingCredentialsError,
    NetworkError,
    create_auth_error,
    format_error_message,
)


class TestAuthErrors(unittest.TestCase):
    """Test cases for authentication error handling."""

    def test_auth_error_creation(self):
        """Test creating authentication errors."""
        # Create a basic auth error
        error = AuthError('Test error message')
        self.assertEqual(error.message, 'Test error message')
        self.assertEqual(error.error_type, AuthErrorType.UNKNOWN_ERROR)
        self.assertEqual(str(error), 'unknown_error: Test error message')

        # Create an error with a specific type
        error = AuthError('Missing API key', AuthErrorType.MISSING_CREDENTIALS)
        self.assertEqual(error.message, 'Missing API key')
        self.assertEqual(error.error_type, AuthErrorType.MISSING_CREDENTIALS)
        self.assertEqual(str(error), 'missing_credentials: Missing API key')

        # Create an error with details
        error = AuthError(
            'Invalid token',
            AuthErrorType.INVALID_CREDENTIALS,
            {'token_type': 'Bearer', 'reason': 'expired'},
        )
        self.assertEqual(error.message, 'Invalid token')
        self.assertEqual(error.error_type, AuthErrorType.INVALID_CREDENTIALS)
        self.assertEqual(error.details, {'token_type': 'Bearer', 'reason': 'expired'})

    def test_specific_error_classes(self):
        """Test specific error classes."""
        # Test MissingCredentialsError
        error = MissingCredentialsError('Missing API key')
        self.assertEqual(error.error_type, AuthErrorType.MISSING_CREDENTIALS)

        # Test InvalidCredentialsError
        error = InvalidCredentialsError('Invalid token')
        self.assertEqual(error.error_type, AuthErrorType.INVALID_CREDENTIALS)

        # Test ExpiredTokenError
        error = ExpiredTokenError('Token expired')
        self.assertEqual(error.error_type, AuthErrorType.EXPIRED_TOKEN)

        # Test InsufficientPermissionsError
        error = InsufficientPermissionsError('Insufficient permissions')
        self.assertEqual(error.error_type, AuthErrorType.INSUFFICIENT_PERMISSIONS)

        # Test ConfigurationError
        error = ConfigurationError('Invalid configuration')
        self.assertEqual(error.error_type, AuthErrorType.CONFIGURATION_ERROR)

        # Test NetworkError
        error = NetworkError('Network error')
        self.assertEqual(error.error_type, AuthErrorType.NETWORK_ERROR)

    def test_create_auth_error(self):
        """Test creating auth errors using the factory function."""
        # Create a MissingCredentialsError
        error = create_auth_error(
            AuthErrorType.MISSING_CREDENTIALS, 'Missing API key', {'param': 'api_key'}
        )
        self.assertIsInstance(error, MissingCredentialsError)
        self.assertEqual(error.message, 'Missing API key')
        self.assertEqual(error.details, {'param': 'api_key'})

        # Create an unknown error type
        error = create_auth_error(AuthErrorType.UNKNOWN_ERROR, 'Unknown error')
        self.assertIsInstance(error, AuthError)
        self.assertEqual(error.error_type, AuthErrorType.UNKNOWN_ERROR)

    def test_format_error_message(self):
        """Test formatting error messages."""
        message = format_error_message(
            'api_key', AuthErrorType.MISSING_CREDENTIALS, 'Missing API key'
        )
        self.assertEqual(message, '[API_KEY] missing_credentials: Missing API key')

        message = format_error_message('bearer', AuthErrorType.EXPIRED_TOKEN, 'Token expired')
        self.assertEqual(message, '[BEARER] expired_token: Token expired')


if __name__ == '__main__':
    unittest.main()
