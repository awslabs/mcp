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

"""Property-based tests that profile is non-authoritative in multi-tenant mode.

Property: Profile is non-authoritative in multi-tenant mode
    For any credential context and for any ``aws_profile`` input (absent, empty, or
    any profile name), the resolved identity in multi-tenant mode is identical
    (determined solely by the context), and the request is not failed merely because
    a profile was supplied.

Validates: Requirements Profile argument is non-authoritative in multi-tenant mode
"""

import pytest
from awslabs.aws_healthomics_mcp_server.utils import aws_utils
from awslabs.aws_healthomics_mcp_server.utils.aws_utils import (
    CredentialContext,
    CredentialRequest,
    RequestScopedCredentialResolver,
    get_credential_context,
    reset_credential_context,
    set_credential_context,
)
from hypothesis import given, settings
from hypothesis import strategies as st
from unittest.mock import MagicMock, patch


# A single fixed context used for every example. The resolved identity must be
# determined solely by this context, never by the supplied profile.
FIXED_REGION = 'us-east-1'
FIXED_ACCESS_KEY_ID = 'AKIAFIXEDCONTEXTKEY'  # pragma: allowlist secret
FIXED_SECRET_ACCESS_KEY = 'fixed-context-secret'  # pragma: allowlist secret
FIXED_SESSION_TOKEN = 'fixed-context-session-token'  # pragma: allowlist secret
FIXED_IDENTITY_KEY = 'fixed-identity-key'


def _make_fixed_context() -> CredentialContext:
    """Build the single fixed credential context shared by all examples."""
    return CredentialContext(
        identity_key=FIXED_IDENTITY_KEY,
        access_key_id=FIXED_ACCESS_KEY_ID,
        secret_access_key=FIXED_SECRET_ACCESS_KEY,
        session_token=FIXED_SESSION_TOKEN,
        source='explicit',
    )


@pytest.fixture(autouse=True)
def no_leaked_context():
    """Guard against a credential context leaking in from a prior test.

    Asserts no per-request credential context is present at the start of each test.
    Each test sets and resets its own context per example, so none should leak out;
    this fixture verifies the precondition and provides defense in depth.
    """
    assert get_credential_context() is None
    yield
    assert get_credential_context() is None


# Profile inputs: absent (None), empty, whitespace-only, and arbitrary profile
# names. Profile is non-authoritative in multi-tenant mode; we vary it across the
# whole input space to prove it never changes the resolved identity and never fails
# the request merely because it was supplied.
profile_inputs = st.one_of(
    st.none(),
    st.just(''),
    st.just('   '),
    st.text(
        alphabet='abcdefghijklmnopqrstuvwxyz-_0123456789',  # pragma: allowlist secret
        max_size=24,
    ),
)


class TestProfileNonAuthoritative:
    """Property: Profile is non-authoritative in multi-tenant mode."""

    @settings(max_examples=100)
    @given(profile=profile_inputs)
    def test_profile_does_not_affect_resolved_identity(self, profile):
        """Property: Profile is non-authoritative in multi-tenant mode.

        With a single fixed credential context active, resolving for any profile
        input (absent, empty, whitespace, or any name) builds a session from the
        context's credentials only: the access key id always equals the context's
        access key id and is never derived from the profile, and ``profile_name`` is
        never forwarded to ``boto3.Session`` (Requirement 10.1). The call also never
        fails merely because a profile was supplied (Requirement 10.2).

        Validates: Requirements Profile argument is non-authoritative in multi-tenant
            mode
        """
        token = set_credential_context(_make_fixed_context())
        try:
            resolver = RequestScopedCredentialResolver()

            # Patch boto3.Session to capture the credentials used and avoid any real
            # AWS interaction. The identity is what boto3.Session is constructed with.
            with patch.object(aws_utils.boto3, 'Session') as mock_session:
                mock_session.return_value = MagicMock()

                # Requirement 10.2: supplying a profile must not fail the request.
                session = resolver.resolve(CredentialRequest(region=FIXED_REGION, profile=profile))

                assert session is mock_session.return_value

            # A session was constructed exactly once from the context.
            mock_session.assert_called_once()
            _, call_kwargs = mock_session.call_args

            # Requirement 10.1: identity comes solely from the context. The access
            # key id always equals the context's key, never anything derived from
            # the supplied profile.
            assert call_kwargs['aws_access_key_id'] == FIXED_ACCESS_KEY_ID
            assert call_kwargs['aws_secret_access_key'] == FIXED_SECRET_ACCESS_KEY
            assert call_kwargs['aws_session_token'] == FIXED_SESSION_TOKEN

            # The profile is ignored entirely for identity selection: it is never
            # forwarded to boto3.Session under any key.
            assert 'profile_name' not in call_kwargs
            assert 'profile' not in call_kwargs
        finally:
            reset_credential_context(token)

        # Requirement 12.3: the context does not leak past the request.
        assert get_credential_context() is None

    @settings(max_examples=100)
    @given(profile=profile_inputs)
    def test_resolved_identity_is_identical_for_all_profiles(self, profile):
        """Property: Profile is non-authoritative in multi-tenant mode.

        The resolved identity for any profile input is identical to the identity
        resolved with no profile at all: both build a session from the same fixed
        context credentials. This proves the resolved identity is determined solely
        by the context, not the profile (Requirement 10.1).

        Validates: Requirements Profile argument is non-authoritative in multi-tenant
            mode
        """
        resolver = RequestScopedCredentialResolver()

        def resolve_with(profile_value):
            token = set_credential_context(_make_fixed_context())
            try:
                with patch.object(aws_utils.boto3, 'Session') as mock_session:
                    mock_session.return_value = MagicMock()
                    resolver.resolve(CredentialRequest(region=FIXED_REGION, profile=profile_value))
                _, call_kwargs = mock_session.call_args
                return {
                    'aws_access_key_id': call_kwargs.get('aws_access_key_id'),
                    'aws_secret_access_key': call_kwargs.get('aws_secret_access_key'),
                    'aws_session_token': call_kwargs.get('aws_session_token'),
                    'profile_name': call_kwargs.get('profile_name'),
                }
            finally:
                reset_credential_context(token)

        # The baseline identity with no profile supplied.
        baseline = resolve_with(None)
        # The identity with the varied profile supplied.
        varied = resolve_with(profile)

        # Identity is identical regardless of the profile value.
        assert varied == baseline
        assert varied['aws_access_key_id'] == FIXED_ACCESS_KEY_ID
        assert varied['profile_name'] is None
