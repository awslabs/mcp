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

"""Unit tests for the InboundSigV4 inbound identity mechanism (Requirement 13.1)."""

import pytest
from awslabs.aws_healthomics_mcp_server.mechanisms.sigv4 import InboundSigV4
from awslabs.aws_healthomics_mcp_server.middleware import InboundMechanism
from awslabs.aws_healthomics_mcp_server.utils.aws_utils import (
    CredentialContext,
    CredentialDerivationError,
    InboundAuthError,
)


ACCESS_KEY_ID = 'AKIDEXAMPLE'
SIGV4_AUTHORIZATION = (
    'AWS4-HMAC-SHA256 '
    f'Credential={ACCESS_KEY_ID}/20150830/us-east-1/omics/aws4_request, '
    'SignedHeaders=host;x-amz-date, '
    'Signature=abcd1234'
)


def _scope(headers: list[tuple[bytes, bytes]]) -> dict:
    """Build a minimal ASGI HTTP scope carrying the given headers."""
    return {'type': 'http', 'headers': headers}


def test_implements_inbound_mechanism_protocol():
    """InboundSigV4 satisfies the InboundMechanism runtime protocol."""
    mechanism = InboundSigV4()
    assert isinstance(mechanism, InboundMechanism)
    assert mechanism.name == 'sigv4'


def test_applies_true_for_sigv4_authorization_header():
    """applies() is True when an AWS4-HMAC-SHA256 Authorization header is present."""
    scope = _scope([(b'authorization', SIGV4_AUTHORIZATION.encode('latin-1'))])
    assert InboundSigV4().applies(scope) is True


def test_applies_true_with_amz_date_and_security_token():
    """applies() is True for a typical SigV4 request with X-Amz-* headers."""
    scope = _scope(
        [
            (b'authorization', SIGV4_AUTHORIZATION.encode('latin-1')),
            (b'x-amz-date', b'20150830T123600Z'),
            (b'x-amz-security-token', b'session-token-value'),
        ]
    )
    assert InboundSigV4().applies(scope) is True


def test_applies_false_when_no_authorization_header():
    """applies() is False when there is no Authorization header."""
    scope = _scope([(b'x-amz-date', b'20150830T123600Z')])
    assert InboundSigV4().applies(scope) is False


def test_applies_false_for_non_sigv4_authorization_header():
    """applies() is False for a non-SigV4 (e.g. Bearer) Authorization header."""
    scope = _scope([(b'authorization', b'Bearer some.jwt.token')])
    assert InboundSigV4().applies(scope) is False


def test_applies_false_for_empty_headers():
    """applies() is False when the scope has no headers."""
    assert InboundSigV4().applies({'type': 'http', 'headers': []}) is False
    assert InboundSigV4().applies({'type': 'http'}) is False


def test_derive_parses_access_key_id_and_builds_context():
    """derive() parses the access key id and builds a usable sigv4 context."""
    scope = _scope(
        [
            (b'authorization', SIGV4_AUTHORIZATION.encode('latin-1')),
            (b'x-aho-forwarded-secret-access-key', b'forwarded-secret'),
        ]
    )
    ctx = InboundSigV4().derive(scope)
    assert isinstance(ctx, CredentialContext)
    assert ctx.identity_key == ACCESS_KEY_ID
    assert ctx.access_key_id == ACCESS_KEY_ID
    assert ctx.secret_access_key == 'forwarded-secret'  # pragma: allowlist secret
    assert ctx.session_token is None
    assert ctx.source == 'sigv4'


def test_derive_uses_forwarded_session_token_header():
    """derive() picks up the forwarded session token header when present."""
    scope = _scope(
        [
            (b'authorization', SIGV4_AUTHORIZATION.encode('latin-1')),
            (b'x-aho-forwarded-secret-access-key', b'forwarded-secret'),
            (b'x-aho-forwarded-session-token', b'forwarded-session'),
        ]
    )
    ctx = InboundSigV4().derive(scope)
    assert ctx.session_token == 'forwarded-session'


def test_derive_falls_back_to_amz_security_token():
    """derive() falls back to X-Amz-Security-Token for the session token."""
    scope = _scope(
        [
            (b'authorization', SIGV4_AUTHORIZATION.encode('latin-1')),
            (b'x-aho-forwarded-secret-access-key', b'forwarded-secret'),
            (b'x-amz-security-token', b'amz-session'),
        ]
    )
    ctx = InboundSigV4().derive(scope)
    assert ctx.session_token == 'amz-session'


def test_derive_raises_when_authorization_header_missing():
    """derive() raises CredentialDerivationError when no Authorization header."""
    scope = _scope([(b'x-aho-forwarded-secret-access-key', b'forwarded-secret')])
    with pytest.raises(CredentialDerivationError):
        InboundSigV4().derive(scope)


def test_derive_raises_for_non_sigv4_authorization_header():
    """derive() raises when the Authorization header is not SigV4."""
    scope = _scope(
        [
            (b'authorization', b'Bearer some.jwt.token'),
            (b'x-aho-forwarded-secret-access-key', b'forwarded-secret'),
        ]
    )
    with pytest.raises(CredentialDerivationError):
        InboundSigV4().derive(scope)


def test_derive_raises_for_malformed_credential_scope():
    """derive() raises when the Credential scope cannot be parsed."""
    scope = _scope(
        [
            (b'authorization', b'AWS4-HMAC-SHA256 SignedHeaders=host, Signature=abc'),
            (b'x-aho-forwarded-secret-access-key', b'forwarded-secret'),
        ]
    )
    with pytest.raises(CredentialDerivationError):
        InboundSigV4().derive(scope)


def test_derive_raises_when_forwarded_secret_absent():
    """derive() fails closed when no forwarded secret is available."""
    scope = _scope([(b'authorization', SIGV4_AUTHORIZATION.encode('latin-1'))])
    with pytest.raises(CredentialDerivationError) as exc_info:
        InboundSigV4().derive(scope)
    # CredentialDerivationError is an InboundAuthError the middleware can reject.
    assert isinstance(exc_info.value, InboundAuthError)


def test_derive_error_message_never_contains_credential_material():
    """A derivation error message must not leak forwarded secret material."""
    scope = _scope(
        [
            (b'authorization', b'AWS4-HMAC-SHA256 SignedHeaders=host, Signature=abc'),
            (b'x-aho-forwarded-secret-access-key', b'super-secret-value'),
        ]
    )
    with pytest.raises(CredentialDerivationError) as exc_info:
        InboundSigV4().derive(scope)
    assert 'super-secret-value' not in str(exc_info.value)
