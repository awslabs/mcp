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

"""Data models for the HyperPod MCP tools."""

from mcp.types import TextContent
from pydantic import BaseModel, Field
from typing import Dict, List, Optional


class CallToolResult(BaseModel):
    """Base class for tool call results with TextContent only."""

    content: List[TextContent] = Field(..., description='Response content')
    isError: bool = Field(False, description='Whether this is an error response')


class ClusterSummary(BaseModel):
    """Summary of a SageMaker HyperPod cluster."""

    cluster_name: str
    cluster_arn: str
    cluster_status: str
    creation_time: str
    training_plan_arns: Optional[List[str]] = None


class ClusterInstanceStatusDetails(BaseModel):
    """Status details of an instance in a SageMaker HyperPod cluster."""

    status: str  # Valid Values: Running | Failure | Pending | ShuttingDown | SystemUpdating | DeepHealthCheckInProgress
    message: Optional[str] = None


class ClusterNodeSummary(BaseModel):
    """Summary of a SageMaker HyperPod cluster node."""

    instance_group_name: str
    instance_id: str
    instance_status: ClusterInstanceStatusDetails
    instance_type: str
    launch_time: str
    last_software_update_time: Optional[str] = None


class ListClustersResponse(CallToolResult):
    """Response model for list_clusters operation."""

    clusters: List[ClusterSummary] = Field(..., description='List of HyperPod clusters')
    next_token: Optional[str] = Field(None, description='Token for pagination')


class ListClusterNodesResponse(CallToolResult):
    """Response model for list_cluster_nodes operation."""

    nodes: List[ClusterNodeSummary] = Field(..., description='List of HyperPod cluster nodes')
    next_token: Optional[str] = Field(None, description='Token for pagination')


class ClusterEbsVolumeConfig(BaseModel):
    """EBS volume configuration for an instance in a SageMaker HyperPod cluster."""

    volume_size_in_gb: Optional[int] = None


class ClusterInstanceStorageConfig(BaseModel):
    """Storage configuration for an instance in a SageMaker HyperPod cluster."""

    ebs_volume_config: Optional[ClusterEbsVolumeConfig] = None


class ClusterLifeCycleConfig(BaseModel):
    """Life cycle configuration for an instance in a SageMaker HyperPod cluster."""

    on_create: str
    source_s3_uri: str


class VpcConfig(BaseModel):
    """VPC configuration for an instance in a SageMaker HyperPod cluster.

    See: https://docs.aws.amazon.com/sagemaker/latest/APIReference/API_VpcConfig.html
    """

    security_group_ids: Optional[List[str]] = None
    subnets: Optional[List[str]] = None


class ClusterInstancePlacement(BaseModel):
    """Placement information for an instance in a SageMaker HyperPod cluster.

    See: https://docs.aws.amazon.com/sagemaker/latest/APIReference/API_ClusterInstancePlacement.html
    """

    availability_zone: Optional[str] = None
    availability_zone_id: Optional[str] = None


class AlarmDetails(BaseModel):
    """Details of an alarm for auto rollback configuration.

    See: https://docs.aws.amazon.com/sagemaker/latest/APIReference/API_AlarmDetails.html
    """

    alarm_name: str


class CapacitySizeConfig(BaseModel):
    """Configuration for capacity size in rolling deployment policy.

    See: https://docs.aws.amazon.com/sagemaker/latest/APIReference/API_CapacitySizeConfig.html
    """

    type: str  # Valid Values: "INSTANCE_COUNT" | "CAPACITY_PERCENTAGE"
    value: int


class RollingDeploymentPolicy(BaseModel):
    """Policy for rolling deployment during cluster software updates.

    See: https://docs.aws.amazon.com/sagemaker/latest/APIReference/API_RollingDeploymentPolicy.html
    """

    maximum_batch_size: CapacitySizeConfig
    rollback_maximum_batch_size: Optional[CapacitySizeConfig] = None


