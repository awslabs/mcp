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
from typing import Any, Optional, Union


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
