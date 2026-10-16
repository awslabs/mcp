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

"""Vended-metrics tools for the AWS HealthOmics MCP server.

These tools query the HealthOmics vended metrics (CloudWatch OTel metrics
delivered into the customer's account) through the CloudWatch PromQL API.
They complement the timeline/manifest based AnalyzeAHORunPerformance with
fine-grained resource utilization: CPU, memory, GPU, network, run-filesystem
I/O, and scratch storage.

All responses are structured JSON with explicit ``datapoint_count`` per series
and a ``missing_metrics`` list explaining absent data (per-mode presence rules,
feature availability), so agents can explain gaps instead of failing.
"""

import statistics
from awslabs.aws_healthomics_mcp_server.metrics import schema
from awslabs.aws_healthomics_mcp_server.metrics.client import (
    SeriesSummary,
    TimeSeries,
    VendedMetricsClient,
    query_metric_series,
    summarize_series,
)
from awslabs.aws_healthomics_mcp_server.metrics.run_context import (
    RunContext,
    resolve_run,
)
from awslabs.aws_healthomics_mcp_server.utils.aws_utils import get_omics_client
from awslabs.aws_healthomics_mcp_server.utils.error_utils import handle_tool_error
from datetime import datetime, timezone
from mcp.server.mcpserver import Context
from pydantic import Field
from typing import Any, Dict, List, Optional


MAX_TIMESERIES_POINTS = 200
"""Datapoints per series included in tool output; longer series are downsampled."""

DEFAULT_WORKFLOW_LOOKBACK_RUNS = 5

FEATURE_ABSENT_REASON = (
    'No vended metrics found for this run. Vended metrics exist only for runs '
    'started after the feature launched in the account/region; for older runs '
    'fall back to timeline/manifest analysis (AnalyzeAHORunPerformance). '
    'Delivery is at-least-once, not guaranteed, so isolated gaps are possible.'
)


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _default(value: Any) -> Any:
    """Resolve unresolved pydantic FieldInfo defaults (direct/test invocation)."""
    from pydantic.fields import FieldInfo

    return value.default if isinstance(value, FieldInfo) else value


def _absence_reason(run: RunContext, task_id: Optional[str] = None) -> str:
    """Best explanation for a metric that was expected but returned no series.

    Precedence: run predates the production launch > the queried task was too
    short to emit datapoints > generic at-least-once / feature-availability note.
    """
    if schema.predates_launch(run.start_time):
        return schema.launch_date_reason()
    if task_id:
        task = run.task_by_id.get(task_id)
        if (
            task
            and task.duration_seconds is not None
            and task.duration_seconds < schema.MIN_TASK_DURATION_SECONDS
        ):
            return schema.short_task_reason(task.duration_seconds)
    return 'No datapoints in the query window. ' + FEATURE_ABSENT_REASON


def _unsupported_region_result(client_region: str) -> Optional[Dict[str, Any]]:
    """A structured no-data response if the region has no vended metrics."""
    if schema.is_region_supported(client_region):
        return None
    return {
        'region': client_region,
        'vended_metrics_supported': False,
        'note': schema.region_unsupported_reason(client_region),
    }


def _iso(dt: Optional[datetime]) -> Optional[str]:
    return dt.isoformat() if dt else None


def _parse_time(value: Optional[str], name: str) -> Optional[datetime]:
    """Parse an ISO-8601 timestamp argument (None passes through)."""
    if value is None:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    except ValueError as e:
        raise ValueError(f'{name} must be an ISO-8601 timestamp: {e}') from e
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def _downsample(series: TimeSeries, max_points: int = MAX_TIMESERIES_POINTS) -> List[List[float]]:
    """Return [timestamp, value] pairs, evenly downsampled to max_points."""
    n = series.datapoint_count
    if n <= max_points:
        return [[t, v] for t, v in zip(series.timestamps, series.values)]
    stride = n / max_points
    indices = [int(i * stride) for i in range(max_points)]
    return [[series.timestamps[i], series.values[i]] for i in indices]


