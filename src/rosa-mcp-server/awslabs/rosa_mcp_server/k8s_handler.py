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

"""Kubernetes/OpenShift handler for the ROSA MCP Server."""

import os
import subprocess
import tempfile
import yaml
from awslabs.rosa_mcp_server.logging_helper import LogLevel, log_with_request_id
from awslabs.rosa_mcp_server.models import (
    ApplyYamlResponse,
    EventItem,
    EventsResponse,
    KubernetesResourceListResponse,
    KubernetesResourceResponse,
    Operation,
    PodLogResponse,
    ResourceSummary,
)
from kubernetes import client, config
from kubernetes.client.rest import ApiException
from loguru import logger
from mcp.server.fastmcp import Context, FastMCP
from mcp.types import CallToolResult
from pydantic import Field
from typing import Any, Dict, List, Optional


class K8sHandler:
    """Handler for Kubernetes/OpenShift operations in the ROSA MCP Server.

    This class provides tools for interacting with ROSA clusters using Kubernetes APIs.
    It handles authentication through ROSA CLI and provides access to OpenShift resources.
    """

    def __init__(
        self,
        mcp: FastMCP,
        allow_write: bool = False,
        allow_sensitive_data_access: bool = False
    ):
        """Initialize the K8s handler."""
        self.mcp = mcp
        self.allow_write = allow_write
        self.allow_sensitive_data_access = allow_sensitive_data_access
        self._register_tools()

    def _get_kubeconfig(self, cluster_name: str) -> str:
        """Generate and return path to kubeconfig for a ROSA cluster."""
        kubeconfig_path = f'/tmp/kubeconfig-{cluster_name}'
        
        # Generate kubeconfig using ROSA CLI
        cmd = ['rosa', 'create', 'kubeconfig', '--cluster', cluster_name, '--output', kubeconfig_path]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            raise Exception(f'Failed to generate kubeconfig: {result.stderr}')
        
        return kubeconfig_path

    def _get_k8s_client(self, cluster_name: str, api_type: str = 'core'):
        """Get a Kubernetes API client for the specified cluster."""
        kubeconfig_path = self._get_kubeconfig(cluster_name)
        config.load_kube_config(config_file=kubeconfig_path)
        
        if api_type == 'core':
            return client.CoreV1Api()
        elif api_type == 'apps':
            return client.AppsV1Api()
        elif api_type == 'batch':
            return client.BatchV1Api()
        elif api_type == 'networking':
            return client.NetworkingV1Api()
        elif api_type == 'rbac':
            return client.RbacAuthorizationV1Api()
        elif api_type == 'custom':
            return client.CustomObjectsApi()
        else:
            return client.CoreV1Api()

    def _register_tools(self):
        """Register Kubernetes/OpenShift tools with the MCP server."""
        
        # Apply YAML manifest
        @self.mcp.tool()
        async def apply_yaml(
            ctx: Context,
            yaml_path: str = Field(..., description='Path to YAML manifest file'),
            cluster_name: str = Field(..., description='Name of the ROSA cluster'),
            namespace: str = Field('default', description='Target namespace'),
            force: bool = Field(False, description='Force apply (update existing resources)'),
        ) -> ApplyYamlResponse:
            """Apply a YAML manifest to a ROSA cluster.

            This tool applies Kubernetes/OpenShift YAML manifests to deploy or update resources.

            Args:
                ctx: MCP context
                yaml_path: Path to the YAML manifest file
                cluster_name: Name of the ROSA cluster
                namespace: Target namespace for resources
                force: Whether to update existing resources

            Returns:
                ApplyYamlResponse with operation results

            Example:
                apply_yaml(
                    yaml_path="/path/to/deployment.yaml",
                    cluster_name="my-cluster",
                    namespace="production"
                )
            """
            if not self.allow_write:
                return CallToolResult(
                    success=False,
                    content='Write access is required to apply manifests. Run with --allow-write flag.'
                )
            
            log_with_request_id(ctx, LogLevel.INFO, 'Applying YAML manifest', 
                              cluster_name=cluster_name, yaml_path=yaml_path)
            
            try:
                # Get kubeconfig
                kubeconfig_path = self._get_kubeconfig(cluster_name)
                
                # Apply using kubectl/oc
                cmd = ['kubectl', 'apply', '-f', yaml_path, '-n', namespace, '--kubeconfig', kubeconfig_path]
                if force:
                    cmd.append('--force')
                
                result = subprocess.run(cmd, capture_output=True, text=True, check=True)
                
                # Parse output to count resources
                lines = result.stdout.strip().split('\n')
                created = sum(1 for line in lines if 'created' in line)
                configured = sum(1 for line in lines if 'configured' in line)
                
                return ApplyYamlResponse(
                    force_applied=force,
                    resources_created=created,
                    resources_updated=configured,
                    success=True,
                    content=result.stdout
                )
                
            except subprocess.CalledProcessError as e:
                error_msg = f'Failed to apply YAML: {e.stderr}'
                log_with_request_id(ctx, LogLevel.ERROR, error_msg)
                return CallToolResult(success=False, content=error_msg)
            except Exception as e:
                error_msg = f'Error applying YAML: {str(e)}'
                log_with_request_id(ctx, LogLevel.ERROR, error_msg)
                return CallToolResult(success=False, content=error_msg)

        # List Kubernetes resources
        @self.mcp.tool()
        async def list_k8s_resources(
            ctx: Context,
            cluster_name: str = Field(..., description='Name of the ROSA cluster'),
            kind: str = Field(..., description='Resource kind (e.g., Pod, Service, Deployment)'),
            api_version: str = Field('v1', description='API version (e.g., v1, apps/v1)'),
            namespace: Optional[str] = Field(None, description='Namespace (None for all namespaces)'),
            label_selector: Optional[str] = Field(None, description='Label selector (e.g., app=nginx)'),
            field_selector: Optional[str] = Field(None, description='Field selector'),
        ) -> KubernetesResourceListResponse:
            """List Kubernetes/OpenShift resources in a ROSA cluster.

            This tool lists resources of a specific kind, with optional filtering.

            Args:
                ctx: MCP context
                cluster_name: Name of the ROSA cluster
                kind: Resource kind to list
                api_version: API version of the resource
                namespace: Namespace to search in (None for all)
                label_selector: Label selector for filtering
                field_selector: Field selector for filtering

            Returns:
                KubernetesResourceListResponse with resource list

            Example:
                list_k8s_resources(
                    cluster_name="my-cluster",
                    kind="Pod",
                    namespace="default",
                    label_selector="app=nginx"
                )
            """
            log_with_request_id(ctx, LogLevel.INFO, 'Listing K8s resources', 
                              cluster_name=cluster_name, kind=kind)
            
            try:
                # Determine API client type based on kind and version
                if api_version == 'apps/v1':
                    api_client = self._get_k8s_client(cluster_name, 'apps')
                elif api_version == 'batch/v1':
                    api_client = self._get_k8s_client(cluster_name, 'batch')
                elif api_version == 'networking.k8s.io/v1':
                    api_client = self._get_k8s_client(cluster_name, 'networking')
                elif api_version == 'rbac.authorization.k8s.io/v1':
                    api_client = self._get_k8s_client(cluster_name, 'rbac')
                else:
                    api_client = self._get_k8s_client(cluster_name, 'core')
                
                # Get list method based on kind
                list_methods = {
                    'Pod': 'list_pod_for_all_namespaces' if namespace is None else 'list_namespaced_pod',
                    'Service': 'list_service_for_all_namespaces' if namespace is None else 'list_namespaced_service',
                    'Deployment': 'list_deployment_for_all_namespaces' if namespace is None else 'list_namespaced_deployment',
                    'ConfigMap': 'list_config_map_for_all_namespaces' if namespace is None else 'list_namespaced_config_map',
                    'Secret': 'list_secret_for_all_namespaces' if namespace is None else 'list_namespaced_secret',
                    'Namespace': 'list_namespace',
                    'Node': 'list_node',
                }
                
                method_name = list_methods.get(kind)
                if not method_name:
                    return CallToolResult(
                        success=False,
                        content=f'Unsupported resource kind: {kind}'
                    )
                
                # Call the appropriate list method
                kwargs = {}
                if label_selector:
                    kwargs['label_selector'] = label_selector
                if field_selector:
                    kwargs['field_selector'] = field_selector
                if namespace and 'namespaced' in method_name:
                    kwargs['namespace'] = namespace
                
                list_method = getattr(api_client, method_name)
                result = list_method(**kwargs)
                
                # Convert to ResourceSummary objects
                items = []
                for item in result.items:
                    summary = ResourceSummary(
                        name=item.metadata.name,
                        namespace=getattr(item.metadata, 'namespace', None),
                        creation_timestamp=item.metadata.creation_timestamp.isoformat() if item.metadata.creation_timestamp else None,
                        labels=item.metadata.labels or {},
                        annotations=item.metadata.annotations or {}
                    )
                    items.append(summary)
                
                return KubernetesResourceListResponse(
                    kind=kind,
                    api_version=api_version,
                    namespace=namespace,
                    count=len(items),
                    items=items,
                    success=True,
                    content=f'Found {len(items)} {kind} resources'
                )
                
            except ApiException as e:
                error_msg = f'Kubernetes API error: {e.reason}'
                log_with_request_id(ctx, LogLevel.ERROR, error_msg)
                return KubernetesResourceListResponse(
                    kind=kind,
                    api_version=api_version,
                    namespace=namespace,
                    count=0,
                    items=[],
                    success=False,
                    content=error_msg
                )
            except Exception as e:
                error_msg = f'Error listing resources: {str(e)}'
                log_with_request_id(ctx, LogLevel.ERROR, error_msg)
                return KubernetesResourceListResponse(
                    kind=kind,
                    api_version=api_version,
                    namespace=namespace,
                    count=0,
                    items=[],
                    success=False,
                    content=error_msg
                )

        # Get pod logs
        @self.mcp.tool()
        async def get_pod_logs(
            ctx: Context,
            cluster_name: str = Field(..., description='Name of the ROSA cluster'),
            namespace: str = Field(..., description='Namespace of the pod'),
            pod_name: str = Field(..., description='Name of the pod'),
            container: Optional[str] = Field(None, description='Container name (for multi-container pods)'),
            tail_lines: int = Field(100, description='Number of lines to return from the end'),
            previous: bool = Field(False, description='Get logs from previous container instance'),
        ) -> PodLogResponse:
            """Get logs from a pod in a ROSA cluster.

            This tool retrieves logs from a specific pod, useful for debugging applications.

            Args:
                ctx: MCP context
                cluster_name: Name of the ROSA cluster
                namespace: Namespace of the pod
                pod_name: Name of the pod
                container: Container name (optional for single-container pods)
                tail_lines: Number of recent lines to return
                previous: Whether to get logs from previous container instance

            Returns:
                PodLogResponse with log content

            Example:
                get_pod_logs(
                    cluster_name="my-cluster",
                    namespace="default",
                    pod_name="nginx-deployment-abc123",
                    tail_lines=50
                )
            """
            if not self.allow_sensitive_data_access:
                return CallToolResult(
                    success=False,
                    content='Sensitive data access is required to read pod logs. Run with --allow-sensitive-data-access flag.'
                )
            
            log_with_request_id(ctx, LogLevel.INFO, 'Getting pod logs', 
                              cluster_name=cluster_name, pod_name=pod_name)
            
            try:
                api_client = self._get_k8s_client(cluster_name, 'core')
                
                # Get pod logs
                logs = api_client.read_namespaced_pod_log(
                    name=pod_name,
                    namespace=namespace,
                    container=container,
                    tail_lines=tail_lines,
                    previous=previous
                )
                
                lines = logs.split('\n')
                
                return PodLogResponse(
                    cluster_name=cluster_name,
                    namespace=namespace,
                    pod_name=pod_name,
                    container=container,
                    logs=logs,
                    lines_returned=len(lines),
                    success=True,
                    content=f'Retrieved {len(lines)} log lines'
                )
                
            except ApiException as e:
                error_msg = f'Failed to get pod logs: {e.reason}'
                log_with_request_id(ctx, LogLevel.ERROR, error_msg)
                return CallToolResult(success=False, content=error_msg)
            except Exception as e:
                error_msg = f'Error getting pod logs: {str(e)}'
                log_with_request_id(ctx, LogLevel.ERROR, error_msg)
                return CallToolResult(success=False, content=error_msg)

        # Get events
        @self.mcp.tool()
        async def get_k8s_events(
            ctx: Context,
            cluster_name: str = Field(..., description='Name of the ROSA cluster'),
            kind: str = Field(..., description='Resource kind'),
            name: str = Field(..., description='Resource name'),
            namespace: Optional[str] = Field(None, description='Namespace (for namespaced resources)'),
        ) -> EventsResponse:
            """Get events for a Kubernetes/OpenShift resource.

            This tool retrieves events related to a specific resource, helpful for
            troubleshooting issues.

            Args:
                ctx: MCP context
                cluster_name: Name of the ROSA cluster
                kind: Kind of the resource
                name: Name of the resource
                namespace: Namespace of the resource

            Returns:
                EventsResponse with related events

            Example:
                get_k8s_events(
                    cluster_name="my-cluster",
                    kind="Pod",
                    name="nginx-deployment-abc123",
                    namespace="default"
                )
            """
            if not self.allow_sensitive_data_access:
                return CallToolResult(
                    success=False,
                    content='Sensitive data access is required to read events. Run with --allow-sensitive-data-access flag.'
                )
            
            log_with_request_id(ctx, LogLevel.INFO, 'Getting K8s events', 
                              cluster_name=cluster_name, kind=kind, name=name)
            
            try:
                api_client = self._get_k8s_client(cluster_name, 'core')
                
                # Build field selector
                field_selectors = [f'involvedObject.name={name}', f'involvedObject.kind={kind}']
                if namespace:
                    field_selectors.append(f'involvedObject.namespace={namespace}')
                field_selector = ','.join(field_selectors)
                
                # Get events
                if namespace:
                    events = api_client.list_namespaced_event(
                        namespace=namespace,
                        field_selector=field_selector
                    )
                else:
                    events = api_client.list_event_for_all_namespaces(
                        field_selector=field_selector
                    )
                
                # Convert to EventItem objects
                event_items = []
                for event in events.items:
                    item = EventItem(
                        first_timestamp=event.first_timestamp.isoformat() if event.first_timestamp else None,
                        last_timestamp=event.last_timestamp.isoformat() if event.last_timestamp else None,
                        count=event.count,
                        message=event.message,
                        reason=event.reason,
                        reporting_component=event.reporting_component,
                        type=event.type
                    )
                    event_items.append(item)
                
                return EventsResponse(
                    cluster_name=cluster_name,
                    kind=kind,
                    name=name,
                    namespace=namespace,
                    count=len(event_items),
                    events=event_items,
                    success=True,
                    content=f'Found {len(event_items)} events'
                )
                
            except ApiException as e:
                error_msg = f'Failed to get events: {e.reason}'
                log_with_request_id(ctx, LogLevel.ERROR, error_msg)
                return EventsResponse(
                    cluster_name=cluster_name,
                    kind=kind,
                    name=name,
                    namespace=namespace,
                    count=0,
                    events=[],
                    success=False,
                    content=error_msg
                )
            except Exception as e:
                error_msg = f'Error getting events: {str(e)}'
                log_with_request_id(ctx, LogLevel.ERROR, error_msg)
                return EventsResponse(
                    cluster_name=cluster_name,
                    kind=kind,
                    name=name,
                    namespace=namespace,
                    count=0,
                    events=[],
                    success=False,
                    content=error_msg
                )

        # Manage resource (create, update, delete)
        @self.mcp.tool()
        async def manage_k8s_resource(
            ctx: Context,
            cluster_name: str = Field(..., description='Name of the ROSA cluster'),
            operation: Operation = Field(..., description='Operation to perform'),
            kind: str = Field(..., description='Resource kind'),
            api_version: str = Field('v1', description='API version'),
            name: str = Field(..., description='Resource name'),
            namespace: Optional[str] = Field(None, description='Namespace (for namespaced resources)'),
            manifest: Optional[Dict[str, Any]] = Field(None, description='Resource manifest (for create/update)'),
        ) -> KubernetesResourceResponse:
            """Manage a Kubernetes/OpenShift resource (create, update, delete, read).

            This tool performs CRUD operations on individual resources.

            Args:
                ctx: MCP context
                cluster_name: Name of the ROSA cluster
                operation: Operation to perform (create, replace, patch, delete, read)
                kind: Resource kind
                api_version: API version
                name: Resource name
                namespace: Namespace (for namespaced resources)
                manifest: Resource manifest (for create/update operations)

            Returns:
                KubernetesResourceResponse with operation result

            Example:
                # Create a namespace
                manage_k8s_resource(
                    cluster_name="my-cluster",
                    operation="create",
                    kind="Namespace",
                    name="my-namespace",
                    manifest={"metadata": {"name": "my-namespace"}}
                )
            """
            if operation != Operation.READ and not self.allow_write:
                return CallToolResult(
                    success=False,
                    content='Write access is required for this operation. Run with --allow-write flag.'
                )
            
            log_with_request_id(ctx, LogLevel.INFO, f'Managing K8s resource: {operation.value}', 
                              cluster_name=cluster_name, kind=kind, name=name)
            
            try:
                # For simplicity, use kubectl for these operations
                kubeconfig_path = self._get_kubeconfig(cluster_name)
                
                if operation == Operation.CREATE:
                    if not manifest:
                        return CallToolResult(success=False, content='Manifest required for create operation')
                    
                    # Write manifest to temp file
                    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
                        yaml.dump(manifest, f)
                        temp_path = f.name
                    
                    try:
                        cmd = ['kubectl', 'create', '-f', temp_path, '--kubeconfig', kubeconfig_path]
                        if namespace:
                            cmd.extend(['-n', namespace])
                        
                        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
                        
                        return KubernetesResourceResponse(
                            kind=kind,
                            name=name,
                            namespace=namespace,
                            api_version=api_version,
                            operation='create',
                            success=True,
                            content=f'Successfully created {kind} {name}'
                        )
                    finally:
                        os.unlink(temp_path)
                
                elif operation == Operation.DELETE:
                    cmd = ['kubectl', 'delete', kind, name, '--kubeconfig', kubeconfig_path]
                    if namespace:
                        cmd.extend(['-n', namespace])
                    
                    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
                    
                    return KubernetesResourceResponse(
                        kind=kind,
                        name=name,
                        namespace=namespace,
                        api_version=api_version,
                        operation='delete',
                        success=True,
                        content=f'Successfully deleted {kind} {name}'
                    )
                
                elif operation == Operation.READ:
                    cmd = ['kubectl', 'get', kind, name, '-o', 'json', '--kubeconfig', kubeconfig_path]
                    if namespace:
                        cmd.extend(['-n', namespace])
                    
                    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
                    resource_data = yaml.safe_load(result.stdout)
                    
                    return KubernetesResourceResponse(
                        kind=kind,
                        name=name,
                        namespace=namespace,
                        api_version=api_version,
                        operation='read',
                        resource=resource_data,
                        success=True,
                        content=f'Successfully retrieved {kind} {name}'
                    )
                
                else:
                    return CallToolResult(
                        success=False,
                        content=f'Operation {operation.value} not implemented yet'
                    )
                    
            except subprocess.CalledProcessError as e:
                error_msg = f'Failed to {operation.value} resource: {e.stderr}'
                log_with_request_id(ctx, LogLevel.ERROR, error_msg)
                return CallToolResult(success=False, content=error_msg)
            except Exception as e:
                error_msg = f'Error managing resource: {str(e)}'
                log_with_request_id(ctx, LogLevel.ERROR, error_msg)
                return CallToolResult(success=False, content=error_msg)

        # List API versions
        @self.mcp.tool()
        async def list_api_versions(
            ctx: Context,
            cluster_name: str = Field(..., description='Name of the ROSA cluster'),
        ) -> CallToolResult:
            """List available API versions in a ROSA cluster.

            This tool lists all API versions available in the cluster, including
            OpenShift-specific APIs.

            Args:
                ctx: MCP context
                cluster_name: Name of the ROSA cluster

            Returns:
                CallToolResult with API version list

            Example:
                list_api_versions(cluster_name="my-cluster")
            """
            log_with_request_id(ctx, LogLevel.INFO, 'Listing API versions', 
                              cluster_name=cluster_name)
            
            try:
                kubeconfig_path = self._get_kubeconfig(cluster_name)
                
                cmd = ['kubectl', 'api-versions', '--kubeconfig', kubeconfig_path]
                result = subprocess.run(cmd, capture_output=True, text=True, check=True)
                
                api_versions = result.stdout.strip().split('\n')
                
                # Organize by group
                organized = {}
                for version in api_versions:
                    if '/' in version:
                        group, ver = version.split('/', 1)
                        if group not in organized:
                            organized[group] = []
                        organized[group].append(ver)
                    else:
                        if 'core' not in organized:
                            organized['core'] = []
                        organized['core'].append(version)
                
                return CallToolResult(
                    success=True,
                    content=yaml.dump(organized, default_flow_style=False)
                )
                
            except subprocess.CalledProcessError as e:
                error_msg = f'Failed to list API versions: {e.stderr}'
                log_with_request_id(ctx, LogLevel.ERROR, error_msg)
                return CallToolResult(success=False, content=error_msg)
            except Exception as e:
                error_msg = f'Error listing API versions: {str(e)}'
                log_with_request_id(ctx, LogLevel.ERROR, error_msg)
                return CallToolResult(success=False, content=error_msg)