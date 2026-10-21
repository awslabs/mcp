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

"""Tests for the auth module."""

import pytest
from awslabs.ec2rescue_for_linux_mcp_server.auth import (
    JWTTokenVerifier,
    get_auth_type_from_env,
    get_server_auth,
)
from unittest.mock import MagicMock, patch


class TestGetAuthTypeFromEnv:
    """Tests for get_auth_type_from_env."""

    def test_returns_none_when_not_set(self):
        """Should return None when AUTH_TYPE is not set."""
        with patch.dict('os.environ', {}, clear=True):
            assert get_auth_type_from_env() is None

    def test_returns_no_auth(self):
        """Should return 'no-auth' when AUTH_TYPE=no-auth."""
        with patch.dict('os.environ', {'AUTH_TYPE': 'no-auth'}):
            assert get_auth_type_from_env() == 'no-auth'

    def test_returns_oauth(self):
        """Should return 'oauth' when AUTH_TYPE=oauth."""
        with patch.dict('os.environ', {'AUTH_TYPE': 'oauth'}):
            assert get_auth_type_from_env() == 'oauth'

    def test_case_insensitive(self):
        """Should handle case-insensitive values."""
        with patch.dict('os.environ', {'AUTH_TYPE': 'OAuth'}):
            assert get_auth_type_from_env() == 'oauth'

    def test_strips_whitespace(self):
        """Should strip whitespace from value."""
        with patch.dict('os.environ', {'AUTH_TYPE': '  no-auth  '}):
            assert get_auth_type_from_env() == 'no-auth'

    def test_raises_on_invalid_value(self):
        """Should raise ValueError for invalid AUTH_TYPE values."""
        with patch.dict('os.environ', {'AUTH_TYPE': 'basic'}):
            with pytest.raises(ValueError, match='must be "no-auth" or "oauth"'):
                get_auth_type_from_env()


class TestGetServerAuth:
    """Tests for get_server_auth."""

    def test_stdio_returns_none(self):
        """Should return (None, None) for stdio transport."""
        auth_settings, token_verifier = get_server_auth('stdio')
        assert auth_settings is None
        assert token_verifier is None

    def test_streamable_http_requires_auth_type(self):
        """Should raise when AUTH_TYPE is not set for streamable-http."""
        with patch.dict('os.environ', {}, clear=True):
            with pytest.raises(ValueError, match='AUTH_TYPE environment variable must be set'):
                get_server_auth('streamable-http')

    def test_streamable_http_no_auth(self):
        """Should return (None, None) when AUTH_TYPE=no-auth."""
        with patch.dict('os.environ', {'AUTH_TYPE': 'no-auth'}):
            auth_settings, token_verifier = get_server_auth('streamable-http')
            assert auth_settings is None
            assert token_verifier is None

    def test_streamable_http_oauth_missing_issuer(self):
        """Should raise when AUTH_TYPE=oauth but AUTH_ISSUER is missing."""
        with patch.dict('os.environ', {'AUTH_TYPE': 'oauth'}, clear=True):
            with pytest.raises(ValueError, match='AUTH_ISSUER, AUTH_JWKS_URI and AUTH_AUDIENCE'):
                get_server_auth('streamable-http')

    def test_streamable_http_oauth_missing_jwks_uri(self):
        """Should raise when AUTH_TYPE=oauth but AUTH_JWKS_URI is missing."""
        env = {'AUTH_TYPE': 'oauth', 'AUTH_ISSUER': 'https://example.com'}
        with patch.dict('os.environ', env, clear=True):
            with pytest.raises(ValueError, match='AUTH_ISSUER, AUTH_JWKS_URI and AUTH_AUDIENCE'):
                get_server_auth('streamable-http')

    def test_streamable_http_oauth_missing_audience(self):
        """Should raise when AUTH_AUDIENCE is unset.

        Without an expected aud claim, any signature-valid token from the
        issuer would be accepted whichever service it was minted for.
        """
        env = {
            'AUTH_TYPE': 'oauth',
            'AUTH_ISSUER': 'https://auth.example.com',
            'AUTH_JWKS_URI': 'https://auth.example.com/.well-known/jwks.json',
        }
        with patch.dict('os.environ', env, clear=True):
            with pytest.raises(ValueError, match='AUTH_AUDIENCE'):
                get_server_auth('streamable-http')

    @pytest.mark.parametrize(
        'key,value',
        [
            ('AUTH_JWKS_URI', 'http://auth.example.com/.well-known/jwks.json'),
            ('AUTH_ISSUER', 'http://auth.example.com'),
            ('AUTH_JWKS_URI', 'auth.example.com/.well-known/jwks.json'),
            ('AUTH_JWKS_URI', 'ftp://auth.example.com/jwks'),
        ],
    )
    def test_streamable_http_oauth_requires_https(self, key, value):
        """Should reject a non-https issuer or JWKS URI."""
        env = {
            'AUTH_TYPE': 'oauth',
            'AUTH_ISSUER': 'https://auth.example.com',
            'AUTH_JWKS_URI': 'https://auth.example.com/.well-known/jwks.json',
            'AUTH_AUDIENCE': 'ec2rescue-mcp',
            key: value,
        }
        with patch.dict('os.environ', env, clear=True):
            with pytest.raises(ValueError, match=f'{key} must be an https URL'):
                get_server_auth('streamable-http')

    def test_streamable_http_oauth_with_audience(self):
        """Should return auth settings and verifier when fully configured."""
        env = {
            'AUTH_TYPE': 'oauth',
            'AUTH_ISSUER': 'https://auth.example.com',
            'AUTH_JWKS_URI': 'https://auth.example.com/.well-known/jwks.json',
            'AUTH_AUDIENCE': 'ec2rescue-mcp',
        }
        with patch.dict('os.environ', env, clear=True):
            auth_settings, token_verifier = get_server_auth('streamable-http')
            assert auth_settings is not None
            assert str(auth_settings.issuer_url) == 'https://auth.example.com/'
            assert isinstance(token_verifier, JWTTokenVerifier)
            assert token_verifier._audience == 'ec2rescue-mcp'


