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

"""Describe engine default parameters tool for ElastiCache MCP server."""

from ...common.connection import ElastiCacheConnectionManager
from ...common.decorators import handle_exceptions
from ...common.server import mcp
from typing import Dict, Optional


@mcp.tool(name='describe-engine-default-parameters')
@handle_exceptions
async def describe_engine_default_parameters(
    cache_parameter_group_family: str,
    max_records: Optional[int] = None,
    marker: Optional[str] = None,
) -> Dict:
    """Returns the default engine and system parameter information for the specified cache engine family.

    Parameters:
        cache_parameter_group_family (str): The name of the cache parameter group family.
            Valid values are: memcached1.4 | memcached1.5 | memcached1.6 | redis2.6 | redis2.8 |
            redis3.2 | redis4.0 | redis5.0 | redis6.x | redis7.x | valkey7.x | valkey8.x
        max_records (Optional[int]): The maximum number of records to include in the response.
            If more records exist than the specified MaxRecords value, a marker is included
            in the response so that the remaining results can be retrieved.
        marker (Optional[str]): An optional marker returned from a previous request. Use this marker
            for pagination of results from this operation. If this parameter is specified,
            the response includes only records beyond the marker, up to the value specified
            by MaxRecords.

    Returns:
        Dict containing information about the engine default parameters, including:
        - Parameters: List of parameters with their details
        - CacheParameterGroupFamily: The name of the cache parameter group family
        - Marker: Pagination marker for next set of results
    """
    # Get ElastiCache client
    elasticache_client = ElastiCacheConnectionManager.get_connection()

    # Build describe request
    describe_request = {'CacheParameterGroupFamily': cache_parameter_group_family}

    # Add optional parameters if provided
    if max_records is not None:
        describe_request['MaxRecords'] = str(max_records)
    if marker:
        describe_request['Marker'] = marker

    # Describe the engine default parameters
    response = elasticache_client.describe_engine_default_parameters(**describe_request)
    return response
