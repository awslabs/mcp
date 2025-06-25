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

"""Data models for the ROSA MCP Server."""

from enum import Enum
from mcp.types import CallToolResult
from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional, Union


class EventItem(BaseModel):
    """Summary of a Kubernetes/OpenShift event.

    This model represents a Kubernetes/OpenShift event with timestamps, message, and metadata.
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
    """Kubernetes/OpenShift resource operations for single resources."""

    CREATE = 'create'
    REPLACE = 'replace'
    PATCH = 'patch'
    DELETE = 'delete'
    READ = 'read'


class ROSAClusterState(str, Enum):
    """ROSA cluster states."""

    PENDING = 'pending'
    INSTALLING = 'installing'  
    READY = 'ready'
    ERROR = 'error'
    DELETING = 'deleting'
    UNINSTALLING = 'uninstalling'
    VALIDATING = 'validating'
    WAITING = 'waiting'


class ROSAClusterSummary(BaseModel):
    """Summary of a ROSA cluster."""

    id: str = Field(..., description='Unique identifier of the ROSA cluster')
    name: str = Field(..., description='Name of the ROSA cluster')
    state: str = Field(..., description='Current state of the cluster')
    version: str = Field(..., description='OpenShift version')
    region: str = Field(..., description='AWS region where cluster is deployed')
    multi_az: bool = Field(False, description='Whether cluster is multi-AZ')
    api_url: Optional[str] = Field(None, description='API endpoint URL')
    console_url: Optional[str] = Field(None, description='Web console URL')
    created_at: Optional[str] = Field(None, description='Creation timestamp')
    nodes: Optional[Dict[str, int]] = Field(
        None, description='Node counts by type (control_plane, infra, worker)'
    )


class ROSAClusterResponse(CallToolResult):
    """Response model for ROSA cluster operations."""

    cluster: ROSAClusterSummary = Field(..., description='ROSA cluster details')
    operation: str = Field(..., description='Operation performed')


class ROSAClusterListResponse(CallToolResult):
    """Response model for listing ROSA clusters."""

    count: int = Field(..., description='Number of clusters found')
    clusters: List[ROSAClusterSummary] = Field(..., description='List of ROSA clusters')


class MachinePoolSummary(BaseModel):
    """Summary of a ROSA machine pool."""

    id: str = Field(..., description='Machine pool ID')
    name: str = Field(..., description='Machine pool name')
    replicas: int = Field(..., description='Number of replicas')
    instance_type: str = Field(..., description='AWS instance type')
    labels: Optional[Dict[str, str]] = Field(None, description='Machine pool labels')
    taints: Optional[List[Dict[str, str]]] = Field(None, description='Node taints')
    availability_zones: Optional[List[str]] = Field(None, description='Availability zones')
    autoscaling: Optional[Dict[str, int]] = Field(
        None, description='Autoscaling configuration (min, max)'
    )


class MachinePoolResponse(CallToolResult):
    """Response model for machine pool operations."""

    machine_pool: MachinePoolSummary = Field(..., description='Machine pool details')
    cluster_name: str = Field(..., description='Name of the parent cluster')
    operation: str = Field(..., description='Operation performed')


class MachinePoolListResponse(CallToolResult):
    """Response model for listing machine pools."""

    cluster_name: str = Field(..., description='Name of the parent cluster')
    count: int = Field(..., description='Number of machine pools found')
    machine_pools: List[MachinePoolSummary] = Field(..., description='List of machine pools')


class IdentityProviderSummary(BaseModel):
    """Summary of a ROSA identity provider."""

    name: str = Field(..., description='Identity provider name')
    type: str = Field(..., description='Type of identity provider (github, gitlab, google, ldap, openid)')
    mapping_method: Optional[str] = Field('claim', description='User mapping method')
    challenge: bool = Field(True, description='Whether provider supports challenge authentication')


class IdentityProviderResponse(CallToolResult):
    """Response model for identity provider operations."""

    idp: IdentityProviderSummary = Field(..., description='Identity provider details')
    cluster_name: str = Field(..., description='Name of the parent cluster')
    operation: str = Field(..., description='Operation performed')


class IdentityProviderListResponse(CallToolResult):
    """Response model for listing identity providers."""

    cluster_name: str = Field(..., description='Name of the parent cluster')
    count: int = Field(..., description='Number of identity providers found')
    idps: List[IdentityProviderSummary] = Field(..., description='List of identity providers')


class ROSACredentialsResponse(CallToolResult):
    """Response model for getting ROSA cluster credentials."""

    api_url: str = Field(..., description='API server URL')
    username: Optional[str] = Field(None, description='Admin username if applicable')
    password: Optional[str] = Field(None, description='Admin password if applicable')
    kubeconfig_path: Optional[str] = Field(None, description='Path to generated kubeconfig file')


class ApplyYamlResponse(CallToolResult):
    """Response model for apply_yaml tool."""

    force_applied: bool = Field(
        False, description='Whether force option was used to update existing resources'
    )
    resources_created: int = Field(0, description='Number of resources created')
    resources_updated: int = Field(0, description='Number of resources updated (when force=True)')


class KubernetesResourceResponse(CallToolResult):
    """Response model for single Kubernetes/OpenShift resource operations."""

    kind: str = Field(..., description='Kind of the Kubernetes/OpenShift resource')
    name: str = Field(..., description='Name of the Kubernetes/OpenShift resource')
    namespace: Optional[str] = Field(None, description='Namespace of the Kubernetes/OpenShift resource')
    api_version: str = Field(..., description='API version of the Kubernetes/OpenShift resource')
    operation: str = Field(
        ..., description='Operation performed (create, replace, patch, delete, read)'
    )
    resource: Optional[Dict[str, Any]] = Field(
        None, description='Resource data (for read operation)'
    )


class ResourceSummary(BaseModel):
    """Summary of a Kubernetes/OpenShift resource."""

    name: str = Field(..., description='Name of the resource')
    namespace: Optional[str] = Field(None, description='Namespace of the resource')
    creation_timestamp: Optional[str] = Field(None, description='Creation timestamp')
    labels: Optional[Dict[str, str]] = Field(None, description='Resource labels')
    annotations: Optional[Dict[str, str]] = Field(None, description='Resource annotations')


class KubernetesResourceListResponse(CallToolResult):
    """Response model for list_resources tool."""

    kind: str = Field(..., description='Kind of the Kubernetes/OpenShift resources')
    api_version: str = Field(..., description='API version of the Kubernetes/OpenShift resources')
    namespace: Optional[str] = Field(None, description='Namespace of the Kubernetes/OpenShift resources')
    count: int = Field(..., description='Number of resources found')
    items: List[ResourceSummary] = Field(..., description='List of resources')


class PodLogResponse(CallToolResult):
    """Response model for get_pod_logs tool."""

    cluster_name: str = Field(..., description='Name of the cluster')
    namespace: str = Field(..., description='Namespace of the pod')
    pod_name: str = Field(..., description='Name of the pod')
    container: Optional[str] = Field(None, description='Container name if specified')
    logs: str = Field(..., description='Pod logs content')
    lines_returned: int = Field(..., description='Number of log lines returned')


class EventsResponse(CallToolResult):
    """Response model for get_k8s_events tool."""

    cluster_name: str = Field(..., description='Name of the cluster')
    kind: str = Field(..., description='Kind of resource the events are for')
    name: str = Field(..., description='Name of the resource')
    namespace: Optional[str] = Field(None, description='Namespace of the resource')
    count: int = Field(..., description='Number of events found')
    events: List[EventItem] = Field(..., description='List of events')


class IAMRoleResponse(CallToolResult):
    """Response model for IAM role operations."""

    role_name: str = Field(..., description='Name of the IAM role')
    role_arn: str = Field(..., description='ARN of the IAM role')
    operation: str = Field(..., description='Operation performed')


class AccountRolesResponse(CallToolResult):
    """Response model for ROSA account roles setup."""

    installer_role_arn: str = Field(..., description='ARN of the installer role')
    control_plane_role_arn: str = Field(..., description='ARN of the control plane role')
    worker_role_arn: str = Field(..., description='ARN of the worker role')
    support_role_arn: str = Field(..., description='ARN of the support role')


class OperatorRolesResponse(CallToolResult):
    """Response model for ROSA operator roles setup."""

    cluster_name: str = Field(..., description='Name of the ROSA cluster')
    operator_roles: List[str] = Field(..., description='List of created operator role ARNs')


class OIDCProviderResponse(CallToolResult):
    """Response model for OIDC provider operations."""

    cluster_name: str = Field(..., description='Name of the ROSA cluster')
    oidc_endpoint: str = Field(..., description='OIDC provider endpoint URL')
    oidc_provider_arn: str = Field(..., description='ARN of the OIDC provider')
    operation: str = Field(..., description='Operation performed')