def _summary_dict(summary: SeriesSummary) -> Dict[str, Any]:
    result: Dict[str, Any] = {'datapoint_count': summary.datapoint_count}
    for key in ('minimum', 'maximum', 'average', 'last', 'total_delta', 'average_rate'):
        value = getattr(summary, key)
        if value is not None:
            result[key] = value
    return result


def _series_output(
    series: TimeSeries,
    metric: schema.VendedMetric,
    run: Optional[RunContext],
    include_timeseries: bool,
) -> Dict[str, Any]:
    """Shape one PromQL series for tool output, resolving task identity."""
    task_id = series.labels.get(schema.TASK_ID_LABEL)
    output: Dict[str, Any] = {
        'summary': _summary_dict(summarize_series(series, metric.is_counter)),
    }
    if task_id:
        output['task_id'] = task_id
        if run is not None:
            task = run.task_by_id.get(task_id)
            if task:
                output['task_name'] = task.name
    for attr in metric.datapoint_attributes:
        if attr in series.labels:
            output[attr] = series.labels[attr]
    if include_timeseries:
        output['values'] = _downsample(series)
    return output


def _run_config(run: RunContext) -> Dict[str, Any]:
    return {
        'run_id': run.run_id,
        'workflow_id': run.workflow_id,
        'status': run.status,
        'storage_type': run.storage_type,
        'scratch_storage_mode': run.scratch_mode,
        'has_gpu_tasks': run.has_gpu_tasks,
        'task_count': len(run.tasks),
        'start_time': _iso(run.start_time),
        'stop_time': _iso(run.stop_time),
    }


def _presence_notes(run: RunContext) -> List[Dict[str, str]]:
    """Expected-absent metrics for the run's configuration, with reasons."""
    return [{'metric': m.name, 'reason': m.reason} for m in run.presence.missing]


def _resolve_metric_names(
    metric_names: Optional[List[str]], run: Optional[RunContext]
) -> List[schema.VendedMetric]:
    """Validate requested names against the schema (or default to expected-present)."""
    if metric_names:
        return [schema.metric_of(name) for name in metric_names]
    if run is not None:
        return [schema.metric_of(name) for name in run.presence.present]
    return list(schema.ALL_METRICS)


# ---------------------------------------------------------------------------
# ListAHORunMetrics
# ---------------------------------------------------------------------------


