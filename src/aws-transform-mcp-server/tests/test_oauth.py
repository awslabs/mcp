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

"""Tests for oauth module."""
# ruff: noqa: D101, D102, D103

import base64
import hashlib
import pytest
import urllib.request
from awslabs.aws_transform_mcp_server.models import RefreshedTokens
from awslabs.aws_transform_mcp_server.oauth import (
    _generate_pkce,
    refresh_access_token,
    run_oauth_flow,
)
from unittest.mock import MagicMock, patch


# ── PKCE generation ─────────────────────────────────────────────────────


class TestPKCE:
    """Tests for PKCE generation."""

    def test_verifier_length(self):
        verifier, _ = _generate_pkce()
        assert len(verifier) == 80

    def test_challenge_is_valid_base64url_sha256(self):
        verifier, challenge = _generate_pkce()
        expected_digest = hashlib.sha256(verifier.encode('ascii')).digest()
        expected_challenge = base64.urlsafe_b64encode(expected_digest).rstrip(b'=').decode('ascii')
        assert challenge == expected_challenge

    def test_no_padding_in_challenge(self):
        _, challenge = _generate_pkce()
        assert '=' not in challenge

    def test_verifier_is_url_safe(self):
        verifier, _ = _generate_pkce()
        # URL-safe base64 chars plus alphanumeric, hyphen, underscore
        for ch in verifier:
            assert ch.isalnum() or ch in '-_'


# ── refresh_access_token ────────────────────────────────────────────────


class TestRefreshAccessToken:
    """Tests for refresh_access_token."""

    @pytest.mark.asyncio
    async def test_refresh_success(self):
        mock_client = MagicMock()
        mock_client.create_token.return_value = {
            'accessToken': 'new-access',
            'refreshToken': 'new-refresh',
            'expiresIn': 3600,
        }

        with patch('awslabs.aws_transform_mcp_server.oauth.AwsHelper') as mock_helper:
            mock_helper.create_boto3_client.return_value = mock_client
            result = await refresh_access_token(
                idc_region='us-east-1',
                client_id='cid',
                client_secret='csec',  # pragma: allowlist secret
                refresh_token='old-ref',
            )

        assert result == RefreshedTokens(
            access_token='new-access',
            refresh_token='new-refresh',
            expires_in=3600,
        )
        mock_helper.create_boto3_client.assert_called_once_with(
            'sso-oidc', region_name='us-east-1'
        )
        mock_client.create_token.assert_called_once_with(
            clientId='cid',
            clientSecret='csec',  # pragma: allowlist secret
            grantType='refresh_token',
            refreshToken='old-ref',
        )

    @pytest.mark.asyncio
    async def test_refresh_no_access_token(self):
        mock_client = MagicMock()
        mock_client.create_token.return_value = {}

        with patch('awslabs.aws_transform_mcp_server.oauth.AwsHelper') as mock_helper:
            mock_helper.create_boto3_client.return_value = mock_client
            with pytest.raises(RuntimeError, match='No accessToken'):
                await refresh_access_token(
                    idc_region='us-east-1',
                    client_id='cid',
                    client_secret='csec',  # pragma: allowlist secret
                    refresh_token='old-ref',
                )


# ── run_oauth_flow ──────────────────────────────────────────────────────


