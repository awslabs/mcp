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

"""ServiceEvents data tool handlers (function, endpoint, incident, deployment telemetry)."""

import asyncio
import concurrent.futures
import logging
from . import cw_logs, function_metrics, state
from .cw_logs import CwLogsQueryError
from .formatting import render_incident_call_tree
from .promql_client import PromQLQueryError
from datetime import datetime, timedelta, timezone
from typing import Optional


logger = logging.getLogger(__name__)


# =============================================================================
# Function Telemetry Tools
# =============================================================================


def list_functions(
    hours: int = 24,
    filter: Optional[str] = None,
    threshold_ms: float = 100.0,
    top: int = 20,
    sort_by: str = 'calls',
    endpoint: Optional[str] = None,
    service_name: Optional[str] = None,
    environment: Optional[str] = None,
) -> dict:
    """List instrumented functions with runtime metrics, with filtering and limiting.

    This is the primary discovery tool for functions. Use filters to narrow down:
    - No filter: Top functions by call count (default)
    - filter="errors": Only functions that have recorded errors
    - filter="slow": Only functions with avg duration > threshold_ms

    **Data source:** CloudWatch Metrics V2 (`service.function.duration` native
    histogram) via PromQL. Metrics are **average duration** and **call/error
    counts** only — percentiles (p50/p99) and file paths are NOT available from
    this source (see plan_006). `sort_by="duration"` ranks by *average* duration.

    **Output is limited to `top` results to avoid large responses.**

    Args:
        hours: Time range to query in hours (default 24).
        filter: Optional filter - "errors" (with errors), "slow" (avg above threshold), or None (all).
        threshold_ms: Average-duration threshold in ms when filter="slow" (default 100ms).
        top: Maximum number of functions to return (default 20).
        sort_by: Sort order - "calls" (most called), "duration" (slowest by average), "errors" (most errors).
        endpoint: Filter to functions that executed under a specific endpoint/operation
            (e.g., "POST /checkout"). Exact match on the metric's `operation` label.
            Use get_endpoint_performance to discover operation names. Optional.
        service_name: Service name to query. Optional — from user prompt or prior tool output.
        environment: Environment name. Optional — from user prompt or prior tool output.

    Returns:
        Dict with a limited list of functions, each with name, line, calls,
        avg_duration_ms, and errors.
    """
    logger.debug(
        f'list_functions called: hours={hours}, filter={filter}, sort_by={sort_by}, '
        f'top={top}, endpoint={endpoint}, service_name={service_name}, environment={environment}'
    )

    try:
        records = function_metrics.fetch_function_records(
            service_name=service_name,
            environment=environment,
            hours=hours,
            operation=endpoint,
        )
    except PromQLQueryError as e:
        logger.error(f'Functions PromQL error: {e}')
        return {
            'total_functions': 0,
            'returned': 0,
            'filter': filter,
            'sort_by': sort_by,
            'time_range_hours': hours,
            'error': str(e),
            'functions': [],
        }

    # Apply filters (client-side; the metric source has no server-side filter API).
    if filter == 'errors':
        records = [r for r in records if r.get('errors', 0) > 0]
    elif filter == 'slow':
        records = [r for r in records if (r.get('avg_duration_ms') or 0) > threshold_ms]

    total = len(records)
    formatted = function_metrics.sort_and_limit(records, sort_by, top)

    result = {
        'total_functions': total,
        'returned': len(formatted),
        'filter': filter,
        'sort_by': sort_by,
        'time_range_hours': hours,
        'functions': formatted,
        'data_source': 'cloudwatch_metrics_v2',
    }

    if endpoint:
        result['endpoint_filter'] = endpoint

    logger.debug(
        f'list_functions returning {result["returned"]}/{result["total_functions"]} functions'
    )
    return result


async def get_function_details(
    function_name: str,
    hours: int = 24,
    include_exceptions: bool = False,
    service_name: Optional[str] = None,
    environment: Optional[str] = None,
    endpoint: Optional[str] = None,
) -> dict:
    """Get detailed metrics for a specific function.

    **Data source:** CloudWatch Metrics V2 (`service.function.duration`) via PromQL.
    Available stats are **average duration** and **call/error counts** only.
    Percentiles (p50/p99), file path, and min/max duration are NOT available from
    this source (see plan_006 Gaps G1–G3).

    Args:
        function_name: The fully qualified function name (e.g., "module.function_name"),
            from list_functions. Matched exactly against the `function.name` label.
        hours: Time range to query in hours (default 24).
        include_exceptions: When True, also fetches recent incidents for the service
            (from CloudWatch Logs) and returns them as `related_incidents`. Default False.
        service_name: Service name to query. Optional — from user prompt or prior tool output.
        environment: Environment name. Optional — from user prompt or prior tool output.
        endpoint: Scope the function's metrics to a specific endpoint/operation
            (e.g., "POST /checkout"). Exact match on the metric's `operation` label.
            Optional — when omitted, metrics are aggregated across all endpoints.

    Returns:
        Function metrics: name, line, total_calls, avg_duration_ms, total_errors,
        and related_incidents (only when include_exceptions=True).
    """
    logger.debug(
        'get_function_details called: function_name=%s, hours=%s, include_exceptions=%s, endpoint=%s',
        function_name,
        hours,
        include_exceptions,
        endpoint,
    )

    def _fetch_records():
        try:
            return function_metrics.fetch_function_records(
                service_name=service_name,
                environment=environment,
                hours=hours,
                function_name=function_name,
                operation=endpoint,
            )
        except PromQLQueryError as e:
            logger.debug(f'Functions PromQL error: {e}')
            return None

    def _fetch_incidents():
        try:
            return cw_logs.query_incidents(
                service_name=service_name, hours=hours, endpoint=endpoint, limit=20
            )
        except CwLogsQueryError as e:
            logger.warning(f'Failed to fetch related incidents: {e}')
            return None

    if include_exceptions:
        records, inc_response = await asyncio.gather(
            asyncio.to_thread(_fetch_records),
            asyncio.to_thread(_fetch_incidents),
        )
    else:
        records = await asyncio.to_thread(_fetch_records)
        inc_response = None

    if records is None:
        return {'function_name': function_name, 'error': 'Functions metrics query failed'}
    if not records:
        return {'function_name': function_name, 'error': 'Function not found in metrics'}

    # Exact match preferred; fall back to first record.
    rec = next((r for r in records if r['name'] == function_name), records[0])

    details = {
        'name': rec['name'],
        'line': rec.get('line', 0),
        'total_calls': rec.get('calls', 0),
        'avg_duration_ms': rec.get('avg_duration_ms'),
        'total_errors': rec.get('errors', 0),
    }

    if endpoint:
        details['endpoint_filter'] = endpoint

    # Related incidents from CloudWatch Logs (independent of metrics). When an
    # endpoint is given, the incident query is scoped to that operation as well.
    if inc_response is not None:
        related = []
        for inc in inc_response[:5]:
            attrs = inc.get('attributes') or {}
            related.append(
                {
                    'snapshot_id': attrs.get('aws.service_events.snapshot_id'),
                    'operation': attrs.get('aws.service_events.operation'),
                    'trigger_type': attrs.get('aws.service_events.trigger_type'),
                    'duration_ms': attrs.get('aws.service_events.duration_ms'),
                }
            )
        details['related_incidents'] = related

    details['time_range_hours'] = hours
    details['data_source'] = 'cloudwatch_metrics_v2'
    logger.debug(
        f'get_function_details returning: {details.get("name", "unknown")}, '
        f'calls={details.get("total_calls", 0)}, errors={details.get("total_errors", 0)}'
    )
    return details


