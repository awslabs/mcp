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

"""Data models for the EKS MCP Server."""

from enum import Enum
from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional, Union


class EventItem(BaseModel):
    """Summary of a Kubernetes event.

    This model represents a Kubernetes event with timestamps, message, and metadata.
    Events provide information about state changes and important occurrences in the cluster.
    """

    first_timestamp: Optional[str] = Field(
        None, description='First timestamp of the event in ISO format'
    )
    last_timestamp: Optional[str] = Field(
        None, description='Last timestamp of the event in ISO format'
    )
    count: Optional[int] = Field(None, description='Count of occurrences', ge=0)
    message: str = Field(..., description='Event message describing what happened')
    reason: Optional[str] = Field(
        None, description='Short, machine-understandable reason for the event'
    )
    reporting_component: Optional[str] = Field(
        None, description='Component that reported the event (e.g., kubelet, controller-manager)'
    )
    type: Optional[str] = Field(None, description='Event type (Normal, Warning)')


class Operation(str, Enum):
    """Kubernetes resource operations for single resources."""

    CREATE = 'create'
    REPLACE = 'replace'
    PATCH = 'patch'
    DELETE = 'delete'
    READ = 'read'


class ApplyYamlData(BaseModel):
    """Data model for apply_yaml response."""

    force_applied: bool = Field(
        False, description='Whether force option was used to update existing resources'
    )
    resources_created: int = Field(0, description='Number of resources created')
    resources_updated: int = Field(0, description='Number of resources updated (when force=True)')


class KubernetesResourceData(BaseModel):
    """Data model for single Kubernetes resource operations."""

    kind: str = Field(..., description='Kind of the Kubernetes resource')
    name: str = Field(..., description='Name of the Kubernetes resource')
    namespace: Optional[str] = Field(None, description='Namespace of the Kubernetes resource')
    api_version: str = Field(..., description='API version of the Kubernetes resource')
    operation: str = Field(
        ..., description='Operation performed (create, replace, patch, delete, read)'
    )
    resource: Optional[Dict[str, Any]] = Field(
        None, description='Resource data (for read operation)'
    )


class ResourceSummary(BaseModel):
    """Summary of a Kubernetes resource."""

    name: str = Field(..., description='Name of the resource')
    namespace: Optional[str] = Field(None, description='Namespace of the resource')
    creation_timestamp: Optional[str] = Field(None, description='Creation timestamp')
    labels: Optional[Dict[str, str]] = Field(None, description='Resource labels')
    annotations: Optional[Dict[str, str]] = Field(None, description='Resource annotations')


class KubernetesResourceListData(BaseModel):
    """Data model for list_resources response."""

    kind: str = Field(..., description='Kind of the Kubernetes resources')
    api_version: str = Field(..., description='API version of the Kubernetes resources')
    namespace: Optional[str] = Field(None, description='Namespace of the Kubernetes resources')
    count: int = Field(..., description='Number of resources found')
    items: List[ResourceSummary] = Field(..., description='List of resources')


class ApiVersionsData(BaseModel):
    """Data model for list_api_versions response."""

    cluster_name: str = Field(..., description='Name of the EKS cluster')
    api_versions: List[str] = Field(..., description='List of available API versions')
    count: int = Field(..., description='Number of API versions')


class GenerateAppManifestData(BaseModel):
    """Data model for generate_app_manifest response."""

    output_file_path: str = Field(..., description='Path to the output manifest file')


class PodLogsData(BaseModel):
    """Data model for get_pod_logs response."""

    pod_name: str = Field(..., description='Name of the pod')
    namespace: str = Field(..., description='Namespace of the pod')
    container_name: Optional[str] = Field(None, description='Container name (if specified)')
    log_lines: List[str] = Field(..., description='Pod log lines')


class EventsData(BaseModel):
    """Data model for get_k8s_events response."""

    involved_object_kind: str = Field(..., description='Kind of the involved object')
    involved_object_name: str = Field(..., description='Name of the involved object')
    involved_object_namespace: Optional[str] = Field(
        None, description='Namespace of the involved object'
    )
    count: int = Field(..., description='Number of events found')
    events: List[EventItem] = Field(..., description='List of events')