class DeploymentConfiguration(BaseModel):
    """Configuration for deployment during cluster software updates.

    See: https://docs.aws.amazon.com/sagemaker/latest/APIReference/API_DeploymentConfiguration.html
    """

    auto_rollback_configuration: Optional[List[AlarmDetails]] = None
    rolling_update_policy: Optional[RollingDeploymentPolicy] = None
    wait_interval_in_seconds: Optional[int] = None


class ScheduledUpdateConfig(BaseModel):
    """The configuration object of the schedule that SageMaker follows when updating the AMI..

    See: https://docs.aws.amazon.com/sagemaker/latest/APIReference/API_ScheduledUpdateConfig.html
    """

    schedule_expression: str = Field(
        ...,
        description='A cron expression that specifies the schedule that SageMaker follows when updating the AMI.',
        min_length=1,
        max_length=256,
    )
    deployment_config: Optional[DeploymentConfiguration] = None


class UpdateClusterSoftwareInstanceGroupSpecification(BaseModel):
    """Specification for an instance group to update in a SageMaker HyperPod cluster.

    See: https://docs.aws.amazon.com/sagemaker/latest/APIReference/API_UpdateClusterSoftwareInstanceGroupSpecification.html
    """

    instance_group_name: str


class ClusterNodeDetails(BaseModel):
    """Details of a SageMaker HyperPod cluster node."""

    instance_group_name: str
    instance_id: str
    instance_status: ClusterInstanceStatusDetails
    instance_storage_configs: Optional[List[ClusterInstanceStorageConfig]] = None
    instance_type: str
    last_software_update_time: Optional[str] = None
    launch_time: Optional[str] = None
    life_cycle_config: Optional[ClusterLifeCycleConfig] = None
    override_vpc_config: Optional[VpcConfig] = None
    placement: Optional[ClusterInstancePlacement] = None
    private_dns_hostname: Optional[str] = None
    private_primary_ip: Optional[str] = None
    private_primary_ipv6: Optional[str] = None
    threads_per_core: Optional[int] = None


class DescribeClusterNodeResponse(CallToolResult):
    """Response model for describe_hp_cluster_node operation."""

    node_details: Optional[ClusterNodeDetails] = Field(
        None, description='Details of the HyperPod cluster node'
    )


class UpdateClusterSoftwareResponse(CallToolResult):
    """Response model for update_hp_cluster_software operation."""

    cluster_arn: str = Field(..., description='ARN of the HyperPod cluster')


class BatchDeleteClusterNodesError(BaseModel):
    """Error details for a failed node deletion in a SageMaker HyperPod cluster."""

    code: str
    message: str
    node_id: str


class BatchDeleteClusterNodesResponse(CallToolResult):
    """Response model for batch_delete_hp_cluster_nodes operation."""

    cluster_name: str = Field(..., description='Name of the HyperPod cluster')
    successful: List[str] = Field(..., description='List of successfully deleted node IDs')
    failed: Optional[List[BatchDeleteClusterNodesError]] = Field(
        None, description='List of failed node deletions'
    )


# CloudFormation stack operation response models


class DeployStackResponse(CallToolResult):
    """Response model for deploy operation of manage_hyperpod_stacks tool."""

    stack_name: str = Field(..., description='Name of the CloudFormation stack')
    stack_arn: str = Field(..., description='ARN of the CloudFormation stack')


class DescribeStackResponse(CallToolResult):
    """Response model for describe operation of manage_hyperpod_stacks tool."""

    stack_name: str = Field(..., description='Name of the CloudFormation stack')
    stack_id: str = Field(..., description='ID of the CloudFormation stack')
    creation_time: str = Field(..., description='Creation time of the stack')
    stack_status: str = Field(..., description='Current status of the stack')
    outputs: Dict[str, str] = Field(..., description='Stack outputs')


class DeleteStackResponse(CallToolResult):
    """Response model for delete operation of manage_hyperpod_stacks tool."""

    stack_name: str = Field(..., description='Name of the deleted CloudFormation stack')
    stack_id: str = Field(..., description='ID of the deleted CloudFormation stack')