class TestRunOAuthFlow:
    """Tests for run_oauth_flow end-to-end."""

    @pytest.mark.asyncio
    async def test_end_to_end(self):
        mock_client = MagicMock()
        mock_client.register_client.return_value = {
            'clientId': 'test-cid',
            'clientSecret': 'test-csec',  # pragma: allowlist secret
            'clientSecretExpiresAt': 9999999999,
            'authorizationEndpoint': 'https://auth.example.com/authorize',
        }
        mock_client.create_token.return_value = {
            'accessToken': 'test-access',
            'refreshToken': 'test-refresh',
            'expiresIn': 3600,
        }

        captured_url = None

        def fake_open(url):
            nonlocal captured_url
            captured_url = url
            # Simulate the callback by hitting the local server
            # Parse out the state from the authorize URL
            from urllib.parse import parse_qs, urlparse

            params = parse_qs(urlparse(url).query)
            state = params['state'][0]
            port = 18932  # must match the port we pass below
            callback_url = f'http://127.0.0.1:{port}/oauth/callback?code=test-code&state={state}'
            urllib.request.urlopen(callback_url, timeout=5)

        with (
            patch('awslabs.aws_transform_mcp_server.oauth.AwsHelper') as mock_helper,
            patch('awslabs.aws_transform_mcp_server.oauth._open_browser') as mock_wb,
        ):
            mock_helper.create_boto3_client.return_value = mock_client
            mock_wb.side_effect = fake_open

            result = await run_oauth_flow(
                start_url='https://sso.example.com/start',
                idc_region='us-east-1',
                scope='transform:read_write',
                port=18932,
                timeout_ms=10_000,
            )

        assert result.access_token == 'test-access'
        assert result.refresh_token == 'test-refresh'
        assert result.expires_in == 3600
        assert result.client_id == 'test-cid'
        assert result.client_secret == 'test-csec'  # pragma: allowlist secret
        assert result.client_secret_expires_at == 9999999999

        # Verify register_client was called correctly
        mock_client.register_client.assert_called_once_with(
            clientName='aws-transform-mcp',
            clientType='public',
            scopes=['transform:read_write'],
            grantTypes=['authorization_code', 'refresh_token'],
            redirectUris=['http://127.0.0.1:18932/oauth/callback'],
            issuerUrl='https://sso.example.com/start',
        )

        # Verify create_token was called with the auth code
        call_kwargs = mock_client.create_token.call_args[1]
        assert call_kwargs['grantType'] == 'authorization_code'
        assert call_kwargs['code'] == 'test-code'
        assert call_kwargs['clientId'] == 'test-cid'
        assert call_kwargs['clientSecret'] == 'test-csec'  # pragma: allowlist secret
        assert 'codeVerifier' in call_kwargs
        assert call_kwargs['redirectUri'] == 'http://127.0.0.1:18932/oauth/callback'

    @pytest.mark.asyncio
    async def test_timeout(self):
        mock_client = MagicMock()
        mock_client.register_client.return_value = {
            'clientId': 'test-cid',
            'clientSecret': 'test-csec',  # pragma: allowlist secret
            'clientSecretExpiresAt': 9999999999,
            'authorizationEndpoint': 'https://auth.example.com/authorize',
        }

        with (
            patch('awslabs.aws_transform_mcp_server.oauth.AwsHelper') as mock_helper,
            patch('awslabs.aws_transform_mcp_server.oauth._open_browser'),
        ):
            mock_helper.create_boto3_client.return_value = mock_client

            with pytest.raises(TimeoutError, match='timed out'):
                await run_oauth_flow(
                    start_url='https://sso.example.com/start',
                    idc_region='us-east-1',
                    scope='transform:read_write',
                    port=18933,
                    timeout_ms=500,  # very short timeout
                )

    @pytest.mark.asyncio
    async def test_state_mismatch(self):
        mock_client = MagicMock()
        mock_client.register_client.return_value = {
            'clientId': 'test-cid',
            'clientSecret': 'test-csec',  # pragma: allowlist secret
            'clientSecretExpiresAt': 9999999999,
            'authorizationEndpoint': 'https://auth.example.com/authorize',
        }

        def fake_open(url):
            port = 18934
            # Send callback with wrong state
            try:
                urllib.request.urlopen(
                    f'http://127.0.0.1:{port}/oauth/callback?code=test-code&state=wrong-state',
                    timeout=5,
                )
            except Exception:
                pass

        with (
            patch('awslabs.aws_transform_mcp_server.oauth.AwsHelper') as mock_helper,
            patch('awslabs.aws_transform_mcp_server.oauth._open_browser') as mock_wb,
        ):
            mock_helper.create_boto3_client.return_value = mock_client
            mock_wb.side_effect = fake_open

            with pytest.raises(RuntimeError, match='State parameter mismatch'):
                await run_oauth_flow(
                    start_url='https://sso.example.com/start',
                    idc_region='us-east-1',
                    scope='transform:read_write',
                    port=18934,
                    timeout_ms=5_000,
                )


