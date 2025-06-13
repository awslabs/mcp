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

"""Create serverless cache operations."""

from ...common.connection import ElastiCacheConnectionManager
from ...common.decorators import handle_exceptions
from ...common.server import mcp
from ...context import Context
from .models import CreateServerlessCacheRequest
from typing import Dict


@mcp.tool(name='create_serverless_cache')
@handle_exceptions
async def create_serverless_cache(request: CreateServerlessCacheRequest) -> Dict:
    """Create a new Amazon ElastiCache serverless cache.

    This tool creates a new serverless cache with specified configuration including:
    - Serverless cache name and capacity
    - Optional VPC and security settings
    - Optional encryption settings
    - Optional snapshot restoration and backup settings
    - Optional usage limits and user groups
    - Optional tags

    Parameters:
        serverless_cache_name (str): Name of the serverless cache.
        engine (str): Cache engine type.
        description (Optional[str]): Description for the cache.
        kms_key_id (Optional[str]): KMS key ID for encryption.
        major_engine_version (Optional[str]): Major engine version.
        snapshot_arns_to_restore (Optional[List[str]]): List of snapshot ARNs to restore from.
        subnet_ids (Optional[List[str]]): List of subnet IDs for VPC configuration.
        tags (Optional[Union[str, List[Dict[str, Optional[str]]], Dict[str, Optional[str]]]]): Tags to apply to the cache.
            Tag requirements:
            - Key: (string) Required. The key for the tag. Must not be empty.
            - Value: (string) Optional. The tag's value. May be null.

            Supports three formats:
            1. Shorthand syntax: "Key=value,Key2=value2" or "Key=,Key2=" for null values
            2. Dictionary: {"key": "value", "key2": null}
            3. JSON array: [{"Key": "string", "Value": "string"}, {"Key": "string2", "Value": null}]

            Can be None if no tags are needed.
        security_group_ids (Optional[List[str]]): List of security group IDs.
        cache_usage_limits (Optional[CacheUsageLimits]): Usage limits for the cache. Structure:
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
        user_group_id (Optional[str]): ID of the user group to associate with the cache.
        snapshot_retention_limit (Optional[int]): Number of days for which ElastiCache retains automatic snapshots.
        daily_snapshot_time (Optional[str]): Time range (in UTC) when daily snapshots are taken (e.g., '04:00-05:00').

    Returns:
        Dict containing information about the created serverless cache.
    """
    """Create a new Amazon ElastiCache serverless cache.

    This tool creates a new serverless cache with specified configuration including:
    - Serverless cache name and capacity
    - Optional VPC and security settings
    - Optional encryption settings
    - Optional snapshot restoration and backup settings
    - Optional usage limits and user groups
    - Optional tags

    Args:
        request: The CreateServerlessCacheRequest object containing all parameters

    Returns:
        Dict containing information about the created serverless cache.
    """
    # Check if readonly mode is enabled
    if Context.readonly_mode():
        raise ValueError(
            'You have configured this tool in readonly mode. To make this change you will have to update your configuration.'
        )

    # Get ElastiCache client
    elasticache_client = ElastiCacheConnectionManager.get_connection()

    # Build AWS API request
    create_request = {}

    # Required parameters
    create_request['ServerlessCacheName'] = request.serverless_cache_name
    create_request['Engine'] = request.engine

    # Optional string parameters
    for param_name, value in [
        ('Description', request.description),
        ('KmsKeyId', request.kms_key_id),
        ('MajorEngineVersion', request.major_engine_version),
        ('UserGroupId', request.user_group_id),
        ('DailySnapshotTime', request.daily_snapshot_time),
    ]:
        if value:
            create_request[param_name] = str(value)

    # Optional list parameters
    for param_name, value in [
        ('SnapshotArnsToRestore', request.snapshot_arns_to_restore),
        ('SubnetIds', request.subnet_ids),
        ('SecurityGroupIds', request.security_group_ids),
    ]:
        if value:
            create_request[param_name] = list(map(str, value))

    # Optional numeric parameters
    if request.snapshot_retention_limit is not None:
        create_request['SnapshotRetentionLimit'] = str(request.snapshot_retention_limit)

    # Cache usage limits
    if request.cache_usage_limits:
        limits_dict = request.cache_usage_limits.model_dump()
        # Ensure numeric values are properly formatted
        if 'DataStorage' in limits_dict:
            limits_dict['DataStorage']['Maximum'] = int(limits_dict['DataStorage']['Maximum'])
            limits_dict['DataStorage']['Minimum'] = int(limits_dict['DataStorage']['Minimum'])
        if 'ECPUPerSecond' in limits_dict:
            limits_dict['ECPUPerSecond']['Maximum'] = int(limits_dict['ECPUPerSecond']['Maximum'])
            limits_dict['ECPUPerSecond']['Minimum'] = int(limits_dict['ECPUPerSecond']['Minimum'])
        create_request['CacheUsageLimits'] = limits_dict

    # Tags
    if request.tags:
        if isinstance(request.tags, str):
            # Parse string format "key=value,key2=value2"
            tags = []
            for pair in request.tags.split(','):
                key, value = pair.split('=')
                tags.append(
                    {
                        'Key': str(key.strip()),
                        'Value': str(value.strip()) if value.strip() else None,
                    }
                )
            create_request['Tags'] = tags
        elif isinstance(request.tags, dict):
            # Convert dict format to list of Tag objects
            create_request['Tags'] = [
                {'Key': str(k), 'Value': str(v) if v is not None else None}
                for k, v in request.tags.items()
            ]
        else:
            # Convert Tag objects to dict format
            create_request['Tags'] = [
                {'Key': str(tag.Key), 'Value': str(tag.Value) if tag.Value is not None else None}
                for tag in request.tags
            ]

    # Create the cache
    response = elasticache_client.create_serverless_cache(**create_request)
    return response