def search_functions(
    query: str,
    limit: int = 20,
    service_name: Optional[str] = None,
    environment: Optional[str] = None,
    endpoint: Optional[str] = None,
) -> dict:
    """Search for functions by name.

    **Data source:** CloudWatch Metrics V2 — matches against the `function.name`
    label values of `service.function.duration`. (File-path search is not available;
    the metric carries no file label — plan_006 Gap G2.)

    **Output is limited to avoid large responses.**

    Args:
        query: Search string (case-insensitive substring match on function name).
        limit: Maximum number of results to return (default 20).
        service_name: Service name to query. Optional — from user prompt or prior tool output.
        environment: Environment name. Optional — from user prompt or prior tool output.
        endpoint: Scope the search to functions that executed under a specific
            endpoint/operation (e.g., "POST /checkout"). Exact match on the metric's
            `operation` label. Optional.

    Returns:
        Limited list of functions whose name contains the query string.
    """
    logger.debug(
        f'search_functions called: query={query}, limit={limit}, '
        f'endpoint={endpoint}, service_name={service_name}'
    )

    try:
        names = function_metrics.search_function_names(
            query=query,
            service_name=service_name,
            limit=limit,
            operation=endpoint,
        )
    except PromQLQueryError as e:
        return {
            'query': query,
            'total_matches': 0,
            'returned': 0,
            'functions': [],
            'error': str(e),
        }

    formatted = [{'name': name} for name in names]
    result = {
        'query': query,
        'total_matches': len(formatted),
        'returned': len(formatted),
        'functions': formatted,
        'data_source': 'cloudwatch_metrics_v2',
    }
    if endpoint:
        result['endpoint_filter'] = endpoint
    logger.debug(f'search_functions returning {len(formatted)} matches')
    return result


# =============================================================================
# Endpoint Telemetry Tools
# =============================================================================


