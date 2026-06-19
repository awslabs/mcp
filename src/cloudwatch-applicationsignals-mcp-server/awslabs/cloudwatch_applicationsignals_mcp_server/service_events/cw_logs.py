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

"""CloudWatch Logs Insights data layer for ServiceEvents service_events records.

ServiceEvents telemetry is emitted as OTLP "service_events" log records to one
CloudWatch Logs group per service: ``/aws/service-events/{service.name}``. Each
record is a JSON document with this shape::

    {
      "resource": {"attributes": {"service.name": ..., "deployment.environment.name": ...}},
      "attributes": {"aws.service_events.operation": ..., "event.name": ..., ...},
      "body": {...},                      # event-type specific
      "eventName": "aws.service_events.<type>",
      "timeUnixNano": ...,
      "traceId": ..., "spanId": ...
    }

The ``attributes`` object uses keys that contain literal dots
(``"aws.service_events.operation"``), which CloudWatch Logs Insights cannot
disambiguate from JSON nesting. We therefore fetch ``@message`` and parse the
JSON in Python rather than projecting deep fields in the query.
"""

import json
import logging
import os
import time
from typing import Any, Dict, List, Optional


logger = logging.getLogger(__name__)

# Event-type discriminators (value of top-level ``eventName`` / ``attributes."event.name"``).
EVENT_ENDPOINT_SUMMARY = 'aws.service_events.endpoint_summary'
EVENT_INCIDENT_SNAPSHOT = 'aws.service_events.incident_snapshot'
EVENT_DEPLOYMENT_EVENT = 'aws.service_events.deployment_event'

# One log group per service: /aws/service-events/{service.name}. Overridable for
# deployments that use a different naming convention.
DEFAULT_LOG_GROUP_PREFIX = '/aws/service-events/'

# Polling configuration for Logs Insights queries.
QUERY_TIMEOUT_SECONDS = 30
QUERY_POLL_INTERVAL_SECONDS = 1

# Cap on log groups scanned in the cross-service (wildcard) case. CloudWatch
# Logs Insights accepts at most 50 log groups per query.
MAX_WILDCARD_LOG_GROUPS = 50


class CwLogsQueryError(Exception):
    """Raised when a CloudWatch Logs Insights query fails."""


def _log_group_prefix() -> str:
    return os.environ.get('SERVICE_EVENTS_LOG_GROUP_PREFIX', DEFAULT_LOG_GROUP_PREFIX)


def _log_group_for(service_name: str) -> str:
    """Return the per-service log group name ``/aws/service-events/{service_name}``."""
    prefix = _log_group_prefix()
    if not prefix.endswith('/'):
        prefix += '/'
    return f'{prefix}{service_name}'


def _region() -> str:
    """Resolve AWS region: AWS_REGION env var > profile/config > us-east-1."""
    from ..aws_clients import AWS_REGION

    return AWS_REGION


_logs_client = None


def _get_logs_client():
    """Return a lazily-built CloudWatch Logs boto3 client."""
    global _logs_client
    if _logs_client is None:
        import boto3

        _logs_client = boto3.client('logs', region_name=_region())
    return _logs_client


def _reset_client() -> None:
    """Drop the cached logs client (test hook)."""
    global _logs_client
    _logs_client = None


def _resolve_log_groups(service_name: Optional[str]) -> List[str]:
    """Resolve which log group(s) to query.

    When ``service_name`` is provided, query that service's group directly.
    Otherwise, enumerate all ``/aws/service-events/*`` groups (capped) for a
    cross-service query.
    """
    if service_name:
        return [_log_group_for(service_name)]

    prefix = _log_group_prefix()
    try:
        client = _get_logs_client()
        groups: List[str] = []
        paginator = client.get_paginator('describe_log_groups')
        for page in paginator.paginate(logGroupNamePrefix=prefix):
            for lg in page.get('logGroups', []):
                name = lg.get('logGroupName')
                if name:
                    groups.append(name)
                if len(groups) >= MAX_WILDCARD_LOG_GROUPS:
                    break
            if len(groups) >= MAX_WILDCARD_LOG_GROUPS:
                logger.warning(
                    'service_events log group scan capped at %d groups (prefix=%s); '
                    'some services may be omitted. Pass service_name to target one group.',
                    MAX_WILDCARD_LOG_GROUPS,
                    prefix,
                )
                break
        return groups
    except Exception as e:  # pylint: disable=broad-exception-caught
        logger.warning(f'Failed to enumerate service_events log groups (prefix={prefix}): {e}')
        return []


