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

"""CloudWatch Application Signals MCP Server - RUM tools.

All RUM functionality is exposed through a single ``query_rum_events`` tool
that takes an ``action`` parameter to select the operation.  The individual
``_*`` async helpers are kept as private implementation details.
"""

import asyncio
import json
import time
from . import rum_queries
from .aws_clients import (
    AWS_REGION,
    applicationsignals_client,
    cloudwatch_client,
    logs_client,
    rum_client,
    sts_client,
    xray_client,
)
from .utils import remove_null_values
from datetime import datetime, timezone
from functools import lru_cache
from loguru import logger
from typing import Any, Callable, Optional


# ---------------------------------------------------------------------------
# Dispatcher – the single public MCP tool
# ---------------------------------------------------------------------------

_ACTION_MAP: dict[str, Callable] = {}  # populated after function definitions

# Cap for arbitrary `query` action to bound LLM context blow-up.
_QUERY_ACTION_MAX_RESULTS_CAP = 200

# Cap for `session_detail` row limit. A single session can emit thousands of
# events; 500 keeps response size bounded (~150 KB / ~40k tokens worst case).
_SESSION_DETAIL_MAX_LIMIT = 500

# Cap for `correlate` max_traces. BatchGetTraces fans out 5 IDs per call, so
# 100 traces = 20 parallel X-Ray calls — sufficient for correlation, bounded.
_CORRELATE_MAX_TRACES_CAP = 100

# Cap for list_anomalies pagination per detector. Each detector can page a
# long tail of historical anomalies; we only surface ones in the user window.
_ANOMALY_PAGE_CAP = 20

# Cap for GetMetricData NextToken pagination. A long window at a short period
# (e.g., 7d at period=1) can span many pages; cap so a pathological response
# can't pin the worker thread. Each page returns up to 100_800 data points.
_METRIC_DATA_PAGE_CAP = 10

# Oversample factor for correlate trace lookups: a single trace typically
# surfaces in 2-5 RUM events for the same page load (navigation + http spans
# sharing a trace_id), so we query 5x and truncate post-dedupe.
_CORRELATE_OVERSAMPLE_FACTOR = 5

# Platform fallback detection: sample window and event limit when the RUM API
# doesn't return an explicit Platform. A monitor with no events in this window
# falls back to 'unknown'.
_PLATFORM_DETECT_WINDOW_MS = 24 * 60 * 60 * 1000
_PLATFORM_DETECT_SAMPLE_LIMIT = 10


async def query_rum_events(
    action: str,
    app_monitor_name: Optional[str] = None,
    resource_arn: Optional[str] = None,
    query_string: Optional[str] = None,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    max_results: Optional[int] = None,
    page_url: Optional[str] = None,
    group_by: Optional[str] = None,
    platform: Optional[str] = None,
    max_traces: Optional[int] = None,
    metric_names: Optional[str] = None,
    statistic: Optional[str] = None,
    period: Optional[int] = None,
    session_id: Optional[str] = None,
    metric: Optional[str] = None,
    bucket: Optional[str] = None,
    compare_previous: Optional[bool] = None,
    limit: Optional[int] = None,
) -> str:
    """CloudWatch RUM – monitor real user experience across web and mobile apps.

    Use the ``action`` parameter to select an operation.  All other parameters
    are optional and depend on the chosen action.

    **Actions & required parameters** (JSON shape — keys are action names,
    values are required parameter names):

    ```json
    {
      "check_data_access": ["app_monitor_name"],
      "list_monitors": [],
      "get_monitor": ["app_monitor_name"],
      "list_tags": ["resource_arn"],
      "get_policy": ["app_monitor_name"],
      "query": ["app_monitor_name", "query_string", "start_time", "end_time"],
      "health": ["app_monitor_name", "start_time", "end_time"],
      "errors": ["app_monitor_name", "start_time", "end_time"],
      "performance": ["app_monitor_name", "start_time", "end_time"],
      "sessions": ["app_monitor_name", "start_time", "end_time"],
      "session_detail": ["app_monitor_name", "session_id", "start_time", "end_time"],
      "page_views": ["app_monitor_name", "start_time", "end_time"],
      "timeseries": ["app_monitor_name", "start_time", "end_time"],
      "locations": ["app_monitor_name", "start_time", "end_time"],
      "http_requests": ["app_monitor_name", "start_time", "end_time"],
      "resources": ["app_monitor_name", "start_time", "end_time"],
      "page_flows": ["app_monitor_name", "start_time", "end_time"],
      "crashes": ["app_monitor_name", "start_time", "end_time"],
      "app_launches": ["app_monitor_name", "start_time", "end_time"],
      "analyze": ["app_monitor_name", "start_time", "end_time"],
      "correlate": ["app_monitor_name", "page_url", "start_time", "end_time"],
      "metrics": ["app_monitor_name", "metric_names", "start_time", "end_time"],
      "slo_health": ["app_monitor_name", "start_time", "end_time"]
    }
    ```

    Optional params: ``compare_previous`` (health), ``page_url``/``group_by`` (errors,
    performance, locations, http_requests, resources, timeseries), ``metric``/``bucket``
    (timeseries), ``platform`` (crashes, app_launches — 'ios'/'android'/'all'),
    ``max_results`` (list_monitors, query; capped at 200 for query),
    ``max_traces`` (correlate), ``statistic``/``period`` (metrics),
    ``limit`` (session_detail — default 100).

    All responses are read-only. Logs Insights is the query engine; the server
    does not write any data.
    """
    handler = _ACTION_MAP.get(action)
    if not handler:
        return json.dumps(
            {
                'error': f"Unknown action '{action}'.",
                'error_type': 'bad_request',
                'available_actions': sorted(_ACTION_MAP.keys()),
            }
        )
    # Build kwargs from non-None values (excluding 'action')
    _all_kwargs = {
        'app_monitor_name': app_monitor_name,
        'resource_arn': resource_arn,
        'query_string': query_string,
        'start_time': start_time,
        'end_time': end_time,
        'max_results': max_results,
        'page_url': page_url,
        'group_by': group_by,
        'platform': platform,
        'max_traces': max_traces,
        'metric_names': metric_names,
        'statistic': statistic,
        'period': period,
        'session_id': session_id,
        'metric': metric,
        'bucket': bucket,
        'compare_previous': compare_previous,
        'limit': limit,
    }
    kwargs = {k: v for k, v in _all_kwargs.items() if v is not None}
    try:
        return await handler(**kwargs)
    except (TypeError, ValueError) as e:
        return json.dumps(
            {
                'error': f"Invalid parameters for action '{action}': {e}",
                'error_type': 'bad_request',
            }
        )


# --- Internal helpers ---


@lru_cache(maxsize=1)
def _get_account_id() -> str:
    """Return the caller's account ID (cached for the process lifetime)."""
    return sts_client.get_caller_identity()['Account']


@lru_cache(maxsize=1)
def _get_partition() -> str:
    """Resolve the AWS partition for the current region (aws / aws-us-gov / aws-cn)."""
    if AWS_REGION.startswith('us-gov-'):
        return 'aws-us-gov'
    if AWS_REGION.startswith('cn-'):
        return 'aws-cn'
    return 'aws'


def _log_group_arn(log_group_name: str) -> str:
    """Compose a CloudWatch Logs log group ARN from its name."""
    return (
        f'arn:{_get_partition()}:logs:{AWS_REGION}:{_get_account_id()}:log-group:{log_group_name}'
    )