async def get_endpoints(
    hours: int = 24,
    operation: Optional[str] = None,
    limit: int = 20,
    service_name: Optional[str] = None,
    environment: Optional[str] = None,
    percentile: float = 99,
) -> dict:
    """Get summaries for HTTP endpoints with optional filtering.

    **Data sources (mutually exclusive):**
    - When **Application Signals is enabled** for the application, endpoint
      telemetry is not emitted to CloudWatch Logs; per-operation RED metrics
      (Requests, Errors, Faults, latency) are read from Application Signals.
      `data_source` is `"application_signals"`.
    - Otherwise, endpoint summaries are read from the ServiceEvents
      `endpoint_summary` records in CloudWatch Logs. `data_source` is `"service_events"`.

    **Two modes:**
    - **List mode** (default): Returns endpoint summaries with request counts,
      fault/error counts, incident counts (CW-logs source only), average duration,
      and percentile duration. Each endpoint includes `total_faults` (5xx),
      `total_errors` (4xx), `avg_duration_ms`, and `p{N}_duration_ms`.
      Use `operation` to filter by operation substring.
    - **Detail mode** (when `operation` matches exactly one endpoint): Returns that
      endpoint with its error breakdown (CW-logs source only).

    **Output is limited to avoid large responses.** Use `operation` parameter
    to filter to a specific API if you know the operation name.

    Args:
        hours: Time range to query in hours (default 24).
        operation: Filter by operation name (e.g., "POST /api/users"). Substring match. Optional.
            When exactly one endpoint matches, detail mode is returned.
        limit: Maximum number of endpoints to return (default 20).
        service_name: Service name to query. Optional — from user prompt or prior tool output.
            Required to query Application Signals; the CW-logs source scans all services when omitted.
        environment: Environment name. Optional — from user prompt or prior tool output.
        percentile: Percentile to compute for duration (default 99). E.g., 99 for p99, 50 for p50.
            The result appears as `p{N}_duration_ms` in each endpoint entry.

    Returns:
        Dict with total endpoints count and limited list of endpoint summaries
        (including `p{N}_duration_ms`), or a single endpoint when one matches.
        Includes a `data_source` field indicating which backend provided the data.
    """
    logger.debug(
        f'get_endpoints called: hours={hours}, operation={operation}, service_name={service_name}'
    )
    pkey = f'p{int(percentile)}'

    # Application Signals path: endpoint RED metrics come from AppSignals, not CW logs.
    if state.is_appsignals_enabled() and service_name:
        from ..endpoint_metrics import get_endpoint_red_metrics

        try:
            formatted = await asyncio.to_thread(
                get_endpoint_red_metrics,
                service_name=service_name,
                hours=hours,
                operation=operation,
                limit=limit,
                percentile=percentile,
            )
        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f'Application Signals endpoint metrics error: {e}')
            return {
                'total_endpoints': 0,
                'returned': 0,
                'time_range_hours': hours,
                'error': str(e),
                'endpoints': [],
                'data_source': 'application_signals',
            }

        if operation and len(formatted) == 1:
            result = formatted[0]
            result['time_range_hours'] = hours
            result['data_source'] = 'application_signals'
            return result

        return {
            'total_endpoints': len(formatted),
            'returned': len(formatted),
            'filter_operation': operation,
            'percentile': pkey,
            'time_range_hours': hours,
            'endpoints': formatted,
            'data_source': 'application_signals',
        }

    # ServiceEvents CloudWatch Logs path: endpoint_summary records.
    try:
        formatted = await asyncio.to_thread(
            cw_logs.query_endpoint_summaries,
            service_name=service_name,
            hours=hours,
            operation=operation,
            limit=limit,
            percentile=percentile,
        )
    except CwLogsQueryError as e:
        logger.error(f'Endpoints CloudWatch Logs query error: {e}')
        return {
            'total_endpoints': 0,
            'returned': 0,
            'time_range_hours': hours,
            'error': str(e),
            'endpoints': [],
            'data_source': 'service_events',
        }

    logger.debug(f'get_endpoints returning {len(formatted)} endpoints')

    # Detail mode: when operation filter matches exactly one endpoint, return it with breakdown
    if operation and len(formatted) == 1:
        result = formatted[0]
        result['time_range_hours'] = hours
        result['data_source'] = 'service_events'
        return result

    return {
        'total_endpoints': len(formatted),
        'returned': len(formatted),
        'filter_operation': operation,
        'percentile': pkey,
        'time_range_hours': hours,
        'endpoints': formatted,
        'data_source': 'service_events',
    }


# =============================================================================
# Incident Snapshot Tools
# =============================================================================


