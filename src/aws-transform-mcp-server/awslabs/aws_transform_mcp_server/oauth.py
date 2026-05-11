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

"""OAuth Authorization Code + PKCE flow using AWS SSO OIDC."""

import base64
import hashlib
import os
import platform
import secrets
import subprocess
import sys
import threading
from awslabs.aws_transform_mcp_server.aws_helper import AwsHelper
from awslabs.aws_transform_mcp_server.models import OAuthTokens, RefreshedTokens
from html import escape
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Optional, Tuple
from urllib.parse import parse_qs, urlencode, urlparse


def _open_browser(url: str) -> None:
    """Open a URL in the default browser.

    Uses platform-specific commands (matching the npm 'open' package behavior)
    instead of Python's webbrowser module, which can fail silently when running
    as a subprocess spawned by an MCP client.

    Args:
        url: The URL to open.
    """
    try:
        popen_kwargs = {
            'stdout': subprocess.DEVNULL,
            'stderr': subprocess.DEVNULL,
            'start_new_session': True,
        }
        system = platform.system()
        if system == 'Darwin':
            subprocess.Popen(['open', url], **popen_kwargs)
        elif system == 'Windows':
            os.startfile(url)  # type: ignore[attr-defined]  # Windows-only API
        else:
            subprocess.Popen(['xdg-open', url], **popen_kwargs)
    except Exception:
        # The URL must be shown so the user can complete OAuth login manually.
        # It contains only the authorize endpoint + PKCE challenge (public values),
        # not tokens or secrets.
        print(  # codeql[py/clear-text-logging-sensitive-data]
            f'Could not open browser. Please open this URL manually:\n{url}',
            file=sys.stderr,
        )


def _generate_pkce() -> Tuple[str, str]:
    """Generate a PKCE code_verifier and code_challenge (S256).

    Returns:
        A (code_verifier, code_challenge) tuple.
    """
    code_verifier = secrets.token_urlsafe(60)[:80]
    digest = hashlib.sha256(code_verifier.encode('ascii')).digest()
    code_challenge = base64.urlsafe_b64encode(digest).rstrip(b'=').decode('ascii')
    return code_verifier, code_challenge


class OAuthState:
    """Shared state between the OAuth flow and the HTTP callback handler."""

    def __init__(self, expected_state: str) -> None:
        """Initialize OAuth state."""
        self.expected_state = expected_state
        self.auth_code: Optional[str] = None
        self.error: Optional[str] = None
        self.code_received = threading.Event()


class CallbackHandler(BaseHTTPRequestHandler):
    """HTTP handler that captures the OAuth callback.

    Access ``oauth_state`` via ``self.server.oauth_state`` (set per-server instance).
    """

    def do_GET(self) -> None:  # noqa: D102
        if not self.path.startswith('/oauth/callback'):
            self.send_response(404)
            self.end_headers()
            return

        params = parse_qs(urlparse(self.path).query)
        state = self.server.oauth_state

        error = params.get('error', [None])[0]
        if error:
            error_desc = params.get('error_description', [''])[0]
            self.send_response(400)
            self.send_header('Content-Type', 'text/html')
            self.end_headers()
            self.wfile.write(
                f'<html><body><h1>Error</h1><p>{escape(error)}: {escape(error_desc)}</p></body></html>'.encode()  # noqa: E501
            )
            state.error = f'{error}: {error_desc}'
            state.code_received.set()
            return

        code = params.get('code', [None])[0]
        cb_state = params.get('state', [None])[0]

        if not code:
            self.send_response(400)
            self.send_header('Content-Type', 'text/html')
            self.end_headers()
            self.wfile.write(
                b'<html><body><h1>Error</h1><p>No authorization code received.</p></body></html>'  # noqa: E501
            )
            state.error = 'No authorization code in callback'
            state.code_received.set()
            return

        if cb_state != state.expected_state:
            self.send_response(400)
            self.send_header('Content-Type', 'text/html')
            self.end_headers()
            self.wfile.write(
                b'<html><body><h1>Error</h1><p>State mismatch (possible CSRF).</p></body></html>'  # noqa: E501
            )
            state.error = 'State parameter mismatch'
            state.code_received.set()
            return

        self.send_response(200)
        self.send_header('Content-Type', 'text/html')
        self.end_headers()
        self.wfile.write(
            b'<html><body><h1>Success!</h1>'
            b'<p>Authorization complete. You can close this window.</p></body></html>'
        )
        state.auth_code = code
        state.code_received.set()

    def log_message(self, format: str, *args: object) -> None:  # noqa: D102
        # Suppress default request logging
        pass


