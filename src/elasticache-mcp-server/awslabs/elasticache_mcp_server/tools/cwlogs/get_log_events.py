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

"""Tool for retrieving log events from CloudWatch Logs."""

from ...common.connection import CloudWatchLogsConnectionManager
from ...common.decorators import handle_exceptions
from ...common.server import mcp
from datetime import datetime
from typing import Any, Dict, Optional


@mcp.tool(name='get-log-events')
@handle_exceptions
async def get_log_events(
    log_stream_name: str,
    log_group_name: Optional[str] = None,
    log_group_identifier: Optional[str] = None,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    next_token: Optional[str] = None,
    limit: Optional[int] = None,
    start_from_head: Optional[bool] = None,
    unmask: Optional[bool] = None,
) -> Dict[str, Any]:
    """Get log events from CloudWatch Logs.

    Args:
        log_group_name: The name of the log group
        log_group_identifier: The unique identifier of the log group
        log_stream_name: The name of the log stream
        start_time: The start of the time range, inclusive
        end_time: The end of the time range, inclusive
        next_token: The token for the next set of items to return
        limit: The maximum number of log events to return
        start_from_head: If true, read from oldest to newest
        unmask: If true, unmask sensitive log data

    Returns:
        Dict containing:
        - events: List of log events
        - nextForwardToken: Token for getting the next set of events
        - nextBackwardToken: Token for getting the previous set of events
    """
    client = CloudWatchLogsConnectionManager.get_connection()

    # Build request parameters
    params: Dict[str, Any] = {
        'logStreamName': log_stream_name,
    }

    # Add optional parameters
    if log_group_name:
        params['logGroupName'] = log_group_name
    if log_group_identifier:
        params['logGroupIdentifier'] = log_group_identifier
    if start_time:
        params['startTime'] = int(start_time.timestamp() * 1000)
    if end_time:
        params['endTime'] = int(end_time.timestamp() * 1000)
    if next_token:
        params['nextToken'] = next_token
    if limit:
        params['limit'] = limit
    if start_from_head is not None:
        params['startFromHead'] = start_from_head
    if unmask is not None:
        params['unmask'] = unmask

    # Make API call
    response = client.get_log_events(**params)

    # Format response
    events = []
    for event in response.get('events', []):
        events.append(
            {
                'timestamp': event['timestamp'],
                'message': event['message'],
                'ingestionTime': event.get('ingestionTime'),
            }
        )

    return {
        'events': events,
        'nextForwardToken': response.get('nextForwardToken'),
        'nextBackwardToken': response.get('nextBackwardToken'),
    }