def _clear_module_caches() -> None:
    """Clear all module-level lru_caches.

    Intended for test fixtures — the production caches are process-lifetime and
    never need to be cleared at runtime. Kept close to the cache definitions so
    any new ``@lru_cache`` added below is easy to register here too.
    """
    _get_account_id.cache_clear()
    _get_partition.cache_clear()
    _get_rum_app_info_confident_cached.cache_clear()


# Only cache confident (explicit Platform) results for the process lifetime.
# Fallback-detected platform is re-checked each call so a sparse log group
# doesn't poison the cache with a wrong classification.
@lru_cache(maxsize=256)
def _get_rum_app_info_confident_cached(app_monitor_name: str) -> tuple[str, str, bool]:
    """Return (log_group, platform, confident) from GetAppMonitor.

    ``confident`` is True when ``Platform`` was returned by the API; False
    when we fell back to log sampling (in which case the caller must not
    use the cached ``platform`` value).
    """
    resp = rum_client.get_app_monitor(Name=app_monitor_name)
    app_monitor = resp['AppMonitor']
    cw_log = app_monitor.get('DataStorage', {}).get('CwLog', {})
    if not cw_log.get('CwLogEnabled', False):
        raise ValueError(
            f"App monitor '{app_monitor_name}' does not have CloudWatch Logs enabled. "
            f'To enable it, run: aws rum update-app-monitor --name {app_monitor_name} --cw-log-enabled. '
            f'Once enabled, new events will be sent to CW Logs (existing events are not backfilled). '
            f'Recommended log retention: 30 days.'
        )
    log_group = cw_log.get('CwLogGroup')
    if not log_group:
        raise ValueError(
            f"App monitor '{app_monitor_name}' has CW Logs enabled but no log group found. "
            f'This may indicate the app monitor was recently created. Wait a few minutes and retry.'
        )
    raw_platform = app_monitor.get('Platform')
    if raw_platform:
        return log_group, ('web' if raw_platform == 'Web' else 'mobile'), True
    # Platform unknown; sampling done by caller. Return placeholder.
    return log_group, 'unknown', False


def _get_rum_app_info_sync(app_monitor_name: str) -> tuple[str, str]:
    log_group, platform, confident = _get_rum_app_info_confident_cached(app_monitor_name)
    if confident:
        return log_group, platform
    # Re-sample each call so a previously-empty log group isn't cached as 'web'.
    return log_group, _detect_platform_from_logs(log_group)


def _detect_platform_from_logs(log_group: str) -> str:
    """Fallback platform detection by sampling recent log events.

    Mobile (OTel) events have a top-level ``resource`` key or ``scope`` key;
    web events use ``event_type`` starting with ``com.amazon.rum.``. Samples
    up to ``_PLATFORM_DETECT_SAMPLE_LIMIT`` events over the last
    ``_PLATFORM_DETECT_WINDOW_MS`` and returns the majority signal. Returns
    'unknown' if the sample produces no signal (empty log group, unparseable
    events, or API error) so callers can decide how to degrade rather than
    silently being routed as 'web'.
    """
    try:
        end_ms = int(time.time() * 1000)
        start_ms = end_ms - _PLATFORM_DETECT_WINDOW_MS
        resp = logs_client.filter_log_events(
            logGroupName=log_group,
            startTime=start_ms,
            endTime=end_ms,
            limit=_PLATFORM_DETECT_SAMPLE_LIMIT,
        )
        events = resp.get('events') or []
        mobile_hits = 0
        web_hits = 0
        for ev in events:
            try:
                msg = json.loads(ev.get('message', '{}'))
            except (ValueError, TypeError):
                continue
            if 'resource' in msg or 'scope' in msg:
                mobile_hits += 1
            elif isinstance(msg.get('event_type'), str) and msg['event_type'].startswith(
                'com.amazon.rum.'
            ):
                web_hits += 1
        if mobile_hits > web_hits:
            return 'mobile'
        if web_hits > 0:
            return 'web'
        return 'unknown'
    except Exception as e:
        logger.debug(f'platform detection fallback failed for {log_group}: {e}')
        return 'unknown'


async def _get_rum_app_info(app_monitor_name: str) -> tuple[str, str]:
    """Async wrapper: returns (log_group, platform)."""
    return await asyncio.to_thread(_get_rum_app_info_sync, app_monitor_name)


_UNKNOWN_PLATFORM_HINT = (
    'Platform could not be determined: GetAppMonitor did not return a Platform '
    'and the log group has no parseable events in the last 24h. '
    'For a new monitor, wait for events to arrive; otherwise verify the monitor '
    'is instrumented and CwLogEnabled=true.'
)


def _unknown_platform_response(app_monitor_name: str) -> str:
    """Standard response for tools that must bail when monitor platform is unknown.

    Web-schema queries against a mobile/OTel log group return zero rows, which
    is indistinguishable from a genuinely quiet web monitor. Tools that run the
    web schema unconditionally must bail early rather than return a misleading
    empty result.

    Emits both ``platform`` and ``monitor_platform`` keyed to 'unknown' so
    callers can read either key without branching on action type.
    """
    return json.dumps(
        {
            'app_monitor': app_monitor_name,
            'platform': 'unknown',
            'monitor_platform': 'unknown',
            'error': _UNKNOWN_PLATFORM_HINT,
            'error_type': 'bad_request',
        }
    )


def _run_logs_insights_query_sync(
    log_group: str,
    query_string: str,
    start_time: datetime,
    end_time: datetime,
    max_results: int = 1000,
    poll_interval: float = 1.0,
    max_poll_seconds: float = 60.0,
) -> dict:
    """Run a CW Logs Insights query and poll for results (synchronous)."""
    resp = logs_client.start_query(
        logGroupName=log_group,
        startTime=int(start_time.timestamp()),
        endTime=int(end_time.timestamp()),
        queryString=query_string,
        limit=max_results,
    )
    query_id = resp['queryId']
    logger.debug(f'Started Logs Insights query {query_id}')

    deadline = time.monotonic() + max_poll_seconds
    result = None
    timed_out = True
    while time.monotonic() < deadline:
        result = logs_client.get_query_results(queryId=query_id)
        status = result['status']
        if status in ('Complete', 'Failed', 'Cancelled'):
            timed_out = False
            break
        time.sleep(poll_interval)

    if timed_out or result is None:
        # Free the concurrency slot — otherwise the query keeps running server-side.
        try:
            logs_client.stop_query(queryId=query_id)
        except Exception as e:
            logger.debug(f'stop_query failed for {query_id}: {e}')
        return {'status': 'Timeout', 'results': [], 'statistics': {}, 'queryId': query_id}

    rows = []
    for row in result.get('results', []):
        rows.append({f.get('field', ''): f.get('value', '') for f in row})

    return {
        'status': result['status'],
        'results': rows,
        'statistics': result.get('statistics', {}),
    }


async def _run_logs_insights_query(
    log_group: str,
    query_string: str,
    start_time: datetime,
    end_time: datetime,
    max_results: int = 1000,
    poll_interval: float = 1.0,
    max_poll_seconds: float = 60.0,
) -> dict:
    """Async wrapper around the sync Logs Insights poll loop.

    Wrapping in ``asyncio.to_thread`` keeps the event loop free while the
    blocking boto3 calls and ``time.sleep`` run in a worker thread.
    """
    return await asyncio.to_thread(
        _run_logs_insights_query_sync,
        log_group,
        query_string,
        start_time,
        end_time,
        max_results,
        poll_interval,
        max_poll_seconds,
    )


