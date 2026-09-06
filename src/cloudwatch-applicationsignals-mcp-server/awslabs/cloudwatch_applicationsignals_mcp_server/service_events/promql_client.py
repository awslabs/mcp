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

"""PromQL client for the CloudWatch Metrics V2 Prometheus-compatible API.

CloudWatch Metrics V2 metrics (including the ServiceEvents ``service.function.duration``
and ``count`` metrics) are queryable only via PromQL, served from a
Prometheus-compatible HTTP API at::

    https://monitoring.{region}.amazonaws.com/api/v1/{query,query_range,series,labels,label/<name>/values}

Requests are SigV4-signed against the ``monitoring`` service (NOT ``aps`` — that is
AMP). Credentials and region come from the shared boto3 session in
the package ``aws_clients`` module.

IMPORTANT — query syntax: metric and label names emitted by ServiceEvents contain
literal dots (``service.function.duration``, ``@resource.service.name``,
``function.name``). Classic PromQL ``metric{label="v"}`` syntax fails to parse
these. Callers MUST use UTF-8 quoted-label syntax — the metric name is a quoted
string inside the braces and every dotted label key is quoted::

    {"service.function.duration","@resource.service.name"="svc","function.name"="m"}

See ``promql_query.py`` for builders that emit this form.

IMPORTANT — signing: query params MUST be attached to the ``AWSRequest`` before
signing (and the prepared URL sent verbatim). Signing the bare URL and appending
params afterward produces a canonical-query mismatch → HTTP 403
"signature does not match".
"""

import json
import logging
import time
from typing import Any, Dict, List, Optional


logger = logging.getLogger(__name__)

# SigV4 signing service for the CloudWatch Metrics V2 Prometheus API.
SIGNING_SERVICE = 'monitoring'

# Prometheus HTTP API endpoint names (relative to /api/v1/).
ENDPOINT_QUERY = 'query'
ENDPOINT_QUERY_RANGE = 'query_range'
ENDPOINT_SERIES = 'series'
ENDPOINT_LABELS = 'labels'

HTTP_TIMEOUT_SECONDS = 30
MAX_RETRIES = 3
RETRY_BASE_DELAY_SECONDS = 1.0


class PromQLQueryError(Exception):
    """Raised when a PromQL query fails (HTTP error or Prometheus-level error)."""


def _base_url(region: str) -> str:
    return f'https://{SIGNING_SERVICE}.{region}.amazonaws.com/api/v1'


def _region() -> str:
    from ..aws_clients import AWS_REGION

    return AWS_REGION


_http_session = None


def _get_http_session():
    """Return a lazily-built botocore HTTP session (no new third-party dep)."""
    global _http_session
    if _http_session is None:
        from botocore.httpsession import URLLib3Session

        _http_session = URLLib3Session(timeout=HTTP_TIMEOUT_SECONDS)
    return _http_session


def _reset_session() -> None:
    """Drop the cached HTTP session (test hook)."""
    global _http_session
    _http_session = None


def _get_credentials():
    """Resolve SigV4 credentials from the shared boto3 session."""
    import boto3
    import os

    profile = os.environ.get('AWS_PROFILE')
    session = boto3.Session(profile_name=profile, region_name=_region())
    creds = session.get_credentials()
    if creds is None:
        raise PromQLQueryError('AWS credentials not found')
    return creds.get_frozen_credentials()


def make_request(
    endpoint: str,
    params: Optional[Dict[str, Any]] = None,
    region: Optional[str] = None,
) -> Any:
    """Issue a signed GET to a Prometheus HTTP API endpoint and return its ``data``.

    Args:
        endpoint: One of the Prometheus API paths, e.g. ``query``, ``query_range``,
            ``series``, ``labels``, or ``label/<name>/values``.
        params: Query parameters (e.g. ``{"query": "...", "time": ...}``). Multi-value
            params (e.g. ``match[]``) may pass a list.
        region: AWS region override; defaults to the shared resolved region.

    Returns:
        The Prometheus ``data`` field (shape depends on endpoint/result type).

    Raises:
        PromQLQueryError: on signing failure, HTTP error, or a Prometheus
            ``status != "success"`` response.
    """
    from botocore.auth import SigV4Auth
    from botocore.awsrequest import AWSRequest

    r = region or _region()
    url = f'{_base_url(r)}/{endpoint}'
    creds = _get_credentials()

    last_error: Optional[str] = None
    for attempt in range(1, MAX_RETRIES + 1):
        # Params must be on the request BEFORE signing so the canonical query matches.
        aws_request = AWSRequest(method='GET', url=url, params=params or {})
        SigV4Auth(creds, SIGNING_SERVICE, r).add_auth(aws_request)
        prepared = aws_request.prepare()

        try:
            response = _get_http_session().send(prepared)
        except Exception as e:  # pylint: disable=broad-exception-caught
            last_error = f'HTTP request failed: {e}'
            logger.debug('PromQL request error (attempt %d/%d): %s', attempt, MAX_RETRIES, e)
            _sleep_backoff(attempt)
            continue

        status_code = response.status_code
        body = response.text or ''

        # Retry transient server errors; surface client errors immediately.
        if status_code >= 500:
            last_error = f'HTTP {status_code}'
            logger.debug(
                'PromQL server error (attempt %d/%d): HTTP %d', attempt, MAX_RETRIES, status_code
            )
            _sleep_backoff(attempt)
            continue

        try:
            payload = json.loads(body)
        except (ValueError, TypeError) as e:
            raise PromQLQueryError(
                f'Invalid JSON from PromQL API (HTTP {status_code}): {e}'
            ) from e

        if payload.get('status') != 'success':
            # Prometheus error envelope: {"status":"error","errorType":...,"error":...}
            err = payload.get('error', 'unknown error')
            err_type = payload.get('errorType', '')
            raise PromQLQueryError(f'PromQL API error (HTTP {status_code}, {err_type}): {err}')

        return payload.get('data')

    raise PromQLQueryError(f'PromQL request failed after {MAX_RETRIES} attempts: {last_error}')


