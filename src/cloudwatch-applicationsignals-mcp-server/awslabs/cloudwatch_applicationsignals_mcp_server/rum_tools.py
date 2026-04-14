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

All RUM functionality is exposed through a single ``rum`` tool that takes an
``action`` parameter to select the operation.  The individual ``_*`` async
helpers are kept as private implementation details.
"""

import json
import time
from .aws_clients import cloudwatch_client, logs_client, rum_client, xray_client
from .utils import remove_null_values
from datetime import datetime, timezone
from loguru import logger
from typing import Optional


# ---------------------------------------------------------------------------
# Dispatcher – the single public MCP tool
# ---------------------------------------------------------------------------

_ACTION_MAP: dict[str, callable] = {}  # populated after function definitions


async def rum(
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
) -> str:
    """CloudWatch RUM – monitor real user experience across web and mobile apps.

    Use the ``action`` parameter to select an operation.  All other parameters
    are optional and depend on the chosen action.

    **Actions & required parameters:**

    Discovery:
    - ``check_data_access`` – Inspect app monitor config (app_monitor_name)
    - ``list_monitors`` – List all app monitors (no required params)
    - ``get_monitor`` – Get app monitor details (app_monitor_name)
    - ``list_tags`` – List tags for an app monitor (resource_arn)
    - ``get_policy`` – Get resource-based policy (app_monitor_name)

    Analytics (require CW Logs enabled):
    - ``query`` – Run custom Logs Insights query (app_monitor_name, query_string, start_time, end_time; optional: max_results)
    - ``health`` – Quick health audit (app_monitor_name, start_time, end_time)
    - ``errors`` – Error analysis (app_monitor_name, start_time, end_time; optional: page_url, group_by)
    - ``performance`` – Page load + Web Vitals (app_monitor_name, start_time, end_time; optional: page_url)
    - ``sessions`` – Recent sessions (app_monitor_name, start_time, end_time)
    - ``session_detail`` – All events for one session (app_monitor_name, session_id, start_time, end_time)
    - ``page_views`` – Top pages by views (app_monitor_name, start_time, end_time)
    - ``timeseries`` – Time-bucketed trends (app_monitor_name, start_time, end_time; optional: metric='errors'|'performance'|'sessions', bucket='1h', page_url)
    - ``locations`` – Sessions and performance by country (app_monitor_name, start_time, end_time; optional: page_url)
    - ``http_requests`` – Top HTTP requests with latency/errors (app_monitor_name, start_time, end_time; optional: page_url)
    - ``resources`` – Top resource requests by duration/size (app_monitor_name, start_time, end_time; optional: page_url)
    - ``page_flows`` – Page-to-page navigation flows (app_monitor_name, start_time, end_time)
    - ``crashes`` – Mobile crashes + ANRs (app_monitor_name, start_time, end_time; optional: platform)
    - ``app_launches`` – Mobile launch times (app_monitor_name, start_time, end_time; optional: platform)
    - ``analyze`` – Anomaly detection + patterns (app_monitor_name, start_time, end_time)

    Correlation & Metrics:
    - ``correlate`` – Frontend-to-backend X-Ray correlation (app_monitor_name, page_url, start_time, end_time; optional: max_traces)
    - ``metrics`` – CloudWatch RUM namespace metrics (app_monitor_name, metric_names as JSON array, start_time, end_time; optional: statistic, period)
    """
    handler = _ACTION_MAP.get(action)
    if not handler:
        return json.dumps({
            'error': f"Unknown action '{action}'.",
            'available_actions': sorted(_ACTION_MAP.keys()),
        })
    # Build kwargs from non-None values (excluding 'action')
    kwargs = {k: v for k, v in dict(
        app_monitor_name=app_monitor_name, resource_arn=resource_arn,
        query_string=query_string, start_time=start_time, end_time=end_time,
        max_results=max_results, page_url=page_url, group_by=group_by,
        platform=platform, max_traces=max_traces, metric_names=metric_names,
        statistic=statistic, period=period, session_id=session_id,
        metric=metric, bucket=bucket,
    ).items() if v is not None}
    try:
        return await handler(**kwargs)
    except TypeError as e:
        return json.dumps({'error': f"Invalid parameters for action '{action}': {e}"})


# --- Internal helpers ---


def _get_rum_log_group(app_monitor_name: str) -> str:
    """Get the CW Logs log group for a RUM app monitor.

    Returns the log group name or raises ValueError with guidance.
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
    return log_group


