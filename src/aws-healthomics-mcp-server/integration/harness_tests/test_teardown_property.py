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

"""Property test for the teardown workflow's attempt-and-report contract.

This module lives outside ``integration/tests/`` (which is opt-in gated behind a real-AWS
signal) and outside the top-level ``tests/`` suite, so it runs as a fully offline unit-style
property test: it never constructs an AWS client, resolves credentials, or opens a network
connection. Teardown is exercised through its injected deleter seam only, with a fake deleter
that maps each inventoried resource to a canned outcome -- deleted, already-absent, or failure.

Property: Teardown attempts every resource and reports the exact undeleted set.

Validates: Requirements Provisioning and teardown lifecycle.
"""

# Feature: remote-deployment-integration-tests, Property: Teardown attempts every resource and reports the exact undeleted set

from hypothesis import given, settings
from hypothesis import strategies as st
from integration.deploy.common import ResourceNotFound, teardown
from integration.harness.inventory import ResourceInventory, ResourceRecord


# The three per-resource outcomes a deleter can drive: a clean delete, an already-absent
# resource (raises ResourceNotFound -> idempotent success), or a real failure (raises).
_OUTCOMES = ('deleted', 'absent', 'failure')


@st.composite
def inventories_with_outcomes(
    draw: st.DrawFn,
) -> tuple[ResourceInventory, list[str]]:
    """Draw an inventory paired with one delete outcome per record, aligned by index.

    Resource ids are intentionally allowed to collide so the test also covers inventories with
    duplicate ids; outcomes are therefore aligned positionally and consumed by object identity
    rather than by id string, which keeps the mapping unambiguous even with duplicates. The
    all-``'absent'`` case (idempotent teardown of an already-absent inventory) is reachable by
    Hypothesis and asserted to report success.
    """
    deployment = draw(st.sampled_from(['agentcore', 'apigateway']))
    region = draw(st.sampled_from(['us-east-1', 'us-west-2', 'eu-west-1']))
    count = draw(st.integers(min_value=0, max_value=8))
    records: list[ResourceRecord] = []
    outcomes: list[str] = []
    for _ in range(count):
        records.append(
            ResourceRecord(
                resource_id=draw(st.text(alphabet='ab', min_size=1, max_size=3)),
                resource_type=draw(st.sampled_from(['dynamodb-table', 'agentcore-runtime'])),
                region=region,
                deployment=deployment,
            )
        )
        outcomes.append(draw(st.sampled_from(_OUTCOMES)))
    inventory = ResourceInventory(deployment=deployment, region=region, records=records)
    return inventory, outcomes


@settings(max_examples=200)
@given(inventory_and_outcomes=inventories_with_outcomes())
def test_teardown_attempts_every_resource_and_reports_exact_undeleted_set(
    inventory_and_outcomes: tuple[ResourceInventory, list[str]],
) -> None:
    """Property: Teardown attempts every resource and reports the exact undeleted set.

    For any recorded inventory and any assignment of per-resource delete outcomes, teardown
    attempts a delete for every inventoried resource exactly once in recorded order, treats an
    already-absent resource (``ResourceNotFound``) as deleted, reports success iff no resource
    remains undeleted, and -- when it reports failure -- names exactly the resources whose
    deletion failed, in inventory order. Tearing down an inventory whose resources are all
    already absent therefore reports success (idempotence).

    Validates: Requirements Provisioning and teardown lifecycle.
    """
    inventory, outcomes = inventory_and_outcomes

    # Map each record to its outcome by object identity so duplicate resource ids stay
    # unambiguous, and record every record the deleter was invoked with (in call order).
    outcome_by_identity = {
        id(record): outcome for record, outcome in zip(inventory.records, outcomes)
    }
    attempted: list[ResourceRecord] = []

    def fake_deleter(record: ResourceRecord, /) -> None:
        attempted.append(record)
        outcome = outcome_by_identity[id(record)]
        if outcome == 'deleted':
            return None
        if outcome == 'absent':
            raise ResourceNotFound('already absent')
        raise RuntimeError('injected deletion failure')

    result = teardown(inventory=inventory, deleter=fake_deleter)

    # Every inventoried resource was attempted exactly once, in recorded order.
    assert attempted == list(inventory.records)

    # The undeleted set is exactly the records whose outcome was 'failure', in inventory order.
    expected_undeleted = tuple(
        record for record, outcome in zip(inventory.records, outcomes) if outcome == 'failure'
    )
    assert result.undeleted == expected_undeleted

    # Success iff nothing remained undeleted (covers all-absent idempotent success).
    assert result.succeeded == (len(expected_undeleted) == 0)