def _parse_time(time_str: str) -> datetime:
    """Parse ISO 8601 time string to datetime. Assumes UTC if no timezone."""
    dt = datetime.fromisoformat(time_str.replace('Z', '+00:00'))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _platform_mismatch(requested: str, monitor_platform: str) -> Optional[str]:
    """Return an error message if the requested platform is incompatible with the monitor.

    ``requested`` is 'ios'/'android'/'all' and ``monitor_platform`` is 'web'/'mobile'.
    Returns ``None`` when the platforms are compatible.
    """
    if requested == 'all':
        return None
    # When platform is undetectable, defer to the dedicated unknown-platform
    # guard in the caller so users see the hint instead of a confusing mismatch.
    if monitor_platform == 'unknown':
        return None
    if requested in ('ios', 'android') and monitor_platform != 'mobile':
        return (
            f"platform='{requested}' was requested, but app monitor is '{monitor_platform}'. "
            f'Mobile crash/launch queries require a mobile app monitor.'
        )
    return None


# --- Wave 1: Foundation tools ---


async def check_rum_data_access(app_monitor_name: str) -> str:
    """Check an app monitor's configuration and data access capabilities."""
    try:
        resp = await asyncio.to_thread(rum_client.get_app_monitor, Name=app_monitor_name)
    except rum_client.exceptions.ResourceNotFoundException:
        return json.dumps(
            {'error': f"App monitor '{app_monitor_name}' not found.", 'error_type': 'bad_request'}
        )
    except Exception as e:
        return json.dumps({'error': str(e), 'error_type': 'service_error'})

    app_monitor = resp['AppMonitor']
    config = app_monitor.get('AppMonitorConfiguration', {})
    data_storage = app_monitor.get('DataStorage', {})
    cw_log = data_storage.get('CwLog', {})

    cw_log_enabled = cw_log.get('CwLogEnabled', False)
    cw_log_group = cw_log.get('CwLogGroup', None)
    xray_enabled = config.get('EnableXRay', False)
    telemetries = config.get('Telemetries', [])
    sample_rate = config.get('SessionSampleRate', 1.0)
    allow_cookies = config.get('AllowCookies', False)

    findings = []
    capabilities = []

    if cw_log_enabled:
        capabilities.append('CW Logs Insights queries (errors, performance, sessions, page views)')
        capabilities.append(f'Log group: {cw_log_group}')
    else:
        findings.append(
            {
                'severity': 'HIGH',
                'issue': 'CloudWatch Logs not enabled',
                'impact': 'Cannot use Logs Insights analytics tools (errors, performance, sessions)',
                'fix': 'Enable CW Logs via the AWS console or CLI: aws rum update-app-monitor --name <name> --cw-log-enabled. Recommended retention: 30 days.',
            }
        )

    if xray_enabled:
        capabilities.append('X-Ray trace correlation (frontend-to-backend)')
    else:
        findings.append(
            {
                'severity': 'MEDIUM',
                'issue': 'X-Ray tracing not enabled',
                'impact': 'Cannot correlate frontend errors to backend services',
                'fix': "Enable X-Ray in app monitor config and add 'http' to telemetries.",
            }
        )

    expected = {'errors', 'performance', 'http'}
    enabled = {t.lower() for t in telemetries}
    missing = expected - enabled
    if missing:
        findings.append(
            {
                'severity': 'MEDIUM',
                'issue': f'Missing telemetry categories: {", ".join(sorted(missing))}',
                'impact': f'No data collection for: {", ".join(sorted(missing))}',
                'fix': f'Add {sorted(missing)} to telemetries list.',
            }
        )
    else:
        capabilities.append(f'Telemetries: {", ".join(sorted(enabled))}')

    if sample_rate == 0:
        findings.append(
            {
                'severity': 'HIGH',
                'issue': 'Session sample rate is 0%',
                'impact': 'No sessions are being recorded',
                'fix': 'Set sessionSampleRate to a value > 0 (e.g., 1.0 for 100%).',
            }
        )
    elif sample_rate < 0.1:
        findings.append(
            {
                'severity': 'LOW',
                'issue': f'Low session sample rate: {sample_rate * 100:.0f}%',
                'impact': 'Limited data for analytics — results may not be representative',
                'fix': 'Consider increasing sample rate for better coverage.',
            }
        )

    if not allow_cookies:
        findings.append(
            {
                'severity': 'LOW',
                'issue': 'Cookies disabled (allowCookies=false)',
                'impact': 'No session tracking — sessions cannot span page reloads, no return visitor counts',
                'fix': 'Set allowCookies=true for session tracking.',
            }
        )

    capabilities.append('CloudWatch Metrics (AWS/RUM namespace) — always available')

    result = {
        'app_monitor': app_monitor_name,
        'state': app_monitor.get('State', 'UNKNOWN'),
        'id': app_monitor.get('Id', 'UNKNOWN'),
        'domain': app_monitor.get('Domain', 'UNKNOWN'),
        'sample_rate': sample_rate,
        'capabilities': capabilities,
        'findings': findings,
        'summary': 'All checks passed — full analytics available.'
        if not findings
        else f'{len(findings)} issue(s) found.',
    }
    return json.dumps(result)


# --- Wave 2: App Monitor CRUD tools ---


async def list_rum_app_monitors(max_results: int = 25) -> str:
    """List all CloudWatch RUM app monitors in the account."""

    def _list() -> list:
        out = []
        paginator = rum_client.get_paginator('list_app_monitors')
        for page in paginator.paginate(PaginationConfig={'MaxItems': max_results}):
            for m in page.get('AppMonitorSummaries', []):
                out.append(remove_null_values(m))
        return out

    monitors = await asyncio.to_thread(_list)
    return json.dumps({'app_monitors': monitors, 'count': len(monitors)}, default=str)


async def get_rum_app_monitor(app_monitor_name: str) -> str:
    """Get full configuration of a CloudWatch RUM app monitor."""
    try:
        resp = await asyncio.to_thread(rum_client.get_app_monitor, Name=app_monitor_name)
        return json.dumps(remove_null_values(resp['AppMonitor']), default=str)
    except Exception as e:
        return json.dumps({'error': str(e), 'error_type': 'service_error'})


async def list_rum_tags(resource_arn: str) -> str:
    """List tags for a RUM resource (app monitor)."""
    try:
        resp = await asyncio.to_thread(rum_client.list_tags_for_resource, ResourceArn=resource_arn)
        return json.dumps({'tags': resp.get('Tags', {})})
    except Exception as e:
        return json.dumps({'error': str(e), 'error_type': 'service_error'})


async def get_rum_resource_policy(app_monitor_name: str) -> str:
    """Get the resource-based policy for a RUM app monitor."""
    try:
        resp = await asyncio.to_thread(rum_client.get_resource_policy, Name=app_monitor_name)
        policy = resp.get('PolicyDocument', '{}')
        return json.dumps({'policy': json.loads(policy) if policy else None})
    except Exception as e:
        return json.dumps({'error': str(e), 'error_type': 'service_error'})


# --- Wave 3: Custom Logs Insights query engine ---


