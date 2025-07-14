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

"""EMREc2InstanceHandler for Data Processing MCP Server."""

from awslabs.aws_dataprocessing_mcp_server.models.emr_models import (
    AddInstanceFleetResponse,
    AddInstanceGroupsResponse,
    ListInstanceFleetsResponse,
    ListInstancesResponse,
    ListSupportedInstanceTypesResponse,
    ModifyInstanceFleetResponse,
    ModifyInstanceGroupsResponse,
)
from awslabs.aws_dataprocessing_mcp_server.utils.aws_helper import AwsHelper
from awslabs.aws_dataprocessing_mcp_server.utils.consts import (
    EMR_INSTANCE_FLEET_RESOURCE_TYPE,
    EMR_INSTANCE_GROUP_RESOURCE_TYPE,
)
from awslabs.aws_dataprocessing_mcp_server.utils.logging_helper import (
    LogLevel,
    log_with_request_id,
)
from mcp.server.fastmcp import Context
from mcp.types import TextContent
from pydantic import Field
from typing import Annotated, Any, Dict, List, Optional, Union


class EMREc2InstanceHandler:
    """Handler for Amazon EMR EC2 Instance operations."""

    def __init__(self, mcp, allow_write: bool = False, allow_sensitive_data_access: bool = False):
        """Initialize the EMR EC2 Instance handler.

        Args:
            mcp: The MCP server instance
            allow_write: Whether to enable write access (default: False)
            allow_sensitive_data_access: Whether to allow access to sensitive data (default: False)
        """
        self.mcp = mcp
        self.allow_write = allow_write
        self.allow_sensitive_data_access = allow_sensitive_data_access
        self.emr_client = AwsHelper.create_boto3_client('emr')

        # Register tools
        self.mcp.tool(name='manage_aws_emr_ec2_instances')(self.manage_aws_emr_ec2_instances)

    async def manage_aws_emr_ec2_instances(
        self,
        ctx: Context,
        operation: Annotated[
            str,
            Field(
                description='Operation to perform: add-instance-fleet, add-instance-groups, modify-instance-fleet, modify-instance-groups, list-instance-fleets, list-instances, list-supported-instance-types. Choose read-only operations when write access is disabled.',
            ),
        ],
        cluster_id: Annotated[
            Optional[str],
            Field(
                description='ID of the EMR cluster (required for all operations except list-supported-instance-types).',
            ),
        ] = None,
        instance_fleet_id: Annotated[
            Optional[str],
            Field(
                description='ID of the instance fleet (required for modify-instance-fleet).',
            ),
        ] = None,
        instance_fleet: Annotated[
            Optional[Dict[str, Any]],
            Field(
                description='Instance fleet configuration (required for add-instance-fleet). Must include InstanceFleetType and can include Name, TargetOnDemandCapacity, TargetSpotCapacity, InstanceTypeConfigs, LaunchSpecifications, and ResizeSpecifications.',
            ),
        ] = None,
        instance_groups: Annotated[
            Optional[List[Dict[str, Any]]],
            Field(
                description='List of instance group configurations (required for add-instance-groups). Each must include InstanceRole, InstanceType, InstanceCount, and can include Name, Market, BidPrice, Configurations, EbsConfiguration, AutoScalingPolicy, and CustomAmiId.',
            ),
        ] = None,
        instance_group_configs: Annotated[
            Optional[List[Dict[str, Any]]],
            Field(
                description='List of instance group configurations for modification (required for modify-instance-groups). Each must include InstanceGroupId and can include InstanceCount, EC2InstanceIdsToTerminate, ShrinkPolicy, ReconfigurationType, and Configurations.',
            ),
        ] = None,
        instance_fleet_config: Annotated[
            Optional[Dict[str, Any]],
            Field(
                description='Instance fleet configuration for modification (required for modify-instance-fleet). Can include TargetOnDemandCapacity, TargetSpotCapacity, ResizeSpecifications, InstanceTypeConfigs, and Context.',
            ),
        ] = None,
        instance_group_ids: Annotated[
            Optional[List[str]],
            Field(
                description='List of instance group IDs (optional for list-instances).',
            ),
        ] = None,
        instance_states: Annotated[
            Optional[List[str]],
            Field(
                description='List of instance states to filter by (optional for list-instances). Valid values: AWAITING_FULFILLMENT, PROVISIONING, BOOTSTRAPPING, RUNNING, TERMINATED.',
            ),
        ] = None,
        instance_group_types: Annotated[
            Optional[List[str]],
            Field(
                description='List of instance group types to filter by (optional for list-instances). Valid values: MASTER, CORE, TASK.',
            ),
        ] = None,
        instance_fleet_type: Annotated[
            Optional[str],
            Field(
                description='Instance fleet type to filter by (optional for list-instances). Valid values: MASTER, CORE, TASK.',
            ),
        ] = None,
        release_label: Annotated[
            Optional[str],
            Field(
                description='EMR release label (required for list-supported-instance-types). Format: emr-x.x.x (e.g., emr-6.10.0).',
            ),
        ] = None,
        marker: Annotated[
            Optional[str],
            Field(
                description='Pagination token for list operations.',
            ),
        ] = None,
    ) -> Union[
        AddInstanceFleetResponse,
        AddInstanceGroupsResponse,
        ModifyInstanceFleetResponse,
        ModifyInstanceGroupsResponse,
        ListInstanceFleetsResponse,
        ListInstancesResponse,
        ListSupportedInstanceTypesResponse,
    ]:
        """Manage AWS EMR EC2 instances with both read and write operations.

        This tool provides comprehensive operations for managing Amazon EMR EC2 instances,
        including adding and modifying instance fleets and groups, as well as listing
        instance details. It enables scaling cluster capacity, configuring instance
        specifications, and monitoring instance status.

        ## Requirements
        - The server must be run with the `--allow-write` flag for add-instance-fleet, add-instance-groups,
          modify-instance-fleet, and modify-instance-groups operations
        - Appropriate AWS permissions for EMR instance operations

        ## Operations
        - **add-instance-fleet**: Add an instance fleet to an existing EMR cluster
          - Required: cluster_id, instance_fleet (with InstanceFleetType)
          - Returns: cluster_id, instance_fleet_id, cluster_arn

        - **add-instance-groups**: Add instance groups to an existing EMR cluster
          - Required: cluster_id, instance_groups (each with InstanceRole, InstanceType, InstanceCount)
          - Returns: cluster_id (as job_flow_id), instance_group_ids, cluster_arn

        - **modify-instance-fleet**: Modify an instance fleet in an EMR cluster
          - Required: cluster_id, instance_fleet_id, instance_fleet_config
          - Returns: confirmation of modification

        - **modify-instance-groups**: Modify instance groups in an EMR cluster
          - Required: instance_group_configs (each with InstanceGroupId)
          - Optional: cluster_id
          - Returns: confirmation of modification

        - **list-instance-fleets**: List all instance fleets in an EMR cluster
          - Required: cluster_id
          - Optional: marker
          - Returns: instance_fleets, marker for pagination

        - **list-instances**: List all instances in an EMR cluster
          - Required: cluster_id
          - Optional: instance_group_id, instance_group_types, instance_fleet_id,
                     instance_fleet_type, instance_states, marker
          - Returns: instances, marker for pagination

        - **list-supported-instance-types**: List all supported instance types for EMR
          - Required: release_label
          - Optional: marker
          - Returns: instance_types, marker for pagination

        ## Example
        ```python
        # Add a task instance fleet with mixed instance types
        response = await manage_aws_emr_ec2_instances(
            operation='add-instance-fleet',
            cluster_id='j-123ABC456DEF',
            instance_fleet={
                'InstanceFleetType': 'TASK',
                'Name': 'TaskFleet',
                'TargetOnDemandCapacity': 2,
                'TargetSpotCapacity': 3,
                'InstanceTypeConfigs': [
                    {
                        'InstanceType': 'm5.xlarge',
                        'WeightedCapacity': 1,
                        'BidPriceAsPercentageOfOnDemandPrice': 80,
                    },
                    {
                        'InstanceType': 'm5.2xlarge',
                        'WeightedCapacity': 2,
                        'BidPriceAsPercentageOfOnDemandPrice': 75,
                    },
                ],
            },
        )
        ```

        Args:
            ctx: MCP context
            operation: Operation to perform
            cluster_id: ID of the EMR cluster
            instance_fleet_id: ID of the instance fleet
            instance_fleet: Instance fleet configuration
            instance_groups: List of instance group configurations
            instance_group_configs: List of instance group configurations for modification
            instance_fleet_config: Instance fleet configuration for modification
            instance_group_ids: List of instance group IDs
            instance_states: List of instance states to filter by
            instance_group_types: List of instance group types to filter by
            instance_fleet_type: Instance fleet type to filter by
            release_label: EMR release label for list-supported-instance-types
            marker: Pagination token for list operations

        Returns:
            Union of response types specific to the operation performed
        """
        try:
            if not self.allow_write and operation in [
                'add-instance-fleet',
                'add-instance-groups',
                'modify-instance-fleet',
                'modify-instance-groups',
            ]:
                error_message = f'Operation {operation} is not allowed without write access'
                log_with_request_id(ctx, LogLevel.ERROR, error_message)

                if operation == 'add-instance-fleet':
                    return AddInstanceFleetResponse(
                        isError=True,
                        content=[TextContent(type='text', text=error_message)],
                        cluster_id='',
                        instance_fleet_id='',
                    )
                elif operation == 'add-instance-groups':
                    return AddInstanceGroupsResponse(
                        isError=True,
                        content=[TextContent(type='text', text=error_message)],
                        cluster_id='',
                        instance_group_ids=[],
                    )
                elif operation == 'modify-instance-fleet':
                    return ModifyInstanceFleetResponse(
                        isError=True,
                        content=[TextContent(type='text', text=error_message)],
                        cluster_id='',
                        instance_fleet_id='',
                    )
                elif operation == 'modify-instance-groups':
                    return ModifyInstanceGroupsResponse(
                        isError=True,
                        content=[TextContent(type='text', text=error_message)],
                        cluster_id='',
                        instance_group_ids=[],
                    )

            if operation == 'add-instance-fleet':
                if cluster_id is None or instance_fleet is None:
                    raise ValueError(
                        'cluster_id and instance_fleet are required for add-instance-fleet operation'
                    )

                # verify if resource is already MCP managed
                verification_result = AwsHelper.verify_emr_cluster_managed_by_mcp(
                    self.emr_client, cluster_id, EMR_INSTANCE_FLEET_RESOURCE_TYPE
                )

                tags = None
                if not verification_result['is_valid']:
                    tags = AwsHelper.prepare_resource_tags(EMR_INSTANCE_FLEET_RESOURCE_TYPE)

                # Add instance fleet - ensure ClusterId is a string
                response = self.emr_client.add_instance_fleet(
                    ClusterId=str(cluster_id),
                    InstanceFleet=instance_fleet,
                )

                # Apply tags to the newly created instance fleet
                if tags and not verification_result['is_valid'] and 'InstanceFleetId' in response:
                    self.emr_client.add_tags(
                        ResourceId=str(cluster_id),
                        Tags=[{'Key': k, 'Value': v} for k, v in tags.items()],
                    )

                return AddInstanceFleetResponse(
                    isError=False,
                    content=[
                        TextContent(
                            type='text',
                            text=f'Successfully added instance fleet to EMR cluster {cluster_id}',
                        )
                    ],
                    cluster_id=cluster_id,
                    instance_fleet_id=response.get('InstanceFleetId', ''),
                    cluster_arn=response.get('ClusterArn', ''),
                )

            elif operation == 'add-instance-groups':
                if cluster_id is None or instance_groups is None:
                    raise ValueError(
                        'cluster_id and instance_groups are required for add-instance-groups operation'
                    )

                # verify if resource is already MCP managed
                verification_result = AwsHelper.verify_emr_cluster_managed_by_mcp(
                    self.emr_client, cluster_id, EMR_INSTANCE_GROUP_RESOURCE_TYPE
                )

                tags = None
                if not verification_result['is_valid']:
                    tags = AwsHelper.prepare_resource_tags(EMR_INSTANCE_GROUP_RESOURCE_TYPE)

                # Add instance groups - ensure JobFlowId (ClusterId) is a string
                response = self.emr_client.add_instance_groups(
                    JobFlowId=str(cluster_id),  # API uses JobFlowId instead of ClusterId
                    InstanceGroups=instance_groups,
                )

                # Apply tags to the cluster
                if tags and not verification_result['is_valid'] and 'InstanceGroupIds' in response:
                    self.emr_client.add_tags(
                        ResourceId=cluster_id,
                        Tags=[{'Key': k, 'Value': v} for k, v in tags.items()],
                    )

                return AddInstanceGroupsResponse(
                    isError=False,
                    content=[
                        TextContent(
                            type='text',
                            text=f'Successfully added instance groups to EMR cluster {cluster_id}',
                        )
                    ],
                    cluster_id=cluster_id,
                    job_flow_id=response.get('JobFlowId', ''),
                    instance_group_ids=response.get('InstanceGroupIds', []),
                    cluster_arn=response.get('ClusterArn', ''),
                )

            elif operation == 'modify-instance-fleet':
                if (
                    cluster_id is None
                    or instance_fleet_id is None
                    or instance_fleet_config is None
                ):
                    raise ValueError(
                        'cluster_id, instance_fleet_id, and instance_fleet_config are required for modify-instance-fleet operation'
                    )

                # Modify instance fleet
                instance_fleet_param = {'InstanceFleetId': instance_fleet_id}

                # Add the configuration parameters if provided
                if instance_fleet_config:
                    for key, value in instance_fleet_config.items():
                        instance_fleet_param[key] = value

                # Verify that the cluster is managed by MCP and has the correct resource type
                verification_result = AwsHelper.verify_emr_cluster_managed_by_mcp(
                    self.emr_client, cluster_id, EMR_INSTANCE_FLEET_RESOURCE_TYPE
                )

                if not verification_result['is_valid']:
                    error_message = verification_result['error_message']
                    log_with_request_id(ctx, LogLevel.ERROR, error_message)
                    return ModifyInstanceFleetResponse(
                        isError=True,
                        content=[TextContent(type='text', text=error_message)],
                        cluster_id=cluster_id,
                        instance_fleet_id=instance_fleet_id,
                    )

                # Resource is MCP managed with correct type, proceed with modification
                log_with_request_id(
                    ctx,
                    LogLevel.INFO,
                    'Resource is MCP managed with correct type, proceeding with instance fleet modification',
                )

                # Perform the fleet modification
                self.emr_client.modify_instance_fleet(
                    ClusterId=str(cluster_id), InstanceFleet=instance_fleet_param
                )

                return ModifyInstanceFleetResponse(
                    isError=False,
                    content=[
                        TextContent(
                            type='text',
                            text=f'Successfully modified instance fleet {instance_fleet_id} in EMR cluster {cluster_id}',
                        )
                    ],
                    cluster_id=cluster_id,
                    instance_fleet_id=instance_fleet_id,
                )

            elif operation == 'modify-instance-groups':
                if instance_group_configs is None:
                    raise ValueError(
                        'instance_group_configs is required for modify-instance-groups operation'
                    )

                # Modify instance groups
                # Don't use a params dictionary to avoid type issues
                # We'll pass parameters directly to the API call later

                # Verify that the cluster is managed by MCP and has the correct resource type
                if cluster_id:
                    verification_result = AwsHelper.verify_emr_cluster_managed_by_mcp(
                        self.emr_client, cluster_id, EMR_INSTANCE_GROUP_RESOURCE_TYPE
                    )

                    if not verification_result['is_valid']:
                        error_message = verification_result['error_message']
                        log_with_request_id(ctx, LogLevel.ERROR, error_message)
                        return ModifyInstanceGroupsResponse(
                            isError=True,
                            content=[TextContent(type='text', text=error_message)],
                            cluster_id=cluster_id,
                            instance_group_ids=[],
                        )

                    # Resource is MCP managed with correct type, proceed with modification
                    log_with_request_id(
                        ctx,
                        LogLevel.INFO,
                        'Resource is MCP managed with correct type, proceeding with instance group modification',
                    )
                else:
                    # If no cluster_id is provided, we can't verify tags, so we don't allow the operation
                    error_message = 'Cannot modify instance groups without providing a cluster_id for tag verification'
                    log_with_request_id(ctx, LogLevel.ERROR, error_message)
                    return ModifyInstanceGroupsResponse(
                        isError=True,
                        content=[TextContent(type='text', text=error_message)],
                        cluster_id='',
                        instance_group_ids=[],
                    )

                # Perform the group modification with direct parameter passing
                if cluster_id:
                    self.emr_client.modify_instance_groups(
                        ClusterId=str(cluster_id), InstanceGroups=instance_group_configs
                    )
                else:
                    self.emr_client.modify_instance_groups(InstanceGroups=instance_group_configs)

                # Extract instance group IDs from the configs
                ids = [
                    config.get('InstanceGroupId', '')
                    for config in instance_group_configs
                    if 'InstanceGroupId' in config
                ]

                return ModifyInstanceGroupsResponse(
                    isError=False,
                    content=[
                        TextContent(
                            type='text',
                            text=f'Successfully modified {len(ids)} instance groups',
                        )
                    ],
                    cluster_id=cluster_id or '',
                    instance_group_ids=ids,
                )

            elif operation == 'list-instance-fleets':
                if cluster_id is None:
                    raise ValueError('cluster_id is required for list-instance-fleets operation')

                params = {'ClusterId': str(cluster_id)}
                if marker is not None:
                    params['Marker'] = marker

                # List instance fleets
                response = self.emr_client.list_instance_fleets(**params)

                instance_fleets = response.get('InstanceFleets', [])
                return ListInstanceFleetsResponse(
                    isError=False,
                    content=[
                        TextContent(
                            type='text',
                            text=f'Successfully listed instance fleets for EMR cluster {cluster_id}',
                        )
                    ],
                    cluster_id=cluster_id,
                    instance_fleets=instance_fleets,
                    count=len(instance_fleets),
                    marker=response.get('Marker'),
                )

            elif operation == 'list-instances':
                if cluster_id is None:
                    raise ValueError('cluster_id is required for list-instances operation')

                params = {'ClusterId': str(cluster_id) if cluster_id is not None else ''}

                request_params = {}

                if instance_states is not None:
                    request_params['InstanceStates'] = instance_states
                if instance_group_types is not None:
                    request_params['InstanceGroupTypes'] = instance_group_types
                if instance_group_ids is not None:
                    request_params['InstanceGroupIds'] = instance_group_ids
                if instance_fleet_id is not None:
                    request_params['InstanceFleetId'] = instance_fleet_id
                if instance_fleet_type is not None:
                    log_with_request_id(
                        ctx,
                        LogLevel.INFO,
                        f'Filtering by instance fleet type: {instance_fleet_type}',
                    )
                if marker is not None:
                    request_params['Marker'] = marker

                # Merge the parameters
                params.update(request_params)

                if instance_fleet_type is not None:
                    # Remove it if it's in params to avoid duplicate parameters
                    if 'InstanceFleetType' in params:
                        del params['InstanceFleetType']

                    # Create a modified copy of params for API call
                    api_params = params.copy()

                    api_params['InstanceFleetType'] = instance_fleet_type

                    log_with_request_id(
                        ctx,
                        LogLevel.INFO,
                        f'Calling list_instances with fleet type: {instance_fleet_type}',
                    )
                    response = self.emr_client.list_instances(**api_params)
                else:
                    response = self.emr_client.list_instances(**params)

                instances = response.get('Instances', [])
                return ListInstancesResponse(
                    isError=False,
                    content=[
                        TextContent(
                            type='text',
                            text=f'Successfully listed instances for EMR cluster {cluster_id}',
                        )
                    ],
                    cluster_id=cluster_id,
                    instances=instances,
                    count=len(instances),
                    marker=response.get('Marker'),
                )

            elif operation == 'list-supported-instance-types':
                if release_label is None:
                    raise ValueError(
                        'release_label is required for list-supported-instance-types operation'
                    )

                # Prepare parameters
                params = {'ReleaseLabel': release_label}
                if marker is not None:
                    params['Marker'] = marker

                # List supported instance types
                response = self.emr_client.list_supported_instance_types(**params)

                instance_types = response.get('SupportedInstanceTypes', [])
                return ListSupportedInstanceTypesResponse(
                    isError=False,
                    content=[
                        TextContent(
                            type='text',
                            text='Successfully listed supported instance types for EMR',
                        )
                    ],
                    instance_types=instance_types,
                    count=len(instance_types),
                    marker=response.get('Marker'),
                    release_label=release_label,
                )

            else:
                error_message = f'Invalid operation: {operation}. Must be one of: add-instance-fleet, add-instance-groups, modify-instance-fleet, modify-instance-groups, list-instance-fleets, list-instances, list-supported-instance-types'
                log_with_request_id(ctx, LogLevel.ERROR, error_message)
                return ListInstancesResponse(
                    isError=True,
                    content=[TextContent(type='text', text=error_message)],
                    cluster_id='',
                    instances=[],
                )

        except ValueError as e:
            log_with_request_id(ctx, LogLevel.ERROR, f'Parameter validation error: {str(e)}')
            raise
        except Exception as e:
            error_message = f'Error in manage_aws_emr_ec2_instances: {str(e)}'
            log_with_request_id(ctx, LogLevel.ERROR, error_message)
            return ListInstancesResponse(
                isError=True,
                content=[TextContent(type='text', text=error_message)],
                cluster_id='',
                instances=[],
            )
