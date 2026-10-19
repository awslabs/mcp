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

"""Authentication configuration for the EC2Rescue for Linux MCP Server.

When the server runs with ``--transport=streamable-http``, it requires
the ``AUTH_TYPE`` environment variable to be explicitly set:

* ``no-auth`` — disables authentication (operator explicitly opts out).
* ``oauth``   — enables OAuth 2.0 JWT Bearer token verification via JWKS.

Required environment variables for ``AUTH_TYPE=oauth``:

* ``AUTH_ISSUER``   — expected ``iss`` claim in the JWT. Must be https.
* ``AUTH_JWKS_URI`` — URL of the JWKS endpoint for token signature
  verification. Must be https.
* ``AUTH_AUDIENCE`` — expected ``aud`` claim. Required: without it any
  signature-valid token from the issuer would be accepted, whichever service
  it was minted for.
"""

from __future__ import annotations

import jwt as pyjwt
import os
from jwt import PyJWKClient
from loguru import logger
from mcp.server.auth.provider import AccessToken, TokenVerifier
from mcp.server.auth.settings import AuthSettings
from pydantic import AnyHttpUrl
from typing import Literal
from urllib.parse import urlsplit


# Environment variable keys
_AUTH_TYPE_KEY = 'AUTH_TYPE'
_AUTH_ISSUER_KEY = 'AUTH_ISSUER'
_AUTH_JWKS_URI_KEY = 'AUTH_JWKS_URI'
_AUTH_AUDIENCE_KEY = 'AUTH_AUDIENCE'


class JWTTokenVerifier:
    """Verify OAuth 2.0 Bearer tokens using a remote JWKS endpoint.

    Implements the :class:`~mcp.server.auth.provider.TokenVerifier` protocol
    expected by FastMCP's ``token_verifier`` parameter.
    """

    def __init__(self, issuer: str, jwks_uri: str, audience: str):
        """Store the expected issuer and audience, and open the JWKS client."""
        self._issuer = issuer
        self._audience = audience
        self._jwks_client = PyJWKClient(jwks_uri, cache_jwk_set=True, lifespan=300)

    async def verify_token(self, token: str) -> AccessToken | None:
        """Verify a Bearer token and return access info if valid."""
        try:
            signing_key = self._jwks_client.get_signing_key_from_jwt(token)

            # Passing both issuer and audience makes `iss` and `aud` required:
            # PyJWT raises MissingRequiredClaimError when either is absent.
            payload = pyjwt.decode(
                token,
                key=signing_key.key,
                # Asymmetric only. The JWKS public key is public, so an HS*
                # entry here would accept it as a shared HMAC secret.
                algorithms=['RS256', 'RS384', 'RS512', 'ES256', 'ES384', 'ES512'],
                issuer=self._issuer,
                audience=self._audience,
            )

            # Extract standard claims
            client_id = payload.get('client_id') or payload.get('sub', 'unknown')
            scopes = payload.get('scope', '').split() if payload.get('scope') else []
            expires_at = payload.get('exp')

            return AccessToken(
                token=token,
                client_id=client_id,
                scopes=scopes,
                expires_at=expires_at,
            )
        except pyjwt.ExpiredSignatureError:
            logger.warning('JWT token expired')
            return None
        except pyjwt.InvalidTokenError as e:
            logger.warning(f'JWT token validation failed: {e}')
            return None
        except Exception as e:
            logger.error(f'Unexpected error during token verification: {e}')
            return None


def _require_https(key: str, value: str) -> str:
    """Reject a non-https URL in an authentication setting."""
    if urlsplit(value).scheme.lower() != 'https':
        raise ValueError(
            f'{key} must be an https URL, got: {value!r}. Authentication '
            'decisions depend on this endpoint, so plaintext is not accepted.'
        )
    return value


def get_auth_type_from_env() -> Literal['no-auth', 'oauth'] | None:
    """Read AUTH_TYPE from environment. Returns None when not set."""
    value = os.environ.get(_AUTH_TYPE_KEY)
    if value is None:
        return None
    value = value.strip().lower()
    if value not in ('no-auth', 'oauth'):
        raise ValueError(f'{_AUTH_TYPE_KEY} must be "no-auth" or "oauth", got: {value!r}')
    return value  # type: ignore[return-value]


def get_server_auth(
    transport: str,
) -> tuple[AuthSettings | None, TokenVerifier | None]:
    """Configure authentication for the MCP server.

    Returns a (auth_settings, token_verifier) tuple suitable for passing to
    ``FastMCP(auth=..., token_verifier=...)``.

    For stdio transport, returns (None, None) — no authentication needed.
    For streamable-http, requires AUTH_TYPE to be explicitly set.
    """
    if transport != 'streamable-http':
        return None, None

    auth_type = get_auth_type_from_env()

    if auth_type is None:
        raise ValueError(
            'When using --transport=streamable-http, the AUTH_TYPE environment '
            'variable must be set to "no-auth" or "oauth". '
            'Set AUTH_TYPE=no-auth to explicitly disable authentication, or '
            'AUTH_TYPE=oauth with AUTH_ISSUER and AUTH_JWKS_URI for JWT verification.'
        )

    if auth_type == 'no-auth':
        logger.warning(
            'AUTH_TYPE=no-auth: streamable-http transport running WITHOUT '
            'authentication. Ensure network access is properly restricted.'
        )
        return None, None

    # auth_type == 'oauth'
    issuer = os.environ.get(_AUTH_ISSUER_KEY)
    jwks_uri = os.environ.get(_AUTH_JWKS_URI_KEY)
    audience = os.environ.get(_AUTH_AUDIENCE_KEY)

    if not issuer or not jwks_uri or not audience:
        raise ValueError(
            'AUTH_TYPE=oauth requires the following environment variables: '
            f'{_AUTH_ISSUER_KEY}, {_AUTH_JWKS_URI_KEY} and '
            f'{_AUTH_AUDIENCE_KEY}. {_AUTH_AUDIENCE_KEY} is required because '
            'without an expected aud claim any signature-valid token from the '
            'issuer would be accepted, whichever service it was minted for.'
        )

    _require_https(_AUTH_ISSUER_KEY, issuer)
    _require_https(_AUTH_JWKS_URI_KEY, jwks_uri)

    logger.info(
        f'OAuth JWT authentication enabled: issuer={issuer}, '
        f'jwks_uri={jwks_uri}, audience={audience}'
    )

    auth_settings = AuthSettings(
        issuer_url=AnyHttpUrl(issuer),
        resource_server_url=None,
    )
    token_verifier = JWTTokenVerifier(
        issuer=issuer,
        jwks_uri=jwks_uri,
        audience=audience,
    )

    return auth_settings, token_verifier