# ── _open_browser ──────────────────────────────────────────────────────


class TestOpenBrowser:
    """Tests for _open_browser platform dispatch."""

    @patch('awslabs.aws_transform_mcp_server.oauth.platform.system', return_value='Darwin')
    @patch('awslabs.aws_transform_mcp_server.oauth.subprocess.Popen')
    def test_darwin(self, mock_popen, _mock_system):
        from awslabs.aws_transform_mcp_server.oauth import _open_browser

        _open_browser('https://example.com')
        mock_popen.assert_called_once()
        args = mock_popen.call_args[0][0]
        assert args == ['open', 'https://example.com']

    @patch('awslabs.aws_transform_mcp_server.oauth.platform.system', return_value='Windows')
    @patch('awslabs.aws_transform_mcp_server.oauth.os.startfile', create=True)
    def test_windows(self, mock_startfile, _mock_system):
        from awslabs.aws_transform_mcp_server.oauth import _open_browser

        _open_browser('https://example.com?foo=1&bar=2')
        mock_startfile.assert_called_once_with('https://example.com?foo=1&bar=2')

    @patch('awslabs.aws_transform_mcp_server.oauth.platform.system', return_value='Linux')
    @patch('awslabs.aws_transform_mcp_server.oauth.subprocess.Popen')
    def test_linux(self, mock_popen, _mock_system):
        from awslabs.aws_transform_mcp_server.oauth import _open_browser

        _open_browser('https://example.com')
        mock_popen.assert_called_once()
        args = mock_popen.call_args[0][0]
        assert args == ['xdg-open', 'https://example.com']

    @patch('awslabs.aws_transform_mcp_server.oauth.platform.system', return_value='Linux')
    @patch(
        'awslabs.aws_transform_mcp_server.oauth.subprocess.Popen',
        side_effect=OSError('no such file'),
    )
    def test_exception_prints_url(self, _mock_popen, _mock_system, capsys):
        from awslabs.aws_transform_mcp_server.oauth import _open_browser

        _open_browser('https://example.com')
        captured = capsys.readouterr()
        assert captured.err.startswith('Could not open browser')


# ── CallbackHandler ────────────────────────────────────────────────────


