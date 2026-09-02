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

"""SigV4-signed client for the CloudWatch Metrics PromQL API.

Vended metrics land in the customer's account as CloudWatch OTel metrics and
are queried through CloudWatch's Prometheus-compatible HTTP API
(``https://monitoring.<region>.amazonaws.com/api/v1/...``). boto3 has no
client for this API, so requests are signed manually with SigV4 (service name
``monitoring``) using the same credential resolution as every other tool in
this server (:func:`get_aws_session`), and sent over botocore's HTTP session
to avoid adding an HTTP-library dependency.
"""

import json
import time as time_module
from awslabs.aws_healthomics_mcp_server.metrics import schema
from awslabs.aws_healthomics_mcp_server.utils.aws_utils import get_aws_session
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest
from botocore.httpsession import URLLib3Session
from dataclasses import dataclass, field
from datetime import datetime, timezone
from loguru import logger
from typing import Any, Dict, List, Optional
from urllib.parse import urlencode


SERVICE_NAME = 'monitoring'
MAX_RETRIES = 3
RETRY_DELAY_SECONDS = 1

DEFAULT_STEP_SECONDS = 60

# CloudWatch PromQL API caps query_range at 11,000 datapoints per series;
# steps are widened as needed to keep long windows under the cap.
MAX_DATAPOINTS_PER_SERIES = 11_000


@dataclass
class TimeSeries:
    """One PromQL series: its labels and (timestamp, value) samples."""

    labels: Dict[str, str]
    timestamps: List[float] = field(default_factory=list)
    values: List[float] = field(default_factory=list)

    @property
    def datapoint_count(self) -> int:
        """Number of samples in the series."""
        return len(self.values)


@dataclass
class SeriesSummary:
    """Summary statistics for one series, instrument-type aware.

    For gauges, ``minimum``/``maximum``/``average``/``last`` describe the
    sampled values. For cumulative counters, ``total_delta`` is the increase
    over the window (last - first sample) and ``average_rate`` is that delta
    divided by the sampled duration in seconds; the raw-value stats are still
    included but are rarely meaningful for counters.
    """

    labels: Dict[str, str]
    datapoint_count: int
    minimum: Optional[float] = None
    maximum: Optional[float] = None
    average: Optional[float] = None
    last: Optional[float] = None
    total_delta: Optional[float] = None
    average_rate: Optional[float] = None


def summarize_series(series: TimeSeries, is_counter: bool) -> SeriesSummary:
    """Compute summary statistics for a series.

    Counter series are cumulative monotonic sums (raw totals since
    container/mount start), so the meaningful aggregates are the window delta
    and average rate, not the raw min/max.
    """
    if not series.values:
        return SeriesSummary(labels=series.labels, datapoint_count=0)

    summary = SeriesSummary(
        labels=series.labels,
        datapoint_count=len(series.values),
        minimum=min(series.values),
        maximum=max(series.values),
        average=sum(series.values) / len(series.values),
        last=series.values[-1],
    )

    if is_counter and len(series.values) >= 2:
        delta = series.values[-1] - series.values[0]
        duration = series.timestamps[-1] - series.timestamps[0]
        # A negative delta means the counter reset (container restart); fall
        # back to the last raw total as a lower bound rather than reporting a
        # negative increase.
        summary.total_delta = delta if delta >= 0 else series.values[-1]
        if duration > 0:
            summary.average_rate = summary.total_delta / duration

    return summary


