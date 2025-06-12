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

"""Describe cache clusters tool for ElastiCache MCP server."""

from ...common.connection import ElastiCacheConnectionManager
from ...common.decorators import handle_exceptions
from ...common.server import mcp
from typing import Dict, Optional


@mcp.tool(name='describe-cache-clusters')
@handle_exceptions
async def describe_cache_clusters(
    cache_cluster_id: Optional[str] = None,
    max_records: Optional[int] = None,
    marker: Optional[str] = None,
    show_cache_node_info: Optional[bool] = None,
    show_cache_clusters_not_in_replication_groups: Optional[bool] = None,
) -> Dict:
    """Describe one or more ElastiCache cache clusters.

    This tool returns information about provisioned cache clusters. If a cache cluster ID
    is specified, information about only that cache cluster is returned. Otherwise, information
    about up to MaxRecords cache clusters is returned.

    Parameters:
        cache_cluster_id (Optional[str]): The identifier for the cache cluster to describe.
            If not provided, information about all cache clusters is returned.
        max_records (Optional[int]): The maximum number of records to include in the response.
            If more records exist than the specified MaxRecords value, a marker is included
            in the response so that the remaining results can be retrieved.
        marker (Optional[str]): An optional marker returned from a previous request. Use this marker
            for pagination of results from this operation. If this parameter is specified,
            the response includes only records beyond the marker, up to the value specified
            by MaxRecords.
        show_cache_node_info (Optional[bool]): Whether to include detailed information about
            cache nodes in the response.
        show_cache_clusters_not_in_replication_groups (Optional[bool]): Whether to show only
            cache clusters that are not members of a replication group.

    Returns:
        Dict containing information about the cache cluster(s), including:
        - CacheClusters: List of cache clusters
        - Marker: Pagination marker for next set of results
    """
    # Get ElastiCache client
    elasticache_client = ElastiCacheConnectionManager.get_connection()

    # Build describe request
    describe_request = {}

    # Add optional parameters if provided
    if cache_cluster_id:
        describe_request['CacheClusterId'] = cache_cluster_id
    if max_records:
        describe_request['MaxRecords'] = max_records
    if marker:
        describe_request['Marker'] = marker
    if show_cache_node_info is not None:
        describe_request['ShowCacheNodeInfo'] = show_cache_node_info
    if show_cache_clusters_not_in_replication_groups is not None:
        describe_request['ShowCacheClustersNotInReplicationGroups'] = (
            show_cache_clusters_not_in_replication_groups
        )

    # Describe the cache cluster(s)
    response = elasticache_client.describe_cache_clusters(**describe_request)
    return response
