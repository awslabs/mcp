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

"""PromQL query builders using UTF-8 quoted-label syntax.

ServiceEvents metric and label names contain literal dots, which classic PromQL
``metric{label="v"}`` syntax cannot parse. These builders emit the quoted form —
the metric name as a quoted string inside the braces, every label key quoted::

    {"service.function.duration","@resource.service.name"="svc"}

Latency/percentile note: ``histogram_quantile`` is unreliable on CloudWatch
Metrics V2 native histograms (panics non-deterministically), so these builders
expose only ``histogram_avg`` (average) and ``histogram_count`` (call count).
See ``.claude/completed-plans/plan_006_metrics_v2_promql.md`` (Gap 1).
"""

import math
from typing import Dict, List, Optional, Tuple


METRIC_FUNCTION_DURATION = 'service.function.duration'
METRIC_COUNT = 'count'

# Resource-attribute label keys (CloudWatch prefixes resource attrs with @resource.).
LABEL_SERVICE_NAME = '@resource.service.name'
LABEL_ENVIRONMENT = '@resource.deployment.environment.name'
LABEL_DEPLOYMENT_ID = '@resource.aws.service_events.deployment.id'

# Data-point attribute label keys (bare — no prefix).
LABEL_FUNCTION_NAME = 'function.name'
LABEL_CALLER = 'aws.service_events.caller'
LABEL_FUNCTION_AT_LINE = 'aws.service_events.function_at_line'
LABEL_STATUS = 'status'
# Endpoint/operation the function executed under (e.g. "POST /checkout"). Added to
# the service.function.duration metric so function metrics can be filtered by endpoint.
LABEL_OPERATION = 'operation'
# Exception label on the ``count`` metric. Value is "<dotted.path> <ExceptionName>"
# (e.g. "...WebAsyncUtils.getAsyncManager NotFound"); the short name is the last token.
LABEL_EXCEPTION = 'exception'

DEFAULT_RATE_WINDOW = '5m'


def _escape(value: str) -> str:
    r"""Escape a PromQL string literal (backslash and double-quote)."""
    return value.replace('\\', '\\\\').replace('"', '\\"')


def build_selector(metric: str, matchers: Optional[Dict[str, str]] = None) -> str:
    """Build a quoted-label selector: ``{"metric","key"="val",...}``.

    The metric name is emitted as a bare quoted string (the ``__name__`` shorthand);
    each matcher key/value is quoted and escaped.
    """
    parts = [f'"{_escape(metric)}"']
    for key, value in (matchers or {}).items():
        parts.append(f'"{_escape(key)}"="{_escape(value)}"')
    return '{' + ','.join(parts) + '}'


def _function_matchers(
    service_name: Optional[str],
    environment: Optional[str] = None,
    deployment_id: Optional[str] = None,
    function_name: Optional[str] = None,
    status: Optional[str] = None,
    operation: Optional[str] = None,
) -> Dict[str, str]:
    matchers: Dict[str, str] = {}
    if service_name:
        matchers[LABEL_SERVICE_NAME] = service_name
    if environment:
        matchers[LABEL_ENVIRONMENT] = environment
    if deployment_id:
        matchers[LABEL_DEPLOYMENT_ID] = deployment_id
    if function_name:
        matchers[LABEL_FUNCTION_NAME] = function_name
    if status:
        matchers[LABEL_STATUS] = status
    if operation:
        matchers[LABEL_OPERATION] = operation
    return matchers


def function_duration_selector(
    service_name: Optional[str] = None,
    environment: Optional[str] = None,
    deployment_id: Optional[str] = None,
    function_name: Optional[str] = None,
    status: Optional[str] = None,
    operation: Optional[str] = None,
) -> str:
    """Raw selector for ``service.function.duration`` with optional filters."""
    return build_selector(
        METRIC_FUNCTION_DURATION,
        _function_matchers(
            service_name, environment, deployment_id, function_name, status, operation
        ),
    )


