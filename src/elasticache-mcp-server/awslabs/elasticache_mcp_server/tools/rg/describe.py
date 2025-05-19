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

"""Describe replication groups tool for ElastiCache MCP server."""

from ...common.connection import ElastiCacheConnectionManager
from ...common.decorators import handle_exceptions
from ...common.server import mcp
from typing import Dict, Optional


@mcp.tool(name='describe-replication-groups')
@handle_exceptions
async def describe_replication_groups(
    replication_group_id: Optional[str] = None,
    max_records: Optional[int] = None,
    marker: Optional[str] = None,
) -> Dict:
    """Describe one or more ElastiCache replication groups.

    This tool returns information about provisioned replication groups. If a replication group ID
    is specified, information about only that replication group is returned. Otherwise, information
    about up to MaxRecords replication groups is returned.

    Parameters:
        replication_group_id (Optional[str]): The identifier for the replication group to describe.
            If not provided, information about all replication groups is returned.
        max_records (Optional[int]): The maximum number of records to include in the response.
            If more records exist than the specified MaxRecords value, a marker is included
            in the response so that the remaining results can be retrieved.
        marker (Optional[str]): An optional marker returned from a previous request. Use this marker
            for pagination of results from this operation. If this parameter is specified,
            the response includes only records beyond the marker, up to the value specified
            by MaxRecords.

    Returns:
        Dict containing information about the replication group(s), including:
        - ReplicationGroups: List of replication groups
        - Marker: Pagination marker for next set of results
    """
    # Get ElastiCache client
    elasticache_client = ElastiCacheConnectionManager.get_connection()

    # Build describe request
    describe_request = {}

    # Add optional parameters if provided
    if replication_group_id:
        describe_request['ReplicationGroupId'] = replication_group_id
    if max_records:
        describe_request['MaxRecords'] = max_records
    if marker:
        describe_request['Marker'] = marker

    # Describe the replication group(s)
    response = elasticache_client.describe_replication_groups(**describe_request)
    return response
