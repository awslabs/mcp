"""Tests for exception handling in Cognito authentication provider."""

import pytest
from awslabs.openapi_mcp_server.auth.auth_errors import (
    ConfigurationError,
    MissingCredentialsError,
    NetworkError,
)
from awslabs.openapi_mcp_server.auth.cognito_auth import CognitoAuthProvider
from unittest.mock import MagicMock, patch


class TestCognitoAuthExceptions:
    """Tests for exception handling in CognitoAuthProvider."""

    @patch('boto3.client')
    def test_user_not_confirmed_exception(self, mock_boto_client):
        """Test handling of UserNotConfirmedException - covers lines 304-313."""
        # Mock the boto3 client
        mock_client = MagicMock()
        mock_boto_client.return_value = mock_client

        # Create UserNotConfirmedException
        class UserNotConfirmedException(Exception):
            pass

        # Add exception to client.exceptions
        mock_client.exceptions.UserNotConfirmedException = UserNotConfirmedException
        mock_client.exceptions.InvalidParameterException = type(
            'InvalidParameterException', (Exception,), {}
        )
        mock_client.exceptions.ResourceNotFoundException = type(
            'ResourceNotFoundException', (Exception,), {}
        )
        mock_client.exceptions.NotAuthorizedException = type(
            'NotAuthorizedException', (Exception,), {}
        )

        # Make initiate_auth raise UserNotConfirmedException
        mock_client.initiate_auth.side_effect = UserNotConfirmedException('User is not confirmed')

        # Create auth provider instance without calling __init__
        provider = CognitoAuthProvider.__new__(CognitoAuthProvider)
        provider._is_valid = True
        provider._token_lock = MagicMock()
        provider._username = 'testuser'
        provider._password = 'testpass'  # pragma: allowlist secret
        provider._client_id = 'test_client_id'
        provider._user_pool_id = 'us-east-1_test123'
        provider._region = 'us-east-1'
        provider._auth_headers = {}
        provider._token = None
        provider._token_expires_at = 0

        # Test the _get_cognito_token method directly
        with pytest.raises(ConfigurationError) as excinfo:
            provider._get_cognito_token()

        # Verify the error message
        assert 'User not confirmed' in str(excinfo.value)

    @patch('boto3.client')
    def test_resource_not_found_exception(self, mock_boto_client):
        """Test handling of ResourceNotFoundException - covers lines 374-380."""
        # Mock the boto3 client
        mock_client = MagicMock()
        mock_boto_client.return_value = mock_client

        # Create ResourceNotFoundException
        class ResourceNotFoundException(Exception):
            pass

        # Add exception to client.exceptions
        mock_client.exceptions.UserNotConfirmedException = type(
            'UserNotConfirmedException', (Exception,), {}
        )
        mock_client.exceptions.InvalidParameterException = type(
            'InvalidParameterException', (Exception,), {}
        )
        mock_client.exceptions.ResourceNotFoundException = ResourceNotFoundException
        mock_client.exceptions.NotAuthorizedException = type(
            'NotAuthorizedException', (Exception,), {}
        )

        # Make initiate_auth raise ResourceNotFoundException
        mock_client.initiate_auth.side_effect = ResourceNotFoundException('User pool not found')

        # Create auth provider instance without calling __init__
        provider = CognitoAuthProvider.__new__(CognitoAuthProvider)
        provider._is_valid = True
        provider._token_lock = MagicMock()
        provider._username = 'testuser'
        provider._password = 'testpass'  # pragma: allowlist secret
        provider._client_id = 'test_client_id'
        provider._user_pool_id = 'us-east-1_test123'
        provider._region = 'us-east-1'
        provider._auth_headers = {}
        provider._token = None
        provider._token_expires_at = 0

        # Test the _get_cognito_token method directly
        with pytest.raises(ConfigurationError) as excinfo:
            provider._get_cognito_token()

        # Verify the error message
        assert 'Cognito resource not found' in str(excinfo.value)

    @patch('boto3.client')
    def test_general_exception(self, mock_boto_client):
        """Test handling of general exceptions - covers lines 381-390."""
        # Mock the boto3 client
        mock_client = MagicMock()
        mock_boto_client.return_value = mock_client

        # Add exception classes to client.exceptions
        mock_client.exceptions.UserNotConfirmedException = type(
            'UserNotConfirmedException', (Exception,), {}
        )
        mock_client.exceptions.InvalidParameterException = type(
            'InvalidParameterException', (Exception,), {}
        )
        mock_client.exceptions.ResourceNotFoundException = type(
            'ResourceNotFoundException', (Exception,), {}
        )
        mock_client.exceptions.NotAuthorizedException = type(
            'NotAuthorizedException', (Exception,), {}
        )

        # Make initiate_auth raise a general Exception
        mock_client.initiate_auth.side_effect = Exception('Network connection error')

        # Create auth provider instance without calling __init__
        provider = CognitoAuthProvider.__new__(CognitoAuthProvider)
        provider._is_valid = True
        provider._token_lock = MagicMock()
        provider._username = 'testuser'
        provider._password = 'testpass'  # pragma: allowlist secret
        provider._client_id = 'test_client_id'
        provider._user_pool_id = 'us-east-1_test123'
        provider._region = 'us-east-1'
        provider._auth_headers = {}
        provider._token = None
        provider._token_expires_at = 0

        # Test the _get_cognito_token method directly
        with pytest.raises(NetworkError):
            provider._get_cognito_token()

    @patch('boto3.client')
    def test_invalid_parameter_exception_with_missing_client_id(self, mock_boto_client):
        """Test handling of InvalidParameterException with missing client ID."""
        # Mock the boto3 client
        mock_client = MagicMock()
        mock_boto_client.return_value = mock_client

        # Create InvalidParameterException
        class InvalidParameterException(Exception):
            pass

        # Add exception to client.exceptions
        mock_client.exceptions.UserNotConfirmedException = type(
            'UserNotConfirmedException', (Exception,), {}
        )
        mock_client.exceptions.InvalidParameterException = InvalidParameterException
        mock_client.exceptions.ResourceNotFoundException = type(
            'ResourceNotFoundException', (Exception,), {}
        )
        mock_client.exceptions.NotAuthorizedException = type(
            'NotAuthorizedException', (Exception,), {}
        )

        # Make initiate_auth raise InvalidParameterException with "Missing required parameter"
        mock_client.initiate_auth.side_effect = InvalidParameterException(
            'Missing required parameter ClientId'
        )
        # Also mock admin_initiate_auth to raise the same exception
        mock_client.admin_initiate_auth.side_effect = InvalidParameterException(
            'Missing required parameter ClientId'
        )

        # Create auth provider instance without calling __init__
        provider = CognitoAuthProvider.__new__(CognitoAuthProvider)
        provider._is_valid = True
        provider._token_lock = MagicMock()
        provider._username = 'testuser'
        provider._password = 'testpass'  # pragma: allowlist secret
        provider._client_id = ''  # Empty client ID
        provider._user_pool_id = 'us-east-1_test123'
        provider._region = 'us-east-1'
        provider._auth_headers = {}
        provider._token = None
        provider._token_expires_at = 0

        # Test the _get_cognito_token method directly
        with pytest.raises(MissingCredentialsError) as excinfo:
            provider._get_cognito_token()

        # Verify the error message
        assert 'Missing Cognito client ID' in str(excinfo.value)

    @patch('boto3.client')
    def test_invalid_parameter_exception_with_missing_user_pool_id(self, mock_boto_client):
        """Test handling of InvalidParameterException with missing user pool ID."""
        # Mock the boto3 client
        mock_client = MagicMock()
        mock_boto_client.return_value = mock_client

        # Create InvalidParameterException
        class InvalidParameterException(Exception):
            pass

        # Add exception to client.exceptions
        mock_client.exceptions.UserNotConfirmedException = type(
            'UserNotConfirmedException', (Exception,), {}
        )
        mock_client.exceptions.InvalidParameterException = InvalidParameterException
        mock_client.exceptions.ResourceNotFoundException = type(
            'ResourceNotFoundException', (Exception,), {}
        )
        mock_client.exceptions.NotAuthorizedException = type(
            'NotAuthorizedException', (Exception,), {}
        )

        # Make initiate_auth raise InvalidParameterException with "Missing required parameter"
        mock_client.initiate_auth.side_effect = InvalidParameterException(
            'Missing required parameter UserPoolId'
        )
        # Also mock admin_initiate_auth to raise the same exception
        mock_client.admin_initiate_auth.side_effect = InvalidParameterException(
            'Missing required parameter UserPoolId'
        )

        # Create auth provider instance without calling __init__
        provider = CognitoAuthProvider.__new__(CognitoAuthProvider)
        provider._is_valid = True
        provider._token_lock = MagicMock()
        provider._username = 'testuser'
        provider._password = 'testpass'  # pragma: allowlist secret
        provider._client_id = 'test_client_id'
        provider._user_pool_id = None  # No user pool ID
        provider._region = 'us-east-1'
        provider._auth_headers = {}
        provider._token = None
        provider._token_expires_at = 0

        # Test the _get_cognito_token method directly
        with pytest.raises(ConfigurationError) as excinfo:
            provider._get_cognito_token()

        # Verify the error message
        assert 'Missing User Pool ID' in str(excinfo.value)

    @patch('boto3.client')
    def test_invalid_parameter_exception_with_other_issue(self, mock_boto_client):
        """Test handling of InvalidParameterException with other issues."""
        # Mock the boto3 client
        mock_client = MagicMock()
        mock_boto_client.return_value = mock_client

        # Create InvalidParameterException
        class InvalidParameterException(Exception):
            pass

        # Add exception to client.exceptions
        mock_client.exceptions.UserNotConfirmedException = type(
            'UserNotConfirmedException', (Exception,), {}
        )
        mock_client.exceptions.InvalidParameterException = InvalidParameterException
        mock_client.exceptions.ResourceNotFoundException = type(
            'ResourceNotFoundException', (Exception,), {}
        )
        mock_client.exceptions.NotAuthorizedException = type(
            'NotAuthorizedException', (Exception,), {}
        )

        # Make initiate_auth raise InvalidParameterException with some other message
        mock_client.initiate_auth.side_effect = InvalidParameterException(
            'Some other parameter issue'
        )
        # Also mock admin_initiate_auth to raise the same exception
        mock_client.admin_initiate_auth.side_effect = InvalidParameterException(
            'Some other parameter issue'
        )

        # Create auth provider instance without calling __init__
        provider = CognitoAuthProvider.__new__(CognitoAuthProvider)
        provider._is_valid = True
        provider._token_lock = MagicMock()
        provider._username = 'testuser'
        provider._password = 'testpass'  # pragma: allowlist secret
        provider._client_id = 'test_client_id'
        provider._user_pool_id = 'us-east-1_test123'
        provider._region = 'us-east-1'
        provider._auth_headers = {}
        provider._token = None
        provider._token_expires_at = 0

        # Test the _get_cognito_token method directly
        with pytest.raises(ConfigurationError) as excinfo:
            provider._get_cognito_token()

        # Verify the error message
        assert 'Invalid parameter for Cognito authentication' in str(excinfo.value)
