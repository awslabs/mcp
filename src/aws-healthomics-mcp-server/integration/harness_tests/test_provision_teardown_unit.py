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

"""Example-based unit tests for provisioning/teardown derivation.

These tests are pure and offline: they exercise the provisioning FSM and teardown workflow in
``integration/deploy/common.py`` through their injected creator/clock/deleter seams only,
never constructing an AWS client, resolving credentials, or opening a network connection. They
live in ``integration/harness_tests/`` -- separate from the opt-in-gated ``integration/tests/``
suite and from the offline top-level ``tests/`` suite -- and are not gated by the Opt_In_Signal.

Where the property tests cover universal behaviour across many inputs, these examples pin the
specific derivations called out by the lifecycle requirements: an emitted endpoint yields
COMPLETE, a spent budget yields FAILED with timeout detail, a raising stage yields FAILED
naming the stage and cause, the target region is threaded into every created-resource record,
and teardown reports success when every resource is deleted.

Validates: Requirements Provisioning and teardown lifecycle.
"""

from integration.deploy.common import (
    CreatedResource,
    ProvisionStage,
    ProvisionStatus,
    ResourceNotFound,
    StageContext,
    teardown,
)
from integration.deploy.common import provision as run_provision
from integration.harness.inventory import ResourceInventory, ResourceRecord
from pathlib import Path
from typing import Any


def _canned_creator(resource_type: str, /, **params: Any) -> CreatedResource:
    """Return a deterministic resource whose id echoes the ``tag`` the stage supplied."""
    return CreatedResource(resource_id=params['tag'], resource_type=resource_type)


class _SteppingClock:
    """A fake monotonic clock returning a scripted sequence of increasing values.

    Each call pops the next value; the final value repeats once the script is exhausted so the
    FSM can call the clock as many times as it needs without running off the end.
    """

    def __init__(self, values: list[float]) -> None:
        self._values = list(values)
        self._index = 0

    def __call__(self) -> float:
        value = self._values[min(self._index, len(self._values) - 1)]
        self._index += 1
        return value


class TestEndpointEmittedCompletes:
    """A stage that emits an endpoint within budget yields COMPLETE.

    Validates: Requirements Provisioning and teardown lifecycle.
    """

    def test_endpoint_emitted_reports_complete(self, tmp_path: Path) -> None:
        """The emitted endpoint is carried on a COMPLETE result with no failure fields."""
        endpoint = 'https://example.test/mcp'

        def emit(ctx: StageContext) -> str:
            ctx.create('agentcore-runtime', tag='runtime-1')
            return endpoint

        result = run_provision(
            deployment='agentcore',
            region='us-east-1',
            stages=[ProvisionStage(name='deploy-runtime', run=emit)],
            creator=_canned_creator,
            inventory_path=tmp_path / 'inventory.json',
            # A clock that never advances keeps the run comfortably within budget.
            clock=lambda: 0.0,
        )

        assert result.status == ProvisionStatus.COMPLETE
        assert result.endpoint == endpoint
        assert result.failed_stage is None
        assert result.detail is None


class TestBudgetExceededFails:
    """A run whose budget is spent before the endpoint is emitted yields FAILED.

    Validates: Requirements Provisioning and teardown lifecycle.
    """

    def test_timeout_reports_failed_with_budget_detail(self, tmp_path: Path) -> None:
        """A fake clock jumping past the budget trips the pre-stage timeout check.

        The clock returns ``0`` at start, then a value beyond the budget on the next reading,
        so the first stage runs (emitting no endpoint) and the pre-stage budget check on the
        second stage trips. The result is FAILED with detail naming the budget/timeout.
        """

        def make_resource(ctx: StageContext) -> None:
            ctx.create('dynamodb-table', tag='table-1')
            return None

        stages = [
            ProvisionStage(name='create-table', run=make_resource),
            ProvisionStage(name='deploy-runtime', run=make_resource),
        ]
        # start=0, first pre-stage check=0 (within budget), second pre-stage check=1000
        # (beyond the 900s budget) so the second stage's pre-check trips.
        clock = _SteppingClock([0.0, 0.0, 1000.0])

        result = run_provision(
            deployment='agentcore',
            region='us-east-1',
            stages=stages,
            creator=_canned_creator,
            inventory_path=tmp_path / 'inventory.json',
            clock=clock,
            budget_seconds=900.0,
        )

        assert result.status == ProvisionStatus.FAILED
        assert result.endpoint is None
        assert result.detail is not None
        # The detail names the budget and the timeout condition in human-readable form.
        assert '900' in result.detail
        assert 'budget' in result.detail


