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

"""Unit tests for InboundJwtExchange.derive assume-role call shape and fail-closed paths.

These tests pin the exact ``sts:AssumeRole`` request that ``derive`` builds from a
resolved Role_Target and assert the fail-closed behavior when the caller claim is
missing or the STS call fails. They exercise the per-request role resolution seam
through the injectable ``role_resolver`` (a ``StaticRoleResolver`` and a small
stub resolver returning a Role_Target with an ExternalId) and the injectable
``sts_client_factory``.

Validates:
- Requirements Per-request role and ExternalId resolution (resolved RoleArn and
  ExternalId present/omitted, caller session tag).
- Requirements Fail Closed On Failure (missing caller claim and STS failure raise
  Credential_Derivation_Error with no returned Credential_Context).

No real tokens, credentials, or AWS calls are used: the JWT is a fabricated
unsigned token whose payload carries only the claims under test, and the STS
client is a stub that records ``assume_role`` calls and returns fabricated
credentials.
"""

import base64
import json
import pytest
from awslabs.aws_healthomics_mcp_server.mechanisms.jwt_exchange import InboundJwtExchange
from awslabs.aws_healthomics_mcp_server.mechanisms.role_resolver import (
    RoleTarget,
    StaticRoleResolver,
)
from awslabs.aws_healthomics_mcp_server.utils.aws_utils import (
    CredentialDerivationError,
    InboundAuthError,
)
from botocore.exceptions import BotoCoreError, ClientError


ROLE_ARN = 'arn:aws:iam::123456789012:role/per-tenant-role'
REGISTRY_ROLE_ARN = 'arn:aws:iam::210987654321:role/customer-role'
EXTERNAL_ID = 'ext-id-9f8e7d6c-uuid'
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


class _StubStsClient:
    """Records assume_role calls and returns fabricated credentials (or raises)."""

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
    """Return an sts_client_factory yielding the given stub client."""

    def _make(region=None):
        return client

    return _make


class _ExternalIdResolver:
    """Minimal non-static resolver returning a fixed Role_Target with an ExternalId."""

    def __init__(self, role_arn: str, external_id: str | None):
        self._target = RoleTarget(role_arn=role_arn, external_id=external_id)

    def resolve(self, claims: dict) -> RoleTarget:
        return self._target


def test_derive_calls_assume_role_with_resolved_arn_and_omits_external_id():
    """A StaticRoleResolver drives assume_role with its ARN, caller tag, no ExternalId.

    Validates: Requirements Per-request role and ExternalId resolution.
    """
    client = _StubStsClient()
    token = _make_jwt({'sub': 'caller-1'})
    mechanism = InboundJwtExchange(
        role_resolver=StaticRoleResolver(ROLE_ARN),
        session_duration=3600,
        sts_client_factory=_factory(client),
    )

    ctx = mechanism.derive(_bearer_scope(token))

    assert len(client.calls) == 1
    call = client.calls[0]
    # RoleArn is the resolver-supplied ARN.
    assert call['RoleArn'] == ROLE_ARN
    # ExternalId is omitted entirely for the static single-role case.
    assert 'ExternalId' not in call
    # The caller session tag identifies the authenticated caller.
    assert call['Tags'] == [{'Key': 'caller', 'Value': 'caller-1'}]
    assert call['DurationSeconds'] == 3600
    assert call['RoleSessionName']
    # A jwt-sourced context is returned on success.
    assert ctx.source == 'jwt'
    assert ctx.identity_key == 'caller-1'


def test_derive_calls_assume_role_with_external_id_when_resolver_supplies_one():
    """A resolver returning an ExternalId passes that exact ExternalId to assume_role.

    Validates: Requirements Per-request role and ExternalId resolution.
    """
    client = _StubStsClient()
    token = _make_jwt({'sub': 'customer-7'})
    mechanism = InboundJwtExchange(
        role_resolver=_ExternalIdResolver(REGISTRY_ROLE_ARN, EXTERNAL_ID),
        sts_client_factory=_factory(client),
    )

    ctx = mechanism.derive(_bearer_scope(token))

    assert len(client.calls) == 1
    call = client.calls[0]
    assert call['RoleArn'] == REGISTRY_ROLE_ARN
    # The exact ExternalId from the resolved Role_Target is presented to STS.
    assert call['ExternalId'] == EXTERNAL_ID
    assert call['Tags'] == [{'Key': 'caller', 'Value': 'customer-7'}]
    assert ctx.identity_key == 'customer-7'
    assert ctx.source == 'jwt'


def test_derive_missing_caller_claim_fails_closed_without_assume_role():
    """A token lacking the caller claim raises and never calls assume_role.

    Validates: Requirements Fail Closed On Failure.
    """
    client = _StubStsClient()
    token = _make_jwt({'aud': 'no-subject-here'})
    mechanism = InboundJwtExchange(
        role_resolver=StaticRoleResolver(ROLE_ARN),
        sts_client_factory=_factory(client),
    )

    with pytest.raises(CredentialDerivationError) as exc_info:
        mechanism.derive(_bearer_scope(token))

    # Fail closed: no assume_role call was made and the error is an auth error.
    assert client.calls == []
    assert isinstance(exc_info.value, InboundAuthError)


def test_derive_empty_caller_claim_fails_closed_without_assume_role():
    """An empty caller claim value raises and never calls assume_role.

    Validates: Requirements Fail Closed On Failure.
    """
    client = _StubStsClient()
    token = _make_jwt({'sub': ''})
    mechanism = InboundJwtExchange(
        role_resolver=StaticRoleResolver(ROLE_ARN),
        sts_client_factory=_factory(client),
    )

    with pytest.raises(CredentialDerivationError):
        mechanism.derive(_bearer_scope(token))
    assert client.calls == []


def test_derive_sts_client_error_fails_closed_with_no_context():
    """An STS ClientError raises Credential_Derivation_Error and returns no context.

    Validates: Requirements Fail Closed On Failure.
    """
    error = ClientError(
        error_response={'Error': {'Code': 'AccessDenied', 'Message': 'denied'}},
        operation_name='AssumeRole',
    )
    client = _StubStsClient(error=error)
    token = _make_jwt({'sub': 'caller-1'})
    mechanism = InboundJwtExchange(
        role_resolver=StaticRoleResolver(ROLE_ARN),
        sts_client_factory=_factory(client),
    )

    with pytest.raises(CredentialDerivationError) as exc_info:
        mechanism.derive(_bearer_scope(token))

    # The single failing assume_role was the only AWS call; error is an auth error.
    assert len(client.calls) == 1
    assert isinstance(exc_info.value, InboundAuthError)


def test_derive_sts_botocore_error_fails_closed_with_no_context():
    """An STS BotoCoreError raises Credential_Derivation_Error and returns no context.

    Validates: Requirements Fail Closed On Failure.
    """
    client = _StubStsClient(error=BotoCoreError())
    token = _make_jwt({'sub': 'caller-1'})
    mechanism = InboundJwtExchange(
        role_resolver=_ExternalIdResolver(REGISTRY_ROLE_ARN, EXTERNAL_ID),
        sts_client_factory=_factory(client),
    )

    with pytest.raises(CredentialDerivationError) as exc_info:
        mechanism.derive(_bearer_scope(token))

    assert len(client.calls) == 1
    assert isinstance(exc_info.value, InboundAuthError)
