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

"""Shared helpers for the Amazon Connect MCP Server."""

import datetime
from typing import Any, Callable, Dict, Iterator


def remove_null_values(d: Dict) -> Dict:
    """Return a new dictionary with any key whose value is null/empty removed."""
    return {k: v for k, v in d.items() if v is not None}


def paginate_with_next_token(
    operation: Callable[..., Dict[str, Any]],
    request: Dict[str, Any],
    max_pages: int = 100,
) -> Iterator[Dict[str, Any]]:
    """Manually paginate an AWS operation that uses a NextToken field.

    Several Amazon Connect metric operations (for example, GetMetricDataV2,
    GetCurrentMetricData, and GetCurrentUserData) support NextToken-based
    pagination but are not registered with boto3 paginators, so
    ``client.get_paginator(...)`` raises ``OperationNotPageableError``. This
    helper drives the NextToken loop directly.

    Args:
        operation: The bound boto3 client method to call (e.g. client.get_metric_data_v2).
        request: The request kwargs to pass on each call. Must not include NextToken.
        max_pages: Safety cap on the number of pages to fetch.

    Yields:
        Each response page returned by the operation.
    """
    next_token = None
    pages = 0
    while True:
        params = dict(request)
        if next_token:
            params['NextToken'] = next_token

        response = operation(**params)
        yield response
        pages += 1

        next_token = response.get('NextToken')
        if not next_token or pages >= max_pages:
            break


def parse_iso_datetime(value: str) -> datetime.datetime:
    """Parse an ISO 8601 timestamp string into a timezone-aware datetime.

    Accepts a trailing 'Z' (UTC) suffix. If the parsed value is naive, it is
    assumed to be UTC.

    Args:
        value: ISO 8601 timestamp string (e.g., '2025-06-08T00:00:00Z').

    Returns:
        A timezone-aware datetime object.
    """
    parsed = datetime.datetime.fromisoformat(value.replace('Z', '+00:00'))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=datetime.timezone.utc)
    return parsed


def to_utc_iso(dt: datetime.datetime) -> str:
    """Convert a datetime to an ISO 8601 UTC string ending in '+00:00'."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=datetime.timezone.utc)
    return dt.astimezone(datetime.timezone.utc).isoformat()


def split_into_intervals(
    start: datetime.datetime,
    end: datetime.datetime,
    interval_hours: int = 24,
    max_chunks: int = 90,
) -> Iterator[tuple]:
    """Split a time range into consecutive intervals of at most ``interval_hours``.

    Several Amazon Connect historical APIs (notably GetMetricDataV2) cap a single
    request's StartTime->EndTime window at 24 hours. This helper yields successive
    (chunk_start, chunk_end) pairs that cover ``[start, end)`` so the caller can
    issue one request per interval.

    Args:
        start: Timezone-aware start of the overall range.
        end: Timezone-aware end of the overall range.
        interval_hours: Maximum size of each interval in hours.
        max_chunks: Safety cap on the number of intervals yielded.

    Yields:
        (chunk_start, chunk_end) datetime pairs in chronological order.
    """
    step = datetime.timedelta(hours=interval_hours)
    chunk_start = start
    chunks = 0
    while chunk_start < end and chunks < max_chunks:
        chunk_end = min(chunk_start + step, end)
        yield chunk_start, chunk_end
        chunk_start = chunk_end
        chunks += 1