async def list_run_metrics(
    ctx: Context,
    run_id: str = Field(..., description='ID of the run to inspect'),
    aws_profile: Optional[str] = Field(
        None,
        description='AWS profile name for this operation. Overrides the default credential chain.',
    ),
    aws_region: Optional[str] = Field(
        None,
        description='AWS region for this operation. Overrides the server default.',
    ),
) -> Dict[str, Any]:
    """List which vended metric series actually exist for a HealthOmics run.

    Use this first when answering metrics questions: it reports which metrics
    have data (and for how many tasks), which are expected to be absent for the
    run's storage/scratch/GPU configuration (with reasons), and whether the run
    appears to predate vended-metrics availability.

    Returns:
        Dictionary with run configuration, available metrics (per-task series
        counts), and missing metrics with reasons.
    """
    try:
        aws_profile = _default(aws_profile)
        aws_region = _default(aws_region)
        run = resolve_run(run_id, region=aws_region, profile=aws_profile)
        client = VendedMetricsClient(region=aws_region, profile=aws_profile)
        unsupported = _unsupported_region_result(client.region)
        if unsupported:
            unsupported['run'] = _run_config(run)
            unsupported['vended_metrics_found'] = False
            return unsupported
        start, end = run.query_window()

        matches = [schema.build_selector(name, run_id=run_id) for name in schema.ALL_METRIC_NAMES]
        found = client.series(matches, start, end)

        by_metric: Dict[str, set] = {}
        for labels in found:
            name = labels.get(schema.METRIC_NAME_LABEL)
            if name:
                by_metric.setdefault(name, set()).add(labels.get(schema.TASK_ID_LABEL))

        predates_launch = schema.predates_launch(run.start_time)
        unexpected_absence_reason = (
            schema.launch_date_reason() if predates_launch else FEATURE_ABSENT_REASON
        )
        expected_absent = {m.name: m.reason for m in run.presence.missing}
        available = []
        missing = []
        for name in schema.ALL_METRIC_NAMES:
            metric = schema.metric_of(name)
            if name in by_metric:
                task_ids = {t for t in by_metric[name] if t}
                entry: Dict[str, Any] = {
                    'metric': name,
                    'unit': metric.unit,
                    'is_counter': metric.is_counter,
                    'per_task': schema.is_per_task(name),
                }
                if schema.is_per_task(name):
                    entry['tasks_with_data'] = len(task_ids)
                if metric.sampling_interval_seconds != schema.DEFAULT_SAMPLING_INTERVAL_SECONDS:
                    entry['sampling_interval_seconds'] = metric.sampling_interval_seconds
                available.append(entry)
            elif name in expected_absent:
                missing.append({'metric': name, 'reason': expected_absent[name]})
            else:
                missing.append(
                    {
                        'metric': name,
                        'reason': 'Expected for this run configuration but no series found. '
                        + unexpected_absence_reason,
                    }
                )

        result: Dict[str, Any] = {
            'run': _run_config(run),
            'query_window': {'start': _iso(start), 'end': _iso(end)},
            'vended_metrics_found': bool(available),
            'available_metrics': available,
            'missing_metrics': missing,
        }
        if not available:
            result['note'] = unexpected_absence_reason
        if run.storage_type == schema.StorageType.DYNAMIC.value:
            result.setdefault('caveats', []).append(
                'DYNAMIC (EFS) run-filesystem usage lags ~35 minutes behind real time.'
            )
        if run.is_active:
            result.setdefault('caveats', []).append(
                'Run is still active; recent datapoints may not be ingested yet (~2 min lag).'
            )
        short_tasks = [
            t
            for t in run.tasks
            if t.duration_seconds is not None
            and t.duration_seconds < schema.MIN_TASK_DURATION_SECONDS
        ]
        if short_tasks:
            result.setdefault('caveats', []).append(
                f'{len(short_tasks)} task(s) ran shorter than '
                f'{schema.MIN_TASK_DURATION_SECONDS}s and may have produced no metric '
                f'datapoints (~{schema.DEFAULT_SAMPLING_INTERVAL_SECONDS}s sampling cadence).'
            )
        if any(
            m['metric'] == 'aws.omics.task.filesystem.scratch.storage.usage' for m in available
        ):
            result.setdefault('caveats', []).append(
                'aws.omics.task.filesystem.scratch.storage.usage is sampled every ~20 minutes '
                '(measuring it walks the filesystem); tasks shorter than that may have no '
                'scratch datapoints and short-lived peaks can be missed.'
            )
        return result
    except Exception as e:
        return await handle_tool_error(ctx, e, f'Error listing run metrics for run {run_id}')


# ---------------------------------------------------------------------------
# GetAHORunMetrics
# ---------------------------------------------------------------------------


