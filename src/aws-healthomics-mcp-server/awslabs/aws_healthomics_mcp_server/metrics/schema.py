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

"""Schema for AWS HealthOmics vended metrics (CloudWatch OpenTelemetry metrics).

This module is the single source of truth for the vended-metrics contract: the
OTel metric names HealthOmics emits into the customer's account, their units,
instrument types (counter vs gauge), datapoint attributes, and the run
configurations under which each metric is present.

PromQL label mapping (CloudWatch Metrics PromQL API):

- OTLP resource attributes are prefixed ``@resource.``
- the instrumentation scope name is the label ``@instrumentation.@name``
- datapoint attributes are bare label names
- ``@aws.account`` / ``@aws.region`` are system labels

All of these contain ``.`` and ``@`` so they must be quoted in selectors, e.g.::

    {"aws.omics.task.cpu.usage", "@instrumentation.@name"="cloudwatch.aws/omics",
     "@resource.aws.omics.run.id"="1234567"}

Counter semantics: ``network.io``, ``filesystem.io`` and ``filesystem.operations``
are cumulative monotonic sums carrying raw totals since container/mount start,
NOT per-second rates. Consumers derive rates (e.g. via ``rate()``) or read the
window max.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional


# ---------------------------------------------------------------------------
# Scope and label constants
# ---------------------------------------------------------------------------

SCOPE_NAME = 'cloudwatch.aws/omics'
"""Instrumentation scope name for HealthOmics vended metrics."""

SCOPE_NAME_LABEL = '@instrumentation.@name'
"""PromQL label carrying the instrumentation scope name."""

METRIC_NAME_LABEL = '__name__'
AWS_ACCOUNT_LABEL = '@aws.account'
AWS_REGION_LABEL = '@aws.region'

RESOURCE_LABEL_PREFIX = '@resource.'


def resource_label(key: str) -> str:
    """Return the PromQL label for an OTLP resource attribute key."""
    return f'{RESOURCE_LABEL_PREFIX}{key}'


# Resource attributes (task identity is a *resource* attribute, not a datapoint
# attribute: each per-task metrics sidecar exports its own OTLP resource).
RUN_ID_ATTRIBUTE = 'aws.omics.run.id'
WORKFLOW_ID_ATTRIBUTE = 'aws.omics.workflow.id'
TASK_ID_ATTRIBUTE = 'aws.omics.task.id'
STORAGE_TYPE_ATTRIBUTE = 'aws.omics.storage.type'

RUN_ID_LABEL = resource_label(RUN_ID_ATTRIBUTE)
WORKFLOW_ID_LABEL = resource_label(WORKFLOW_ID_ATTRIBUTE)
TASK_ID_LABEL = resource_label(TASK_ID_ATTRIBUTE)
STORAGE_TYPE_LABEL = resource_label(STORAGE_TYPE_ATTRIBUTE)

# Datapoint attributes (bare PromQL labels)
SCRATCH_STORAGE_MODE_ATTRIBUTE = 'scratch.storage.mode'
GPU_ID_ATTRIBUTE = 'gpu.id'
NETWORK_IO_DIRECTION_ATTRIBUTE = 'network.io.direction'
FILESYSTEM_IO_DIRECTION_ATTRIBUTE = 'filesystem.io.direction'

NETWORK_IO_DIRECTIONS = ['receive', 'transmit']
FILESYSTEM_IO_DIRECTIONS = ['read', 'write']

# Regions where HealthOmics is available but vended metrics are NOT supported.
# Runs in these regions emit no vended metrics regardless of run configuration;
# consumers should fall back to timeline/manifest analysis.
UNSUPPORTED_REGIONS = frozenset({'il-central-1'})


def is_region_supported(region: Optional[str]) -> bool:
    """Whether vended metrics are supported in the given region.

    None (region not yet resolved) is treated as supported; the query itself
    will surface any real availability problem.
    """
    return region not in UNSUPPORTED_REGIONS


def region_unsupported_reason(region: str) -> str:
    """Explanation for tools to return when a region has no vended metrics."""
    return (
        f'HealthOmics vended metrics are not supported in {region}. '
        'No metric series exist for runs in this region; use timeline/manifest '
        'analysis (AnalyzeAHORunPerformance) instead.'
    )


# Ingestion characteristics consumers must account for
INGESTION_LAG_SECONDS = 120
"""Nominal end-to-end delay before emitted datapoints are queryable."""

EFS_RUN_FILESYSTEM_LAG_SECONDS = 35 * 60
"""DYNAMIC (EFS) run-filesystem usage lags ~35 minutes (EFS metered-size lag)."""

MIN_TASK_DURATION_SECONDS = 60
"""Tasks shorter than the ~30s sampling cadence may produce no datapoints."""

DEFAULT_SAMPLING_INTERVAL_SECONDS = 30
"""Emitter sampling cadence for metrics without a per-metric override."""

SCRATCH_USAGE_SAMPLING_INTERVAL_SECONDS = 20 * 60
"""Scratch storage usage is sampled every ~20 minutes: measuring it walks the
filesystem, so the emitter uses a slow cadence to avoid adding I/O load."""

VENDED_METRICS_LAUNCH_DATE = '2026-09-07'
"""Production launch date (UTC) of HealthOmics vended metrics. Runs started
before this date have no vended OTel metrics."""


def predates_launch(run_start: Optional[datetime]) -> bool:
    """Whether a run started before vended metrics launched in production."""
    if run_start is None:
        return False
    launch = datetime.fromisoformat(VENDED_METRICS_LAUNCH_DATE).replace(tzinfo=timezone.utc)
    return run_start < launch


def launch_date_reason() -> str:
    """Explanation for runs that predate the vended-metrics production launch."""
    return (
        f'This run started before the vended metrics production launch '
        f'({VENDED_METRICS_LAUNCH_DATE}); no vended OTel metrics exist for it. '
        'Use timeline/manifest analysis (AnalyzeAHORunPerformance) instead.'
    )


def short_task_reason(duration_seconds: float) -> str:
    """Explanation for a task too short to produce metric datapoints."""
    return (
        f'Task ran for {duration_seconds:.0f}s, shorter than the '
        f'{MIN_TASK_DURATION_SECONDS}s minimum for reliable metric emission '
        f'(~{DEFAULT_SAMPLING_INTERVAL_SECONDS}s sampling cadence); '
        'it may have produced no datapoints.'
    )


class StorageType(str, Enum):
    """Run storage types that carry the storage.type resource attribute.

    Other storage types (e.g. S3) omit the attribute and emit no
    filesystem/run-storage metrics.
    """

    STATIC = 'STATIC'
    DYNAMIC = 'DYNAMIC'


class ScratchStorageMode(str, Enum):
    """Allowed scratch.storage.mode values; matches the run's scratchStorageMode."""

    LOCAL = 'LOCAL'
    SHARED = 'SHARED'