def _sleep_backoff(attempt: int) -> None:
    """Exponential backoff between retries (no sleep after the final attempt)."""
    if attempt < MAX_RETRIES:
        time.sleep(RETRY_BASE_DELAY_SECONDS * (2 ** (attempt - 1)))


# ---------------------------------------------------------------------------
# Typed endpoint helpers
# ---------------------------------------------------------------------------


def instant_query(
    query: str, time_param: Optional[str] = None, region: Optional[str] = None
) -> Dict[str, Any]:
    """Run an instant query. Returns the ``data`` dict (``resultType`` + ``result``)."""
    params: Dict[str, Any] = {'query': query}
    if time_param:
        params['time'] = time_param
    return make_request(ENDPOINT_QUERY, params, region)


def range_query(
    query: str,
    start: str,
    end: str,
    step: str,
    region: Optional[str] = None,
) -> Dict[str, Any]:
    """Run a range query over ``[start, end]`` at ``step`` resolution."""
    params = {'query': query, 'start': start, 'end': end, 'step': step}
    return make_request(ENDPOINT_QUERY_RANGE, params, region)


def _match_param(match: Optional[List[str]]) -> Optional[str]:
    """Encode a ``match[]`` value for SigV4-safe signing.

    botocore mis-signs a list value for a ``[]``-suffixed param key (produces a
    canonical-query mismatch → HTTP 403), so the value must be a single string.
    The Prometheus endpoints we use accept one selector; if multiple are passed,
    only the first is sent and a warning is logged.
    """
    if not match:
        return None
    if len(match) > 1:
        logger.warning(
            'PromQL match[] supports a single selector via this client; using the first of %d.',
            len(match),
        )
    return match[0]


def series_query(
    match: List[str],
    start: Optional[str] = None,
    end: Optional[str] = None,
    region: Optional[str] = None,
) -> List[Dict[str, str]]:
    """Find series matching a selector. Returns a list of label-set dicts.

    Note: the Prometheus ``/series`` endpoint requires ``start`` and ``end``.
    """
    params: Dict[str, Any] = {'match[]': _match_param(match)}
    if start:
        params['start'] = start
    if end:
        params['end'] = end
    data = make_request(ENDPOINT_SERIES, params, region)
    return data if isinstance(data, list) else []


def labels_query(
    match: Optional[List[str]] = None,
    start: Optional[str] = None,
    end: Optional[str] = None,
    region: Optional[str] = None,
) -> List[str]:
    """List label names, optionally restricted to series matching ``match``."""
    params: Dict[str, Any] = {}
    match_value = _match_param(match)
    if match_value:
        params['match[]'] = match_value
    if start:
        params['start'] = start
    if end:
        params['end'] = end
    data = make_request(ENDPOINT_LABELS, params, region)
    return sorted(data) if isinstance(data, list) else []


def label_values_query(
    label_name: str,
    match: Optional[List[str]] = None,
    start: Optional[str] = None,
    end: Optional[str] = None,
    region: Optional[str] = None,
) -> List[str]:
    """List values for ``label_name``, optionally restricted to series matching ``match``."""
    params: Dict[str, Any] = {}
    match_value = _match_param(match)
    if match_value:
        params['match[]'] = match_value
    if start:
        params['start'] = start
    if end:
        params['end'] = end
    data = make_request(f'label/{label_name}/values', params, region)
    return sorted(data) if isinstance(data, list) else []