def _run_logs_insights_query(
    log_group: str,
    query_string: str,
    start_time: datetime,
    end_time: datetime,
    max_results: int = 1000,
    poll_interval: float = 1.0,
    max_poll_seconds: float = 60.0,
) -> dict:
    """Run a CW Logs Insights query and poll for results.

    Returns dict with 'status', 'results', 'statistics'.
    """
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
    while time.monotonic() < deadline:
        result = logs_client.get_query_results(queryId=query_id)
        status = result['status']
        if status in ('Complete', 'Failed', 'Cancelled'):
            break
        time.sleep(poll_interval)

    # Convert results to list of dicts
    rows = []
    for row in result.get('results', []):
        rows.append({f['field']: f['value'] for f in row})

    return {
        'status': result['status'],
        'results': rows,
        'statistics': result.get('statistics', {}),
    }


def _parse_time(time_str: str) -> datetime:
    """Parse ISO 8601 time string to datetime. Assumes UTC if no timezone."""
    dt = datetime.fromisoformat(time_str.replace('Z', '+00:00'))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


# --- Wave 1: Foundation tools ---


async def check_rum_data_access(app_monitor_name: str) -> str:
    """Check an app monitor's configuration and data access capabilities.

    Inspects CW Logs, X-Ray, telemetry, sampling, and cookie settings.
    Returns structured advice on what's enabled and what's missing.
    """
    try:
        resp = rum_client.get_app_monitor(Name=app_monitor_name)
    except rum_client.exceptions.ResourceNotFoundException:
        return json.dumps({'error': f"App monitor '{app_monitor_name}' not found."})
    except Exception as e:
        return json.dumps({'error': str(e)})

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

    # CW Logs
    if cw_log_enabled:
        capabilities.append('CW Logs Insights queries (errors, performance, sessions, page views)')
        capabilities.append(f'Log group: {cw_log_group}')
    else:
        findings.append({
            'severity': 'HIGH',
            'issue': 'CloudWatch Logs not enabled',
            'impact': 'Cannot use Logs Insights analytics tools (errors, performance, sessions)',
            'fix': 'Enable CW Logs via the AWS console or CLI: aws rum update-app-monitor --name <name> --cw-log-enabled. Recommended retention: 30 days.',
        })

    # X-Ray
    if xray_enabled:
        capabilities.append('X-Ray trace correlation (frontend-to-backend)')
    else:
        findings.append({
            'severity': 'MEDIUM',
            'issue': 'X-Ray tracing not enabled',
            'impact': 'Cannot correlate frontend errors to backend services',
            'fix': "Enable X-Ray in app monitor config and add 'http' to telemetries.",
        })

    # Telemetries
    expected = {'errors', 'performance', 'http'}
    enabled = {t.lower() for t in telemetries}
    missing = expected - enabled
    if missing:
        findings.append({
            'severity': 'MEDIUM',
            'issue': f"Missing telemetry categories: {', '.join(sorted(missing))}",
            'impact': f"No data collection for: {', '.join(sorted(missing))}",
            'fix': f"Add {sorted(missing)} to telemetries list.",
        })
    else:
        capabilities.append(f"Telemetries: {', '.join(sorted(enabled))}")

    # Sampling
    if sample_rate == 0:
        findings.append({
            'severity': 'HIGH',
            'issue': 'Session sample rate is 0%',
            'impact': 'No sessions are being recorded',
            'fix': 'Set sessionSampleRate to a value > 0 (e.g., 1.0 for 100%).',
        })
    elif sample_rate < 0.1:
        findings.append({
            'severity': 'LOW',
            'issue': f'Low session sample rate: {sample_rate * 100:.0f}%',
            'impact': 'Limited data for analytics — results may not be representative',
            'fix': 'Consider increasing sample rate for better coverage.',
        })

    # Cookies
    if not allow_cookies:
        findings.append({
            'severity': 'LOW',
            'issue': 'Cookies disabled (allowCookies=false)',
            'impact': 'No session tracking — sessions cannot span page reloads, no return visitor counts',
            'fix': 'Set allowCookies=true for session tracking.',
        })

    # Vended metrics always available
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
    return json.dumps(result, indent=2)


