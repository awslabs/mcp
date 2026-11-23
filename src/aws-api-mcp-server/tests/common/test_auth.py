import pytest
from awslabs.aws_api_mcp_server.core.common.auth import ClientIdJWTVerifier
from fastmcp.server.auth import JWTVerifier
from fastmcp.server.auth.providers.jwt import RSAKeyPair


ISSUER = 'https://cognito-idp.us-east-1.amazonaws.com/us-east-1_example'


@pytest.fixture
def key_pair() -> RSAKeyPair:
    """Generate an RSA key pair to sign test tokens with."""
    return RSAKeyPair.generate()


@pytest.fixture
def verifier(key_pair: RSAKeyPair) -> ClientIdJWTVerifier:
    """Build a verifier that only accepts tokens from the MCP server's client."""
    return ClientIdJWTVerifier(
        client_id='mcp-server-client',
        public_key=key_pair.public_key,
        issuer=ISSUER,
    )


def test_requires_a_client_id(key_pair: RSAKeyPair):
    """Test the verifier refuses to be built without a client ID."""
    with pytest.raises(ValueError, match='client_id must not be empty'):
        ClientIdJWTVerifier(client_id='', public_key=key_pair.public_key, issuer=ISSUER)


async def test_token_from_expected_client_is_accepted(
    key_pair: RSAKeyPair, verifier: ClientIdJWTVerifier
):
    """Test a token carrying the expected client_id claim is accepted."""
    token = key_pair.create_token(
        issuer=ISSUER, additional_claims={'client_id': 'mcp-server-client'}
    )

    access_token = await verifier.verify_token(token)

    assert access_token is not None
    assert access_token.client_id == 'mcp-server-client'


async def test_token_from_other_client_in_same_tenant_is_rejected(
    key_pair: RSAKeyPair, verifier: ClientIdJWTVerifier
):
    """Test a token minted for another application in the same tenant is rejected."""
    token = key_pair.create_token(
        issuer=ISSUER, additional_claims={'client_id': 'unrelated-app-client'}
    )

    assert await verifier.verify_token(token) is None


async def test_token_without_client_id_claim_is_rejected(
    key_pair: RSAKeyPair, verifier: ClientIdJWTVerifier
):
    """Test a token that does not identify the requesting application is rejected."""
    token = key_pair.create_token(issuer=ISSUER, subject='mcp-server-client')

    assert await verifier.verify_token(token) is None


async def test_azp_claim_is_accepted(key_pair: RSAKeyPair, verifier: ClientIdJWTVerifier):
    """Test the `azp` claim is used by issuers that do not emit `client_id`."""
    token = key_pair.create_token(issuer=ISSUER, additional_claims={'azp': 'mcp-server-client'})

    assert await verifier.verify_token(token) is not None


async def test_other_issuer_is_still_rejected(key_pair: RSAKeyPair, verifier: ClientIdJWTVerifier):
    """Test the checks inherited from JWTVerifier still apply."""
    token = key_pair.create_token(
        issuer='https://other-issuer.example.com',
        additional_claims={'client_id': 'mcp-server-client'},
    )

    assert await verifier.verify_token(token) is None


async def test_audience_check_alone_cannot_cover_tokens_without_aud(key_pair: RSAKeyPair):
    """Test why AUTH_CLIENT_ID exists: an audience check rejects every token without `aud`.

    Issuers such as Amazon Cognito never populate `aud` in access tokens, so an
    audience-only configuration cannot distinguish their applications.
    """
    verifier = JWTVerifier(public_key=key_pair.public_key, issuer=ISSUER, audience='my-mcp-server')

    assert await verifier.verify_token(key_pair.create_token(issuer=ISSUER)) is None
    assert (
        await verifier.verify_token(key_pair.create_token(issuer=ISSUER, audience='my-mcp-server'))
        is not None
    )
    assert (
        await verifier.verify_token(
            key_pair.create_token(issuer=ISSUER, audience='some-other-resource')
        )
        is None
    )


async def test_audience_and_client_id_are_both_enforced(key_pair: RSAKeyPair):
    """Test audience validation is combined with client ID validation when both are set."""
    verifier = ClientIdJWTVerifier(
        client_id='mcp-server-client',
        public_key=key_pair.public_key,
        issuer=ISSUER,
        audience='my-mcp-server',
    )

    wrong_audience_token = key_pair.create_token(
        issuer=ISSUER,
        audience='some-other-resource',
        additional_claims={'client_id': 'mcp-server-client'},
    )
    valid_token = key_pair.create_token(
        issuer=ISSUER,
        audience='my-mcp-server',
        additional_claims={'client_id': 'mcp-server-client'},
    )

    assert await verifier.verify_token(wrong_audience_token) is None
    assert await verifier.verify_token(valid_token) is not None
