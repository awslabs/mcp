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

"""Property-based tests for missing-context auth error without fallback.

Property: Missing context yields auth error without fallback
    For any resolve (or partition) call in multi-tenant mode when no credential
    context is present, the call raises an authentication error
    (``NoRequestIdentityError``, an ``InboundAuthError``), performs no AWS service
    call (no ``boto3.Session`` is constructed), and does not fall back to another
    context or to the ``DefaultCredentialResolver``.

Validates: Requirements Request-scoped credential resolution, Per-request credential
    freshness
"""

import pytest
from awslabs.aws_healthomics_mcp_server.utils import aws_utils
from awslabs.aws_healthomics_mcp_server.utils.aws_utils import (
    CredentialRequest,
    DefaultCredentialResolver,
    InboundAuthError,
    NoRequestIdentityError,
    RequestScopedCredentialResolver,
    get_active_resolver,
    get_credential_context,
    get_partition,
    set_active_resolver,
)
from hypothesis import given, settings
from hypothesis import strategies as st
from unittest.mock import patch


@pytest.fixture(autouse=True)
def restore_resolver_and_context():
    """Save/restore the active resolver and ensure no credential context leaks.

    Saves the active resolver and clears the cached partition before each test, and
    restores both afterwards so neither the installed resolver nor the ``lru_cache``
    on ``get_partition`` leak state across tests. Also asserts that no per-request
    credential context is present at the start of each test (a prior test must not
    leak a context); if one is present it indicates a contextvar leak.
    """
    saved = get_active_resolver()
    get_partition.cache_clear()
    # Guard against a leaked context from a prior test in this process/task.
    assert get_credential_context() is None
    try:
        yield
    finally:
        set_active_resolver(saved)
        get_partition.cache_clear()


# Region inputs: absent, empty/whitespace, and named regions.
region_inputs = st.one_of(
    st.none(),
    st.sampled_from(['', '   ', 'us-east-1', 'eu-west-1', 'ap-southeast-2']),
    st.text(
        alphabet='abcdefghijklmnopqrstuvwxyz-0123456789',  # pragma: allowlist secret
        max_size=16,
    ),
)

# Profile inputs: absent, empty/whitespace, and named profiles. Profile is
# non-authoritative in multi-tenant mode, but we vary it to prove it never enables
# any fallback when no context is present.
profile_inputs = st.one_of(
    st.none(),
    st.sampled_from(['', '   ', 'default', 'bogus', 'does-not-exist']),
    st.text(
        alphabet='abcdefghijklmnopqrstuvwxyz-_0123456789',  # pragma: allowlist secret
        max_size=16,
    ),
)


class TestMissingContextAuthError:
    """Property: Missing context yields auth error without fallback."""

    @settings(max_examples=100)
    @given(region=region_inputs, profile=profile_inputs)
    def test_resolve_without_context_raises_auth_error_no_fallback(self, region, profile):
        """Property: Missing context yields auth error without fallback (resolve).

        With no credential context present, ``RequestScopedCredentialResolver.resolve``
        raises ``NoRequestIdentityError`` (an ``InboundAuthError``), constructs no
        ``boto3.Session`` (no AWS service call), and never falls back to the
        ``DefaultCredentialResolver``.

        Validates: Requirements Request-scoped credential resolution, Per-request
            credential freshness
        """
        # Precondition: no per-request credential context is set.
        assert get_credential_context() is None

        resolver = RequestScopedCredentialResolver()

        # Patch boto3.Session to PROVE no AWS session/client is constructed, and spy on
        # DefaultCredentialResolver.resolve to PROVE no fallback to the default chain.
        with (
            patch.object(aws_utils.boto3, 'Session') as mock_session,
            patch.object(
                DefaultCredentialResolver, 'resolve', autospec=True
            ) as mock_default_resolve,
        ):
            with pytest.raises(NoRequestIdentityError) as exc_info:
                resolver.resolve(CredentialRequest(region=region, profile=profile))

        # The raised error is an inbound authentication error.
        assert isinstance(exc_info.value, InboundAuthError)
        # No AWS session (and therefore no AWS service call) was constructed.
        mock_session.assert_not_called()
        # No fallback to the default credential resolver occurred.
        mock_default_resolve.assert_not_called()

    @settings(max_examples=100)
    @given(region=region_inputs, profile=profile_inputs)
    def test_get_partition_without_context_raises_auth_error_no_fallback(self, region, profile):
        """Property: Missing context yields auth error without fallback (get_partition).

        With the request-scoped resolver active and no credential context present,
        ``get_partition`` raises ``NoRequestIdentityError`` (an ``InboundAuthError``),
        constructs no ``boto3.Session`` (no AWS service call), and never falls back to
        the ``DefaultCredentialResolver``.

        Validates: Requirements Request-scoped credential resolution, Per-request
            credential freshness
        """
        # Precondition: no per-request credential context is set.
        assert get_credential_context() is None

        # Install the request-scoped resolver as the active resolver (multi-tenant mode).
        set_active_resolver(RequestScopedCredentialResolver())
        # get_partition is lru_cache'd; clear so the call under test actually routes
        # through the active resolver rather than returning a memoized value.
        get_partition.cache_clear()

        with (
            patch.object(aws_utils.boto3, 'Session') as mock_session,
            patch.object(
                DefaultCredentialResolver, 'resolve', autospec=True
            ) as mock_default_resolve,
        ):
            with pytest.raises(NoRequestIdentityError) as exc_info:
                get_partition(region_name=region, profile_name=profile)

        # The raised error is an inbound authentication error.
        assert isinstance(exc_info.value, InboundAuthError)
        # No AWS session (and therefore no AWS service call) was constructed.
        mock_session.assert_not_called()
        # No fallback to the default credential resolver occurred.
        mock_default_resolve.assert_not_called()
