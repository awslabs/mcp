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


"""Cross-tenant isolation comparison helpers for the integration harness.

The isolation integration tests (``integration/tests/test_cross_tenant_isolation.py``)
invoke an identity-revealing tool (``WhoAmI``) through a provisioned deployment and
must confirm that each tool call ran under the *expected* ``Tenant_Role`` and never
under another tenant's role. The signal they compare is the assumed-role identifier
reported by the tool against the identifier of the Tenant_Role the calling tenant maps
to in the DynamoDB role registry.

This module provides the pure-logic comparison used by those tests:

- :func:`identities_match` — a boolean predicate for an exact identity match.
- :func:`compare_identities` — a comparison that returns an :class:`IdentityComparison`
  result carrying both the expected and observed identities.
- :func:`assert_identity_matches` — an assert-style helper that raises
  :class:`TenantIdentityMismatch` (an ``AssertionError``) on mismatch, carrying both
  identities on the exception so a failing test reports the expected and observed
  identities (Req 6.3).

The comparison is an *exact* equality check on the identity strings. Keeping the
predicate, the result type, and the assert-style helper separate makes the logic
directly unit-testable offline without touching AWS (see task 5.6).
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class IdentityComparison:
    """The outcome of comparing an observed identity against an expected one.

    Attributes:
        expected: The identifier of the Tenant_Role the calling tenant is expected
            to act under (for example the role ARN or the assumed-role ARN derived
            from it).
        observed: The assumed-role identifier reported by the identity-revealing
            tool for the tool call under verification.
        matches: ``True`` iff ``observed`` is exactly equal to ``expected``.
    """

    expected: str
    observed: str
    matches: bool


class TenantIdentityMismatch(AssertionError):
    """Raised when an observed identity is not exactly the expected Tenant_Role.

    Subclasses ``AssertionError`` so it integrates with pytest's assertion
    reporting while still being catchable as a dedicated type. Both the expected
    and observed identities are carried as attributes and embedded in the message
    so a failing isolation test reports both identities (Req 6.3).

    Attributes:
        expected: The expected Tenant_Role identifier.
        observed: The observed assumed-role identifier that did not match.
        context: Optional human-readable context (for example which tenant or tool
            call the comparison was for) included in the message when present.
    """

    def __init__(self, expected: str, observed: str, context: str | None = None) -> None:
        """Build the mismatch error, carrying the expected and observed identities."""
        self.expected = expected
        self.observed = observed
        self.context = context
        prefix = f'{context}: ' if context else ''
        super().__init__(
            f'{prefix}assumed-role identity mismatch: '
            f'expected {expected!r} but observed {observed!r}'
        )


def identities_match(expected: str, observed: str) -> bool:
    """Return ``True`` iff ``observed`` is exactly equal to ``expected``.

    The check is an exact string equality with no normalization, so any
    difference (case, whitespace, partition, account, or role path) is treated as
    a mismatch, matching the strict isolation guarantee the tests assert.

    Args:
        expected: The expected Tenant_Role identifier.
        observed: The observed assumed-role identifier.

    Returns:
        ``True`` when the two identifiers are exactly equal.
    """
    return expected == observed


def compare_identities(expected: str, observed: str) -> IdentityComparison:
    """Compare ``observed`` against ``expected`` and return the result.

    Args:
        expected: The expected Tenant_Role identifier.
        observed: The observed assumed-role identifier.

    Returns:
        An :class:`IdentityComparison` carrying both identities and whether they
        match exactly.
    """
    return IdentityComparison(
        expected=expected,
        observed=observed,
        matches=identities_match(expected, observed),
    )


def assert_identity_matches(
    expected: str, observed: str, context: str | None = None
) -> IdentityComparison:
    """Assert that ``observed`` is exactly the expected Tenant_Role identifier.

    On a match, returns the :class:`IdentityComparison` result so callers can chain
    or record it. On a mismatch, raises :class:`TenantIdentityMismatch` (an
    ``AssertionError``) carrying both the expected and observed identities so the
    failing isolation test reports both (Req 6.3).

    Args:
        expected: The expected Tenant_Role identifier.
        observed: The observed assumed-role identifier reported by the
            identity-revealing tool.
        context: Optional context (for example the tenant name or tool call index)
            included in the failure message.

    Returns:
        The :class:`IdentityComparison` result when the identities match.

    Raises:
        TenantIdentityMismatch: When ``observed`` is not exactly equal to
            ``expected``.
    """
    result = compare_identities(expected, observed)
    if not result.matches:
        raise TenantIdentityMismatch(expected, observed, context)
    return result