class TestJWTTokenVerifier:
    """Token verification must reject anything not minted for this server."""

    ISSUER = 'https://auth.example.com'
    AUDIENCE = 'ec2rescue-mcp'

    @pytest.fixture(scope='class')
    def signing_key(self):
        """An RSA key pair used to mint and verify test tokens."""
        from cryptography.hazmat.primitives.asymmetric import rsa

        return rsa.generate_private_key(public_exponent=65537, key_size=2048)

    @pytest.fixture
    def verifier(self, signing_key):
        """A verifier whose JWKS lookup returns the test public key."""
        from awslabs.ec2rescue_for_linux_mcp_server.auth import JWTTokenVerifier

        with patch('awslabs.ec2rescue_for_linux_mcp_server.auth.PyJWKClient') as jwks_client:
            jwks_client.return_value.get_signing_key_from_jwt.return_value = MagicMock(
                key=signing_key.public_key()
            )
            yield JWTTokenVerifier(
                issuer=self.ISSUER,
                jwks_uri=f'{self.ISSUER}/.well-known/jwks.json',
                audience=self.AUDIENCE,
            )

    def _mint(self, signing_key, **claims):
        """Sign a token, with claims overriding the valid defaults."""
        import jwt as pyjwt

        payload = {
            'iss': self.ISSUER,
            'aud': self.AUDIENCE,
            'sub': 'user-1',
            'exp': 9999999999,
            **claims,
        }
        return pyjwt.encode(payload, signing_key, algorithm='RS256')

    @pytest.mark.asyncio
    async def test_accepts_valid_token(self, verifier, signing_key):
        """A token minted for this server and issuer is accepted."""
        result = await verifier.verify_token(self._mint(signing_key))
        assert result is not None
        assert result.client_id == 'user-1'

    @pytest.mark.asyncio
    async def test_rejects_token_for_another_audience(self, verifier, signing_key):
        """A signature-valid token minted for a different service is rejected."""
        token = self._mint(signing_key, aud='some-other-service')
        assert await verifier.verify_token(token) is None

    @pytest.mark.asyncio
    async def test_rejects_token_without_aud_claim(self, verifier, signing_key):
        """A token carrying no aud claim at all is rejected."""
        import jwt as pyjwt

        token = pyjwt.encode(
            {'iss': self.ISSUER, 'sub': 'user-1', 'exp': 9999999999},
            signing_key,
            algorithm='RS256',
        )
        assert await verifier.verify_token(token) is None

    @pytest.mark.asyncio
    async def test_rejects_token_from_another_issuer(self, verifier, signing_key):
        """A token from a different issuer is rejected."""
        token = self._mint(signing_key, iss='https://evil.example.com')
        assert await verifier.verify_token(token) is None

    @pytest.mark.asyncio
    async def test_rejects_expired_token(self, verifier, signing_key):
        """An expired token is rejected."""
        assert await verifier.verify_token(self._mint(signing_key, exp=1)) is None

    @pytest.mark.asyncio
    async def test_rejects_token_signed_by_another_key(self, verifier):
        """A token signed by a key the JWKS endpoint does not vouch for is rejected."""
        from cryptography.hazmat.primitives.asymmetric import rsa

        other_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        assert await verifier.verify_token(self._mint(other_key)) is None

    @pytest.mark.asyncio
    async def test_offers_pyjwt_no_hmac_algorithm(self, verifier, signing_key):
        """The allow-list handed to PyJWT stays asymmetric-only.

        The JWKS public key is public by design, so accepting an HS* entry
        alongside it invites key confusion: a caller signs their own claims
        with that key as a shared secret. Adding 'HS256' for client
        compatibility would fail no other test in this file.
        """
        import awslabs.ec2rescue_for_linux_mcp_server.auth as auth

        with patch.object(auth.pyjwt, 'decode', wraps=auth.pyjwt.decode) as decode:
            assert await verifier.verify_token(self._mint(signing_key)) is not None

        algorithms = decode.call_args.kwargs['algorithms']
        assert algorithms, 'an empty allow-list would let the token pick'
        assert not [a for a in algorithms if a.upper().startswith('HS')]
