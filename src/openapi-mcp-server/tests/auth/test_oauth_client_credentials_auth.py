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
"""Tests for the generic OAuth 2.0 client credentials authentication provider."""

import base64
import json
import pytest
import time
from awslabs.openapi_mcp_server.api.config import Config
from awslabs.openapi_mcp_server.auth.auth_errors import (
    ExpiredTokenError,
    InvalidCredentialsError,
    MissingCredentialsError,
)
from awslabs.openapi_mcp_server.auth.oauth_client_credentials_auth import (
    OAuthClientCredentialsAuthProvider,
)
from unittest.mock import MagicMock, patch


class TestOAuthClientCredentialsAuth:
    """Tests for the generic OAuth 2.0 client credentials authentication provider."""

    @pytest.fixture
    def mock_config(self):
        """Create a mock config for testing."""
        config = MagicMock(spec=Config)
        config.auth_oauth_token_endpoint = 'https://example.com/oauth/token'
        config.auth_oauth_client_id = 'test_client_id'
        config.auth_oauth_client_secret = 'test_client_secret'  # pragma: allowlist secret
        config.auth_oauth_scopes = 'scope1,scope2'
        config.auth_token = None
        return config

    def _make_provider(self, scopes=None):
        """Create an OAuthClientCredentialsAuthProvider without calling __init__."""
        provider = OAuthClientCredentialsAuthProvider.__new__(OAuthClientCredentialsAuthProvider)
        provider._token_endpoint = 'https://example.com/oauth/token'
        provider._oauth_client_id = 'test_client_id'
        provider._oauth_client_secret = 'test_client_secret'  # pragma: allowlist secret
        provider._oauth_scopes = scopes if scopes is not None else ['scope1', 'scope2']
        provider._token_expires_at = 0
        return provider

    # ------------------------------------------------------------------
    # _fetch_oauth_token
    # ------------------------------------------------------------------

    @patch('httpx.post')
    def test_fetch_oauth_token_success(self, mock_post):
        """Test successful token acquisition."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'access_token': 'test_token', 'expires_in': 3600}
        mock_post.return_value = mock_response

        provider = self._make_provider()
        token = provider._fetch_oauth_token()

        assert token == 'test_token'
        assert provider._token_expires_at > time.time()

        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        assert args[0] == 'https://example.com/oauth/token'
        assert kwargs['data']['grant_type'] == 'client_credentials'
        assert kwargs['data']['scope'] == 'scope1 scope2'

        # Verify Basic auth header
        auth_header = kwargs['headers']['Authorization']
        assert auth_header.startswith('Basic ')
        decoded = base64.b64decode(auth_header[6:]).decode()
        assert decoded == 'test_client_id:test_client_secret'

    @patch('httpx.post')
    def test_fetch_oauth_token_no_scopes(self, mock_post):
        """Test token acquisition with no scopes — scope key must be absent."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'access_token': 'test_token', 'expires_in': 3600}
        mock_post.return_value = mock_response

        provider = self._make_provider(scopes=[])
        token = provider._fetch_oauth_token()

        assert token == 'test_token'
        args, kwargs = mock_post.call_args
        assert 'scope' not in kwargs['data']

    @patch('httpx.post')
    def test_fetch_oauth_token_error_response(self, mock_post):
        """Test that a non-200 response raises InvalidCredentialsError."""
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.text = 'invalid_client'
        mock_post.return_value = mock_response

        provider = self._make_provider()
        with pytest.raises(InvalidCredentialsError) as excinfo:
            provider._fetch_oauth_token()

        assert 'Failed to obtain token with client credentials' in str(excinfo.value)
        assert 'invalid_client' in str(excinfo.value.details.get('error', ''))

    @patch('httpx.post')
    def test_fetch_oauth_token_missing_access_token(self, mock_post):
        """Test that a response with no access_token returns None."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'expires_in': 3600}
        mock_post.return_value = mock_response

        provider = self._make_provider()
        token = provider._fetch_oauth_token()
        assert token is None

    @patch('httpx.post')
    def test_fetch_oauth_token_network_exception(self, mock_post):
        """Test that a network exception propagates."""
        mock_post.side_effect = Exception('Connection refused')

        provider = self._make_provider()
        with pytest.raises(Exception) as excinfo:
            provider._fetch_oauth_token()
        assert 'Connection refused' in str(excinfo.value)

    # ------------------------------------------------------------------
    # _extract_token_expiry
    # ------------------------------------------------------------------

    def test_extract_token_expiry_valid_jwt(self):
        """Test extracting expiry from a valid JWT."""
        exp = int(time.time()) + 3600
        header_b64 = (
            base64.urlsafe_b64encode(json.dumps({'alg': 'RS256'}).encode()).decode().rstrip('=')
        )
        payload_b64 = (
            base64.urlsafe_b64encode(json.dumps({'exp': exp}).encode()).decode().rstrip('=')
        )
        token = f'{header_b64}.{payload_b64}.sig'

        provider = OAuthClientCredentialsAuthProvider.__new__(OAuthClientCredentialsAuthProvider)
        assert provider._extract_token_expiry(token) == exp

    def test_extract_token_expiry_malformed_defaults_one_hour(self):
        """Test that a malformed token defaults to ~1 hour from now."""
        provider = OAuthClientCredentialsAuthProvider.__new__(OAuthClientCredentialsAuthProvider)
        expiry = provider._extract_token_expiry('not.a.jwt')
        assert expiry > time.time()
        assert expiry <= time.time() + 3601

    # ------------------------------------------------------------------
    # _is_token_expired_or_expiring_soon / _check_and_refresh_token_if_needed
    # ------------------------------------------------------------------

    def test_is_token_expired_or_expiring_soon_expired(self):
        """Token with past expiry should be flagged."""
        provider = self._make_provider()
        provider._token_expires_at = time.time() - 1
        assert provider._is_token_expired_or_expiring_soon() is True

    def test_is_token_expired_or_expiring_soon_within_5min(self):
        """Token expiring within 5 minutes should be flagged."""
        provider = self._make_provider()
        provider._token_expires_at = time.time() + 200  # < 300 s
        assert provider._is_token_expired_or_expiring_soon() is True

    def test_is_token_expired_or_expiring_soon_valid(self):
        """Token with plenty of time left should not be flagged."""
        provider = self._make_provider()
        provider._token_expires_at = time.time() + 3600
        assert provider._is_token_expired_or_expiring_soon() is False

    # ------------------------------------------------------------------
    # _refresh_token
    # ------------------------------------------------------------------

    def test_refresh_token_success(self):
        """Test that _refresh_token updates _token and re-initialises auth."""
        provider = self._make_provider()
        provider._token = 'old_token'

        with patch.object(provider, '_fetch_oauth_token', return_value='new_token'):
            with patch.object(provider, '_initialize_auth') as mock_init:
                provider._refresh_token()
                assert provider._token == 'new_token'
                mock_init.assert_called_once()

    def test_refresh_token_same_token_skips_init(self):
        """If _fetch_oauth_token returns the same token, _initialize_auth is not called."""
        provider = self._make_provider()
        provider._token = 'same_token'

        with patch.object(provider, '_fetch_oauth_token', return_value='same_token'):
            with patch.object(provider, '_initialize_auth') as mock_init:
                provider._refresh_token()
                mock_init.assert_not_called()

    def test_refresh_token_raises_expired_token_error_on_none(self):
        """Test that a None return from _fetch_oauth_token raises ExpiredTokenError."""
        provider = self._make_provider()
        provider._token = 'old_token'

        with patch.object(provider, '_fetch_oauth_token', return_value=None):
            with pytest.raises(ExpiredTokenError):
                provider._refresh_token()

    def test_refresh_token_raises_expired_token_error_on_failure(self):
        """Test that a failing refresh raises ExpiredTokenError."""
        provider = self._make_provider()
        provider._token = 'old_token'

        with patch.object(provider, '_fetch_oauth_token', side_effect=Exception('timeout')):
            with pytest.raises(ExpiredTokenError):
                provider._refresh_token()

    # ------------------------------------------------------------------
    # _validate_config
    # ------------------------------------------------------------------

    def test_validate_config_missing_token_endpoint(self):
        """Test validation error when token endpoint is missing."""
        provider = self._make_provider()
        provider._token_endpoint = ''
        with pytest.raises(MissingCredentialsError):
            provider._validate_config()

    def test_validate_config_missing_client_id(self):
        """Test validation error when client ID is missing."""
        provider = self._make_provider()
        provider._oauth_client_id = ''
        with pytest.raises(MissingCredentialsError):
            provider._validate_config()

    def test_validate_config_missing_client_secret(self):
        """Test validation error when client secret is missing."""
        provider = self._make_provider()
        provider._oauth_client_secret = ''
        with pytest.raises(MissingCredentialsError):
            provider._validate_config()

    # ------------------------------------------------------------------
    # provider_name
    # ------------------------------------------------------------------

    def test_provider_name(self):
        """Test provider name."""
        provider = self._make_provider()
        assert provider.provider_name == 'oauth_client_credentials'
