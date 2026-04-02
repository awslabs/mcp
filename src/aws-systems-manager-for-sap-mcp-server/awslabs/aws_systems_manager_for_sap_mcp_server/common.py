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

"""Common utilities for SSM for SAP MCP Server."""

import json
from datetime import datetime
from typing import Any, Dict


def remove_null_values(d: Dict) -> Dict:
    """Return a new dictionary with key-value pairs of any null value removed."""
    return {k: v for k, v in d.items() if v is not None}


def format_datetime(dt: Any) -> str:
    """Format a datetime value for display."""
    if not dt:
        return 'N/A'
    try:
        if isinstance(dt, datetime):
            return dt.strftime('%Y-%m-%d %H:%M:%S UTC')
        return str(dt)
    except Exception:
        return str(dt)


def safe_json_serialize(obj: Any) -> str:
    """Serialize an object to JSON, handling datetime and other non-serializable types."""
    return json.dumps(obj, indent=2, default=str)
