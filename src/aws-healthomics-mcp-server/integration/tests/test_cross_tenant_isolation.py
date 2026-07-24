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

"""Opt-in cross-tenant isolation verification against a provisioned deployment.

This module proves, against a live multi-tenant deployment, that interleaved tool calls
from two tenants each run under their own mapped ``Tenant_Role`` and never under the other
tenant's role. It authenticates as Tenant_A and Tenant_B (each with its own bearer token),
issues interleaved ``WhoAmI`` calls (at least two per tenant), and uses the isolation
comparison helper to assert that every observed assumed-role identity is exactly the calling
tenant's expected ``Tenant_Role`` identifier — and never the other tenant's.

The identity-revealing ``WhoAmI`` tool (attached by the harness deployment entrypoint)
returns ``{'arn', 'account', 'user_id'}`` where ``arn`` is the assumed-role identity that
STS reports for the request. Because the isolation helper performs an *exact* string
comparison, the operator supplies each tenant's expected value as the exact assumed-role ARN
that ``WhoAmI`` should return for that tenant (an
``arn:aws:sts::<account>:assumed-role/<RoleName>/<session>`` value), so the comparison is
like-for-like.

AWS isolation: this suite is opt-in. It is skipped at collection time unless the
``RUN_REMOTE_INTEGRATION_TESTS`` signal is present (see ``integration/conftest.py``), and
when the signal is present but a required configuration input is missing, the affected test
is skipped rather than failed. No AWS client is constructed and no network connection is
opened while the suite is skipped.

Validates: Requirements Cross-tenant isolation verification.
"""

import json
import pytest
from collections.abc import Mapping
from integration.harness.headers import (
    EXPLICIT_ACCESS_KEY_ID_HEADER,
    EXPLICIT_SECRET_ACCESS_KEY_HEADER,
    EXPLICIT_SESSION_TOKEN_HEADER,
)
from integration.harness.isolation import assert_identity_matches, identities_match
from integration.harness.mcp_client import HarnessMcpClient, ToolResult, with_retries
from typing import Any


# Configuration input names resolved via the ``require_inputs`` fixture. Missing any of
# these causes the test to be skipped (not failed) with a reason naming the missing input.
ENV_ENDPOINT = 'AHO_ITEST_ENDPOINT'
ENV_TENANT_A_TOKEN = 'AHO_ITEST_TENANT_A_TOKEN'  # pragma: allowlist secret
ENV_TENANT_B_TOKEN = 'AHO_ITEST_TENANT_B_TOKEN'  # pragma: allowlist secret
ENV_TENANT_A_EXPECTED_ARN = 'AHO_ITEST_TENANT_A_EXPECTED_ARN'
ENV_TENANT_B_EXPECTED_ARN = 'AHO_ITEST_TENANT_B_EXPECTED_ARN'

_REQUIRED_INPUTS = (
    ENV_ENDPOINT,
    ENV_TENANT_A_TOKEN,
    ENV_TENANT_B_TOKEN,
    ENV_TENANT_A_EXPECTED_ARN,
    ENV_TENANT_B_EXPECTED_ARN,
)

# The identity-revealing tool registered by the harness deployment entrypoint.
_WHOAMI_TOOL = 'WhoAmI'


def _explicit_credential_headers(env: Mapping[str, str], prefix: str) -> dict[str, str]:
    """Return the per-tenant X-Aws-* headers for the explicit-mechanism workaround, or empty.

    Absent in the default ``jwt`` deployment (returns ``{}``); populated in the ``explicit``
    deployment where the harness exports each tenant's short-lived credentials under
    ``<prefix>ACCESS_KEY_ID`` / ``SECRET_ACCESS_KEY`` / ``SESSION_TOKEN``.
    """
    access_key_id = env.get(f'{prefix}ACCESS_KEY_ID')
    secret_access_key = env.get(f'{prefix}SECRET_ACCESS_KEY')
    session_token = env.get(f'{prefix}SESSION_TOKEN')
    if access_key_id and secret_access_key and session_token:
        return {
            EXPLICIT_ACCESS_KEY_ID_HEADER: access_key_id,
            EXPLICIT_SECRET_ACCESS_KEY_HEADER: secret_access_key,
            EXPLICIT_SESSION_TOKEN_HEADER: session_token,
        }
    return {}