# --- Wave 2: App Monitor CRUD tools ---


async def list_rum_app_monitors(max_results: int = 100) -> str:
    """List all CloudWatch RUM app monitors in the account.

    Returns app monitor names, IDs, states, and creation dates.
    """
    monitors = []
    paginator = rum_client.get_paginator('list_app_monitors')
    for page in paginator.paginate(PaginationConfig={'MaxItems': max_results}):
        for m in page.get('AppMonitorSummaries', []):
            monitors.append(remove_null_values(m))
    return json.dumps({'app_monitors': monitors, 'count': len(monitors)}, indent=2, default=str)


async def get_rum_app_monitor(app_monitor_name: str) -> str:
    """Get full configuration of a CloudWatch RUM app monitor.

    Returns app monitor config including CW Logs status, telemetries,
    sampling rate, X-Ray, domain, and data storage settings.
    """
    try:
        resp = rum_client.get_app_monitor(Name=app_monitor_name)
        return json.dumps(remove_null_values(resp['AppMonitor']), indent=2, default=str)
    except Exception as e:
        return json.dumps({'error': str(e)})


async def list_rum_tags(resource_arn: str) -> str:
    """List tags for a RUM resource (app monitor).

    Args:
        resource_arn: ARN of the app monitor.
    """
    try:
        resp = rum_client.list_tags_for_resource(ResourceArn=resource_arn)
        return json.dumps({'tags': resp.get('Tags', {})})
    except Exception as e:
        return json.dumps({'error': str(e)})


async def get_rum_resource_policy(app_monitor_name: str) -> str:
    """Get the resource-based policy for a RUM app monitor.

    Resource policies control who can call PutRumEvents (send telemetry).
    """
    try:
        resp = rum_client.get_resource_policy(Name=app_monitor_name)
        policy = resp.get('PolicyDocument', '{}')
        return json.dumps({'policy': json.loads(policy) if policy else None}, indent=2)
    except Exception as e:
        return json.dumps({'error': str(e)})


# --- Wave 3: Custom Logs Insights query engine ---


async def query_rum_events(
    app_monitor_name: str,
    query_string: str,
    start_time: str,
    end_time: str,
    max_results: int = 1000,
) -> str:
    """Run an arbitrary CloudWatch Logs Insights query against a RUM app monitor's log group.

    Auto-discovers the log group from the app monitor config. Requires CW Logs to be enabled.

    Common RUM event types: com.amazon.rum.js_error_event, com.amazon.rum.http_event,
    com.amazon.rum.performance_navigation_event, com.amazon.rum.page_view_event,
    com.amazon.rum.session_start_event, com.amazon.rum.largest_contentful_paint_event,
    com.amazon.rum.first_input_delay_event, com.amazon.rum.cumulative_layout_shift_event,
    com.amazon.rum.interaction_to_next_paint_event, com.amazon.rum.performance_resource_event,
    com.amazon.rum.xray_trace_event, com.amazon.rum.dom_event

    Common fields: event_type, event_timestamp, metadata.pageUrl, metadata.browserName,
    metadata.osName, metadata.deviceType, metadata.countryCode, user_details.sessionId,
    event_details.* (varies by event type)

    Args:
        app_monitor_name: Name of the RUM app monitor.
        query_string: CW Logs Insights query string.
        start_time: ISO 8601 start time (e.g., '2026-03-01T00:00:00Z').
        end_time: ISO 8601 end time (e.g., '2026-03-18T00:00:00Z').
        max_results: Maximum results to return (default 1000).
    """
    try:
        log_group = _get_rum_log_group(app_monitor_name)
    except ValueError as e:
        return json.dumps({'error': str(e)})

    try:
        result = _run_logs_insights_query(
            log_group=log_group,
            query_string=query_string,
            start_time=_parse_time(start_time),
            end_time=_parse_time(end_time),
            max_results=max_results,
        )
        return json.dumps({
            'app_monitor': app_monitor_name,
            'log_group': log_group,
            'query': query_string,
            **result,
        }, indent=2, default=str)
    except Exception as e:
        return json.dumps({'error': str(e)})