async def get_incidents(
    endpoint: Optional[str] = None,
    trigger_type: Optional[str] = None,
    limit: int = 10,
    hours: int = 24,
    service_name: Optional[str] = None,
    environment: Optional[str] = None,
) -> dict:
    """Get a lightweight summary of recent incidents (errors, timeouts, slow requests).

    **Data sources:** Queries the ServiceEvents incident_snapshot records in
    CloudWatch Logs. If no incidents are found and Application Signals is enabled,
    falls back to service-level trace audit findings.

    Returns minimal data per incident for quick scanning. Use get_incident_root_cause(snapshot_id)
    to get the full call tree for detailed RCA.

    **Deployment-anchored investigation:**
    If the issue may be deployment-related, use `hours_since_deployment` from
    find_deployment() as the `hours` parameter to scope the query to the
    post-deployment window.

    **Incident Types (trigger_type):**
    - "exception": server error (HTTP 5xx or unhandled exception)
    - "latency": request duration exceeded configured threshold (slow request)

    **For latency incidents:**
    - No exception was thrown.
    - Use get_incident_root_cause() to examine the call_tree (when present): per-function
      timing from function-call instrumentation (`call_path`) shows where time was spent.
    - If call_tree is absent in get_incident_root_cause(), no instrumentation was captured —
      rely on duration_ms and trace correlation instead.

    **Duration field:**
    - `duration_ms` shows total request duration for ALL incident types
    - Useful for sorting/filtering incidents by response time

    **Workflow:**
    1. Use this tool to list incidents and identify which one to investigate
    2. Use get_incident_root_cause(snapshot_id) for exception context and the
       optional call_tree

    **SLO breach correlation (primary RCA path):**
    This is the **first tool to use** when investigating SLO breaches from `get_health_overview`:
    - Use the `endpoint` parameter to filter incidents by the breaching SLO's operation route
    - For latency SLOs, filter with `trigger_type="latency"` to find slow request incidents
    - For availability SLOs, filter with `trigger_type="exception"`
    - Matching incidents surface code-level root cause via `get_incident_root_cause(snapshot_id)` —
      exception_type + stack_trace pinpoint the failure; call_tree adds per-function timing when captured
    - If the root cause is in a downstream dependency, use the incident's
      `telemetry_correlation.trace_id` with `get_xray_trace()` for full distributed trace analysis

    Args:
        endpoint: Filter by operation substring (e.g., "/api/users"). Uses contains match. Optional.
        trigger_type: Filter by incident type - "exception" or "latency". Optional.
        limit: Maximum number of unique incidents to return (default 10).
        hours: Time range to query in hours (default 24).
        service_name: Service name to query. Optional — from user prompt or prior tool output.
            When provided, also queries Application Signals for trace-based error findings.
        environment: Environment name. Optional — from user prompt or prior tool output.

    Returns:
        List of incident summaries with:
        - snapshot_id: Use with get_incident_root_cause() for exception context and optional call_tree
        - operation: HTTP method + route
        - trigger_type: "exception" or "latency"
        - duration_ms: Total request duration in ms
        - status_code: HTTP response status code
        - cloud_context: Cloud infrastructure context when available
        - telemetry_correlation: trace_id / span_id for distributed-trace drill-down
        - data_source: "service_events" or "application_signals"
    """
    logger.debug(
        f'get_incidents called: hours={hours}, endpoint={endpoint}, '
        f'trigger_type={trigger_type}, service_name={service_name}'
    )

    # Normalize trigger_type ("error_status" is treated as "exception")
    norm_trigger = None
    if trigger_type:
        trigger_map = {'exception': 'exception', 'error_status': 'exception', 'latency': 'latency'}
        norm_trigger = trigger_map.get(trigger_type.lower(), trigger_type.lower())

    try:
        raw_incidents = await asyncio.to_thread(
            cw_logs.query_incidents,
            service_name=service_name,
            hours=hours,
            trigger_type=norm_trigger,
            endpoint=endpoint,
            limit=limit * 5,  # Fetch more for client-side dedup
        )
    except CwLogsQueryError as e:
        logger.error(f'Incidents CloudWatch Logs query error: {e}')
        return {
            'total_unique_incidents': 0,
            'time_range_hours': hours,
            'incidents': [],
            'error': str(e),
            'data_source': 'service_events',
        }

    # Dedup: keep latest incident per (operation, trigger_type) — latency keyed by day-timestamp
    seen = {}
    for rec in raw_incidents:
        attrs = rec.get('attributes') or {}
        inc_trigger = attrs.get('aws.service_events.trigger_type', '')
        operation = attrs.get('aws.service_events.operation', '')
        if inc_trigger == 'latency':
            ts = str(rec.get('timeUnixNano', ''))[:10]
            exc_key = ('latency', ts)
        else:
            exc_key = (inc_trigger,)
        key = (operation, exc_key)
        if key not in seen:
            seen[key] = rec

    # Build lightweight summaries
    unique_incidents = []
    for rec in list(seen.values())[:limit]:
        attrs = rec.get('attributes') or {}
        resource_attrs = cw_logs._resource_attrs(rec)
        cloud_context = (
            {k: v for k, v in resource_attrs.items() if k in state.CLOUD_ATTR_KEYS}
            if resource_attrs
            else {}
        )

        summary = {
            'snapshot_id': attrs.get('aws.service_events.snapshot_id'),
            'operation': attrs.get('aws.service_events.operation', 'unknown'),
            'trigger_type': attrs.get('aws.service_events.trigger_type'),
            'duration_ms': attrs.get('aws.service_events.duration_ms'),
            'status_code': attrs.get('http.response.status_code'),
        }

        if cloud_context:
            summary['cloud_context'] = cloud_context

        # Include trace correlation for distributed-trace drill-down
        trace_id = rec.get('traceId')
        span_id = rec.get('spanId')
        if trace_id:
            summary['telemetry_correlation'] = {'trace_id': trace_id, 'span_id': span_id}

        unique_incidents.append(summary)

    logger.debug(
        f'get_incidents returning {len(unique_incidents)} unique incidents (from {len(raw_incidents)} raw)'
    )

    result = {
        'total_unique_incidents': len(unique_incidents),
        'time_range_hours': hours,
        'incidents': unique_incidents,
    }

    if endpoint:
        result['filter_endpoint'] = endpoint
    if trigger_type:
        result['filter_trigger_type'] = trigger_type

    has_service_events_data = len(unique_incidents) > 0

    # Fall back to Application Signals trace audit when no incidents and AppSignals enabled.
    if has_service_events_data or not state.is_appsignals_enabled():
        result['data_source'] = 'service_events'
        return result

    try:
        from ..audit_utils import run_service_trace_audit

        appsignals_result = await run_service_trace_audit(service_name, hours)
        return {
            'data_source': 'application_signals',
            'service_level_incidents': appsignals_result,
            'incidents': result,
        }
    except Exception as e:
        logger.warning(f'AppSignals fallback failed in get_incidents: {e}')
        result['data_source'] = 'service_events'
        return result


