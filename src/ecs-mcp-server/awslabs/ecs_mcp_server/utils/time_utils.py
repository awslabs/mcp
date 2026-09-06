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

"""
Utility functions for handling time calculations.
"""

import datetime
from typing import Optional, Tuple, Union


def _ensure_datetime(
    value: Optional[Union[str, datetime.datetime]],
) -> Optional[datetime.datetime]:
    """
    Normalize a value into an optional ``datetime`` object.

    MCP serializes all tool arguments as JSON, so ``start_time``/``end_time``
    always arrive as ISO-8601 strings rather than ``datetime`` objects. This
    helper parses those strings while passing ``datetime`` objects (and ``None``)
    through unchanged. See https://github.com/awslabs/mcp/issues/2858.

    Parameters
    ----------
    value : str | datetime | None
        An ISO-8601 string, a ``datetime`` object, or ``None``.

    Returns
    -------
    datetime | None
        The parsed/passthrough ``datetime``, or ``None`` if ``value`` is ``None``.

    Raises
    ------
    ValueError
        If ``value`` is a string that is not valid ISO-8601.
    """
    if value is None:
        return None
    if isinstance(value, datetime.datetime):
        return value
    if isinstance(value, str):
        # datetime.fromisoformat() does not accept a trailing "Z" until
        # Python 3.11, so normalize it to an explicit UTC offset first.
        normalized = value.replace("Z", "+00:00")
        try:
            return datetime.datetime.fromisoformat(normalized)
        except ValueError as exc:
            raise ValueError(
                f"Invalid ISO-8601 datetime string: {value!r}. "
                "Expected a format such as '2026-04-03T12:00:00Z' or "
                "'2026-04-03T12:00:00+00:00'."
            ) from exc
    raise ValueError(
        f"Expected an ISO-8601 string or datetime, got {type(value).__name__}: {value!r}."
    )


def calculate_time_window(
    time_window: int = 3600,
    start_time: Optional[Union[str, datetime.datetime]] = None,
    end_time: Optional[Union[str, datetime.datetime]] = None,
) -> Tuple[datetime.datetime, datetime.datetime]:
    """
    Calculate the actual start time and end time for a time window.

    Parameters
    ----------
    time_window : int, optional
        Time window in seconds (default: 3600)
    start_time : str | datetime, optional
        Explicit start time (takes precedence over time_window if provided).
        May be an ISO-8601 string (as delivered by MCP) or a datetime object.
    end_time : str | datetime, optional
        Explicit end time (defaults to current time if not provided).
        May be an ISO-8601 string (as delivered by MCP) or a datetime object.

    Returns
    -------
    Tuple[datetime.datetime, datetime.datetime]
        Tuple of (actual_start_time, actual_end_time) with timezone info

    Raises
    ------
    ValueError
        If start_time or end_time is a string that is not valid ISO-8601.
    """
    # MCP serializes tool arguments as JSON, so start_time/end_time arrive as
    # ISO-8601 strings. Normalize them to datetime objects up front so the
    # tz-awareness logic below works regardless of how they were supplied.
    start_time = _ensure_datetime(start_time)
    end_time = _ensure_datetime(end_time)

    now = datetime.datetime.now(datetime.timezone.utc)

    # Handle provided start_time and end_time
    if end_time is None:
        # If no end_time provided, use current time
        actual_end_time = now
    else:
        # Ensure end_time is timezone-aware
        actual_end_time = (
            end_time if end_time.tzinfo else end_time.replace(tzinfo=datetime.timezone.utc)
        )

    if start_time is not None:
        # If start_time provided, use it directly
        actual_start_time = (
            start_time if start_time.tzinfo else start_time.replace(tzinfo=datetime.timezone.utc)
        )
    elif end_time is not None:
        # If only end_time provided, calculate start_time using time_window
        actual_start_time = actual_end_time - datetime.timedelta(seconds=time_window)
    else:
        # Default case: use time_window from now
        actual_start_time = now - datetime.timedelta(seconds=time_window)

    return actual_start_time, actual_end_time