# --- Wave 4: Pre-built web analytics ---


async def audit_rum_health(
    app_monitor_name: str,
    start_time: str,
    end_time: str,
) -> str:
    """Quick health check: "Are my users impacted right now?".

    Runs parallel queries for error rates, slowest pages, and sessions with most errors.
    Returns a combined health summary.

    Args:
        app_monitor_name: Name of the RUM app monitor.
        start_time: ISO 8601 start time.
        end_time: ISO 8601 end time.
    """
    from . import rum_queries

    try:
        log_group = _get_rum_log_group(app_monitor_name)
    except ValueError as e:
        return json.dumps({'error': str(e)})

    st = _parse_time(start_time)
    et = _parse_time(end_time)

    # Run 3 queries
    queries = {
        'error_breakdown': rum_queries.HEALTH_ERROR_RATE,
        'slowest_pages': rum_queries.HEALTH_SLOWEST_PAGES,
        'sessions_with_errors': rum_queries.HEALTH_SESSION_ERRORS,
    }
    results = {}
    for name, q in queries.items():
        try:
            results[name] = _run_logs_insights_query(log_group, q, st, et, max_results=10)
        except Exception as e:
            results[name] = {'status': 'Failed', 'error': str(e), 'results': []}

    return json.dumps({
        'app_monitor': app_monitor_name,
        'time_range': {'start': start_time, 'end': end_time},
        **results,
    }, indent=2, default=str)


async def get_rum_errors(
    app_monitor_name: str,
    start_time: str,
    end_time: str,
    page_url: Optional[str] = None,
    group_by: Optional[str] = None,
) -> str:
    """Get JS and HTTP errors grouped by message and page.

    Args:
        app_monitor_name: Name of the RUM app monitor.
        start_time: ISO 8601 start time.
        end_time: ISO 8601 end time.
        page_url: Optional page URL filter.
        group_by: Optional grouping: 'country', 'browser', 'device', 'os'.
    """
    from . import rum_queries

    try:
        log_group = _get_rum_log_group(app_monitor_name)
    except ValueError as e:
        return json.dumps({'error': str(e)})

    query = rum_queries.errors_query(page_url=page_url, group_by=group_by)
    result = _run_logs_insights_query(log_group, query, _parse_time(start_time), _parse_time(end_time))
    return json.dumps({
        'app_monitor': app_monitor_name,
        'query': query,
        **result,
    }, indent=2, default=str)


async def get_rum_performance(
    app_monitor_name: str,
    start_time: str,
    end_time: str,
    page_url: Optional[str] = None,
) -> str:
    """Get page load performance and Core Web Vitals (LCP, FID, CLS, INP).

    Runs two queries: navigation timings and web vitals, returns both.

    Args:
        app_monitor_name: Name of the RUM app monitor.
        start_time: ISO 8601 start time.
        end_time: ISO 8601 end time.
        page_url: Optional page URL filter.
    """
    from . import rum_queries

    try:
        log_group = _get_rum_log_group(app_monitor_name)
    except ValueError as e:
        return json.dumps({'error': str(e)})

    st = _parse_time(start_time)
    et = _parse_time(end_time)

    nav_result = _run_logs_insights_query(
        log_group, rum_queries.performance_navigation_query(page_url), st, et
    )
    vitals_result = _run_logs_insights_query(
        log_group, rum_queries.performance_web_vitals_query(page_url), st, et
    )

    return json.dumps({
        'app_monitor': app_monitor_name,
        'navigation_timings': nav_result,
        'web_vitals': vitals_result,
    }, indent=2, default=str)


async def get_rum_sessions(
    app_monitor_name: str,
    start_time: str,
    end_time: str,
) -> str:
    """Get recent sessions with browser, OS, device type, and event counts.

    Args:
        app_monitor_name: Name of the RUM app monitor.
        start_time: ISO 8601 start time.
        end_time: ISO 8601 end time.
    """
    from . import rum_queries

    try:
        log_group = _get_rum_log_group(app_monitor_name)
    except ValueError as e:
        return json.dumps({'error': str(e)})

    result = _run_logs_insights_query(
        log_group, rum_queries.SESSIONS_QUERY, _parse_time(start_time), _parse_time(end_time)
    )
    return json.dumps({'app_monitor': app_monitor_name, **result}, indent=2, default=str)


