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

"""Property tests for the pure-logic tenant-record builder.

This module lives outside ``integration/tests/`` (which is opt-in gated behind a
real-AWS signal) and outside the top-level ``tests/`` suite, so it runs as a
fully offline unit-style property test: it never constructs an AWS client,
resolves credentials, or opens a network connection.

Property: Tenant records are pairwise distinct and round-trip to the registry
item shape.

Validates: Requirements DynamoDB-backed multi-tenant registry.
"""

# Feature: remote-deployment-integration-tests, Property: Tenant records are pairwise distinct and round-trip to the registry item shape

import pytest
from dataclasses import replace
from hypothesis import given, settings
from hypothesis import strategies as st
from integration.harness.tenants import TenantRecord, TenantSpec, build_tenant_records


# Non-empty field text. The builder treats identity/role_arn/external_id as
# opaque provider-controlled strings, so any non-empty text exercises the
# contract; printable text keeps failing examples readable.
non_empty_text = st.text(min_size=1, max_size=16)

# Modes that force the fail-closed branch of ``build_tenant_records``. Each maps
# to a mutation of an otherwise-valid batch that must raise ``ValueError``.
_RAISING_MODES = (
    'too_few',
    'empty_identity',
    'empty_external_id',
    'duplicate_identity',
    'duplicate_role_arn',
    'duplicate_external_id',
)


@st.composite
def tenant_batches(draw: st.DrawFn) -> tuple[list[TenantSpec], str]:
    """Draw a batch of tenant specs tagged with its expected outcome.

    Returns a ``(specs, expectation)`` pair where ``expectation`` is ``'valid'``
    (the specs satisfy every invariant and should build cleanly and round-trip)
    or ``'raises'`` (the specs violate an invariant and should fail closed). The
    valid batches carry pairwise-distinct identity/role_arn/external_id values;
    the raising batches are valid batches mutated to collide or carry empties.
    """
    count = draw(st.integers(min_value=2, max_value=6))
    identities = draw(st.lists(non_empty_text, min_size=count, max_size=count, unique=True))
    role_arns = draw(st.lists(non_empty_text, min_size=count, max_size=count, unique=True))
    external_ids = draw(st.lists(non_empty_text, min_size=count, max_size=count, unique=True))
    account_ids = draw(
        st.lists(st.one_of(st.none(), non_empty_text), min_size=count, max_size=count)
    )
    enableds = draw(st.lists(st.booleans(), min_size=count, max_size=count))

    specs = [
        TenantSpec(
            identity=identity,
            role_arn=role_arn,
            external_id=external_id,
            account_id=account_id,
            enabled=enabled,
        )
        for identity, role_arn, external_id, account_id, enabled in zip(
            identities, role_arns, external_ids, account_ids, enableds
        )
    ]

    mode = draw(st.sampled_from(('valid',) + _RAISING_MODES))
    if mode == 'valid':
        return specs, 'valid'

    if mode == 'too_few':
        keep = draw(st.integers(min_value=0, max_value=1))
        return specs[:keep], 'raises'

    target = draw(st.integers(min_value=0, max_value=count - 1))
    if mode == 'empty_identity':
        specs[target] = replace(specs[target], identity='')
    elif mode == 'empty_external_id':
        specs[target] = replace(specs[target], external_id='')
    elif mode == 'duplicate_identity':
        specs[1] = replace(specs[1], identity=specs[0].identity)
    elif mode == 'duplicate_role_arn':
        specs[1] = replace(specs[1], role_arn=specs[0].role_arn)
    else:  # duplicate_external_id
        specs[1] = replace(specs[1], external_id=specs[0].external_id)

    return specs, 'raises'


def _assert_round_trips(spec: TenantSpec, record: TenantRecord) -> None:
    """Assert a record preserves its spec and renders the expected item shape."""
    # The record is a faithful, order-preserving copy of its source spec.
    assert record.identity == spec.identity
    assert record.role_arn == spec.role_arn
    assert record.external_id == spec.external_id
    assert record.account_id == spec.account_id
    assert record.enabled == spec.enabled

    item = record.to_registry_item()

    # Required fields plus always-present ``enabled``; ``account_id`` only when set.
    expected_keys = {'identity', 'role_arn', 'external_id', 'enabled'}
    if record.account_id is not None:
        expected_keys.add('account_id')
    assert set(item) == expected_keys

    assert item['identity'] == record.identity
    assert item['role_arn'] == record.role_arn
    assert item['external_id'] == record.external_id
    assert item['enabled'] == record.enabled
    if record.account_id is not None:
        assert item['account_id'] == record.account_id
    else:
        assert 'account_id' not in item


@settings(max_examples=200)
@given(batch=tenant_batches())
def test_tenant_records_distinct_and_round_trip(
    batch: tuple[list[TenantSpec], str],
) -> None:
    """Property: Tenant records are pairwise distinct and round-trip to the registry item shape.

    For any collection of two or more tenant specifications, ``build_tenant_records``
    produces records whose ``role_arn`` values are pairwise distinct and whose
    ``external_id`` values are non-empty and pairwise distinct (and whose
    ``identity`` partition keys are pairwise distinct), and each record
    round-trips through ``to_registry_item`` into the ``{identity, role_arn,
    external_id, account_id?, enabled?}`` shape; otherwise the builder fails
    closed with ``ValueError`` when fewer than two specs are given or any
    identity/role_arn/external_id collides or is empty.

    Validates: Requirements DynamoDB-backed multi-tenant registry.
    """
    specs, expectation = batch

    if expectation == 'raises':
        with pytest.raises(ValueError):
            build_tenant_records(specs)
        return

    records = build_tenant_records(specs)

    # Records preserve count and order of the input specs.
    assert len(records) == len(specs)

    identities = [record.identity for record in records]
    role_arns = [record.role_arn for record in records]
    external_ids = [record.external_id for record in records]

    # Pairwise-distinct partition keys and role ARNs.
    assert len(set(identities)) == len(identities)
    assert len(set(role_arns)) == len(role_arns)

    # External ids are non-empty and pairwise distinct.
    assert all(external_id for external_id in external_ids)
    assert len(set(external_ids)) == len(external_ids)

    # Every record round-trips into the registry item shape the resolver reads.
    for spec, record in zip(specs, records):
        _assert_round_trips(spec, record)
