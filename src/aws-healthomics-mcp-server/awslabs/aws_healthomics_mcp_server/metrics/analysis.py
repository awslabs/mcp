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

"""Vended-metrics classification for run performance analysis.

Turns per-task vended-metric summaries into resource signatures, bottleneck
verdicts, stuck-task verdicts (for active runs), and right-sizing suggestions.
This enriches AnalyzeAHORunPerformance beyond the manifest-derived analysis
with the fine-grained OTel dimensions (GPU, filesystem I/O, network, scratch).

All classification is pure and threshold-based so it is unit-testable against
synthetic series; the query orchestration lives in :func:`analyze_run_metrics`.
"""

import math
from awslabs.aws_healthomics_mcp_server.metrics import schema
from awslabs.aws_healthomics_mcp_server.metrics.client import (
    SeriesSummary,
    VendedMetricsClient,
    summarize_series,
    utc_now,
)
from awslabs.aws_healthomics_mcp_server.metrics.run_context import (
    RunContext,
    TaskContext,
    resolve_run,
)
from dataclasses import dataclass, field
from datetime import timedelta
from loguru import logger
from typing import Any, Dict, List, Optional


GIB = 1024**3

# Classification thresholds (fractions of the task's limit unless noted).
CPU_BOUND_THRESHOLD = 0.85
MEMORY_PRESSURE_THRESHOLD = 0.90
GPU_IDLE_THRESHOLD = 0.10  # percent-scale metric: 10%
SCRATCH_NEAR_LIMIT_THRESHOLD = 0.85
OVER_PROVISIONED_THRESHOLD = 0.25
IO_ACTIVE_BYTES_PER_SECOND = 1_000_000  # sustained >=1 MB/s counts as I/O activity
IO_BOUND_CPU_CEILING = 0.30

# Stuck-task detection (active runs): a RUNNING task with essentially no CPU
# and no I/O progress over the recent window is possibly hung.
STUCK_WINDOW = timedelta(minutes=15)
STUCK_CPU_CORES_CEILING = 0.05
STUCK_IO_DELTA_BYTES = 1024

# Metric families the analysis pass queries.
ANALYSIS_METRICS = [
    'aws.omics.task.cpu.usage',
    'aws.omics.task.cpu.limit',
    'aws.omics.task.memory.usage',
    'aws.omics.task.memory.limit',
    'aws.omics.task.gpu.utilization',
    'aws.omics.task.filesystem.io',
    'aws.omics.task.network.io',
    'aws.omics.task.filesystem.scratch.storage.usage',
    'aws.omics.task.filesystem.scratch.storage.limit',
]


@dataclass
class TaskSignature:
    """One task's observed resource signature from vended metrics."""

    task_id: str
    task_name: str
    cpu_peak: Optional[float] = None
    cpu_limit: Optional[float] = None
    cpu_average: Optional[float] = None
    memory_peak_bytes: Optional[float] = None
    memory_limit_bytes: Optional[float] = None
    gpu_peak_percent: Optional[float] = None
    filesystem_rate_bytes_per_second: Optional[float] = None
    network_rate_bytes_per_second: Optional[float] = None
    scratch_peak_bytes: Optional[float] = None
    scratch_limit_bytes: Optional[float] = None
    categories: List[str] = field(default_factory=list)

    @property
    def cpu_utilization(self) -> Optional[float]:
        """Average CPU as a fraction of the CPU limit."""
        if self.cpu_average is not None and self.cpu_limit:
            return self.cpu_average / self.cpu_limit
        return None

    @property
    def memory_utilization(self) -> Optional[float]:
        """Peak memory as a fraction of the memory limit."""
        if self.memory_peak_bytes is not None and self.memory_limit_bytes:
            return self.memory_peak_bytes / self.memory_limit_bytes
        return None

    @property
    def scratch_utilization(self) -> Optional[float]:
        """Peak scratch usage as a fraction of the scratch limit (LOCAL only)."""
        if self.scratch_peak_bytes is not None and self.scratch_limit_bytes:
            return self.scratch_peak_bytes / self.scratch_limit_bytes
        return None


def _summary_for(
    summaries: Dict[str, Dict[str, SeriesSummary]], metric: str, task_id: str
) -> Optional[SeriesSummary]:
    return summaries.get(metric, {}).get(task_id)