def _extract_identity_arn(result: ToolResult) -> str:
    """Extract the assumed-role ``arn`` from a ``WhoAmI`` tool-call result.

    ``WhoAmI`` returns ``{'arn', 'account', 'user_id'}``. Over the MCP transport this is
    surfaced as structured content and/or a JSON text block, so both shapes are handled:
    the structured content is preferred (unwrapping a ``result`` envelope if present) and a
    JSON text block is used as a fallback.

    Args:
        result: The tool-call result returned by invoking ``WhoAmI``.

    Returns:
        The assumed-role ARN string reported for the request.

    Raises:
        AssertionError: If no assumed-role ``arn`` can be found in the result.
    """
    structured = getattr(result, 'structuredContent', None)
    if isinstance(structured, Mapping):
        payload: Any = structured.get('result', structured)
        if isinstance(payload, Mapping) and 'arn' in payload:
            return str(payload['arn'])

    for block in getattr(result, 'content', None) or []:
        text = getattr(block, 'text', None)
        if text is None:
            continue
        try:
            parsed = json.loads(text)
        except (ValueError, TypeError):
            continue
        if isinstance(parsed, Mapping) and 'arn' in parsed:
            return str(parsed['arn'])

    raise AssertionError(f'{_WHOAMI_TOOL} result did not contain an assumed-role arn')


async def _observe_identity(client: HarnessMcpClient, context: str) -> str:
    """Invoke ``WhoAmI`` (with transient-failure retries) and return the observed arn.

    The call is wrapped in :func:`with_retries` so a temporarily unavailable fronting layer
    or server is retried up to three additional times at >= 1s spacing before failing.

    Args:
        client: An opened :class:`HarnessMcpClient` bound to one tenant's bearer token.
        context: Human-readable context (tenant + call index) for failure messages.

    Returns:
        The assumed-role ARN observed for this tool call.
    """

    async def _call() -> ToolResult:
        return await client.call_tool(_WHOAMI_TOOL, {})

    result = await with_retries(_call)
    return _extract_identity_arn(result)


@pytest.mark.integration
async def test_interleaved_calls_stay_within_each_tenant_role(
    require_inputs, integration_env
) -> None:
    """Interleaved Tenant_A/Tenant_B calls each run under their own role, never the other's.

    Authenticates as Tenant_A and Tenant_B with their own bearer tokens, issues interleaved
    ``WhoAmI`` calls (A, B, A, B — two per tenant), and asserts that every observed
    assumed-role identity is exactly the calling tenant's expected ``Tenant_Role`` and never
    the other tenant's. A mismatch raises :class:`TenantIdentityMismatch` carrying both the
    expected and observed identities.

    Validates: Requirements Cross-tenant isolation verification.
    """
    inputs = require_inputs(_REQUIRED_INPUTS)
    endpoint = inputs[ENV_ENDPOINT]
    tenant_a_expected = inputs[ENV_TENANT_A_EXPECTED_ARN]
    tenant_b_expected = inputs[ENV_TENANT_B_EXPECTED_ARN]

    # Guard the test's own premise: the two tenants must expect distinct identities, else the
    # "never the other's" assertion below would be meaningless.
    assert not identities_match(tenant_a_expected, tenant_b_expected), (
        'Tenant_A and Tenant_B must map to distinct expected Tenant_Role identifiers'
    )

    tenant_a_headers = {
        'Authorization': f'Bearer {inputs[ENV_TENANT_A_TOKEN]}',
        **_explicit_credential_headers(integration_env, 'AHO_ITEST_TENANT_A_AWS_'),
    }
    tenant_b_headers = {
        'Authorization': f'Bearer {inputs[ENV_TENANT_B_TOKEN]}',
        **_explicit_credential_headers(integration_env, 'AHO_ITEST_TENANT_B_AWS_'),
    }

    async with HarnessMcpClient() as tenant_a, HarnessMcpClient() as tenant_b:
        await with_retries(lambda: tenant_a.open_session(endpoint, tenant_a_headers))
        await with_retries(lambda: tenant_b.open_session(endpoint, tenant_b_headers))

        # Interleave the calls: A, B, A, B — at least two tool calls per tenant (Req 6.1).
        call_plan = (
            (tenant_a, tenant_a_expected, tenant_b_expected, 'Tenant_A call #1'),
            (tenant_b, tenant_b_expected, tenant_a_expected, 'Tenant_B call #1'),
            (tenant_a, tenant_a_expected, tenant_b_expected, 'Tenant_A call #2'),
            (tenant_b, tenant_b_expected, tenant_a_expected, 'Tenant_B call #2'),
        )

        for client, own_expected, other_expected, context in call_plan:
            observed = await _observe_identity(client, context)

            # Every call runs under the calling tenant's own Tenant_Role (Req 6.1, 6.2). On
            # mismatch this raises TenantIdentityMismatch carrying both identities (Req 6.3).
            assert_identity_matches(expected=own_expected, observed=observed, context=context)

            # ...and never under the other tenant's Tenant_Role (Req 6.1).
            assert not identities_match(other_expected, observed), (
                f'{context}: observed identity {observed!r} must never equal the other '
                f"tenant's expected role {other_expected!r}"
            )