async def get_rum_page_views(
    app_monitor_name: str,
    start_time: str,
    end_time: str,
) -> str:
    """Get top pages by view count.

    Args:
        app_monitor_name: Name of the RUM app monitor.
        start_time: ISO 8601 start time.
        end_time: ISO 8601 end time.
    """
    from . import rum_queries

    try:
        log_group = _get_rum_log_group(app_monitor_name)
    except ValueError as e:
        return json.dumps({'error': str(e)})

    result = _run_logs_insights_query(
        log_group, rum_queries.PAGE_VIEWS_QUERY, _parse_time(start_time), _parse_time(end_time)
    )
    return json.dumps({'app_monitor': app_monitor_name, **result}, indent=2, default=str)


# --- Wave 4b: Time series, geo, HTTP requests, session detail, resources, page flows ---


async def get_rum_timeseries(
    app_monitor_name: str,
    start_time: str,
    end_time: str,
    metric: str = 'errors',
    bucket: str = '1h',
    page_url: Optional[str] = None,
) -> str:
    """Get time-bucketed trends for errors, performance, or sessions.

    Args:
        app_monitor_name: Name of the RUM app monitor.
        start_time: ISO 8601 start time.
        end_time: ISO 8601 end time.
        metric: 'errors', 'performance', or 'sessions' (default: errors).
        bucket: Time bucket size (default: '1h'). E.g. '5m', '15m', '1h', '1d'.
        page_url: Optional page URL filter.
    """
    from . import rum_queries

    try:
        log_group = _get_rum_log_group(app_monitor_name)
    except ValueError as e:
        return json.dumps({'error': str(e)})

    query_map = {
        'errors': rum_queries.errors_timeseries_query(bucket, page_url),
        'performance': rum_queries.performance_timeseries_query(bucket, page_url),
        'sessions': rum_queries.sessions_timeseries_query(bucket),
    }
    query = query_map.get(metric)
    if not query:
        return json.dumps({'error': f"Unknown metric '{metric}'. Use: errors, performance, sessions."})

    result = _run_logs_insights_query(log_group, query, _parse_time(start_time), _parse_time(end_time))
    return json.dumps({'app_monitor': app_monitor_name, 'metric': metric, 'bucket': bucket, **result}, indent=2, default=str)


async def get_rum_locations(
    app_monitor_name: str,
    start_time: str,
    end_time: str,
    page_url: Optional[str] = None,
) -> str:
    """Get session counts and performance by country.

    Args:
        app_monitor_name: Name of the RUM app monitor.
        start_time: ISO 8601 start time.
        end_time: ISO 8601 end time.
        page_url: Optional page URL filter.
    """
    from . import rum_queries

    try:
        log_group = _get_rum_log_group(app_monitor_name)
    except ValueError as e:
        return json.dumps({'error': str(e)})

    st = _parse_time(start_time)
    et = _parse_time(end_time)
    sessions_result = _run_logs_insights_query(log_group, rum_queries.geo_sessions_query(page_url), st, et)
    perf_result = _run_logs_insights_query(log_group, rum_queries.geo_performance_query(page_url), st, et)

    return json.dumps({
        'app_monitor': app_monitor_name,
        'sessions_by_country': sessions_result,
        'performance_by_country': perf_result,
    }, indent=2, default=str)


async def get_rum_http_requests(
    app_monitor_name: str,
    start_time: str,
    end_time: str,
    page_url: Optional[str] = None,
) -> str:
    """Get top HTTP requests by URL with latency and error rates.

    Args:
        app_monitor_name: Name of the RUM app monitor.
        start_time: ISO 8601 start time.
        end_time: ISO 8601 end time.
        page_url: Optional page URL filter.
    """
    from . import rum_queries

    try:
        log_group = _get_rum_log_group(app_monitor_name)
    except ValueError as e:
        return json.dumps({'error': str(e)})

    result = _run_logs_insights_query(
        log_group, rum_queries.http_requests_query(page_url),
        _parse_time(start_time), _parse_time(end_time),
    )
    return json.dumps({'app_monitor': app_monitor_name, **result}, indent=2, default=str)