async def get_incident_details(
    snapshot_id: str,
    hours: int = 72,
    service_name: Optional[str] = None,
    environment: Optional[str] = None,
) -> dict:
    """Get full details for a specific incident for root-cause analysis.

    **Two RCA signals are available:**

    1. **Exception info (present for exception-triggered incidents)** —
       `exception_type`, `exception_message`, and `stack_trace` pinpoint the exact
       code location that threw. This is the primary RCA signal for failures.

    2. **Call tree (optional)** — `call_tree` is an ASCII rendering of the incident's
       function-call instrumentation (`call_path`), showing per-function timing in ms
       with a percentage relative to the slowest frame. ★ ERROR marks a failing frame.
       Call tree is **absent** when no `call_path` was captured (e.g. the request was
       too short for instrumentation). When absent, a `call_tree_note` field explains
       this and directs RCA back to exception info.

    **RCA flow by trigger_type:**
    - `exception`: Start with `exception_type` + `stack_trace`. Inspect `call_tree`
      (if present) for what the app was doing; ★ ERROR flags the failing frame.
    - `latency`: No exception — focus on `call_tree`. High-ms frames are bottleneck
      candidates. If `call_tree` is absent, examine `duration_ms` and trace data
      (`telemetry_correlation.trace_id`) instead.

    **Example call_tree output:**
    ```
    [Timing: function-call instrumentation]
    module.handle_request [150.5ms, 100.0%]
    ├── module.validate_input [5.2ms, 3.5%]
    └── module.query_database [120.0ms, 79.7%] ★ ERROR
    ```

    Args:
        snapshot_id: The incident snapshot ID (from get_incidents).
        hours: Time range to search in hours (default 72 for older incidents).
        service_name: Service name to query. Optional — from user prompt or prior tool output.
        environment: Environment name. Optional — from user prompt or prior tool output.

    Returns:
        Incident details with:
        - trigger_type: "exception" or "latency"
        - exception_type, exception_message, stack_trace: present for exception incidents
        - call_tree: ASCII-rendered call_path (present only when call_path data available)
        - call_tree_note: Explanatory message when call_tree is absent
        - request_context: Request data that triggered the incident
        - resource_attributes: Cloud/host/k8s attributes
        - telemetry_correlation: Trace/span IDs for distributed tracing

    **Presenting the call tree:**
    Default to rendering the call_tree as indented ASCII text in the terminal.
    Only create HTML files if the user explicitly asks for HTML or visual output.
    """
    logger.debug(f'get_incident_details called: snapshot_id={snapshot_id}, hours={hours}')

    try:
        inc = await asyncio.to_thread(
            cw_logs.query_incident_by_id,
            snapshot_id=snapshot_id,
            hours=hours,
            service_name=service_name,
        )
    except CwLogsQueryError as e:
        return {'snapshot_id': snapshot_id, 'error': str(e)}

    if inc is None:
        return {'snapshot_id': snapshot_id, 'error': 'No data found'}

    attrs = inc.get('attributes') or {}
    body = inc.get('body') or {}

    details = {
        'snapshot_id': attrs.get('aws.service_events.snapshot_id'),
        'trigger_type': attrs.get('aws.service_events.trigger_type', 'unknown'),
        'operation': attrs.get('aws.service_events.operation'),
        'duration_ms': attrs.get('aws.service_events.duration_ms'),
        'status_code': attrs.get('http.response.status_code'),
    }

    # Build the call tree from exception_info[].call_path (function-call instrumentation).
    exception_info = body.get('exception_info') or []
    call_path = []
    for exc in exception_info:
        cp = exc.get('call_path') or []
        if cp:
            call_path = cp
            break

    if call_path:
        details['call_tree'] = render_incident_call_tree(call_path)
    else:
        details['call_tree_note'] = (
            'Call tree not available for this incident '
            '(no function-call instrumentation was captured, e.g. the request was too short). '
            'Use exception_type, exception_message, and stack_trace for root cause analysis.'
        )

    # Exception info — type/message/stack_trace come from the first exception entry.
    if exception_info:
        first_exc = exception_info[0]
        exception_type = first_exc.get('exception_type')
        exception_message = first_exc.get('exception_message')
        if exception_type or exception_message:
            details['exception_type'] = exception_type
            details['exception_message'] = exception_message
        stack_trace = first_exc.get('stack_trace')
        if stack_trace:
            details['stack_trace'] = stack_trace

    # Request context
    request_context = body.get('request_context')
    if request_context:
        details['request_context'] = request_context

    # Resource attributes
    resource_attrs = cw_logs._resource_attrs(inc)
    if resource_attrs:
        details['resource_attributes'] = resource_attrs

    # Telemetry correlation
    trace_id = inc.get('traceId')
    span_id = inc.get('spanId')
    if trace_id:
        details['telemetry_correlation'] = {'trace_id': trace_id, 'span_id': span_id}

    # Deployment ID
    deployment_id = attrs.get('aws.service_events.deployment.id')
    if deployment_id:
        details['deployment_id'] = deployment_id

    # Latency incident helpers
    if details.get('trigger_type') == 'latency':
        details['is_latency_incident'] = True
        if 'call_tree' in details:
            details['latency_note'] = (
                'Slow request incident. Inspect call_tree: high-ms frames are bottleneck candidates.'
            )
        else:
            details['latency_note'] = (
                'Slow request incident, but call tree is not available. '
                'Inspect duration_ms and telemetry_correlation.trace_id for downstream analysis.'
            )

    details['time_range_hours'] = hours
    logger.debug(
        f'get_incident_details returning: trigger_type={details.get("trigger_type")}, '
        f'has_call_tree={"call_tree" in details}'
    )
    return details


# =============================================================================
# Health and Summary Tools
# =============================================================================


def _get_slo_compliance_summary(hours: int) -> Optional[dict]:
    """Get structured SLO compliance summary for the health overview."""
    from ..aws_clients import get_applicationsignals_client

    client = get_applicationsignals_client()

    # Discover all SLOs (paginate)
    slo_summaries = []
    next_token = None
    while True:
        params = {'MaxResults': 50, 'IncludeLinkedAccounts': True}
        if next_token:
            params['NextToken'] = next_token
        response = client.list_service_level_objectives(**params)
        slo_summaries.extend(response.get('SloSummaries', []))
        next_token = response.get('NextToken')
        if not next_token:
            break
    if not slo_summaries:
        return None

    # Build audit targets from discovered SLOs
    slo_targets = [{'Type': 'slo', 'Data': {'Slo': {'SloName': s['Name']}}} for s in slo_summaries]

    # Call list_audit_findings in batches of 5 with SLO auditor only (parallelized)
    end_dt = datetime.now(timezone.utc)
    start_dt = end_dt - timedelta(hours=hours)
    BATCH_SIZE = 5
    batches = [slo_targets[i : i + BATCH_SIZE] for i in range(0, len(slo_targets), BATCH_SIZE)]
    all_findings = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = [
            executor.submit(
                client.list_audit_findings,
                StartTime=start_dt,
                EndTime=end_dt,
                AuditTargets=batch,  # type: ignore[arg-type]
                Auditors=['slo'],
            )
            for batch in batches
        ]
        for f in concurrent.futures.as_completed(futures):
            all_findings.extend(f.result().get('AuditFindings', []))

    return {
        'total_slos': len(slo_summaries),
        'total_findings': len(all_findings),
        'findings': all_findings,
    }


