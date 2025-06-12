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

"""Batch stop update action tool for ElastiCache MCP server."""

from ...common.connection import ElastiCacheConnectionManager
from ...common.decorators import handle_exceptions
from ...common.server import mcp
from ...context import Context
from typing import Dict, List, Optional


@mcp.tool(name='batch-stop-update-action')
@handle_exceptions
async def batch_stop_update_action(
    service_update_name: str,
    replication_group_ids: Optional[List[str]] = None,
    cache_cluster_ids: Optional[List[str]] = None,
) -> Dict:
    """Stop service update for multiple ElastiCache resources.

    Parameters:
        service_update_name (str): The unique ID of the service update to stop.
        replication_group_ids (Optional[List[str]]): List of replication group IDs to stop update.
            Either this or cache_cluster_ids must be provided.
        cache_cluster_ids (Optional[List[str]]): List of cache cluster IDs to stop update.
            Either this or replication_group_ids must be provided.

    Returns:
        Dict containing information about the batch stop operation.
    """
    # Check if readonly mode is enabled
    if Context.readonly_mode():
        raise ValueError(
            'You have configured this tool in readonly mode. To make this change you will have to update your configuration.'
        )

    # Get ElastiCache client
    elasticache_client = ElastiCacheConnectionManager.get_connection()

    # Build request
    request: Dict[str, str | List[str]] = {'ServiceUpdateName': service_update_name}

    if replication_group_ids:
        request['ReplicationGroupIds'] = replication_group_ids
    if cache_cluster_ids:
        request['CacheClusterIds'] = cache_cluster_ids

    # Stop the service update
    response = elasticache_client.batch_stop_update_action(**request)
    return response