class InstrumentType(str, Enum):
    """OTel instrument type of a vended metric."""

    GAUGE = 'gauge'
    SUM = 'sum'  # cumulative monotonic counter


# ---------------------------------------------------------------------------
# Metric definitions
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class VendedMetric:
    """One vended metric as the emitters produce it.

    Attributes:
        name: OTel metric name (also the PromQL ``__name__``).
        unit: UCUM unit (``{cpu}`` = fractional vCPUs, ``By`` = bytes,
            ``{operation}`` = operation count, ``%`` = percent).
        type: Instrument type; SUM metrics are cumulative counters.
        datapoint_attributes: Datapoint attribute key -> allowed values
            (empty list = any value, e.g. gpu ids).
        emitted_only_when: Human-readable condition for conditional metrics,
            or None if the metric is emitted for every run.
        sampling_interval_seconds: Emitter sampling cadence when it differs
            from the ~30s default (e.g. scratch usage's slow cadence).
    """

    name: str
    unit: str
    type: InstrumentType = InstrumentType.GAUGE
    datapoint_attributes: Dict[str, List[str]] = field(default_factory=dict)
    emitted_only_when: Optional[str] = None
    sampling_interval_seconds: int = DEFAULT_SAMPLING_INTERVAL_SECONDS

    @property
    def is_conditional(self) -> bool:
        """Whether this metric is only emitted under a specific run configuration."""
        return self.emitted_only_when is not None

    @property
    def is_counter(self) -> bool:
        """Whether this metric is a cumulative monotonic counter."""
        return self.type == InstrumentType.SUM


