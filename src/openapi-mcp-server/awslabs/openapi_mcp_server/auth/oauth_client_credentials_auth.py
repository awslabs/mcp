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
"""Generic OAuth 2.0 client credentials authentication provider."""

import base64
import httpx
import json
import threading
import time
from awslabs.openapi_mcp_server import logger
from awslabs.openapi_mcp_server.api.config import Config
from awslabs.openapi_mcp_server.auth.auth_errors import (
    ExpiredTokenError,
    InvalidCredentialsError,
    MissingCredentialsError,
)
from awslabs.openapi_mcp_server.auth.bearer_auth import BearerAuthProvider
from typing import Dict, List, Optional


class OAuthClientCredentialsAuthProvider(BearerAuthProvider):
    """Generic OAuth 2.0 client credentials authentication provider.

    Obtains a Bearer token via the OAuth 2.0 client credentials flow and
    delegates to BearerAuthProvider for adding Authorization headers.
    Tokens are refreshed automatically 5 minutes before expiry.

    Configuration (environment variables / CLI arguments):

    - ``AUTH_OAUTH_TOKEN_ENDPOINT`` / ``--auth-oauth-token-endpoint``
    - ``AUTH_OAUTH_CLIENT_ID`` / ``--auth-oauth-client-id``
    - ``AUTH_OAUTH_CLIENT_SECRET`` / ``--auth-oauth-client-secret``
    - ``AUTH_OAUTH_SCOPES`` / ``--auth-oauth-scopes`` (optional, comma-separated)

    Subclasses may pre-set ``_token_endpoint``, ``_oauth_client_id``,
    ``_oauth_client_secret``, and ``_oauth_scopes`` as instance variables
    before calling ``super().__init__(config)``; those values take precedence
    over what would be read from config.
    """

    def __init__(self, config: Config):
        """Initialize with configuration.

        Reads OAuth parameters from config unless already set by a subclass.
        """
        # Respect values pre-set by subclasses; fall back to generic config fields.
        self._token_endpoint: str = getattr(
            self, '_token_endpoint', config.auth_oauth_token_endpoint
        )
        self._oauth_client_id: str = getattr(self, '_oauth_client_id', config.auth_oauth_client_id)
        self._oauth_client_secret: str = getattr(
            self, '_oauth_client_secret', config.auth_oauth_client_secret
        )
        raw_scopes: str = getattr(self, '_raw_oauth_scopes', config.auth_oauth_scopes)
        self._oauth_scopes: List[str] = (
            [s.strip() for s in raw_scopes.split(',') if s.strip()] if raw_scopes else []
        )

        # Token expiry tracking
        self._token_expires_at: float = 0
        self._token_lock = threading.RLock()

        logger.debug(
            f'OAuth client credentials: endpoint={self._token_endpoint}, '
            f'client_id={self._oauth_client_id}, '
            f'secret={"SET" if self._oauth_client_secret else "NOT SET"}'
        )

        # Fetch the initial token and hand it to BearerAuthProvider via config.
        try:
            if self._oauth_client_id and self._oauth_client_secret and self._token_endpoint:
                token = self._fetch_oauth_token()
                if token:
                    config.auth_token = token
            else:
                logger.warning(
                    'Missing OAuth client credentials or token endpoint; '
                    'skipping initial token acquisition'
                )
        except Exception as e:
            logger.warning(f'Failed to get initial OAuth token: {e}')
            config.auth_token = 'PENDING_OAUTH_TOKEN'

        super().__init__(config)

    # ------------------------------------------------------------------
    # Token acquisition
    # ------------------------------------------------------------------

    def _fetch_oauth_token(self) -> Optional[str]:
        """POST to the token endpoint and return the access token.

        Raises:
            InvalidCredentialsError: When the server rejects the credentials.

        """
        auth_header = base64.b64encode(
            f'{self._oauth_client_id}:{self._oauth_client_secret}'.encode('utf-8')
        ).decode('utf-8')

        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Authorization': f'Basic {auth_header}',
        }
        data: Dict[str, str] = {'grant_type': 'client_credentials'}
        if self._oauth_scopes:
            data['scope'] = ' '.join(self._oauth_scopes)
            logger.debug(f'Requesting scopes: {data["scope"]}')

        logger.debug(f'Fetching OAuth token from: {self._token_endpoint}')
        response = httpx.post(self._token_endpoint, headers=headers, data=data)

        if response.status_code != 200:
            logger.error(f'Token request failed: {response.status_code} {response.text}')
            raise InvalidCredentialsError(
                'Failed to obtain token with client credentials',
                {
                    'error': response.text,
                    'help': 'Check client ID, client secret, and token endpoint',
                },
            )

        token_data = response.json()
        access_token = token_data.get('access_token')
        expires_in = token_data.get('expires_in', 3600)

        if access_token:
            self._token_expires_at = time.time() + expires_in
            logger.info(f'OAuth token obtained (expires in {expires_in}s)')
            return access_token

        logger.error('No access_token in token endpoint response')
        return None

    # ------------------------------------------------------------------
    # Token expiry and auto-refresh
    # ------------------------------------------------------------------

    def _extract_token_expiry(self, token: str) -> float:
        """Extract expiry timestamp from a JWT, defaulting to 1 hour from now."""
        try:
            parts = token.split('.')
            if len(parts) != 3:
                raise ValueError('Not a three-part JWT')
            payload = parts[1]
            padding = '=' * ((4 - len(payload) % 4) % 4)
            payload = payload.replace('-', '+').replace('_', '/') + padding
            payload_data = json.loads(base64.b64decode(payload).decode('utf-8'))
            exp = float(payload_data.get('exp', 0))
            if exp > 0:
                logger.info(f'Token expires in {(exp - time.time()) / 60:.0f} minutes')
            return exp
        except Exception as e:
            logger.warning(f'Could not decode token expiry: {e}; defaulting to 1 hour')
            return time.time() + 3600

    def _is_token_expired_or_expiring_soon(self) -> bool:
        """Return True if the token is expired or will expire within 5 minutes."""
        return time.time() + 300 >= self._token_expires_at

    def _check_and_refresh_token_if_needed(self) -> None:
        """Refresh the token when it is expired or about to expire."""
        with self._token_lock:
            if self._is_token_expired_or_expiring_soon():
                self._do_refresh_token()

    def _do_refresh_token(self) -> None:
        """Fetch a fresh token and update internal state."""
        try:
            new_token = self._fetch_oauth_token()
            if new_token and new_token != self._token:
                self._token = new_token
                logger.info('OAuth token refreshed')
                self._initialize_auth()
        except Exception as e:
            logger.error(f'Failed to refresh OAuth token: {e}')
            raise ExpiredTokenError('OAuth token refresh failed', {'error': str(e)})

    # ------------------------------------------------------------------
    # BearerAuthProvider override
    # ------------------------------------------------------------------

    def get_auth_headers(self) -> Dict[str, str]:
        """Return auth headers, refreshing the token first if needed."""
        self._check_and_refresh_token_if_needed()
        return super().get_auth_headers()

    # ------------------------------------------------------------------
    # Config validation
    # ------------------------------------------------------------------

    def _validate_config(self) -> bool:
        if not self._token_endpoint:
            raise MissingCredentialsError(
                'OAuth client credentials requires a token endpoint URL',
                {'help': 'Set AUTH_OAUTH_TOKEN_ENDPOINT or --auth-oauth-token-endpoint'},
            )
        if not self._oauth_client_id:
            raise MissingCredentialsError(
                'OAuth client credentials requires a client ID',
                {'help': 'Set AUTH_OAUTH_CLIENT_ID or --auth-oauth-client-id'},
            )
        if not self._oauth_client_secret:
            raise MissingCredentialsError(
                'OAuth client credentials requires a client secret',
                {'help': 'Set AUTH_OAUTH_CLIENT_SECRET or --auth-oauth-client-secret'},
            )
        return super()._validate_config()

    def _log_validation_error(self) -> None:
        logger.error(
            'OAuth client credentials requires AUTH_OAUTH_TOKEN_ENDPOINT, '
            'AUTH_OAUTH_CLIENT_ID, and AUTH_OAUTH_CLIENT_SECRET.'
        )

    @property
    def provider_name(self) -> str:
        """Get the name of the authentication provider."""
        return 'oauth_client_credentials'
