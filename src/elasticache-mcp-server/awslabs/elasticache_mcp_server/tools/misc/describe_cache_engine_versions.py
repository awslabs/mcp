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

"""Describe cache engine versions tool for ElastiCache MCP server."""

from ...common.connection import ElastiCacheConnectionManager
from ...common.decorators import handle_exceptions
from ...common.server import mcp
from typing import Dict, Optional


@mcp.tool(name='describe-cache-engine-versions')
@handle_exceptions
async def describe_cache_engine_versions(
    engine: Optional[str] = None,
    engine_version: Optional[str] = None,
    cache_parameter_group_family: Optional[str] = None,
    max_records: Optional[int] = None,
    marker: Optional[str] = None,
    default_only: Optional[bool] = None,
) -> Dict:
    """Returns a list of the available cache engines and their versions.

    Parameters:
        engine (Optional[str]): The cache engine to return. Valid values: memcached | redis | valkey
        engine_version (Optional[str]): The cache engine version to return.
            Example: memcached 1.4.14, redis 6.x, valkey 8.0
        cache_parameter_group_family (Optional[str]): The name of a specific cache parameter group family.
            Valid values are: memcached1.4 | memcached1.5 | memcached1.6 | redis2.6 | redis2.8 |
            redis3.2 | redis4.0 | redis5.0 | redis6.x | redis7.x | valkey7.x | valkey8.x
        max_records (Optional[int]): The maximum number of records to include in the response.
            If more records exist than the specified MaxRecords value, a marker is included
            in the response so that the remaining results can be retrieved.
        marker (Optional[str]): An optional marker returned from a previous request. Use this marker
            for pagination of results from this operation. If this parameter is specified,
            the response includes only records beyond the marker, up to the value specified
            by MaxRecords.
        default_only (Optional[bool]): If true, specifies that only the default version of the specified engine
            or engine and major version combination is to be returned.

    Returns:
        Dict containing information about the cache engine versions, including:
        - CacheEngineVersions: List of cache engine versions
        - Marker: Pagination marker for next set of results
    """
    # Get ElastiCache client
    elasticache_client = ElastiCacheConnectionManager.get_connection()

    # Build describe request
    describe_request = {}

    # Add optional parameters if provided
    if engine:
        describe_request['Engine'] = engine
    if engine_version:
        describe_request['EngineVersion'] = engine_version
    if cache_parameter_group_family:
        describe_request['CacheParameterGroupFamily'] = cache_parameter_group_family
    if max_records:
        describe_request['MaxRecords'] = max_records
    if marker:
        describe_request['Marker'] = marker
    if default_only is not None:
        describe_request['DefaultOnly'] = default_only

    # Describe the cache engine versions
    response = elasticache_client.describe_cache_engine_versions(**describe_request)
    return response
