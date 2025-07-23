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

"""Create replication group tool for ElastiCache MCP server."""

from ...common.connection import ElastiCacheConnectionManager
from ...common.decorators import handle_exceptions
from ...common.server import mcp
from ...context import Context
from .processors import process_log_delivery_configurations, process_nodegroup_configuration
from pydantic import BaseModel, ConfigDict, Field
from typing import Any, Dict, List, Optional, Union


class Tag(BaseModel):
    """Tag model for ElastiCache resources."""

    Key: str = Field(..., description='The key for the tag')
    Value: Optional[str] = Field(None, description="The tag's value")
    model_config = ConfigDict(validate_by_name=True, arbitrary_types_allowed=True)


class NodeGroupConfiguration(BaseModel):
    """Node group configuration model."""

    NodeGroupId: Optional[str] = Field(None, description='The identifier for the node group')
    ReplicaCount: Optional[int] = Field(None, description='The number of replica nodes')
    Slots: Optional[str] = Field(None, description='The keyspace for the node group')
    PrimaryAvailabilityZone: Optional[str] = Field(
        None, description='The Availability Zone where the primary node will be launched'
    )
    ReplicaAvailabilityZones: Optional[List[str]] = Field(
        None, description='A list of Availability Zones where the replica nodes will be launched'
    )
    model_config = ConfigDict(validate_by_name=True, arbitrary_types_allowed=True)


class LogDeliveryDestinationDetails(BaseModel):
    """Log delivery destination details model."""

    CloudWatchLogsDetails: Optional[Dict] = Field(
        None, description='The configuration details of CloudWatch Logs destination'
    )
    KinesisFirehoseDetails: Optional[Dict] = Field(
        None, description='The configuration details of Kinesis Data Firehose destination'
    )
    model_config = ConfigDict(validate_by_name=True, arbitrary_types_allowed=True)


class LogDeliveryConfiguration(BaseModel):
    """Log delivery configuration model."""

    LogType: str = Field(..., description='The type of log to deliver')
    DestinationType: str = Field(..., description='The type of destination to deliver to')
    DestinationDetails: LogDeliveryDestinationDetails = Field(
        ..., description='The configuration details of the destination'
    )
    LogFormat: str = Field(..., description='The format of the logs')
    Enabled: bool = Field(..., description='Whether log delivery is enabled')
    model_config = ConfigDict(validate_by_name=True, arbitrary_types_allowed=True)


class CreateReplicationGroupRequest(BaseModel):
    """Request model for creating an ElastiCache replication group."""

    model_config = ConfigDict(validate_by_name=True, arbitrary_types_allowed=True)

    replication_group_id: str = Field(..., description='The identifier of the replication group')
    replication_group_description: str = Field(
        ..., description='The description of the replication group'
    )
    cache_node_type: Optional[str] = Field(
        None, description='The compute and memory capacity of nodes'
    )
    engine: Optional[str] = Field(None, description='The name of the cache engine')
    engine_version: Optional[str] = Field(
        None, description='The version number of the cache engine'
    )
    num_cache_clusters: Optional[int] = Field(None, description='The number of cache clusters')
    preferred_cache_cluster_azs: Optional[List[str]] = Field(
        None, description='List of Availability Zones'
    )
    num_node_groups: Optional[int] = Field(None, description='The number of node groups')
    replicas_per_node_group: Optional[int] = Field(
        None, description='The number of replica nodes in each node group'
    )
    node_group_configuration: Optional[Union[str, List[NodeGroupConfiguration]]] = Field(
        None, description='Configuration for each node group'
    )
    cache_parameter_group_name: Optional[str] = Field(
        None, description='The name of the parameter group to associate'
    )
    cache_subnet_group_name: Optional[str] = Field(
        None, description='The name of the cache subnet group to use'
    )
    cache_security_group_names: Optional[List[str]] = Field(
        None, description='List of cache security group names'
    )
    security_group_ids: Optional[List[str]] = Field(
        None, description='List of Amazon VPC security group IDs'
    )
    tags: Optional[Union[str, List[Tag], Dict[str, Optional[str]]]] = Field(
        None, description='Tags to apply to the replication group'
    )
    snapshot_arns: Optional[List[str]] = Field(
        None, description='List of ARNs of snapshots to restore from'
    )
    snapshot_name: Optional[str] = Field(
        None, description='The name of a snapshot to restore from'
    )
    preferred_maintenance_window: Optional[str] = Field(
        None, description='The weekly time range for maintenance'
    )
    port: Optional[int] = Field(
        None, description='The port number on which the cache accepts connections'
    )
    notification_topic_arn: Optional[str] = Field(
        None, description='The ARN of an SNS topic for notifications'
    )
    auto_minor_version_upgrade: Optional[bool] = Field(
        None, description='Enable/disable automatic minor version upgrades'
    )
    snapshot_retention_limit: Optional[int] = Field(
        None, description='The number of days to retain backups'
    )
    snapshot_window: Optional[str] = Field(None, description='The daily time range for backups')
    auth_token: Optional[str] = Field(
        None, description='Password used to access a password protected server'
    )
    transit_encryption_enabled: Optional[bool] = Field(
        None, description='Enable/disable encryption in transit'
    )
    at_rest_encryption_enabled: Optional[bool] = Field(
        None, description='Enable/disable encryption at rest'
    )
    kms_key_id: Optional[str] = Field(
        None, description='The ID of the KMS key used to encrypt the disk'
    )
    user_group_ids: Optional[List[str]] = Field(
        None, description='List of user group IDs to associate'
    )
    log_delivery_configurations: Optional[Union[str, List[LogDeliveryConfiguration]]] = Field(
        None, description='Log delivery configurations'
    )


