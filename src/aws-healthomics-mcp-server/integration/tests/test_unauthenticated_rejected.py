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


"""Boundary rejection of unauthenticated and invalid-credential requests (live AWS).

This opt-in integration module asserts the Server's fronting layer terminates inbound
authentication at its boundary: a request that presents no credential, and a request that
presents an invalid/garbage credential, is rejected *before* it can reach the Server, so no
tool ever runs. For the AgentCore deployment this rejection is performed by AgentCore
Runtime's inbound authorizer ("AgentCore deployment demonstration"); for the API Gateway
deployment it is performed by the gateway's authorizer, which does not forward the request to
the loopback-bound Server ("API Gateway deployment demonstration"). In both cases a request
carrying no inbound identity that any enabled mechanism can authenticate is refused at the
boundary before any tool call is attempted ("Cross-tenant isolation verification" -- inbound
identity is required before any tool runs).

The most direct signal for boundary auth termination is the HTTP status: a rejected request
receives an HTTP 401 (preferred) or 403 and is never forwarded, so the response is never a
successful (2xx) tool exchange. This module issues a direct HTTP request to the fronting-layer
endpoint -- once with no ``Authorization`` header and once with a deliberately invalid bearer
token -- and asserts each is rejected with 401/403 and that no successful tool exchange
occurred.

The test is gated behind the Opt_In_Signal (``RUN_REMOTE_INTEGRATION_TESTS``) by the
collection hook in ``integration/conftest.py`` and is skipped by default. When the signal is
present it resolves the fronting-layer endpoint from the environment via the
``require_inputs`` fixture and skips -- rather than fails -- when that input is absent. Because
the skip is applied at collection time, no AWS client is constructed offline.

Additional fail-closed multi-tenant assertions (unregistered identity, disabled record,
unauthenticable request) are appended to this module by a later task; the shared endpoint
input, request helper, and rejection-status constants below are intended to be reused by
those tests.
"""

from __future__ import annotations

import httpx
import pytest
from collections.abc import Callable, Mapping, Sequence
from integration.harness.credential_scan import (
    CredentialMaterialScanner,
    CredentialMaterialType,
)


# The fronting-layer endpoint under test (the AgentCore or API Gateway URL that fronts the
# Server). Reused across this module's tests. When absent, the test is skipped (not failed)
# by the ``require_inputs`` fixture (Req 1.6).
ENDPOINT_ENV = 'AHO_ITEST_ENDPOINT'

# A deliberately invalid, well-formed-looking bearer token. It is not a real credential and
# carries no secret material; the boundary must reject it because it fails cryptographic
# verification.
INVALID_BEARER_TOKEN = 'invalid.garbage.token'  # pragma: allowlist secret

# HTTP statuses that demonstrate the boundary rejected the request before it reached the
# Server. 401 (Unauthorized) is preferred and most directly matches the requirement; 403
# (Forbidden) is also accepted, since some fronting-layer authorizers signal an unauthorized
# caller that way.
REJECTED_STATUSES: frozenset[int] = frozenset({401, 403})

# How long to wait for the boundary to respond. A boundary rejection is prompt; this bounds
# the request so a hung connection does not stall the suite.
_REQUEST_TIMEOUT_SECONDS = 30.0

# A minimal MCP ``initialize`` JSON-RPC request body. The boundary rejects before the body is
# ever processed, but sending a well-formed body ensures a 2xx could only come from the Server
# actually handling the request -- which must never happen for an unauthenticated caller.
_INITIALIZE_BODY: dict[str, object] = {
    'jsonrpc': '2.0',
    'id': 1,
    'method': 'initialize',
    'params': {
        'protocolVersion': '2025-06-18',
        'capabilities': {},
        'clientInfo': {'name': 'aho-itest-unauth', 'version': '0'},
    },
}

# Headers an MCP streamable-http client sends on the initial POST, minus any ``Authorization``
# header. The caller-specific auth header (present or invalid) is merged in per attempt.
_BASE_HEADERS: dict[str, str] = {
    'Content-Type': 'application/json',
    'Accept': 'application/json, text/event-stream',
}


