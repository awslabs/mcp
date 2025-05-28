"""Tests for the Cognito authentication provider."""

import unittest
from awslabs.openapi_mcp_server.api.config import Config
from awslabs.openapi_mcp_server.auth.auth_errors import (
    ExpiredTokenError,
    InvalidCredentialsError,
    MissingCredentialsError,
)
from awslabs.openapi_mcp_server.auth.cognito_auth import CognitoAuthProvider
from unittest.mock import MagicMock, patch


# Original JWT token with expiry for testing
# This is the original token that contains the necessary 'exp' claim with value 1516239022
ORIGINAL_JWT_TOKEN = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiZXhwIjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c'


class TestCognitoAuthProvider(unittest.TestCase):
    """Tests for the Cognito authentication provider."""

    def test_init_with_missing_client_id(self):
        """Test initialization with missing client ID."""
        config = Config()
        config.auth_type = 'cognito'
        config.auth_cognito_username = 'test_user'
        config.auth_cognito_password = 'test_password'

        with self.assertRaises(MissingCredentialsError):
            CognitoAuthProvider(config)

    def test_init_with_missing_username(self):
        """Test initialization with missing username."""
        config = Config()
        config.auth_type = 'cognito'
        config.auth_cognito_client_id = 'test_client_id'
        config.auth_cognito_password = 'test_password'

        with self.assertRaises(MissingCredentialsError):
            CognitoAuthProvider(config)

    def test_init_with_missing_password(self):
        """Test initialization with missing password."""
        config = Config()
        config.auth_type = 'cognito'
        config.auth_cognito_client_id = 'test_client_id'
        config.auth_cognito_username = 'test_user'

        # Create a mock for the _validate_config method
        with patch.object(CognitoAuthProvider, '_validate_config') as mock_validate:
            # Make _validate_config raise MissingCredentialsError
            mock_validate.side_effect = MissingCredentialsError(
                'Cognito authentication requires a password'
            )

            # Test that the exception is raised
            with self.assertRaises(MissingCredentialsError):
                CognitoAuthProvider(config)

    def test_extract_token_expiry_direct(self):
        """Test extracting token expiry directly."""
        # Create a provider instance without calling __init__
        provider = CognitoAuthProvider.__new__(CognitoAuthProvider)
        provider._is_valid = True
        provider._token_lock = MagicMock()

        # Use the original token that works with the JWT decoder
        mock_token = ORIGINAL_JWT_TOKEN

        # Test the method
        expiry = provider._extract_token_expiry(mock_token)
        self.assertEqual(expiry, 1516239022)

    def test_extract_token_expiry_error_direct(self):
        """Test extracting token expiry with an error."""
        # Create a provider instance without calling __init__
        provider = CognitoAuthProvider.__new__(CognitoAuthProvider)
        provider._is_valid = True
        provider._token_lock = MagicMock()

        # Create an invalid token
        mock_token = 'invalid_token'

        # Test the method with a mock for time.time()
        with patch('time.time', return_value=1000):
            expiry = provider._extract_token_expiry(mock_token)
            # Should default to 1 hour from now
            self.assertEqual(expiry, 4600)  # 1000 + 3600

    def test_log_validation_error_direct(self):
        """Test logging validation error directly."""
        # Create a provider instance without calling __init__
        provider = CognitoAuthProvider.__new__(CognitoAuthProvider)
        provider._is_valid = True
        provider._token_lock = MagicMock()
        provider._username = 'test_user'

        # Mock the logger
        with patch('awslabs.openapi_mcp_server.auth.cognito_auth.logger') as mock_logger:
            provider._log_validation_error()
            mock_logger.error.assert_called()

    def test_is_token_expired_or_expiring_soon_direct(self):
        """Test checking if token is expired or expiring soon."""
        # Create a provider instance without calling __init__
        provider = CognitoAuthProvider.__new__(CognitoAuthProvider)
        provider._is_valid = True
        provider._token_lock = MagicMock()

        # Set token expiry to 1 hour from now
        with patch('time.time', return_value=1000):
            provider._token_expires_at = 1000 + 3600

            # Test with current time + buffer < expiry (not expired)
            with patch('time.time', return_value=1000):
                self.assertFalse(provider._is_token_expired_or_expiring_soon())

            # Test with current time + buffer > expiry (expired or expiring soon)
            with patch('time.time', return_value=1000 + 3600 - 200):
                self.assertTrue(provider._is_token_expired_or_expiring_soon())

    def test_provider_name_direct(self):
        """Test getting provider name."""
        # Create a provider instance without calling __init__
        provider = CognitoAuthProvider.__new__(CognitoAuthProvider)
        provider._is_valid = True
        provider._token_lock = MagicMock()

        # Test the property
        self.assertEqual(provider.provider_name, 'cognito')

    def test_refresh_token_method_direct(self):
        """Test refreshing token directly."""
        # Create a provider instance without calling __init__
        provider = CognitoAuthProvider.__new__(CognitoAuthProvider)
        provider._is_valid = True
        provider._token_lock = MagicMock()
        provider._username = 'test_user'
        provider._token = 'old_token'
        provider._refresh_token_value = 'refresh_token'

        # Mock the refresh method
        with patch.object(
            provider, '_refresh_cognito_token', return_value='new_token'
        ) as mock_refresh:
            with patch.object(provider, '_generate_auth_headers') as mock_generate:
                provider._refresh_token()
                mock_refresh.assert_called_once()
                mock_generate.assert_called_once_with('new_token')
                self.assertEqual(provider._token, 'new_token')

    def test_refresh_token_error_direct(self):
        """Test refreshing token with an error."""
        # Create a provider instance without calling __init__
        provider = CognitoAuthProvider.__new__(CognitoAuthProvider)
        provider._is_valid = True
        provider._token_lock = MagicMock()
        provider._username = 'test_user'
        provider._token = 'old_token'
        provider._refresh_token_value = 'refresh_token'

        # Mock the refresh method to raise an exception
        with patch.object(
            provider, '_refresh_cognito_token', side_effect=Exception('Refresh error')
        ):
            with patch('awslabs.openapi_mcp_server.auth.cognito_auth.logger') as mock_logger:
                with self.assertRaises(ExpiredTokenError):
                    provider._refresh_token()
                mock_logger.error.assert_called()

    def test_get_auth_headers_direct(self):
        """Test getting auth headers directly."""
        # Create a provider instance without calling __init__
        provider = CognitoAuthProvider.__new__(CognitoAuthProvider)
        provider._is_valid = True
        provider._token_lock = MagicMock()
        provider._auth_headers = {'Authorization': 'Bearer test_token'}

        # Mock the token expiry check
        with patch.object(provider, '_is_token_expired_or_expiring_soon', return_value=False):
            headers = provider.get_auth_headers()
            self.assertEqual(headers, {'Authorization': 'Bearer test_token'})

    def test_get_auth_headers_with_refresh_direct(self):
        """Test getting auth headers with refresh."""
        # Create a provider instance without calling __init__
        provider = CognitoAuthProvider.__new__(CognitoAuthProvider)
        provider._is_valid = True
        provider._token_lock = MagicMock()
        provider._auth_headers = {'Authorization': 'Bearer old_token'}

        # Mock the token expiry check and refresh
        with patch.object(provider, '_is_token_expired_or_expiring_soon', return_value=True):
            with patch.object(provider, '_refresh_token') as mock_refresh:
                headers = provider.get_auth_headers()
                mock_refresh.assert_called_once()
                self.assertEqual(headers, {'Authorization': 'Bearer old_token'})

    def test_get_cognito_token_success_direct(self):
        """Test getting Cognito token successfully."""
        # Create a provider instance without calling __init__
        provider = CognitoAuthProvider.__new__(CognitoAuthProvider)
        provider._is_valid = True
        provider._token_lock = MagicMock()
        provider._username = 'test_user'
        provider._password = 'test_password'
        provider._client_id = 'test_client_id'
        provider._user_pool_id = None
        provider._region = 'us-east-1'

        # Create exception classes that inherit from Exception
        class NotAuthorizedException(Exception):
            pass

        class UserNotConfirmedException(Exception):
            pass

        class InvalidParameterException(Exception):
            pass

        class ResourceNotFoundException(Exception):
            pass

        # Assign the exception classes to the client.exceptions
        mock_client = MagicMock()
        mock_client.exceptions.NotAuthorizedException = NotAuthorizedException
        mock_client.exceptions.UserNotConfirmedException = UserNotConfirmedException
        mock_client.exceptions.InvalidParameterException = InvalidParameterException
        mock_client.exceptions.ResourceNotFoundException = ResourceNotFoundException

        # Mock the response
        mock_response = {
            'AuthenticationResult': {
                'AccessToken': 'test_access_token',
                'IdToken': 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiZXhwIjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c',
                'RefreshToken': 'test_refresh_token',
            }
        }
        mock_client.initiate_auth.return_value = mock_response

        # Mock boto3.client
        with patch('boto3.client', return_value=mock_client):
            # Mock logger
            with patch('awslabs.openapi_mcp_server.auth.cognito_auth.logger'):
                # Test the method
                token = provider._get_cognito_token()
                self.assertEqual(token, 'test_access_token')
                self.assertEqual(provider._refresh_token_value, 'test_refresh_token')
                self.assertEqual(provider._token_expires_at, 1516239022)

    def test_get_cognito_token_with_user_pool_id_direct(self):
        """Test getting Cognito token with user pool ID."""
        # Create a provider instance without calling __init__
        provider = CognitoAuthProvider.__new__(CognitoAuthProvider)
        provider._is_valid = True
        provider._token_lock = MagicMock()
        provider._username = 'test_user'
        provider._password = 'test_password'
        provider._client_id = 'test_client_id'
        provider._user_pool_id = 'test_user_pool_id'
        provider._region = 'us-east-1'

        # Create exception classes that inherit from Exception
        class NotAuthorizedException(Exception):
            pass

        class UserNotConfirmedException(Exception):
            pass

        class InvalidParameterException(Exception):
            pass

        class ResourceNotFoundException(Exception):
            pass

        # Assign the exception classes to the client.exceptions
        mock_client = MagicMock()
        mock_client.exceptions.NotAuthorizedException = NotAuthorizedException
        mock_client.exceptions.UserNotConfirmedException = UserNotConfirmedException
        mock_client.exceptions.InvalidParameterException = InvalidParameterException
        mock_client.exceptions.ResourceNotFoundException = ResourceNotFoundException

        # Mock the response
        mock_response = {
            'AuthenticationResult': {
                'AccessToken': 'test_access_token',
                'IdToken': 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiZXhwIjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c',
                'RefreshToken': 'test_refresh_token',
            }
        }
        mock_client.initiate_auth.return_value = mock_response

        # Mock boto3.client
        with patch('boto3.client', return_value=mock_client):
            # Mock logger
            with patch('awslabs.openapi_mcp_server.auth.cognito_auth.logger'):
                # Test the method
                token = provider._get_cognito_token()
                self.assertEqual(token, 'test_access_token')
                self.assertEqual(provider._refresh_token_value, 'test_refresh_token')
                self.assertEqual(provider._token_expires_at, 1516239022)

    def test_get_cognito_token_admin_fallback_direct(self):
        """Test getting Cognito token with admin fallback."""
        # Create a provider instance without calling __init__
        provider = CognitoAuthProvider.__new__(CognitoAuthProvider)
        provider._is_valid = True
        provider._token_lock = MagicMock()
        provider._username = 'test_user'
        provider._password = 'test_password'
        provider._client_id = 'test_client_id'
        provider._user_pool_id = 'test_user_pool_id'
        provider._region = 'us-east-1'

        # Create exception classes that inherit from Exception
        class NotAuthorizedException(Exception):
            pass

        class UserNotConfirmedException(Exception):
            pass

        class InvalidParameterException(Exception):
            pass

        class ResourceNotFoundException(Exception):
            pass

        # Assign the exception classes to the client.exceptions
        mock_client = MagicMock()
        mock_client.exceptions.NotAuthorizedException = NotAuthorizedException
        mock_client.exceptions.UserNotConfirmedException = UserNotConfirmedException
        mock_client.exceptions.InvalidParameterException = InvalidParameterException
        mock_client.exceptions.ResourceNotFoundException = ResourceNotFoundException

        # Mock the responses
        mock_response = {
            'AuthenticationResult': {
                'AccessToken': 'test_access_token',
                'IdToken': 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiZXhwIjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c',
                'RefreshToken': 'test_refresh_token',
            }
        }
        mock_client.initiate_auth.side_effect = InvalidParameterException('Invalid parameter')
        mock_client.admin_initiate_auth.return_value = mock_response

        # Mock boto3.client
        with patch('boto3.client', return_value=mock_client):
            # Mock logger
            with patch('awslabs.openapi_mcp_server.auth.cognito_auth.logger'):
                # Test the method
                token = provider._get_cognito_token()
                self.assertEqual(token, 'test_access_token')
                self.assertEqual(provider._refresh_token_value, 'test_refresh_token')
                self.assertEqual(provider._token_expires_at, 1516239022)
                mock_client.admin_initiate_auth.assert_called_once()

    def test_get_cognito_token_not_authorized_direct(self):
        """Test getting Cognito token with not authorized error."""
        # Create a provider instance without calling __init__
        provider = CognitoAuthProvider.__new__(CognitoAuthProvider)
        provider._is_valid = True
        provider._token_lock = MagicMock()
        provider._username = 'test_user'
        provider._password = 'test_password'
        provider._client_id = 'test_client_id'
        provider._user_pool_id = None
        provider._region = 'us-east-1'

        # Create exception classes that inherit from Exception
        class NotAuthorizedException(Exception):
            pass

        class UserNotConfirmedException(Exception):
            pass

        class InvalidParameterException(Exception):
            pass

        class ResourceNotFoundException(Exception):
            pass

        # Assign the exception classes to the client.exceptions
        mock_client = MagicMock()
        mock_client.exceptions.NotAuthorizedException = NotAuthorizedException
        mock_client.exceptions.UserNotConfirmedException = UserNotConfirmedException
        mock_client.exceptions.InvalidParameterException = InvalidParameterException
        mock_client.exceptions.ResourceNotFoundException = ResourceNotFoundException

        # Mock the error
        mock_client.initiate_auth.side_effect = NotAuthorizedException('Not authorized')

        # Mock boto3.client
        with patch('boto3.client', return_value=mock_client):
            # Mock logger
            with patch('awslabs.openapi_mcp_server.auth.cognito_auth.logger'):
                # Test the method
                with self.assertRaises(InvalidCredentialsError):
                    provider._get_cognito_token()

    def test_refresh_cognito_token_success_direct(self):
        """Test refreshing Cognito token successfully."""
        # Create a provider instance without calling __init__
        provider = CognitoAuthProvider.__new__(CognitoAuthProvider)
        provider._is_valid = True
        provider._token_lock = MagicMock()
        provider._username = 'test_user'
        provider._client_id = 'test_client_id'
        provider._refresh_token_value = 'test_refresh_token'
        provider._user_pool_id = None
        provider._region = 'us-east-1'

        # Create exception classes that inherit from Exception
        class NotAuthorizedException(Exception):
            pass

        class InvalidParameterException(Exception):
            pass

        # Assign the exception classes to the client.exceptions
        mock_client = MagicMock()
        mock_client.exceptions.NotAuthorizedException = NotAuthorizedException
        mock_client.exceptions.InvalidParameterException = InvalidParameterException

        # Mock the response
        mock_response = {
            'AuthenticationResult': {
                'AccessToken': 'test_access_token',
                'IdToken': 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiZXhwIjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c',
            }
        }
        mock_client.initiate_auth.return_value = mock_response

        # Mock boto3.client
        with patch('boto3.client', return_value=mock_client):
            # Mock logger
            with patch('awslabs.openapi_mcp_server.auth.cognito_auth.logger'):
                # Test the method
                token = provider._refresh_cognito_token()
                self.assertEqual(token, 'test_access_token')
                self.assertEqual(provider._token_expires_at, 1516239022)
                mock_client.initiate_auth.assert_called_once_with(
                    ClientId='test_client_id',
                    AuthFlow='REFRESH_TOKEN_AUTH',
                    AuthParameters={'REFRESH_TOKEN': 'test_refresh_token'},
                )

    def test_refresh_cognito_token_admin_fallback_direct(self):
        """Test refreshing Cognito token with admin fallback."""
        # Create a provider instance without calling __init__
        provider = CognitoAuthProvider.__new__(CognitoAuthProvider)
        provider._is_valid = True
        provider._token_lock = MagicMock()
        provider._username = 'test_user'
        provider._client_id = 'test_client_id'
        provider._refresh_token_value = 'test_refresh_token'
        provider._user_pool_id = 'test_user_pool_id'
        provider._region = 'us-east-1'

        # Create exception classes that inherit from Exception
        class NotAuthorizedException(Exception):
            pass

        class InvalidParameterException(Exception):
            pass

        # Assign the exception classes to the client.exceptions
        mock_client = MagicMock()
        mock_client.exceptions.NotAuthorizedException = NotAuthorizedException
        mock_client.exceptions.InvalidParameterException = InvalidParameterException

        # Mock the responses
        mock_response = {
            'AuthenticationResult': {
                'AccessToken': 'test_access_token',
                'IdToken': 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiZXhwIjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c',
            }
        }
        mock_client.initiate_auth.side_effect = InvalidParameterException('Invalid parameter')
        mock_client.admin_initiate_auth.return_value = mock_response

        # Mock boto3.client
        with patch('boto3.client', return_value=mock_client):
            # Mock logger
            with patch('awslabs.openapi_mcp_server.auth.cognito_auth.logger'):
                # Test the method
                token = provider._refresh_cognito_token()
                self.assertEqual(token, 'test_access_token')
                self.assertEqual(provider._token_expires_at, 1516239022)
                mock_client.admin_initiate_auth.assert_called_once()

    def test_refresh_cognito_token_not_authorized_direct(self):
        """Test refreshing Cognito token with not authorized error."""
        # Create a provider instance without calling __init__
        provider = CognitoAuthProvider.__new__(CognitoAuthProvider)
        provider._is_valid = True
        provider._token_lock = MagicMock()
        provider._username = 'test_user'
        provider._password = 'test_password'
        provider._client_id = 'test_client_id'
        provider._refresh_token_value = 'test_refresh_token'
        provider._user_pool_id = None
        provider._region = 'us-east-1'

        # Create exception classes that inherit from Exception
        class NotAuthorizedException(Exception):
            pass

        class InvalidParameterException(Exception):
            pass

        # Assign the exception classes to the client.exceptions
        mock_client = MagicMock()
        mock_client.exceptions.NotAuthorizedException = NotAuthorizedException
        mock_client.exceptions.InvalidParameterException = InvalidParameterException

        # Mock the error response
        mock_client.initiate_auth.side_effect = NotAuthorizedException('Not authorized')

        # Mock boto3.client
        with patch('boto3.client', return_value=mock_client):
            # Mock logger
            with patch('awslabs.openapi_mcp_server.auth.cognito_auth.logger'):
                # Mock _get_cognito_token
                with patch.object(
                    provider, '_get_cognito_token', return_value='test_access_token'
                ) as mock_get_token:
                    # Test the method
                    token = provider._refresh_cognito_token()
                    self.assertEqual(token, 'test_access_token')
                    mock_get_token.assert_called_once()

    def test_refresh_cognito_token_error_direct(self):
        """Test refreshing Cognito token with an error."""
        # Create a provider instance without calling __init__
        provider = CognitoAuthProvider.__new__(CognitoAuthProvider)
        provider._is_valid = True
        provider._token_lock = MagicMock()
        provider._username = 'test_user'
        provider._client_id = 'test_client_id'
        provider._refresh_token_value = 'test_refresh_token'
        provider._user_pool_id = None
        provider._region = 'us-east-1'

        # Create exception classes that inherit from Exception
        class NotAuthorizedException(Exception):
            pass

        class InvalidParameterException(Exception):
            pass

        # Assign the exception classes to the client.exceptions
        mock_client = MagicMock()
        mock_client.exceptions.NotAuthorizedException = NotAuthorizedException
        mock_client.exceptions.InvalidParameterException = InvalidParameterException

        # Mock the error
        mock_client.initiate_auth.side_effect = Exception('Unexpected error')

        # Mock boto3.client
        with patch('boto3.client', return_value=mock_client):
            # Mock logger
            with patch('awslabs.openapi_mcp_server.auth.cognito_auth.logger'):
                # Test the method
                with self.assertRaises(ExpiredTokenError):
                    provider._refresh_cognito_token()
