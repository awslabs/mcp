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


"""Unit tests for the cross-tenant isolation comparison helper.

These tests are pure and offline: they exercise the identity-comparison logic in
``integration/harness/isolation.py`` without touching AWS or the network. They live
in ``integration/harness_tests/`` — separate from the opt-in-gated
``integration/tests/`` suite and from the offline ``tests/`` suite — and are not
gated by the Opt_In_Signal.

The core assertion covered here is that a mismatch carries BOTH the expected and
observed identities on the raised exception and in its message, so a failing
isolation test reports both identities.

Validates: Requirements Cross-tenant isolation verification.
"""

import pytest
from integration.harness.isolation import (
    IdentityComparison,
    TenantIdentityMismatch,
    assert_identity_matches,
    compare_identities,
    identities_match,
)


# Representative assumed-role identifiers standing in for two distinct Tenant_Roles.
_TENANT_A = 'arn:aws:sts::111111111111:assumed-role/Tenant_A_Role/session'
_TENANT_B = 'arn:aws:sts::222222222222:assumed-role/Tenant_B_Role/session'


class TestEqualIdentities:
    """Equal identities are reported as a match by every helper.

    Validates: Requirements Cross-tenant isolation verification.
    """

    def test_identities_match_returns_true(self) -> None:
        """``identities_match`` is True when the identifiers are exactly equal."""
        assert identities_match(_TENANT_A, _TENANT_A) is True

    def test_compare_identities_matches_and_carries_values(self) -> None:
        """``compare_identities`` reports a match and carries both identities."""
        result = compare_identities(_TENANT_A, _TENANT_A)

        assert isinstance(result, IdentityComparison)
        assert result.matches is True
        assert result.expected == _TENANT_A
        assert result.observed == _TENANT_A

    def test_assert_identity_matches_returns_comparison_without_raising(self) -> None:
        """``assert_identity_matches`` returns the comparison and does not raise."""
        result = assert_identity_matches(_TENANT_A, _TENANT_A)

        assert isinstance(result, IdentityComparison)
        assert result.matches is True
        assert result.expected == _TENANT_A
        assert result.observed == _TENANT_A


class TestUnequalIdentities:
    """Unequal identities produce a failure carrying expected and observed values.

    This is the core Req 6.3 assertion: a mismatch must report BOTH identities.

    Validates: Requirements Cross-tenant isolation verification.
    """

    def test_identities_match_returns_false(self) -> None:
        """``identities_match`` is False when the identifiers differ."""
        assert identities_match(_TENANT_A, _TENANT_B) is False

    def test_compare_identities_does_not_match_and_carries_values(self) -> None:
        """``compare_identities`` reports no match while carrying both identities."""
        result = compare_identities(_TENANT_A, _TENANT_B)

        assert result.matches is False
        assert result.expected == _TENANT_A
        assert result.observed == _TENANT_B

    def test_assert_identity_matches_raises_carrying_both_identities(self) -> None:
        """A mismatch raises ``TenantIdentityMismatch`` carrying both identities.

        Both the expected and observed identities must appear on the exception
        attributes and in ``str(exc)`` so a failing isolation test reports both.
        """
        with pytest.raises(TenantIdentityMismatch) as exc_info:
            assert_identity_matches(_TENANT_A, _TENANT_B)

        exc = exc_info.value
        # Carried on the exception attributes.
        assert exc.expected == _TENANT_A
        assert exc.observed == _TENANT_B
        # Embedded in the message so both identities are visible in the failure.
        message = str(exc)
        assert _TENANT_A in message
        assert _TENANT_B in message

    def test_mismatch_is_an_assertion_error(self) -> None:
        """``TenantIdentityMismatch`` is an ``AssertionError`` for pytest reporting."""
        assert issubclass(TenantIdentityMismatch, AssertionError)


class TestContextInMessage:
    """Optional context is included in the failure message when provided.

    Validates: Requirements Cross-tenant isolation verification.
    """

    def test_context_included_in_message_and_attribute(self) -> None:
        """Provided context appears on the exception and in its message."""
        context = 'Tenant_A tool call #1'
        with pytest.raises(TenantIdentityMismatch) as exc_info:
            assert_identity_matches(_TENANT_A, _TENANT_B, context=context)

        exc = exc_info.value
        assert exc.context == context
        message = str(exc)
        assert context in message
        # Both identities remain present alongside the context.
        assert _TENANT_A in message
        assert _TENANT_B in message

    def test_message_omits_context_prefix_when_absent(self) -> None:
        """Without context, the message still carries both identities."""
        with pytest.raises(TenantIdentityMismatch) as exc_info:
            assert_identity_matches(_TENANT_A, _TENANT_B)

        exc = exc_info.value
        assert exc.context is None
        message = str(exc)
        assert _TENANT_A in message
        assert _TENANT_B in message