async def get_rum_session_detail(
    app_monitor_name: str,
    session_id: str,
    start_time: str,
    end_time: str,
) -> str:
    """Get all events for a single session in chronological order.

    Args:
        app_monitor_name: Name of the RUM app monitor.
        session_id: The session ID to look up.
        start_time: ISO 8601 start time.
        end_time: ISO 8601 end time.
    """
    from . import rum_queries

    try:
        log_group = _get_rum_log_group(app_monitor_name)
    except ValueError as e:
        return json.dumps({'error': str(e)})

    result = _run_logs_insights_query(
        log_group, rum_queries.session_detail_query(session_id),
        _parse_time(start_time), _parse_time(end_time),
    )
    return json.dumps({'app_monitor': app_monitor_name, 'session_id': session_id, **result}, indent=2, default=str)


async def get_rum_resources(
    app_monitor_name: str,
    start_time: str,
    end_time: str,
    page_url: Optional[str] = None,
) -> str:
    """Get top resource requests by duration and size.

    Args:
        app_monitor_name: Name of the RUM app monitor.
        start_time: ISO 8601 start time.
        end_time: ISO 8601 end time.
        page_url: Optional page URL filter.
    """
    from . import rum_queries

    try:
        log_group = _get_rum_log_group(app_monitor_name)
    except ValueError as e:
        return json.dumps({'error': str(e)})

    result = _run_logs_insights_query(
        log_group, rum_queries.resource_requests_query(page_url),
        _parse_time(start_time), _parse_time(end_time),
    )
    return json.dumps({'app_monitor': app_monitor_name, **result}, indent=2, default=str)


async def get_rum_page_flows(
    app_monitor_name: str,
    start_time: str,
    end_time: str,
) -> str:
    """Get page-to-page navigation flows (approximates user journey).

    Args:
        app_monitor_name: Name of the RUM app monitor.
        start_time: ISO 8601 start time.
        end_time: ISO 8601 end time.
    """
    from . import rum_queries

    try:
        log_group = _get_rum_log_group(app_monitor_name)
    except ValueError as e:
        return json.dumps({'error': str(e)})

    result = _run_logs_insights_query(
        log_group, rum_queries.PAGE_FLOWS_QUERY,
        _parse_time(start_time), _parse_time(end_time),
    )
    return json.dumps({'app_monitor': app_monitor_name, **result}, indent=2, default=str)


# --- Wave 5: Mobile analytics (experimental) + Anomaly detection ---


async def get_rum_crashes(
    app_monitor_name: str,
    start_time: str,
    end_time: str,
    platform: str = 'all',
) -> str:
    """Get mobile crashes and stability issues.

    iOS: crashes and hangs. Android: crashes and ANRs.
    Android queries validated against real data. iOS queries are experimental.

    Args:
        app_monitor_name: Name of the RUM app monitor.
        start_time: ISO 8601 start time.
        end_time: ISO 8601 end time.
        platform: 'ios', 'android', or 'all' (default).
    """
    from . import rum_queries

    try:
        log_group = _get_rum_log_group(app_monitor_name)
    except ValueError as e:
        return json.dumps({'error': str(e)})

    st = _parse_time(start_time)
    et = _parse_time(end_time)
    results = {}

    if platform in ('ios', 'all'):
        results['ios'] = _run_logs_insights_query(log_group, rum_queries.MOBILE_CRASHES_IOS, st, et)
    if platform in ('android', 'all'):
        results['android'] = _run_logs_insights_query(log_group, rum_queries.MOBILE_CRASHES_ANDROID, st, et)
        results['android_anrs'] = _run_logs_insights_query(log_group, rum_queries.MOBILE_ANRS_ANDROID, st, et)

    return json.dumps({
        'app_monitor': app_monitor_name,
        'note': 'Android validated. iOS field paths are experimental.',
        **results,
    }, indent=2, default=str)


