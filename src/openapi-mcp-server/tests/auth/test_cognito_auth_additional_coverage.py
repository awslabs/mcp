"""Additional tests to boost coverage for cognito_auth.py."""

import pytest
import time
from awslabs.openapi_mcp_server.api.config import Config
from awslabs.openapi_mcp_server.auth.auth_errors import ExpiredTokenError
from awslabs.openapi_mcp_server.auth.cognito_auth import CognitoAuthProvider
from unittest.mock import MagicMock, patch


class TestCognitoAuthAdditionalCoverage:
    """Additional tests to boost coverage for cognito_auth.py."""

    @pytest.fixture
    def mock_config(self):
        """Create a mock config for testing."""
        config = MagicMock(spec=Config)
        config.auth_cognito_client_id = 'test_client_id'
        config.auth_cognito_username = 'test_username'
        config.auth_cognito_password = 'test_password'
        config.auth_cognito_client_secret = None
        config.auth_cognito_domain = None
        config.auth_cognito_region = 'us-east-1'
        config.auth_cognito_scopes = ''
        config.auth_cognito_user_pool_id = 'test_pool_id'
        config.auth_token = None
        return config

    @patch('boto3.client')
    def test_refresh_token_success(self, mock_boto3, mock_config):
        """Test successful token refresh."""
        # Set up mock boto3 client
        mock_client = MagicMock()
        mock_boto3.return_value = mock_client

        # Set up mock response for initiate_auth
        mock_client.initiate_auth.return_value = {
            'AuthenticationResult': {
                'IdToken': 'new_id_token',
                'ExpiresIn': 3600,
            }
        }

        # Create provider instance without calling __init__
        provider = CognitoAuthProvider.__new__(CognitoAuthProvider)
        provider._client_id = 'test_client_id'
        provider._username = 'test_username'
        provider._password = 'test_password'
        provider._user_pool_id = 'test_pool_id'
        provider._region = 'us-east-1'
        provider._token = 'old_token'
        provider._refresh_token_value = 'old_refresh_token'
        provider._token_expires_at = time.time() - 100  # Expired
        provider._token_lock = MagicMock()
        provider._auth_headers = {'Authorization': 'Bearer old_token'}
        provider._is_valid = True
        provider._grant_type = 'password'

        # Mock _initialize_auth to avoid errors
        with patch.object(provider, '_initialize_auth'):
            # Mock _extract_token_expiry to return a future time
            with patch.object(provider, '_extract_token_expiry', return_value=time.time() + 3600):
                # Mock _refresh_cognito_token to return a new token and update refresh token
                with patch.object(
                    provider, '_refresh_cognito_token', return_value='new_id_token'
                ) as mock_refresh:
                    # Call _refresh_token
                    provider._refresh_token()

                    # Verify _refresh_cognito_token was called
                    mock_refresh.assert_called_once()

                    # Verify token was updated
                    assert provider._token == 'new_id_token'

    @patch('boto3.client')
    def test_refresh_token_failure(self, mock_boto3, mock_config):
        """Test token refresh failure."""
        # Create provider instance without calling __init__
        provider = CognitoAuthProvider.__new__(CognitoAuthProvider)
        provider._client_id = 'test_client_id'
        provider._username = 'test_username'
        provider._password = 'test_password'
        provider._user_pool_id = 'test_pool_id'
        provider._region = 'us-east-1'
        provider._token = 'old_token'
        provider._refresh_token_value = 'old_refresh_token'
        provider._token_expires_at = time.time() - 100  # Expired
        provider._token_lock = MagicMock()
        provider._auth_headers = {'Authorization': 'Bearer old_token'}
        provider._is_valid = True
        provider._grant_type = 'password'

        # Mock _refresh_cognito_token to return None
        with patch.object(provider, '_refresh_cognito_token', return_value=None):
            # Mock _get_cognito_token to raise an exception
            with patch.object(provider, '_get_cognito_token', side_effect=Exception('Auth failed')):
                # Call _refresh_token and expect exception
                with pytest.raises(ExpiredTokenError):
                    provider._refresh_token()

    @patch('boto3.client')
    def test_refresh_cognito_token_success(self, mock_boto3, mock_config):
        """Test successful Cognito token refresh."""
        # Set up mock boto3 client
        mock_client = MagicMock()
        mock_boto3.return_value = mock_client

        # Set up mock response for initiate_auth
        mock_client.initiate_auth.return_value = {
            'AuthenticationResult': {
                'IdToken': 'new_id_token',
                'ExpiresIn': 3600,
            }
        }

        # Create provider instance without calling __init__
        provider = CognitoAuthProvider.__new__(CognitoAuthProvider)
        provider._client_id = 'test_client_id'
        provider._username = 'test_username'
        provider._password = 'test_password'
        provider._user_pool_id = None
        provider._region = 'us-east-1'
        provider._refresh_token_value = 'refresh_token'
        provider._token_expires_at = 0
        provider._grant_type = 'password'

        # Mock _extract_token_expiry to return a future time
        with patch.object(provider, '_extract_token_expiry', return_value=time.time() + 3600):
            # Call _refresh_cognito_token
            token = provider._refresh_cognito_token()

            # Verify token was returned
            assert token == 'new_id_token'

            # Verify initiate_auth was called with correct parameters
            mock_client.initiate_auth.assert_called_once_with(
                ClientId='test_client_id',
                AuthFlow='REFRESH_TOKEN_AUTH',
                AuthParameters={'REFRESH_TOKEN': 'refresh_token'},
            )

    @patch('boto3.client')
    def test_refresh_cognito_token_with_user_pool(self, mock_boto3, mock_config):
        """Test Cognito token refresh with user pool ID."""
        # Set up mock boto3 client
        mock_client = MagicMock()
        mock_boto3.return_value = mock_client

        # Create proper exception classes that inherit from BaseException
        class NotAuthorizedException(Exception):
            pass

        class InvalidParameterException(Exception):
            pass

        # Set up exceptions on the mock client
        mock_client.exceptions = MagicMock()
        mock_client.exceptions.NotAuthorizedException = NotAuthorizedException
        mock_client.exceptions.InvalidParameterException = InvalidParameterException

        # Set up mock responses
        mock_client.initiate_auth.side_effect = InvalidParameterException('Invalid parameter')

        mock_client.admin_initiate_auth.return_value = {
            'AuthenticationResult': {
                'IdToken': 'new_id_token',
                'ExpiresIn': 3600,
            }
        }

        # Create provider instance without calling __init__
        provider = CognitoAuthProvider.__new__(CognitoAuthProvider)
        provider._client_id = 'test_client_id'
        provider._username = 'test_username'
        provider._password = 'test_password'
        provider._user_pool_id = 'test_pool_id'
        provider._region = 'us-east-1'
        provider._refresh_token_value = 'refresh_token'
        provider._token_expires_at = 0
        provider._grant_type = 'password'

        # Mock _extract_token_expiry to return a future time
        with patch.object(provider, '_extract_token_expiry', return_value=time.time() + 3600):
            # Call _refresh_cognito_token
            token = provider._refresh_cognito_token()

            # Verify token was returned
            assert token == 'new_id_token'

            # Verify admin_initiate_auth was called with correct parameters
            mock_client.admin_initiate_auth.assert_called_once_with(
                UserPoolId='test_pool_id',
                ClientId='test_client_id',
                AuthFlow='REFRESH_TOKEN',
                AuthParameters={'REFRESH_TOKEN': 'refresh_token'},
            )

    @patch('boto3.client')
    def test_refresh_cognito_token_failure(self, mock_boto3, mock_config):
        """Test Cognito token refresh failure."""
        # Set up mock boto3 client
        mock_client = MagicMock()
        mock_boto3.return_value = mock_client

        # Create proper exception classes that inherit from BaseException
        class NotAuthorizedException(Exception):
            pass

        class InvalidParameterException(Exception):
            pass

        # Set up exceptions on the mock client
        mock_client.exceptions = MagicMock()
        mock_client.exceptions.NotAuthorizedException = NotAuthorizedException
        mock_client.exceptions.InvalidParameterException = InvalidParameterException

        # Set up mock response for initiate_auth to raise exception
        mock_client.initiate_auth.side_effect = Exception('Refresh failed')

        # Create provider instance without calling __init__
        provider = CognitoAuthProvider.__new__(CognitoAuthProvider)
        provider._client_id = 'test_client_id'
        provider._username = 'test_username'
        provider._password = 'test_password'
        provider._user_pool_id = None
        provider._region = 'us-east-1'
        provider._refresh_token_value = 'refresh_token'
        provider._token_expires_at = 0
        provider._grant_type = 'password'

        # Call _refresh_cognito_token
        token = provider._refresh_cognito_token()

        # Verify no token was returned
        assert token is None

    @patch('boto3.client')
    def test_refresh_cognito_token_no_id_token(self, mock_boto3, mock_config):
        """Test Cognito token refresh with no ID token in response."""
        # Set up mock boto3 client
        mock_client = MagicMock()
        mock_boto3.return_value = mock_client

        # Set up mock response for initiate_auth with no ID token
        mock_client.initiate_auth.return_value = {
            'AuthenticationResult': {
                # No IdToken
                'ExpiresIn': 3600,
            }
        }

        # Create provider instance without calling __init__
        provider = CognitoAuthProvider.__new__(CognitoAuthProvider)
        provider._client_id = 'test_client_id'
        provider._username = 'test_username'
        provider._password = 'test_password'
        provider._user_pool_id = None
        provider._region = 'us-east-1'
        provider._refresh_token_value = 'refresh_token'
        provider._token_expires_at = 0
        provider._grant_type = 'password'

        # Call _refresh_cognito_token
        token = provider._refresh_cognito_token()

        # Verify no token was returned
        assert token is None

    def test_is_token_expired_or_expiring_soon(self):
        """Test token expiry check."""
        # Create provider instance without calling __init__
        provider = CognitoAuthProvider.__new__(CognitoAuthProvider)

        # Test expired token
        provider._token_expires_at = time.time() - 100  # Expired 100 seconds ago
        assert provider._is_token_expired_or_expiring_soon() is True

        # Test token expiring soon (within buffer)
        provider._token_expires_at = time.time() + 200  # Expires in 200 seconds (buffer is 300)
        assert provider._is_token_expired_or_expiring_soon() is True

        # Test valid token
        provider._token_expires_at = time.time() + 600  # Expires in 10 minutes
        assert provider._is_token_expired_or_expiring_soon() is False

    @patch('boto3.client')
    @patch('requests.post')
    def test_check_and_refresh_token_if_needed_not_expired(
        self, mock_post, mock_boto3, mock_config
    ):
        """Test token check when token is not expired."""
        # Create provider instance without calling __init__
        provider = CognitoAuthProvider.__new__(CognitoAuthProvider)
        provider._token = 'test_token'
        provider._token_expires_at = time.time() + 3600  # Not expired
        provider._token_lock = MagicMock()

        # Mock _is_token_expired_or_expiring_soon to return False
        with patch.object(provider, '_is_token_expired_or_expiring_soon', return_value=False):
            # Mock _refresh_token to verify it's not called
            with patch.object(provider, '_refresh_token') as mock_refresh:
                # Call _check_and_refresh_token_if_needed
                provider._check_and_refresh_token_if_needed()

                # Verify _refresh_token was not called
                mock_refresh.assert_not_called()

    @patch('boto3.client')
    def test_log_validation_error(self, mock_boto3, mock_config):
        """Test _log_validation_error method."""
        # Create provider instance without calling __init__
        provider = CognitoAuthProvider.__new__(CognitoAuthProvider)

        # Call _log_validation_error
        with patch('awslabs.openapi_mcp_server.logger.error') as mock_error:
            provider._log_validation_error()

            # Verify logger.error was called
            assert mock_error.call_count >= 1
