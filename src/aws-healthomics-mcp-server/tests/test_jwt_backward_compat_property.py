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

"""End-to-end backward-compatibility property test for the ``jwt`` mechanism.

This module pins the static ``MCP_JWT_ROLE_ARN`` behavior end-to-end: it builds
an ``InboundJwtExchange`` exactly as the server does when only ``MCP_JWT_ROLE_ARN``
is configured -- injecting the default ``StaticRoleResolver(role_arn)`` -- and
drives ``derive`` from a fabricated unsigned bearer token whose only claim under
test is the caller identity (``sub``). For any caller identity, the resulting
``sts:AssumeRole`` call must reproduce the pre-feature static behavior: the
configured ARN, a caller-derived session name, the ``caller`` session tag, and no
``ExternalId``.

Property: Backward compatibility.

Validates: Requirements Backward Compatibility.

No real tokens, credentials, or AWS calls are used: the JWT is a fabricated
unsigned token and the STS client is a stub that records ``assume_role`` calls and
returns fabricated credentials.
"""

import base64
import json
from awslabs.aws_healthomics_mcp_server.mechanisms.jwt_exchange import InboundJwtExchange
from awslabs.aws_healthomics_mcp_server.mechanisms.role_resolver import StaticRoleResolver
from hypothesis import given, settings
from hypothesis import strategies as st


ROLE_ARN = 'arn:aws:iam::123456789012:role/static-single-role'
FAKE_ACCESS_KEY_ID = 'ASIAEXAMPLE'  # pragma: allowlist secret
FAKE_SECRET_ACCESS_KEY = 'fake-secret-value'  # pragma: allowlist secret
FAKE_SESSION_TOKEN = 'fake-session-token'  # pragma: allowlist secret

# Arbitrary caller identity strings for the ``sub`` claim. Non-empty printable
# text (including characters outside the STS session-name set) exercises the
# session-name sanitization while keeping the caller claim usable.
caller_identities = st.text(
    alphabet=st.characters(min_codepoint=0x21, max_codepoint=0x7E),
    min_size=1,
    max_size=80,
)


def _make_jwt(claims: dict) -> str:
    """Build an unsigned compact JWT carrying the given claims (no signature)."""

    def _b64(obj: dict) -> str:
        raw = json.dumps(obj).encode('utf-8')
        return base64.urlsafe_b64encode(raw).rstrip(b'=').decode('ascii')

    header = _b64({'alg': 'none', 'typ': 'JWT'})
    payload = _b64(claims)
    return f'{header}.{payload}.'


def _bearer_scope(token: str) -> dict:
    """Build an ASGI HTTP scope with an Authorization: Bearer header."""
    return {
        'type': 'http',
        'headers': [(b'authorization', f'Bearer {token}'.encode('latin-1'))],
    }


class _StubStsClient:
    """Records assume_role calls and returns fabricated credentials."""

    def __init__(self) -> None:
        self.calls: list[dict] = []

    def assume_role(self, **kwargs):
        self.calls.append(kwargs)
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
    """Return an sts_client_factory yielding the given stub client."""

    def _make(region=None):
        return client

    return _make


class TestJwtBackwardCompatibility:
    """Property: Backward compatibility.

    Validates: Requirements Backward Compatibility.
    """

    @given(caller=caller_identities)
    @settings(max_examples=200)
    def test_static_arn_derive_omits_external_id_and_tags_caller(self, caller):
        """Property: Backward compatibility.

        With only ``MCP_JWT_ROLE_ARN`` configured (the default
        ``StaticRoleResolver`` injected exactly as the server builds it), for any
        caller identity ``InboundJwtExchange.derive`` calls ``sts:AssumeRole``
        exactly once with the configured ARN, a non-empty caller-derived session
        name of at most 64 characters, the ``caller`` session tag whose value is
        the caller identity, and never an ``ExternalId`` -- reproducing the
        pre-feature static-ARN behavior.

        Validates: Requirements Backward Compatibility.
        """
        client = _StubStsClient()
        token = _make_jwt({'sub': caller})
        # Build the mechanism the way the server does when only MCP_JWT_ROLE_ARN
        # is set: inject the default StaticRoleResolver(role_arn).
        mechanism = InboundJwtExchange(
            role_resolver=StaticRoleResolver(ROLE_ARN),
            session_duration=3600,
            sts_client_factory=_factory(client),
        )

        ctx = mechanism.derive(_bearer_scope(token))

        # Exactly one assume_role call was made.
        assert len(client.calls) == 1
        call = client.calls[0]
        # The role ARN is the statically configured value.
        assert call['RoleArn'] == ROLE_ARN
        # No ExternalId is ever presented for the static single-role case.
        assert 'ExternalId' not in call
        # The caller session tag carries the authenticated caller identity.
        assert call['Tags'] == [{'Key': 'caller', 'Value': caller}]
        # The session name is a non-empty sanitized string within the STS bound.
        session_name = call['RoleSessionName']
        assert isinstance(session_name, str)
        assert 0 < len(session_name) <= 64
        # The derived context is jwt-sourced and keyed to the caller identity.
        assert ctx.source == 'jwt'
        assert ctx.identity_key == caller