def build_task_signature(
    task: TaskContext, summaries: Dict[str, Dict[str, SeriesSummary]]
) -> TaskSignature:
    """Build a task's resource signature from collected metric summaries.

    Args:
        task: The task's context (identity, requested resources).
        summaries: metric name -> task_id -> summary (peak series per task).
    """
    signature = TaskSignature(task_id=task.task_id, task_name=task.name)

    cpu = _summary_for(summaries, 'aws.omics.task.cpu.usage', task.task_id)
    if cpu:
        signature.cpu_peak = cpu.maximum
        signature.cpu_average = cpu.average
    cpu_limit = _summary_for(summaries, 'aws.omics.task.cpu.limit', task.task_id)
    if cpu_limit:
        signature.cpu_limit = cpu_limit.maximum
    memory = _summary_for(summaries, 'aws.omics.task.memory.usage', task.task_id)
    if memory:
        signature.memory_peak_bytes = memory.maximum
    memory_limit = _summary_for(summaries, 'aws.omics.task.memory.limit', task.task_id)
    if memory_limit:
        signature.memory_limit_bytes = memory_limit.maximum
    gpu = _summary_for(summaries, 'aws.omics.task.gpu.utilization', task.task_id)
    if gpu:
        signature.gpu_peak_percent = gpu.maximum
    filesystem = _summary_for(summaries, 'aws.omics.task.filesystem.io', task.task_id)
    if filesystem:
        signature.filesystem_rate_bytes_per_second = filesystem.average_rate
    network = _summary_for(summaries, 'aws.omics.task.network.io', task.task_id)
    if network:
        signature.network_rate_bytes_per_second = network.average_rate
    scratch = _summary_for(
        summaries, 'aws.omics.task.filesystem.scratch.storage.usage', task.task_id
    )
    if scratch:
        signature.scratch_peak_bytes = scratch.maximum
    scratch_limit = _summary_for(
        summaries, 'aws.omics.task.filesystem.scratch.storage.limit', task.task_id
    )
    if scratch_limit:
        signature.scratch_limit_bytes = scratch_limit.maximum

    signature.categories = classify_signature(signature)
    return signature


def classify_signature(signature: TaskSignature) -> List[str]:
    """Assign bottleneck/efficiency categories to a task signature."""
    categories: List[str] = []

    cpu_utilization = signature.cpu_utilization
    memory_utilization = signature.memory_utilization

    if cpu_utilization is not None and cpu_utilization >= CPU_BOUND_THRESHOLD:
        categories.append('CPU_BOUND')
    if memory_utilization is not None and memory_utilization >= MEMORY_PRESSURE_THRESHOLD:
        categories.append('MEMORY_PRESSURE')
    if (
        signature.gpu_peak_percent is not None
        and signature.gpu_peak_percent <= GPU_IDLE_THRESHOLD * 100
    ):
        categories.append('GPU_IDLE')
    scratch_utilization = signature.scratch_utilization
    if scratch_utilization is not None and scratch_utilization >= SCRATCH_NEAR_LIMIT_THRESHOLD:
        categories.append('SCRATCH_NEAR_LIMIT')

    io_rate = max(
        signature.filesystem_rate_bytes_per_second or 0,
        signature.network_rate_bytes_per_second or 0,
    )
    if (
        cpu_utilization is not None
        and cpu_utilization <= IO_BOUND_CPU_CEILING
        and io_rate >= IO_ACTIVE_BYTES_PER_SECOND
    ):
        categories.append('IO_BOUND')

    if (
        not categories
        and cpu_utilization is not None
        and cpu_utilization <= OVER_PROVISIONED_THRESHOLD
        and (memory_utilization is None or memory_utilization <= OVER_PROVISIONED_THRESHOLD)
    ):
        categories.append('OVER_PROVISIONED')

    return categories or ['BALANCED']


@dataclass
class RightSizing:
    """Right-sizing suggestion for one task name, derived from observed peaks."""

    task_name: str
    task_count: int
    recommended_cpus: Optional[int] = None
    current_cpus: Optional[int] = None
    recommended_memory_gib: Optional[float] = None
    current_memory_gib: Optional[float] = None
    recommended_scratch_gib: Optional[float] = None


