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

"""Delete replication group tool for ElastiCache MCP server."""

from ...common.connection import ElastiCacheConnectionManager
from ...common.decorators import handle_exceptions
from ...common.server import mcp
from ...context import Context
from typing import Dict, Optional


@mcp.tool(name='delete-replication-group')
@handle_exceptions
async def delete_replication_group(
    replication_group_id: str,
    retain_primary_cluster: Optional[bool] = None,
    final_snapshot_name: Optional[str] = None,
) -> Dict:
    """Delete an Amazon ElastiCache replication group.

    This tool deletes an existing replication group. You can optionally retain the primary cluster
    as a standalone cache cluster or create a final snapshot before deletion.

    Parameters:
        replication_group_id (str): The identifier of the replication group to delete.
        retain_primary_cluster (Optional[bool]): If True, retains the primary cluster as a standalone
            cache cluster. If False, deletes all clusters in the replication group.
        final_snapshot_name (Optional[str]): The name of a final cache cluster snapshot to create
            before deleting the replication group.

    Returns:
        Dict containing information about the deleted replication group.
    """
    # Check if readonly mode is enabled
    if Context.readonly_mode():
        raise ValueError(
            'You have configured this tool in readonly mode. To make this change you will have to update your configuration.'
        )

    # Get ElastiCache client
    elasticache_client = ElastiCacheConnectionManager.get_connection()

    # Build delete request
    delete_request = {
        'ReplicationGroupId': replication_group_id,
    }

    # Add optional parameters if provided
    if retain_primary_cluster is not None:
        delete_request['RetainPrimaryCluster'] = str(retain_primary_cluster).lower()
    if final_snapshot_name:
        delete_request['FinalSnapshotIdentifier'] = final_snapshot_name

    # Delete the replication group
    response = elasticache_client.delete_replication_group(**delete_request)
    return response