@dataclass(frozen=True)
class VendedMetricGroup:
    """A family of metrics sharing one emitter code path and one granularity.

    ``per_task`` tells consumers where task identity lives: per-task metrics
    carry ``aws.omics.task.id`` as a resource attribute; per-run metrics come
    from the engine sidecar on the logging task and have no task id at all.
    """

    id: str
    per_task: bool
    metrics: List[VendedMetric]

    @property
    def metric_names(self) -> List[str]:
        """Names of all metrics in this group."""
        return [m.name for m in self.metrics]


# Group A - per-task compute (cpu/memory from container stats, network totals).
PER_TASK_COMPUTE = VendedMetricGroup(
    id='per-task-compute',
    per_task=True,
    metrics=[
        VendedMetric('aws.omics.task.cpu.usage', '{cpu}'),
        VendedMetric('aws.omics.task.cpu.limit', '{cpu}'),
        VendedMetric('aws.omics.task.memory.usage', 'By'),
        VendedMetric('aws.omics.task.memory.limit', 'By'),
        VendedMetric(
            'aws.omics.task.network.io',
            'By',
            type=InstrumentType.SUM,
            datapoint_attributes={NETWORK_IO_DIRECTION_ATTRIBUTE: NETWORK_IO_DIRECTIONS},
        ),
    ],
)

# Group B - per-task run-filesystem io (STATIC/DYNAMIC run storage only) and
# GPU gauges (one datapoint per gpu.id; consumers aggregate across devices).
PER_TASK_IO_AND_GPU = VendedMetricGroup(
    id='per-task-io-and-gpu',
    per_task=True,
    metrics=[
        VendedMetric(
            'aws.omics.task.filesystem.io',
            'By',
            type=InstrumentType.SUM,
            datapoint_attributes={FILESYSTEM_IO_DIRECTION_ATTRIBUTE: FILESYSTEM_IO_DIRECTIONS},
            emitted_only_when='the run uses STATIC or DYNAMIC run storage',
        ),
        VendedMetric(
            'aws.omics.task.filesystem.operations',
            '{operation}',
            type=InstrumentType.SUM,
            datapoint_attributes={FILESYSTEM_IO_DIRECTION_ATTRIBUTE: FILESYSTEM_IO_DIRECTIONS},
            emitted_only_when='the run uses STATIC or DYNAMIC run storage',
        ),
        VendedMetric(
            'aws.omics.task.gpu.utilization',
            '%',
            datapoint_attributes={GPU_ID_ATTRIBUTE: []},
            emitted_only_when='the task requests accelerators',
        ),
        VendedMetric(
            'aws.omics.task.gpu.memory.usage',
            'By',
            datapoint_attributes={GPU_ID_ATTRIBUTE: []},
            emitted_only_when='the task requests accelerators',
        ),
        VendedMetric(
            'aws.omics.task.gpu.memory.limit',
            'By',
            datapoint_attributes={GPU_ID_ATTRIBUTE: []},
            emitted_only_when='the task requests accelerators',
        ),
    ],
)

# Group C - per-task scratch storage. LOCAL mode emits usage and limit; SHARED
# mode emits usage only (a filesystem shared by all tasks has no meaningful
# per-task limit).
PER_TASK_SCRATCH = VendedMetricGroup(
    id='per-task-scratch',
    per_task=True,
    metrics=[
        VendedMetric(
            'aws.omics.task.filesystem.scratch.storage.usage',
            'By',
            datapoint_attributes={
                SCRATCH_STORAGE_MODE_ATTRIBUTE: [m.value for m in ScratchStorageMode]
            },
            sampling_interval_seconds=SCRATCH_USAGE_SAMPLING_INTERVAL_SECONDS,
        ),
        VendedMetric(
            'aws.omics.task.filesystem.scratch.storage.limit',
            'By',
            datapoint_attributes={
                SCRATCH_STORAGE_MODE_ATTRIBUTE: [ScratchStorageMode.LOCAL.value]
            },
            emitted_only_when='the run uses LOCAL scratch storage',
        ),
    ],
)

