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

"""Time utility functions for the AWS Billing and Cost Management MCP server."""

from .logging_utils import get_logger
from datetime import datetime, timezone
from typing import Any, Dict, Mapping, Optional, Sequence, Union


logger = get_logger(__name__)


# Supported UTC datetime formats, ordered from most specific to least specific.
_SUPPORTED_UTC_DATETIME_FORMATS = ['%Y-%m-%dT%H:%M:%S', '%Y-%m-%d']


def utc_datetime_string_to_epoch_seconds(datetime_str: str) -> int:
    """Convert a UTC datetime string to epoch seconds.

    Supports the following formats:
    - YYYY-MM-DD (date only, assumes 00:00:00 UTC)
    - YYYY-MM-DDTHH:MM:SS (ISO 8601 without timezone, assumed UTC)

    Args:
        datetime_str: UTC datetime string in YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS format.

    Returns:
        Unix timestamp in seconds (integer).

    Raises:
        ValueError: If the datetime string format is invalid.
    """
    for fmt in _SUPPORTED_UTC_DATETIME_FORMATS:
        try:
            dt = datetime.strptime(datetime_str, fmt)
            return int(dt.replace(tzinfo=timezone.utc).timestamp())
        except ValueError:
            continue

    raise ValueError(
        f"Invalid datetime format: '{datetime_str}'. "
        'Expected format: YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS (UTC)'
    )


def timestamp_to_utc_iso_string(timestamp: Union[int, float, datetime]) -> str:
    """Convert a timestamp to a UTC ISO 8601 formatted string.

    Handles both epoch seconds (int/float) and datetime objects, as different
    AWS services may return timestamps in different formats.

    Args:
        timestamp: Unix timestamp in seconds (int/float) or a datetime object.

    Returns:
        ISO 8601 formatted date string (e.g., "2023-11-14T22:13:20").
    """
    if isinstance(timestamp, datetime):
        if timestamp.tzinfo is not None:
            timestamp = timestamp.astimezone(timezone.utc)
        return timestamp.replace(tzinfo=None).isoformat()
    return datetime.fromtimestamp(timestamp, tz=timezone.utc).replace(tzinfo=None).isoformat()


# An epoch value above this is in milliseconds: read as seconds it would fall after
# the year 5000, while read as milliseconds it falls after March 1973.
EPOCH_MILLISECONDS_THRESHOLD = 1e11


def format_timestamp_to_utc_iso(timestamp: Any) -> Optional[str]:
    """Format an AWS timestamp of any wire form as a UTC ISO 8601 string.

    The same field arrives in different forms depending on the client: boto3
    deserializes timestamps into ``datetime`` objects, while JSON callers see epoch
    seconds or, for some services, epoch milliseconds. Accepts:

    - ``datetime`` (naive values are taken as UTC; aware values are converted)
    - epoch seconds (int/float)
    - epoch milliseconds (int/float above ``EPOCH_MILLISECONDS_THRESHOLD``)
    - strings holding any of the above numbers, or an ISO 8601 datetime

    Args:
        timestamp: The timestamp value, or None.

    Returns:
        ISO 8601 UTC string without offset (e.g. "2023-11-14T22:13:20"), or None when
        the value is missing or cannot be converted. Conversion failures are logged,
        never written into the returned value.
    """
    if timestamp is None:
        return None

    value = timestamp
    if isinstance(value, str):
        value = _parse_timestamp_string(value)

    try:
        if isinstance(value, datetime):
            return timestamp_to_utc_iso_string(value)
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            seconds = value / 1000 if abs(value) > EPOCH_MILLISECONDS_THRESHOLD else value
            return timestamp_to_utc_iso_string(seconds)
    except (OverflowError, OSError, ValueError):
        pass

    logger.warning(
        f'Could not convert timestamp of type {type(timestamp).__name__}; returning None'
    )
    return None


def _parse_timestamp_string(text: str) -> Any:
    """Parse a timestamp string into a number or datetime; return None if neither."""
    stripped = text.strip()
    try:
        return float(stripped)
    except ValueError:
        pass
    try:
        return datetime.fromisoformat(stripped.replace('Z', '+00:00'))
    except ValueError:
        return None