def _get_service_inventory(hours: int = 24) -> Optional[str]:
    """Get a summary of all services, partitioned by instrumentation status."""
    from ..aws_clients import get_applicationsignals_client

    client = get_applicationsignals_client()
    end_time = datetime.now(timezone.utc)
    start_time = end_time - timedelta(hours=hours)

    # Fetch all services with pagination
    all_services = []
    next_token = None
    while True:
        params = {'StartTime': start_time, 'EndTime': end_time, 'MaxResults': 100}
        if next_token:
            params['NextToken'] = next_token
        response = client.list_services(**params)
        all_services.extend(response.get('ServiceSummaries', []))
        next_token = response.get('NextToken')
        if not next_token:
            break

    if not all_services:
        return None

    from ..service_tools import _get_instrumentation_type

    # Partition by instrumentation type
    instrumented = []
    uninstrumented_count = 0
    for service in all_services:
        itype = _get_instrumentation_type(service)

        key_attrs = service.get('KeyAttributes', {})
        if itype in ('UNINSTRUMENTED', 'AWS_NATIVE'):
            uninstrumented_count += 1
        else:
            name = key_attrs.get('Name', 'Unknown')
            env = key_attrs.get('Environment', '')
            instrumented.append(f'- {name} ({env})' if env else f'- {name}')

    # Build a single pre-formatted summary string so the LLM renders it all
    lines = [
        f'Instrumented with Application Signals: {len(instrumented)} of {len(all_services)} services',
    ]
    lines.extend(instrumented)
    if uninstrumented_count > 0:
        lines.append('')
        lines.append(
            f'Note: {uninstrumented_count} other services are NOT instrumented with Application Signals '
            f'and have no telemetry data. Use the Application Signals enablement tools to enable '
            f'observability for those services.'
        )
    return '\n'.join(lines)


