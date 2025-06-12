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

"""Create cache cluster tool for ElastiCache MCP server."""

from ...common.connection import ElastiCacheConnectionManager
from ...common.decorators import handle_exceptions
from ...common.server import mcp
from ...context import Context
from ..rg.processors import process_log_delivery_configurations
from pydantic import BaseModel, ConfigDict, Field
from typing import Any, Dict, List, Optional, Union


class CreateCacheClusterRequest(BaseModel):
    """Request model for creating an ElastiCache cache cluster."""

    model_config = ConfigDict(validate_by_name=True, arbitrary_types_allowed=True)

    cache_cluster_id: str = Field(..., description='The cache cluster identifier')
    cache_node_type: Optional[str] = Field(
        None, description='The compute and memory capacity of nodes'
    )
    engine: Optional[str] = Field(None, description='The name of the cache engine')
    engine_version: Optional[str] = Field(
        None, description='The version number of the cache engine'
    )
    num_cache_nodes: Optional[int] = Field(None, description='The number of cache nodes', gt=0)
    preferred_availability_zone: Optional[str] = Field(
        None, description='The EC2 Availability Zone for the cluster'
    )
    preferred_availability_zones: Optional[List[str]] = Field(
        None, description='List of preferred Availability Zones'
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
    tags: Optional[Union[str, List[Dict[str, str]], Dict[str, str]]] = Field(
        None, description='Tags to apply'
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
    outpost_mode: Optional[str] = Field(
        None, description="Outpost mode ('single-outpost' or 'cross-outpost')"
    )
    preferred_outpost_arn: Optional[str] = Field(
        None, description='The ARN of the preferred outpost'
    )
    preferred_outpost_arns: Optional[List[str]] = Field(
        None, description='List of preferred outpost ARNs'
    )
    log_delivery_configurations: Optional[Union[str, List[Dict]]] = Field(
        None, description='Log delivery configurations'
    )


@mcp.tool(name='create-cache-cluster')
@handle_exceptions
async def create_cache_cluster(request: CreateCacheClusterRequest) -> Dict:
    """Create an Amazon ElastiCache cache cluster."""
    # Check if readonly mode is enabled
    if Context.readonly_mode():
        raise ValueError(
            'You have configured this tool in readonly mode. To make this change you will have to update your configuration.'
        )

    # Get ElastiCache client
    elasticache_client = ElastiCacheConnectionManager.get_connection()

    # Convert request model to dictionary, only including non-None values
    create_request: Dict[str, Any] = {
        'CacheClusterId': request.cache_cluster_id
    }  # Required parameter

    # Optional parameters - only include if they have a value
    if request.cache_node_type is not None:
        create_request['CacheNodeType'] = request.cache_node_type
    if request.engine is not None:
        create_request['Engine'] = request.engine
    if request.engine_version is not None:
        create_request['EngineVersion'] = request.engine_version
    if request.num_cache_nodes is not None:
        create_request['NumCacheNodes'] = request.num_cache_nodes
    if request.preferred_availability_zone is not None:
        create_request['PreferredAvailabilityZone'] = request.preferred_availability_zone
    if request.preferred_availability_zones is not None:
        create_request['PreferredAvailabilityZones'] = request.preferred_availability_zones
    if request.cache_parameter_group_name is not None:
        create_request['CacheParameterGroupName'] = request.cache_parameter_group_name
    if request.cache_subnet_group_name is not None:
        create_request['CacheSubnetGroupName'] = request.cache_subnet_group_name
    if request.cache_security_group_names is not None:
        create_request['CacheSecurityGroupNames'] = request.cache_security_group_names
    if request.security_group_ids is not None:
        create_request['SecurityGroupIds'] = request.security_group_ids
    if request.tags:
        if isinstance(request.tags, str):
            # Parse shorthand syntax: Key=string,Value=string
            tag_list = []
            try:
                pairs = [p.strip() for p in request.tags.split(',') if p.strip()]
                for pair in pairs:
                    if '=' not in pair:
                        return {
                            'error': 'Invalid tag format. Each tag must be in Key=Value format'
                        }
                    key, value = pair.split('=', 1)
                    key = key.strip()
                    value = value.strip() if value.strip() else None
                    if not key:
                        return {'error': 'Tag key cannot be empty'}
                    tag_list.append({'Key': key, 'Value': value})
                create_request['Tags'] = tag_list
            except Exception as e:
                return {
                    'error': f'Invalid tag shorthand syntax. Expected format: Key=string,Value=string. Error: {str(e)}'
                }
        elif isinstance(request.tags, dict):
            # Handle dictionary format
            tag_list = []
            for k, v in request.tags.items():
                if not k:
                    return {'error': 'Tag key cannot be empty'}
                tag_list.append({'Key': k, 'Value': v})
            create_request['Tags'] = tag_list
        elif isinstance(request.tags, list):
            # Handle list format
            for tag in request.tags:
                if not isinstance(tag, dict) or 'Key' not in tag:
                    return {'error': 'Each tag must be a dictionary with a Key'}
                if not tag['Key']:
                    return {'error': 'Tag key cannot be empty'}
            create_request['Tags'] = request.tags
    if request.snapshot_arns is not None:
        create_request['SnapshotArns'] = request.snapshot_arns
    if request.snapshot_name is not None:
        create_request['SnapshotName'] = request.snapshot_name
    if request.preferred_maintenance_window is not None:
        create_request['PreferredMaintenanceWindow'] = request.preferred_maintenance_window
    if request.port is not None:
        create_request['Port'] = request.port
    if request.notification_topic_arn is not None:
        create_request['NotificationTopicArn'] = request.notification_topic_arn
    if request.auto_minor_version_upgrade is not None:
        create_request['AutoMinorVersionUpgrade'] = request.auto_minor_version_upgrade
    if request.snapshot_retention_limit is not None:
        create_request['SnapshotRetentionLimit'] = request.snapshot_retention_limit
    if request.snapshot_window is not None:
        create_request['SnapshotWindow'] = request.snapshot_window
    if request.auth_token is not None:
        create_request['AuthToken'] = request.auth_token
    if request.outpost_mode is not None:
        create_request['OutpostMode'] = request.outpost_mode
    if request.preferred_outpost_arn is not None:
        create_request['PreferredOutpostArn'] = request.preferred_outpost_arn
    if request.preferred_outpost_arns is not None:
        create_request['PreferredOutpostArns'] = request.preferred_outpost_arns
    if request.log_delivery_configurations:
        try:
            processed_configs = process_log_delivery_configurations(
                request.log_delivery_configurations
            )
            create_request['LogDeliveryConfigurations'] = processed_configs
        except ValueError as e:
            return {'error': str(e)}

    # Create the cache cluster
    response = elasticache_client.create_cache_cluster(**create_request)
    return response