class CloudWatchLogEntry(BaseModel):
    """Model for a CloudWatch log entry.

    This model represents a single log entry from CloudWatch logs,
    containing a timestamp and the log message.
    """

    timestamp: str = Field(..., description='Timestamp of the log entry in ISO format')
    message: str = Field(..., description='Log message content')


class CloudWatchLogsData(BaseModel):
    """Data model for CloudWatch logs response.

    This model contains the structured data from a CloudWatch logs query,
    including resource information, time range, and log entries.
    """

    resource_type: str = Field(..., description='Resource type (pod, node, container)')
    resource_name: Optional[str] = Field(None, description='Resource name')
    cluster_name: str = Field(..., description='Name of the EKS cluster')
    log_type: str = Field(
        ..., description='Log type (application, host, performance, control-plane, or custom)'
    )
    log_group: str = Field(..., description='CloudWatch log group name')
    start_time: str = Field(..., description='Start time in ISO format')
    end_time: str = Field(..., description='End time in ISO format')
    log_entries: List[Dict[str, Any]] = Field(
        ..., description='Log entries with timestamps and messages'
    )


class CloudWatchDataPoint(BaseModel):
    """Model for a CloudWatch metric data point.

    This model represents a single data point from CloudWatch metrics,
    containing a timestamp and the corresponding metric value.
    """

    timestamp: str = Field(..., description='Timestamp of the data point in ISO format')
    value: float = Field(..., description='Metric value')


class CloudWatchMetricsData(BaseModel):
    """Data model for CloudWatch metrics response.

    This model contains the structured data from a CloudWatch metrics query,
    including metric details, time range, and data points.
    """

    cluster_name: str = Field(..., description='Name of the EKS cluster')
    metric_name: str = Field(..., description='Metric name (e.g., cpu_usage_total, memory_rss)')
    namespace: str = Field(..., description='CloudWatch namespace (e.g., ContainerInsights)')
    start_time: str = Field(..., description='Start time in ISO format')
    end_time: str = Field(..., description='End time in ISO format')
    data_points: List[Dict[str, Any]] = Field(
        ..., description='Metric data points with timestamps and values'
    )


class StackSummary(BaseModel):
    """Summary of a CloudFormation stack."""

    stack_name: str = Field(..., description='Name of the CloudFormation stack')
    stack_id: str = Field(..., description='ID of the CloudFormation stack')
    cluster_name: str = Field(..., description='Name of the EKS cluster')
    creation_time: str = Field(..., description='Creation time of the stack')
    stack_status: str = Field(..., description='Current status of the stack')
    description: Optional[str] = Field(None, description='Description of the stack')


class ManageEksStacksData(BaseModel):
    """Data model for manage_eks_stacks response."""

    operation: str = Field(
        ..., description='Operation performed (generate, deploy, describe, delete)'
    )

    # Fields for generate operation
    template_path: str = Field(
        '', description='Path to the generated template (generate operation)'
    )

    # Fields for deploy operation
    stack_arn: str = Field('', description='ARN of the CloudFormation stack (deploy operation)')

    # Fields for describe operation
    creation_time: str = Field('', description='Creation time of the stack (describe operation)')
    stack_status: str = Field('', description='Current status of the stack (describe operation)')
    outputs: Dict[str, str] = Field(
        default_factory=dict, description='Stack outputs (describe operation)'
    )

    # Common fields
    stack_name: str = Field('', description='Name of the CloudFormation stack')
    stack_id: str = Field('', description='ID of the CloudFormation stack')
    cluster_name: str = Field('', description='Name of the EKS cluster')


class PolicySummary(BaseModel):
    """Summary of an IAM policy."""

    policy_type: str = Field(..., description='Type of the policy (Managed or Inline)')
    description: Optional[str] = Field(None, description='Description of the policy')
    policy_document: Optional[Dict[str, Any]] = Field(None, description='Policy document')


