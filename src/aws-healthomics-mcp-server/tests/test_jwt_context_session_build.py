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

"""Cross-account execution tests for the jwt ``CredentialContext`` at the seam.

These tests exercise the credential-resolution seam in ``utils/aws_utils.py`` for
a ``source='jwt'`` :class:`CredentialContext` (the context populated by
``InboundJwtExchange`` after an ``sts:AssumeRole`` against the customer role).

They validate two requirements of Cross-account execution under the customer role:

- **Tool sessions build solely from the jwt context's temporary credentials.**
  A ``source='jwt'`` context builds the tool's ``boto3.Session`` only from its
  access key id, secret access key, and session token — never from a process-level
  profile or the default credential chain.
- **Tool-call ``AccessDenied`` is a tool failure, not a credential-derivation
  failure.** An AWS ``AccessDenied`` raised from a client built under the jwt
  context surfaces as a plain ``botocore`` ``ClientError`` and is never converted
  into a ``CredentialDerivationError`` or an inbound ``401`` by the seam.

The boto3/botocore mocking patterns mirror ``tests/test_per_request_freshness.py``
and ``tests/test_partition_cache_isolation.py``. No real AWS calls are made.
"""

import pytest
from awslabs.aws_healthomics_mcp_server.utils.aws_utils import (
    CredentialContext,
    CredentialDerivationError,
    CredentialRequest,
    InboundAuthError,
    NoRequestIdentityError,
    RequestScopedCredentialResolver,
    reset_credential_context,
    set_credential_context,
)
from botocore.exceptions import ClientError
from hypothesis import given, settings
from hypothesis import strategies as st
from typing import Any, cast
from unittest.mock import MagicMock, patch


# Module path prefix for patch targets, matching tests/test_per_request_freshness.py.
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


# Printable, non-space ASCII identity strings keep the derived credentials
# readable and unambiguous when asserting which values were passed through.
identity_strategy = st.text(
    alphabet=st.characters(min_codepoint=0x21, max_codepoint=0x7E),
    min_size=1,
    max_size=12,
)

region_strategy = st.sampled_from(
    [
        'us-east-1',
        'us-west-2',
        'eu-west-1',
        'cn-north-1',
        'us-gov-west-1',
    ]
)


class TestJwtContextBuildsSessionFromTemporaryCredentialsOnly:
    """Property: tool sessions build solely from the jwt context's credentials.

    Validates: Requirements Cross-account execution under the customer role.
    """

    @given(identity=identity_strategy, region=region_strategy)
    @settings(max_examples=100)
    def test_build_session_uses_only_context_temporary_credentials(self, identity, region):
        """A jwt context builds a session from ONLY its temporary credentials.

        ``CredentialContext.build_session`` must construct the ``boto3.Session``
        purely from the context's access key id, secret access key, and session
        token, and must NOT introduce any process-level fallback such as a
        ``profile_name`` (which would select the default credential chain / a named
        profile instead of the assumed-role credentials).

        Validates: Requirements Cross-account execution under the customer role.
        """
        context = _jwt_context(identity)
        captured: dict[str, Any] = {}

        def _make_session(*args, **kwargs):
            captured.update(kwargs)
            return MagicMock()

        with (
            patch(f'{_AWS_UTILS}.boto3.Session', side_effect=_make_session),
            patch(f'{_AWS_UTILS}.botocore.session.Session', return_value=MagicMock()),
        ):
            context.build_session(region=region)

        # The session is built from exactly the context's temporary credentials.
        assert captured['aws_access_key_id'] == f'ASIA-{identity}'
        assert captured['aws_secret_access_key'] == f'secret-{identity}'
        assert captured['aws_session_token'] == f'token-{identity}'
        assert captured['region_name'] == region

        # No process-level fallback: a profile would bypass the assumed-role
        # credentials and select the default chain / a named profile instead.
        assert 'profile_name' not in captured

    @given(identity=identity_strategy, region=region_strategy)
    @settings(max_examples=100)
    def test_resolver_seam_builds_jwt_session_from_context_and_ignores_profile(
        self, identity, region
    ):
        """The request-scoped seam builds the jwt session from the context only.

        Routing through ``RequestScopedCredentialResolver.resolve`` (the seam every
        tool uses) must build the session from the active jwt context's temporary
        credentials and must ignore any ``profile`` on the request, so no
        process-level profile can override the assumed-role credentials.

        Validates: Requirements Cross-account execution under the customer role.
        """
        context = _jwt_context(identity)
        captured: dict[str, Any] = {}

        def _make_session(*args, **kwargs):
            captured.update(kwargs)
            return MagicMock()

        resolver = RequestScopedCredentialResolver()

        with (
            patch(f'{_AWS_UTILS}.boto3.Session', side_effect=_make_session),
            patch(f'{_AWS_UTILS}.botocore.session.Session', return_value=MagicMock()),
        ):
            token = set_credential_context(context)
            try:
                # A process-level profile is supplied but MUST be ignored for
                # identity selection; the jwt context's credentials win.
                resolver.resolve(CredentialRequest(region=region, profile='some-process-profile'))
            finally:
                reset_credential_context(token)

        assert captured['aws_access_key_id'] == f'ASIA-{identity}'
        assert captured['aws_secret_access_key'] == f'secret-{identity}'
        assert captured['aws_session_token'] == f'token-{identity}'
        assert captured['region_name'] == region
        assert 'profile_name' not in captured

    def test_resolver_never_falls_back_to_process_credentials(self):
        """With no jwt context installed, the seam refuses a process-level fallback.

        When a tool runs without a resolved inbound identity, the request-scoped
        resolver raises ``NoRequestIdentityError`` rather than silently building a
        session from process-level credentials.

        Validates: Requirements Cross-account execution under the customer role.
        """
        resolver = RequestScopedCredentialResolver()
        with pytest.raises(NoRequestIdentityError):
            resolver.resolve(CredentialRequest(region='us-east-1'))