async def get_run_metrics(
    ctx: Context,
    run_id: str = Field(..., description='ID of the run to query'),
    metric_names: Optional[List[str]] = Field(
        None,
        description=(
            'Vended metric names to retrieve (e.g. "aws.omics.task.cpu.usage"). '
            'Defaults to all metrics expected for the run configuration. '
            'Use ListAHORunMetrics to discover valid, available names.'
        ),
    ),
    task_id: Optional[str] = Field(
        None, description='Restrict to one task (per-task metrics only)'
    ),
    direction: Optional[str] = Field(
        None,
        description=(
            'For I/O metrics: filter by direction '
            '("read"/"write" for filesystem, "receive"/"transmit" for network)'
        ),
    ),
    start_time: Optional[str] = Field(
        None,
        description='ISO-8601 window start (defaults to the run start minus buffer)',
    ),
    end_time: Optional[str] = Field(
        None, description='ISO-8601 window end (defaults to the run stop plus buffer, or now)'
    ),
    step_seconds: Optional[int] = Field(
        None, description='Sample step in seconds (default 60; widened for long windows)'
    ),
    include_timeseries: bool = Field(
        True,
        description=(
            'Include (downsampled) timestamped values per series for graphing/trending; '
            'set false for summaries only'
        ),
    ),
    aws_profile: Optional[str] = Field(
        None,
        description='AWS profile name for this operation. Overrides the default credential chain.',
    ),
    aws_region: Optional[str] = Field(
        None,
        description='AWS region for this operation. Overrides the server default.',
    ),
) -> Dict[str, Any]:
    """Retrieve vended metric time series and summary statistics for a run.

    Powers point queries ("what is the DataReadThroughput for run X"), metric
    math ("which task has the highest write throughput"), storage-type
    filtering, trending, and graphing. Counters (network/filesystem I/O) report
    ``total_delta`` (bytes/operations over the window) and ``average_rate``
    (per second); gauges report min/max/average/last.

    Returns:
        Dictionary with per-metric series (task identity resolved to names),
        summary statistics, and missing-metric explanations.
    """
    try:
        aws_profile = _default(aws_profile)
        aws_region = _default(aws_region)
        metric_names = _default(metric_names)
        task_id = _default(task_id)
        direction = _default(direction)
        start_time = _default(start_time)
        end_time = _default(end_time)
        step_seconds = _default(step_seconds)
        include_timeseries = _default(include_timeseries)

        run = resolve_run(run_id, region=aws_region, profile=aws_profile)
        metrics = _resolve_metric_names(metric_names, run)

        window_start, window_end = run.query_window()
        explicit_start = _parse_time(start_time, 'start_time')
        explicit_end = _parse_time(end_time, 'end_time')
        start = explicit_start or window_start
        end = explicit_end or window_end

        client = VendedMetricsClient(region=aws_region, profile=aws_profile)
        unsupported = _unsupported_region_result(client.region)
        if unsupported:
            unsupported['run'] = _run_config(run)
            unsupported['metrics'] = []
            unsupported['missing_metrics'] = [
                {'metric': m.name, 'reason': schema.region_unsupported_reason(client.region)}
                for m in metrics
            ]
            return unsupported
        expected_absent = {m.name: m.reason for m in run.presence.missing}

        results: List[Dict[str, Any]] = []
        missing: List[Dict[str, str]] = []
        for metric in metrics:
            extra_labels: Dict[str, str] = {}
            if direction:
                direction_attrs = [
                    a for a in metric.datapoint_attributes if a.endswith('.direction')
                ]
                if direction_attrs:
                    extra_labels[direction_attrs[0]] = direction

            series_list, truncated = query_metric_series(
                client,
                metric.name,
                start,
                end,
                step_seconds,
                run_id=run_id,
                task_id=task_id if schema.is_per_task(metric.name) else None,
                extra_labels=extra_labels or None,
            )

            if not series_list:
                reason = expected_absent.get(metric.name) or _absence_reason(run, task_id)
                missing.append({'metric': metric.name, 'reason': reason})
                continue

            entry: Dict[str, Any] = {
                'metric': metric.name,
                'unit': metric.unit,
                'is_counter': metric.is_counter,
                'per_task': schema.is_per_task(metric.name),
                'series': [
                    _series_output(s, metric, run, include_timeseries) for s in series_list
                ],
            }
            if metric.sampling_interval_seconds != schema.DEFAULT_SAMPLING_INTERVAL_SECONDS:
                entry['sampling_interval_seconds'] = metric.sampling_interval_seconds
            if truncated:
                entry['possibly_truncated'] = True
                entry['truncation_note'] = (
                    'The query hit the CloudWatch PromQL per-query series cap; some '
                    'task series may be missing and aggregations may undercount. '
                    'Narrow the query with task_id or direction filters.'
                )
            results.append(entry)

        return {
            'run': _run_config(run),
            'query_window': {'start': _iso(start), 'end': _iso(end)},
            'metrics': results,
            'missing_metrics': missing,
        }
    except Exception as e:
        return await handle_tool_error(ctx, e, f'Error getting run metrics for run {run_id}')