def _attempt_request(endpoint: str, auth_header: Mapping[str, str]) -> httpx.Response:
    """POST a minimal MCP ``initialize`` to ``endpoint`` with ``auth_header`` merged in.

    Returns the HTTP response so the caller can inspect its status. A direct HTTP request is
    used (rather than the MCP client) so the boundary's status code is observable, which is
    the most direct evidence that authentication is terminated at the HTTP layer.
    """
    headers = {**_BASE_HEADERS, **auth_header}
    with httpx.Client(timeout=_REQUEST_TIMEOUT_SECONDS, follow_redirects=False) as client:
        return client.post(endpoint, headers=headers, json=_INITIALIZE_BODY)


def _assert_rejected_at_boundary(response: httpx.Response, *, attempt: str) -> None:
    """Assert ``response`` shows the boundary rejected the request before any tool ran.

    The response must not be a successful (2xx) exchange, and it must carry a rejection status
    (401 preferred, or 403). Any other outcome means the credential-less/invalid request was
    not cleanly refused at the boundary.
    """
    assert not response.is_success, (
        f'{attempt}: boundary returned a successful response '
        f'(HTTP {response.status_code}); an unauthenticated/invalid request must be rejected '
        'before reaching the Server, so no successful tool exchange may occur'
    )
    assert response.status_code in REJECTED_STATUSES, (
        f'{attempt}: expected the boundary to reject with one of '
        f'{sorted(REJECTED_STATUSES)} (401 preferred) but got HTTP {response.status_code}'
    )


@pytest.mark.integration
def test_no_credential_rejected_at_boundary(
    require_inputs: Callable[[list[str]], Mapping[str, str]],
) -> None:
    """A request with no credential is rejected at the boundary before reaching the Server.

    Validates: Requirements AgentCore deployment demonstration (the inbound authorizer rejects
    a request that presents no token/SigV4 signature and returns an error to the caller), API
    Gateway deployment demonstration (an unauthenticated request is rejected and not forwarded
    to the Server), and Cross-tenant isolation verification (a request with no authenticable
    inbound identity is rejected before any tool call is attempted).
    """
    endpoint = require_inputs([ENDPOINT_ENV])[ENDPOINT_ENV]

    response = _attempt_request(endpoint, auth_header={})

    _assert_rejected_at_boundary(response, attempt='no-credential request')


@pytest.mark.integration
def test_invalid_credential_rejected_at_boundary(
    require_inputs: Callable[[list[str]], Mapping[str, str]],
) -> None:
    """A request with an invalid credential is rejected at the boundary before the Server.

    Validates: Requirements AgentCore deployment demonstration (the inbound authorizer rejects
    a token that fails cryptographic verification and returns an error to the caller), API
    Gateway deployment demonstration (an unauthenticated request is rejected and not forwarded
    to the Server), and Cross-tenant isolation verification (a request carrying no
    authenticable inbound identity is rejected before any tool call is attempted).
    """
    endpoint = require_inputs([ENDPOINT_ENV])[ENDPOINT_ENV]

    response = _attempt_request(
        endpoint,
        auth_header={'Authorization': f'Bearer {INVALID_BEARER_TOKEN}'},
    )

    _assert_rejected_at_boundary(response, attempt='invalid-credential request')


# --- Fail-closed multi-tenant scenario inputs and helpers ---------------------------------
#
# The tests below extend the boundary-rejection coverage above with the multi-tenant
# fail-closed paths: an inbound identity that authenticates but resolves to no usable tenant
# (no Registry_Record, or a disabled Registry_Record) and a request the enabled mechanisms
# cannot authenticate at all. Each must yield the specific HTTP 401 status *before* any tool
# runs and *before* any per-request credential is constructed, and the 401 must never carry
# Credential_Material or another tenant's identity. They reuse the endpoint input, the
# ``_attempt_request`` helper, and ``INVALID_BEARER_TOKEN`` defined above.

# A validly-signed JWT whose Authenticated_Identity (the ``sub`` claim) has NO Registry_Record.
# The Server must reject it with HTTP 401 before any tool runs and before constructing
# per-request credentials.
UNREGISTERED_TOKEN_ENV = 'AHO_ITEST_UNREGISTERED_TOKEN'  # pragma: allowlist secret

