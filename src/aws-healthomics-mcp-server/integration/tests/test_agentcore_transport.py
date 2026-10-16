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


"""Opt-in transport verification for the AgentCore fronting layer (live AWS).

This module exercises the AWS HealthOmics MCP Server hosted on Amazon Bedrock AgentCore
Runtime end-to-end, through AgentCore as the sole authenticated ingress. It drives the
ordered ``session -> list -> invoke`` sequence with the harness MCP client and verification
driver, applying the harness retry policy so transient unavailability is retried before the
check is failed.

The test is gated behind the Opt_In_Signal and is skipped by default: the
``pytest_collection_modifyitems`` hook in ``integration/conftest.py`` skips every item under
``integration/tests/`` when ``RUN_REMOTE_INTEGRATION_TESTS`` is absent, and the
``require_inputs`` fixture skips (never fails) when a required configuration input is missing.
Because the skip is applied at collection time, no AWS client is constructed offline.

Validates: Requirements Remote transport end-to-end verification (session establishment,
tool listing, tool invocation, retry-on-transient, and coverage against the AgentCore
deployment) and Requirements AgentCore deployment demonstration (AgentCore serves MCP over
its inbound authorizer and reports completion once its endpoint reference is reachable).
"""

from __future__ import annotations

import pytest
from collections.abc import Callable, Mapping
from integration.harness.headers import (
    EXPLICIT_ACCESS_KEY_ID_HEADER,
    EXPLICIT_SECRET_ACCESS_KEY_HEADER,
    EXPLICIT_SESSION_TOKEN_HEADER,
)
from integration.harness.mcp_client import (
    DEFAULT_ATTEMPTS,
    DEFAULT_MIN_INTERVAL_S,
    HarnessMcpClient,
    TransportVerificationResult,
    verify_transport,
    with_retries,
)


# Environment inputs required to reach the provisioned AgentCore deployment. Missing inputs
# cause a skip (not a failure) via the ``require_inputs`` fixture (Req 1.6).
AGENTCORE_ENDPOINT_ENV = 'AHO_ITEST_AGENTCORE_ENDPOINT'
BEARER_TOKEN_ENV = 'AHO_ITEST_BEARER_TOKEN'


def _explicit_credential_headers(env, prefix: str) -> dict[str, str]:
    """Return the X-Aws-* headers for the explicit-mechanism workaround, or empty if unset.

    In the default ``jwt`` deployment these environment variables are absent and this returns
    ``{}`` (no behavior change). In the ``explicit`` deployment the harness exports short-lived
    per-tenant credentials under ``<prefix>ACCESS_KEY_ID`` / ``SECRET_ACCESS_KEY`` /
    ``SESSION_TOKEN``, which are forwarded so the server can use them directly.
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


# A small set of known, safe, read-only HealthOmics tools registered by the server. The
# verification driver passes if the advertised list contains at least one of these and an
# invocation of it returns a non-error result. ``GetAHOSupportedRegions`` requires no
# arguments and performs no mutation, so it is safe to call against a live deployment.
KNOWN_HEALTHOMICS_TOOLS: frozenset[str] = frozenset({'GetAHOSupportedRegions'})


def _bearer_headers(token: str) -> dict[str, str]:
    """Build the request headers carrying the caller's bearer token."""
    return {'Authorization': f'Bearer {token}'}


@pytest.mark.integration
async def test_agentcore_transport_verification(
    require_inputs: Callable[[list[str]], Mapping[str, str]],
    integration_env: Mapping[str, str],
) -> None:
    """Verify end-to-end MCP transport through the AgentCore fronting layer.

    Establishes an MCP session within 30s, lists tools within 30s and confirms the list
    contains a known HealthOmics tool, then invokes that tool and requires a non-error result
    within 60s. The whole verification runs under the harness retry policy so transient
    fronting-layer or server unavailability is retried up to three additional times at least
    one second apart before the check is failed.

    Validates: Requirements Remote transport end-to-end verification and Requirements
    AgentCore deployment demonstration (AgentCore serves MCP over its inbound authorizer).
    """
    inputs = require_inputs([AGENTCORE_ENDPOINT_ENV, BEARER_TOKEN_ENV])
    endpoint = inputs[AGENTCORE_ENDPOINT_ENV]
    headers = {
        **_bearer_headers(inputs[BEARER_TOKEN_ENV]),
        **_explicit_credential_headers(integration_env, 'AHO_ITEST_AWS_'),
    }

    client = HarnessMcpClient()

    async def _verify() -> TransportVerificationResult:
        return await verify_transport(
            client,
            endpoint,
            headers,
            KNOWN_HEALTHOMICS_TOOLS,
            tool_args={},
        )

    async with client:
        result = await with_retries(
            _verify,
            attempts=DEFAULT_ATTEMPTS,
            min_interval_s=DEFAULT_MIN_INTERVAL_S,
        )

    assert isinstance(result, TransportVerificationResult)
    assert result.tool_name in KNOWN_HEALTHOMICS_TOOLS
    assert not getattr(result.result, 'isError', False)