# ---------------------------------------------------------------------------
# CompareAHORunMetrics
# ---------------------------------------------------------------------------


def _peak_value(summary: SeriesSummary, is_counter: bool) -> Optional[float]:
    """The comparison value for a series: window delta for counters, max for gauges."""
    return summary.total_delta if is_counter else summary.maximum


def _relative_delta(a: Optional[float], b: Optional[float]) -> Optional[float]:
    if a is None or b is None:
        return None
    baseline = max(abs(a), abs(b))
    if baseline == 0:
        return 0.0
    return (b - a) / baseline


def compare_task_metrics(
    run_a: RunContext,
    run_b: RunContext,
    metrics_a: Dict[str, Dict[str, SeriesSummary]],
    metrics_b: Dict[str, Dict[str, SeriesSummary]],
) -> List[Dict[str, Any]]:
    """Align two runs' tasks by name and diff durations and metric signatures.

    Args:
        run_a: First run context.
        run_b: Second run context.
        metrics_a: metric name -> task_id -> summary, for run A.
        metrics_b: Same for run B.

    Returns:
        Per-task-name comparison entries sorted by absolute duration delta,
        each with the metric deltas that distinguish the two runs.
    """
    names = sorted(set(run_a.task_ids_by_name) | set(run_b.task_ids_by_name))
    comparisons: List[Dict[str, Any]] = []

    for name in names:
        ids_a = run_a.task_ids_by_name.get(name, [])
        ids_b = run_b.task_ids_by_name.get(name, [])

        durations_a = [
            d for tid in ids_a if (d := run_a.task_by_id[tid].duration_seconds) is not None
        ]
        durations_b = [
            d for tid in ids_b if (d := run_b.task_by_id[tid].duration_seconds) is not None
        ]
        duration_a = max(durations_a) if durations_a else None
        duration_b = max(durations_b) if durations_b else None

        metric_deltas: List[Dict[str, Any]] = []
        for metric_name in set(metrics_a) | set(metrics_b):
            metric = schema.metric_of(metric_name)
            values_a = [
                v
                for tid in ids_a
                if (summary := metrics_a.get(metric_name, {}).get(tid))
                and (v := _peak_value(summary, metric.is_counter)) is not None
            ]
            values_b = [
                v
                for tid in ids_b
                if (summary := metrics_b.get(metric_name, {}).get(tid))
                and (v := _peak_value(summary, metric.is_counter)) is not None
            ]
            value_a = max(values_a) if values_a else None
            value_b = max(values_b) if values_b else None
            if value_a is None and value_b is None:
                continue
            metric_deltas.append(
                {
                    'metric': metric_name,
                    'unit': metric.unit,
                    'run_a': value_a,
                    'run_b': value_b,
                    'relative_delta': _relative_delta(value_a, value_b),
                }
            )

        metric_deltas.sort(
            key=lambda d: abs(d['relative_delta']) if d['relative_delta'] is not None else 0,
            reverse=True,
        )

        entry: Dict[str, Any] = {
            'task_name': name,
            'run_a': {'task_count': len(ids_a), 'max_duration_seconds': duration_a},
            'run_b': {'task_count': len(ids_b), 'max_duration_seconds': duration_b},
            'metric_deltas': metric_deltas[:5],
        }
        if duration_a is not None and duration_b is not None:
            entry['duration_delta_seconds'] = duration_b - duration_a
        if not ids_a:
            entry['note'] = 'Task only present in run B'
        elif not ids_b:
            entry['note'] = 'Task only present in run A'
        comparisons.append(entry)

    comparisons.sort(
        key=lambda c: abs(c.get('duration_delta_seconds', 0) or 0),
        reverse=True,
    )
    return comparisons


