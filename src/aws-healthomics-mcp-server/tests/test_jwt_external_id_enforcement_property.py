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

"""Property-based tests for ExternalId enforcement on non-static role resolution.

Covers Property: ExternalId enforced from the customer-role-assumption design,
validating Requirements Confused Deputy Protection: when ``InboundJwtExchange``
resolves a downstream :class:`RoleTarget` through a resolver that is not the
static single-role resolver, the resolved ``ExternalId`` gates the assume:

- when the target supplies a non-empty ``external_id``, ``derive`` calls
  ``sts:AssumeRole`` with ``ExternalId`` exactly equal to that value; and
- when the target's ``external_id`` is empty or ``None``, ``derive`` fails closed
  with :class:`CredentialDerivationError` and never calls ``assume_role``.

These tests never use real tokens, credentials, or AWS calls. The JWT is a
fabricated unsigned token carrying only a ``sub`` claim; the resolver is a simple
stub (not a ``StaticRoleResolver``); and the STS client is a stub that records
whether ``assume_role`` was called and with what keyword arguments.
"""

import base64
import json
import pytest
from awslabs.aws_healthomics_mcp_server.mechanisms.jwt_exchange import (
    InboundJwtExchange,
)
from awslabs.aws_healthomics_mcp_server.mechanisms.role_resolver import RoleTarget
from awslabs.aws_healthomics_mcp_server.utils.aws_utils import (
    CredentialContext,
    CredentialDerivationError,
)
from hypothesis import given, settings
from hypothesis import strategies as st


ROLE_ARN = 'arn:aws:iam::123456789012:role/customer-cross-account-role'
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


def _bearer_scope(token: str) -> dict:
    """Build an ASGI HTTP scope with an Authorization: Bearer header."""
    return {
        'type': 'http',
        'headers': [(b'authorization', f'Bearer {token}'.encode('latin-1'))],
    }


class _StubResolver:
    """A non-static resolver that returns a caller-controlled :class:`RoleTarget`.

    Intentionally NOT a subclass/instance of ``StaticRoleResolver`` so that the
    confused-deputy ExternalId enforcement path in ``derive`` applies. It also
    satisfies the ``RoleResolver`` Protocol by exposing ``resolve(claims)``.
    """

    def __init__(self, target: RoleTarget):
        self._target = target

    def resolve(self, claims: dict) -> RoleTarget:
        return self._target


class _RecordingStsClient:
    """Records whether assume_role was called and with what keyword arguments."""

    def __init__(self):
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


def _factory(client: _RecordingStsClient):
    """Return an sts_client_factory yielding the given recording stub."""

    def _make(region=None):
        return client

    return _make


# Caller 'sub' claim strategy: non-empty text spanning a wide character range so
# session-name sanitization is exercised too.
_callers = st.text(min_size=1, max_size=40).filter(lambda value: value.strip() != '')

# Non-empty ExternalId strategy. STS accepts ExternalId values up to 1224
# characters from a documented character set; a broad text strategy is sufficient
# to assert the value is passed through unmodified.
_external_ids = st.text(min_size=1, max_size=64).filter(lambda value: value != '')

# Absent-ExternalId strategy: the two ways a resolver can supply no usable value.
_absent_external_ids = st.sampled_from([None, ''])


class TestExternalIdEnforcement:
    """Property: ExternalId enforced.

    Validates: Requirements Confused Deputy Protection.
    """

    @settings(max_examples=100)
    @given(caller=_callers, external_id=_external_ids)
    def test_non_empty_external_id_is_passed_through_to_assume_role(
        self, caller: str, external_id: str
    ):
        """A non-empty resolved ExternalId reaches assume_role exactly as resolved.

        For any caller identity and any non-empty ``external_id`` produced by a
        non-static resolver, ``derive`` calls ``sts:AssumeRole`` exactly once with
        ``ExternalId`` equal to that resolved value (byte-for-byte), and builds a
        jwt-sourced credential context.

        Validates: Requirements Confused Deputy Protection.
        """
        client = _RecordingStsClient()
        resolver = _StubResolver(RoleTarget(role_arn=ROLE_ARN, external_id=external_id))
        mechanism = InboundJwtExchange(
            role_resolver=resolver,
            sts_client_factory=_factory(client),
        )
        token = _make_jwt({'sub': caller})

        ctx = mechanism.derive(_bearer_scope(token))

        # Exactly one assume_role call carrying the exact resolved ExternalId.
        assert len(client.calls) == 1
        call = client.calls[0]
        assert call['ExternalId'] == external_id
        assert call['RoleArn'] == ROLE_ARN
        # The exchange still produces a jwt-sourced credential context.
        assert isinstance(ctx, CredentialContext)
        assert ctx.source == 'jwt'

    @settings(max_examples=100)
    @given(caller=_callers, external_id=_absent_external_ids)
    def test_absent_external_id_fails_closed_without_assume_role(self, caller: str, external_id):
        """An empty/None ExternalId from a non-static resolver fails closed.

        For any caller identity and an ``external_id`` that is ``None`` or the empty
        string, ``derive`` raises :class:`CredentialDerivationError` and never calls
        ``assume_role`` on the STS client (Requirement 7.4: confused-deputy
        protection fails closed before any AWS call is made).

        Validates: Requirements Confused Deputy Protection.
        """
        client = _RecordingStsClient()
        resolver = _StubResolver(RoleTarget(role_arn=ROLE_ARN, external_id=external_id))
        mechanism = InboundJwtExchange(
            role_resolver=resolver,
            sts_client_factory=_factory(client),
        )
        token = _make_jwt({'sub': caller})

        with pytest.raises(CredentialDerivationError):
            mechanism.derive(_bearer_scope(token))

        # No assume_role call was made: the request failed closed beforehand.
        assert client.calls == []
