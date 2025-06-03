# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance
# with the License. A copy of the License is located at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES
# OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions
# and limitations under the License.

"""Data models for the EKS MCP Server."""

from enum import Enum
from mcp.types import CallToolResult
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


class ApplyYamlResponse(CallToolResult):
    """Response model for apply_yaml tool."""

    force_applied: bool = Field(
        False, description='Whether force option was used to update existing resources'
    )
    resources_created: int = Field(0, description='Number of resources created')
    resources_updated: int = Field(0, description='Number of resources updated (when force=True)')


class KubernetesResourceResponse(CallToolResult):
    """Response model for single Kubernetes resource operations."""

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


class KubernetesResourceListResponse(CallToolResult):
    """Response model for list_resources tool."""

    kind: str = Field(..., description='Kind of the Kubernetes resources')
    api_version: str = Field(..., description='API version of the Kubernetes resources')
    namespace: Optional[str] = Field(None, description='Namespace of the Kubernetes resources')
    count: int = Field(..., description='Number of resources found')
    items: List[ResourceSummary] = Field(..., description='List of resources')


class ApiVersionsResponse(CallToolResult):
    """Response model for list_api_versions tool."""

    cluster_name: str = Field(..., description='Name of the EKS cluster')
    api_versions: List[str] = Field(..., description='List of available API versions')
    count: int = Field(..., description='Number of API versions')


class GenerateAppManifestResponse(CallToolResult):
    """Response model for generate_app_manifest tool."""

    output_file_path: str = Field(..., description='Path to the output manifest file')


class PodLogsResponse(CallToolResult):
    """Response model for get_pod_logs tool."""

    pod_name: str = Field(..., description='Name of the pod')
    namespace: str = Field(..., description='Namespace of the pod')
    container_name: Optional[str] = Field(None, description='Container name (if specified)')
    log_lines: List[str] = Field(..., description='Pod log lines')


class EventsResponse(CallToolResult):
    """Response model for get_k8s_events tool."""

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


class CloudWatchLogsResponse(CallToolResult):
    """Response model for get_cloudwatch_logs tool.

    This model contains the response from a CloudWatch logs query,
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


class CloudWatchMetricsResponse(CallToolResult):
    """Response model for get_cloudwatch_metrics tool.

    This model contains the response from a CloudWatch metrics query,
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


class GenerateTemplateResponse(CallToolResult):
    """Response model for generate operation of manage_eks_stacks tool."""

    template_path: str = Field(..., description='Path to the generated template')


class DeployStackResponse(CallToolResult):
    """Response model for deploy operation of manage_eks_stacks tool."""

    stack_name: str = Field(..., description='Name of the CloudFormation stack')
    stack_arn: str = Field(..., description='ARN of the CloudFormation stack')
    cluster_name: str = Field(..., description='Name of the EKS cluster')


class DescribeStackResponse(CallToolResult):
    """Response model for describe operation of manage_eks_stacks tool."""

    stack_name: str = Field(..., description='Name of the CloudFormation stack')
    stack_id: str = Field(..., description='ID of the CloudFormation stack')
    cluster_name: str = Field(..., description='Name of the EKS cluster')
    creation_time: str = Field(..., description='Creation time of the stack')
    stack_status: str = Field(..., description='Current status of the stack')
    outputs: Dict[str, str] = Field(..., description='Stack outputs')


class DeleteStackResponse(CallToolResult):
    """Response model for delete operation of manage_eks_stacks tool."""

    stack_name: str = Field(..., description='Name of the deleted CloudFormation stack')
    stack_id: str = Field(..., description='ID of the deleted CloudFormation stack')
    cluster_name: str = Field(..., description='Name of the EKS cluster')


class PolicySummary(BaseModel):
    """Summary of an IAM policy."""

    policy_type: str = Field(..., description='Type of the policy (Managed or Inline)')
    description: Optional[str] = Field(None, description='Description of the policy')
    policy_document: Optional[Dict[str, Any]] = Field(None, description='Policy document')


class RoleDescriptionResponse(CallToolResult):
    """Response model for get_policies_for_role tool."""

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


class AddInlinePolicyResponse(CallToolResult):
    """Response model for add_inline_policy tool."""

    policy_name: str = Field(..., description='Name of the inline policy to create')
    role_name: str = Field(..., description='Name of the role to add the policy to')
    permissions_added: Union[Dict[str, Any], List[Dict[str, Any]]] = Field(
        ..., description='Permissions to include in the policy (in JSON format)'
    )


class MetricsGuidanceResponse(CallToolResult):
    """Response model for get_eks_metrics_guidance tool.

    This model contains the response from a metrics guidance query,
    including resource type and available metrics with their details.
    """

    resource_type: str = Field(
        ..., description='Resource type (cluster, node, pod, namespace, service)'
    )
    metrics: List[Dict[str, Any]] = Field(..., description='List of metrics with their details')