# Group D - per-run storage (the run filesystem), emitted by the engine sidecar
# on the logging task. No task id on the resource. usage lags ~35 minutes on
# DYNAMIC (EFS metered size); limit exists only on STATIC.
PER_RUN_STORAGE = VendedMetricGroup(
    id='per-run-storage',
    per_task=False,
    metrics=[
        VendedMetric(
            'aws.omics.run.filesystem.usage',
            'By',
            emitted_only_when='the run uses STATIC or DYNAMIC run storage',
        ),
        VendedMetric(
            'aws.omics.run.filesystem.limit',
            'By',
            emitted_only_when='the run uses STATIC run storage',
        ),
    ],
)

ALL_GROUPS = [PER_TASK_COMPUTE, PER_TASK_IO_AND_GPU, PER_TASK_SCRATCH, PER_RUN_STORAGE]

ALL_METRICS: List[VendedMetric] = [m for g in ALL_GROUPS for m in g.metrics]

ALL_METRIC_NAMES: List[str] = [m.name for m in ALL_METRICS]

PER_TASK_METRIC_NAMES: List[str] = [m.name for g in ALL_GROUPS if g.per_task for m in g.metrics]

GPU_METRIC_NAMES: List[str] = [
    m.name for m in PER_TASK_IO_AND_GPU.metrics if m.name.startswith('aws.omics.task.gpu.')
]

FILESYSTEM_IO_METRIC_NAMES: List[str] = [
    m.name for m in PER_TASK_IO_AND_GPU.metrics if not m.name.startswith('aws.omics.task.gpu.')
]

_METRICS_BY_NAME: Dict[str, VendedMetric] = {m.name: m for m in ALL_METRICS}
_GROUP_BY_METRIC_NAME: Dict[str, VendedMetricGroup] = {
    m.name: g for g in ALL_GROUPS for m in g.metrics
}


def metric_of(metric_name: str) -> VendedMetric:
    """Return the declared metric for a name.

    Raises:
        ValueError: If the name is not in the schema; the message lists all
            valid metric names so callers (and LLMs) can self-correct.
    """
    metric = _METRICS_BY_NAME.get(metric_name)
    if metric is None:
        raise ValueError(
            f'Unknown vended metric name: {metric_name!r}. '
            f'Valid names: {", ".join(sorted(ALL_METRIC_NAMES))}'
        )
    return metric


def group_of(metric_name: str) -> VendedMetricGroup:
    """Return the group that declares a metric name (validates the name)."""
    metric_of(metric_name)
    return _GROUP_BY_METRIC_NAME[metric_name]


def is_per_task(metric_name: str) -> bool:
    """Whether the metric's OTLP resource carries a task id."""
    return group_of(metric_name).per_task


# ---------------------------------------------------------------------------
# Presence rules
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class MissingMetric:
    """A schema metric expected to be absent for a given run configuration."""

    name: str
    reason: str


@dataclass(frozen=True)
class MetricPresence:
    """Which schema metrics are expected present/absent for a run configuration."""

    present: List[str]
    missing: List[MissingMetric]


