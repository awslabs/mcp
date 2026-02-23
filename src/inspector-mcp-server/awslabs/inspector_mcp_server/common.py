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

"""Common utilities for Inspector MCP Server."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


def remove_null_values(data: Dict[str, Any]) -> Dict[str, Any]:
    """Remove keys with None values from a dictionary.

    Args:
        data: Dictionary to clean

    Returns:
        Dictionary with None values removed
    """
    return {k: v for k, v in data.items() if v is not None}


def build_string_filter(values: List[str], comparison: str = 'EQUALS') -> List[Dict[str, str]]:
    """Build Inspector StringFilter criteria format.

    Args:
        values: List of string values to filter on
        comparison: Comparison operator (EQUALS, PREFIX, NOT_EQUALS)

    Returns:
        List of StringFilter dictionaries
    """
    return [{'comparison': comparison, 'value': v} for v in values]


def build_date_filter(
    start: Optional[str] = None, end: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Build Inspector DateFilter criteria format.

    Args:
        start: Start time in ISO format
        end: End time in ISO format

    Returns:
        List of DateFilter dictionaries
    """
    date_filter: Dict[str, Any] = {}
    if start:
        date_filter['startInclusive'] = datetime.fromisoformat(start.replace('Z', '+00:00'))
    if end:
        date_filter['endInclusive'] = datetime.fromisoformat(end.replace('Z', '+00:00'))
    if date_filter:
        return [date_filter]
    return []


def validate_max_results(
    max_results: Optional[int], default: int = 10, max_allowed: int = 100
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


def ensure_utc(dt: datetime) -> datetime:
    """Ensure a datetime object has UTC timezone info.

    Args:
        dt: Datetime object

    Returns:
        Datetime object with UTC timezone
    """
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt
