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

"""Provisioning state machine for the integration harness deployments.

This module holds the deployment-agnostic provisioning FSM. For a selected deployment it
walks an ordered list of named :class:`ProvisionStage` steps, creates the AWS resources each
stage defines through an injected :class:`ResourceCreator` seam, and records every created
resource into a :class:`~integration.harness.inventory.ResourceInventory` at the moment of
creation so a mid-flight failure still leaves a complete-enough inventory for teardown
(Req 8.3). It reports :class:`ProvisionStatus.COMPLETE` as soon as a stage emits the
deployment's endpoint reference (Req 2.5, 3.7), and :class:`ProvisionStatus.FAILED` -- with
the failed stage name and a human-readable detail (never Credential_Material) -- on any stage
error or when the 900s budget is exceeded before the endpoint is emitted (Req 2.6, 2.7, 3.8,
3.9).

Both the resource creator and the monotonic clock are injectable seams, so the FSM is fully
offline-testable with a fake creator (returning canned identifiers) and a fake clock (jumping
time without waiting) -- no boto3 and no network live in this module. The deployment-specific
stage lists live in ``deploy/agentcore.py`` and ``deploy/apigateway.py`` (tasks 10.1/10.3),
which plug their own stages and a real, boto3-backed creator into :func:`provision`.

Alongside the provisioning FSM this module also holds the teardown workflow. Teardown consumes
the :class:`ResourceInventory` the provisioning FSM produces and deletes each recorded resource
through an injected :class:`ResourceDeleter` seam. A deleter signals *already-absent* by raising
:class:`ResourceNotFound`, which teardown treats as an idempotent success so re-runs against an
already-torn-down inventory report success (Req 8.7); any other exception marks that resource as
undeleted. Teardown reports success iff no resource remains, and on failure names exactly the
resources whose deletion failed without retrying ones already deleted (Req 8.2, 8.5, 8.6). Like
the creator/clock seams, the deleter is injectable, so teardown is fully offline-testable with a
fake deleter driving per-resource outcomes -- no boto3 and no network live in this module.
"""

from __future__ import annotations

import enum
import time
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from integration.harness.credential_scan import CredentialMaterialScanner
from integration.harness.inventory import ResourceInventory, ResourceRecord
from pathlib import Path
from typing import Any, Callable, Optional, Protocol


# The maximum wall-clock time a provisioning run may take before it is reported failed
# (Req 2.6, 3.8). Measured with the injected clock seam so tests need not wait in real time.
BUDGET_SECONDS: float = 900.0

# A monotonic clock seam returning a float number of seconds. Injectable for offline tests.
Clock = Callable[[], float]


class ProvisionStatus(enum.Enum):
    """The terminal outcome of a provisioning run."""

    COMPLETE = 'complete'
    FAILED = 'failed'


@dataclass(frozen=True)
class ProvisionResult:
    """The outcome of a provisioning run.

    Exactly one of the COMPLETE or FAILED shapes is populated:

    - On :attr:`ProvisionStatus.COMPLETE`, ``endpoint`` carries the emitted endpoint reference
      and both ``failed_stage`` and ``detail`` are ``None``.
    - On :attr:`ProvisionStatus.FAILED`, ``failed_stage`` names the stage that failed and
      ``detail`` gives a human-readable cause (never Credential_Material); ``endpoint`` is
      ``None``.

    ``inventory_path`` always points at the persisted inventory, whether the run completed or
    failed, so an operator can always run teardown against what was created (Req 8.3).
    """

    status: ProvisionStatus
    endpoint: Optional[str]
    failed_stage: Optional[str]
    detail: Optional[str]
    inventory_path: Path


@dataclass(frozen=True)
class CreatedResource:
    """The identity of a single resource returned by a :class:`ResourceCreator`.

    Attributes:
        resource_id: Provider identifier of the created resource (ARN, name, or physical id).
        resource_type: Resource category, e.g. ``'dynamodb-table'`` or
            ``'agentcore-runtime'``.
        attributes: Non-secret extras to record (for example an endpoint reference). These
            values must never contain Credential_Material; they are validated by the
            inventory's scanner before the inventory is written (Req 7.3).
        endpoint: When this creation emits the deployment's endpoint reference, the endpoint
            URL/identifier; otherwise ``None``.
    """

    resource_id: str
    resource_type: str
    attributes: Mapping[str, str] = field(default_factory=dict)
    endpoint: Optional[str] = None