def _collect_task_summaries(
    client: VendedMetricsClient,
    run: RunContext,
    metric_names: List[str],
) -> Dict[str, Dict[str, SeriesSummary]]:
    """Query one run's per-task summaries: metric name -> task_id -> summary."""
    start, end = run.query_window()
    result: Dict[str, Dict[str, SeriesSummary]] = {}
    for name in metric_names:
        if not schema.is_per_task(name):
            continue
        metric = schema.metric_of(name)
        series_list, _ = query_metric_series(client, name, start, end, run_id=run.run_id)
        by_task: Dict[str, SeriesSummary] = {}
        for series in series_list:
            task_id = series.labels.get(schema.TASK_ID_LABEL)
            if not task_id:
                continue
            summary = summarize_series(series, metric.is_counter)
            existing = by_task.get(task_id)
            # Multiple series per task (directions, gpu ids): keep the peak.
            if existing is None or (
                (_peak_value(summary, metric.is_counter) or 0)
                > (_peak_value(existing, metric.is_counter) or 0)
            ):
                by_task[task_id] = summary
        if by_task:
            result[name] = by_task
    return result


async def compare_run_metrics(
    ctx: Context,
    run_id_a: str = Field(..., description='First (baseline) run ID'),
    run_id_b: str = Field(..., description='Second run ID to compare against the baseline'),
    metric_names: Optional[List[str]] = Field(
        None,
        description='Vended metric names to compare (defaults to all per-task metrics)',
    ),
    aws_profile: Optional[str] = Field(
        None,
        description='AWS profile name for this operation. Overrides the default credential chain.',
    ),
    aws_region: Optional[str] = Field(
        None,
        description='AWS region for this operation. Overrides the server default.',
    ),
) -> Dict[str, Any]:
    """Compare two runs' vended metrics, aligned by task name.

    Answers "why did one run take longer than the other": tasks are aligned by
    name across the runs, wall-clock durations are diffed, and for each task
    the metrics with the largest relative deltas (peak for gauges, window total
    for counters) are reported as the task's changed signature.

    Caveat: for workflows with scattered tasks, the scatter index embedded in
    the task name is not deterministic across runs — the same index may have
    processed different shard data in each run. Name-based alignment can
    therefore pair scattered tasks that did different work; treat per-task
    deltas for scattered task names as indicative rather than a like-for-like
    comparison. (Scattered tasks that share an identical name are aggregated:
    max duration, peak metric value.)

    Returns:
        Dictionary with both run configurations, the wall-clock delta, and
        per-task comparisons sorted by duration impact.
    """
    try:
        aws_profile = _default(aws_profile)
        aws_region = _default(aws_region)
        metric_names = _default(metric_names)
        run_a = resolve_run(run_id_a, region=aws_region, profile=aws_profile)
        run_b = resolve_run(run_id_b, region=aws_region, profile=aws_profile)
        client = VendedMetricsClient(region=aws_region, profile=aws_profile)
        unsupported = _unsupported_region_result(client.region)
        if unsupported:
            unsupported['run_a'] = _run_config(run_a)
            unsupported['run_b'] = _run_config(run_b)
            unsupported['task_comparisons'] = []
            return unsupported

        names = [m.name for m in _resolve_metric_names(metric_names, None)]
        per_task_names = [n for n in names if schema.is_per_task(n)]

        metrics_a = _collect_task_summaries(client, run_a, per_task_names)
        metrics_b = _collect_task_summaries(client, run_b, per_task_names)

        result: Dict[str, Any] = {
            'run_a': _run_config(run_a),
            'run_b': _run_config(run_b),
            'task_comparisons': compare_task_metrics(run_a, run_b, metrics_a, metrics_b),
        }

        duration_a = (
            (run_a.stop_time - run_a.start_time).total_seconds()
            if run_a.start_time and run_a.stop_time
            else None
        )
        duration_b = (
            (run_b.stop_time - run_b.start_time).total_seconds()
            if run_b.start_time and run_b.stop_time
            else None
        )
        if duration_a is not None and duration_b is not None:
            result['wall_clock'] = {
                'run_a_seconds': duration_a,
                'run_b_seconds': duration_b,
                'delta_seconds': duration_b - duration_a,
            }

        if not metrics_a and not metrics_b:
            result['note'] = FEATURE_ABSENT_REASON
        elif not metrics_a:
            result['note'] = f'No vended metrics found for run {run_id_a}. ' + (
                FEATURE_ABSENT_REASON
            )
        elif not metrics_b:
            result['note'] = f'No vended metrics found for run {run_id_b}. ' + (
                FEATURE_ABSENT_REASON
            )
        return result
    except Exception as e:
        return await handle_tool_error(
            ctx, e, f'Error comparing run metrics for runs {run_id_a} and {run_id_b}'
        )