async def run_rum_query(
    app_monitor_name: str,
    query_string: str,
    start_time: str,
    end_time: str,
    max_results: int = 100,
) -> str:
    """Run an arbitrary CloudWatch Logs Insights query against a RUM app monitor's log group.

    SCOPE WARNING: this action executes ``query_string`` verbatim against the
    monitor's CW Logs log group. The query is read-only (no mutations), but the
    log group contains every RUM event — including user agent, page URL, and
    any custom attributes the client sends. A caller who can invoke this action
    can read anything in the log group, not just the monitor's aggregated
    summary. Rely on the caller's IAM scope (`logs:StartQuery` on this log
    group) as the authorization boundary. ``max_results`` is capped at 200 to
    bound response size; this does not bound the data scanned.
    """
    try:
        log_group, _platform = await _get_rum_app_info(app_monitor_name)
    except ValueError as e:
        return json.dumps({'error': str(e), 'error_type': 'bad_request'})

    try:
        capped = max(1, min(int(max_results), _QUERY_ACTION_MAX_RESULTS_CAP))
    except (TypeError, ValueError):
        return json.dumps(
            {
                'error': f"Invalid max_results '{max_results}'; expected integer.",
                'error_type': 'bad_request',
            }
        )
    try:
        result = await _run_logs_insights_query(
            log_group=log_group,
            query_string=query_string,
            start_time=_parse_time(start_time),
            end_time=_parse_time(end_time),
            max_results=capped,
        )
        return json.dumps(
            {
                'app_monitor': app_monitor_name,
                'log_group': log_group,
                'query': query_string,
                'max_results_cap': _QUERY_ACTION_MAX_RESULTS_CAP,
                **result,
            },
            default=str,
        )
    except Exception as e:
        return json.dumps({'error': str(e), 'error_type': 'service_error'})


# --- Wave 4: Pre-built web analytics ---


async def audit_rum_health(
    app_monitor_name: str,
    start_time: str,
    end_time: str,
    compare_previous: bool = False,
) -> str:
    """Quick health check: errors, slowest pages, and sessions with most errors.

    Runs the three queries in parallel, and (optionally) a second set against
    the prior period of equal length for period-over-period comparison.
    """
    try:
        log_group, platform = await _get_rum_app_info(app_monitor_name)
    except ValueError as e:
        return json.dumps({'error': str(e), 'error_type': 'bad_request'})

    if platform == 'unknown':
        return _unknown_platform_response(app_monitor_name)

    st = _parse_time(start_time)
    et = _parse_time(end_time)

    queries = {
        'error_breakdown': rum_queries.HEALTH_ERROR_RATE,
        'slowest_pages': rum_queries.HEALTH_SLOWEST_PAGES,
        'sessions_with_errors': rum_queries.HEALTH_SESSION_ERRORS,
    }

    async def _run(q):
        try:
            return await _run_logs_insights_query(log_group, q, st, et, max_results=10)
        except Exception as e:
            return {'status': 'Failed', 'error': str(e), 'results': []}

    names = list(queries.keys())
    vals = await asyncio.gather(*(_run(queries[n]) for n in names))
    results = dict(zip(names, vals))

    output = {
        'app_monitor': app_monitor_name,
        'time_range': {'start': start_time, 'end': end_time},
        **results,
    }

    if compare_previous:
        duration = et - st
        prev_et = st
        prev_st = st - duration

        async def _run_prev(q):
            try:
                return await _run_logs_insights_query(
                    log_group, q, prev_st, prev_et, max_results=10
                )
            except Exception as e:
                return {'status': 'Failed', 'error': str(e), 'results': []}

        prev_vals = await asyncio.gather(*(_run_prev(queries[n]) for n in names))
        output['previous_period'] = {
            'time_range': {'start': prev_st.isoformat(), 'end': prev_et.isoformat()},
            **dict(zip(names, prev_vals)),
        }

    return json.dumps(output, default=str)


async def get_rum_errors(
    app_monitor_name: str,
    start_time: str,
    end_time: str,
    page_url: Optional[str] = None,
    group_by: Optional[str] = None,
) -> str:
    """Get JS and HTTP errors grouped by message and page."""
    try:
        log_group, platform = await _get_rum_app_info(app_monitor_name)
    except ValueError as e:
        return json.dumps({'error': str(e), 'error_type': 'bad_request'})

    if platform == 'unknown':
        return _unknown_platform_response(app_monitor_name)

    query = rum_queries.errors_query(page_url=page_url, group_by=group_by)
    result = await _run_logs_insights_query(
        log_group, query, _parse_time(start_time), _parse_time(end_time)
    )
    return json.dumps(
        {
            'app_monitor': app_monitor_name,
            'query': query,
            **result,
        },
        default=str,
    )


async def get_rum_performance(
    app_monitor_name: str,
    start_time: str,
    end_time: str,
    page_url: Optional[str] = None,
) -> str:
    """Get page load performance and Core Web Vitals (LCP, FID, CLS, INP)."""
    try:
        log_group, platform = await _get_rum_app_info(app_monitor_name)
    except ValueError as e:
        return json.dumps({'error': str(e), 'error_type': 'bad_request'})

    if platform == 'unknown':
        return _unknown_platform_response(app_monitor_name)

    st = _parse_time(start_time)
    et = _parse_time(end_time)

    nav_result, vitals_result = await asyncio.gather(
        _run_logs_insights_query(
            log_group, rum_queries.performance_navigation_query(page_url), st, et
        ),
        _run_logs_insights_query(
            log_group, rum_queries.performance_web_vitals_query(page_url), st, et
        ),
    )

    # Classify Web Vitals into good/needs-improvement/poor per web.dev thresholds.
    _WEB_VITALS_THRESHOLDS = {
        'largest_contentful_paint_event': (2500, 4000, 'ms'),
        'first_input_delay_event': (100, 300, 'ms'),
        'cumulative_layout_shift_event': (0.1, 0.25, ''),
        'interaction_to_next_paint_event': (200, 500, 'ms'),
    }
    for row in vitals_result.get('results', []):
        event_type = row.get('event_type', '')
        short_name = event_type.split('.')[-1] if '.' in event_type else event_type
        thresholds = _WEB_VITALS_THRESHOLDS.get(short_name)
        if thresholds:
            good_limit, poor_limit, unit = thresholds
            try:
                p90 = float(row.get('p90', 0))
                if p90 <= good_limit:
                    row['assessment'] = 'good'
                elif p90 <= poor_limit:
                    row['assessment'] = 'needs-improvement'
                else:
                    row['assessment'] = 'poor'
                row['thresholds'] = f'good<={good_limit}{unit}, poor>{poor_limit}{unit}'
            except (ValueError, TypeError):
                pass

    return json.dumps(
        {
            'app_monitor': app_monitor_name,
            'navigation_timings': nav_result,
            'web_vitals': vitals_result,
        },
        default=str,
    )


async def get_rum_sessions(
    app_monitor_name: str,
    start_time: str,
    end_time: str,
) -> str:
    """Get recent sessions with browser, OS, device type, and event counts."""
    try:
        log_group, platform = await _get_rum_app_info(app_monitor_name)
    except ValueError as e:
        return json.dumps({'error': str(e), 'error_type': 'bad_request'})

    if platform == 'unknown':
        return _unknown_platform_response(app_monitor_name)

    st = _parse_time(start_time)
    et = _parse_time(end_time)
    query = rum_queries.SESSIONS_QUERY if platform == 'web' else rum_queries.MOBILE_SESSIONS_QUERY
    result = await _run_logs_insights_query(log_group, query, st, et)
    return json.dumps(
        {'app_monitor': app_monitor_name, 'platform': platform, **result}, default=str
    )


