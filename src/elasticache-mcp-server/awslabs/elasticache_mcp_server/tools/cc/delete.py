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

"""Delete cache cluster tool for ElastiCache MCP server."""

from ...common.connection import ElastiCacheConnectionManager
from ...common.decorators import handle_exceptions
from ...common.server import mcp
from typing import Optional


@mcp.tool(name='delete-cache-cluster')
@handle_exceptions
async def delete_cache_cluster(
    cache_cluster_id: str,
    final_snapshot_identifier: Optional[str] = None,
) -> dict:
    """Delete an Amazon ElastiCache cache cluster.

    This tool deletes an existing cache cluster. Optionally, it can create a final
    snapshot of the cluster before deletion.

    Parameters:
        cache_cluster_id (str): The ID of the cache cluster to delete.
        final_snapshot_identifier (Optional[str]): The user-supplied name of a final
            cache cluster snapshot. This is the unique name that identifies the
            snapshot. ElastiCache creates the snapshot, and then deletes the cache
            cluster immediately afterward.

    Returns:
        Dict containing information about the deleted cache cluster.
    """
    # Get ElastiCache client
    elasticache_client = ElastiCacheConnectionManager.get_connection()

    # Build delete request
    delete_request = {
        'CacheClusterId': cache_cluster_id,
    }

    # Add optional final snapshot if provided
    if final_snapshot_identifier:
        delete_request['FinalSnapshotIdentifier'] = final_snapshot_identifier

    # Delete the cache cluster
    response = elasticache_client.delete_cache_cluster(**delete_request)
    return response
