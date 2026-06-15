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
"""Shared rendering primitives used by every ``*_rendering.py`` module.

These convert raw AWS API values into the human-readable shapes that MCP
tool responses depend on.
"""

from datetime import datetime, timezone
from typing import Any


def format_timestamp(value: Any, default: str = 'N/A') -> str:
    """Render a boto3 ``datetime`` value in the AWS-CLI ISO format.

    boto3 returns timestamp fields as native ``datetime`` objects;
    AWS-CLI-era responses are ISO 8601 strings (``YYYY-MM-DDTHH:MM:SSZ``).
    MCP clients depend on the latter shape, so anywhere a renderer surfaces
    an AWS-returned timestamp, it must go through this helper.

    String inputs are passed through unchanged so renderers can safely
    accept either shape (e.g. tests that hand-roll ISO strings).
    """
    if value is None or value == '':
        return default
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    return str(value)