async def get_rum_page_views(
    app_monitor_name: str,
    start_time: str,
    end_time: str,
) -> str:
    """Get top pages by view count."""
    try:
        log_group, platform = await _get_rum_app_info(app_monitor_name)
    except ValueError as e:
        return json.dumps({'error': str(e), 'error_type': 'bad_request'})

    if platform == 'unknown':
        return _unknown_platform_response(app_monitor_name)

    result = await _run_logs_insights_query(
        log_group, rum_queries.PAGE_VIEWS_QUERY, _parse_time(start_time), _parse_time(end_time)
    )
    return json.dumps({'app_monitor': app_monitor_name, **result}, default=str)


# --- Wave 4b: Time series, geo, HTTP requests, session detail, resources, page flows ---


async def get_rum_timeseries(
    app_monitor_name: str,
    start_time: str,
    end_time: str,
    metric: str = 'errors',
    bucket: str = '1h',
    page_url: Optional[str] = None,
) -> str:
    """Get time-bucketed trends for errors, performance, or sessions."""
    try:
        log_group, platform = await _get_rum_app_info(app_monitor_name)
    except ValueError as e:
        return json.dumps({'error': str(e), 'error_type': 'bad_request'})

    if platform == 'unknown':
        return _unknown_platform_response(app_monitor_name)

    st = _parse_time(start_time)
    et = _parse_time(end_time)

    try:
        query_map = {
            'errors': rum_queries.errors_timeseries_query(bucket, page_url),
            'performance': rum_queries.performance_timeseries_query(bucket, page_url),
            'sessions': (
                rum_queries.sessions_timeseries_query(bucket)
                if platform == 'web'
                else rum_queries.mobile_sessions_timeseries_query(bucket)
            ),
        }
    except ValueError as e:
        return json.dumps({'error': str(e), 'error_type': 'bad_request'})
    query = query_map.get(metric)
    if not query:
        return json.dumps(
            {
                'error': f"Unknown metric '{metric}'. Use: errors, performance, sessions.",
                'error_type': 'bad_request',
            }
        )

    result = await _run_logs_insights_query(log_group, query, st, et)
    return json.dumps(
        {
            'app_monitor': app_monitor_name,
            'metric': metric,
            'bucket': bucket,
            'platform': platform,
            **result,
        },
        default=str,
    )


async def get_rum_locations(
    app_monitor_name: str,
    start_time: str,
    end_time: str,
    page_url: Optional[str] = None,
) -> str:
    """Get session counts and performance by country."""
    try:
        log_group, platform = await _get_rum_app_info(app_monitor_name)
    except ValueError as e:
        return json.dumps({'error': str(e), 'error_type': 'bad_request'})

    if platform == 'unknown':
        return _unknown_platform_response(app_monitor_name)

    st = _parse_time(start_time)
    et = _parse_time(end_time)
    sessions_result, perf_result = await asyncio.gather(
        _run_logs_insights_query(log_group, rum_queries.geo_sessions_query(page_url), st, et),
        _run_logs_insights_query(log_group, rum_queries.geo_performance_query(page_url), st, et),
    )

    return json.dumps(
        {
            'app_monitor': app_monitor_name,
            'sessions_by_country': sessions_result,
            'performance_by_country': perf_result,
        },
        default=str,
    )


async def get_rum_http_requests(
    app_monitor_name: str,
    start_time: str,
    end_time: str,
    page_url: Optional[str] = None,
) -> str:
    """Get top HTTP requests by URL with latency and error rates."""
    try:
        log_group, platform = await _get_rum_app_info(app_monitor_name)
    except ValueError as e:
        return json.dumps({'error': str(e), 'error_type': 'bad_request'})

    if platform == 'unknown':
        return _unknown_platform_response(app_monitor_name)

    result = await _run_logs_insights_query(
        log_group,
        rum_queries.http_requests_query(page_url),
        _parse_time(start_time),
        _parse_time(end_time),
    )
    return json.dumps({'app_monitor': app_monitor_name, **result}, default=str)


async def get_rum_session_detail(
    app_monitor_name: str,
    session_id: str,
    start_time: str,
    end_time: str,
    limit: int = 100,
) -> str:
    """Get all events for a single session in chronological order."""
    try:
        log_group, platform = await _get_rum_app_info(app_monitor_name)
    except ValueError as e:
        return json.dumps({'error': str(e), 'error_type': 'bad_request'})

    if platform == 'unknown':
        return _unknown_platform_response(app_monitor_name)

    try:
        capped_limit = max(1, min(int(limit), _SESSION_DETAIL_MAX_LIMIT))
    except (TypeError, ValueError):
        return json.dumps(
            {'error': f"Invalid limit '{limit}'; expected integer.", 'error_type': 'bad_request'}
        )
    st = _parse_time(start_time)
    et = _parse_time(end_time)
    query = (
        rum_queries.session_detail_query(session_id, limit=capped_limit)
        if platform == 'web'
        else rum_queries.mobile_session_detail_query(session_id, limit=capped_limit)
    )
    result = await _run_logs_insights_query(log_group, query, st, et)
    return json.dumps(
        {
            'app_monitor': app_monitor_name,
            'session_id': session_id,
            'platform': platform,
            'limit': capped_limit,
            'limit_cap': _SESSION_DETAIL_MAX_LIMIT,
            **result,
        },
        default=str,
    )


async def get_rum_resources(
    app_monitor_name: str,
    start_time: str,
    end_time: str,
    page_url: Optional[str] = None,
) -> str:
    """Get top resource requests by duration and size."""
    try:
        log_group, platform = await _get_rum_app_info(app_monitor_name)
    except ValueError as e:
        return json.dumps({'error': str(e), 'error_type': 'bad_request'})

    if platform == 'unknown':
        return _unknown_platform_response(app_monitor_name)

    result = await _run_logs_insights_query(
        log_group,
        rum_queries.resource_requests_query(page_url),
        _parse_time(start_time),
        _parse_time(end_time),
    )
    return json.dumps({'app_monitor': app_monitor_name, **result}, default=str)


async def get_rum_page_flows(
    app_monitor_name: str,
    start_time: str,
    end_time: str,
) -> str:
    """Get page-to-page navigation flows (approximates user journey)."""
    try:
        log_group, platform = await _get_rum_app_info(app_monitor_name)
    except ValueError as e:
        return json.dumps({'error': str(e), 'error_type': 'bad_request'})

    if platform == 'unknown':
        return _unknown_platform_response(app_monitor_name)

    result = await _run_logs_insights_query(
        log_group,
        rum_queries.PAGE_FLOWS_QUERY,
        _parse_time(start_time),
        _parse_time(end_time),
    )
    return json.dumps({'app_monitor': app_monitor_name, **result}, default=str)


# --- Wave 5: Mobile analytics (experimental) + Anomaly detection ---