class RoleDescriptionData(BaseModel):
    """Data model for get_policies_for_role response."""

    role_arn: str = Field(..., description='ARN of the IAM role')
    assume_role_policy_document: Dict[str, Any] = Field(
        ..., description='Assume role policy document'
    )
    description: Optional[str] = Field(None, description='Description of the IAM role')
    managed_policies: List[PolicySummary] = Field(
        ..., description='Managed policies attached to the IAM role'
    )
    inline_policies: List[PolicySummary] = Field(
        ..., description='Inline policies embedded in the IAM role'
    )


class AddInlinePolicyData(BaseModel):
    """Data model for add_inline_policy response."""

    policy_name: str = Field(..., description='Name of the inline policy to create')
    role_name: str = Field(..., description='Name of the role to add the policy to')
    permissions_added: Union[Dict[str, Any], List[Dict[str, Any]]] = Field(
        ..., description='Permissions to include in the policy (in JSON format)'
    )


class MetricsGuidanceData(BaseModel):
    """Data model for get_eks_metrics_guidance response.

    This model contains the structured data from a metrics guidance query,
    including resource type and available metrics with their details.
    """

    resource_type: str = Field(
        ..., description='Resource type (cluster, node, pod, namespace, service)'
    )
    metrics: List[Dict[str, Any]] = Field(..., description='List of metrics with their details')


class EksVpcConfigData(BaseModel):
    """Data model for get_eks_vpc_config response.

    This model contains comprehensive VPC configuration details for any EKS cluster,
    including CIDR blocks and route tables which are essential for understanding
    network connectivity. For hybrid node setups, it also automatically identifies
    and includes remote node and pod CIDR configurations.
    """

    vpc_id: str = Field(..., description='ID of the VPC')
    cidr_block: str = Field(..., description='Primary CIDR block of the VPC')
    additional_cidr_blocks: List[str] = Field(
        [], description='Additional CIDR blocks associated with the VPC'
    )
    routes: List[Dict[str, Any]] = Field(
        ..., description='List of route entries in the main route table'
    )
    remote_node_cidr_blocks: List[str] = Field(
        [], description='CIDR blocks configured for remote node access (for hybrid setups)'
    )
    remote_pod_cidr_blocks: List[str] = Field(
        [], description='CIDR blocks configured for remote pod access (for hybrid setups)'
    )
    subnets: List[Dict[str, Any]] = Field(
        [], description='List of subnets in the VPC with their configurations'
    )
    cluster_name: str = Field(..., description='Name of the EKS cluster')


class EksInsightStatus(BaseModel):
    """Status of an EKS insight with status code and reason."""

    status: str = Field(..., description='Status of the insight (e.g., PASSING, FAILING, UNKNOWN)')
    reason: str = Field(..., description='Explanation of the current status')


class EksInsightItem(BaseModel):
    """Model for a single EKS insight item."""

    id: str = Field(..., description='Unique identifier of the insight')
    name: str = Field(..., description='Name of the insight')
    category: str = Field(
        ..., description='Category of the insight (e.g., CONFIGURATION, UPGRADE_READINESS)'
    )
    kubernetes_version: Optional[str] = Field(
        None, description='Target Kubernetes version for upgrade insights'
    )
    last_refresh_time: float = Field(
        ..., description='Timestamp when the insight was last refreshed'
    )
    last_transition_time: float = Field(
        ..., description='Timestamp when the insight last changed status'
    )
    description: str = Field(..., description='Description of what the insight checks')
    insight_status: EksInsightStatus = Field(..., description='Current status of the insight')
    recommendation: Optional[str] = Field(
        None, description='Recommendation for addressing the insight'
    )
    additional_info: Optional[Dict[str, str]] = Field(
        None, description='Additional information links'
    )
    resources: Optional[List[str]] = Field(None, description='Resources involved in the insight')
    category_specific_summary: Optional[Dict[str, Any]] = Field(
        None, description='Additional category-specific details'
    )


class EksInsightsData(BaseModel):
    """Data model for get_eks_insights response."""

    cluster_name: str = Field(..., description='Name of the EKS cluster')
    insights: List[EksInsightItem] = Field(..., description='List of insights')
    next_token: Optional[str] = Field(None, description='Token for pagination')
    detail_mode: bool = Field(
        False, description='Whether the response contains detailed insight information'
    )
