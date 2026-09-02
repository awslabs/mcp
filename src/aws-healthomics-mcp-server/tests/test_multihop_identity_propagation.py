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

"""Integration tests for multi-hop customer identity propagation (token pass-through).

Topology under test: customer -> AI agent (Calling_Agent) -> AHO_MCP_Server. The agent
forwards the customer's bearer token unchanged, so at the MCP the existing ``jwt``
mechanism (``InboundJwtExchange``) processes the customer token exactly as in the
single-hop case. There is no separate agent-identity code path: the "multi-hop"
behavior is simply that the SAME ``jwt`` mechanism derives identity from the forwarded
customer token, so the customer ``sub`` (not the agent's workload identity) becomes the
Authenticated_Identity.

These are standard integration-style tests (not property-based). They wire a real
``InboundJwtExchange`` to a ``RegistryRoleResolver`` (backed by a stub RegistrySource)
or a minimal stub resolver returning a ``RoleTarget`` with an ``external_id``, together
with a recording stub STS client, and drive ``derive()`` with an ASGI scope carrying the
customer's forwarded ``Authorization: Bearer`` header.

Signature verification is performed by an external Fronting_Layer (the MCP runtime's
Custom JWT authorizer), not by this mechanism; a ``CredentialDerivationError`` raised by
``derive`` maps to an inbound ``401`` per the design's Error Handling table.

Validates: Requirements Multi-hop customer identity propagation.

No real tokens, credentials, or AWS calls are used: the JWT is a fabricated unsigned
token whose payload carries only the claims under test, and the STS client is a stub
that records ``assume_role`` calls and returns fabricated credentials.
"""

import base64
import json
import pytest
from awslabs.aws_healthomics_mcp_server.mechanisms.jwt_exchange import InboundJwtExchange
from awslabs.aws_healthomics_mcp_server.mechanisms.role_resolver import (
    RegistryRoleResolver,
    RoleTarget,
)
from awslabs.aws_healthomics_mcp_server.utils.aws_utils import (
    CredentialDerivationError,
    InboundAuthError,
)
from botocore.exceptions import ClientError


CUSTOMER_ROLE_ARN = 'arn:aws:iam::210987654321:role/customer-role'
CUSTOMER_EXTERNAL_ID = 'ext-id-3c2b1a09-customer-uuid'
CUSTOMER_SUB = 'customer-abc-123'
SHARED_AUDIENCE = 'https://platform.example.com/shared-audience'
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
    """Build an ASGI HTTP scope with an Authorization: Bearer header.

    This models the Calling_Agent forwarding the customer's bearer token unchanged
    on its MCP-client call to the AHO_MCP_Server.
    """
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
                'Arn': f'{CUSTOMER_ROLE_ARN}/session',
                'AssumedRoleId': 'AROAEXAMPLE:session',
            },
        }


def _factory(client: _StubStsClient):
    """Return an sts_client_factory yielding the given stub client.

    The factory stands in for the server's own default-credential STS client
    (the MCP_Execution_Role), demonstrating that the assume runs under the
    server's identity and never under the forwarded customer token.
    """

    def _make(region=None):
        return client

    return _make


class _StubRegistrySource:
    """Provider-controlled registry source mapping the customer identity to a record.

    Mirrors the ``RegistrySource`` protocol consumed by ``RegistryRoleResolver`` so
    the resolver's real record-validation path runs, while keeping the mapping
    entirely provider-controlled (never taken from a token claim).
    """

    def __init__(self, records: dict[str, dict]):
        self._records = records

    def get_record(self, identity: str) -> dict | None:
        return self._records.get(identity)


class _ExternalIdResolver:
    """Minimal non-static resolver returning a fixed Role_Target with an ExternalId."""

    def __init__(self, role_arn: str, external_id: str | None):
        self._target = RoleTarget(role_arn=role_arn, external_id=external_id)

    def resolve(self, claims: dict) -> RoleTarget:
        return self._target