def right_size(
    run: RunContext, signatures: List[TaskSignature], headroom: float
) -> List[RightSizing]:
    """Suggest per-task-name resource sizes from observed peaks plus headroom.

    Only emits a suggestion where the observed peak (with headroom) differs
    from the requested value, so the output is actionable rather than a dump.
    """
    by_name: Dict[str, List[TaskSignature]] = {}
    for signature in signatures:
        by_name.setdefault(signature.task_name, []).append(signature)

    task_by_id = run.task_by_id
    suggestions: List[RightSizing] = []
    for name, group in sorted(by_name.items()):
        cpu_peaks = [s.cpu_peak for s in group if s.cpu_peak is not None]
        memory_peaks = [s.memory_peak_bytes for s in group if s.memory_peak_bytes is not None]
        scratch_peaks = [s.scratch_peak_bytes for s in group if s.scratch_peak_bytes is not None]
        requested = [task_by_id.get(s.task_id) for s in group]
        requested_cpus = max((t.cpus for t in requested if t and t.cpus), default=None)
        requested_memory = max(
            (t.memory_gib for t in requested if t and t.memory_gib), default=None
        )

        entry = RightSizing(task_name=name, task_count=len(group))
        if cpu_peaks:
            recommended = max(1, math.ceil(max(cpu_peaks) * (1 + headroom)))
            if requested_cpus and recommended < requested_cpus:
                entry.recommended_cpus = recommended
                entry.current_cpus = requested_cpus
        if memory_peaks:
            recommended_gib = round(max(memory_peaks) * (1 + headroom) / GIB, 2)
            if requested_memory and recommended_gib < requested_memory:
                entry.recommended_memory_gib = max(recommended_gib, 0.5)
                entry.current_memory_gib = requested_memory
        if scratch_peaks:
            recommended_scratch = round(max(scratch_peaks) * (1 + headroom) / GIB, 2)
            # Peaks under half a GiB fit any scratch size; a suggestion is noise.
            if recommended_scratch >= 0.5:
                entry.recommended_scratch_gib = recommended_scratch

        if (
            entry.recommended_cpus is not None
            or entry.recommended_memory_gib is not None
            or entry.recommended_scratch_gib is not None
        ):
            suggestions.append(entry)
    return suggestions


def detect_stuck_tasks(client: VendedMetricsClient, run: RunContext) -> List[Dict[str, Any]]:
    """Classify RUNNING tasks of an active run as progressing or possibly hung.

    A task with essentially zero CPU and zero filesystem-I/O progress over the
    recent window is POSSIBLY_HUNG; one whose memory sits at its limit while
    CPU stays low is MEMORY_THRASH_SUSPECT (working set no longer fits; the
    task refaults pages instead of progressing). Everything else with recent
    datapoints is PROGRESSING.
    """
    running = [t for t in run.tasks if t.status == 'RUNNING']
    if not running or not run.is_active:
        return []

    end = utc_now()
    start = end - STUCK_WINDOW

    def _by_task(metric_name: str) -> Dict[str, SeriesSummary]:
        metric = schema.metric_of(metric_name)
        selector = schema.build_selector(metric_name, run_id=run.run_id)
        result: Dict[str, SeriesSummary] = {}
        for series in client.query_range(selector, start, end):
            task_id = series.labels.get(schema.TASK_ID_LABEL)
            if task_id:
                summary = summarize_series(series, metric.is_counter)
                existing = result.get(task_id)
                if existing is None or (summary.maximum or 0) > (existing.maximum or 0):
                    result[task_id] = summary
        return result

    cpu_by_task = _by_task('aws.omics.task.cpu.usage')
    io_by_task = _by_task('aws.omics.task.filesystem.io')
    memory_by_task = _by_task('aws.omics.task.memory.usage')
    memory_limit_by_task = _by_task('aws.omics.task.memory.limit')

    verdicts: List[Dict[str, Any]] = []
    for task in running:
        cpu = cpu_by_task.get(task.task_id)
        io = io_by_task.get(task.task_id)
        memory = memory_by_task.get(task.task_id)
        memory_limit = memory_limit_by_task.get(task.task_id)

        if cpu is None or cpu.datapoint_count == 0:
            verdict = 'NO_RECENT_DATA'
            evidence = (
                f'no CPU datapoints in the last {int(STUCK_WINDOW.total_seconds() / 60)} min'
            )
        else:
            cpu_recent = cpu.average or 0
            io_delta = (io.total_delta if io else 0) or 0
            memory_utilization = (
                (memory.maximum / memory_limit.maximum)
                if memory and memory.maximum is not None and memory_limit and memory_limit.maximum
                else None
            )
            if (
                memory_utilization is not None
                and memory_utilization >= MEMORY_PRESSURE_THRESHOLD
                and cpu_recent <= IO_BOUND_CPU_CEILING * (task.cpus or 1)
            ):
                verdict = 'MEMORY_THRASH_SUSPECT'
                evidence = (
                    f'memory at {memory_utilization:.0%} of limit with low CPU '
                    f'({cpu_recent:.2f} cores)'
                )
            elif cpu_recent <= STUCK_CPU_CORES_CEILING and io_delta <= STUCK_IO_DELTA_BYTES:
                verdict = 'POSSIBLY_HUNG'
                evidence = (
                    f'~zero CPU ({cpu_recent:.3f} cores avg) and no filesystem I/O progress '
                    f'({io_delta:.0f} B) in the last {int(STUCK_WINDOW.total_seconds() / 60)} min'
                )
            else:
                verdict = 'PROGRESSING'
                evidence = f'CPU {cpu_recent:.2f} cores avg, filesystem I/O delta {io_delta:.0f} B'

        verdicts.append(
            {
                'task_id': task.task_id,
                'task_name': task.name,
                'verdict': verdict,
                'evidence': evidence,
            }
        )
    return verdicts


