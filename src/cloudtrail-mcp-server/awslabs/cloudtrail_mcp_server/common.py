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

"""Common utilities for CloudTrail MCP Server."""

import re
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional


def remove_null_values(data: Dict[str, Any]) -> Dict[str, Any]:
    """Remove keys with None values from a dictionary.

    Args:
        data: Dictionary to clean

    Returns:
        Dictionary with None values removed
    """
    return {k: v for k, v in data.items() if v is not None}


def parse_relative_time(time_str: str) -> datetime:
    """Parse relative time strings like '1 hour ago', '2 days ago', etc.

    Args:
        time_str: Relative time string

    Returns:
        Parsed datetime object

    Raises:
        ValueError: If time string format is invalid
    """
    now = datetime.now(timezone.utc)

    # Handle 'now' case
    if time_str.lower() == 'now':
        return now

    # Parse relative time patterns
    pattern = r'(\d+)\s+(second|minute|hour|day|week|month|year)s?\s+ago'
    match = re.match(pattern, time_str.lower())

    if not match:
        raise ValueError(f'Invalid relative time format: {time_str}')

    amount = int(match.group(1))
    unit = match.group(2)

    if unit == 'second':
        delta = timedelta(seconds=amount)
    elif unit == 'minute':
        delta = timedelta(minutes=amount)
    elif unit == 'hour':
        delta = timedelta(hours=amount)
    elif unit == 'day':
        delta = timedelta(days=amount)
    elif unit == 'week':
        delta = timedelta(weeks=amount)
    elif unit == 'month':
        delta = timedelta(days=amount * 30)  # Approximate
    elif unit == 'year':
        delta = timedelta(days=amount * 365)  # Approximate
    else:
        raise ValueError(f'Unknown time unit: {unit}')

    return now - delta


def parse_time_input(time_input: str) -> datetime:
    """Parse time input which can be ISO format or relative time.

    Args:
        time_input: Time string in ISO format or relative format

    Returns:
        Parsed datetime object

    Raises:
        ValueError: If time format is invalid
    """
    # Try parsing as ISO format first
    iso_parsing_errors = []

    # Handle various ISO formats
    for fmt in [
        '%Y-%m-%dT%H:%M:%S%z',
        '%Y-%m-%dT%H:%M:%S.%f%z',
        '%Y-%m-%dT%H:%M:%SZ',
        '%Y-%m-%dT%H:%M:%S.%fZ',
        '%Y-%m-%dT%H:%M:%S',
        '%Y-%m-%d %H:%M:%S',
        '%Y-%m-%d',
    ]:
        try:
            parsed = datetime.strptime(time_input, fmt)
            # If no timezone info, assume UTC
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return parsed
        except ValueError as e:
            iso_parsing_errors.append(f"Format '{fmt}': {str(e)}")
            continue

    # Try parsing with dateutil if available, otherwise try isoformat
    try:
        parsed = datetime.fromisoformat(time_input.replace('Z', '+00:00'))
        return parsed
    except ValueError as e:
        iso_parsing_errors.append(f'ISO format parsing: {str(e)}')

    # If ISO parsing fails, try relative time parsing
    try:
        return parse_relative_time(time_input)
    except ValueError as e:
        # If both ISO and relative parsing fail, raise a comprehensive error
        error_msg = f"Unable to parse time input '{time_input}'. "
        error_msg += f'Relative time parsing error: {str(e)}. '
        error_msg += f'ISO format errors: {"; ".join(iso_parsing_errors[-2:])}'  # Show last 2 errors to avoid clutter
        raise ValueError(error_msg)


def validate_max_results(
    max_results: Optional[int], default: int = 10, max_allowed: int = 50
) -> int:
    """Validate and return appropriate max_results value.

    Args:
        max_results: Requested max results
        default: Default value if None
        max_allowed: Maximum allowed value

    Returns:
        Validated max_results value
    """
    if max_results is None:
        return default

    if max_results < 1:
        return 1

    if max_results > max_allowed:
        return max_allowed

    return max_results
