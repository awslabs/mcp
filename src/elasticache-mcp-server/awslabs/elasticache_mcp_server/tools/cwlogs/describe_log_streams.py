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

"""Tool for describing CloudWatch Logs log streams."""

from ...common.connection import CloudWatchLogsConnectionManager
from ...common.decorators import handle_exceptions
from ...common.server import mcp
from typing import Any, Dict, Optional


@mcp.tool(name='describe-log-streams')
@handle_exceptions
async def describe_log_streams(
    log_group_name: Optional[str] = None,
    log_group_identifier: Optional[str] = None,
    log_stream_name_prefix: Optional[str] = None,
    order_by: Optional[str] = None,
    descending: Optional[bool] = None,
    starting_token: Optional[str] = None,
    page_size: Optional[int] = None,
    max_items: Optional[int] = None,
) -> Dict[str, Any]:
    """Describe CloudWatch Logs log streams.

    Args:
        log_group_name: The name of the log group containing the log streams to describe.
        log_group_identifier: The unique identifier of the log group.
        log_stream_name_prefix: The prefix to match when describing log streams.
        order_by: The parameter to sort by (LogStreamName or LastEventTime).
        descending: If true, results are returned in descending order.
        starting_token: Token for starting the list from a specific page.
        page_size: Number of records to include in each page.
        max_items: Maximum number of records to return in total.

    Returns:
        Dict containing information about the log streams or error details.
    """
    client = CloudWatchLogsConnectionManager.get_connection()

    # Build request parameters
    params: Dict[str, Any] = {}

    # Add optional parameters
    if log_group_name:
        params['logGroupName'] = log_group_name
    if log_group_identifier:
        params['logGroupIdentifier'] = log_group_identifier
    if log_stream_name_prefix:
        params['logStreamNamePrefix'] = log_stream_name_prefix
    if order_by:
        params['orderBy'] = order_by
    if descending is not None:
        params['descending'] = descending
    if starting_token:
        params['nextToken'] = starting_token
    if page_size:
        params['limit'] = page_size

    # If max_items is set, we need to handle pagination manually
    if max_items is not None:
        log_streams = []
        items_remaining = max_items

        while True:
            # Adjust limit if we're close to max_items
            if page_size and items_remaining < page_size:
                params['limit'] = items_remaining

            # Make API call
            response = client.describe_log_streams(**params)
            current_streams = response.get('logStreams', [])

            # Add streams up to max_items
            if len(current_streams) > items_remaining:
                log_streams.extend(current_streams[:items_remaining])
                next_token = response.get('nextToken')  # Save for result
                break
            else:
                log_streams.extend(current_streams)
                items_remaining -= len(current_streams)

            # Check if we need to continue
            if 'nextToken' not in response or items_remaining <= 0:
                next_token = response.get('nextToken')
                break

            # Update token for next iteration
            params['nextToken'] = response['nextToken']

        result = {'logStreams': log_streams}
        if next_token:
            result['nextToken'] = next_token
        return result

    # If max_items is not set, make a single API call
    # Make API call
    response = client.describe_log_streams(**params)

    # Extract relevant information
    log_streams = response.get('logStreams', [])
    next_token = response.get('nextToken')

    result = {'logStreams': log_streams}

    if next_token:
        result['nextToken'] = next_token

    return result
