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

"""Fail-closed property tests for ``RegistryRoleResolver``.

Property-based tests for ``RegistryRoleResolver.resolve`` in
``mechanisms/role_resolver.py``. This module is dedicated to Property "Fail
closed on resolution or STS failure": whenever a role target cannot be
authoritatively resolved from the provider-controlled registry -- because no
record is mapped to the identity, the record is disabled, the record is
incomplete, or the source itself cannot be read -- ``resolve`` fails closed by
raising ``CredentialDerivationError`` and returns no ``RoleTarget``.

An in-memory stub ``RegistrySource`` stands in for the file/DynamoDB backends so
no real AWS or filesystem access happens. The Hypothesis conventions
(strategies, ``@given``/``@settings`` usage, inclusive parameter names) mirror
those established in ``tests/test_partition_cache_isolation.py``.
"""

from awslabs.aws_healthomics_mcp_server.mechanisms.role_resolver import (
    RegistryRoleResolver,
    RegistrySourceError,
    RoleTarget,
)
from awslabs.aws_healthomics_mcp_server.utils.aws_utils import (
    CredentialDerivationError,
)
from hypothesis import given, settings
from hypothesis import strategies as st
from typing import cast


# Sentinel marking a registry key that should be omitted entirely from a record,
# distinct from an explicit ``None`` value (which is itself an invalid shape).
_ABSENT = object()

# Printable, non-space ASCII keeps generated identities and ARNs readable while
# still exercising the resolver, which treats them as opaque strings.
_printable = st.characters(min_codepoint=0x21, max_codepoint=0x7E)

# Authenticated-identity values placed under the default ``sub`` caller claim.
identity_strategy = st.text(alphabet=_printable, min_size=1, max_size=32)

# A well-formed, non-empty role ARN / ExternalId string. Any non-empty text
# satisfies the resolver's shape checks, so these stand in for otherwise-valid
# fields when a *different* field is what makes the record fail closed.
valid_string = st.text(alphabet=_printable, min_size=1, max_size=64)

# ``enabled`` indicator values that are present but falsy, which must deny access.
falsy_enabled = st.sampled_from([False, 0, '', None, [], {}])

# ``enabled`` indicator values that are present and truthy (access not denied by
# the ``enabled`` gate, so a later missing/invalid field is what fails closed).
truthy_enabled = st.sampled_from([True, 1, 'true', 'yes', 42])

# Values that are NOT a non-empty string, so they fail the resolver's
# ``isinstance(x, str) and x`` field validation for ``role_arn`` / ``external_id``.
invalid_string_values = st.one_of(
    st.just(''),
    st.none(),
    st.integers(),
    st.booleans(),
    st.lists(st.integers(), max_size=2),
    st.dictionaries(st.text(max_size=3), st.integers(), max_size=2),
)

# An ExternalId string longer than the STS maximum (1224 characters), which must
# be rejected even though it is a non-empty string.
too_long_external_id = st.text(alphabet=_printable, min_size=1225, max_size=1300)

# Arbitrary extra claims carried alongside ``sub``. These must never rescue a
# fail-closed resolution, so they are generated freely (including a competing
# ``role_arn`` claim) to prove they are ignored.
extra_claims = st.dictionaries(
    st.text(min_size=1, max_size=8).filter(lambda key: key != 'sub'),
    st.one_of(st.text(max_size=32), st.integers(), st.booleans(), st.none()),
    max_size=4,
)


class _StubRegistrySource:
    """In-memory ``RegistrySource`` stub used to drive fail-closed scenarios.

    Either returns a preconfigured record (or ``None`` for "no record mapped") or
    raises a ``RegistrySourceError`` to model a source read/query failure. No real
    AWS or filesystem access occurs.
    """

    def __init__(self, record=_ABSENT, error=None):
        """Configure the stub to return ``record`` or raise ``error``.

        Args:
            record: The record to return from ``get_record``. ``None`` models "no
                record mapped to the identity"; the ``_ABSENT`` sentinel also maps
                to ``None`` for convenience.
            error: When set, ``get_record`` raises this exception instead of
                returning, modeling a source read/query failure.
        """
        self._record = record
        self._error = error

    def get_record(self, identity: str) -> dict | None:
        """Return the configured record or raise the configured source error."""
        if self._error is not None:
            raise self._error
        if self._record is _ABSENT:
            return None
        return cast('dict | None', self._record)


# A source with no record mapped to the identity (``get_record`` returns ``None``).
_no_record_sources = st.builds(_StubRegistrySource, record=st.none())


@st.composite
def _disabled_record_sources(draw):
    """A record whose ``enabled`` indicator is present and falsy (denied)."""
    record = {'enabled': draw(falsy_enabled)}
    # Otherwise-valid fields may be present; the disabled gate must still deny.
    if draw(st.booleans()):
        record['role_arn'] = draw(valid_string)
    if draw(st.booleans()):
        record['external_id'] = draw(valid_string)
    return _StubRegistrySource(record=record)