async def run_oauth_flow(
    start_url: str,
    idc_region: str,
    scope: str,
    port: int = 8079,
    timeout_ms: int = 120_000,
) -> OAuthTokens:
    """Run the full OAuth Authorization Code Grant with PKCE flow.

    Steps:
        1. Generate PKCE verifier/challenge
        2. Register a temporary public OIDC client
        3. Start a local HTTP server for the callback
        4. Open the browser to the authorization URL
        5. Wait for the callback with the auth code
        6. Exchange the code for tokens

    Args:
        start_url: IAM Identity Center start URL (issuerUrl).
        idc_region: AWS region for the SSO OIDC client.
        scope: OAuth scope string.
        port: Local port for the callback server.
        timeout_ms: Timeout in milliseconds waiting for the callback.

    Returns:
        An OAuthTokens instance with access_token, refresh_token, expires_in,
        client_id, client_secret, client_secret_expires_at.
    """
    redirect_uri = f'http://127.0.0.1:{port}/oauth/callback'

    # Step 1: PKCE
    code_verifier, code_challenge = _generate_pkce()
    state = secrets.token_hex(16)

    # Step 2: Register client
    sso_oidc = AwsHelper.create_boto3_client('sso-oidc', region_name=idc_region)
    reg = sso_oidc.register_client(
        clientName='aws-transform-mcp',
        clientType='public',
        scopes=[scope],
        grantTypes=['authorization_code', 'refresh_token'],
        redirectUris=[redirect_uri],
        issuerUrl=start_url,
    )
    client_id = reg['clientId']
    client_secret = reg['clientSecret']
    client_secret_expires_at = reg['clientSecretExpiresAt']
    # The public SSO-OIDC endpoint does not return authorizationEndpoint
    # in the register_client response. Construct it from the region.
    # URL pattern confirmed via: https://aws.amazon.com/blogs/developer/
    # aws-cli-adds-pkce-based-authorization-for-sso/
    authorization_endpoint = f'https://oidc.{idc_region}.amazonaws.com/authorize'

    # Step 3: Start callback server
    oauth_state = OAuthState(state)

    server = HTTPServer(('127.0.0.1', port), CallbackHandler)
    server.oauth_state = oauth_state
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()

    # Step 4: Build authorize URL and open browser
    authorize_url = f'{authorization_endpoint}?' + urlencode(
        {
            'response_type': 'code',
            'client_id': client_id,
            'redirect_uri': redirect_uri,
            'scope': scope,
            'state': state,
            'code_challenge': code_challenge,
            'code_challenge_method': 'S256',
        }
    )

    print('Opening browser for authentication...', file=sys.stderr)
    print(  # codeql[py/clear-text-logging-sensitive-data]
        f'If the browser does not open, visit:\n{authorize_url}',
        file=sys.stderr,
    )
    _open_browser(authorize_url)

    # Step 5: Wait for callback
    timeout_secs = timeout_ms / 1000.0
    try:
        if not oauth_state.code_received.wait(timeout=timeout_secs):
            raise TimeoutError(f'Authentication timed out after {timeout_secs}s')

        if oauth_state.error:
            raise RuntimeError(f'OAuth error: {oauth_state.error}')

        if not oauth_state.auth_code:
            raise RuntimeError('No authorization code received')

        # Step 6: Exchange code for tokens
        token_resp = sso_oidc.create_token(
            clientId=client_id,
            clientSecret=client_secret,
            grantType='authorization_code',
            code=oauth_state.auth_code,
            codeVerifier=code_verifier,
            redirectUri=redirect_uri,
        )
        return OAuthTokens(
            access_token=token_resp['accessToken'],
            refresh_token=token_resp.get('refreshToken'),
            expires_in=token_resp.get('expiresIn', 0),
            client_id=client_id,
            client_secret=client_secret,
            client_secret_expires_at=client_secret_expires_at,
        )
    finally:
        server.shutdown()
        server.oauth_state = None


async def refresh_access_token(
    idc_region: str,
    client_id: str,
    client_secret: str,
    refresh_token: str,
) -> RefreshedTokens:
    """Refresh an access token using the refresh_token grant.

    Args:
        idc_region: AWS region for the SSO OIDC client.
        client_id: The OIDC client ID.
        client_secret: The OIDC client secret.
        refresh_token: The refresh token.

    Returns:
        A RefreshedTokens instance with access_token, refresh_token (optional), expires_in.
    """
    sso_oidc = AwsHelper.create_boto3_client('sso-oidc', region_name=idc_region)
    result = sso_oidc.create_token(
        clientId=client_id,
        clientSecret=client_secret,
        grantType='refresh_token',
        refreshToken=refresh_token,
    )

    if not result.get('accessToken'):
        raise RuntimeError('No accessToken in refresh response')

    return RefreshedTokens(
        access_token=result['accessToken'],
        refresh_token=result.get('refreshToken'),
        expires_in=result.get('expiresIn', 0),
    )