async def get_rum_crashes(
    app_monitor_name: str,
    start_time: str,
    end_time: str,
    platform: str = 'all',
) -> str:
    """Get mobile crashes and stability issues.

    iOS: crashes and hangs. Android: crashes and ANRs.
    Returns an error if called on a web app monitor with a mobile-only platform filter.
    """
    if platform not in ('ios', 'android', 'all'):
        return json.dumps(
            {
                'error': f"Invalid platform '{platform}'. Use 'ios', 'android', or 'all'.",
                'error_type': 'bad_request',
            }
        )

    try:
        log_group, monitor_platform = await _get_rum_app_info(app_monitor_name)
    except ValueError as e:
        return json.dumps({'error': str(e), 'error_type': 'bad_request'})

    mismatch = _platform_mismatch(platform, monitor_platform)
    if mismatch:
        return json.dumps(
            {'error': mismatch, 'error_type': 'bad_request', 'monitor_platform': monitor_platform}
        )

    if monitor_platform == 'unknown':
        return _unknown_platform_response(app_monitor_name)

    if platform == 'all' and monitor_platform == 'web':
        return json.dumps(
            {
                'app_monitor': app_monitor_name,
                'monitor_platform': 'web',
                'message': 'Crash queries apply to mobile app monitors only.',
            }
        )

    st = _parse_time(start_time)
    et = _parse_time(end_time)
    tasks = {}

    if platform in ('ios', 'all'):
        tasks['ios_crashes'] = _run_logs_insights_query(
            log_group, rum_queries.MOBILE_CRASHES_IOS, st, et
        )
        tasks['ios_hangs'] = _run_logs_insights_query(
            log_group, rum_queries.MOBILE_HANGS_IOS, st, et
        )
    if platform in ('android', 'all'):
        tasks['android'] = _run_logs_insights_query(
            log_group, rum_queries.MOBILE_CRASHES_ANDROID, st, et
        )
        tasks['android_anrs'] = _run_logs_insights_query(
            log_group, rum_queries.MOBILE_ANRS_ANDROID, st, et
        )

    names = list(tasks.keys())
    vals = await asyncio.gather(*(tasks[n] for n in names))
    results = dict(zip(names, vals))

    return json.dumps(
        {
            'app_monitor': app_monitor_name,
            'note': 'Field paths validated against ADOT Android SDK and aws-otel-swift SDK.',
            **results,
        },
        default=str,
    )


async def get_rum_app_launches(
    app_monitor_name: str,
    start_time: str,
    end_time: str,
    platform: str = 'all',
) -> str:
    """Get mobile app launch performance (cold/warm/pre-warm)."""
    if platform not in ('ios', 'android', 'all'):
        return json.dumps(
            {
                'error': f"Invalid platform '{platform}'. Use 'ios', 'android', or 'all'.",
                'error_type': 'bad_request',
            }
        )

    try:
        log_group, monitor_platform = await _get_rum_app_info(app_monitor_name)
    except ValueError as e:
        return json.dumps({'error': str(e), 'error_type': 'bad_request'})

    mismatch = _platform_mismatch(platform, monitor_platform)
    if mismatch:
        return json.dumps(
            {'error': mismatch, 'error_type': 'bad_request', 'monitor_platform': monitor_platform}
        )

    if monitor_platform == 'unknown':
        return _unknown_platform_response(app_monitor_name)

    if platform == 'all' and monitor_platform == 'web':
        return json.dumps(
            {
                'app_monitor': app_monitor_name,
                'monitor_platform': 'web',
                'message': 'App launch queries apply to mobile app monitors only.',
            }
        )

    st = _parse_time(start_time)
    et = _parse_time(end_time)
    tasks = {}

    if platform in ('ios', 'all'):
        tasks['ios'] = _run_logs_insights_query(
            log_group, rum_queries.MOBILE_APP_LAUNCHES_IOS, st, et
        )
    if platform in ('android', 'all'):
        tasks['android'] = _run_logs_insights_query(
            log_group, rum_queries.MOBILE_APP_LAUNCHES_ANDROID, st, et
        )

    names = list(tasks.keys())
    vals = await asyncio.gather(*(tasks[n] for n in names))
    results = dict(zip(names, vals))

    return json.dumps(
        {
            'app_monitor': app_monitor_name,
            'note': 'Field paths validated against ADOT Android SDK and aws-otel-swift SDK.',
            **results,
        },
        default=str,
    )


async def analyze_rum_log_group(
    app_monitor_name: str,
    start_time: str,
    end_time: str,
) -> str:
    """Analyze a RUM log group for anomalies and common patterns."""
    try:
        log_group, _platform = await _get_rum_app_info(app_monitor_name)
        st = _parse_time(start_time)
        et = _parse_time(end_time)
    except ValueError as e:
        return json.dumps({'error': str(e), 'error_type': 'bad_request'})

    log_group_arn = _log_group_arn(log_group)

    anomaly_info: dict[str, Any] = {'detectors': [], 'anomalies': []}

    def _fetch_anomaly_detectors() -> tuple[list, Optional[str]]:
        try:
            resp = logs_client.list_log_anomaly_detectors(filterLogGroupArn=log_group_arn)
            return resp.get('anomalyDetectors', []), None
        except Exception as e:
            return [], str(e)

    def _list_anomalies_for(arn: str) -> tuple[list, bool]:
        try:
            out: list = []
            token: Optional[str] = None
            for _ in range(_ANOMALY_PAGE_CAP):
                if token:
                    resp = logs_client.list_anomalies(anomalyDetectorArn=arn, nextToken=token)
                else:
                    resp = logs_client.list_anomalies(anomalyDetectorArn=arn)
                out.extend(resp.get('anomalies', []))
                token = resp.get('nextToken')
                if not token:
                    return out, False
            return out, True
        except Exception as e:
            logger.debug(f'Failed to list anomalies for detector {arn}: {e}')
            return [], False

    detectors, err = await asyncio.to_thread(_fetch_anomaly_detectors)
    if err:
        anomaly_info['error'] = err
    else:
        anomaly_info['detectors'] = [
            {'name': d.get('detectorName'), 'status': d.get('anomalyDetectorStatus')}
            for d in detectors
        ]
        detector_arns = [
            d.get('anomalyDetectorArn') for d in detectors if d.get('anomalyDetectorArn')
        ]
        anomaly_results = await asyncio.gather(
            *(asyncio.to_thread(_list_anomalies_for, arn) for arn in detector_arns)
        )
        st_ms = st.timestamp() * 1000
        et_ms = et.timestamp() * 1000
        any_truncated = False
        for anomalies, truncated in anomaly_results:
            if truncated:
                any_truncated = True
            for a in anomalies:
                ts = a.get('firstSeen', 0)
                if isinstance(ts, (int, float)) and st_ms <= ts <= et_ms:
                    anomaly_info['anomalies'].append(remove_null_values(a))
        anomaly_info['truncated'] = any_truncated
        anomaly_info['page_cap'] = _ANOMALY_PAGE_CAP

    top_patterns, error_patterns = await asyncio.gather(
        _run_logs_insights_query(log_group, rum_queries.TOP_PATTERNS_QUERY, st, et),
        _run_logs_insights_query(log_group, rum_queries.ERROR_PATTERNS_QUERY, st, et),
    )

    return json.dumps(
        {
            'app_monitor': app_monitor_name,
            'anomaly_detection': anomaly_info,
            'top_patterns': top_patterns,
            'error_patterns': error_patterns,
        },
        default=str,
    )


# --- Wave 6: Correlation + Metrics ---


