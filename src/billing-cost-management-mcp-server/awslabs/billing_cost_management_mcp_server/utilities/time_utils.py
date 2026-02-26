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


def epoch_seconds_to_utc_iso_string(epoch_seconds: Union[int, float]) -> str:
    """Convert epoch seconds to a UTC ISO 8601 formatted string.

    Args:
        epoch_seconds: Unix timestamp in seconds.

    Returns:
        ISO 8601 formatted date string (e.g., "2023-11-14T22:13:20").
    """
    return datetime.fromtimestamp(epoch_seconds, tz=timezone.utc).replace(tzinfo=None).isoformat()
