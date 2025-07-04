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

"""Tool for filtering log events from CloudWatch Logs."""

from ...common.connection import CloudWatchLogsConnectionManager
from ...common.decorators import handle_exceptions
from ...common.server import mcp
from datetime import datetime
from typing import Any, Dict, List, Optional


@mcp.tool(name='filter-log-events')
@handle_exceptions
async def filter_log_events(
    log_group_name: Optional[str] = None,
    log_group_identifier: Optional[str] = None,
    log_stream_names: Optional[List[str]] = None,
    log_stream_name_prefix: Optional[str] = None,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    filter_pattern: Optional[str] = None,
    interleaved: Optional[bool] = None,
    unmask: Optional[bool] = None,
    starting_token: Optional[str] = None,
    page_size: Optional[int] = None,
    max_items: Optional[int] = None,
) -> Dict[str, Any]:
    """Filter log events from CloudWatch Logs.

    Args:
        log_group_name: The name of the log group
        log_group_identifier: The unique identifier of the log group
        log_stream_names: Optional list of log stream names to search
        log_stream_name_prefix: Optional prefix to match log stream names
        start_time: The start of the time range, inclusive
        end_time: The end of the time range, inclusive
        filter_pattern: The filter pattern to use
        interleaved: If true, multiple log streams are interleaved
        unmask: If true, unmask sensitive log data
        starting_token: Token for getting the next set of events
        page_size: Number of events to return per page
        max_items: Maximum number of events to return in total

    Returns:
        Dict containing:
        - events: List of filtered log events
        - searchedLogStreams: List of log streams that were searched
        - nextToken: Token for getting the next set of events
    """
    client = CloudWatchLogsConnectionManager.get_connection()

    # Build request parameters
    params: Dict[str, Any] = {}

    # Add required parameters
    if log_group_name:
        params['logGroupName'] = log_group_name
    if log_group_identifier:
        params['logGroupIdentifier'] = log_group_identifier

    # Add optional parameters
    if log_stream_names:
        params['logStreamNames'] = log_stream_names
    if log_stream_name_prefix:
        params['logStreamNamePrefix'] = log_stream_name_prefix
    if start_time:
        params['startTime'] = int(start_time.timestamp() * 1000)
    if end_time:
        params['endTime'] = int(end_time.timestamp() * 1000)
    if filter_pattern:
        params['filterPattern'] = filter_pattern
    if interleaved is not None:
        params['interleaved'] = interleaved
    if unmask is not None:
        params['unmask'] = unmask
    if starting_token:
        params['nextToken'] = starting_token
    if page_size:
        params['limit'] = page_size

    # Make API call
    response = client.filter_log_events(**params)

    # Format response
    events = []
    for event in response.get('events', []):
        events.append(
            {
                'timestamp': event['timestamp'],
                'message': event['message'],
                'ingestionTime': event.get('ingestionTime'),
                'eventId': event.get('eventId'),
                'logStreamName': event.get('logStreamName'),
            }
        )

    searched_streams = []
    for stream in response.get('searchedLogStreams', []):
        searched_streams.append(
            {
                'logStreamName': stream.get('logStreamName'),
                'searchedCompletely': stream.get('searchedCompletely', False),
            }
        )

    return {
        'events': events,
        'searchedLogStreams': searched_streams,
        'nextToken': response.get('nextToken'),
    }
