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

"""Describe service updates tool for ElastiCache MCP server."""

from ...common.connection import ElastiCacheConnectionManager
from ...common.decorators import handle_exceptions
from ...common.server import mcp
from typing import Dict, List, Optional


@mcp.tool(name='describe-service-updates')
@handle_exceptions
async def describe_service_updates(
    service_update_name: Optional[str] = None,
    service_update_status: Optional[List[str]] = None,
    starting_token: Optional[str] = None,
    page_size: Optional[int] = None,
    max_items: Optional[int] = None,
) -> Dict:
    """Returns details of the service updates.

    Parameters:
        service_update_name (Optional[str]): The unique ID of the service update to describe.
        service_update_status (Optional[List[str]]): List of status values to filter by.
            Valid values: available | cancelled | expired | complete
        starting_token (Optional[str]): An optional token returned from a previous request.
            Use this token for pagination of results from this operation.
        page_size (Optional[int]): The maximum number of records to include in each page
            of results.
        max_items (Optional[int]): The maximum number of records to include in the response.
            If more records exist than the specified MaxItems value, a marker is included
            in the response so that the remaining results can be retrieved.

    Returns:
        Dict containing information about the service updates, including:
        - ServiceUpdates: List of service updates
        - NextToken: Token for next set of results
    """
    # Get ElastiCache client
    elasticache_client = ElastiCacheConnectionManager.get_connection()

    # Build describe request
    describe_request = {}

    # Add optional parameters if provided
    if service_update_name:
        describe_request['ServiceUpdateName'] = service_update_name
    if service_update_status:
        describe_request['ServiceUpdateStatus'] = service_update_status
    if starting_token:
        describe_request['Marker'] = starting_token
    if page_size:
        describe_request['MaxRecords'] = page_size
    if max_items:
        describe_request['MaxItems'] = max_items

    # Describe the service updates
    response = elasticache_client.describe_service_updates(**describe_request)
    return response