# Group by function name AND line so the tools can report `line` alongside each
# function (the line is a stable per-function data-point label).
_GROUP_BY = f'"{LABEL_FUNCTION_NAME}","{LABEL_FUNCTION_AT_LINE}"'


def avg_by_function(
    service_name: Optional[str] = None,
    window: str = DEFAULT_RATE_WINDOW,
    top: Optional[int] = None,
    *,
    environment: Optional[str] = None,
    deployment_id: Optional[str] = None,
    function_name: Optional[str] = None,
    status: Optional[str] = None,
    operation: Optional[str] = None,
) -> str:
    """Average duration (µs) grouped by function+line.

    ``histogram_avg(sum by (fn,line) (increase(<sel>[w])))``. ``increase`` over the
    window keeps the average representative of the whole window. When ``top`` is
    given, wraps in ``topk(top, ...)`` for slowest-by-average ranking.
    """
    sel = function_duration_selector(
        service_name,
        environment=environment,
        deployment_id=deployment_id,
        function_name=function_name,
        status=status,
        operation=operation,
    )
    expr = f'histogram_avg(sum by ({_GROUP_BY}) (increase({sel}[{window}])))'
    if top is not None:
        expr = f'topk({top}, {expr})'
    return expr


def count_by_function(
    service_name: Optional[str] = None,
    window: str = DEFAULT_RATE_WINDOW,
    top: Optional[int] = None,
    group_by_line: bool = True,
    *,
    environment: Optional[str] = None,
    deployment_id: Optional[str] = None,
    function_name: Optional[str] = None,
    status: Optional[str] = None,
    operation: Optional[str] = None,
) -> str:
    """Absolute call count grouped by function (+line).

    ``sum by (fn[,line]) (histogram_count(increase(<sel>[w])))``. ``increase`` (not
    ``rate``) yields an absolute count over the window rather than a per-second
    rate, matching the REST API's ``calls`` field. When ``top`` is given, wraps in
    ``topk(top, ...)`` for most-called ranking.
    """
    sel = function_duration_selector(
        service_name,
        environment=environment,
        deployment_id=deployment_id,
        function_name=function_name,
        status=status,
        operation=operation,
    )
    group = _GROUP_BY if group_by_line else f'"{LABEL_FUNCTION_NAME}"'
    expr = f'sum by ({group}) (histogram_count(increase({sel}[{window}])))'
    if top is not None:
        expr = f'topk({top}, {expr})'
    return expr


def errors_by_function(
    service_name: Optional[str] = None,
    window: str = DEFAULT_RATE_WINDOW,
    top: Optional[int] = None,
    *,
    environment: Optional[str] = None,
    deployment_id: Optional[str] = None,
    function_name: Optional[str] = None,
    status: Optional[str] = 'error',
    operation: Optional[str] = None,
) -> str:
    """Absolute error count grouped by function (``status="error"`` on the duration metric)."""
    return count_by_function(
        service_name,
        window=window,
        top=top,
        environment=environment,
        deployment_id=deployment_id,
        function_name=function_name,
        status=status,
        operation=operation,
    )


def hours_to_window(hours: int) -> str:
    """Map a tool ``hours`` arg to a PromQL rate window string (e.g. 1 -> ``1h``)."""
    if hours <= 0:
        return DEFAULT_RATE_WINDOW
    return f'{hours}h'


def _value_of(entry: dict) -> Optional[float]:
    value = entry.get('value')
    if not value or len(value) < 2:
        return None
    try:
        val = float(value[1])
    except (ValueError, TypeError):
        return None
    # Prometheus can return "NaN"/"Inf" (e.g. histogram_avg over an empty
    # window). float() accepts those without raising, but they later blow up
    # int(round(...)) in function_metrics, so treat them as unparseable.
    if not math.isfinite(val):
        return None
    return val


