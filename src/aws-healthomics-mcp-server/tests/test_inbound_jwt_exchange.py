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

"""Unit tests for the InboundJwtExchange mechanism (Requirements 13.2-13.4).

These tests never use real tokens or credentials. The JWT is a fabricated,
unsigned token whose payload only carries a ``sub`` claim, and the STS client is a
stub that records calls and returns fabricated credentials.
"""

import base64
import json
import pytest
from awslabs.aws_healthomics_mcp_server.mechanisms.jwt_exchange import (
    InboundJwtExchange,
    _decode_jwt_claims,
    _sanitize_session_name,
)
from awslabs.aws_healthomics_mcp_server.middleware import InboundMechanism
from awslabs.aws_healthomics_mcp_server.utils.aws_utils import (
    CredentialContext,
    CredentialDerivationError,
    InboundAuthError,
)
from botocore.exceptions import BotoCoreError, ClientError


ROLE_ARN = 'arn:aws:iam::123456789012:role/per-tenant-role'
FAKE_ACCESS_KEY_ID = 'ASIAEXAMPLE'  # pragma: allowlist secret
FAKE_SECRET_ACCESS_KEY = 'fake-secret-value'  # pragma: allowlist secret
FAKE_SESSION_TOKEN = 'fake-session-token'  # pragma: allowlist secret


def _make_jwt(claims: dict) -> str:
    """Build an unsigned compact JWT carrying the given claims (no signature)."""

    def _b64(obj: dict) -> str:
        raw = json.dumps(obj).encode('utf-8')
        return base64.urlsafe_b64encode(raw).rstrip(b'=').decode('ascii')

    header = _b64({'alg': 'none', 'typ': 'JWT'})
    payload = _b64(claims)
    return f'{header}.{payload}.'


def _scope(headers: list[tuple[bytes, bytes]]) -> dict:
    """Build a minimal ASGI HTTP scope carrying the given headers."""
    return {'type': 'http', 'headers': headers}


def _bearer_scope(token: str) -> dict:
    """Build an ASGI scope with an Authorization: Bearer header."""
    return _scope([(b'authorization', f'Bearer {token}'.encode('latin-1'))])


class _StubStsClient:
    """Records assume_role calls and returns fabricated credentials."""

    def __init__(self, error: Exception | None = None):
        self.error = error
        self.calls: list[dict] = []

    def assume_role(self, **kwargs):
        self.calls.append(kwargs)
        if self.error is not None:
            raise self.error
        return {
            'Credentials': {
                'AccessKeyId': FAKE_ACCESS_KEY_ID,
                'SecretAccessKey': FAKE_SECRET_ACCESS_KEY,
                'SessionToken': FAKE_SESSION_TOKEN,
            },
            'AssumedRoleUser': {
                'Arn': f'{ROLE_ARN}/session',
                'AssumedRoleId': 'AROAEXAMPLE:session',
            },
        }


def _factory(client: _StubStsClient):
    """Return a sts_client_factory that yields the given stub client."""

    def _make(region=None):
        return client

    return _make


def test_implements_inbound_mechanism_protocol():
    """InboundJwtExchange satisfies the InboundMechanism protocol and names itself."""
    mechanism = InboundJwtExchange(role_arn=ROLE_ARN)
    assert isinstance(mechanism, InboundMechanism)
    assert mechanism.name == 'jwt'


def test_applies_true_for_bearer_token():
    """applies() is True when an Authorization: Bearer header is present."""
    token = _make_jwt({'sub': 'caller-1'})
    assert InboundJwtExchange(role_arn=ROLE_ARN).applies(_bearer_scope(token)) is True


def test_applies_false_without_authorization_header():
    """applies() is False when no Authorization header is present."""
    assert InboundJwtExchange(role_arn=ROLE_ARN).applies(_scope([])) is False


def test_applies_false_for_non_bearer_authorization():
    """applies() is False for a non-Bearer Authorization scheme."""
    scope = _scope([(b'authorization', b'Basic dXNlcjpwYXNz')])
    assert InboundJwtExchange(role_arn=ROLE_ARN).applies(scope) is False


def test_derive_success_builds_context_with_abac_tag():
    """derive() exchanges the JWT and builds a jwt-sourced context with ABAC tag."""
    client = _StubStsClient()
    token = _make_jwt({'sub': 'caller-1'})
    mechanism = InboundJwtExchange(role_arn=ROLE_ARN, sts_client_factory=_factory(client))

    ctx = mechanism.derive(_bearer_scope(token))

    assert isinstance(ctx, CredentialContext)
    assert ctx.identity_key == 'caller-1'
    assert ctx.access_key_id == FAKE_ACCESS_KEY_ID
    assert ctx.secret_access_key == FAKE_SECRET_ACCESS_KEY
    assert ctx.session_token == FAKE_SESSION_TOKEN
    assert ctx.source == 'jwt'

    # Exactly one assume_role call, with ABAC session tags identifying the caller.
    assert len(client.calls) == 1
    call = client.calls[0]
    assert call['RoleArn'] == ROLE_ARN
    assert call['Tags'] == [{'Key': 'caller', 'Value': 'caller-1'}]
    assert call['RoleSessionName']