def presence_for(
    storage_type: Optional[str],
    scratch_mode: Optional[str] = None,
    has_gpu_tasks: bool = False,
) -> MetricPresence:
    """Compute expected metric presence for a run configuration.

    Args:
        storage_type: The run's storage type ('STATIC', 'DYNAMIC', or None/other
            for storage types without a run filesystem, e.g. S3).
        scratch_mode: The run's scratch storage mode ('LOCAL' or 'SHARED');
            None is treated as LOCAL-like (limit presence unknown but allowed).
        has_gpu_tasks: Whether any task in the run requested accelerators.

    Returns:
        MetricPresence with expected-present metric names and expected-absent
        names each paired with a human-readable reason. "Present" means the
        emitter produces the metric for this configuration; delivery is
        at-least-once, not guaranteed, so consumers should still verify with a
        series query before asserting on values.
    """
    has_run_filesystem = storage_type in (StorageType.STATIC.value, StorageType.DYNAMIC.value)

    present: List[str] = []
    missing: List[MissingMetric] = []

    for metric in ALL_METRICS:
        if metric.name in GPU_METRIC_NAMES:
            if has_gpu_tasks:
                present.append(metric.name)
            else:
                missing.append(
                    MissingMetric(
                        metric.name,
                        'GPU metrics are only emitted for tasks that request accelerators',
                    )
                )
        elif metric.name in FILESYSTEM_IO_METRIC_NAMES:
            if has_run_filesystem:
                present.append(metric.name)
            else:
                missing.append(
                    MissingMetric(
                        metric.name,
                        'Task filesystem I/O metrics require STATIC or DYNAMIC run storage',
                    )
                )
        elif metric.name == 'aws.omics.task.filesystem.scratch.storage.limit':
            if scratch_mode == ScratchStorageMode.SHARED.value:
                missing.append(
                    MissingMetric(
                        metric.name,
                        'Scratch storage limit is not emitted in SHARED scratch mode '
                        '(the shared run filesystem has no per-task limit)',
                    )
                )
            else:
                present.append(metric.name)
        elif metric.name == 'aws.omics.run.filesystem.usage':
            if has_run_filesystem:
                present.append(metric.name)
            else:
                missing.append(
                    MissingMetric(
                        metric.name,
                        'Run filesystem metrics require STATIC or DYNAMIC run storage',
                    )
                )
        elif metric.name == 'aws.omics.run.filesystem.limit':
            if storage_type == StorageType.STATIC.value:
                present.append(metric.name)
            else:
                missing.append(
                    MissingMetric(
                        metric.name,
                        'Run filesystem limit is only emitted for STATIC run storage '
                        '(DYNAMIC/EFS has no fixed capacity)',
                    )
                )
        else:
            present.append(metric.name)

    return MetricPresence(present=present, missing=missing)


# ---------------------------------------------------------------------------
# PromQL selector construction
# ---------------------------------------------------------------------------


def _quote(value: str) -> str:
    """Quote a label name or value for a PromQL selector."""
    escaped = value.replace('\\', '\\\\').replace('"', '\\"')
    return f'"{escaped}"'


def build_selector(
    metric_name: str,
    run_id: Optional[str] = None,
    task_id: Optional[str] = None,
    workflow_id: Optional[str] = None,
    extra_labels: Optional[Dict[str, str]] = None,
) -> str:
    """Build a PromQL vector selector for a vended metric.

    The metric name is validated against the schema; label names containing
    ``.``/``@`` are quoted as the CloudWatch PromQL API requires. The scope
    label is always included so the selector never matches other producers'
    metrics with colliding names.

    Args:
        metric_name: A schema metric name (validated; raises ValueError with
            the valid names otherwise).
        run_id: Filter by run id resource attribute.
        task_id: Filter by task id resource attribute (per-task metrics only;
            raises ValueError for per-run metrics, which carry no task id).
        workflow_id: Filter by workflow id resource attribute.
        extra_labels: Additional datapoint-attribute filters, validated against
            the metric's declared datapoint attributes.

    Returns:
        A PromQL selector string, e.g.
        ``{"aws.omics.task.cpu.usage", "@instrumentation.@name"="cloudwatch.aws/omics", "@resource.aws.omics.run.id"="123"}``
    """
    metric = metric_of(metric_name)

    if task_id is not None and not is_per_task(metric_name):
        raise ValueError(
            f'{metric_name} is a per-run metric and carries no task id; '
            'query it without a task_id filter'
        )

    parts: List[str] = [_quote(metric_name), f'{_quote(SCOPE_NAME_LABEL)}={_quote(SCOPE_NAME)}']
    if run_id is not None:
        parts.append(f'{_quote(RUN_ID_LABEL)}={_quote(run_id)}')
    if workflow_id is not None:
        parts.append(f'{_quote(WORKFLOW_ID_LABEL)}={_quote(workflow_id)}')
    if task_id is not None:
        parts.append(f'{_quote(TASK_ID_LABEL)}={_quote(task_id)}')

    for key, value in (extra_labels or {}).items():
        allowed = metric.datapoint_attributes.get(key)
        if allowed is None:
            raise ValueError(
                f'{key!r} is not a datapoint attribute of {metric_name}. '
                f'Valid attributes: {sorted(metric.datapoint_attributes) or "(none)"}'
            )
        if allowed and value not in allowed:
            raise ValueError(
                f'{value!r} is not an allowed value for {key!r} on {metric_name}. '
                f'Allowed values: {allowed}'
            )
        parts.append(f'{_quote(key)}={_quote(value)}')

    return '{' + ', '.join(parts) + '}'