def vector_to_function_value(result: Optional[List[dict]]) -> List[Tuple[str, float]]:
    """Extract ``(function.name, value)`` pairs from an instant-vector result."""
    pairs: List[Tuple[str, float]] = []
    for entry in result or []:
        fn = entry.get('metric', {}).get(LABEL_FUNCTION_NAME)
        val = _value_of(entry)
        if fn is None or val is None:
            continue
        pairs.append((fn, val))
    return pairs


def vector_to_function_records(result: List[dict], value_key: str) -> Dict[str, Dict]:
    """Index an instant-vector result by function name.

    Returns ``{function_name: {"line": int, value_key: float}}``. Used to merge the
    avg, count, and error vectors into one per-function record.
    """
    records: Dict[str, Dict] = {}
    for entry in result or []:
        metric = entry.get('metric', {})
        fn = metric.get(LABEL_FUNCTION_NAME)
        val = _value_of(entry)
        if fn is None or val is None:
            continue
        rec = records.setdefault(fn, {})
        rec[value_key] = val
        line = metric.get(LABEL_FUNCTION_AT_LINE)
        if line is not None and 'line' not in rec:
            try:
                rec['line'] = int(line)
            except (ValueError, TypeError):
                rec['line'] = line
    return records


def errors_by_operation_exception(
    service_name: str,
    window: str = DEFAULT_RATE_WINDOW,
    *,
    operation: Optional[str] = None,
    environment: Optional[str] = None,
    top: Optional[int] = None,
) -> str:
    """Build the per-(operation, exception) error-count query on the ``count`` metric.

    ``sum by (operation, exception) (sum_over_time({"count","@resource.service.name"="svc"
    [,"operation"="op"][,env]}[window]))``. The ``count`` metric stores per-interval error
    counts (NOT a cumulative counter), so the total over the window is ``sum_over_time``
    — adding every interval's value. (``increase``/``rate`` are wrong here: they assume a
    monotonic counter and compute deltas between samples, which badly undercounts and does
    not match the CloudWatch "Errors" page.) Only series carrying an ``exception`` label
    are errors, so no extra status filter is needed. When ``top`` is given, wraps in
    ``topk(top, ...)``.
    """
    matchers: Dict[str, str] = {LABEL_SERVICE_NAME: service_name}
    if environment:
        matchers[LABEL_ENVIRONMENT] = environment
    if operation:
        matchers[LABEL_OPERATION] = operation
    sel = build_selector(METRIC_COUNT, matchers)
    expr = f'sum by ({LABEL_OPERATION}, {LABEL_EXCEPTION}) (sum_over_time({sel}[{window}]))'
    if top is not None:
        expr = f'topk({top}, {expr})'
    return expr


def _exception_short_name(exception: str) -> str:
    """Return the short exception name (last whitespace token) from the label value.

    The ``exception`` label is "<dotted.path> <ExceptionName>"; the CloudWatch Errors
    page shows just the trailing name. Falls back to the full string when there is no
    whitespace.
    """
    return exception.rsplit(' ', 1)[-1] if exception else exception


def vector_to_error_patterns(
    result: Optional[List[dict]], top: Optional[int] = None
) -> List[Dict]:
    """Map an instant-vector ``count`` result to per-(operation, exception) error rows.

    Returns ``[{operation, exception, exception_type, count}]`` sorted by count
    descending. Series without an ``exception`` label or a finite value are dropped.
    """
    rows: List[Dict] = []
    for entry in result or []:
        metric = entry.get('metric', {})
        exception = metric.get(LABEL_EXCEPTION)
        val = _value_of(entry)
        if not exception or val is None:
            continue
        rows.append(
            {
                'operation': metric.get(LABEL_OPERATION),
                'exception': exception,
                'exception_type': _exception_short_name(exception),
                'count': int(round(val)),
            }
        )
    rows.sort(key=lambda r: r['count'], reverse=True)
    if top is not None:
        rows = rows[:top]
    return rows