class TestCallbackHandler:
    """Tests for CallbackHandler.do_GET edge cases."""

    def test_non_callback_path_returns_404(self):
        """Requests to non-callback paths get 404."""
        from awslabs.aws_transform_mcp_server.oauth import CallbackHandler, OAuthState

        state = OAuthState('test-state')
        handler = MagicMock(spec=CallbackHandler)
        handler.path = '/some/other/path'
        handler.server = MagicMock()
        handler.server.oauth_state = state
        handler.send_response = MagicMock()
        handler.end_headers = MagicMock()

        CallbackHandler.do_GET(handler)
        handler.send_response.assert_called_once_with(404)

    def test_callback_with_error_param(self):
        """Callback with error parameter sets state.error."""
        from awslabs.aws_transform_mcp_server.oauth import CallbackHandler, OAuthState
        from io import BytesIO

        state = OAuthState('test-state')
        handler = MagicMock(spec=CallbackHandler)
        handler.path = '/oauth/callback?error=access_denied&error_description=User+denied'
        handler.server = MagicMock()
        handler.server.oauth_state = state
        handler.send_response = MagicMock()
        handler.send_header = MagicMock()
        handler.end_headers = MagicMock()
        handler.wfile = BytesIO()

        CallbackHandler.do_GET(handler)
        handler.send_response.assert_called_once_with(400)
        assert state.error is not None
        assert 'access_denied' in state.error
        assert state.code_received.is_set()

    def test_callback_missing_code(self):
        """Callback without code parameter sets error."""
        from awslabs.aws_transform_mcp_server.oauth import CallbackHandler, OAuthState
        from io import BytesIO

        state = OAuthState('test-state')
        handler = MagicMock(spec=CallbackHandler)
        handler.path = '/oauth/callback?state=test-state'
        handler.server = MagicMock()
        handler.server.oauth_state = state
        handler.send_response = MagicMock()
        handler.send_header = MagicMock()
        handler.end_headers = MagicMock()
        handler.wfile = BytesIO()

        CallbackHandler.do_GET(handler)
        handler.send_response.assert_called_once_with(400)
        assert state.error is not None
        assert 'No authorization code' in state.error
        assert state.code_received.is_set()

    def test_callback_state_mismatch(self):
        """Callback with wrong state parameter sets error."""
        from awslabs.aws_transform_mcp_server.oauth import CallbackHandler, OAuthState
        from io import BytesIO

        state = OAuthState('expected-state')
        handler = MagicMock(spec=CallbackHandler)
        handler.path = '/oauth/callback?code=test-code&state=wrong-state'
        handler.server = MagicMock()
        handler.server.oauth_state = state
        handler.send_response = MagicMock()
        handler.send_header = MagicMock()
        handler.end_headers = MagicMock()
        handler.wfile = BytesIO()

        CallbackHandler.do_GET(handler)
        handler.send_response.assert_called_once_with(400)
        assert state.error is not None
        assert 'State parameter mismatch' in state.error
        assert state.code_received.is_set()

    def test_callback_success(self):
        """Successful callback sets auth_code on state."""
        from awslabs.aws_transform_mcp_server.oauth import CallbackHandler, OAuthState
        from io import BytesIO

        state = OAuthState('correct-state')
        handler = MagicMock(spec=CallbackHandler)
        handler.path = '/oauth/callback?code=my-auth-code&state=correct-state'
        handler.server = MagicMock()
        handler.server.oauth_state = state
        handler.send_response = MagicMock()
        handler.send_header = MagicMock()
        handler.end_headers = MagicMock()
        handler.wfile = BytesIO()

        CallbackHandler.do_GET(handler)
        handler.send_response.assert_called_once_with(200)
        assert state.auth_code == 'my-auth-code'
        assert state.error is None
        assert state.code_received.is_set()


# ── run_oauth_flow: no auth code received ──────────────────────────────


class TestRunOAuthFlowNoAuthCode:
    """Tests for run_oauth_flow edge case where code_received fires but no auth code."""

    @pytest.mark.asyncio
    async def test_no_auth_code_received(self):
        """When callback fires the event but has no code, RuntimeError is raised."""
        mock_client = MagicMock()
        mock_client.register_client.return_value = {
            'clientId': 'test-cid',
            'clientSecret': 'test-csec',  # pragma: allowlist secret
            'clientSecretExpiresAt': 9999999999,
        }

        def fake_open(url):
            # Simulate a callback that sets code_received but not auth_code
            from urllib.parse import parse_qs, urlparse

            params = parse_qs(urlparse(url).query)
            _ = params['state'][0]
            port = 18940
            # Hit the callback with an error to trigger code_received but no auth_code
            # Actually, let's directly manipulate the OAuthState
            # We'll hit the callback with just an error
            try:
                urllib.request.urlopen(
                    f'http://127.0.0.1:{port}/oauth/callback?error=server_error'
                    f'&error_description=test_error',
                    timeout=5,
                )
            except Exception:
                pass

        with (
            patch('awslabs.aws_transform_mcp_server.oauth.AwsHelper') as mock_helper,
            patch('awslabs.aws_transform_mcp_server.oauth._open_browser') as mock_wb,
        ):
            mock_helper.create_boto3_client.return_value = mock_client
            mock_wb.side_effect = fake_open

            with pytest.raises(RuntimeError, match='OAuth error'):
                await run_oauth_flow(
                    start_url='https://sso.example.com/start',
                    idc_region='us-east-1',
                    scope='transform:read_write',
                    port=18940,
                    timeout_ms=5_000,
                )