def _registry_resolver() -> RegistryRoleResolver:
    """Build a RegistryRoleResolver mapping the customer sub to the customer role."""
    source = _StubRegistrySource(
        {
            CUSTOMER_SUB: {
                'role_arn': CUSTOMER_ROLE_ARN,
                'external_id': CUSTOMER_EXTERNAL_ID,
            }
        }
    )
    return RegistryRoleResolver(source)


def test_identity_derived_from_customer_sub_not_agent_workload_identity():
    """Identity comes from the forwarded customer ``sub``, not the agent's identity.

    The forwarded token carries agent-ish claims alongside the customer ``sub``;
    the derived Authenticated_Identity and the caller session tag must both be the
    customer ``sub``, proving the MCP maps the customer (not the Calling_Agent).

    Validates: Requirements Multi-hop customer identity propagation.
    """
    client = _StubStsClient()
    # Agent-ish claims are present but MUST be ignored: only ``sub`` identifies the caller.
    token = _make_jwt(
        {
            'sub': CUSTOMER_SUB,
            'azp': 'calling-agent-workload-identity',
            'client_id': 'agentcore-runtime-agent',
            'act': {'sub': 'calling-agent-workload-identity'},
        }
    )
    mechanism = InboundJwtExchange(
        role_resolver=_registry_resolver(),
        sts_client_factory=_factory(client),
    )

    ctx = mechanism.derive(_bearer_scope(token))

    # The Authenticated_Identity is the preserved customer sub.
    assert ctx.identity_key == CUSTOMER_SUB
    # The ABAC caller session tag is the customer sub, not any agent identity.
    assert len(client.calls) == 1
    assert client.calls[0]['Tags'] == [{'Key': 'caller', 'Value': CUSTOMER_SUB}]
    tag_values = {tag['Value'] for tag in client.calls[0]['Tags']}
    assert 'calling-agent-workload-identity' not in tag_values
    assert 'agentcore-runtime-agent' not in tag_values


def test_forwarded_customer_token_flows_through_jwt_mechanism():
    """A normal forwarded customer token yields a successful ``jwt``-sourced derive.

    Confirms the multi-hop path reuses the existing ``jwt`` mechanism with no
    separate agent code path.

    Validates: Requirements Multi-hop customer identity propagation.
    """
    client = _StubStsClient()
    token = _make_jwt({'sub': CUSTOMER_SUB})
    mechanism = InboundJwtExchange(
        role_resolver=_registry_resolver(),
        sts_client_factory=_factory(client),
    )

    ctx = mechanism.derive(_bearer_scope(token))

    assert ctx.source == 'jwt'
    assert ctx.identity_key == CUSTOMER_SUB


def test_shared_audience_token_is_processed_and_preserves_customer_sub():
    """A token carrying the Shared_Audience is processed and preserves the customer sub.

    The customer token carries a shared ``aud`` so the SAME token is valid at both
    hops (agent and MCP). Authorizer acceptance of that audience is a deployment /
    config concern handled by the external Fronting_Layer (the MCP runtime's Custom
    JWT authorizer's ``allowedAudience`` / ``allowedClients``); it is demonstrated
    here by the token carrying the shared ``aud`` and still being processed by the
    mechanism, which decodes claims and does not reject on ``aud`` (signature and
    audience verification are external).

    Validates: Requirements Multi-hop customer identity propagation.
    """
    client = _StubStsClient()
    token = _make_jwt({'sub': CUSTOMER_SUB, 'aud': SHARED_AUDIENCE})
    mechanism = InboundJwtExchange(
        role_resolver=_registry_resolver(),
        sts_client_factory=_factory(client),
    )

    ctx = mechanism.derive(_bearer_scope(token))

    # The mechanism does not reject on the shared audience; the customer sub survives.
    assert ctx.source == 'jwt'
    assert ctx.identity_key == CUSTOMER_SUB