class ResourceCreator(Protocol):
    """Seam that creates one AWS resource for a stage and returns its identity.

    Implementations perform the real AWS calls (in ``deploy/agentcore.py`` and
    ``deploy/apigateway.py``); tests inject a fake that returns canned
    :class:`CreatedResource` values -- or raises to simulate a stage failure -- without
    touching AWS. Keeping this a narrow seam is what makes the FSM offline-testable.
    """

    def __call__(self, resource_type: str, /, **params: Any) -> CreatedResource:
        """Create the resource described by ``resource_type`` and ``params``.

        Args:
            resource_type: The category of resource to create.
            **params: Deployment-specific creation parameters.

        Returns:
            The identity of the created resource.
        """
        ...


@dataclass
class StageContext:
    """The context handed to each stage while the FSM runs.

    A stage creates resources exclusively through :meth:`create`, which invokes the injected
    :class:`ResourceCreator` and records the result into the inventory in the same call, so
    every resource is inventoried at the moment of creation (Req 8.3) -- even within a stage
    that creates several resources before failing.
    """

    region: str
    deployment: str
    creator: ResourceCreator
    inventory: ResourceInventory

    def create(self, resource_type: str, /, **params: Any) -> CreatedResource:
        """Create one resource and record it in the inventory immediately.

        Args:
            resource_type: The category of resource to create.
            **params: Deployment-specific creation parameters forwarded to the creator.

        Returns:
            The :class:`CreatedResource` returned by the injected creator.
        """
        created = self.creator(resource_type, **params)
        self.inventory.add(
            ResourceRecord(
                resource_id=created.resource_id,
                resource_type=created.resource_type,
                region=self.region,
                deployment=self.deployment,
                attributes=dict(created.attributes),
            )
        )
        return created


# A stage runs against the context and returns the emitted endpoint reference, or ``None`` if
# this stage does not emit the endpoint.
StageRun = Callable[[StageContext], Optional[str]]


@dataclass(frozen=True)
class ProvisionStage:
    """A single named step in a deployment's provisioning sequence.

    Attributes:
        name: The human-readable stage name, reported as ``failed_stage`` on failure
            (Req 2.7, 3.9).
        run: A callable that creates this stage's resource(s) through
            :meth:`StageContext.create` and returns the emitted endpoint reference, or
            ``None`` if this stage does not emit the endpoint.
    """

    name: str
    run: StageRun


def _redact(detail: str, scanner: Optional[CredentialMaterialScanner]) -> str:
    """Return ``detail`` if clean, otherwise a redacted message naming only the material type.

    Failure detail is built from exception text, which could in principle echo a secret. When
    a scanner is supplied and it detects registered Credential_Material, the detail is
    replaced with a redacted message that names the material type(s) but never the value
    (Req 7.4). Without a scanner the detail is returned unchanged.
    """
    if scanner is None:
        return detail
    findings = scanner.scan(detail, 'provision-detail')
    if not findings:
        return detail
    types = ', '.join(sorted({finding.material_type.value for finding in findings}))
    return f'failure detail redacted: contained {types} (value redacted)'


def _persist(
    inventory: ResourceInventory,
    inventory_path: Path,
    scanner: Optional[CredentialMaterialScanner],
) -> None:
    """Write the current inventory to disk, validating attributes against the scanner."""
    inventory.save(inventory_path, scanner=scanner)


def _failed(
    inventory: ResourceInventory,
    inventory_path: Path,
    scanner: Optional[CredentialMaterialScanner],
    stage_name: str,
    detail: str,
) -> ProvisionResult:
    """Persist the inventory and build a FAILED result naming the stage and (redacted) cause."""
    _persist(inventory, inventory_path, scanner)
    return ProvisionResult(
        status=ProvisionStatus.FAILED,
        endpoint=None,
        failed_stage=stage_name,
        detail=_redact(detail, scanner),
        inventory_path=inventory_path,
    )


