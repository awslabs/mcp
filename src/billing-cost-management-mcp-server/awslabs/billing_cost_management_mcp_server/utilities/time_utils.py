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

from datetime import datetime, timezone
from typing import Union


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
