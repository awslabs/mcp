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

"""Per-operation (endpoint) RED metrics from Application Signals.

When Application Signals is enabled for a service, endpoint-level telemetry is
not emitted to the service_events CloudWatch Logs group. Instead, RED metrics
(Requests, Errors/Faults, Duration/latency) are available per operation via the
Application Signals ``list_service_operations`` API plus CloudWatch
``get_metric_statistics``. This module assembles those into endpoint summaries
shaped like the service_events ``get_endpoints`` output.
"""

import logging
from .aws_clients import get_applicationsignals_client, get_cloudwatch_client
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional


logger = logging.getLogger(__name__)

# Application Signals operation metric types.
_METRIC_LATENCY = 'Latency'
_METRIC_FAULT = 'Fault'
_METRIC_ERROR = 'Error'


def _period_for_hours(hours: int) -> int:
    """Pick a CloudWatch metric period (seconds) appropriate for the time range."""
    if hours <= 3:
        return 60
    if hours <= 24:
        return 300
    return 3600


def _find_service_key_attributes(
    service_name: str, start_time, end_time
) -> Optional[Dict[str, Any]]:
    """Find KeyAttributes for a service by name (paginated list_services)."""
    client = get_applicationsignals_client()
    next_token = None
    while True:
        params = {'StartTime': start_time, 'EndTime': end_time, 'MaxResults': 100}
        if next_token:
            params['NextToken'] = next_token
        response = client.list_services(**params)
        for service in response.get('ServiceSummaries', []):
            key_attrs = service.get('KeyAttributes', {})
            if key_attrs.get('Name') == service_name:
                return key_attrs
        next_token = response.get('NextToken')
        if not next_token:
            return None


def _sum_datapoints(metric_ref: Dict[str, Any], start_time, end_time, period: int):
    """Sum a metric over the window (for Requests/Fault/Error counts)."""
    response = get_cloudwatch_client().get_metric_statistics(
        Namespace=metric_ref['Namespace'],
        MetricName=metric_ref['MetricName'],
        Dimensions=metric_ref.get('Dimensions', []),
        StartTime=start_time,
        EndTime=end_time,
        Period=period,
        Statistics=['Sum', 'SampleCount'],
    )
    datapoints = response.get('Datapoints', [])
    return (
        sum(dp.get('Sum', 0) or 0 for dp in datapoints),
        sum(dp.get('SampleCount', 0) or 0 for dp in datapoints),
    )


def _latency_stats(
    metric_ref: Dict[str, Any], start_time, end_time, period: int, percentile: float
):
    """Return (avg_ms, p{N}_ms, sample_count) for a Latency metric."""
    pstat = f'p{int(percentile)}'
    response = get_cloudwatch_client().get_metric_statistics(
        Namespace=metric_ref['Namespace'],
        MetricName=metric_ref['MetricName'],
        Dimensions=metric_ref.get('Dimensions', []),
        StartTime=start_time,
        EndTime=end_time,
        Period=period,
        Statistics=['Average', 'SampleCount'],
        ExtendedStatistics=[pstat],
    )
    datapoints = response.get('Datapoints', [])
    if not datapoints:
        return None, None, 0
    total_count = sum(dp.get('SampleCount', 0) or 0 for dp in datapoints)
    # Sample-count-weighted average; max of percentile across datapoints.
    weighted = sum(
        (dp.get('Average', 0) or 0) * (dp.get('SampleCount', 0) or 0) for dp in datapoints
    )
    avg = round(weighted / total_count, 2) if total_count else None
    pvals = [dp.get('ExtendedStatistics', {}).get(pstat) for dp in datapoints]
    pvals = [v for v in pvals if v is not None]
    pval = round(max(pvals), 2) if pvals else None
    return avg, pval, total_count


def get_endpoint_red_metrics(
    service_name: str,
    hours: int = 24,
    operation: Optional[str] = None,
    limit: int = 20,
    percentile: float = 99,
) -> List[Dict[str, Any]]:
    """Return per-operation RED metric summaries for a service from Application Signals.

    Each summary mirrors the service_events ``get_endpoints`` shape:
    operation, total_requests, total_faults, total_errors, avg_duration_ms,
    p{N}_duration_ms. Returns ``[]`` when the service or its operations are not found.
    """
    end_time = datetime.now(timezone.utc)
    start_time = end_time - timedelta(hours=hours)
    period = _period_for_hours(hours)

    key_attrs = _find_service_key_attributes(service_name, start_time, end_time)
    if not key_attrs:
        logger.debug("AppSignals service '%s' not found for endpoint RED metrics", service_name)
        return []

    client = get_applicationsignals_client()
    operations: List[Dict[str, Any]] = []
    next_token = None
    while True:
        params = {
            'StartTime': start_time,
            'EndTime': end_time,
            'KeyAttributes': key_attrs,
            'MaxResults': 100,
        }
        if next_token:
            params['NextToken'] = next_token
        response = client.list_service_operations(**params)
        operations.extend(response.get('Operations', []))
        next_token = response.get('NextToken')
        if not next_token:
            break

    op_filter = operation.lower() if operation else None
    summaries: List[Dict[str, Any]] = []
    for op in operations:
        op_name = op.get('Name', '')
        if op_filter and op_filter not in op_name.lower():
            continue

        metric_refs = op.get('MetricReferences', [])
        by_type = {ref.get('MetricType'): ref for ref in metric_refs}

        total_requests = 0
        total_faults = 0
        total_errors = 0
        avg_ms = None
        pval_ms = None

        if _METRIC_LATENCY in by_type:
            avg_ms, pval_ms, total_requests = _latency_stats(
                by_type[_METRIC_LATENCY], start_time, end_time, period, percentile
            )
        if _METRIC_FAULT in by_type:
            fault_sum, _ = _sum_datapoints(by_type[_METRIC_FAULT], start_time, end_time, period)
            total_faults = int(fault_sum)
        if _METRIC_ERROR in by_type:
            error_sum, _ = _sum_datapoints(by_type[_METRIC_ERROR], start_time, end_time, period)
            total_errors = int(error_sum)

        summaries.append(
            {
                'operation': op_name,
                'service_name': service_name,
                'total_requests': int(total_requests),
                'total_faults': total_faults,
                'total_errors': total_errors,
                'avg_duration_ms': avg_ms,
                f'p{int(percentile)}_duration_ms': pval_ms,
            }
        )
        if len(summaries) >= limit:
            break

    return summaries