def _collect_summaries(
    client: VendedMetricsClient, run: RunContext, metric_names: List[str]
) -> Dict[str, Dict[str, SeriesSummary]]:
    """Query per-task peak summaries for the run: metric -> task_id -> summary."""
    start, end = run.query_window()
    collected: Dict[str, Dict[str, SeriesSummary]] = {}
    for name in metric_names:
        metric = schema.metric_of(name)
        selector = schema.build_selector(name, run_id=run.run_id)
        by_task: Dict[str, SeriesSummary] = {}
        for series in client.query_range(selector, start, end):
            task_id = series.labels.get(schema.TASK_ID_LABEL)
            if not task_id:
                continue
            summary = summarize_series(series, metric.is_counter)
            existing = by_task.get(task_id)
            if existing is None or (summary.maximum or 0) > (existing.maximum or 0):
                by_task[task_id] = summary
        if by_task:
            collected[name] = by_task
    return collected


def analyze_run_metrics(
    run_id: str, region: Optional[str] = None, headroom: float = 0.2
) -> Dict[str, Any]:
    """Run the vended-metrics analysis pass for one run.

    Returns a structured result with per-task signatures, category counts,
    stuck-task verdicts (active runs), right-sizing suggestions, and
    missing-metric notes — or an ``available: False`` result with a reason
    when metrics cannot be analyzed (unsupported region, feature off).
    """
    run = resolve_run(run_id, region=region)
    client = VendedMetricsClient(region=region)

    if not schema.is_region_supported(client.region):
        return {
            'run_id': run_id,
            'available': False,
            'reason': schema.region_unsupported_reason(client.region),
        }

    summaries = _collect_summaries(client, run, ANALYSIS_METRICS)
    if not summaries:
        return {
            'run_id': run_id,
            'available': False,
            'reason': (
                'No vended metric series found for this run. Vended metrics exist only '
                'for runs started after the feature launched; the manifest-based '
                'analysis above is the applicable source.'
            ),
        }

    signatures = [build_task_signature(task, summaries) for task in run.tasks]
    observed = [s for s in signatures if s.cpu_peak is not None or s.memory_peak_bytes is not None]

    category_counts: Dict[str, int] = {}
    for signature in observed:
        for category in signature.categories:
            category_counts[category] = category_counts.get(category, 0) + 1

    return {
        'run_id': run_id,
        'available': True,
        'storage_type': run.storage_type,
        'scratch_mode': run.scratch_mode,
        'tasks_observed': len(observed),
        'task_count': len(run.tasks),
        'category_counts': dict(sorted(category_counts.items())),
        'signatures': observed,
        'stuck_tasks': detect_stuck_tasks(client, run) if run.is_active else [],
        'right_sizing': right_size(run, observed, headroom),
        'missing_metrics': [{'metric': m.name, 'reason': m.reason} for m in run.presence.missing],
    }


def _format_bytes(value: Optional[float]) -> str:
    if value is None:
        return 'n/a'
    if value >= GIB:
        return f'{value / GIB:.2f} GiB'
    if value >= 1024**2:
        return f'{value / 1024**2:.1f} MiB'
    return f'{value:.0f} B'


