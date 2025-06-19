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

"""Modify replication group tool for ElastiCache MCP server."""

import json
from ...common.connection import ElastiCacheConnectionManager
from ...common.decorators import handle_exceptions
from ...common.server import mcp
from ...context import Context
from .processors import process_log_delivery_configurations, process_resharding_configuration
from pydantic import BaseModel, ConfigDict, Field
from typing import Any, Dict, List, Optional, Union


@mcp.tool(name='modify-replication-group-shard-configuration')
@handle_exceptions
async def modify_replication_group_shard_configuration(
    replication_group_id: str,
    node_group_count: int,
    apply_immediately: Optional[bool] = None,
    resharding_configuration: Optional[Union[str, List[Dict]]] = None,
) -> Dict:
    """Modify the shard configuration of an existing Amazon ElastiCache replication group.

    This tool modifies the shard configuration of an existing replication group by:
    - Modifying the number of replicas in a shard
    - Specifying preferred availability zones for replicas

    Parameters:
        replication_group_id (str): The identifier of the replication group to modify.
        node_group_count (int): The number of node groups (shards) in the replication group.
        apply_immediately (Optional[bool]): Whether to apply changes immediately or during maintenance window.
        resharding_configuration (Optional[Union[str, List[Dict]]]): Resharding configuration in either shorthand string format or list of dictionaries format.
            Shorthand format: "NodeGroupId=string,NewShardConfiguration={NewReplicaCount=integer,PreferredAvailabilityZones=string1,string2}"
            Multiple configurations can be separated by spaces.
            JSON format: List of dictionaries with required fields:
            - NodeGroupId: string
            - NewShardConfiguration:
                - NewReplicaCount: integer
                - PreferredAvailabilityZones: list of strings (optional)

    Returns:
        Dict containing information about the modified replication group.
    """
    # Check if readonly mode is enabled
    if Context.readonly_mode():
        raise ValueError(
            'You have configured this tool in readonly mode. To make this change you will have to update your configuration.'
        )

    # Get ElastiCache client
    elasticache_client = ElastiCacheConnectionManager.get_connection()

    # Build modify request
    modify_request = {
        'ReplicationGroupId': replication_group_id,
        'NodeGroupCount': node_group_count,
    }

    # Add optional parameters if provided
    if apply_immediately is not None:
        modify_request['ApplyImmediately'] = str(apply_immediately).lower()

    if resharding_configuration:
        try:
            processed_configs = process_resharding_configuration(resharding_configuration)
            modify_request['ReshardingConfiguration'] = json.dumps(processed_configs)
        except ValueError as e:
            return {'error': str(e)}

    # Modify the replication group shard configuration
    response = elasticache_client.modify_replication_group_shard_configuration(**modify_request)
    return response


class ModifyReplicationGroupRequest(BaseModel):
    """Request model for modifying an ElastiCache replication group."""

    model_config = ConfigDict(extra='allow')  # Allow extra fields to support future API additions

    replication_group_id: str = Field(..., description='The identifier of the replication group')
    apply_immediately: Optional[bool] = None
    auto_minor_version_upgrade: Optional[bool] = None
    automatic_failover_enabled: Optional[bool] = None
    cache_node_type: Optional[str] = None
    cache_parameter_group_name: Optional[str] = None
    cache_security_group_names: Optional[List[str]] = None
    engine_version: Optional[str] = None
    log_delivery_configurations: Optional[Union[str, List[Dict]]] = None
    maintenance_window: Optional[str] = None
    multi_az_enabled: Optional[bool] = None
    notification_topic_arn: Optional[str] = None
    notification_topic_status: Optional[str] = None
    num_node_groups: Optional[int] = None
    preferred_node_groups_to_remove: Optional[List[int]] = None
    primary_cluster_id: Optional[str] = None
    replicas_per_node_group: Optional[int] = None
    replication_group_description: Optional[str] = None
    security_group_ids: Optional[List[str]] = None
    snapshot_retention_limit: Optional[int] = None
    snapshot_window: Optional[str] = None
    user_group_ids_to_add: Optional[List[str]] = None
    user_group_ids_to_remove: Optional[List[str]] = None
    node_group_id: Optional[str] = None
    remove_user_groups: Optional[bool] = None
    auth_token: Optional[str] = None
    auth_token_update_strategy: Optional[str] = None