def compute_step_seconds(start: datetime, end: datetime, requested_step: Optional[int]) -> int:
    """Choose a query step that keeps the series under the datapoint cap."""
    window = max(int((end - start).total_seconds()), 1)
    step = requested_step or DEFAULT_STEP_SECONDS
    min_step = (window // MAX_DATAPOINTS_PER_SERIES) + 1
    return max(step, min_step)


class VendedMetricsClient:
    """Client for querying HealthOmics vended metrics via CloudWatch PromQL."""

    def __init__(self, region: Optional[str] = None):
        """Create a client bound to a region and the server's credential chain.

        Args:
            region: AWS region override; defaults to the server's configured
                region (AWS_REGION or the server default).
        """
        session = get_aws_session(region_name=region)
        self._region = session.region_name
        self._credentials = session.get_credentials()
        if self._credentials is None:
            raise ValueError('AWS credentials not found')
        self._base_url = f'https://monitoring.{self._region}.amazonaws.com/api/v1'
        self._http = URLLib3Session()

    @property
    def region(self) -> str:
        """The region this client queries."""
        return self._region

    def _request(self, endpoint: str, params: Dict[str, Any]) -> Any:
        """Make a SigV4-signed POST request to a PromQL API endpoint.

        Parameters are form-encoded into the body (POST is part of the
        Prometheus HTTP API): PromQL selectors contain characters (``{``,
        ``"``, ``@``) whose query-string canonicalization is error-prone under
        SigV4, while a body is signed as an opaque hash.

        Returns the ``data`` portion of the Prometheus-compatible response.

        Raises:
            RuntimeError: If the API returns a non-success status.
        """
        url = f'{self._base_url}/{endpoint}'
        # Multi-valued params (series match[]) are passed as lists.
        body = urlencode(params, doseq=True)

        last_exception: Optional[Exception] = None
        for attempt in range(MAX_RETRIES):
            try:
                request = AWSRequest(
                    method='POST',
                    url=url,
                    data=body,
                    headers={'Content-Type': 'application/x-www-form-urlencoded'},
                )
                SigV4Auth(
                    self._credentials.get_frozen_credentials(), SERVICE_NAME, self._region
                ).add_auth(request)
                response = self._http.send(request.prepare())

                body = response.content
                if isinstance(body, bytes):
                    body = body.decode('utf-8')
                data = json.loads(body)

                if response.status_code >= 400:
                    raise RuntimeError(
                        f'PromQL API HTTP {response.status_code}: {data.get("error", body[:500])}'
                    )
                if data.get('status') != 'success':
                    raise RuntimeError(f'PromQL API error: {data.get("error", "unknown error")}')
                return data['data']
            except (RuntimeError, json.JSONDecodeError, ConnectionError, OSError) as e:
                last_exception = e
                if attempt < MAX_RETRIES - 1:
                    delay = RETRY_DELAY_SECONDS * (2**attempt)
                    logger.warning(f'PromQL request failed ({e}); retrying in {delay}s')
                    time_module.sleep(delay)

        raise RuntimeError(f'PromQL request failed after {MAX_RETRIES} attempts') from (
            last_exception
        )

    def query_range(
        self,
        query: str,
        start: datetime,
        end: datetime,
        step_seconds: Optional[int] = None,
    ) -> List[TimeSeries]:
        """Run a PromQL range query and return normalized time series.

        Args:
            query: PromQL query (typically from :func:`schema.build_selector`,
                optionally wrapped in functions/aggregations).
            start: Window start (timezone-aware).
            end: Window end (timezone-aware).
            step_seconds: Sample step; widened automatically if the window
                would exceed the API's per-series datapoint cap.
        """
        step = compute_step_seconds(start, end, step_seconds)
        data = self._request(
            'query_range',
            {
                'query': query,
                'start': start.timestamp(),
                'end': end.timestamp(),
                'step': f'{step}s',
            },
        )
        return self._parse_matrix(data)

    def instant_query(self, query: str, at: Optional[datetime] = None) -> List[TimeSeries]:
        """Run a PromQL instant query; each returned series has one sample."""
        params: Dict[str, Any] = {'query': query}
        if at is not None:
            params['time'] = at.timestamp()
        data = self._request('query', params)
        return self._parse_vector(data)

    def series(
        self,
        matches: List[str],
        start: datetime,
        end: datetime,
    ) -> List[Dict[str, str]]:
        """List label sets of series matching the given selectors in the window.

        Used to discover which vended metrics actually have data for a run
        (feature-off detection and per-mode presence checks).
        """
        data = self._request(
            'series',
            {
                'match[]': matches,
                'start': start.timestamp(),
                'end': end.timestamp(),
            },
        )
        return list(data or [])

    @staticmethod
    def _parse_matrix(data: Dict[str, Any]) -> List[TimeSeries]:
        """Parse a range-query (matrix) result into TimeSeries."""
        result: List[TimeSeries] = []
        for item in data.get('result', []):
            series = TimeSeries(labels=dict(item.get('metric', {})))
            for timestamp, value in item.get('values', []):
                series.timestamps.append(float(timestamp))
                series.values.append(float(value))
            result.append(series)
        return result

    @staticmethod
    def _parse_vector(data: Dict[str, Any]) -> List[TimeSeries]:
        """Parse an instant-query (vector) result into single-sample TimeSeries."""
        result: List[TimeSeries] = []
        for item in data.get('result', []):
            series = TimeSeries(labels=dict(item.get('metric', {})))
            value = item.get('value')
            if value:
                series.timestamps.append(float(value[0]))
                series.values.append(float(value[1]))
            result.append(series)
        return result


def utc_now() -> datetime:
    """Timezone-aware now, patchable in tests."""
    return datetime.now(timezone.utc)


def metric_display_name(otel_name: str) -> str:
    """Human-oriented alias for an OTel metric name (used in tool output)."""
    return otel_name.removeprefix('aws.omics.')


__all__ = [
    'TimeSeries',
    'SeriesSummary',
    'VendedMetricsClient',
    'summarize_series',
    'compute_step_seconds',
    'metric_display_name',
    'utc_now',
    'schema',
]