# A validly-signed JWT whose Registry_Record has ``enabled`` set to a non-truthy value. The
# Server must reject it with HTTP 401 before any tool runs and before constructing
# per-request credentials.
DISABLED_TOKEN_ENV = 'AHO_ITEST_DISABLED_TOKEN'  # pragma: allowlist secret

# Another tenant's Authenticated_Identity string that must never appear in a 401 response
# body or header. Optional: when absent, the cross-tenant substring assertion is skipped.
OTHER_TENANT_IDENTITY_ENV = 'AHO_ITEST_OTHER_TENANT_IDENTITY'

# Known STS Credential_Material the harness may observe. Registering these with the scanner
# means a 401 that echoes any of them verbatim is caught. Both are optional; blank/absent
# values are ignored by the scanner so an empty registration never matches all text.
KNOWN_SECRET_ACCESS_KEY_ENV = 'AHO_ITEST_KNOWN_SECRET_ACCESS_KEY'  # pragma: allowlist secret
KNOWN_SESSION_TOKEN_ENV = 'AHO_ITEST_KNOWN_SESSION_TOKEN'  # pragma: allowlist secret


def _assert_rejected_with_401(response: httpx.Response, *, attempt: str) -> None:
    """Assert the Server rejected the request with HTTP 401 before any tool ran.

    The fail-closed multi-tenant scenarios require the specific 401 status (not merely the
    accepted 401/403 rejection set used for boundary rejection). A 401 is the signal that the
    request was refused before any HealthOmics tool ran and before any per-request credential
    was constructed, so this asserts ``== 401`` directly rather than membership in
    ``REJECTED_STATUSES``.
    """
    assert not response.is_success, (
        f'{attempt}: expected an HTTP 401 rejection but got a successful response '
        f'(HTTP {response.status_code}); no tool may run for a fail-closed request'
    )
    assert response.status_code == 401, (
        f'{attempt}: expected HTTP 401 before any tool ran but got HTTP {response.status_code}'
    )


def _build_credential_scanner(
    env: Mapping[str, str],
    presented_tokens: Sequence[str],
) -> CredentialMaterialScanner:
    """Build a scanner registered with the presented token(s) and any known STS secrets.

    The presented bearer token(s) are registered as ``BEARER_TOKEN`` so a 401 that echoes the
    caller's own token verbatim is caught, and any known secret access key / session token
    supplied via the environment is registered as its own material type. Blank or absent
    values are ignored by the scanner, so an empty registration never matches all text.
    """
    bearer_tokens = [token for token in presented_tokens if token and token.strip()]
    secrets: dict[CredentialMaterialType, list[str]] = {
        CredentialMaterialType.BEARER_TOKEN: bearer_tokens,
    }
    secret_access_key = env.get(KNOWN_SECRET_ACCESS_KEY_ENV)
    if secret_access_key and secret_access_key.strip():
        secrets[CredentialMaterialType.SECRET_ACCESS_KEY] = [secret_access_key]
    session_token = env.get(KNOWN_SESSION_TOKEN_ENV)
    if session_token and session_token.strip():
        secrets[CredentialMaterialType.SESSION_TOKEN] = [session_token]
    return CredentialMaterialScanner(secrets)


def _assert_401_leaks_no_material_or_identity(
    response: httpx.Response,
    *,
    scanner: CredentialMaterialScanner,
    other_tenant_identity: 'str | None',
    attempt: str,
) -> None:
    """Assert the 401 carries no Credential_Material and no other tenant's identity.

    Scans the response body text and every response header value with ``scanner`` (whose
    ``assert_clean`` raises naming the material type and location, never the value) and, when
    an other-tenant identity is provided, asserts that identity string appears in neither the
    body nor the headers.
    """
    body_text = response.text
    header_text = '\n'.join(f'{name}: {value}' for name, value in response.headers.items())

    # Raises AssertionError naming type + location (never the value) on any verbatim leak.
    scanner.assert_clean(body_text, f'{attempt} 401 body')
    scanner.assert_clean(header_text, f'{attempt} 401 headers')

    if other_tenant_identity and other_tenant_identity.strip():
        assert other_tenant_identity not in body_text, (
            f"{attempt}: the 401 body must not contain another tenant's identity"
        )
        assert other_tenant_identity not in header_text, (
            f"{attempt}: the 401 headers must not contain another tenant's identity"
        )


