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

"""Describe events tool for ElastiCache MCP server."""

from ...common.connection import ElastiCacheConnectionManager
from ...common.decorators import handle_exceptions
from ...common.server import mcp
from datetime import datetime
from typing import Dict, Optional


@mcp.tool(name='describe-events')
@handle_exceptions
async def describe_events(
    source_type: Optional[str] = None,
    source_identifier: Optional[str] = None,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    duration: Optional[int] = None,
    max_records: Optional[int] = None,
    marker: Optional[str] = None,
) -> Dict:
    """Returns events related to clusters, cache security groups, and parameter groups.

    Parameters:
        source_type (Optional[str]): The event source to retrieve events for. If not specified, all
            events are returned. Valid values: cache-cluster | cache-parameter-group |
            cache-security-group | cache-subnet-group | replication-group | user | user-group
        source_identifier (Optional[str]): The identifier of the event source for which events are
            returned. For example, if source_type is cache-cluster, you can specify a cluster
            identifier to see all events for only that cluster.
        start_time (Optional[datetime]): The beginning of the time interval to retrieve events for,
            specified in ISO 8601 format.
        end_time (Optional[datetime]): The end of the time interval to retrieve events for,
            specified in ISO 8601 format.
        duration (Optional[int]): The number of minutes worth of events to retrieve.
        max_records (Optional[int]): The maximum number of records to include in the response.
            If more records exist than the specified MaxRecords value, a marker is included
            in the response so that the remaining results can be retrieved.
        marker (Optional[str]): An optional marker returned from a previous request. Use this marker
            for pagination of results from this operation. If this parameter is specified,
            the response includes only records beyond the marker, up to the value specified
            by MaxRecords.

    Returns:
        Dict containing information about the events, including:
        - Events: List of events
        - Marker: Pagination marker for next set of results
    """
    # Get ElastiCache client
    elasticache_client = ElastiCacheConnectionManager.get_connection()

    # Build describe request
    describe_request = {}

    # Add optional parameters if provided
    if source_type:
        describe_request['SourceType'] = source_type
    if source_identifier:
        describe_request['SourceIdentifier'] = source_identifier
    if start_time:
        describe_request['StartTime'] = start_time
    if end_time:
        describe_request['EndTime'] = end_time
    if duration:
        describe_request['Duration'] = duration
    if max_records:
        describe_request['MaxRecords'] = max_records
    if marker:
        describe_request['Marker'] = marker

    # Describe the events
    response = elasticache_client.describe_events(**describe_request)
    return response
