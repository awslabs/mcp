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

"""Delete serverless cache operations."""

from ...common.connection import ElastiCacheConnectionManager
from ...common.decorators import handle_exceptions
from ...common.server import mcp
from typing import Dict, Optional


@mcp.tool(name='delete_serverless_cache')
@handle_exceptions
async def delete_serverless_cache(
    serverless_cache_name: str,
    final_snapshot_name: Optional[str] = None,
) -> Dict:
    """Delete an Amazon ElastiCache serverless cache.

    This tool deletes a specified serverless cache from your AWS account.
    The cache must exist and be in a deletable state.

    Parameters:
        serverless_cache_name (str): Name of the serverless cache to delete.
        final_snapshot_name (Optional[str]): Name of the final snapshot to create before deletion.

    Returns:
        Dict containing the deletion response or error information.
    """
    # Get ElastiCache client
    elasticache_client = ElastiCacheConnectionManager.get_connection()

    delete_request = {'ServerlessCacheName': serverless_cache_name}
    if final_snapshot_name:
        delete_request['FinalSnapshotName'] = str(final_snapshot_name)

    response = elasticache_client.delete_serverless_cache(**delete_request)
    return response