async def get_rum_app_launches(
    app_monitor_name: str,
    start_time: str,
    end_time: str,
    platform: str = 'all',
) -> str:
    """Get mobile app launch performance (cold/warm/pre-warm).

    Android queries validated against real data. iOS queries are experimental.

    Args:
        app_monitor_name: Name of the RUM app monitor.
        start_time: ISO 8601 start time.
        end_time: ISO 8601 end time.
        platform: 'ios', 'android', or 'all' (default).
    """
    from . import rum_queries

    try:
        log_group = _get_rum_log_group(app_monitor_name)
    except ValueError as e:
        return json.dumps({'error': str(e)})

    st = _parse_time(start_time)
    et = _parse_time(end_time)
    results = {}

    if platform in ('ios', 'all'):
        results['ios'] = _run_logs_insights_query(log_group, rum_queries.MOBILE_APP_LAUNCHES_IOS, st, et)
    if platform in ('android', 'all'):
        results['android'] = _run_logs_insights_query(log_group, rum_queries.MOBILE_APP_LAUNCHES_ANDROID, st, et)

    return json.dumps({
        'app_monitor': app_monitor_name,
        'note': 'Android validated. iOS field paths are experimental.',
        **results,
    }, indent=2, default=str)


async def analyze_rum_log_group(
    app_monitor_name: str,
    start_time: str,
    end_time: str,
) -> str:
    """Analyze a RUM log group for anomalies and common patterns.

    Checks for anomaly detectors, retrieves anomalies, and identifies
    top message patterns and error patterns.

    Args:
        app_monitor_name: Name of the RUM app monitor.
        start_time: ISO 8601 start time.
        end_time: ISO 8601 end time.
    """
    from . import rum_queries

    try:
        log_group = _get_rum_log_group(app_monitor_name)
    except ValueError as e:
        return json.dumps({'error': str(e)})

    st = _parse_time(start_time)
    et = _parse_time(end_time)

    # Check for anomaly detectors
    anomaly_info = {'detectors': [], 'anomalies': []}
    try:
        detectors_resp = logs_client.list_log_anomaly_detectors(filterLogGroupArn=log_group)
        detectors = detectors_resp.get('anomalyDetectors', [])
        anomaly_info['detectors'] = [
            {'name': d.get('detectorName'), 'status': d.get('anomalyDetectorStatus')}
            for d in detectors
        ]
        for d in detectors:
            arn = d.get('anomalyDetectorArn')
            if arn:
                try:
                    anomalies_resp = logs_client.list_anomalies(anomalyDetectorArn=arn)
                    for a in anomalies_resp.get('anomalies', []):
                        ts = a.get('firstSeen', 0)
                        if isinstance(ts, (int, float)) and st.timestamp() <= ts <= et.timestamp():
                            anomaly_info['anomalies'].append(remove_null_values(a))
                except Exception:
                    pass
    except Exception as e:
        anomaly_info['error'] = str(e)

    # Run pattern queries
    top_patterns = _run_logs_insights_query(log_group, rum_queries.TOP_PATTERNS_QUERY, st, et)
    error_patterns = _run_logs_insights_query(log_group, rum_queries.ERROR_PATTERNS_QUERY, st, et)

    return json.dumps({
        'app_monitor': app_monitor_name,
        'anomaly_detection': anomaly_info,
        'top_patterns': top_patterns,
        'error_patterns': error_patterns,
    }, indent=2, default=str)


# --- Wave 6: Correlation + Metrics ---