# ---------------------------------------------------------------------------
# GetAHOWorkflowMetrics
# ---------------------------------------------------------------------------

# Metric families aggregated for workflow-level distributions & right-sizing.
WORKFLOW_AGGREGATE_METRICS = [
    'aws.omics.task.cpu.usage',
    'aws.omics.task.memory.usage',
    'aws.omics.task.gpu.utilization',
    'aws.omics.task.filesystem.scratch.storage.usage',
]


def _percentile(values: List[float], fraction: float) -> float:
    """Nearest-rank percentile of a non-empty list."""
    ordered = sorted(values)
    index = min(int(len(ordered) * fraction), len(ordered) - 1)
    return ordered[index]


def aggregate_workflow_metrics(
    runs: List[RunContext],
    summaries_by_run: Dict[str, Dict[str, Dict[str, SeriesSummary]]],
) -> Dict[str, Any]:
    """Aggregate per-run task summaries into per-task-name distributions.

    Args:
        runs: The resolved runs included in the aggregation.
        summaries_by_run: run_id -> (metric name -> task_id -> summary).

    Returns:
        Per-task-name distributions: for each metric, p50/p90/max of the
        per-task peak values across all runs, plus duration distributions.
    """
    # task name -> metric name -> list of peak values across runs/tasks
    peaks: Dict[str, Dict[str, List[float]]] = {}
    durations: Dict[str, List[float]] = {}

    for run in runs:
        run_summaries = summaries_by_run.get(run.run_id, {})
        for task in run.tasks:
            if task.duration_seconds is not None:
                durations.setdefault(task.name, []).append(task.duration_seconds)
            for metric_name, by_task in run_summaries.items():
                summary = by_task.get(task.task_id)
                if summary is None:
                    continue
                metric = schema.metric_of(metric_name)
                value = _peak_value(summary, metric.is_counter)
                if value is not None:
                    peaks.setdefault(task.name, {}).setdefault(metric_name, []).append(value)

    task_names = sorted(set(durations) | set(peaks))
    result = []
    for name in task_names:
        entry: Dict[str, Any] = {'task_name': name}
        if name in durations:
            values = durations[name]
            entry['duration_seconds'] = {
                'p50': _percentile(values, 0.50),
                'p90': _percentile(values, 0.90),
                'max': max(values),
                'samples': len(values),
            }
            if len(values) >= 2:
                mean = statistics.mean(values)
                if mean > 0:
                    entry['duration_seconds']['coefficient_of_variation'] = (
                        statistics.pstdev(values) / mean
                    )
        for metric_name, values in sorted(peaks.get(name, {}).items()):
            entry.setdefault('metrics', {})[metric_name] = {
                'unit': schema.metric_of(metric_name).unit,
                'p50': _percentile(values, 0.50),
                'p90': _percentile(values, 0.90),
                'max': max(values),
                'samples': len(values),
            }
        result.append(entry)

    return {'task_distributions': result, 'runs_aggregated': len(runs)}