async def get_health_overview(
    hours: int = 24,
    detail: str = 'overview',
    service_name: Optional[str] = None,
    environment: Optional[str] = None,
) -> dict:
    """Get a health overview of the system.

    **PRIMARY ENTRY POINT for general health & performance questions.** Use this
    FIRST for any broad, open-ended ask such as "is anything wrong with my app?",
    "are there any performance issues?", or "how healthy is service X?". It is a
    FAST, minimal-data tool that consolidates the signals those questions need:
    SLO compliance/breaches, **recent incident events** (errors, timeouts, slow
    requests), and the top error-prone functions — in a single call.

    **MANDATORY for broad health/performance intent:** A general "any issues?"
    question MUST be answered starting from this tool, because it includes recent
    incident events. Do NOT answer such a question from audit_services alone —
    audit_services analyzes Application Signals metrics/SLO/traces/logs but does
    NOT include ServiceEvents incident events, so it will miss issues that only
    surface as incidents. Always check incidents (this tool, or get_recent_incidents)
    before concluding "no issues found".

    **Drill-down after this overview:**
    - get_recent_incidents / get_incident_root_cause(snapshot_id) for incident RCA
      (the slo_compliance findings include the exact get_recent_incidents call to make).
    - audit_services for deeper service-level root cause (traces, logs, dependency
      and top-contributor analysis) once a target service or area is identified.

    **Deployment-anchored investigation:**
    If the issue may be related to a recent deployment, call find_deployment() first
    and use its `hours_since_deployment` value as the `hours` parameter here. This
    scopes the health check to the post-deployment window.

    **Data sources:** Function metrics from CloudWatch Metrics V2 (PromQL) and
    incidents from ServiceEvents CloudWatch Logs. When Application Signals is enabled,
    also includes service inventory (instrumented vs uninstrumented breakdown) and
    SLO compliance/breach status.

    **Detail levels:**
    - detail="overview" (default): Fast health check with error counts and recent incidents.
    - detail="comprehensive": Includes everything from "overview" plus full endpoint stats.

    **IMPORTANT — service_inventory rendering instructions:**
    When `service_inventory` is present in the response, you MUST render it in full
    at the top of your answer, including:
    1. The "Instrumented with Application Signals" header with the count
    2. The bullet-pointed list of instrumented service names
    3. The "Note:" about uninstrumented services and the enablement tools reminder
    Do NOT omit or summarize the service_inventory text — show it verbatim.

    Returns (overview):
    - service_inventory: (when Application Signals enabled) Pre-formatted text block.
      Render this FIRST and IN FULL — it contains the instrumented service list AND
      the uninstrumented services note with enablement guidance.
    - Sampled error count (from top 50 error functions — not an exhaustive total)
    - Top 50 error-prone functions (name and error count only)
    - Top 10 recent incidents (minimal info: endpoint, trigger_type, timestamp)
    - note: Reminder that counts are sampled, not exhaustive totals
    - ALERT: (when SLO breaches detected)
    - slo_compliance: SLO breach summary when Application Signals is enabled
      Each finding includes `next_step` with the exact get_incidents call to make:
      - Availability SLO breach → trigger_type="exception"
      - Latency SLO breach → trigger_type="latency"

    Args:
        hours: Time range to query in hours (default 24).
        detail: Detail level - "overview" (fast, default) or "comprehensive" (includes endpoint stats).
        service_name: Service name to query. Optional — from user prompt or prior tool output.
        environment: Environment name. Optional — from user prompt or prior tool output.

    Returns:
        Health summary with counts and minimal details.
    """
    logger.debug(
        f'get_health_overview called: hours={hours}, detail={detail}, service_name={service_name}'
    )

    appsignals_enabled = state.is_appsignals_enabled()

    # --- Helper functions for parallel execution ---
    def _fetch_error_functions():
        try:
            records = function_metrics.fetch_function_records(
                service_name=service_name,
                environment=environment,
                hours=hours,
            )
            errored = [r for r in records if r.get('errors', 0) > 0]
            return function_metrics.sort_and_limit(errored, 'errors', 50)
        except PromQLQueryError as e:
            logger.warning(f'Failed to fetch error functions: {e}')
            return []

    def _fetch_incidents():
        try:
            return cw_logs.query_incidents(
                service_name=service_name,
                hours=hours,
                limit=10,
            )
        except CwLogsQueryError as e:
            logger.warning(f'Failed to fetch recent incidents: {e}')
            return []

    def _fetch_inventory():
        try:
            return _get_service_inventory(hours)
        except Exception as e:
            logger.warning(f'Service inventory check failed: {e}')
            return None

    def _fetch_endpoints():
        try:
            return cw_logs.query_endpoint_summaries(
                service_name=service_name,
                hours=hours,
                limit=50,
            )
        except CwLogsQueryError as e:
            logger.warning(f'Failed to fetch endpoint stats: {e}')
            return None

    def _fetch_slo_compliance():
        try:
            return _get_slo_compliance_summary(hours)
        except Exception as e:
            logger.warning(f'SLO compliance check failed: {e}')
            return None

    # --- Run all independent queries in parallel ---
    tasks = [
        asyncio.to_thread(_fetch_error_functions),
        asyncio.to_thread(_fetch_incidents),
    ]
    if appsignals_enabled:
        tasks.append(asyncio.to_thread(_fetch_inventory))
        tasks.append(asyncio.to_thread(_fetch_slo_compliance))
    if detail == 'comprehensive':
        tasks.append(asyncio.to_thread(_fetch_endpoints))

    results = await asyncio.gather(*tasks)

    # --- Unpack results based on what was requested ---
    idx = 0
    error_functions = results[idx]
    idx += 1
    recent_incidents_raw = results[idx]
    idx += 1
    inventory = results[idx] if appsignals_enabled else None
    if appsignals_enabled:
        idx += 1
    slo_summary = results[idx] if appsignals_enabled else None
    if appsignals_enabled:
        idx += 1
    ep_response = results[idx] if detail == 'comprehensive' else None

    # Format top error functions (records from CloudWatch Metrics V2)
    sampled_error_count = 0
    top_error_functions = []
    for f in error_functions:
        error_count = f.get('errors', 0)
        sampled_error_count += error_count
        top_error_functions.append(
            {
                'name': f.get('name', 'unknown'),
                'line': f.get('line', 0),
                'error_count': error_count,
            }
        )

    # Format recent incidents (OTLP service_events records)
    recent_incidents = []
    for inc in recent_incidents_raw[:5]:
        attrs = inc.get('attributes') or {}
        recent_incidents.append(
            {
                'snapshot_id': attrs.get('aws.service_events.snapshot_id'),
                'operation': attrs.get('aws.service_events.operation'),
                'trigger_type': attrs.get('aws.service_events.trigger_type'),
                'duration_ms': attrs.get('aws.service_events.duration_ms'),
                'status_code': attrs.get('http.response.status_code'),
            }
        )

    # Build overview dict — service inventory first so LLM renders it at the top
    overview = {}

    if inventory is not None:
        overview['service_inventory'] = inventory

    overview['sampled_error_count'] = sampled_error_count
    overview['sampled_incident_count'] = len(recent_incidents_raw)
    overview['note'] = (
        'Counts are from a sampled subset (top 50 error functions, up to 10 recent incidents) — not exhaustive totals.'
    )
    overview['top_error_functions'] = top_error_functions
    overview['recent_incidents'] = recent_incidents
    overview['time_range_hours'] = hours

    # Extract cloud context from incidents if available
    for inc in recent_incidents_raw:
        resource_attrs = cw_logs._resource_attrs(inc)
        cloud_context = (
            {k: v for k, v in resource_attrs.items() if k in state.CLOUD_ATTR_KEYS}
            if resource_attrs
            else {}
        )
        if cloud_context:
            overview['cloud_context'] = cloud_context
            break

    # Comprehensive mode: add endpoint stats (list of endpoint summary dicts)
    if ep_response is not None:
        overview['service_stats'] = {
            'total_endpoints': len(ep_response),
            'total_requests': sum(ep.get('total_requests', 0) or 0 for ep in ep_response),
            'total_faults': sum(ep.get('total_faults', 0) or 0 for ep in ep_response),
            'total_errors': sum(ep.get('total_errors', 0) or 0 for ep in ep_response),
        }

    # SLO compliance
    if slo_summary is not None:
        overview['slo_compliance'] = slo_summary

    has_appsignals_data = 'slo_compliance' in overview or 'service_inventory' in overview
    overview['data_source'] = (
        'service_events+application_signals' if has_appsignals_data else 'service_events'
    )
    logger.debug(
        f'get_health_overview returning: errors={overview.get("sampled_error_count", 0)}, '
        f'incidents={overview.get("sampled_incident_count", 0)}'
    )

    # When SLO breaches detected, restructure to put them at the top
    slo_compliance = overview.get('slo_compliance')
    if slo_compliance and slo_compliance.get('total_findings', 0) > 0:
        # Enrich each finding with next_step guidance for the LLM
        for finding in slo_compliance.get('findings', []):
            slo_type = finding.get('Type', '').lower()
            svc = finding.get('KeyAttributes', {}).get('Name')
            op = finding.get('Operation')
            if slo_type == 'latency':
                finding['next_step'] = (
                    f'get_recent_incidents(trigger_type="latency", endpoint="{op}", service_name="{svc}")'
                )
            elif slo_type == 'availability':
                finding['next_step'] = (
                    f'get_recent_incidents(trigger_type="exception", endpoint="{op}", service_name="{svc}")'
                )

        result = {
            'ALERT': (
                f'SLO BREACH DETECTED — {slo_compliance["total_findings"]} finding(s) '
                f'across {slo_compliance["total_slos"]} SLOs require immediate attention'
            ),
            'slo_compliance': slo_compliance,
        }
        for key, value in overview.items():
            if key != 'slo_compliance':
                result[key] = value
        return result

    return overview


