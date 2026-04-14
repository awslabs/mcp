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

"""CloudWatch Application Signals MCP Server - RUM tools."""

import json
import time
from .aws_clients import cloudwatch_client, logs_client, rum_client, xray_client
from .utils import remove_null_values
from datetime import datetime, timezone
from loguru import logger
from typing import Optional


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
            f'To enable it, call update_rum_app_monitor with CwLogEnabled=true. '
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
            'fix': 'Call update_rum_app_monitor with CwLogEnabled=true. Recommended retention: 30 days.',
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


async def create_rum_app_monitor(
    name: str,
    domain: str,
    cw_log_enabled: bool = True,
    enable_xray: bool = False,
    session_sample_rate: float = 1.0,
    telemetries: Optional[str] = None,
    allow_cookies: bool = True,
) -> str:
    """Create a new CloudWatch RUM app monitor.

    Defaults CwLogEnabled=true so Logs Insights analytics work immediately.
    Telemetries defaults to ['errors', 'performance', 'http'] if not specified.

    Args:
        name: App monitor name.
        domain: Domain to monitor (e.g., 'example.com').
        cw_log_enabled: Enable CW Logs for analytics (default: true).
        enable_xray: Enable X-Ray tracing (default: false).
        session_sample_rate: 0.0-1.0 proportion of sessions to record (default: 1.0).
        telemetries: JSON array of telemetry types, e.g. '["errors","performance","http"]'.
        allow_cookies: Enable cookies for session tracking (default: true).
    """
    telem_list = json.loads(telemetries) if telemetries else ['errors', 'performance', 'http']
    try:
        resp = rum_client.create_app_monitor(
            Name=name,
            Domain=domain,
            CwLogEnabled=cw_log_enabled,
            AppMonitorConfiguration={
                'EnableXRay': enable_xray,
                'SessionSampleRate': session_sample_rate,
                'Telemetries': telem_list,
                'AllowCookies': allow_cookies,
            },
        )
        return json.dumps({
            'id': resp.get('Id'),
            'name': name,
            'cw_log_enabled': cw_log_enabled,
            'message': f"App monitor '{name}' created. CW Logs {'enabled' if cw_log_enabled else 'disabled'}.",
        })
    except Exception as e:
        return json.dumps({'error': str(e)})


async def update_rum_app_monitor(
    app_monitor_name: str,
    domain: Optional[str] = None,
    cw_log_enabled: Optional[bool] = None,
    enable_xray: Optional[bool] = None,
    session_sample_rate: Optional[float] = None,
    telemetries: Optional[str] = None,
    allow_cookies: Optional[bool] = None,
) -> str:
    """Update a CloudWatch RUM app monitor configuration.

    Only specified fields are updated; others remain unchanged.

    Args:
        app_monitor_name: Name of the app monitor to update.
        domain: New domain.
        cw_log_enabled: Enable/disable CW Logs.
        enable_xray: Enable/disable X-Ray.
        session_sample_rate: New sample rate (0.0-1.0).
        telemetries: JSON array of telemetry types.
        allow_cookies: Enable/disable cookies.
    """
    kwargs = {'Name': app_monitor_name}
    if domain is not None:
        kwargs['Domain'] = domain
    if cw_log_enabled is not None:
        kwargs['CwLogEnabled'] = cw_log_enabled

    config = {}
    if enable_xray is not None:
        config['EnableXRay'] = enable_xray
    if session_sample_rate is not None:
        config['SessionSampleRate'] = session_sample_rate
    if telemetries is not None:
        config['Telemetries'] = json.loads(telemetries)
    if allow_cookies is not None:
        config['AllowCookies'] = allow_cookies
    if config:
        kwargs['AppMonitorConfiguration'] = config

    try:
        rum_client.update_app_monitor(**kwargs)
        return json.dumps({'message': f"App monitor '{app_monitor_name}' updated.", 'updated_fields': list(kwargs.keys())})
    except Exception as e:
        return json.dumps({'error': str(e)})


async def delete_rum_app_monitor(app_monitor_name: str) -> str:
    """Delete a CloudWatch RUM app monitor.

    WARNING: This permanently deletes the app monitor and stops all data collection.
    CW Logs data in the log group is NOT deleted (managed by log group retention).
    """
    try:
        rum_client.delete_app_monitor(Name=app_monitor_name)
        return json.dumps({'message': f"App monitor '{app_monitor_name}' deleted."})
    except Exception as e:
        return json.dumps({'error': str(e)})


async def tag_rum_resource(resource_arn: str, tags: str) -> str:
    """Add tags to a RUM resource (app monitor).

    Args:
        resource_arn: ARN of the app monitor.
        tags: JSON object of key-value tag pairs, e.g. '{"env":"prod","team":"frontend"}'.
    """
    try:
        rum_client.tag_resource(ResourceArn=resource_arn, Tags=json.loads(tags))
        return json.dumps({'message': f'Tags added to {resource_arn}.'})
    except Exception as e:
        return json.dumps({'error': str(e)})


async def untag_rum_resource(resource_arn: str, tag_keys: str) -> str:
    """Remove tags from a RUM resource (app monitor).

    Args:
        resource_arn: ARN of the app monitor.
        tag_keys: JSON array of tag keys to remove, e.g. '["env","team"]'.
    """
    try:
        rum_client.untag_resource(ResourceArn=resource_arn, TagKeys=json.loads(tag_keys))
        return json.dumps({'message': f'Tags removed from {resource_arn}.'})
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


async def put_rum_resource_policy(app_monitor_name: str, policy_document: str) -> str:
    """Set a resource-based policy on a RUM app monitor.

    Controls who can call PutRumEvents. Common use: allow unauthenticated
    ingestion for mobile apps or web apps without Cognito.

    Args:
        app_monitor_name: Name of the app monitor.
        policy_document: JSON policy document string.
    """
    try:
        rum_client.put_resource_policy(Name=app_monitor_name, PolicyDocument=policy_document)
        return json.dumps({'message': f"Resource policy set on '{app_monitor_name}'."})
    except Exception as e:
        return json.dumps({'error': str(e)})


async def delete_rum_resource_policy(app_monitor_name: str) -> str:
    """Delete the resource-based policy from a RUM app monitor.

    WARNING: This removes all resource-based access. Unauthenticated clients
    will no longer be able to send telemetry.
    """
    try:
        rum_client.delete_resource_policy(Name=app_monitor_name)
        return json.dumps({'message': f"Resource policy deleted from '{app_monitor_name}'."})
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
