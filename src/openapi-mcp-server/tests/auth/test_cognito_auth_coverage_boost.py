"""Test to improve coverage for cognito_auth.py - one test case at a time."""

import pytest
from awslabs.openapi_mcp_server.api.config import Config
from awslabs.openapi_mcp_server.auth.cognito_auth import CognitoAuthProvider
from unittest.mock import MagicMock, patch


class TestCognitoAuthCoverageBoost:
    """Tests to improve coverage for CognitoAuth - adding one test at a time."""

    @patch.object(CognitoAuthProvider, '_get_cognito_token')
    def test_cognito_auth_init_exception_handling(self, mock_get_token):
        """Test exception handling during CognitoAuthProvider initialization."""
        # Mock _get_cognito_token to raise an exception
        mock_get_token.side_effect = Exception('Network error')

        # Create config
        config = Config(
            api_name='test',
            api_base_url='https://api.example.com',
            api_spec_url='https://api.example.com/spec.json',
            auth_type='cognito',
            auth_cognito_user_pool_id='us-east-1_test123',
            auth_cognito_client_id='test_client_id',
            auth_cognito_username='testuser',
            auth_cognito_password='testpass',
        )

        # This should raise MissingCredentialsError because no token was obtained
        from awslabs.openapi_mcp_server.auth.auth_errors import MissingCredentialsError

        with pytest.raises(MissingCredentialsError):
            CognitoAuthProvider(config)

    @patch.object(CognitoAuthProvider, '_get_cognito_token')
    def test_cognito_auth_successful_validation(self, mock_get_token):
        """Test successful CognitoAuthProvider validation."""
        # Mock _get_cognito_token to return a valid token
        mock_get_token.return_value = 'valid_token_123'

        # Create config
        config = Config(
            api_name='test',
            api_base_url='https://api.example.com',
            api_spec_url='https://api.example.com/spec.json',
            auth_type='cognito',
            auth_cognito_user_pool_id='us-east-1_test123',
            auth_cognito_client_id='test_client_id',
            auth_cognito_username='testuser',
            auth_cognito_password='testpass',
        )

        # This should succeed and create the auth provider
        auth = CognitoAuthProvider(config)

        # Verify the auth object was created successfully
        assert auth is not None
        assert auth.provider_name == 'cognito'
        assert auth.is_configured() is True

    @patch('boto3.client')
    def test_get_cognito_token_successful_auth(self, mock_boto_client):
        """Test _get_cognito_token with successful authentication - covers lines 205-390."""
        # Mock the boto3 client and its response
        mock_client = MagicMock()
        mock_boto_client.return_value = mock_client

        # Mock successful initiate_auth response
        mock_client.initiate_auth.return_value = {
            'AuthenticationResult': {
                'IdToken': 'test_id_token_123',
                'AccessToken': 'test_access_token',
                'RefreshToken': 'test_refresh_token',
                'ExpiresIn': 3600,
            }
        }

        # Create config
        config = Config(
            api_name='test',
            api_base_url='https://api.example.com',
            api_spec_url='https://api.example.com/spec.json',
            auth_type='cognito',
            auth_cognito_user_pool_id='us-east-1_test123',
            auth_cognito_client_id='test_client_id',
            auth_cognito_username='testuser',
            auth_cognito_password='testpass',
        )

        # Create auth provider (this will call _get_cognito_token internally)
        auth = CognitoAuthProvider(config)

        # Verify the token was obtained and stored
        assert auth.is_configured() is True

        # Verify boto3 client was called correctly
        mock_boto_client.assert_called_with('cognito-idp', region_name='us-east-1')
        mock_client.initiate_auth.assert_called_once()

    @patch('boto3.client')
    def test_refresh_cognito_token_successful(self, mock_boto_client):
        """Test _refresh_cognito_token with successful refresh - covers lines 405-470."""
        # Mock the boto3 client and its response
        mock_client = MagicMock()
        mock_boto_client.return_value = mock_client

        # Mock successful initiate_auth response for initial token
        mock_client.initiate_auth.return_value = {
            'AuthenticationResult': {
                'IdToken': 'initial_token_123',
                'AccessToken': 'initial_access_token',
                'RefreshToken': 'initial_refresh_token',
                'ExpiresIn': 3600,
            }
        }

        # Create config
        config = Config(
            api_name='test',
            api_base_url='https://api.example.com',
            api_spec_url='https://api.example.com/spec.json',
            auth_type='cognito',
            auth_cognito_user_pool_id='us-east-1_test123',
            auth_cognito_client_id='test_client_id',
            auth_cognito_username='testuser',
            auth_cognito_password='testpass',
        )

        # Create auth provider
        auth = CognitoAuthProvider(config)

        # Now mock the refresh response
        mock_client.initiate_auth.return_value = {
            'AuthenticationResult': {
                'IdToken': 'refreshed_token_456',
                'AccessToken': 'refreshed_access_token',
                'RefreshToken': 'refreshed_refresh_token',
                'ExpiresIn': 3600,
            }
        }

        # Call the refresh method directly to cover the refresh logic
        refreshed_token = auth._refresh_cognito_token()

        # Verify the refresh was successful
        assert refreshed_token == 'refreshed_token_456'

        # Verify boto3 client was called for refresh
        assert mock_client.initiate_auth.call_count == 2  # Initial + refresh

    def test_extract_token_expiry_valid_jwt(self):
        """Test _extract_token_expiry with valid JWT token - covers lines 492-524."""
        # Create a valid JWT token with expiry
        import base64
        import json
        import time

        # Create payload with expiry timestamp (1 hour from now)
        future_exp = int(time.time()) + 3600
        payload_data = {'sub': 'test-user', 'exp': future_exp, 'iat': int(time.time())}

        # Encode payload as base64url
        payload_json = json.dumps(payload_data)
        payload_b64 = base64.b64encode(payload_json.encode()).decode()
        # Convert to base64url format
        payload_b64url = payload_b64.replace('+', '-').replace('/', '_').rstrip('=')

        # Create a mock JWT token (header.payload.signature)
        header_b64url = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9'  # Mock header
        signature_b64url = 'mock_signature'  # Mock signature
        jwt_token = f'{header_b64url}.{payload_b64url}.{signature_b64url}'

        # Create config and auth provider
        config = Config(
            api_name='test',
            api_base_url='https://api.example.com',
            api_spec_url='https://api.example.com/spec.json',
            auth_type='cognito',
            auth_cognito_user_pool_id='us-east-1_test123',
            auth_cognito_client_id='test_client_id',
            auth_cognito_username='testuser',
            auth_cognito_password='testpass',
        )

        # Mock _get_cognito_token to avoid actual auth
        with patch.object(CognitoAuthProvider, '_get_cognito_token', return_value='mock_token'):
            auth = CognitoAuthProvider(config)

        # Test the _extract_token_expiry method
        extracted_exp = auth._extract_token_expiry(jwt_token)

        # Verify the expiry was extracted correctly
        assert extracted_exp == future_exp
