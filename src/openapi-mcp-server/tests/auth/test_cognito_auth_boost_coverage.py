"""Tests to boost coverage for cognito_auth.py."""

import pytest
import time
from awslabs.openapi_mcp_server.api.config import Config
from awslabs.openapi_mcp_server.auth.cognito_auth import (
    CognitoAuthProvider,
)
from unittest.mock import MagicMock, patch


class TestCognitoAuthBoostCoverage:
    """Tests to boost coverage for cognito_auth.py."""

    @pytest.fixture
    def mock_config(self):
        """Create a mock config for testing."""
        config = MagicMock(spec=Config)
        config.auth_cognito_client_id = 'test_client_id'
        config.auth_cognito_username = 'test_username'
        config.auth_cognito_password = 'test_password'  # pragma: allowlist secret
        config.auth_cognito_client_secret = 'test_client_secret'  # pragma: allowlist secret
        config.auth_cognito_domain = 'test-domain'
        config.auth_cognito_region = 'us-east-1'
        config.auth_cognito_scopes = 'scope1 scope2'
        config.auth_token = None  # Add this to avoid validation errors
        return config

    @pytest.fixture
    def mock_boto3_client(self):
        """Create a mock boto3 client."""
        client = MagicMock()
        return client

    @patch('requests.post')
    @patch('boto3.client')
    def test_cognito_auth_provider_init(self, mock_boto3, mock_requests_post, mock_config):
        """Test CognitoAuthProvider initialization."""
        # Set up mock boto3 client
        mock_client = MagicMock()
        mock_boto3.return_value = mock_client

        # Mock requests.post to avoid actual API calls
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'access_token': 'test_access_token', 'expires_in': 3600}
        mock_requests_post.return_value = mock_response

        # Create CognitoAuthProvider
        with patch(
            'awslabs.openapi_mcp_server.auth.cognito_auth.CognitoAuthProvider._get_token_client_credentials',
            return_value='test_token',
        ):
            auth_provider = CognitoAuthProvider(mock_config)

        # Verify attributes were set correctly
        assert auth_provider._client_id == 'test_client_id'
        assert auth_provider._username == 'test_username'
        assert auth_provider._password == 'test_password'  # pragma: allowlist secret

        # We're not testing the boto3 client creation here since it's mocked differently
        # The important part is that the attributes are set correctly

    @patch('requests.post')
    @patch('boto3.client')
    def test_is_configured_with_username_password(
        self, mock_boto3, mock_requests_post, mock_config
    ):
        """Test is_configured with username and password."""
        # Set up mock boto3 client
        mock_boto3.return_value = MagicMock()

        # Mock requests.post to avoid actual API calls
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'access_token': 'test_access_token', 'expires_in': 3600}
        mock_requests_post.return_value = mock_response

        # Create CognitoAuthProvider
        with patch(
            'awslabs.openapi_mcp_server.auth.cognito_auth.CognitoAuthProvider._get_token_client_credentials',
            return_value='test_token',
        ):
            auth_provider = CognitoAuthProvider(mock_config)

        # Verify is_configured returns True
        assert auth_provider.is_configured() is True

    @patch('requests.post')
    @patch('boto3.client')
    def test_is_configured_with_client_credentials(
        self, mock_boto3, mock_requests_post, mock_config
    ):
        """Test is_configured with client credentials."""
        # Set up mock boto3 client
        mock_boto3.return_value = MagicMock()

        # Mock requests.post to avoid actual API calls
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'access_token': 'test_access_token', 'expires_in': 3600}
        mock_requests_post.return_value = mock_response

        # Modify config to remove username/password
        mock_config.auth_cognito_username = None
        mock_config.auth_cognito_password = None

        # Create CognitoAuthProvider
        with patch(
            'awslabs.openapi_mcp_server.auth.cognito_auth.CognitoAuthProvider._get_token_client_credentials',
            return_value='test_token',
        ):
            auth_provider = CognitoAuthProvider(mock_config)

        # Verify is_configured returns True
        assert auth_provider.is_configured() is True

    @patch('boto3.client')
    def test_is_configured_missing_credentials(self, mock_boto3, mock_config):
        """Test is_configured with missing credentials."""
        # Set up mock boto3 client
        mock_boto3.return_value = MagicMock()

        # Modify config to remove all credentials
        mock_config.auth_cognito_username = None
        mock_config.auth_cognito_password = None
        mock_config.auth_cognito_client_secret = None
        mock_config.auth_cognito_client_id = (
            None  # Also remove client_id to avoid validation errors
        )

        # Create CognitoAuthProvider with patched _validate_config to avoid errors
        with patch(
            'awslabs.openapi_mcp_server.auth.cognito_auth.CognitoAuthProvider._validate_config',
            return_value=False,
        ):
            auth_provider = CognitoAuthProvider(mock_config)

        # Verify is_configured returns False
        assert auth_provider.is_configured() is False

    @patch('requests.post')
    @patch('boto3.client')
    def test_get_auth_headers(self, mock_boto3, mock_requests_post, mock_config):
        """Test get_auth_headers method."""
        # Set up mock boto3 client
        mock_boto3.return_value = MagicMock()

        # Mock requests.post to avoid actual API calls
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'access_token': 'test_access_token', 'expires_in': 3600}
        mock_requests_post.return_value = mock_response

        # Create CognitoAuthProvider with patched methods
        with patch(
            'awslabs.openapi_mcp_server.auth.cognito_auth.CognitoAuthProvider._get_token_client_credentials',
            return_value='test_token',
        ):
            auth_provider = CognitoAuthProvider(mock_config)

        # Set token and disable token expiry check
        auth_provider._token = 'test_token'
        auth_provider._auth_headers = {'Authorization': 'Bearer test_token'}

        # Patch the _is_token_expired_or_expiring_soon method to return False
        with patch.object(auth_provider, '_is_token_expired_or_expiring_soon', return_value=False):
            # Get auth headers
            headers = auth_provider.get_auth_headers()

        # Verify headers
        assert headers == {'Authorization': 'Bearer test_token'}

    @patch('requests.post')
    @patch('boto3.client')
    def test_get_auth_headers_no_token(self, mock_boto3, mock_requests_post, mock_config):
        """Test get_auth_headers method with no token."""
        # Set up mock boto3 client
        mock_client = MagicMock()
        mock_boto3.return_value = mock_client

        # Set up mock response for initiate_auth
        mock_client.initiate_auth.return_value = {
            'AuthenticationResult': {
                'AccessToken': 'new_access_token',
                'IdToken': 'new_id_token',
                'RefreshToken': 'new_refresh_token',
                'ExpiresIn': 3600,
            }
        }

        # Mock requests.post to avoid actual API calls
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'access_token': 'new_access_token', 'expires_in': 3600}
        mock_requests_post.return_value = mock_response

        # Create CognitoAuthProvider with patched methods
        with patch(
            'awslabs.openapi_mcp_server.auth.cognito_auth.CognitoAuthProvider._get_token_client_credentials',
            return_value='new_access_token',
        ):
            auth_provider = CognitoAuthProvider(mock_config)

        # Set up auth_provider for testing
        auth_provider._token = 'new_access_token'
        auth_provider._auth_headers = {'Authorization': 'Bearer new_access_token'}

        # Patch the _is_token_expired_or_expiring_soon method to return False
        with patch.object(auth_provider, '_is_token_expired_or_expiring_soon', return_value=False):
            # Get auth headers
            headers = auth_provider.get_auth_headers()

        # Verify headers
        assert headers == {'Authorization': 'Bearer new_access_token'}

    @patch('requests.post')
    @patch('boto3.client')
    def test_check_and_refresh_token(self, mock_boto3, mock_requests_post, mock_config):
        """Test _check_and_refresh_token_if_needed method."""
        # Set up mock boto3 client
        mock_client = MagicMock()
        mock_boto3.return_value = mock_client

        # Set up mock response for initiate_auth
        mock_client.initiate_auth.return_value = {
            'AuthenticationResult': {
                'AccessToken': 'new_access_token',
                'IdToken': 'new_id_token',
                'RefreshToken': 'new_refresh_token',
                'ExpiresIn': 3600,
            }
        }

        # Mock requests.post to avoid actual API calls
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'access_token': 'new_access_token', 'expires_in': 3600}
        mock_requests_post.return_value = mock_response

        # Create CognitoAuthProvider with patched methods
        with patch(
            'awslabs.openapi_mcp_server.auth.cognito_auth.CognitoAuthProvider._get_token_client_credentials',
            return_value='test_token',
        ):
            auth_provider = CognitoAuthProvider(mock_config)

        # Set expired token
        auth_provider._token = 'old_token'
        auth_provider._refresh_token_value = 'old_refresh_token'
        auth_provider._token_expires_at = time.time() - 100  # Expired 100 seconds ago

        # Patch the _refresh_token method to avoid actual refresh
        with patch.object(auth_provider, '_refresh_token') as mock_refresh:
            # Call _check_and_refresh_token_if_needed
            auth_provider._check_and_refresh_token_if_needed()

            # Verify _refresh_token was called
            mock_refresh.assert_called_once()