@pytest.mark.integration
def test_unregistered_identity_rejected_with_401(
    require_inputs: Callable[[list[str]], Mapping[str, str]],
    integration_env: Mapping[str, str],
) -> None:
    """An authenticated identity with no Registry_Record is refused with HTTP 401.

    Presents a validly-signed JWT whose Authenticated_Identity has no Registry_Record and
    asserts the Server returns HTTP 401 before any HealthOmics tool runs and before any
    per-request credential is constructed, then asserts the 401 body and headers contain no
    Credential_Material (including the presented token itself) and no other tenant's identity.

    Validates: Requirements DynamoDB-backed multi-tenant registry, Cross-tenant isolation
    verification, and Credential material safety.
    """
    inputs = require_inputs([ENDPOINT_ENV, UNREGISTERED_TOKEN_ENV])
    endpoint = inputs[ENDPOINT_ENV]
    token = inputs[UNREGISTERED_TOKEN_ENV]

    response = _attempt_request(endpoint, {'Authorization': f'Bearer {token}'})

    _assert_rejected_with_401(response, attempt='unregistered-identity request')
    _assert_401_leaks_no_material_or_identity(
        response,
        scanner=_build_credential_scanner(integration_env, [token]),
        other_tenant_identity=integration_env.get(OTHER_TENANT_IDENTITY_ENV),
        attempt='unregistered-identity request',
    )


@pytest.mark.integration
def test_disabled_record_rejected_with_401(
    require_inputs: Callable[[list[str]], Mapping[str, str]],
    integration_env: Mapping[str, str],
) -> None:
    """An identity whose Registry_Record is disabled is refused with HTTP 401.

    Presents a validly-signed JWT whose Registry_Record has ``enabled`` set to a non-truthy
    value and asserts the Server returns HTTP 401 before any HealthOmics tool runs and before
    any per-request credential is constructed, then asserts the 401 body and headers contain
    no Credential_Material (including the presented token itself) and no other tenant's
    identity.

    Validates: Requirements DynamoDB-backed multi-tenant registry, Cross-tenant isolation
    verification, and Credential material safety.
    """
    inputs = require_inputs([ENDPOINT_ENV, DISABLED_TOKEN_ENV])
    endpoint = inputs[ENDPOINT_ENV]
    token = inputs[DISABLED_TOKEN_ENV]

    response = _attempt_request(endpoint, {'Authorization': f'Bearer {token}'})

    _assert_rejected_with_401(response, attempt='disabled-record request')
    _assert_401_leaks_no_material_or_identity(
        response,
        scanner=_build_credential_scanner(integration_env, [token]),
        other_tenant_identity=integration_env.get(OTHER_TENANT_IDENTITY_ENV),
        attempt='disabled-record request',
    )


@pytest.mark.integration
def test_unauthenticable_request_rejected_with_401(
    require_inputs: Callable[[list[str]], Mapping[str, str]],
    integration_env: Mapping[str, str],
) -> None:
    """A request no enabled mechanism can authenticate is refused with HTTP 401.

    Presents a garbage bearer token that no enabled mechanism (``sigv4``, ``jwt``, or
    ``explicit``) can authenticate and asserts the Server returns HTTP 401 before any
    HealthOmics tool runs and before any per-request credential is constructed, then asserts
    the 401 body and headers contain no Credential_Material (including the presented token
    itself) and no other tenant's identity.

    Validates: Requirements DynamoDB-backed multi-tenant registry, Cross-tenant isolation
    verification, and Credential material safety.
    """
    endpoint = require_inputs([ENDPOINT_ENV])[ENDPOINT_ENV]

    response = _attempt_request(
        endpoint,
        {'Authorization': f'Bearer {INVALID_BEARER_TOKEN}'},
    )

    _assert_rejected_with_401(response, attempt='unauthenticable request')
    _assert_401_leaks_no_material_or_identity(
        response,
        scanner=_build_credential_scanner(integration_env, [INVALID_BEARER_TOKEN]),
        other_tenant_identity=integration_env.get(OTHER_TENANT_IDENTITY_ENV),
        attempt='unauthenticable request',
    )