def normalize_datetimes_to_iso(obj: Any) -> Any:
    """Recursively convert ``datetime`` values in a structure to ISO 8601 UTC strings.

    boto3 returns Python ``datetime`` objects for AWS timestamp fields, which are
    not JSON-serializable. This walks an arbitrary response value (dict, list, or
    scalar) and converts every ``datetime`` to an ISO 8601 UTC string via
    :func:`timestamp_to_utc_iso_string`, leaving all other values untouched.
    Walking the structure (rather than normalizing named fields) stays correct as
    APIs add nested timestamp fields.

    Args:
        obj: An arbitrary value from an AWS response (dict, list, or scalar).

    Returns:
        The value with any ``datetime`` instances converted to ISO 8601 strings.
    """
    if isinstance(obj, dict):
        return {key: normalize_datetimes_to_iso(value) for key, value in obj.items()}
    if isinstance(obj, list):
        return [normalize_datetimes_to_iso(item) for item in obj]
    if isinstance(obj, datetime):
        return timestamp_to_utc_iso_string(obj)
    return obj


def monthly_period_note(
    requested_start: str,
    requested_end: str,
    periods: Sequence[Optional[Mapping[str, Any]]],
    granularity: Optional[str] = None,
) -> Dict[str, str]:
    """Say when MONTHLY entries are labelled with more of the month than their figures cover.

    With MONTHLY granularity, GetReservationUtilization and GetSavingsPlansUtilization label
    each entry with its whole calendar month, while the figures cover only the requested
    days: a request for 2026-01-24 to 2026-03-10 returns a first entry labelled 2026-01-01
    to 2026-02-01 holding only 2026-01-24 onward, and a last entry labelled 2026-03-01 to
    2026-04-01 holding only the days before 2026-03-10. The current month's entry is the
    exception: its label, and its data, end at the first day without data, which in the
    processing lag is before the requested end; the note then says so, and the covered
    range ends there.

    Args:
        requested_start: Requested start date (YYYY-MM-DD, inclusive)
        requested_end: Requested end date (YYYY-MM-DD, exclusive)
        periods: Each returned entry's TimePeriod (``{'Start': ..., 'End': ...}``), in order
        granularity: The Granularity sent. The data lag is flagged only for MONTHLY, since a
            DAILY entry also ends inside its month.

    Returns:
        ``{'period_note': ...}`` when the first label starts before the requested start,
        the last label ends after the requested end, or the last label stops inside its
        month before the requested end (the data lag); otherwise an empty dict.
    """
    if not periods:
        return {}
    first, last = periods[0] or {}, periods[-1] or {}
    first_start, first_end = first.get('Start'), first.get('End')
    last_start, last_end = last.get('Start'), last.get('End')
    start_snapped = bool(first_start and first_end and first_start < requested_start)
    end_snapped = bool(last_start and last_end and last_end > requested_end)
    # Only the current month's label ends inside its own month: at the first day without
    # data. A past month's label always ends on the 1st of the next month.
    lagged = bool(
        (granularity or '').upper() == 'MONTHLY'
        and last_start
        and last_end
        and last_end < requested_end
        and last_end < _first_of_next_month(last_start)
    )
    if not (start_snapped or end_snapped or lagged):
        return {}
    data_end = last_end if lagged and last_end else requested_end
    parts = []
    if len(periods) == 1 and (start_snapped or end_snapped):
        parts.append(
            f'The entry labelled {first_start} to {first_end} covers only {requested_start} '
            f'to {data_end}.'
        )
    else:
        if start_snapped:
            parts.append(
                f'The first entry, labelled {first_start} to {first_end}, covers only '
                f'{requested_start} onward.'
            )
        if end_snapped:
            parts.append(
                f'The last entry, labelled {last_start} to {last_end}, covers only the days '
                f'before {requested_end}.'
            )
    if lagged:
        parts.append(f'Data from {data_end} is not available yet and is not included.')
    intro = ''
    if start_snapped or end_snapped:
        current = " (the current month's ends at the first day without data)" if lagged else ''
        intro = (
            f'Cost Explorer labels each MONTHLY entry with its whole calendar month{current}, '
            'but the figures cover only the requested days. '
        )
    partial = 'those months' if start_snapped or end_snapped else 'the last month'
    return {
        'period_note': (
            f'{intro}{" ".join(parts)} Report {partial} as partial: the figures, and '
            f'total, cover {requested_start} to {data_end} (end exclusive) only.'
        )
    }


def _first_of_next_month(day: str) -> str:
    """Return the 1st of the month after ``day`` (YYYY-MM-DD) as YYYY-MM-DD."""
    year, month = int(day[:4]), int(day[5:7])
    return f'{year + month // 12:04d}-{month % 12 + 1:02d}-01'
