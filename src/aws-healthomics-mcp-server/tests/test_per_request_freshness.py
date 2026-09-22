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

"""Phase 2 per-request credential freshness tests.

Property-based tests for the ``RequestScopedCredentialResolver`` introduced in
``utils/aws_utils.py``. This module is dedicated to Property 18 (Per-request
credential freshness); sibling resolver properties live in separate modules to
avoid file conflicts.

The boto3/botocore mocking patterns mirror those established in
``tests/test_request_scoped_resolver.py`` and ``tests/test_aws_utils.py``.
"""

from awslabs.aws_healthomics_mcp_server.utils.aws_utils import (
    CredentialContext,
    CredentialRequest,
    RequestScopedCredentialResolver,
    get_credential_context,
    reset_credential_context,
    set_credential_context,
)
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st
from typing import Any, cast
from unittest.mock import MagicMock, patch


# Module path prefix for patch targets, matching tests/test_request_scoped_resolver.py.
_AWS_UTILS = 'awslabs.aws_healthomics_mcp_server.utils.aws_utils'


def _access_key_id_for(identity: str) -> str:
    """Derive a distinct, recognizable access key id for an identity."""
    return f'AKIA-{identity}'


def _make_context(identity: str) -> CredentialContext:
    """Build a CredentialContext whose secret fields are derived from the identity."""
    return CredentialContext(
        identity_key=identity,
        access_key_id=_access_key_id_for(identity),
        secret_access_key=f'secret-{identity}',
        session_token=f'token-{identity}',
        source='explicit',
    )


# Pairs of distinct identity strings. Using printable, non-space ASCII keeps the
# derived access key ids readable and unambiguous; ``unique=True`` guarantees the
# two identities (and therefore their access key ids) differ, which is what makes
# cross-request credential reuse observable.
distinct_identity_pairs = st.lists(
    st.text(
        alphabet=st.characters(min_codepoint=0x21, max_codepoint=0x7E),
        min_size=1,
        max_size=10,
    ),
    unique=True,
    min_size=2,
    max_size=2,
)


class TestPerRequestCredentialFreshness:
    """Property: Per-request credential freshness.

    Validates: Requirements Per-request credential freshness.
    """

    @given(identities=distinct_identity_pairs)
    @settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_per_request_credential_freshness(self, identities):
        """Property: Per-request credential freshness.

        For any sequence of two requests with different inbound identities, the
        credentials used for the second request are derived from the second
        request's identity and are never the credentials derived for the first
        request; and after a request completes its context is no longer
        retrievable.

        - The credentials recorded for request one are derived from identity one
          (Requirement: fresh derivation from the request's identity).
        - After request one resets its context, ``get_credential_context()`` is
          ``None`` (Requirement: discard on completion).
        - The credentials recorded for request two are derived from identity two
          and are NEVER identity one's credentials, proving no process-level or
          prior-request session is reused (Requirement: no cross-identity reuse).

        Validates: Requirements Per-request credential freshness.
        """
        identity_one, identity_two = identities
        access_key_id_one = _access_key_id_for(identity_one)
        access_key_id_two = _access_key_id_for(identity_two)

        def _make_session(*args, **kwargs):
            # Return a recordable sentinel keyed by the credentials this call was
            # built with, so each request can assert it received a session built
            # from its own identity rather than a prior request's.
            sentinel = MagicMock()
            sentinel.recorded_access_key_id = kwargs.get('aws_access_key_id')
            sentinel.recorded_secret_access_key = kwargs.get('aws_secret_access_key')
            sentinel.recorded_session_token = kwargs.get('aws_session_token')
            return sentinel

        resolver = RequestScopedCredentialResolver()

        with (
            patch(f'{_AWS_UTILS}.boto3.Session', side_effect=_make_session),
            patch(f'{_AWS_UTILS}.botocore.session.Session', return_value=MagicMock()),
        ):
            # --- Request one: set context, resolve, capture, then complete. ---
            token_one = set_credential_context(_make_context(identity_one))
            try:
                session_one = cast(Any, resolver.resolve(CredentialRequest(region='us-east-1')))
            finally:
                reset_credential_context(token_one)

            # Requirement (discard on completion): once request one completes, its
            # context is no longer retrievable for any subsequent request.
            assert get_credential_context() is None

            # --- Request two: a different inbound identity. ---
            token_two = set_credential_context(_make_context(identity_two))
            try:
                session_two = cast(Any, resolver.resolve(CredentialRequest(region='us-east-1')))
            finally:
                reset_credential_context(token_two)

            # Requirement (discard on completion) again for request two.
            assert get_credential_context() is None

        # Request one derived credentials from identity one.
        assert session_one.recorded_access_key_id == access_key_id_one
        assert session_one.recorded_secret_access_key == f'secret-{identity_one}'
        assert session_one.recorded_session_token == f'token-{identity_one}'

        # Requirement (fresh derivation / no cross-identity reuse): request two's
        # credentials are derived from identity two and are NEVER identity one's.
        assert session_two.recorded_access_key_id == access_key_id_two
        assert session_two.recorded_secret_access_key == f'secret-{identity_two}'
        assert session_two.recorded_session_token == f'token-{identity_two}'

        assert session_two.recorded_access_key_id != access_key_id_one
        assert session_two.recorded_secret_access_key != f'secret-{identity_one}'
        assert session_two.recorded_session_token != f'token-{identity_one}'

    @given(identities=distinct_identity_pairs)
    @settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_build_session_is_fresh_each_call_within_a_context(self, identities):
        """Property: Per-request credential freshness (fresh session per call).

        Within a single request's context, building two sessions constructs a
        fresh ``boto3.Session`` each time rather than reusing a cached one, and
        both sessions carry that request's own credentials.

        Validates: Requirements Per-request credential freshness.
        """
        identity_one, _identity_two = identities
        access_key_id_one = _access_key_id_for(identity_one)

        constructed_sessions = []

        def _make_session(*args, **kwargs):
            sentinel = MagicMock()
            sentinel.recorded_access_key_id = kwargs.get('aws_access_key_id')
            constructed_sessions.append(sentinel)
            return sentinel

        resolver = RequestScopedCredentialResolver()

        with (
            patch(f'{_AWS_UTILS}.boto3.Session', side_effect=_make_session) as mock_session,
            patch(f'{_AWS_UTILS}.botocore.session.Session', return_value=MagicMock()),
        ):
            token = set_credential_context(_make_context(identity_one))
            try:
                first = cast(Any, resolver.resolve(CredentialRequest(region='us-east-1')))
                second = cast(Any, resolver.resolve(CredentialRequest(region='us-east-1')))
            finally:
                reset_credential_context(token)

        # A brand-new session object was constructed on each resolve (no reuse).
        assert mock_session.call_count == 2
        assert first is not second
        assert first.recorded_access_key_id == access_key_id_one
        assert second.recorded_access_key_id == access_key_id_one