async def correlate_rum_to_backend(
    app_monitor_name: str,
    page_url: str,
    start_time: str,
    end_time: str,
    max_traces: int = 10,
) -> str:
    """Correlate frontend RUM events to backend X-Ray traces.

    ``max_traces`` is capped at 100 to bound X-Ray BatchGetTraces fan-out.
    """
    try:
        log_group, platform = await _get_rum_app_info(app_monitor_name)
    except ValueError as e:
        return json.dumps({'error': str(e), 'error_type': 'bad_request'})

    if platform == 'unknown':
        return _unknown_platform_response(app_monitor_name)

    try:
        capped_traces = max(1, min(int(max_traces), _CORRELATE_MAX_TRACES_CAP))
    except (TypeError, ValueError):
        return json.dumps(
            {
                'error': f"Invalid max_traces '{max_traces}'; expected integer.",
                'error_type': 'bad_request',
            }
        )

    # capped_traces is already clamped to _CORRELATE_MAX_TRACES_CAP above, so
    # raw_limit is bounded at 100 * 5 = 500 scanned rows.
    raw_limit = capped_traces * _CORRELATE_OVERSAMPLE_FACTOR
    query = rum_queries.trace_ids_for_page_query(page_url, limit=raw_limit)
    logs_result = await _run_logs_insights_query(
        log_group, query, _parse_time(start_time), _parse_time(end_time), max_results=raw_limit
    )

    raw_trace_ids = [
        r.get('event_details.trace_id')
        for r in logs_result.get('results', [])
        if r.get('event_details.trace_id')
    ]
    trace_ids = list(dict.fromkeys(raw_trace_ids))[:capped_traces]

    if not trace_ids:
        return json.dumps(
            {
                'app_monitor': app_monitor_name,
                'page_url': page_url,
                'trace_ids': [],
                'trace_count': 0,
                'max_traces': capped_traces,
                'max_traces_cap': _CORRELATE_MAX_TRACES_CAP,
                'backend_services': {},
                'message': 'No X-Ray trace events found. Ensure X-Ray is enabled and http telemetry is active.',
                'logs_query_result': logs_result,
            },
            default=str,
        )

    # BatchGetTraces accepts max 5 IDs per call — fan out in parallel.
    batches = [trace_ids[i : i + 5] for i in range(0, len(trace_ids), 5)]

    def _get_batch(batch):
        try:
            return xray_client.batch_get_traces(TraceIds=batch).get('Traces', []), None
        except Exception as e:
            logger.warning(f'Failed to get traces {batch}: {e}')
            return [], str(e)

    batch_results = await asyncio.gather(*(asyncio.to_thread(_get_batch, b) for b in batches))
    batch_errors = [err for _, err in batch_results if err]
    traces = [t for batch_traces, _ in batch_results for t in batch_traces]

    # If every batch failed, callers otherwise can't distinguish from "no traces".
    # Keep the response shape identical to the success and no-traces branches so
    # callers can iterate uniformly across the three outcomes.
    if batch_errors and not traces:
        return json.dumps(
            {
                'app_monitor': app_monitor_name,
                'page_url': page_url,
                'trace_ids': trace_ids,
                'trace_count': 0,
                'max_traces': capped_traces,
                'max_traces_cap': _CORRELATE_MAX_TRACES_CAP,
                'backend_services': {},
                'error': f'All X-Ray batch_get_traces calls failed: {batch_errors[0]}',
                'error_type': 'service_error',
                'batch_error_count': len(batch_errors),
            },
            default=str,
        )

    services = {}
    for trace in traces:
        for segment in trace.get('Segments', []):
            try:
                doc = json.loads(segment.get('Document', '{}'))
            except (ValueError, TypeError) as e:
                logger.debug(f'Failed to parse X-Ray segment document: {e}')
                continue
            svc_name = doc.get('name', 'unknown')
            start = doc.get('start_time')
            end = doc.get('end_time')
            if start is None or end is None:
                continue
            duration = end - start
            if svc_name not in services:
                services[svc_name] = {'calls': 0, 'total_duration': 0, 'errors': 0}
            services[svc_name]['calls'] += 1
            services[svc_name]['total_duration'] += duration
            if doc.get('error') or doc.get('fault'):
                services[svc_name]['errors'] += 1

    response = {
        'app_monitor': app_monitor_name,
        'page_url': page_url,
        'trace_ids': trace_ids,
        'trace_count': len(traces),
        'max_traces': capped_traces,
        'max_traces_cap': _CORRELATE_MAX_TRACES_CAP,
        'backend_services': services,
    }
    if batch_errors:
        # Partial failure — some batches succeeded, some didn't. Surface so the
        # LLM knows the result is incomplete rather than assuming full coverage.
        response['partial_failure'] = True
        response['batch_error_count'] = len(batch_errors)
        response['batch_error_sample'] = batch_errors[0]
    return json.dumps(response, default=str)


async def get_rum_metrics(
    app_monitor_name: str,
    metric_names: str,
    start_time: str,
    end_time: str,
    statistic: str = 'Average',
    period: int = 300,
) -> str:
    """Get vended CloudWatch metrics from the AWS/RUM namespace."""
    # Caller-input parsing — return a 'bad_request' shape so callers can distinguish.
    try:
        names = json.loads(metric_names)
        st = _parse_time(start_time)
        et = _parse_time(end_time)
    except (ValueError, TypeError) as e:
        return json.dumps({'error': str(e), 'error_type': 'bad_request'})

    if (
        not isinstance(names, list)
        or not names
        or not all(isinstance(n, str) and n for n in names)
    ):
        return json.dumps(
            {
                'error': 'metric_names must be a non-empty JSON array of strings, e.g. \'["JsErrorCount"]\'.',
                'error_type': 'bad_request',
            }
        )

    queries = []
    for i, name in enumerate(names):
        queries.append(
            {
                'Id': f'm{i}',
                'MetricStat': {
                    'Metric': {
                        'Namespace': 'AWS/RUM',
                        'MetricName': name,
                        'Dimensions': [{'Name': 'application_name', 'Value': app_monitor_name}],
                    },
                    'Period': period,
                    'Stat': statistic,
                },
            }
        )

    # Service call — throttling, permissions, etc. Paginate on NextToken so
    # long windows at short periods don't silently truncate to the first page.
    # Capped at _METRIC_DATA_PAGE_CAP to bound worker-thread time and memory;
    # returns (pages, truncated) where truncated=True means more data existed.
    def _paginate() -> tuple[list, bool]:
        pages = []
        token = None
        for _ in range(_METRIC_DATA_PAGE_CAP):
            kwargs = {
                'MetricDataQueries': queries,
                'StartTime': st,
                'EndTime': et,
            }
            if token:
                kwargs['NextToken'] = token
            page = cloudwatch_client.get_metric_data(**kwargs)
            pages.append(page)
            token = page.get('NextToken')
            if not token:
                return pages, False
        return pages, True

    try:
        pages, truncated = await asyncio.to_thread(_paginate)
    except Exception as e:
        return json.dumps({'error': str(e), 'error_type': 'service_error'})

    # Response formatting — preserve structured error shape for unexpected payloads.
    # Status aggregation: report the "worst" status seen across pages so callers
    # don't silently lose a PartialData signal if a later page reports Complete.
    _STATUS_RANK = {'Complete': 0, 'InternalError': 1, 'PartialData': 2, 'Unknown': 3}
    try:
        results: dict = {}
        for page in pages:
            for mr in page.get('MetricDataResults', []):
                idx = int(mr['Id'][1:])
                metric_name = names[idx]
                entry = results.setdefault(
                    metric_name,
                    {
                        'timestamps': [],
                        'values': [],
                        'statistic': statistic,
                        'status': mr.get('StatusCode', 'Unknown'),
                    },
                )
                entry['timestamps'].extend(t.isoformat() for t in mr.get('Timestamps', []))
                entry['values'].extend(mr.get('Values', []))
                page_status = mr.get('StatusCode', entry['status'])
                if _STATUS_RANK.get(page_status, 3) > _STATUS_RANK.get(entry['status'], 3):
                    entry['status'] = page_status
    except (KeyError, IndexError, ValueError) as e:
        logger.exception('malformed MetricDataResults payload')
        return json.dumps({'error': str(e), 'error_type': 'internal_error'})
    if truncated:
        logger.warning(
            f'get_metric_data truncated at {_METRIC_DATA_PAGE_CAP} pages '
            f'for {app_monitor_name}; narrow the window or increase period.'
        )
    return json.dumps(
        {
            'app_monitor': app_monitor_name,
            'metrics': results,
            'truncated': truncated,
            'page_cap': _METRIC_DATA_PAGE_CAP,
        },
        default=str,
    )


