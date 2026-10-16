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

"""Property test for failed-provisioning inventory capture.

This module lives outside ``integration/tests/`` (which is opt-in gated behind a real-AWS
signal) and outside the top-level ``tests/`` suite, so it runs as a fully offline unit-style
property test: it never constructs an AWS client, resolves credentials, or opens a network
connection. The provisioning FSM is exercised through its injected creator and clock seams
only, with a fake creator returning canned identifiers and a fake clock that never advances.

Property: A failed provisioning run still inventories every resource it created.

Validates: Requirements Provisioning and teardown lifecycle.
"""

# Feature: remote-deployment-integration-tests, Property: A failed provisioning run still inventories every resource it created

import tempfile
from dataclasses import dataclass
from hypothesis import given, settings
from hypothesis import strategies as st
from integration.deploy.common import (
    CreatedResource,
    ProvisionStage,
    ProvisionStatus,
    StageContext,
    provision,
)
from integration.harness.inventory import ResourceInventory
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class _StagePlan:
    """A generated provisioning plan with a failure injected at ``fail_index``.

    Attributes:
        stage_counts: The number of resources each stage attempts to create, in order.
        fail_index: The index of the stage that raises after creating its resources; every
            stage before it succeeds and returns no endpoint, and every stage after it is
            never reached.
    """

    stage_counts: tuple[int, ...]
    fail_index: int


@st.composite
def stage_plans(draw: st.DrawFn) -> _StagePlan:
    """Draw a provisioning plan whose failing stage is at an arbitrary position.

    Stages before the failing stage each create at least one resource and return no endpoint,
    so provisioning keeps walking. The failing stage creates zero-or-more resources and then
    raises, so the inventory must contain exactly the resources created up to and including
    that stage's pre-raise creations. Stages after the failing stage are never executed.
    """
    num_stages = draw(st.integers(min_value=1, max_value=6))
    fail_index = draw(st.integers(min_value=0, max_value=num_stages - 1))
    stage_counts: list[int] = []
    for index in range(num_stages):
        # The failing stage may create zero resources before raising; every other stage
        # creates at least one so successful creations accumulate in the inventory.
        low = 0 if index == fail_index else 1
        stage_counts.append(draw(st.integers(min_value=low, max_value=3)))
    return _StagePlan(stage_counts=tuple(stage_counts), fail_index=fail_index)


def _make_stage(name: str, tags: list[str], raises: bool) -> ProvisionStage:
    """Build a stage that creates one resource per tag, then optionally raises.

    Each ``ctx.create`` call forwards its tag to the fake creator, which echoes it back as the
    resource id, so the created resource identities are fully deterministic from the plan.
    """

    def run(ctx: StageContext) -> None:
        for tag in tags:
            ctx.create(f'type-{tag}', tag=tag)
        if raises:
            raise RuntimeError('injected stage failure')
        # A non-failing stage emits no endpoint so provisioning continues to the next stage.
        return None

    return ProvisionStage(name=name, run=run)


def _fake_creator(resource_type: str, /, **params: Any) -> CreatedResource:
    """Return a deterministic resource whose id is the tag supplied by the stage."""
    return CreatedResource(resource_id=params['tag'], resource_type=resource_type)


@settings(max_examples=200)
@given(plan=stage_plans())
def test_failed_provisioning_inventories_every_created_resource(plan: _StagePlan) -> None:
    """Property: A failed provisioning run still inventories every resource it created.

    For any provisioning sequence with a failure injected at an arbitrary stage, the persisted
    inventory contains exactly the resources created up to and including the last successful
    creation -- the resources of every stage before the failing one plus any the failing stage
    created before it raised -- in creation order. This lets an operator tear down everything
    that was created even when provisioning fails mid-flight. The result reports FAILED and
    names the stage that raised.

    Validates: Requirements Provisioning and teardown lifecycle.
    """
    stages: list[ProvisionStage] = []
    expected_tags: list[str] = []
    next_tag = 0
    for index, count in enumerate(plan.stage_counts):
        tags = [f'r{next_tag + offset}' for offset in range(count)]
        next_tag += count
        raises = index == plan.fail_index
        stages.append(_make_stage(f'stage-{index}', tags, raises=raises))
        # Only stages up to and including the failing one actually run; the failing stage
        # creates all its resources before raising, so they are inventoried too.
        if index < plan.fail_index:
            expected_tags.extend(tags)
        elif index == plan.fail_index:
            expected_tags.extend(tags)

    with tempfile.TemporaryDirectory() as tmp_dir:
        inventory_path = Path(tmp_dir) / 'inventory.json'
        result = provision(
            deployment='agentcore',
            region='us-east-1',
            stages=stages,
            creator=_fake_creator,
            inventory_path=inventory_path,
            # A fake clock that never advances keeps the run within budget, so the only cause
            # of failure is the injected raise rather than a timeout.
            clock=lambda: 0.0,
        )

        # The run failed at the injected stage, and the inventory was still persisted.
        assert result.status == ProvisionStatus.FAILED
        assert result.failed_stage == f'stage-{plan.fail_index}'

        loaded = ResourceInventory.load(result.inventory_path)

    # The inventory holds exactly the resources created before the raise, in creation order.
    assert [record.resource_id for record in loaded.records] == expected_tags
    assert [record.resource_type for record in loaded.records] == [
        f'type-{tag}' for tag in expected_tags
    ]
