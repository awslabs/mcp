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

"""Datetime utility functions for the AWS HealthOmics MCP server."""

from datetime import datetime
from typing import Any, Optional


def datetime_to_iso(dt: Optional[datetime]) -> Optional[str]:
    """Convert datetime to ISO format string.

    Args:
        dt: Datetime object or None

    Returns:
        ISO format string or None if input is None
    """
    if dt is None:
        return None
    return dt.isoformat()


def convert_datetime_to_string(obj: Any) -> Any:
    """Recursively convert datetime objects to ISO strings in nested data structures.

    Args:
        obj: Any object that may contain datetime objects

    Returns:
        The object with all datetime objects converted to ISO format strings
    """
    if isinstance(obj, datetime):
        return obj.isoformat()
    elif isinstance(obj, dict):
        return {key: convert_datetime_to_string(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [convert_datetime_to_string(item) for item in obj]
    else:
        return obj