def format_metrics_report_section(result: Dict[str, Any], max_tasks: int = 10) -> List[str]:
    """Format an analysis result as markdown report lines.

    Args:
        result: Output of :func:`analyze_run_metrics`.
        max_tasks: Cap on per-task signature lines (worst-first).
    """
    lines: List[str] = [f'## Vended Metrics Analysis (Run {result["run_id"]})', '']
    if not result.get('available'):
        lines.append(f'*{result["reason"]}*')
        lines.append('')
        return lines

    lines.append(f'- **Tasks with metrics**: {result["tasks_observed"]} of {result["task_count"]}')
    lines.append(f'- **Storage**: {result["storage_type"]} (scratch: {result["scratch_mode"]})')
    categories = ', '.join(f'{k}: {v}' for k, v in result['category_counts'].items())
    lines.append(f'- **Task categories**: {categories}')
    lines.append('')

    stuck = result.get('stuck_tasks') or []
    concerning = [s for s in stuck if s['verdict'] not in ('PROGRESSING',)]
    if stuck:
        lines.append('### Stuck-Run Check (active run)')
        lines.append(f'- {len(stuck)} RUNNING task(s) checked; {len(concerning)} need attention')
        for s in concerning[:max_tasks]:
            lines.append(
                f'- **{s["task_name"]}** ({s["task_id"]}): {s["verdict"]} — {s["evidence"]}'
            )
        lines.append('')

    interesting = [s for s in result['signatures'] if s.categories != ['BALANCED']]
    interesting.sort(key=lambda s: s.cpu_utilization if s.cpu_utilization is not None else 1.0)
    if interesting:
        lines.append('### Notable Task Signatures')
        for s in interesting[:max_tasks]:
            parts = [f'categories: {", ".join(s.categories)}']
            if s.cpu_utilization is not None:
                parts.append(f'cpu {s.cpu_utilization:.0%} of {s.cpu_limit:g} cores')
            if s.memory_utilization is not None:
                parts.append(
                    f'mem {s.memory_utilization:.0%} of {_format_bytes(s.memory_limit_bytes)}'
                )
            if s.gpu_peak_percent is not None:
                parts.append(f'gpu peak {s.gpu_peak_percent:.0f}%')
            if s.filesystem_rate_bytes_per_second:
                parts.append(f'fs io {_format_bytes(s.filesystem_rate_bytes_per_second)}/s')
            if s.scratch_peak_bytes is not None:
                parts.append(f'scratch peak {_format_bytes(s.scratch_peak_bytes)}')
            lines.append(f'- **{s.task_name}** ({s.task_id}): {"; ".join(parts)}')
        if len(interesting) > max_tasks:
            lines.append(f'- *...and {len(interesting) - max_tasks} more*')
        lines.append('')

    right_sizing = result.get('right_sizing') or []
    if right_sizing:
        lines.append('### Right-Sizing Suggestions (observed peak + headroom)')
        for r in right_sizing[:max_tasks]:
            parts = []
            if r.recommended_cpus is not None:
                parts.append(f'cpus {r.current_cpus} -> {r.recommended_cpus}')
            if r.recommended_memory_gib is not None:
                parts.append(f'memory {r.current_memory_gib} -> {r.recommended_memory_gib} GiB')
            if r.recommended_scratch_gib is not None:
                parts.append(f'scratch needs ~{r.recommended_scratch_gib} GiB')
            lines.append(f'- **{r.task_name}** (x{r.task_count}): {"; ".join(parts)}')
        if len(right_sizing) > max_tasks:
            lines.append(f'- *...and {len(right_sizing) - max_tasks} more*')
        lines.append('')

    missing = result.get('missing_metrics') or []
    if missing:
        lines.append('### Metrics Not Applicable to This Run')
        for m in missing:
            lines.append(f'- `{m["metric"]}`: {m["reason"]}')
        lines.append('')

    return lines


def metrics_section_for_report(
    run_id: str, region: Optional[str] = None, headroom: float = 0.2
) -> List[str]:
    """Analysis pass + formatting with a never-raise contract for report use."""
    try:
        result = analyze_run_metrics(run_id, region=region, headroom=headroom)
        return format_metrics_report_section(result)
    except Exception as e:  # never break the manifest-based report
        logger.warning(f'Vended metrics pass failed for run {run_id}: {e}')
        return [
            f'## Vended Metrics Analysis (Run {run_id})',
            '',
            f'*Vended metrics could not be analyzed: {e}. '
            'The manifest-based analysis above is unaffected.*',
            '',
        ]