def test_assume_role_uses_execution_role_creds_and_request_external_id():
    """The assume uses the injected server-credential STS client + request ExternalId.

    The ``sts:AssumeRole`` presents the resolved customer ``ExternalId`` and runs on
    the STS client from the injected server-credential factory (the MCP_Execution_Role
    path). The mechanism never presents the forwarded bearer token to STS, so the
    customer trust policy authorizes the MCP_Execution_Role principal + matching
    ExternalId, not the Calling_Agent.

    Validates: Requirements Multi-hop customer identity propagation.
    """
    client = _StubStsClient()
    token = _make_jwt({'sub': CUSTOMER_SUB, 'aud': SHARED_AUDIENCE})
    mechanism = InboundJwtExchange(
        role_resolver=_ExternalIdResolver(CUSTOMER_ROLE_ARN, CUSTOMER_EXTERNAL_ID),
        sts_client_factory=_factory(client),
    )

    ctx = mechanism.derive(_bearer_scope(token))

    assert len(client.calls) == 1
    call = client.calls[0]
    # The role assumed and the ExternalId presented are the resolved customer values.
    assert call['RoleArn'] == CUSTOMER_ROLE_ARN
    assert call['ExternalId'] == CUSTOMER_EXTERNAL_ID
    # The bearer token is NEVER passed to STS in any parameter value.
    bearer_token = token
    for value in call.values():
        assert bearer_token not in json.dumps(value, default=str)
    assert ctx.identity_key == CUSTOMER_SUB


def test_missing_propagated_identity_fails_closed_to_401():
    """A forwarded token lacking a customer ``sub`` fails closed (maps to inbound 401).

    Models a request that does not carry a verified propagated customer identity: no
    ``sub`` claim. The mechanism raises ``CredentialDerivationError`` (an
    ``InboundAuthError`` -> inbound ``401`` per the design) and makes no STS call.

    Validates: Requirements Multi-hop customer identity propagation.
    """
    client = _StubStsClient()
    token = _make_jwt({'aud': SHARED_AUDIENCE, 'azp': 'calling-agent-workload-identity'})
    mechanism = InboundJwtExchange(
        role_resolver=_registry_resolver(),
        sts_client_factory=_factory(client),
    )

    with pytest.raises(CredentialDerivationError) as exc_info:
        mechanism.derive(_bearer_scope(token))

    assert client.calls == []
    assert isinstance(exc_info.value, InboundAuthError)


def test_no_forwarded_bearer_token_fails_closed_to_401():
    """A request with no forwarded bearer token fails closed (maps to inbound 401).

    Models the agent hop failing to propagate any customer token. The mechanism
    raises ``CredentialDerivationError`` (-> inbound ``401``) and makes no STS call.

    Validates: Requirements Multi-hop customer identity propagation.
    """
    client = _StubStsClient()
    mechanism = InboundJwtExchange(
        role_resolver=_registry_resolver(),
        sts_client_factory=_factory(client),
    )

    with pytest.raises(CredentialDerivationError) as exc_info:
        mechanism.derive({'type': 'http', 'headers': []})

    assert client.calls == []
    assert isinstance(exc_info.value, InboundAuthError)


def test_sts_failure_fails_closed_to_401():
    """An STS AssumeRole failure fails closed (maps to inbound 401).

    Models an ExternalId / trust-policy / permission failure at the customer role.
    The mechanism raises ``CredentialDerivationError`` (-> inbound ``401``), returns
    no ``CredentialContext``, and the single failing assume was the only AWS call.

    Validates: Requirements Multi-hop customer identity propagation.
    """
    error = ClientError(
        error_response={'Error': {'Code': 'AccessDenied', 'Message': 'denied'}},
        operation_name='AssumeRole',
    )
    client = _StubStsClient(error=error)
    token = _make_jwt({'sub': CUSTOMER_SUB, 'aud': SHARED_AUDIENCE})
    mechanism = InboundJwtExchange(
        role_resolver=_registry_resolver(),
        sts_client_factory=_factory(client),
    )

    with pytest.raises(CredentialDerivationError) as exc_info:
        mechanism.derive(_bearer_scope(token))

    assert len(client.calls) == 1
    assert isinstance(exc_info.value, InboundAuthError)
