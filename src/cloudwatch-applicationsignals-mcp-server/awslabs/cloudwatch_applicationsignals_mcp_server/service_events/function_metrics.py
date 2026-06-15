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

"""Function-level telemetry from CloudWatch Metrics V2 (PromQL).

Backs the Functions MCP tools (``list_monitored_functions``, ``get_function_metrics``,
``search_functions_by_name``) by querying the ``service.function.duration`` native
histogram via PromQL and merging the avg / count / error vectors into per-function
records.

Stats exposed: average duration (``histogram_avg``) and call/error counts
(``histogram_count`` over ``increase``). Percentiles, file paths, min/max, and
endpoint correlation are NOT available from these metrics — see
``.claude/completed-plans/plan_006_metrics_v2_promql.md`` (Gaps G1–G8).
"""

import logging
from . import promql_client, promql_query
from typing import Dict, List, Optional


logger = logging.getLogger(__name__)

# Microseconds (metric unit) -> milliseconds (tool output unit).
_US_PER_MS = 1000.0


def _us_to_ms(value: Optional[float]) -> Optional[float]:
    return round(value / _US_PER_MS, 2) if value is not None else None


def fetch_function_records(
    service_name: Optional[str] = None,
    environment: Optional[str] = None,
    hours: int = 24,
    function_name: Optional[str] = None,
    operation: Optional[str] = None,
) -> List[Dict]:
    """Return merged per-function records: name, line, calls, avg_duration_ms, errors.

    Issues three instant queries (avg, count, error-count) over the ``hours`` window
    and merges them by function name. ``function_name`` (exact label match) narrows
    to one function; ``operation`` (exact ``operation`` label match, e.g.
    "POST /checkout") narrows to functions that executed under one endpoint. Raises
    ``PromQLQueryError`` on query failure.
    """
    window = promql_query.hours_to_window(hours)

    avg_q = promql_query.avg_by_function(
        service_name, window=window, function_name=function_name, operation=operation
    )
    count_q = promql_query.count_by_function(
        service_name, window=window, function_name=function_name, operation=operation
    )
    errors_q = promql_query.errors_by_function(
        service_name, window=window, function_name=function_name, operation=operation
    )

    avg_res = promql_client.instant_query(avg_q).get('result', [])
    count_res = promql_client.instant_query(count_q).get('result', [])
    errors_res = promql_client.instant_query(errors_q).get('result', [])

    avg = promql_query.vector_to_function_records(avg_res, 'avg_us')
    counts = promql_query.vector_to_function_records(count_res, 'calls')
    errors = promql_query.vector_to_function_records(errors_res, 'errors')

    records: List[Dict] = []
    for name in set(avg) | set(counts):
        a = avg.get(name, {})
        c = counts.get(name, {})
        e = errors.get(name, {})
        line = a.get('line') or c.get('line') or 0
        records.append(
            {
                'name': name,
                'line': line,
                'calls': int(round(c.get('calls', 0))),
                'avg_duration_ms': _us_to_ms(a.get('avg_us')),
                'errors': int(round(e.get('errors', 0))),
            }
        )
    return records


def sort_and_limit(records: List[Dict], sort_by: str, top: int) -> List[Dict]:
    """Sort merged records and truncate to ``top``.

    ``sort_by``: "calls" (default), "duration" (by average — NO percentiles
    available), or "errors". Descending.
    """
    key_map = {
        'calls': lambda r: r.get('calls', 0),
        'duration': lambda r: r.get('avg_duration_ms') or 0,
        'errors': lambda r: r.get('errors', 0),
    }
    key = key_map.get(sort_by, key_map['calls'])
    return sorted(records, key=key, reverse=True)[:top]


def search_function_names(
    query: str,
    service_name: Optional[str] = None,
    hours: int = 24,
    limit: int = 20,
    operation: Optional[str] = None,
) -> List[str]:
    """Return function names matching ``query`` (case-insensitive substring).

    Uses the PromQL ``label/function.name/values`` endpoint scoped to the
    ``service.function.duration`` selector, then filters in Python. ``operation``
    (exact ``operation`` label match) scopes the search to one endpoint.
    """
    selector = promql_query.function_duration_selector(service_name, operation=operation)
    values = promql_client.label_values_query(promql_query.LABEL_FUNCTION_NAME, match=[selector])
    q = query.lower()
    matches = [v for v in values if q in v.lower()]
    return matches[:limit]
