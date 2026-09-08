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

"""Tool-call-level ``AccessDenied`` pass-through tests under a jwt context.

These tests focus on Cross-account execution under the customer role: when the
Customer_Role lacks a specific action, a tool's AWS call returns a normal AWS
``AccessDenied`` and that outcome is surfaced to the caller as a *tool-call
failure result* — never retried under other credentials, and never converted
into a Credential_Derivation_Error or an inbound ``401``. This is the row
"Customer role lacks a specific action -> Normal AWS AccessDenied from the tool
call (per-action)" in the design's Error Handling table.

The companion ``tests/test_jwt_context_session_build.py`` asserts the same
guarantee at the credential-resolution seam (the resolver builds the session
solely from the jwt context and does not catch/convert a tool-call
``AccessDenied``). This module complements that by exercising a representative
*real tool* end to end — ``list_runs`` from ``tools/workflow_execution.py`` —
so the assertion is made at the genuine tool-call level:

- A ``source='jwt'`` :class:`CredentialContext` is installed and the
  request-scoped resolver is the active credential seam, exactly as in
  multi-tenant mode.
- The tool builds its ``omics`` client through that seam (``get_omics_client``
  -> ``get_aws_session`` -> :class:`RequestScopedCredentialResolver` ->
  ``CredentialContext.build_session``) from ONLY the jwt context's temporary
  credentials.
- The omics operation raises a botocore ``AccessDenied`` ``ClientError``.

The boto3/botocore mocking mirrors ``tests/test_jwt_context_session_build.py``
and ``tests/test_per_request_freshness.py``; no real AWS calls are made.
"""

import pytest
from awslabs.aws_healthomics_mcp_server.tools.workflow_execution import list_runs
from awslabs.aws_healthomics_mcp_server.utils import aws_utils
from awslabs.aws_healthomics_mcp_server.utils.aws_utils import (
    CredentialContext,
    CredentialDerivationError,
    InboundAuthError,
    RequestScopedCredentialResolver,
    get_active_resolver,
    reset_credential_context,
    set_active_resolver,
    set_credential_context,
)
from botocore.exceptions import ClientError
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch


# Module path prefix for patch targets, matching tests/test_jwt_context_session_build.py.
_AWS_UTILS = 'awslabs.aws_healthomics_mcp_server.utils.aws_utils'


def _jwt_context(identity: str) -> CredentialContext:
    """Build a ``source='jwt'`` context with credentials derived from the identity.

    Mirrors the shape ``InboundJwtExchange.derive`` populates from an
    ``sts:AssumeRole`` response, so the credentials are recognizable per identity.
    """
    return CredentialContext(
        identity_key=identity,
        access_key_id=f'ASIA-{identity}',
        secret_access_key=f'secret-{identity}',
        session_token=f'token-{identity}',
        source='jwt',
    )


def _access_denied_error(operation_name: str) -> ClientError:
    """Build a botocore ``AccessDenied`` ClientError for a tool operation.

    Represents the customer role lacking a specific action's permission — a normal
    per-action AWS denial, distinct from an STS/credential-derivation failure.
    """
    return ClientError(
        error_response={
            'Error': {
                'Code': 'AccessDenied',
                'Message': 'User is not authorized to perform this action.',
            }
        },
        operation_name=operation_name,
    )


@pytest.fixture
def request_scoped_resolver_active():
    """Install the request-scoped resolver as the active seam for the test.

    Restores the previously active resolver afterwards so the process-wide seam
    is unchanged for other tests. This reproduces multi-tenant mode, where tools
    build sessions from the per-request jwt :class:`CredentialContext`.
    """
    previous_resolver = get_active_resolver()
    set_active_resolver(RequestScopedCredentialResolver())
    try:
        yield
    finally:
        set_active_resolver(previous_resolver)