def provision(
    *,
    deployment: str,
    region: str,
    stages: Sequence[ProvisionStage],
    creator: ResourceCreator,
    inventory_path: str | Path,
    scanner: Optional[CredentialMaterialScanner] = None,
    clock: Clock = time.monotonic,
    budget_seconds: float = BUDGET_SECONDS,
) -> ProvisionResult:
    """Run the provisioning FSM for a deployment and return its terminal outcome.

    The FSM walks ``stages`` in order. Each stage creates its resource(s) through the injected
    ``creator`` and records them into a fresh inventory at the moment of creation, and the
    inventory is persisted after each stage so a failure at any point still leaves a complete
    teardown trail (Req 8.3). The run reports:

    - :class:`ProvisionStatus.COMPLETE` as soon as a stage emits an endpoint reference within
      the budget, carrying that endpoint (Req 2.5, 3.7).
    - :class:`ProvisionStatus.FAILED` with the failed stage name and a human-readable detail
      if a stage raises (Req 2.7, 3.9), if the ``budget_seconds`` budget is exceeded before an
      endpoint is emitted (Req 2.6, 3.8), or if every stage runs without emitting an endpoint.

    Elapsed time is measured with the injected ``clock`` seam, so tests drive timeouts with a
    fake clock without waiting in real time. No AWS client or network access lives in this
    function; the ``creator`` seam is the only path to resource creation.

    Args:
        deployment: The deployment identifier, ``'agentcore'`` or ``'apigateway'``, recorded
            on the inventory and every resource record.
        region: The target AWS region; provisioned resources are recorded in this region
            (Req 8.4).
        stages: The ordered provisioning stages for this deployment.
        creator: The injected resource-creation seam (real boto3-backed, or a test fake).
        inventory_path: Where the resource inventory is persisted; also returned on the result.
        scanner: Optional credential-material scanner used to validate inventory attributes
            before write and to redact any secret that appears in a failure detail (Req 7.3,
            7.4).
        clock: Monotonic clock seam returning seconds; defaults to :func:`time.monotonic`.
        budget_seconds: The provisioning budget in seconds; defaults to
            :data:`BUDGET_SECONDS` (900s).

    Returns:
        A :class:`ProvisionResult` describing the terminal outcome, always carrying the
        ``inventory_path`` of the persisted inventory.
    """
    path = Path(inventory_path)
    inventory = ResourceInventory(deployment=deployment, region=region)
    context = StageContext(
        region=region,
        deployment=deployment,
        creator=creator,
        inventory=inventory,
    )

    start = clock()

    for stage in stages:
        # Budget check before starting the stage: if the budget is already spent and no
        # endpoint has been emitted, the run has timed out (Req 2.6, 3.8).
        elapsed = clock() - start
        if elapsed > budget_seconds:
            return _failed(
                inventory,
                path,
                scanner,
                stage.name,
                f'provisioning exceeded the {budget_seconds:g}s budget before stage '
                f'{stage.name!r} ({elapsed:.0f}s elapsed) without emitting an endpoint',
            )

        try:
            emitted = stage.run(context)
        except Exception as exc:  # noqa: BLE001 - surfaced as a FAILED stage outcome
            return _failed(
                inventory,
                path,
                scanner,
                stage.name,
                f'stage {stage.name!r} failed: {exc}',
            )

        # Persist the trail after every successful stage so teardown always sees what exists.
        _persist(inventory, path, scanner)

        if emitted is not None:
            # An endpoint was emitted: complete iff it landed within the budget (Req 2.6, 3.8).
            elapsed = clock() - start
            if elapsed > budget_seconds:
                return _failed(
                    inventory,
                    path,
                    scanner,
                    stage.name,
                    f'provisioning exceeded the {budget_seconds:g}s budget while emitting the '
                    f'endpoint in stage {stage.name!r} ({elapsed:.0f}s elapsed)',
                )
            return ProvisionResult(
                status=ProvisionStatus.COMPLETE,
                endpoint=emitted,
                failed_stage=None,
                detail=None,
                inventory_path=path,
            )

    # Every stage ran without emitting an endpoint reference: cannot report complete.
    last_stage = stages[-1].name if stages else 'provision'
    return _failed(
        inventory,
        path,
        scanner,
        last_stage,
        'provisioning completed all stages without emitting an endpoint reference',
    )