# ---------------------------------------------------------------------------
# Wire action map (must come after all function definitions)
# ---------------------------------------------------------------------------


# --- Wave 7: SLO health (Application Signals integration) ---


async def get_rum_slo_health(
    app_monitor_name: str,
    start_time: str,
    end_time: str,
) -> str:
    """Get SLO health status for a RUM app monitor.

    ``start_time`` is accepted for API symmetry with the other RUM actions but
    is not used — the SLO budget report is evaluated at ``end_time`` only.
    """
    et = _parse_time(end_time)

    def _list_slos() -> list:
        out = []
        paginator = applicationsignals_client.get_paginator('list_service_level_objectives')
        for page in paginator.paginate(
            KeyAttributes={
                'Type': 'AWS::Resource',
                'ResourceType': 'AWS::RUM::AppMonitor',
                'Identifier': app_monitor_name,
            },
        ):
            out.extend(page.get('SloSummaries', []))
        return out

    try:
        slos = await asyncio.to_thread(_list_slos)
    except Exception as e:
        return json.dumps(
            {
                'app_monitor': app_monitor_name,
                'status': 'NO_SLO',
                'total': 0,
                'healthy': 0,
                'breaching': 0,
                'breaching_slos': [],
                'message': f'Could not list SLOs: {e}',
            }
        )

    if not slos:
        return json.dumps(
            {
                'app_monitor': app_monitor_name,
                'status': 'NO_SLO',
                'total': 0,
                'healthy': 0,
                'breaching': 0,
                'breaching_slos': [],
            }
        )

    async def _check_slo(slo: dict) -> dict:
        slo_name = slo.get('Name', '')
        slo_arn = slo.get('Arn', '')
        # Per the Application Signals API, GetServiceLevelObjective and
        # BatchGetServiceLevelObjectiveBudgetReport expect the SLO ARN or ID,
        # not the display name.
        slo_id = slo_arn or slo_name
        try:
            resp = await asyncio.to_thread(
                applicationsignals_client.get_service_level_objective,
                Id=slo_id,
            )
            slo_detail = resp.get('Slo', {})
            goal = slo_detail.get('Goal', {})
            attainment = goal.get('AttainmentGoal')

            budget_resp = await asyncio.to_thread(
                applicationsignals_client.batch_get_service_level_objective_budget_report,
                Timestamp=et,
                SloIds=[slo_id],
            )
            reports = budget_resp.get('Reports', [])
            if reports:
                report = reports[0]
                budget_status = report.get('BudgetStatus', 'UNKNOWN')
                if budget_status == 'OK':
                    return {'kind': 'healthy'}
                if budget_status == 'BREACHED':
                    metric_name = _extract_slo_metric_name(slo_detail)
                    return {
                        'kind': 'breaching',
                        'entry': {
                            'slo_name': slo_name,
                            'slo_arn': slo_arn,
                            'budget_status': budget_status,
                            'attainment': report.get('Attainment'),
                            'goal': attainment,
                            'metric': metric_name,
                        },
                    }
                return {'kind': 'insufficient'}
            return {'kind': 'insufficient'}
        except Exception as e:
            logger.warning(f'Failed to check SLO {slo_id}: {e}')
            return {
                'kind': 'error',
                'entry': {
                    'slo_name': slo_name,
                    'slo_arn': slo_arn,
                    'budget_status': None,
                    'attainment': None,
                    'goal': None,
                    'metric': None,
                    'error': str(e),
                },
            }

    outcomes = await asyncio.gather(*(_check_slo(s) for s in slos))
    breaching = [o['entry'] for o in outcomes if o['kind'] == 'breaching']
    errored = [o['entry'] for o in outcomes if o['kind'] == 'error']
    healthy = sum(1 for o in outcomes if o['kind'] == 'healthy')
    insufficient = sum(1 for o in outcomes if o['kind'] == 'insufficient')

    total = len(slos)
    if breaching:
        status = 'BREACHED'
    elif total and len(errored) == total:
        status = 'ERROR'
    elif total and healthy == 0:
        status = 'INSUFFICIENT_DATA'
    else:
        status = 'OK'

    return json.dumps(
        {
            'app_monitor': app_monitor_name,
            'status': status,
            'total': total,
            'healthy': healthy,
            'breaching': len(breaching),
            'insufficient_data': insufficient,
            'errored': len(errored),
            'breaching_slos': breaching,
            'errored_slos': errored,
            'slo_names': [s.get('Name') for s in slos],
        },
        default=str,
    )


def _extract_slo_metric_name(slo_detail: Any) -> str:
    """Extract the RUM metric name from an SLO config."""
    req_sli = slo_detail.get('RequestBasedSli', {}).get('RequestBasedSliMetric', {})
    count_metric = req_sli.get('MonitoredRequestCountMetric', {})
    for metric_list_key in ('GoodCountMetric', 'BadCountMetric'):
        metrics = count_metric.get(metric_list_key, [])
        if isinstance(metrics, list):
            for m in metrics:
                mid = m.get('Id', '')
                if mid.startswith('fault_') or mid.startswith('good_'):
                    return m.get('MetricStat', {}).get('Metric', {}).get('MetricName', 'unknown')
    sli_metric = slo_detail.get('Sli', {}).get('SliMetric', {})
    for m in sli_metric.get('MetricDataQueries', []):
        return m.get('MetricStat', {}).get('Metric', {}).get('MetricName', 'unknown')
    return 'unknown'


_ACTION_MAP.update(
    {
        'check_data_access': check_rum_data_access,
        'list_monitors': list_rum_app_monitors,
        'get_monitor': get_rum_app_monitor,
        'list_tags': list_rum_tags,
        'get_policy': get_rum_resource_policy,
        'query': run_rum_query,
        'health': audit_rum_health,
        'errors': get_rum_errors,
        'performance': get_rum_performance,
        'sessions': get_rum_sessions,
        'session_detail': get_rum_session_detail,
        'page_views': get_rum_page_views,
        'timeseries': get_rum_timeseries,
        'locations': get_rum_locations,
        'http_requests': get_rum_http_requests,
        'resources': get_rum_resources,
        'page_flows': get_rum_page_flows,
        'crashes': get_rum_crashes,
        'app_launches': get_rum_app_launches,
        'analyze': analyze_rum_log_group,
        'correlate': correlate_rum_to_backend,
        'metrics': get_rum_metrics,
        'slo_health': get_rum_slo_health,
    }
)