async def get_workflow_metrics(
    ctx: Context,
    workflow_id: str = Field(..., description='ID of the workflow to aggregate metrics for'),
    max_runs: int = Field(
        DEFAULT_WORKFLOW_LOOKBACK_RUNS,
        description='Maximum number of recent completed runs to aggregate (default 5)',
        ge=1,
        le=20,
    ),
    aws_profile: Optional[str] = Field(
        None,
        description='AWS profile name for this operation. Overrides the default credential chain.',
    ),
    aws_region: Optional[str] = Field(
        None,
        description='AWS region for this operation. Overrides the server default.',
    ),
) -> Dict[str, Any]:
    """Aggregate vended metrics across a workflow's recent completed runs.

    Produces per-task-name distributions (p50/p90/max across runs) of task
    durations, peak CPU/memory/GPU usage, and peak scratch-storage usage. This
    is the data source for right-sizing recommendations ("what local disk
    should I set", "am I over-provisioned") and cross-run regression checks
    (high duration variance is flagged via coefficient_of_variation).

    Caveat: for workflows with scattered tasks, the scatter index embedded in
    the task name is not deterministic across runs, so samples aggregated
    under one scattered task name may come from different shard data in each
    run. Such distributions describe arbitrary shards of the scatter, not a
    consistent one; for right-sizing a scattered task, use the maximum across
    all of its shards' entries.

    Returns:
        Dictionary with the aggregated per-task distributions and the list of
        runs included.
    """
    try:
        aws_profile = _default(aws_profile)
        aws_region = _default(aws_region)
        max_runs = _default(max_runs)
        client = get_omics_client(region_name=aws_region, profile_name=aws_profile)

        run_ids: List[str] = []
        next_token: Optional[str] = None
        while len(run_ids) < max_runs:
            kwargs: Dict[str, Any] = {'maxResults': 100, 'status': 'COMPLETED'}
            if next_token:
                kwargs['startingToken'] = next_token
            response = client.list_runs(**kwargs)
            for item in response.get('items', []):
                if item.get('workflowId') == workflow_id:
                    run_ids.append(item['id'])
                    if len(run_ids) >= max_runs:
                        break
            next_token = response.get('nextToken')
            if not next_token:
                break

        if not run_ids:
            return {
                'workflow_id': workflow_id,
                'runs_aggregated': 0,
                'note': f'No completed runs found for workflow {workflow_id}.',
            }

        metrics_client = VendedMetricsClient(region=aws_region, profile=aws_profile)
        unsupported = _unsupported_region_result(metrics_client.region)
        if unsupported:
            unsupported['workflow_id'] = workflow_id
            unsupported['run_ids'] = run_ids
            unsupported['runs_aggregated'] = 0
            return unsupported
        runs: List[RunContext] = []
        summaries_by_run: Dict[str, Dict[str, Dict[str, SeriesSummary]]] = {}
        for run_id in run_ids:
            run = resolve_run(run_id, region=aws_region, profile=aws_profile)
            runs.append(run)
            summaries_by_run[run_id] = _collect_task_summaries(
                metrics_client, run, WORKFLOW_AGGREGATE_METRICS
            )

        result = aggregate_workflow_metrics(runs, summaries_by_run)
        result['workflow_id'] = workflow_id
        result['run_ids'] = run_ids
        runs_without_metrics = [run_id for run_id in run_ids if not summaries_by_run.get(run_id)]
        if runs_without_metrics:
            result['runs_without_vended_metrics'] = runs_without_metrics
            result['note'] = FEATURE_ABSENT_REASON
        return result
    except Exception as e:
        return await handle_tool_error(
            ctx, e, f'Error aggregating workflow metrics for workflow {workflow_id}'
        )