@st.composite
def _missing_role_arn_sources(draw):
    """An enabled record whose ``role_arn`` is absent or not a non-empty string."""
    record: dict = {}
    if draw(st.booleans()):
        record['enabled'] = draw(truthy_enabled)
    role_arn = draw(st.one_of(st.just(_ABSENT), invalid_string_values))
    if role_arn is not _ABSENT:
        record['role_arn'] = role_arn
    # A valid ExternalId may be present; the missing role ARN must still deny.
    if draw(st.booleans()):
        record['external_id'] = draw(valid_string)
    return _StubRegistrySource(record=record)


@st.composite
def _missing_external_id_sources(draw):
    """An enabled record with a valid ``role_arn`` but an invalid ``external_id``."""
    record: dict = {'role_arn': draw(valid_string)}
    if draw(st.booleans()):
        record['enabled'] = draw(truthy_enabled)
    external_id = draw(st.one_of(st.just(_ABSENT), invalid_string_values))
    if external_id is not _ABSENT:
        record['external_id'] = external_id
    return _StubRegistrySource(record=record)


@st.composite
def _too_long_external_id_sources(draw):
    """An enabled record with a valid ``role_arn`` but an over-length ``external_id``."""
    record: dict = {
        'role_arn': draw(valid_string),
        'external_id': draw(too_long_external_id),
    }
    if draw(st.booleans()):
        record['enabled'] = draw(truthy_enabled)
    return _StubRegistrySource(record=record)


@st.composite
def _source_read_failure_sources(draw):
    """A source that raises ``RegistrySourceError`` on lookup (read/query failure)."""
    message = draw(st.text(max_size=32))
    return _StubRegistrySource(error=RegistrySourceError(message))


# Union of every scenario that MUST cause the resolver to fail closed: no record,
# a disabled record, an incomplete/invalid record, an over-length ExternalId, and
# a source read/query failure.
fail_closed_sources = st.one_of(
    _no_record_sources,
    _disabled_record_sources(),
    _missing_role_arn_sources(),
    _missing_external_id_sources(),
    _too_long_external_id_sources(),
    _source_read_failure_sources(),
)


class TestRegistryRoleResolverFailClosed:
    """Property: Fail closed on resolution or STS failure.

    Validates: Requirements Fail Closed On Failure.
    """

    @given(
        identity=identity_strategy,
        source=fail_closed_sources,
        other_claims=extra_claims,
    )
    @settings(max_examples=300)
    def test_unresolvable_record_fails_closed(self, identity, source, other_claims):
        """Property: Fail closed on resolution or STS failure.

        For any authenticated identity whose registry lookup yields no record, a
        disabled record, an incomplete or invalid record, or a source read/query
        failure, ``RegistryRoleResolver.resolve`` raises
        ``CredentialDerivationError`` and returns no ``RoleTarget``. Arbitrary
        extra claims present in the token never rescue the resolution, so the
        resolver never falls back to unintended credentials.

        Validates: Requirements Fail Closed On Failure.
        """
        resolver = RegistryRoleResolver(source)
        claims = {**other_claims, 'sub': identity}

        result = None
        try:
            result = resolver.resolve(claims)
        except CredentialDerivationError:
            # Failing closed with this exception is the required behavior.
            pass
        else:  # pragma: no cover - only reached if the resolver fails to fail closed
            raise AssertionError(
                f'resolve returned a target instead of failing closed: {type(result).__name__}'
            )

        # No RoleTarget escaped the fail-closed path.
        assert not isinstance(result, RoleTarget)
        assert result is None

    @given(
        source=fail_closed_sources,
        other_claims=extra_claims,
    )
    @settings(max_examples=200)
    def test_missing_caller_identity_fails_closed(self, source, other_claims):
        """Property: Fail closed on resolution or STS failure (no caller identity).

        When the decoded claims carry no usable ``sub`` caller identity, the
        resolver fails closed with ``CredentialDerivationError`` before it can
        derive any credentials, regardless of what the source would have returned.

        Validates: Requirements Fail Closed On Failure.
        """
        resolver = RegistryRoleResolver(source)
        # Ensure no usable caller identity is present under the default claim.
        claims = {key: value for key, value in other_claims.items() if key != 'sub'}

        result = None
        try:
            result = resolver.resolve(claims)
        except CredentialDerivationError:
            pass
        else:  # pragma: no cover - only reached if the resolver fails to fail closed
            raise AssertionError('resolve returned a target for a missing caller identity')

        assert not isinstance(result, RoleTarget)
        assert result is None