def prepare_request_dict(request: CreateReplicationGroupRequest) -> Dict[str, Any]:
    """Prepare the request dictionary for the AWS API.

    Args:
        request: The CreateReplicationGroupRequest object

    Returns:
        Dict containing the properly formatted request parameters
    """
    # Start with required parameters
    create_request: Dict[str, Any] = {
        'ReplicationGroupId': request.replication_group_id,
        'ReplicationGroupDescription': request.replication_group_description,
    }

    # Optional string parameters
    for param_name, value in [
        ('CacheNodeType', request.cache_node_type),
        ('Engine', request.engine),
        ('EngineVersion', request.engine_version),
        ('CacheParameterGroupName', request.cache_parameter_group_name),
        ('CacheSubnetGroupName', request.cache_subnet_group_name),
        ('SnapshotName', request.snapshot_name),
        ('PreferredMaintenanceWindow', request.preferred_maintenance_window),
        ('NotificationTopicArn', request.notification_topic_arn),
        ('SnapshotWindow', request.snapshot_window),
        ('AuthToken', request.auth_token),
        ('KmsKeyId', request.kms_key_id),
    ]:
        if value:
            create_request[param_name] = str(value)

    # Optional numeric parameters
    for param_name, value in [
        ('NumCacheClusters', request.num_cache_clusters),
        ('NumNodeGroups', request.num_node_groups),
        ('ReplicasPerNodeGroup', request.replicas_per_node_group),
        ('Port', request.port),
        ('SnapshotRetentionLimit', request.snapshot_retention_limit),
    ]:
        if value is not None:
            create_request[param_name] = value

    # Optional boolean parameters
    for param_name, value in [
        ('AutoMinorVersionUpgrade', request.auto_minor_version_upgrade),
        ('TransitEncryptionEnabled', request.transit_encryption_enabled),
        ('AtRestEncryptionEnabled', request.at_rest_encryption_enabled),
    ]:
        if value is not None:
            create_request[param_name] = value

    # Optional list parameters
    for param_name, value in [
        ('PreferredCacheClusterAZs', request.preferred_cache_cluster_azs),
        ('CacheSecurityGroupNames', request.cache_security_group_names),
        ('SecurityGroupIds', request.security_group_ids),
        ('SnapshotArns', request.snapshot_arns),
        ('UserGroupIds', request.user_group_ids),
    ]:
        if value:
            create_request[param_name] = list(value)

    # Handle node group configuration
    if request.node_group_configuration:
        if isinstance(request.node_group_configuration, list):
            configs = [
                config.model_dump(exclude_none=True) for config in request.node_group_configuration
            ]
            create_request['NodeGroupConfiguration'] = configs
        else:
            processed_config = process_nodegroup_configuration(request.node_group_configuration)
            if processed_config:
                create_request['NodeGroupConfiguration'] = processed_config

    # Handle tags
    if request.tags:
        if isinstance(request.tags, str):
            # Parse shorthand syntax: Key=string,Value=string
            tag_list = []
            try:
                pairs = [p.strip() for p in request.tags.split(',') if p.strip()]
                for pair in pairs:
                    if '=' not in pair:
                        raise ValueError(
                            'Invalid tag format. Each tag must be in Key=Value format'
                        )
                    key, value = pair.split('=', 1)
                    key = key.strip()
                    value = value.strip() if value.strip() else None
                    if not key:
                        raise ValueError('Tag key cannot be empty')
                    tag_list.append({'Key': key, 'Value': value})
                create_request['Tags'] = tag_list
            except Exception as e:
                raise ValueError(
                    f'Invalid tag shorthand syntax. Expected format: Key=string,Value=string. Error: {str(e)}'
                )
        elif isinstance(request.tags, dict):
            # Handle dictionary format
            tag_list = []
            for k, v in request.tags.items():
                if not k:
                    raise ValueError('Tag key cannot be empty')
                tag_list.append({'Key': k, 'Value': v})
            create_request['Tags'] = tag_list
        elif isinstance(request.tags, list):
            create_request['Tags'] = [tag.model_dump(exclude_none=True) for tag in request.tags]

    # Handle log delivery configurations
    if request.log_delivery_configurations:
        if isinstance(request.log_delivery_configurations, list):
            configs = [
                config.model_dump(exclude_none=True)
                for config in request.log_delivery_configurations
            ]
            create_request['LogDeliveryConfigurations'] = configs
        else:
            processed_configs = process_log_delivery_configurations(
                request.log_delivery_configurations
            )
            if processed_configs:
                create_request['LogDeliveryConfigurations'] = processed_configs

    return create_request


@mcp.tool(name='create-replication-group')
@handle_exceptions
async def create_replication_group(request: CreateReplicationGroupRequest) -> Dict:
    """Create an Amazon ElastiCache replication group.

    This tool creates a new replication group with specified configuration including:
    - Basic replication group settings
    - Cache node configuration
    - Network and security settings
    - Encryption settings
    - Backup and maintenance settings
    - Monitoring and logging settings

    Args:
        request: The CreateReplicationGroupRequest object containing all parameters

    Returns:
        Dict containing information about the created replication group.
    """
    # Check if readonly mode is enabled
    if Context.readonly_mode():
        raise ValueError(
            'You have configured this tool in readonly mode. To make this change you will have to update your configuration.'
        )

    # Get ElastiCache client
    elasticache_client = ElastiCacheConnectionManager.get_connection()

    # Prepare request dictionary
    create_request = prepare_request_dict(request)

    # Create the replication group
    response = elasticache_client.create_replication_group(**create_request)
    return response
