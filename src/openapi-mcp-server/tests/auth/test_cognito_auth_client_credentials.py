"""Tests for the Cognito authentication provider client credentials flow."""

import base64
import json
import pytest
import time
from awslabs.openapi_mcp_server.api.config import Config
from awslabs.openapi_mcp_server.auth.auth_errors import InvalidCredentialsError
from awslabs.openapi_mcp_server.auth.cognito_auth import CognitoAuthProvider
from unittest.mock import MagicMock, patch


class TestCognitoAuthClientCredentials:
    """Tests for the Cognito authentication provider client credentials flow."""

    @pytest.fixture
    def mock_config(self):
        """Create a mock config for testing."""
        config = MagicMock(spec=Config)
        config.auth_cognito_client_id = 'test_client_id'
        config.auth_cognito_username = None
        config.auth_cognito_password = None
        config.auth_cognito_client_secret = 'test_client_secret'
        config.auth_cognito_domain = 'test-domain'
        config.auth_cognito_region = 'us-east-1'
        config.auth_cognito_scopes = 'scope1,scope2'
        config.auth_token = None
        return config

    @patch('requests.post')
    def test_get_token_client_credentials_success(self, mock_post, mock_config):
        """Test successful token acquisition with client credentials flow."""
        # Mock successful response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'access_token': 'test_access_token', 'expires_in': 3600}
        mock_post.return_value = mock_response

        # Create provider instance without calling __init__
        provider = CognitoAuthProvider.__new__(CognitoAuthProvider)
        provider._client_id = 'test_client_id'
        provider._client_secret = 'test_client_secret'
        provider._domain = 'test-domain'
        provider._region = 'us-east-1'
        provider._scopes = ['scope1', 'scope2']
        provider._token_expires_at = 0
        provider._grant_type = 'client_credentials'

        # Call the method directly
        token = provider._get_token_client_credentials()

        # Verify the token was returned
        assert token == 'test_access_token'
        assert provider._token_expires_at > time.time()

        # Verify the request was made correctly
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        assert args[0] == 'https://test-domain.auth.us-east-1.amazoncognito.com/oauth2/token'
        assert 'headers' in kwargs
        assert 'data' in kwargs
        assert kwargs['data']['grant_type'] == 'client_credentials'
        assert kwargs['data']['scope'] == 'scope1 scope2'

    @patch('requests.post')
    def test_get_token_client_credentials_no_scopes(self, mock_post, mock_config):
        """Test token acquisition with no scopes."""
        # Mock successful response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'access_token': 'test_access_token', 'expires_in': 3600}
        mock_post.return_value = mock_response

        # Create provider instance without calling __init__
        provider = CognitoAuthProvider.__new__(CognitoAuthProvider)
        provider._client_id = 'test_client_id'
        provider._client_secret = 'test_client_secret'
        provider._domain = 'test-domain'
        provider._region = 'us-east-1'
        provider._scopes = []  # No scopes
        provider._token_expires_at = 0
        provider._grant_type = 'client_credentials'

        # Call the method directly
        token = provider._get_token_client_credentials()

        # Verify the token was returned
        assert token == 'test_access_token'

        # Verify the request was made correctly
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        assert 'data' in kwargs
        assert kwargs['data']['grant_type'] == 'client_credentials'
        assert 'scope' not in kwargs['data']

    @patch('requests.post')
    def test_get_token_client_credentials_error(self, mock_post, mock_config):
        """Test error handling in client credentials flow."""
        # Mock error response
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.text = 'Invalid client'
        mock_post.return_value = mock_response

        # Create provider instance without calling __init__
        provider = CognitoAuthProvider.__new__(CognitoAuthProvider)
        provider._client_id = 'test_client_id'
        provider._client_secret = 'test_client_secret'
        provider._domain = 'test-domain'
        provider._region = 'us-east-1'
        provider._scopes = ['scope1', 'scope2']
        provider._token_expires_at = 0
        provider._grant_type = 'client_credentials'

        # Call the method and expect an exception
        with pytest.raises(InvalidCredentialsError) as excinfo:
            provider._get_token_client_credentials()

        # Verify the exception details
        assert 'Failed to obtain token with client credentials' in str(excinfo.value)
        assert 'Invalid client' in str(excinfo.value.details.get('error', ''))

    @patch('requests.post')
    def test_get_token_client_credentials_no_token(self, mock_post, mock_config):
        """Test handling of response with no access token."""
        # Mock response with no access token
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'expires_in': 3600
            # No access_token
        }
        mock_post.return_value = mock_response

        # Create provider instance without calling __init__
        provider = CognitoAuthProvider.__new__(CognitoAuthProvider)
        provider._client_id = 'test_client_id'
        provider._client_secret = 'test_client_secret'
        provider._domain = 'test-domain'
        provider._region = 'us-east-1'
        provider._scopes = ['scope1', 'scope2']
        provider._token_expires_at = 0
        provider._grant_type = 'client_credentials'

        # Call the method directly
        token = provider._get_token_client_credentials()

        # Verify no token was returned
        assert token is None

    @patch('requests.post')
    def test_get_token_client_credentials_exception(self, mock_post, mock_config):
        """Test exception handling in client credentials flow."""
        # Mock post to raise an exception
        mock_post.side_effect = Exception('Network error')

        # Create provider instance without calling __init__
        provider = CognitoAuthProvider.__new__(CognitoAuthProvider)
        provider._client_id = 'test_client_id'
        provider._client_secret = 'test_client_secret'
        provider._domain = 'test-domain'
        provider._region = 'us-east-1'
        provider._scopes = ['scope1', 'scope2']
        provider._token_expires_at = 0
        provider._grant_type = 'client_credentials'

        # Call the method and expect an exception
        with pytest.raises(Exception) as excinfo:
            provider._get_token_client_credentials()

        # Verify the exception details
        assert 'Network error' in str(excinfo.value)

    def test_extract_token_expiry_valid_token(self):
        """Test extracting expiry from a valid token."""
        # Create a valid JWT token with expiry
        header = {'alg': 'HS256', 'typ': 'JWT'}
        payload = {'exp': int(time.time()) + 3600}  # 1 hour from now

        # Encode header and payload
        header_json = json.dumps(header).encode()
        header_b64 = base64.urlsafe_b64encode(header_json).decode().rstrip('=')

        payload_json = json.dumps(payload).encode()
        payload_b64 = base64.urlsafe_b64encode(payload_json).decode().rstrip('=')

        # Create token (without signature for simplicity)
        token = f'{header_b64}.{payload_b64}.signature'

        # Create provider instance without calling __init__
        provider = CognitoAuthProvider.__new__(CognitoAuthProvider)

        # Extract expiry
        expiry = provider._extract_token_expiry(token)

        # Verify expiry matches what we set
        assert expiry == payload['exp']

    def test_extract_token_expiry_invalid_token(self):
        """Test extracting expiry from an invalid token."""
        # Create provider instance without calling __init__
        provider = CognitoAuthProvider.__new__(CognitoAuthProvider)

        # Extract expiry from invalid token
        expiry = provider._extract_token_expiry('invalid.token.format')

        # Verify default expiry is returned (1 hour from now)
        assert expiry > int(time.time())
        assert expiry <= int(time.time()) + 3601  # Allow 1 second for execution time

    def test_extract_token_expiry_malformed_payload(self):
        """Test extracting expiry from a token with malformed payload."""
        # Create a token with invalid base64 in payload
        token = 'header.not_valid_base64.signature'

        # Create provider instance without calling __init__
        provider = CognitoAuthProvider.__new__(CognitoAuthProvider)

        # Extract expiry
        expiry = provider._extract_token_expiry(token)

        # Verify default expiry is returned
        assert expiry > int(time.time())
        assert expiry <= int(time.time()) + 3601  # Allow 1 second for execution time

    def test_determine_grant_type(self):
        """Test grant type determination logic."""
        # Create provider instance without calling __init__
        provider = CognitoAuthProvider.__new__(CognitoAuthProvider)

        # Test client credentials flow
        provider._client_id = 'test_client_id'
        provider._client_secret = 'test_client_secret'
        provider._domain = 'test-domain'
        provider._username = None
        provider._password = None

        assert provider._determine_grant_type() == 'client_credentials'

        # Test password flow
        provider._client_id = 'test_client_id'
        provider._client_secret = None
        provider._domain = None
        provider._username = 'test_user'
        provider._password = 'test_password'

        assert provider._determine_grant_type() == 'password'

        # Test default to password flow
        provider._client_id = 'test_client_id'
        provider._client_secret = None
        provider._domain = None
        provider._username = None
        provider._password = None

        assert provider._determine_grant_type() == 'password'

    @patch('requests.post')
    @patch('boto3.client')
    def test_get_cognito_token_client_credentials(self, mock_boto3, mock_post, mock_config):
        """Test _get_cognito_token with client credentials flow."""
        # Mock successful response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'access_token': 'test_access_token', 'expires_in': 3600}
        mock_post.return_value = mock_response

        # Create provider instance without calling __init__
        provider = CognitoAuthProvider.__new__(CognitoAuthProvider)
        provider._client_id = 'test_client_id'
        provider._client_secret = 'test_client_secret'
        provider._domain = 'test-domain'
        provider._region = 'us-east-1'
        provider._scopes = ['scope1', 'scope2']
        provider._token_expires_at = 0
        provider._grant_type = 'client_credentials'
        provider._username = None
        provider._password = None

        # Mock _get_token_client_credentials and _get_token_password
        with patch.object(
            provider, '_get_token_client_credentials', return_value='test_token'
        ) as mock_client_creds:
            with patch.object(provider, '_get_token_password') as mock_password:
                # Call the method
                token = provider._get_cognito_token()

                # Verify the correct method was called
                mock_client_creds.assert_called_once()
                mock_password.assert_not_called()
                assert token == 'test_token'

    @patch('requests.post')
    @patch('boto3.client')
    def test_get_cognito_token_password(self, mock_boto3, mock_post, mock_config):
        """Test _get_cognito_token with password flow."""
        # Create provider instance without calling __init__
        provider = CognitoAuthProvider.__new__(CognitoAuthProvider)
        provider._client_id = 'test_client_id'
        provider._client_secret = None
        provider._domain = None
        provider._region = 'us-east-1'
        provider._scopes = []
        provider._token_expires_at = 0
        provider._grant_type = 'password'
        provider._username = 'test_user'
        provider._password = 'test_password'

        # Mock _get_token_client_credentials and _get_token_password
        with patch.object(provider, '_get_token_client_credentials') as mock_client_creds:
            with patch.object(
                provider, '_get_token_password', return_value='test_token'
            ) as mock_password:
                # Call the method
                token = provider._get_cognito_token()

                # Verify the correct method was called
                mock_client_creds.assert_not_called()
                mock_password.assert_called_once()
                assert token == 'test_token'