class ResourceNotFound(Exception):
    """Raised by a :class:`ResourceDeleter` to signal a resource is already absent.

    A deleter raises this when the target resource does not exist (for example the provider
    returned a not-found error, or a previous teardown already removed it). Teardown treats
    this as an idempotent success -- the resource is considered deleted and is not retried --
    so re-running teardown against an inventory whose resources are already gone reports
    success (Req 8.7).

    Any *other* exception a deleter raises is treated as a real deletion failure, and the
    resource is recorded as undeleted (Req 8.6).
    """


class ResourceDeleter(Protocol):
    """Seam that deletes one recorded resource, or signals it was already absent.

    Implementations perform the real AWS delete calls (in ``deploy/agentcore.py`` and
    ``deploy/apigateway.py``); tests inject a fake that maps each record to a canned outcome
    -- deleted, already-absent, or failure -- without touching AWS. Keeping this a narrow seam
    is what makes teardown offline-testable.

    The contract is:

    - Return ``None`` when the resource was deleted successfully.
    - Raise :class:`ResourceNotFound` when the resource is already absent; teardown treats
      this as an idempotent success (the resource is considered deleted, Req 8.7).
    - Raise any other exception to signal a real failure; teardown records that resource as
      undeleted (Req 8.6).
    """

    def __call__(self, record: ResourceRecord, /) -> None:
        """Delete the resource identified by ``record``.

        Args:
            record: The inventoried resource to delete.

        Raises:
            ResourceNotFound: If the resource is already absent (idempotent success).
            Exception: Any other exception signals a real deletion failure.
        """
        ...


@dataclass(frozen=True)
class TeardownResult:
    """The outcome of a teardown run.

    Attributes:
        succeeded: ``True`` iff every inventoried resource was deleted or already absent, i.e.
            iff ``undeleted`` is empty (Req 8.5, 8.7).
        undeleted: Exactly the records whose deletion failed, in inventory order; empty on
            success. This names precisely the resources that were not deleted so an operator
            can act on them (Req 8.6).
    """

    succeeded: bool
    undeleted: tuple[ResourceRecord, ...]


def teardown(
    *,
    inventory: ResourceInventory,
    deleter: ResourceDeleter,
) -> TeardownResult:
    """Delete every resource in ``inventory`` through ``deleter`` and report the outcome.

    Teardown iterates the inventory in recorded order and attempts to delete each resource
    exactly once through the injected ``deleter`` seam. A :class:`ResourceNotFound` raised by
    the deleter means the resource is already absent and is treated as deleted, so re-running
    teardown against an already-torn-down inventory reports success (Req 8.7). Any other
    exception marks that resource as undeleted; resources that were deleted (or already absent)
    are never retried on the failure path.

    The run reports success iff no resource remains undeleted (Req 8.5); on failure the result
    names exactly the resources whose deletion failed (Req 8.6). No AWS client or network
    access lives in this function; the ``deleter`` seam is the only path to deletion.

    Args:
        inventory: The recorded inventory of resources to delete.
        deleter: The injected resource-deletion seam (real boto3-backed, or a test fake).

    Returns:
        A :class:`TeardownResult` whose ``succeeded`` is ``True`` iff ``undeleted`` is empty.
    """
    undeleted: list[ResourceRecord] = []
    for record in inventory.records:
        try:
            deleter(record)
        except ResourceNotFound:
            # Already absent: treat as deleted (idempotent success) and do not retry.
            continue
        except Exception:  # noqa: BLE001 - any real failure marks the resource undeleted
            undeleted.append(record)
    return TeardownResult(succeeded=not undeleted, undeleted=tuple(undeleted))


def teardown_from_path(
    path: str | Path,
    deleter: ResourceDeleter,
) -> TeardownResult:
    """Load an inventory from ``path`` and tear it down through ``deleter``.

    A convenience wrapper around :func:`teardown` that loads the persisted inventory written by
    the provisioning FSM (see :meth:`ResourceInventory.load`) before delegating. All teardown
    semantics -- idempotent already-absent handling and precise undeleted reporting -- are
    those of :func:`teardown`.

    Args:
        path: The file path of the persisted inventory to tear down.
        deleter: The injected resource-deletion seam.

    Returns:
        A :class:`TeardownResult` describing the teardown outcome.
    """
    inventory = ResourceInventory.load(path)
    return teardown(inventory=inventory, deleter=deleter)
