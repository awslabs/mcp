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

"""Modify cache cluster tool for ElastiCache MCP server."""

from ...common.connection import ElastiCacheConnectionManager
from ...common.decorators import handle_exceptions
from ...common.server import mcp
from ..rg.processors import process_log_delivery_configurations
from .processors import process_scale_config
from pydantic import BaseModel, ConfigDict, Field
from typing import Any, Dict, List, Optional, Union


class ModifyCacheClusterRequest(BaseModel):
    """Request model for modifying an ElastiCache cache cluster."""

    model_config = ConfigDict(validate_by_name=True, arbitrary_types_allowed=True)

    cache_cluster_id: str = Field(..., description='The cache cluster to modify')
    num_cache_nodes: Optional[int] = Field(None, description='The new number of cache nodes')
    cache_node_ids_to_remove: Optional[List[str]] = Field(
        None, description='Cache node IDs to remove when scaling down'
    )
    az_mode: Optional[str] = Field(
        None,
        description='Specifies whether nodes in this Memcached cluster are created in a single AZ or multiple AZs',
    )
    new_availability_zones: Optional[List[str]] = Field(
        None, description='List of Availability Zones to use when modifying AZ mode'
    )
    cache_security_group_names: Optional[List[str]] = Field(
        None, description='List of cache security group names to associate'
    )
    security_group_ids: Optional[List[str]] = Field(
        None, description='List of Amazon VPC security group IDs'
    )
    preferred_maintenance_window: Optional[str] = Field(
        None, description='The weekly time range for maintenance'
    )
    notification_topic_arn: Optional[str] = Field(
        None, description='The ARN of an SNS topic for notifications'
    )
    cache_parameter_group_name: Optional[str] = Field(
        None, description='The name of the cache parameter group to apply'
    )
    notification_topic_status: Optional[str] = Field(
        None, description='The status of the SNS notification topic'
    )
    apply_immediately: Optional[bool] = Field(
        None, description='Whether to apply changes immediately or during maintenance window'
    )
    engine_version: Optional[str] = Field(
        None, description='The upgraded version of the cache engine'
    )
    auto_minor_version_upgrade: Optional[bool] = Field(
        None, description='Enable/disable automatic minor version upgrades'
    )
    snapshot_retention_limit: Optional[int] = Field(
        None, description='The number of days to retain backups'
    )
    snapshot_window: Optional[str] = Field(None, description='The daily time range for backups')
    cache_node_type: Optional[str] = Field(
        None, description='The new compute and memory capacity of the nodes'
    )
    auth_token: Optional[str] = Field(
        None, description='The password used to access a password protected server'
    )
    auth_token_update_strategy: Optional[str] = Field(
        None, description="Strategy to use when updating auth token ('SET', 'ROTATE', 'DELETE')"
    )
    log_delivery_configurations: Optional[Union[str, List[Dict]]] = Field(
        None, description='Log delivery configurations'
    )
    scale_config: Optional[Union[str, Dict]] = Field(None, description='Scale configuration')


@mcp.tool(name='modify-cache-cluster')
@handle_exceptions
async def modify_cache_cluster(request: ModifyCacheClusterRequest) -> Dict:
    """Modify an existing Amazon ElastiCache cache cluster."""
    # Get ElastiCache client
    elasticache_client = ElastiCacheConnectionManager.get_connection()

    # Convert request model to dictionary, only including non-None values
    modify_request: Dict[str, Any] = {'CacheClusterId': request.cache_cluster_id}

    if request.num_cache_nodes is not None:
        modify_request['NumCacheNodes'] = request.num_cache_nodes
    if request.cache_node_ids_to_remove:
        modify_request['CacheNodeIdsToRemove'] = request.cache_node_ids_to_remove
    if request.az_mode:
        modify_request['AZMode'] = request.az_mode
    if request.new_availability_zones:
        modify_request['NewAvailabilityZones'] = request.new_availability_zones
    if request.cache_security_group_names:
        modify_request['CacheSecurityGroupNames'] = request.cache_security_group_names
    if request.security_group_ids:
        modify_request['SecurityGroupIds'] = request.security_group_ids
    if request.preferred_maintenance_window:
        modify_request['PreferredMaintenanceWindow'] = request.preferred_maintenance_window
    if request.notification_topic_arn:
        modify_request['NotificationTopicArn'] = request.notification_topic_arn
    if request.cache_parameter_group_name:
        modify_request['CacheParameterGroupName'] = request.cache_parameter_group_name
    if request.notification_topic_status:
        modify_request['NotificationTopicStatus'] = request.notification_topic_status
    if request.apply_immediately is not None:
        modify_request['ApplyImmediately'] = request.apply_immediately
    if request.engine_version:
        modify_request['EngineVersion'] = request.engine_version
    if request.auto_minor_version_upgrade is not None:
        modify_request['AutoMinorVersionUpgrade'] = request.auto_minor_version_upgrade
    if request.snapshot_retention_limit is not None:
        modify_request['SnapshotRetentionLimit'] = request.snapshot_retention_limit
    if request.snapshot_window:
        modify_request['SnapshotWindow'] = request.snapshot_window
    if request.cache_node_type:
        modify_request['CacheNodeType'] = request.cache_node_type
    if request.auth_token:
        modify_request['AuthToken'] = request.auth_token
    if request.auth_token_update_strategy:
        modify_request['AuthTokenUpdateStrategy'] = request.auth_token_update_strategy
    if request.log_delivery_configurations:
        try:
            processed_configs = process_log_delivery_configurations(
                request.log_delivery_configurations
            )
            modify_request['LogDeliveryConfigurations'] = processed_configs
        except ValueError as e:
            return {'error': str(e)}
    if request.scale_config:
        try:
            processed_scale_config = process_scale_config(request.scale_config)
            modify_request['ScaleConfig'] = processed_scale_config
        except ValueError as e:
            return {'error': str(e)}

    # Modify the cache cluster
    response = elasticache_client.modify_cache_cluster(**modify_request)
    return response