class TestJwtContextAccessDeniedIsToolFailureNotAuthError:
    """A tool-call ``AccessDenied`` under a jwt context is a plain ``ClientError``.

    Validates: Requirements Cross-account execution under the customer role.
    """

    def _access_denied_error(self, operation_name: str) -> ClientError:
        """Build a botocore ``AccessDenied`` ClientError for a tool operation."""
        return ClientError(
            error_response={
                'Error': {
                    'Code': 'AccessDenied',
                    'Message': 'User is not authorized to perform this action.',
                }
            },
            operation_name=operation_name,
        )

    def test_access_denied_from_tool_call_surfaces_as_plain_client_error(self):
        """AccessDenied from an operation propagates as a botocore ClientError.

        The seam builds the session/client from the jwt context successfully; the
        ``AccessDenied`` raised by an actual tool operation (here ``ListRuns``) is a
        normal ``botocore`` ``ClientError`` and is NOT converted into a
        ``CredentialDerivationError`` or any inbound-auth (``401``) error.

        Validates: Requirements Cross-account execution under the customer role.
        """
        context = _jwt_context('customer-a')

        tool_client = MagicMock()
        tool_client.list_runs.side_effect = self._access_denied_error('ListRuns')
        built_session = MagicMock()
        built_session.client.return_value = tool_client

        resolver = RequestScopedCredentialResolver()

        with (
            patch(f'{_AWS_UTILS}.boto3.Session', return_value=built_session),
            patch(f'{_AWS_UTILS}.botocore.session.Session', return_value=MagicMock()),
        ):
            token = set_credential_context(context)
            try:
                # Building the session and client under the jwt context succeeds:
                # the seam does not fail closed on a tool-level permissions error.
                session = cast(Any, resolver.resolve(CredentialRequest(region='us-east-1')))
                client = session.client('omics')

                # The tool operation's AccessDenied surfaces as-is.
                with pytest.raises(ClientError) as excinfo:
                    client.list_runs()
            finally:
                reset_credential_context(token)

        error = excinfo.value
        # It is a per-action AWS AccessDenied, i.e. a normal tool-call failure.
        assert error.response['Error']['Code'] == 'AccessDenied'
        # It was NOT converted into a credential-derivation / inbound-auth failure.
        assert not isinstance(error, CredentialDerivationError)
        assert not isinstance(error, InboundAuthError)

    def test_seam_does_not_retry_or_convert_access_denied(self):
        """The seam does not catch, retry, or convert a tool-call AccessDenied.

        The client operation is invoked exactly once (no retry under other
        credentials), and the resolver builds the session solely from the jwt
        context's temporary credentials, confirming the AccessDenied is left to
        surface as a tool-call failure rather than being re-derived.

        Validates: Requirements Cross-account execution under the customer role.
        """
        context = _jwt_context('customer-b')
        captured: dict[str, Any] = {}

        tool_client = MagicMock()
        tool_client.list_runs.side_effect = self._access_denied_error('ListRuns')

        def _make_session(*args, **kwargs):
            captured.update(kwargs)
            session = MagicMock()
            session.client.return_value = tool_client
            return session

        resolver = RequestScopedCredentialResolver()

        with (
            patch(f'{_AWS_UTILS}.boto3.Session', side_effect=_make_session),
            patch(f'{_AWS_UTILS}.botocore.session.Session', return_value=MagicMock()),
        ):
            token = set_credential_context(context)
            try:
                session = cast(Any, resolver.resolve(CredentialRequest(region='us-east-1')))
                client = session.client('omics')
                with pytest.raises(ClientError):
                    client.list_runs()
            finally:
                reset_credential_context(token)

        # The denied operation was attempted once and not retried.
        assert tool_client.list_runs.call_count == 1
        # The session was built solely from the jwt context's temporary credentials.
        assert captured['aws_access_key_id'] == 'ASIA-customer-b'
        assert captured['aws_secret_access_key'] == 'secret-customer-b'  # pragma: allowlist secret
        assert captured['aws_session_token'] == 'token-customer-b'  # pragma: allowlist secret
        assert 'profile_name' not in captured
