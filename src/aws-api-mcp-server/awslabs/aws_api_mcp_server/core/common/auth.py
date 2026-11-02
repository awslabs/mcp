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

"""Token verification for the MCP server running with OAuth authentication."""

from fastmcp.server.auth import AccessToken, JWTVerifier
from loguru import logger


class ClientIdJWTVerifier(JWTVerifier):
    """JWT verifier that also requires tokens to be issued to a given client ID.

    Some issuers do not populate the `aud` claim in access tokens, Amazon Cognito
    being the most common one: its access tokens identify the application that
    requested them through the `client_id` claim instead. For those issuers an
    audience check cannot tell which application a token was minted for, so this
    verifier validates the client identity claim on top of everything
    `JWTVerifier` already validates (signature, issuer, expiry and audience).

    `load_access_token` is the hook rather than `verify_token` because
    `JWTVerifier.verify_token` delegates to it, so overriding it covers both
    entry points.
    """

    def __init__(self, *, client_id: str, **kwargs):
        """Initialize the verifier with the client ID whose tokens are accepted.

        Args:
            client_id: The client ID that is allowed to call this server.
            **kwargs: Arguments forwarded to `JWTVerifier`.
        """
        super().__init__(**kwargs)

        if not client_id:
            raise ValueError('client_id must not be empty')

        self.client_id = client_id

    async def load_access_token(self, token: str) -> AccessToken | None:
        """Validate a JWT bearer token and check it was issued to the expected client.

        Args:
            token: The JWT bearer token string to validate.

        Returns:
            An `AccessToken` when the token is valid and was issued to the
            expected client ID, `None` otherwise.
        """
        access_token = await super().load_access_token(token)

        if access_token is None:
            return None

        claims = access_token.claims or {}
        # Only the claims that identify the requesting application are read here.
        # `sub` identifies the user, not the application, so unlike
        # AccessToken.client_id this does not fall back to it.
        token_client_id = claims.get('client_id') or claims.get('azp')

        if token_client_id != self.client_id:
            logger.warning(
                'Bearer token rejected: client ID mismatch (got {}, expected {})',
                token_client_id,
                self.client_id,
            )
            return None

        return access_token
