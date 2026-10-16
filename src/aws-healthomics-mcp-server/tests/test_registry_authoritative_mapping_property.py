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

"""Property-based test for authoritative registry role mapping.

This module is dedicated to Property: Authoritative role mapping, exercised
against ``RegistryRoleResolver`` in ``mechanisms/role_resolver.py``. It proves
that the resolved role is always the one the provider-controlled registry mapped
to the request's authenticated identity, and that no other claim in the token
(including a decoy ``role_arn`` claim) can select the target.

The sibling registry properties live in separate modules to avoid file
conflicts: the fail-closed property lives in
``tests/test_registry_fail_closed_property.py`` and the example-based resolver
tests live in ``tests/test_registry_role_resolver.py``.
"""

from awslabs.aws_healthomics_mcp_server.mechanisms.role_resolver import (
    RegistryRoleResolver,
    RoleTarget,
)
from hypothesis import given, settings
from hypothesis import strategies as st


class StubRegistrySource:
    """In-memory ``RegistrySource`` backed by a dict of identity->record pairs.

    Records are provider-controlled and returned verbatim. Every record supplied
    to this stub is valid and enabled, so ``RegistryRoleResolver.resolve`` always
    reaches a successful resolution and any deviation in the resolved target is
    observable.
    """

    def __init__(self, records_by_identity: dict[str, dict]) -> None:
        """Store the provider-controlled records keyed on the identity."""
        self._records_by_identity = records_by_identity

    def get_record(self, identity: str) -> dict | None:
        """Return the record mapped to ``identity``, or ``None`` if absent."""
        return self._records_by_identity.get(identity)


# Distinct identity strings used as registry keys. Printable, non-space ASCII
# keeps them readable; ``unique=True`` guarantees each record is keyed on a
# distinct identity so cross-identity mis-resolution is observable.
identity_strategy = st.text(
    alphabet=st.characters(min_codepoint=0x21, max_codepoint=0x7E),
    min_size=1,
    max_size=12,
)

# Distinct role ARN / ExternalId component values. Kept simple and non-empty so
# each generated record is valid (per the resolver's fail-closed rules) and
# distinguishable from every other record's values.
value_strategy = st.text(
    alphabet=st.characters(min_codepoint=0x21, max_codepoint=0x7E),
    min_size=1,
    max_size=20,
)


@st.composite
def registries_with_decoys(draw):
    """Generate a registry of distinct identity->record pairs plus decoy values.

    Returns ``(records_by_identity, decoy_role_arn, decoy_external_id)`` where the
    mapping has at least two distinct identities, each with a distinct, valid
    ``role_arn`` and ``external_id``. Distinctness across records is what makes an
    authoritative mapping violation observable: any identity receiving another
    identity's target would surface as a mismatch.

    The two decoy values are drawn from the same unique pool as the record values,
    so they are guaranteed distinct from every record's ``role_arn`` and
    ``external_id``. This makes the "decoy never selects the target" assertion
    sound: a match against a decoy can only mean the resolver used the claim, never
    a coincidental value collision.
    """
    identities = draw(st.lists(identity_strategy, min_size=2, max_size=6, unique=True))
    # Draw enough distinct values to give every record a unique role_arn and a
    # unique external_id (2 per identity), plus two decoy values, so nothing
    # collides across records or with the decoys.
    values = draw(
        st.lists(
            value_strategy,
            min_size=2 * len(identities) + 2,
            max_size=2 * len(identities) + 2,
            unique=True,
        )
    )
    records_by_identity: dict[str, dict] = {}
    for index, identity in enumerate(identities):
        records_by_identity[identity] = {
            'role_arn': values[2 * index],
            'external_id': values[2 * index + 1],
            'enabled': True,
        }
    decoy_role_arn = values[-2]
    decoy_external_id = values[-1]
    return records_by_identity, decoy_role_arn, decoy_external_id


# Arbitrary extra claim keys that must never influence resolution. ``role_arn``
# and ``external_id`` are deliberately included below as decoys; the caller claim
# (``sub``) is excluded here so it is only ever set to the chosen identity.
extra_claim_key_strategy = st.text(
    alphabet=st.characters(min_codepoint=0x21, max_codepoint=0x7E),
    min_size=1,
    max_size=12,
).filter(lambda key: key != 'sub')


class TestAuthoritativeRoleMapping:
    """Property: Authoritative role mapping.

    Validates: Requirements Authoritative Identity To Role Mapping.
    """

    @given(
        registry_and_decoys=registries_with_decoys(),
        chooser=st.randoms(use_true_random=True),
        extra_claims=st.dictionaries(
            keys=extra_claim_key_strategy,
            values=value_strategy,
            max_size=5,
        ),
    )
    @settings(max_examples=200)
    def test_resolve_returns_the_identitys_own_mapped_record(
        self,
        registry_and_decoys,
        chooser,
        extra_claims,
    ):
        """Property: Authoritative role mapping.

        For a registry populated with distinct identity->record pairs,
        ``resolve(claims)`` returns exactly the record mapped to the caller
        identity's claim (``sub`` by default) and never another identity's record,
        regardless of any extra claims present in the token -- including a decoy
        ``role_arn``/``external_id`` claim. This proves the identity-to-role
        mapping is authoritative and that no token claim other than the caller
        identity can select the target.

        Validates: Requirements Authoritative Identity To Role Mapping.
        """
        records_by_identity, decoy_role_arn, decoy_external_id = registry_and_decoys
        resolver = RegistryRoleResolver(StubRegistrySource(records_by_identity))

        identities = list(records_by_identity)
        chosen_identity = identities[chooser.randrange(len(identities))]
        expected_record = records_by_identity[chosen_identity]

        # Build claims: the caller claim identifies the chosen identity, plus
        # arbitrary extra claims and decoy role_arn/external_id claims that must be
        # ignored by an authoritative mapping.
        claims = dict(extra_claims)
        claims['role_arn'] = decoy_role_arn
        claims['external_id'] = decoy_external_id
        claims['sub'] = chosen_identity

        target = resolver.resolve(claims)

        # The resolved target is exactly the chosen identity's own mapped record.
        assert target == RoleTarget(
            role_arn=expected_record['role_arn'],
            external_id=expected_record['external_id'],
        )

        # And never any other identity's record: the resolved values belong only
        # to the chosen identity, so no decoy claim or other record selected it.
        for identity, record in records_by_identity.items():
            if identity == chosen_identity:
                continue
            assert target.role_arn != record['role_arn']
            assert target.external_id != record['external_id']

        # The decoy claims never leak into the resolved target.
        assert target.role_arn != decoy_role_arn
        assert target.external_id != decoy_external_id