# =============================================================================
# Deployment Lookup Tools
# =============================================================================


def find_deployment(
    git_commit_sha: Optional[str] = None,
    hours: int = 168,
    service_name: Optional[str] = None,
    environment: Optional[str] = None,
) -> dict:
    """Find deployments by searching deployment history in the ServiceEvents CloudWatch Logs.

    **Mode 1 - Find specific deployment (git_commit_sha provided):**
    Use when you've identified a suspect commit from code analysis but need to confirm
    when it was deployed. Searches by commit SHA prefix match.

    **Mode 2 - List recent deployments (git_commit_sha omitted):**
    Use when you cannot determine which commit caused the issue and need a deployment
    timeline to correlate with the issue onset time. Returns all recent unique deployments.

    **Workflow:**
    1. During RCA, you identify a commit that likely caused the issue → use Mode 1
    2. Or you know the issue started at a certain time but not which commit → use Mode 2
       to see all deployments and correlate timestamps
    3. Correlate the deployment timestamp with the issue onset time

    **Anchoring investigations to deployment time:**
    When any issue might be caused by or correlated with a deployment, use
    `hours_since_deployment` from the response as the `hours` parameter for all
    subsequent tool calls (get_health_overview, get_incidents, get_endpoints,
    list_functions, etc.). This scopes queries to the post-deployment window,
    making it easy to see what changed after the deploy.

    **Presenting Results:**
    Each deployment in the response has these fields:
    - `git_commit_sha`: The git commit hash
    - `deployment_url`: The CI/CD workflow run link — ALWAYS include this
    - `deployed_at`: When the deployment happened
    - `git_repo_url`: The repository URL (for context only)
    - `hours_since_deployment`: Hours elapsed since deployment (rounded up)
    - `trigger`: How the event was produced — `"startup"` (process start/restart),
      `"periodic"` (background re-emit), or `"shutdown"`.

    **Interpreting duplicate deployments:**
    The instrumentation re-emits deployment events over a service's lifetime (a
    `trigger="periodic"` timer re-emit roughly every 24h, plus a `trigger="startup"`
    event on every process start/restart). Results are collapsed **per unique commit
    SHA** so you don't double-count:
    - If a commit has any **startup** events, only those are shown (one per distinct
      restart) and its periodic re-emissions are dropped. Multiple startup entries for
      the same `git_commit_sha` are real restarts/redeploys of that code.
    - If a commit has **only periodic** events (no startup observed in the window), a
      single representative entry is shown for that commit.
    So a long-running deployment is counted once, and same-commit entries reflect actual
    restarts rather than timer noise.

    Args:
        git_commit_sha: Full/partial commit SHA to search for (prefix match). If omitted, lists all recent deployments.
        hours: Time range to search in hours (default 168 = 7 days).
        service_name: Service name to query. Optional — from user prompt or prior tool output.
        environment: Environment name. Optional — from user prompt or prior tool output.

    Returns:
        Dict with matching deployments including deployment context and timestamps.
    """
    logger.debug(
        f'find_deployment called: git_commit_sha={git_commit_sha}, hours={hours}, service_name={service_name}'
    )

    try:
        deployments_raw = cw_logs.query_deployments(
            service_name=service_name,
            hours=hours,
            commit=git_commit_sha,
        )
    except CwLogsQueryError as e:
        return {
            'query_git_commit_sha': git_commit_sha,
            'time_range_hours': hours,
            'found': False,
            'total_deployments': 0,
            'deployments': [],
            'error': str(e),
        }

    # Transform to tool output format
    deployments = []
    now = datetime.now(timezone.utc)
    for d in deployments_raw:
        dep = {
            'git_commit_sha': d.get('git_commit_sha'),
            'git_repo_url': d.get('git_repo_url', 'unknown'),
            'deployment_url': d.get('deployment_url', 'unknown'),
            'deployed_at': d.get('deployed_at', 'unknown'),
            'deployment_id': d.get('deployment_id'),
            'trigger': d.get('trigger'),
            'service_name': d.get('service_name'),
            'environment': d.get('environment'),
        }

        # Compute hours_since_deployment
        deployed_at = d.get('deployed_at', '')
        if deployed_at and deployed_at != 'unknown':
            try:
                dep_time = datetime.fromisoformat(deployed_at.replace('Z', '+00:00'))
                delta_hours = (now - dep_time).total_seconds() / 3600
                dep['hours_since_deployment'] = max(1, int(delta_hours) + 1)
            except (ValueError, TypeError):
                pass

        deployments.append(dep)

    result = {
        'query_git_commit_sha': git_commit_sha,
        'time_range_hours': hours,
        'found': len(deployments) > 0,
        'total_deployments': len(deployments),
        'deployments': deployments,
    }

    logger.debug(f'find_deployment returning {len(deployments)} deployments')

    if deployments:
        latest = deployments[0]
        h = latest.get('hours_since_deployment', 24)
        result['next_step'] = (
            f'Pass hours={h} to get_health_overview, get_incidents, get_endpoints, '
            f'list_functions, and other tools to scope queries to the post-deployment window.'
        )

    if not deployments:
        if git_commit_sha:
            result['suggestion'] = (
                f"No deployments found matching commit '{git_commit_sha}' in the last {hours} hours. "
                "Try increasing the time range with a larger 'hours' value."
            )
        else:
            result['suggestion'] = (
                f'No deployments found in the last {hours} hours. '
                "Try increasing the time range with a larger 'hours' value."
            )

    return result