class TestStageErrorFails:
    """A stage that raises yields FAILED naming that stage and a human-readable cause.

    Validates: Requirements Provisioning and teardown lifecycle.
    """

    def test_stage_error_reports_failed_stage_and_detail(self, tmp_path: Path) -> None:
        """A raising stage surfaces its name in ``failed_stage`` and its cause in ``detail``."""

        def boom(ctx: StageContext) -> None:
            raise RuntimeError('boom')

        stages = [
            ProvisionStage(name='create-table', run=lambda ctx: None),
            ProvisionStage(name='deploy-runtime', run=boom),
        ]

        result = run_provision(
            deployment='apigateway',
            region='us-west-2',
            stages=stages,
            creator=_canned_creator,
            inventory_path=tmp_path / 'inventory.json',
            # Within-budget clock so the only cause of failure is the raise.
            clock=lambda: 0.0,
        )

        assert result.status == ProvisionStatus.FAILED
        assert result.endpoint is None
        assert result.failed_stage == 'deploy-runtime'
        assert result.detail is not None
        # The detail is human-readable and carries both the stage name and the raised cause.
        assert 'deploy-runtime' in result.detail
        assert 'boom' in result.detail


class TestRegionThreadedIntoRecords:
    """Every created-resource record carries the region passed to provision.

    Validates: Requirements Provisioning and teardown lifecycle.
    """

    def test_created_records_carry_provision_region(self, tmp_path: Path) -> None:
        """After a successful provision, every persisted record's region matches the input."""
        region = 'eu-central-1'

        def create_several(ctx: StageContext) -> str:
            ctx.create('dynamodb-table', tag='table-1')
            ctx.create('agentcore-runtime', tag='runtime-1')
            return 'https://example.test/mcp'

        result = run_provision(
            deployment='agentcore',
            region=region,
            stages=[ProvisionStage(name='deploy', run=create_several)],
            creator=_canned_creator,
            inventory_path=tmp_path / 'inventory.json',
            clock=lambda: 0.0,
        )

        assert result.status == ProvisionStatus.COMPLETE

        loaded = ResourceInventory.load(result.inventory_path)
        assert loaded.records  # sanity: resources were actually recorded
        assert all(record.region == region for record in loaded.records)


class TestTeardownSuccessAllDeleted:
    """Teardown reports success when every recorded resource is deleted.

    Validates: Requirements Provisioning and teardown lifecycle.
    """

    def test_all_deleted_reports_success_with_empty_undeleted(self) -> None:
        """A deleter returning ``None`` for all records yields success and no undeleted set.

        The deleter reports each resource as deleted regardless of whether a deletion report is
        emitted; teardown reports success and names no undeleted resource.
        """
        inventory = ResourceInventory(deployment='agentcore', region='us-east-1')
        for index in range(3):
            inventory.add(
                ResourceRecord(
                    resource_id=f'resource-{index}',
                    resource_type='dynamodb-table',
                    region='us-east-1',
                    deployment='agentcore',
                )
            )

        deleted: list[str] = []

        def deleter(record: ResourceRecord, /) -> None:
            deleted.append(record.resource_id)
            return None

        result = teardown(inventory=inventory, deleter=deleter)

        assert result.succeeded is True
        assert result.undeleted == ()
        # Every recorded resource was attempted exactly once, in inventory order.
        assert deleted == ['resource-0', 'resource-1', 'resource-2']

    def test_already_absent_is_treated_as_deleted(self) -> None:
        """A deleter raising ``ResourceNotFound`` is an idempotent success, not a failure."""
        inventory = ResourceInventory(deployment='apigateway', region='us-east-1')
        inventory.add(
            ResourceRecord(
                resource_id='gone-already',
                resource_type='apigateway-restapi',
                region='us-east-1',
                deployment='apigateway',
            )
        )

        def deleter(record: ResourceRecord, /) -> None:
            raise ResourceNotFound(record.resource_id)

        result = teardown(inventory=inventory, deleter=deleter)

        assert result.succeeded is True
        assert result.undeleted == ()