async def correlate_rum_to_backend(
    app_monitor_name: str,
    page_url: str,
    start_time: str,
    end_time: str,
    max_traces: int = 10,
) -> str:
    """Correlate frontend RUM events to backend X-Ray traces.

    Finds X-Ray trace IDs from slow pages in CW Logs, then retrieves
    full trace details via X-Ray BatchGetTraces.

    Requires X-Ray to be enabled on the app monitor.

    Args:
        app_monitor_name: Name of the RUM app monitor.
        page_url: Page URL to investigate (e.g., '/checkout').
        start_time: ISO 8601 start time.
        end_time: ISO 8601 end time.
        max_traces: Maximum traces to retrieve (default 10).
    """
    from . import rum_queries

    try:
        log_group = _get_rum_log_group(app_monitor_name)
    except ValueError as e:
        return json.dumps({'error': str(e)})

    # Step 1: Find trace IDs from CW Logs
    query = rum_queries.trace_ids_for_page_query(page_url)
    logs_result = _run_logs_insights_query(
        log_group, query, _parse_time(start_time), _parse_time(end_time), max_results=max_traces
    )

    trace_ids = [
        r.get('event_details.trace_id')
        for r in logs_result.get('results', [])
        if r.get('event_details.trace_id')
    ]

    if not trace_ids:
        return json.dumps({
            'app_monitor': app_monitor_name,
            'page_url': page_url,
            'message': 'No X-Ray trace events found. Ensure X-Ray is enabled and http telemetry is active.',
            'logs_query_result': logs_result,
        }, indent=2, default=str)

    # Step 2: Get full traces via X-Ray
    traces = []
    # BatchGetTraces accepts max 5 IDs per call
    for i in range(0, len(trace_ids), 5):
        batch = trace_ids[i:i + 5]
        try:
            resp = xray_client.batch_get_traces(TraceIds=batch)
            traces.extend(resp.get('Traces', []))
        except Exception as e:
            logger.warning(f'Failed to get traces {batch}: {e}')

    # Summarize backend services from trace segments
    services = {}
    for trace in traces:
        for segment in trace.get('Segments', []):
            try:
                doc = json.loads(segment.get('Document', '{}'))
                svc_name = doc.get('name', 'unknown')
                duration = doc.get('end_time', 0) - doc.get('start_time', 0)
                if svc_name not in services:
                    services[svc_name] = {'calls': 0, 'total_duration': 0, 'errors': 0}
                services[svc_name]['calls'] += 1
                services[svc_name]['total_duration'] += duration
                if doc.get('error') or doc.get('fault'):
                    services[svc_name]['errors'] += 1
            except Exception:
                pass

    return json.dumps({
        'app_monitor': app_monitor_name,
        'page_url': page_url,
        'trace_ids': trace_ids,
        'trace_count': len(traces),
        'backend_services': services,
    }, indent=2, default=str)


async def get_rum_metrics(
    app_monitor_name: str,
    metric_names: str,
    start_time: str,
    end_time: str,
    statistic: str = 'Average',
    period: int = 300,
) -> str:
    """Get vended CloudWatch metrics from the AWS/RUM namespace.

    Common metrics: JsErrorCount, SessionCount, PageViewCount,
    WebVitalsLargestContentfulPaint, WebVitalsFirstInputDelay,
    WebVitalsCumulativeLayoutShift, PerformanceNavigationDuration,
    Http4xxCount, Http5xxCount, CrashCount, ColdLaunchTime, WarmLaunchTime.

    Args:
        app_monitor_name: Name of the RUM app monitor (used as application_name dimension).
        metric_names: JSON array of metric names, e.g. '["JsErrorCount","SessionCount"]'.
        start_time: ISO 8601 start time.
        end_time: ISO 8601 end time.
        statistic: Statistic type: Average, Sum, Minimum, Maximum, SampleCount (default: Average).
        period: Period in seconds (default: 300).
    """
    names = json.loads(metric_names)
    st = _parse_time(start_time)
    et = _parse_time(end_time)

    queries = []
    for i, name in enumerate(names):
        queries.append({
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
        })

    try:
        resp = cloudwatch_client.get_metric_data(
            MetricDataQueries=queries,
            StartTime=st,
            EndTime=et,
        )
        results = {}
        for mr in resp.get('MetricDataResults', []):
            idx = int(mr['Id'][1:])
            metric_name = names[idx]
            results[metric_name] = {
                'timestamps': [t.isoformat() for t in mr.get('Timestamps', [])],
                'values': mr.get('Values', []),
                'statistic': statistic,
                'status': mr.get('StatusCode', 'Unknown'),
            }
        return json.dumps({
            'app_monitor': app_monitor_name,
            'metrics': results,
        }, indent=2, default=str)
    except Exception as e:
        return json.dumps({'error': str(e)})


# ---------------------------------------------------------------------------
# Wire action map (must come after all function definitions)
# ---------------------------------------------------------------------------

_ACTION_MAP.update({
    'check_data_access': check_rum_data_access,
    'list_monitors': list_rum_app_monitors,
    'get_monitor': get_rum_app_monitor,
    'list_tags': list_rum_tags,
    'get_policy': get_rum_resource_policy,
    'query': query_rum_events,
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
})
