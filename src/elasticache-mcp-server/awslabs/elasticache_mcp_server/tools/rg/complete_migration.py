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

"""Complete migration tool for ElastiCache MCP server."""

from ...common.connection import ElastiCacheConnectionManager
from ...common.decorators import handle_exceptions
from ...common.server import mcp
from pydantic import BaseModel, ConfigDict, Field
from typing import Any, Dict, Optional


class CompleteMigrationRequest(BaseModel):
    """Request model for completing migration to an ElastiCache replication group."""

    model_config = ConfigDict(validate_by_name=True, arbitrary_types_allowed=True)

    replication_group_id: str = Field(
        ..., description='The ID of the replication group to which data is being migrated'
    )
    force: Optional[bool] = Field(
        None,
        description='Forces the migration to stop without ensuring that data is in sync. '
        'It is recommended to use this option only to abort the migration and not recommended '
        'when application wants to continue migration to ElastiCache.',
    )


def prepare_request_dict(request: CompleteMigrationRequest) -> Dict[str, Any]:
    """Prepare the request dictionary for the AWS API.

    Args:
        request: The CompleteMigrationRequest object

    Returns:
        Dict containing the properly formatted request parameters
    """
    # Start with required parameters
    complete_migration_request: Dict[str, Any] = {
        'ReplicationGroupId': request.replication_group_id,
    }

    # Add optional force parameter if provided
    if request.force is not None:
        complete_migration_request['Force'] = request.force

    return complete_migration_request


@mcp.tool(name='complete-migration')
@handle_exceptions
async def complete_migration(request: CompleteMigrationRequest) -> Dict:
    """Complete migration to an Amazon ElastiCache replication group.

    This tool completes the migration of data from a Redis instance to an ElastiCache replication group.
    It finalizes the data migration process and transitions the replication group to normal operation.

    Args:
        request: The CompleteMigrationRequest object containing:
            - replication_group_id: The ID of the replication group to which data is being migrated
            - force: (Optional) Forces the migration to stop without ensuring that data is in sync.
              It is recommended to use this option only to abort the migration and not recommended
              when application wants to continue migration to ElastiCache.

    Returns:
        Dict containing information about the migration completion result.
    """
    # Get ElastiCache client
    elasticache_client = ElastiCacheConnectionManager.get_connection()

    # Prepare request dictionary
    complete_request = prepare_request_dict(request)

    # Complete the migration
    response = elasticache_client.complete_migration(**complete_request)
    return response
