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

"""Modify serverless cache operations."""

from ...common.connection import ElastiCacheConnectionManager
from ...common.decorators import handle_exceptions
from ...common.server import mcp
from .models import ModifyServerlessCacheRequest
from typing import Dict


@mcp.tool(name='modify_serverless_cache')
@handle_exceptions
async def modify_serverless_cache(request: ModifyServerlessCacheRequest) -> Dict:
    """Modify an Amazon ElastiCache serverless cache.

    This tool modifies the configuration of an existing serverless cache including:
    - Cache description
    - Engine version
    - Snapshot settings
    - Usage limits
    - Security groups
    - User groups

    Parameters:
        serverless_cache_name (str): Name of the serverless cache to modify.
        apply_immediately (Optional[bool]): Whether to apply changes immediately or during maintenance window.
        description (Optional[str]): New description for the cache.
        major_engine_version (Optional[str]): New major engine version.
        snapshot_retention_limit (Optional[int]): Number of days for which ElastiCache retains automatic snapshots.
        daily_snapshot_time (Optional[str]): Time range (in UTC) when daily snapshots are taken (e.g., '04:00-05:00').
        cache_usage_limits (Optional[CacheUsageLimits]): New usage limits for the cache. Structure:
            {
                "DataStorage": {
                    "Maximum": int,  # Maximum storage in GB
                    "Minimum": int,  # Minimum storage in GB
                    "Unit": "GB"     # Storage unit (currently only GB is supported)
                },
                "ECPUPerSecond": {
                    "Maximum": int,  # Maximum ECPU per second
                    "Minimum": int   # Minimum ECPU per second
                }
            }
        security_group_ids (Optional[List[str]]): List of VPC security group IDs.
        user_group_id (Optional[str]): ID of the user group to associate with the cache.

    Returns:
        Dict containing information about the modified serverless cache.
    """
    """Modify an Amazon ElastiCache serverless cache.

    This tool modifies the configuration of an existing serverless cache including:
    - Cache description
    - Engine version
    - Snapshot settings
    - Usage limits
    - Security groups
    - User groups

    Args:
        request: ModifyServerlessCacheRequest object containing modification parameters

    Returns:
        Dict containing information about the modified serverless cache.
    """
    # Get ElastiCache client
    elasticache_client = ElastiCacheConnectionManager.get_connection()

    # Convert request to dict and remove None values
    modify_request = {k: v for k, v in request.model_dump().items() if v is not None}

    # Convert snake_case to PascalCase for AWS API
    aws_request = {}
    for key, value in modify_request.items():
        # Special handling for boolean values
        if isinstance(value, bool):
            aws_request[key.title().replace('_', '')] = str(value).lower()
        else:
            aws_request[key.title().replace('_', '')] = value

    # Modify the cache
    response = elasticache_client.modify_serverless_cache(**aws_request)
    return response