def run_insights_query(
    event_name: str,
    hours: int,
    service_name: Optional[str] = None,
    limit: int = 100,
    extra_query_filter: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Run a Logs Insights query for one service_events event type and return parsed records.

    Args:
        event_name: The ``eventName`` discriminator to filter on (one of the EVENT_* constants).
        hours: Look-back window in hours.
        service_name: When provided, query ``/aws/service-events/{service_name}`` directly;
            otherwise scan all ``/aws/service-events/*`` groups.
        limit: Max records to return from the query.
        extra_query_filter: Optional additional Logs Insights ``filter`` clause appended
            to the query (used only for fields safe to reference, e.g. top-level ``eventName``).

    Returns:
        List of parsed OTLP record dicts (the JSON ``@message`` of each matching log event),
        newest first. Returns ``[]`` when no log groups exist or no records match.
    """
    log_groups = _resolve_log_groups(service_name)
    if not log_groups:
        logger.debug('No service_events log groups resolved (service_name=%s)', service_name)
        return []

    query_parts = [
        'fields @message, @timestamp',
        f'filter eventName = "{event_name}"',
    ]
    if extra_query_filter:
        query_parts.append(extra_query_filter)
    query_parts.append('sort @timestamp desc')
    query_parts.append(f'limit {limit}')
    query_string = ' | '.join(query_parts)

    rows = _execute(query_string, hours, log_groups)

    records: List[Dict[str, Any]] = []
    for row in rows:
        message = row.get('@message')
        if not message:
            continue
        try:
            records.append(json.loads(message))
        except (ValueError, TypeError) as e:
            logger.debug(f'Skipping unparsable log message: {e}')
    return records


def _execute(query_string: str, hours: int, log_groups: List[str]) -> List[Dict[str, str]]:
    """Execute a Logs Insights query string and poll for results.

    Returns a list of ``{field: value}`` dicts (one per result row). Raises
    CwLogsQueryError on start/poll failure.
    """
    client = _get_logs_client()
    end_epoch = int(time.time())
    start_epoch = end_epoch - hours * 3600

    try:
        start_response = client.start_query(
            logGroupNames=log_groups,
            startTime=start_epoch,
            endTime=end_epoch,
            queryString=query_string,
        )
    except Exception as e:  # pylint: disable=broad-exception-caught
        raise CwLogsQueryError(f'Failed to start query: {e}') from e

    query_id = start_response.get('queryId')
    if not query_id:
        raise CwLogsQueryError(
            f'start_query did not return a queryId (response: {start_response})'
        )

    poll_start = time.time()
    while time.time() - poll_start < QUERY_TIMEOUT_SECONDS:
        try:
            response = client.get_query_results(queryId=query_id)
        except Exception as e:  # pylint: disable=broad-exception-caught
            raise CwLogsQueryError(f'Failed to get query results: {e}') from e

        status = response.get('status', 'Unknown')
        if status in ('Complete', 'Failed', 'Cancelled'):
            if status != 'Complete':
                raise CwLogsQueryError(f'Query {status} (queryId={query_id})')
            return [
                {field.get('field', ''): field.get('value', '') for field in line}
                for line in response.get('results', [])
            ]

        time.sleep(QUERY_POLL_INTERVAL_SECONDS)

    raise CwLogsQueryError(
        f'Query did not complete within {QUERY_TIMEOUT_SECONDS}s (queryId={query_id})'
    )


# ---------------------------------------------------------------------------
# OTLP record field accessors (defensive — examples vary in resource shape)
# ---------------------------------------------------------------------------


def _attrs(record: Dict[str, Any]) -> Dict[str, Any]:
    """Return the top-level ``attributes`` block."""
    return record.get('attributes') or {}


def _resource_attrs(record: Dict[str, Any]) -> Dict[str, Any]:
    """Return resource attributes, tolerating both flat and nested ``resource`` shapes."""
    resource = record.get('resource') or {}
    if isinstance(resource.get('attributes'), dict):
        return resource['attributes']
    return resource


def _service_name(record: Dict[str, Any]) -> Optional[str]:
    return _resource_attrs(record).get('service.name') or _resource_attrs(record).get(
        'aws.local.service'
    )


def _environment(record: Dict[str, Any]) -> Optional[str]:
    res = _resource_attrs(record)
    return res.get('deployment.environment.name') or res.get('deployment.environment')


def _operation(record: Dict[str, Any]) -> Optional[str]:
    return _attrs(record).get('aws.service_events.operation')


def _avg_ms_from_duration(duration: Dict[str, Any]) -> Optional[float]:
    """Compute average latency in ms from a service_events ``duration`` block (microseconds)."""
    if not duration:
        return None
    count = duration.get('Count') or 0
    total = duration.get('Sum') or 0
    if not count:
        return None
    return round((total / count) / 1000.0, 2)


def _percentile_ms_from_duration(duration: Dict[str, Any], percentile: float) -> Optional[float]:
    """Approximate a percentile (ms) from the sparse ``duration`` histogram (microseconds).

    The ``duration`` block holds parallel ``Values`` (bucket midpoints, microseconds)
    and ``Counts`` arrays. Walks the cumulative distribution to the target rank.
    """
    if not duration:
        return None
    values = duration.get('Values') or []
    counts = duration.get('Counts') or []
    if not values or not counts or len(values) != len(counts):
        return None

    pairs = sorted(zip(values, counts), key=lambda p: p[0])
    total = sum(c for _, c in pairs)
    if total <= 0:
        return None

    target_rank = total * (percentile / 100.0)
    cumulative = 0
    for value, count in pairs:
        cumulative += count
        if cumulative >= target_rank:
            return round(value / 1000.0, 2)
    return round(pairs[-1][0] / 1000.0, 2)


# ---------------------------------------------------------------------------
# Typed query helpers (consumed by the ServiceEvents tools)
# ---------------------------------------------------------------------------


def query_endpoint_summaries(
    service_name: Optional[str] = None,
    hours: int = 24,
    operation: Optional[str] = None,
    limit: int = 20,
    percentile: float = 99,
) -> List[Dict[str, Any]]:
    """Return normalized endpoint summaries from service_events ``endpoint_summary`` records.

    When ``operation`` is given, results are filtered (substring, case-insensitive)
    in Python. Returns at most ``limit`` summaries.
    """
    # Fetch extra candidates so a Python-side operation filter still yields up to `limit`.
    records = run_insights_query(
        EVENT_ENDPOINT_SUMMARY,
        hours=hours,
        service_name=service_name,
        limit=limit * 5 if operation else limit,
    )

    summaries: List[Dict[str, Any]] = []
    op_filter = operation.lower() if operation else None
    for record in records:
        attrs = _attrs(record)
        op = _operation(record) or 'unknown'
        if op_filter and op_filter not in op.lower():
            continue

        body = record.get('body') or {}
        duration = body.get('duration') or {}
        summary = {
            'operation': op,
            'method': attrs.get('http.request.method', 'unknown'),
            'route': attrs.get('url.route', 'unknown'),
            'service_name': _service_name(record) or 'unknown',
            'environment': _environment(record) or 'unknown',
            'total_requests': attrs.get('aws.service_events.request.count', 0),
            'total_faults': attrs.get('aws.service_events.request.faults', 0),
            'total_errors': attrs.get('aws.service_events.request.errors', 0),
            'total_incidents': attrs.get('aws.service_events.incident.count') or 0,
            'avg_duration_ms': _avg_ms_from_duration(duration),
            f'p{int(percentile)}_duration_ms': _percentile_ms_from_duration(duration, percentile),
            'deployment_id': attrs.get('aws.service_events.deployment.id'),
        }

        error_breakdown = body.get('exception_breakdown')
        if error_breakdown:
            summary['error_breakdown'] = error_breakdown

        summaries.append(summary)
        if len(summaries) >= limit:
            break

    return summaries


def query_incidents(
    service_name: Optional[str] = None,
    hours: int = 24,
    trigger_type: Optional[str] = None,
    endpoint: Optional[str] = None,
    limit: int = 50,
) -> List[Dict[str, Any]]:
    """Return raw service_events ``incident_snapshot`` records (newest first).

    ``trigger_type`` (e.g. "exception"/"latency") and ``endpoint`` (operation
    substring) filters are applied in Python. The full OTLP records are returned
    so callers can build either summaries or full RCA detail.
    """
    records = run_insights_query(
        EVENT_INCIDENT_SNAPSHOT,
        hours=hours,
        service_name=service_name,
        limit=limit,
    )

    trigger_filter = trigger_type.lower() if trigger_type else None
    endpoint_filter = endpoint.lower() if endpoint else None
    filtered: List[Dict[str, Any]] = []
    for record in records:
        attrs = _attrs(record)
        if (
            trigger_filter
            and (attrs.get('aws.service_events.trigger_type') or '').lower() != trigger_filter
        ):
            continue
        if endpoint_filter and endpoint_filter not in (_operation(record) or '').lower():
            continue
        filtered.append(record)
    return filtered


def query_incident_by_id(
    snapshot_id: str,
    hours: int = 72,
    service_name: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """Return the full service_events ``incident_snapshot`` record for a snapshot id, or None."""
    records = run_insights_query(
        EVENT_INCIDENT_SNAPSHOT,
        hours=hours,
        service_name=service_name,
        limit=500,
    )
    for record in records:
        if _attrs(record).get('aws.service_events.snapshot_id') == snapshot_id:
            return record
    return None


def query_deployments(
    service_name: Optional[str] = None,
    hours: int = 168,
    commit: Optional[str] = None,
    limit: int = 50,
) -> List[Dict[str, Any]]:
    """Return normalized deployments from service_events ``deployment_event`` records.

    When ``commit`` is given, results are filtered by commit-SHA prefix in Python.

    Records are de-duplicated and collapsed **per unique commit SHA** to avoid
    confusing repeats (the SDK re-emits deployment events periodically and on every
    restart):

    - If a commit has any ``startup`` events (process start/restart), only those are
      kept (one per distinct ``deployment_id``) and its ``periodic`` re-emissions are
      dropped — restarts are real, periodic timer re-emits are noise.
    - If a commit has only ``periodic`` events (no startup observed in the window),
      a single representative entry is shown for that commit.

    Newest-first ordering is preserved.
    """
    records = run_insights_query(
        EVENT_DEPLOYMENT_EVENT,
        hours=hours,
        service_name=service_name,
        limit=limit * 5 if commit else limit,
    )

    commit_prefix = commit.lower() if commit else None

    # Normalize matching records, grouped by commit SHA (input is newest-first).
    by_commit: Dict[str, List[Dict[str, Any]]] = {}
    commit_order: List[str] = []
    for record in records:
        attrs = _attrs(record)
        sha = attrs.get('vcs.ref.head.revision') or ''
        if commit_prefix and not sha.lower().startswith(commit_prefix):
            continue

        entry = {
            'git_commit_sha': sha or None,
            'git_repo_url': attrs.get('vcs.repository.url.full', 'unknown'),
            'deployment_url': attrs.get('aws.service_events.deployment.url', 'unknown'),
            'deployed_at': attrs.get('aws.service_events.deployment.timestamp', 'unknown'),
            'deployment_id': attrs.get('aws.service_events.deployment.id'),
            'trigger': attrs.get('aws.service_events.deployment.trigger'),
            'service_name': _service_name(record),
            'environment': _environment(record),
        }
        key = str(sha or entry['deployment_id'] or id(record))
        if key not in by_commit:
            by_commit[key] = []
            commit_order.append(key)
        by_commit[key].append(entry)

    # Collapse per commit: prefer startup entries (one per deployment_id); else a
    # single representative periodic entry.
    deployments: List[Dict[str, Any]] = []
    for key in commit_order:
        entries = by_commit[key]
        startups = [e for e in entries if (e.get('trigger') or '').lower() == 'startup']
        if startups:
            seen_ids = set()
            for e in startups:
                dep_id = e.get('deployment_id')
                if dep_id in seen_ids:
                    continue
                seen_ids.add(dep_id)
                deployments.append(e)
        else:
            deployments.append(entries[0])
        if len(deployments) >= limit:
            break

    return deployments[:limit]
