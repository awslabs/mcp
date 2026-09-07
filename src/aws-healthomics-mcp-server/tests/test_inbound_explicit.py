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

"""Unit tests for the InboundExplicitCredentials mechanism (Requirement 13.5).

These tests use obviously fake credential values only. They never log credential
material and assert the mechanism's contract: applies()/derive() behavior, header
case-insensitivity, optional session token, and defensive failure when required
headers are absent.
"""

import pytest
from awslabs.aws_healthomics_mcp_server.mechanisms.explicit import (
    InboundExplicitCredentials,
)
from awslabs.aws_healthomics_mcp_server.middleware import InboundMechanism
from awslabs.aws_healthomics_mcp_server.utils.aws_utils import (
    CredentialContext,
    CredentialDerivationError,
    InboundAuthError,
)


# Obviously fake, non-functional credential values used throughout these tests.
FAKE_ACCESS_KEY_ID = 'AKIAFAKEEXAMPLE12345'  # pragma: allowlist secret
FAKE_SECRET_ACCESS_KEY = 'fake-secret-not-a-real-key'  # pragma: allowlist secret
FAKE_SESSION_TOKEN = 'fake-session-token-not-real'


def _scope(headers: list[tuple[bytes, bytes]]) -> dict:
    """Build a minimal ASGI HTTP scope with the given headers."""
    return {'type': 'http', 'headers': headers}


def test_implements_inbound_mechanism_protocol():
    """The mechanism satisfies the InboundMechanism protocol and names itself."""
    mechanism = InboundExplicitCredentials()
    assert isinstance(mechanism, InboundMechanism)
    assert mechanism.name == 'explicit'


def test_applies_true_when_both_required_headers_present():
    """applies() is True when access-key-id and secret-access-key are present."""
    scope = _scope(
        [
            (b'x-aws-access-key-id', FAKE_ACCESS_KEY_ID.encode()),
            (b'x-aws-secret-access-key', FAKE_SECRET_ACCESS_KEY.encode()),
        ]
    )
    assert InboundExplicitCredentials().applies(scope) is True


def test_applies_true_with_session_token_present():
    """applies() is True when the optional session-token header is also present."""
    scope = _scope(
        [
            (b'x-aws-access-key-id', FAKE_ACCESS_KEY_ID.encode()),
            (b'x-aws-secret-access-key', FAKE_SECRET_ACCESS_KEY.encode()),
            (b'x-aws-session-token', FAKE_SESSION_TOKEN.encode()),
        ]
    )
    assert InboundExplicitCredentials().applies(scope) is True


def test_applies_case_insensitive_header_names():
    """applies() matches header names case-insensitively."""
    scope = _scope(
        [
            (b'X-AWS-Access-Key-Id', FAKE_ACCESS_KEY_ID.encode()),
            (b'X-Aws-Secret-Access-Key', FAKE_SECRET_ACCESS_KEY.encode()),
        ]
    )
    assert InboundExplicitCredentials().applies(scope) is True


def test_applies_false_when_secret_missing():
    """applies() is False when the secret-access-key header is absent."""
    scope = _scope([(b'x-aws-access-key-id', FAKE_ACCESS_KEY_ID.encode())])
    assert InboundExplicitCredentials().applies(scope) is False


def test_applies_false_when_access_key_missing():
    """applies() is False when the access-key-id header is absent."""
    scope = _scope([(b'x-aws-secret-access-key', FAKE_SECRET_ACCESS_KEY.encode())])
    assert InboundExplicitCredentials().applies(scope) is False


def test_applies_false_when_no_headers():
    """applies() is False when no headers are present."""
    assert InboundExplicitCredentials().applies(_scope([])) is False


def test_applies_false_when_required_header_empty():
    """applies() is False when a required header is present but empty."""
    scope = _scope(
        [
            (b'x-aws-access-key-id', b''),
            (b'x-aws-secret-access-key', FAKE_SECRET_ACCESS_KEY.encode()),
        ]
    )
    assert InboundExplicitCredentials().applies(scope) is False


def test_derive_builds_context_without_session_token():
    """derive() builds a context from headers when no session token is supplied."""
    scope = _scope(
        [
            (b'x-aws-access-key-id', FAKE_ACCESS_KEY_ID.encode()),
            (b'x-aws-secret-access-key', FAKE_SECRET_ACCESS_KEY.encode()),
        ]
    )
    ctx = InboundExplicitCredentials().derive(scope)
    assert isinstance(ctx, CredentialContext)
    assert ctx.identity_key == FAKE_ACCESS_KEY_ID
    assert ctx.access_key_id == FAKE_ACCESS_KEY_ID
    assert ctx.secret_access_key == FAKE_SECRET_ACCESS_KEY
    assert ctx.session_token is None
    assert ctx.source == 'explicit'


def test_derive_builds_context_with_session_token():
    """derive() includes the session token when the optional header is present."""
    scope = _scope(
        [
            (b'x-aws-access-key-id', FAKE_ACCESS_KEY_ID.encode()),
            (b'x-aws-secret-access-key', FAKE_SECRET_ACCESS_KEY.encode()),
            (b'x-aws-session-token', FAKE_SESSION_TOKEN.encode()),
        ]
    )
    ctx = InboundExplicitCredentials().derive(scope)
    assert ctx.session_token == FAKE_SESSION_TOKEN
    assert ctx.identity_key == FAKE_ACCESS_KEY_ID
    assert ctx.source == 'explicit'


def test_derive_case_insensitive_headers():
    """derive() reads credential values regardless of header name casing."""
    scope = _scope(
        [
            (b'X-Aws-Access-Key-Id', FAKE_ACCESS_KEY_ID.encode()),
            (b'X-AWS-SECRET-ACCESS-KEY', FAKE_SECRET_ACCESS_KEY.encode()),
            (b'X-Aws-Session-Token', FAKE_SESSION_TOKEN.encode()),
        ]
    )
    ctx = InboundExplicitCredentials().derive(scope)
    assert ctx.access_key_id == FAKE_ACCESS_KEY_ID
    assert ctx.secret_access_key == FAKE_SECRET_ACCESS_KEY
    assert ctx.session_token == FAKE_SESSION_TOKEN


def test_derive_treats_empty_session_token_as_none():
    """An empty session-token header is normalized to None, not an empty string."""
    scope = _scope(
        [
            (b'x-aws-access-key-id', FAKE_ACCESS_KEY_ID.encode()),
            (b'x-aws-secret-access-key', FAKE_SECRET_ACCESS_KEY.encode()),
            (b'x-aws-session-token', b''),
        ]
    )
    ctx = InboundExplicitCredentials().derive(scope)
    assert ctx.session_token is None


def test_derive_raises_when_required_headers_absent():
    """derive() raises CredentialDerivationError when required headers are missing."""
    with pytest.raises(CredentialDerivationError):
        InboundExplicitCredentials().derive(_scope([]))


def test_derive_raises_when_secret_missing():
    """derive() raises when only the access-key-id header is present."""
    scope = _scope([(b'x-aws-access-key-id', FAKE_ACCESS_KEY_ID.encode())])
    with pytest.raises(CredentialDerivationError):
        InboundExplicitCredentials().derive(scope)


def test_derivation_error_is_inbound_auth_error():
    """CredentialDerivationError is an InboundAuthError so the middleware rejects it."""
    scope = _scope([(b'x-aws-secret-access-key', FAKE_SECRET_ACCESS_KEY.encode())])
    with pytest.raises(InboundAuthError):
        InboundExplicitCredentials().derive(scope)
