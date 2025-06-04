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
from typing import Optional, Tuple


def calculate_time_window(
    time_window: int = 3600,
    start_time: Optional[datetime.datetime] = None,
    end_time: Optional[datetime.datetime] = None,
) -> Tuple[datetime.datetime, datetime.datetime]:
    """
    Calculate the actual start time and end time for a time window.

    Parameters
    ----------
    time_window : int, optional
        Time window in seconds (default: 3600)
    start_time : datetime, optional
        Explicit start time (takes precedence over time_window if provided)
    end_time : datetime, optional
        Explicit end time (defaults to current time if not provided)

    Returns
    -------
    Tuple[datetime.datetime, datetime.datetime]
        Tuple of (actual_start_time, actual_end_time) with timezone info
    """
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