class TestAccessDeniedToolCallPassthrough:
    """A tool-call ``AccessDenied`` under a jwt context is a tool-call failure.

    Validates: Requirements Cross-account execution under the customer role.
    """

    @pytest.mark.asyncio
    async def test_tool_call_access_denied_surfaces_as_tool_failure_result(
        self, request_scoped_resolver_active
    ):
        """AccessDenied from a real tool call becomes a tool-call failure result.

        Exercising the real ``list_runs`` tool end to end under a ``source='jwt'``
        context: the omics ``ListRuns`` operation raises an AWS ``AccessDenied``.
        The tool returns a plain error result (an ``{'error': ...}`` dict reported
        via ``ctx.error``) indicating the AWS call was denied. It does NOT raise —
        and specifically does NOT convert the denial into a
        ``CredentialDerivationError`` or an inbound-auth (``401``) error.

        Validates: Requirements Cross-account execution under the customer role.
        """
        context = _jwt_context('customer-a')
        mock_ctx = AsyncMock()

        omics_client = MagicMock()
        omics_client.list_runs.side_effect = _access_denied_error('ListRuns')
        built_session = MagicMock()
        built_session.client.return_value = omics_client

        with (
            patch(f'{_AWS_UTILS}.boto3.Session', return_value=built_session),
            patch(f'{_AWS_UTILS}.botocore.session.Session', return_value=MagicMock()),
        ):
            token = set_credential_context(context)
            try:
                # No exception should escape the tool: the denial is a tool-call
                # failure result, not a credential-derivation / inbound-auth error.
                result = await list_runs(
                    ctx=mock_ctx,
                    max_results=10,
                    next_token=None,
                    status=None,
                    created_after=None,
                    created_before=None,
                )
            except (CredentialDerivationError, InboundAuthError) as exc:  # pragma: no cover
                pytest.fail(
                    'Tool-call AccessDenied was wrongly converted into a credential '
                    f'derivation / inbound-auth error: {type(exc).__name__}'
                )
            finally:
                reset_credential_context(token)

        # The tool returned a failure result describing the denied AWS call.
        assert isinstance(result, dict)
        assert 'error' in result
        assert 'Error listing runs' in result['error']
        # The per-action AWS AccessDenied is reflected in the surfaced failure.
        assert 'AccessDenied' in result['error']

        # The denial was reported to the caller as a tool error exactly once.
        mock_ctx.error.assert_called_once()
        assert 'Error listing runs' in mock_ctx.error.call_args[0][0]

    @pytest.mark.asyncio
    async def test_tool_call_access_denied_is_not_retried_under_other_credentials(
        self, request_scoped_resolver_active
    ):
        """The denied operation runs once, solely under the jwt context credentials.

        The tool must not retry the denied ``ListRuns`` call under any other
        credentials, and the session it built must come from ONLY the jwt
        context's temporary credentials (no process-level ``profile_name`` /
        default-chain fallback). ``aws_profile`` is supplied on the tool call to
        prove the seam ignores it and never re-derives under a process profile.

        Validates: Requirements Cross-account execution under the customer role.
        """
        context = _jwt_context('customer-b')
        mock_ctx = AsyncMock()
        captured: dict[str, Any] = {}

        omics_client = MagicMock()
        omics_client.list_runs.side_effect = _access_denied_error('ListRuns')

        def _make_session(*args, **kwargs):
            captured.update(kwargs)
            session = MagicMock()
            session.client.return_value = omics_client
            return session

        with (
            patch(f'{_AWS_UTILS}.boto3.Session', side_effect=_make_session),
            patch(f'{_AWS_UTILS}.botocore.session.Session', return_value=MagicMock()),
        ):
            token = set_credential_context(context)
            try:
                result = await list_runs(
                    ctx=mock_ctx,
                    max_results=10,
                    next_token=None,
                    status=None,
                    created_after=None,
                    created_before=None,
                    aws_profile='some-process-profile',
                )
            finally:
                reset_credential_context(token)

        # A tool-call failure result was returned (no retry loop, no raised error).
        assert isinstance(result, dict)
        assert 'error' in result

        # The denied operation was attempted exactly once — not retried under any
        # other credentials.
        assert omics_client.list_runs.call_count == 1

        # The session was built solely from the jwt context's temporary
        # credentials; the supplied process profile was ignored (no fallback).
        assert captured['aws_access_key_id'] == 'ASIA-customer-b'
        assert captured['aws_secret_access_key'] == 'secret-customer-b'  # pragma: allowlist secret
        assert captured['aws_session_token'] == 'token-customer-b'  # pragma: allowlist secret
        assert 'profile_name' not in captured


class TestAccessDeniedIsPlainClientErrorNotConverted:
    """The raw tool-call denial is a botocore ``ClientError``, not a wrapped error.

    Validates: Requirements Cross-account execution under the customer role.
    """

    def test_access_denied_from_seam_built_client_is_unconverted_client_error(self):
        """AccessDenied raised by a seam-built client is a plain botocore ClientError.

        A client built through the credential seam under a jwt context raises the
        AWS ``AccessDenied`` directly. The exception is a botocore ``ClientError``
        carrying error Code ``AccessDenied`` and is NOT an instance of
        ``CredentialDerivationError`` or ``InboundAuthError`` — the seam neither
        wraps nor re-derives on a per-action tool-call denial.

        Validates: Requirements Cross-account execution under the customer role.
        """
        context = _jwt_context('customer-c')

        omics_client = MagicMock()
        omics_client.list_runs.side_effect = _access_denied_error('ListRuns')
        built_session = MagicMock()
        built_session.client.return_value = omics_client

        resolver = RequestScopedCredentialResolver()

        with (
            patch(f'{_AWS_UTILS}.boto3.Session', return_value=built_session),
            patch(f'{_AWS_UTILS}.botocore.session.Session', return_value=MagicMock()),
        ):
            token = set_credential_context(context)
            try:
                session = resolver.resolve(aws_utils.CredentialRequest(region='us-east-1'))
                client = session.client('omics')
                with pytest.raises(ClientError) as excinfo:
                    client.list_runs()
            finally:
                reset_credential_context(token)

        error = excinfo.value
        # A per-action AWS AccessDenied, i.e. a normal tool-call failure.
        assert error.response['Error']['Code'] == 'AccessDenied'
        # Not converted into a credential-derivation / inbound-auth (401) failure.
        assert not isinstance(error, CredentialDerivationError)
        assert not isinstance(error, InboundAuthError)
        # The denied operation was attempted exactly once (no retry).
        assert omics_client.list_runs.call_count == 1