def prepare_modify_request_dict(request: ModifyReplicationGroupRequest) -> Dict[str, Any]:
    """Prepare the request dictionary for the AWS API.

    Args:
        request: The ModifyReplicationGroupRequest object

    Returns:
        Dict containing the properly formatted request parameters
    """
    # Start with required parameters
    modify_request: Dict[str, Any] = {
        'ReplicationGroupId': request.replication_group_id,
    }

    # Optional string parameters
    for param_name, value in [
        ('CacheNodeType', request.cache_node_type),
        ('CacheParameterGroupName', request.cache_parameter_group_name),
        ('EngineVersion', request.engine_version),
        ('PreferredMaintenanceWindow', request.maintenance_window),
        ('NotificationTopicArn', request.notification_topic_arn),
        ('NotificationTopicStatus', request.notification_topic_status),
        ('PrimaryClusterId', request.primary_cluster_id),
        ('ReplicationGroupDescription', request.replication_group_description),
        ('SnapshotWindow', request.snapshot_window),
        ('NodeGroupId', request.node_group_id),
        ('AuthToken', request.auth_token),
        ('AuthTokenUpdateStrategy', request.auth_token_update_strategy),
    ]:
        if value:
            modify_request[param_name] = str(value)

    # Optional numeric parameters
    for param_name, value in [
        ('NodeGroupCount', request.num_node_groups),
        ('ReplicasPerNodeGroup', request.replicas_per_node_group),
        ('SnapshotRetentionLimit', request.snapshot_retention_limit),
    ]:
        if value is not None:
            modify_request[param_name] = value

    # Optional boolean parameters
    for param_name, value in [
        ('ApplyImmediately', request.apply_immediately),
        ('AutoMinorVersionUpgrade', request.auto_minor_version_upgrade),
        ('AutomaticFailoverEnabled', request.automatic_failover_enabled),
        ('MultiAZEnabled', request.multi_az_enabled),
        ('RemoveUserGroups', request.remove_user_groups),
    ]:
        if value is not None:
            modify_request[param_name] = value

    # Optional list parameters
    for param_name, value in [
        ('CacheSecurityGroupNames', request.cache_security_group_names),
        ('SecurityGroupIds', request.security_group_ids),
        ('UserGroupIdsToAdd', request.user_group_ids_to_add),
        ('UserGroupIdsToRemove', request.user_group_ids_to_remove),
    ]:
        if value:
            modify_request[param_name] = list(value)

    # Handle node groups to remove
    if request.preferred_node_groups_to_remove:
        modify_request['NodeGroupsToRemove'] = request.preferred_node_groups_to_remove

    # Handle log delivery configurations
    if request.log_delivery_configurations:
        try:
            processed_configs = process_log_delivery_configurations(
                request.log_delivery_configurations
            )
            if processed_configs:
                modify_request['LogDeliveryConfigurations'] = processed_configs
        except ValueError as e:
            return {'error': str(e)}

    return modify_request


@mcp.tool(name='modify-replication-group')
@handle_exceptions
async def modify_replication_group(request: ModifyReplicationGroupRequest) -> Dict:
    """Modify an existing Amazon ElastiCache replication group.

    This tool modifies the settings of an existing replication group including:
    - Node configuration
    - Security settings
    - Maintenance settings
    - Backup settings
    - Engine settings
    - Monitoring settings
    - User group settings

    Args:
        request: The ModifyReplicationGroupRequest object containing all parameters

    Returns:
        Dict containing information about the modified replication group.
    """
    # Check if readonly mode is enabled
    if Context.readonly_mode():
        raise ValueError(
            'You have configured this tool in readonly mode. To make this change you will have to update your configuration.'
        )

    # Get ElastiCache client
    elasticache_client = ElastiCacheConnectionManager.get_connection()

    # Prepare request dictionary
    modify_request = prepare_modify_request_dict(request)

    # Modify the replication group
    response = elasticache_client.modify_replication_group(**modify_request)
    return response