def test_derive_passes_configured_tag_key_and_duration():
    """derive() honors a custom tag key, caller claim, and session duration."""
    client = _StubStsClient()
    token = _make_jwt({'tenant': 'tenant-42'})
    mechanism = InboundJwtExchange(
        role_arn=ROLE_ARN,
        session_duration=900,
        caller_claim='tenant',
        tag_key='tenant',
        sts_client_factory=_factory(client),
    )

    ctx = mechanism.derive(_bearer_scope(token))

    assert ctx.identity_key == 'tenant-42'
    call = client.calls[0]
    assert call['DurationSeconds'] == 900
    assert call['Tags'] == [{'Key': 'tenant', 'Value': 'tenant-42'}]


def test_derive_raises_on_sts_client_error_without_context():
    """STS ClientError -> CredentialDerivationError; no context, single AWS call."""
    error = ClientError(
        error_response={'Error': {'Code': 'AccessDenied', 'Message': 'denied'}},
        operation_name='AssumeRole',
    )
    client = _StubStsClient(error=error)
    token = _make_jwt({'sub': 'caller-1'})
    mechanism = InboundJwtExchange(role_arn=ROLE_ARN, sts_client_factory=_factory(client))

    with pytest.raises(CredentialDerivationError) as exc_info:
        mechanism.derive(_bearer_scope(token))

    # The only AWS call was the failed assume_role; no other AWS call is made.
    assert len(client.calls) == 1
    assert isinstance(exc_info.value, InboundAuthError)


def test_derive_raises_on_botocore_error():
    """STS BotoCoreError -> CredentialDerivationError (auth error)."""
    client = _StubStsClient(error=BotoCoreError())
    token = _make_jwt({'sub': 'caller-1'})
    mechanism = InboundJwtExchange(role_arn=ROLE_ARN, sts_client_factory=_factory(client))

    with pytest.raises(CredentialDerivationError):
        mechanism.derive(_bearer_scope(token))


def test_derive_raises_when_no_bearer_token():
    """derive() with no bearer token raises and never calls STS."""
    client = _StubStsClient()
    mechanism = InboundJwtExchange(role_arn=ROLE_ARN, sts_client_factory=_factory(client))

    with pytest.raises(CredentialDerivationError):
        mechanism.derive(_scope([]))
    assert client.calls == []


def test_derive_raises_when_caller_claim_missing():
    """A JWT lacking the configured caller claim fails before any STS call."""
    client = _StubStsClient()
    token = _make_jwt({'aud': 'someone'})
    mechanism = InboundJwtExchange(role_arn=ROLE_ARN, sts_client_factory=_factory(client))

    with pytest.raises(CredentialDerivationError):
        mechanism.derive(_bearer_scope(token))
    # No AWS call is made when the token is unusable (Requirement 13.4).
    assert client.calls == []


def test_derive_raises_on_malformed_token():
    """A malformed (non-JWT) bearer token fails before any STS call."""
    client = _StubStsClient()
    mechanism = InboundJwtExchange(role_arn=ROLE_ARN, sts_client_factory=_factory(client))

    with pytest.raises(CredentialDerivationError):
        mechanism.derive(_bearer_scope('not-a-jwt'))
    assert client.calls == []


def test_error_never_leaks_token_value():
    """The derivation error message never includes the raw token value."""
    client = _StubStsClient()
    secret_sub = 'super-secret-subject'  # pragma: allowlist secret
    token = _make_jwt({'aud': secret_sub})  # missing 'sub' -> error path
    mechanism = InboundJwtExchange(role_arn=ROLE_ARN, sts_client_factory=_factory(client))

    with pytest.raises(CredentialDerivationError) as exc_info:
        mechanism.derive(_bearer_scope(token))
    assert token not in str(exc_info.value)


def test_decode_jwt_claims_reads_sub():
    """_decode_jwt_claims decodes a payload without verifying the signature."""
    token = _make_jwt({'sub': 'abc', 'extra': 1})
    claims = _decode_jwt_claims(token)
    assert claims['sub'] == 'abc'
    assert claims['extra'] == 1


def test_sanitize_session_name_replaces_invalid_chars():
    """_sanitize_session_name produces a valid, bounded RoleSessionName."""
    name = _sanitize_session_name('user:with/invalid chars')
    assert ':' not in name
    assert '/' not in name
    assert ' ' not in name
    assert 0 < len(name) <= 64


def test_sanitize_session_name_falls_back_when_empty():
    """_sanitize_session_name falls back to a default when nothing usable remains."""
    assert _sanitize_session_name('::://') == 'jwt-caller'
