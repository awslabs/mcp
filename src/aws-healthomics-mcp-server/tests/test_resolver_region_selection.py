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

"""Property-based tests for region selection in multi-tenant mode.

Property: Region selection in multi-tenant mode
    For any credential context, when an ``aws_region`` input is present and
    non-empty the resolved session uses that region, and when it is absent the
    resolved session uses the configured default region.

Validates: Requirements Profile argument is non-authoritative in multi-tenant mode
"""

import pytest
from awslabs.aws_healthomics_mcp_server.consts import DEFAULT_REGION
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
from unittest.mock import patch


def _make_context() -> CredentialContext:
    """Build a fixed, non-secret credential context for use in tests."""
    return CredentialContext(
        identity_key='identity-under-test',
        access_key_id='AKIAEXAMPLE',  # pragma: allowlist secret
        secret_access_key='secret-example',  # pragma: allowlist secret
        session_token=None,
        source='explicit',
    )


@pytest.fixture(autouse=True)
def guard_no_leaked_context():
    """Ensure no per-request credential context leaks into or out of a test.

    Asserts no context is present at the start of each test (a prior test must not
    leak a context via the contextvar) so that each example sets and resets its own
    context explicitly.
    """
    assert get_credential_context() is None
    yield
    assert get_credential_context() is None


# Present-and-non-empty region inputs. Per the property statement, a present
# non-empty region is used as-is. We include named regions plus arbitrary
# non-empty strings; whitespace-only strings are truthy and therefore used
# as-is (documented behavior of ``request.region or get_region()``), so we
# exclude purely-empty strings here and cover empty/absent in the default case.
present_regions = st.one_of(
    st.sampled_from(['us-east-1', 'eu-west-1', 'ap-southeast-2', 'us-gov-west-1']),
    st.text(
        alphabet='abcdefghijklmnopqrstuvwxyz-0123456789',  # pragma: allowlist secret
        min_size=1,
        max_size=16,
    ).filter(lambda string_value: string_value != ''),
)

# Absent/empty region inputs that should fall through to the configured default
# region via ``get_region()`` (``request.region or get_region()`` treats both
# ``None`` and ``''`` as falsy).
absent_regions = st.sampled_from([None, ''])


class TestRegionSelectionMultiTenant:
    """Property: Region selection in multi-tenant mode."""

    @settings(max_examples=100)
    @given(region=present_regions)
    def test_present_region_is_used(self, region):
        """Property: Region selection in multi-tenant mode (present region).

        With a credential context active, when a present non-empty ``aws_region``
        input is supplied, the resolved session is built with that exact region.

        Validates: Requirements Profile argument is non-authoritative in multi-tenant
            mode
        """
        token = set_credential_context(_make_context())
        try:
            resolver = RequestScopedCredentialResolver()
            with patch.object(aws_utils.boto3, 'Session') as mock_session:
                resolver.resolve(CredentialRequest(region=region, profile=None))

            mock_session.assert_called_once()
            assert mock_session.call_args.kwargs['region_name'] == region
        finally:
            reset_credential_context(token)

    @settings(max_examples=100)
    @given(region=absent_regions, default_region=present_regions)
    def test_absent_region_uses_configured_default(self, region, default_region):
        """Property: Region selection in multi-tenant mode (absent region).

        With a credential context active, when the ``aws_region`` input is absent
        (``None``) or empty (``''``), the resolved session is built using the
        configured default region from ``get_region()`` (the ``AWS_REGION``
        environment variable).

        Validates: Requirements Profile argument is non-authoritative in multi-tenant
            mode
        """
        token = set_credential_context(_make_context())
        try:
            resolver = RequestScopedCredentialResolver()
            with (
                patch.dict('os.environ', {'AWS_REGION': default_region}),
                patch.object(aws_utils.boto3, 'Session') as mock_session,
            ):
                resolver.resolve(CredentialRequest(region=region, profile=None))

            mock_session.assert_called_once()
            assert mock_session.call_args.kwargs['region_name'] == default_region
        finally:
            reset_credential_context(token)

    def test_absent_region_unset_env_uses_default_region_constant(self):
        """Example: absent region with ``AWS_REGION`` unset uses ``DEFAULT_REGION``.

        With a credential context active and the ``AWS_REGION`` environment variable
        unset, an absent ``aws_region`` input resolves the session using the
        ``DEFAULT_REGION`` constant ('us-east-1').

        Validates: Requirements Profile argument is non-authoritative in multi-tenant
            mode
        """
        token = set_credential_context(_make_context())
        try:
            resolver = RequestScopedCredentialResolver()
            with (
                patch.dict('os.environ', {}, clear=False) as _,
                patch.object(aws_utils.boto3, 'Session') as mock_session,
            ):
                import os

                os.environ.pop('AWS_REGION', None)
                resolver.resolve(CredentialRequest(region=None, profile=None))

            mock_session.assert_called_once()
            assert mock_session.call_args.kwargs['region_name'] == DEFAULT_REGION
        finally:
            reset_credential_context(token)
