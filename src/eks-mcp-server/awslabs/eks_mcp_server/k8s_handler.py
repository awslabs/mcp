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

"""Kubernetes handler for the EKS MCP Server."""

import os
import yaml
from awslabs.eks_mcp_server.k8s_apis import K8sApis
from awslabs.eks_mcp_server.k8s_client_cache import K8sClientCache
from awslabs.eks_mcp_server.logging_helper import LogLevel, log_with_request_id
from awslabs.eks_mcp_server.models import (
    ApiVersionsResponse,
    ApplyYamlResponse,
    EventItem,
    EventsResponse,
    GenerateAppManifestResponse,
    KubernetesResourceListResponse,
    KubernetesResourceResponse,
    Operation,
    PodLogsResponse,
    ResourceSummary,
)
from mcp.server.fastmcp import Context
from mcp.types import TextContent
from pydantic import Field
from typing import Any, Dict, Optional


class K8sHandler:
    """Handler for Kubernetes operations in the EKS MCP Server.

    This class provides tools for interacting with Kubernetes clusters, including
    applying YAML manifests.
    """

    def __init__(
        self,
        mcp,
        allow_write: bool = False,
        allow_sensitive_data_access: bool = False,
    ):
        """Initialize the Kubernetes handler.

        Args:
            mcp: The MCP server instance
            allow_write: Whether to enable write access (default: False)
            allow_sensitive_data_access: Whether to allow access to sensitive data (default: False)
        """
        self.mcp = mcp
        self.client_cache = K8sClientCache()
        self.allow_write = allow_write
        self.allow_sensitive_data_access = allow_sensitive_data_access

        # Register tools
        self.mcp.tool(name='list_k8s_resources')(self.list_k8s_resources)
        self.mcp.tool(name='get_pod_logs')(self.get_pod_logs)
        self.mcp.tool(name='get_k8s_events')(self.get_k8s_events)
        self.mcp.tool(name='list_api_versions')(self.list_api_versions)
        self.mcp.tool(name='manage_k8s_resource')(self.manage_k8s_resource)
        self.mcp.tool(name='apply_yaml')(self.apply_yaml)
        self.mcp.tool(name='generate_app_manifest')(self.generate_app_manifest)

    def get_client(self, cluster_name: str) -> K8sApis:
        """Get a Kubernetes client for the specified cluster.

        Args:
            cluster_name: Name of the EKS cluster

        Returns:
            K8sApis instance

        Raises:
            ValueError: If the cluster credentials are invalid
            Exception: If there's an error getting the cluster credentials
        """
        return self.client_cache.get_client(cluster_name)

    async def apply_yaml(
        self,
        ctx: Context,
        yaml_path: str = Field(
            ...,
            description="""Absolute path to the YAML file to apply.
            IMPORTANT: Must be an absolute path (e.g., '/home/user/manifests/app.yaml') as the MCP client and server might not run from the same location.""",
        ),
        cluster_name: str = Field(
            ...,
            description='Name of the EKS cluster where the resources will be created or updated.',
        ),
        namespace: str = Field(
            ...,
            description='Kubernetes namespace to apply resources to. Will be used for namespaced resources that do not specify a namespace.',
        ),
        force: bool = Field(
            True,
            description='Whether to update resources if they already exist (similar to kubectl apply). Set to false to only create new resources.',
        ),
    ) -> ApplyYamlResponse:
        """Apply a Kubernetes YAML from a local file.

        This tool applies Kubernetes resources defined in a YAML file to an EKS cluster,
        similar to the `kubectl apply` command. It supports multi-document YAML files
        and can create or update resources, useful for deploying applications, creating
        Kubernetes resources, and applying complete application stacks.

        ## Requirements
        - The server must be run with the `--allow-write` flag
        - The YAML file must exist and be accessible to the server
        - The path must be absolute (e.g., '/home/user/manifests/app.yaml')
        - The EKS cluster must exist and be accessible

        ## Response Information
        The response includes the number of resources created, number of resources
        updated (when force=True), and whether force was applied.

        Args:
            ctx: MCP context
            yaml_path: Absolute path to the YAML file to apply
            cluster_name: Name of the EKS cluster
            namespace: Default namespace to use for resources
            force: Whether to update resources if they already exist (like kubectl apply)

        Returns:
            ApplyYamlResponse with operation result
        """
        try:
            # Validate that the path is absolute
            if not os.path.isabs(yaml_path):
                error_msg = f'Path must be absolute: {yaml_path}'
                log_with_request_id(ctx, LogLevel.ERROR, error_msg)
                return ApplyYamlResponse(
                    isError=True,
                    content=[TextContent(type='text', text=error_msg)],
                    force_applied=force,
                    resources_created=0,
                    resources_updated=0,
                )

            # Get Kubernetes client for the cluster
            k8s_client = self.get_client(cluster_name)

            # Read the YAML content from the local file
            log_with_request_id(ctx, LogLevel.INFO, f'Reading YAML content from file: {yaml_path}')

            try:
                with open(yaml_path, 'r') as yaml_file:
                    yaml_content = yaml_file.read()
            except FileNotFoundError:
                error_msg = f'YAML file not found: {yaml_path}'
                log_with_request_id(ctx, LogLevel.ERROR, error_msg)
                return ApplyYamlResponse(
                    isError=True,
                    content=[TextContent(type='text', text=error_msg)],
                    force_applied=force,
                    resources_created=0,
                    resources_updated=0,
                )
            except IOError as e:
                error_msg = f'Error reading YAML file {yaml_path}: {str(e)}'
                log_with_request_id(ctx, LogLevel.ERROR, error_msg)
                return ApplyYamlResponse(
                    isError=True,
                    content=[TextContent(type='text', text=error_msg)],
                    force_applied=force,
                    resources_created=0,
                    resources_updated=0,
                )

            # Parse YAML documents
            yaml_objects = list(yaml.safe_load_all(yaml_content))
            yaml_objects = [doc for doc in yaml_objects if doc]  # Filter out None/empty documents

            log_with_request_id(
                ctx, LogLevel.INFO, f'Found {len(yaml_objects)} resources in the manifest'
            )

            # Apply all resources using our custom implementation
            try:
                # Apply the YAML objects
                results, created_count, updated_count = k8s_client.apply_from_yaml(
                    yaml_objects=yaml_objects,
                    namespace=namespace,
                    force=force,
                )

                # If we get here, all resources were applied successfully
                success_msg = (
                    f'Successfully applied all resources from YAML file {yaml_path} '
                    f'({created_count} created, {updated_count} updated)'
                )
                log_with_request_id(ctx, LogLevel.INFO, success_msg)

                return ApplyYamlResponse(
                    isError=False,
                    content=[TextContent(type='text', text=success_msg)],
                    force_applied=force,
                    resources_created=created_count,
                    resources_updated=updated_count,
                )

            except Exception as e:
                # Any exception means the operation failed
                error_msg = f'Failed to apply YAML from file {yaml_path}: {str(e)}'
                log_with_request_id(ctx, LogLevel.ERROR, error_msg)

                return ApplyYamlResponse(
                    isError=True,
                    content=[TextContent(type='text', text=error_msg)],
                    force_applied=force,
                    resources_created=0,
                    resources_updated=0,
                )

        except Exception as e:
            error_msg = f'Error applying YAML from file: {str(e)}'
            log_with_request_id(ctx, LogLevel.ERROR, error_msg)

            return ApplyYamlResponse(
                isError=True,
                content=[TextContent(type='text', text=error_msg)],
                force_applied=force,
                resources_created=0,
                resources_updated=0,
            )

    def filter_null_values(self, data: Any) -> Any:
        """Recursively filter out null values from dictionaries and lists.

        Args:
            data: The data structure to filter (dict, list, or primitive)

        Returns:
            The filtered data structure with null values removed
        """
        if isinstance(data, dict):
            return {k: self.filter_null_values(v) for k, v in data.items() if v is not None}
        elif isinstance(data, list):
            return [self.filter_null_values(item) for item in data if item is not None]
        else:
            return data

    def remove_managed_fields(self, resource: Dict[str, Any]) -> Dict[str, Any]:
        """Remove metadata.managed_fields from a Kubernetes resource.

        Args:
            resource: The Kubernetes resource dictionary

        Returns:
            The resource with metadata.managed_fields removed
        """
        if (
            isinstance(resource, dict)
            and 'metadata' in resource
            and isinstance(resource['metadata'], dict)
        ):
            # Dynamic client uses camelCase
            if 'managedFields' in resource['metadata']:
                resource['metadata'].pop('managedFields')
        return resource

    def cleanup_resource_response(self, resource: Any) -> Any:
        """Clean up a Kubernetes resource response by removing managed fields and null values.

        This method:
        1. Removes metadata.managed_fields which is typically large and not useful
        2. Recursively removes null values to reduce response size

        Args:
            resource: The Kubernetes resource to clean up

        Returns:
            The cleaned up resource
        """
        # First remove managed fields
        resource = self.remove_managed_fields(resource)

        # Then filter out null values
        return self.filter_null_values(resource)

    async def manage_k8s_resource(
        self,
        ctx: Context,
        operation: str = Field(
            ...,
            description="""Operation to perform on the resource. Valid values:
            - create: Create a new resource
            - replace: Replace an existing resource
            - patch: Update specific fields of an existing resource
            - delete: Delete an existing resource
            - read: Get details of an existing resource
            Use list_k8s_resources for listing multiple resources.""",
        ),
        cluster_name: str = Field(
            ...,
            description='Name of the EKS cluster where the resource is located or will be created.',
        ),
        kind: str = Field(
            ...,
            description='Kind of the Kubernetes resource (e.g., "Pod", "Service", "Deployment").',
        ),
        api_version: str = Field(
            ...,
            description='API version of the Kubernetes resource (e.g., "v1", "apps/v1", "networking.k8s.io/v1").',
        ),
        name: Optional[str] = Field(
            None,
            description='Name of the Kubernetes resource. Required for all operations except create (where it can be specified in the body).',
        ),
        namespace: Optional[str] = Field(
            None,
            description="""Namespace of the Kubernetes resource. Required for namespaced resources.
            Not required for cluster-scoped resources (like Nodes, PersistentVolumes).""",
        ),
        body: Optional[Dict[str, Any]] = Field(
            None,
            description="""Resource definition as a dictionary. Required for create, replace, and patch operations.
            For create and replace, this should be a complete resource definition.
            For patch, this should contain only the fields to update.""",
        ),
    ) -> KubernetesResourceResponse:
        """Manage a single Kubernetes resource with various operations.

        This tool provides complete CRUD (Create, Read, Update, Delete) operations
        for Kubernetes resources in an EKS cluster. It supports all resource types
        and allows for precise control over individual resources, enabling you to create
        custom resources, update specific fields, read detailed information, and delete
        resources that are no longer needed.

        ## Requirements
        - The server must be run with the `--allow-write` flag for mutating operations
        - The server must be run with the `--allow-sensitive-data-access` flag for Secret resources
        - The EKS cluster must exist and be accessible

        ## Operations
        - **create**: Create a new resource with the provided definition
        - **replace**: Replace an existing resource with a new definition
        - **patch**: Update specific fields of an existing resource
        - **delete**: Remove an existing resource
        - **read**: Get details of an existing resource

        ## Usage Tips
        - Use list_api_versions to find available API versions
        - For namespaced resources, always provide the namespace
        - When creating resources, ensure the name in the body matches the name parameter
        - For patch operations, only include the fields you want to update

        Args:
            ctx: MCP context
            operation: Operation to perform (create, replace, patch, delete, read)
            cluster_name: Name of the EKS cluster
            kind: Kind of the Kubernetes resource (e.g., 'Pod', 'Service')
            api_version: API version of the Kubernetes resource (e.g., 'v1', 'apps/v1')
            name: Name of the Kubernetes resource
            namespace: Namespace of the Kubernetes resource (optional)
            body: Resource definition

        Returns:
            KubernetesResourceResponse with operation result
        """
        try:
            # Convert string operation to enum
            try:
                operation_enum = Operation(operation)
            except ValueError:
                valid_ops = ', '.join([op.value for op in Operation])
                error_msg = f'Invalid operation: {operation}. Valid operations are: {valid_ops}'
                log_with_request_id(ctx, LogLevel.ERROR, error_msg)
                return KubernetesResourceResponse(
                    isError=True,
                    content=[TextContent(type='text', text=error_msg)],
                    kind=kind,
                    name=name or '',
                    namespace=namespace,
                    api_version=api_version,
                    operation=operation,
                    resource=None,
                )

            # Check if write access is disabled and trying to perform a mutating operation
            if not self.allow_write and operation_enum not in [Operation.READ]:
                error_msg = f'Operation {operation} is not allowed without write access'
                log_with_request_id(ctx, LogLevel.ERROR, error_msg)
                return KubernetesResourceResponse(
                    isError=True,
                    content=[TextContent(type='text', text=error_msg)],
                    kind=kind,
                    name=name or '',
                    namespace=namespace,
                    api_version=api_version,
                    operation=operation,
                    resource=None,
                )

            # Check if sensitive data access is disabled and trying to read Secret resources
            if (
                not self.allow_sensitive_data_access
                and kind.lower() == 'secret'
                and operation_enum in [Operation.READ]
            ):
                error_msg = (
                    'Access to Kubernetes Secrets requires --allow-sensitive-data-access flag'
                )
                log_with_request_id(ctx, LogLevel.ERROR, error_msg)
                return KubernetesResourceResponse(
                    isError=True,
                    content=[TextContent(type='text', text=error_msg)],
                    kind=kind,
                    name=name or '',
                    namespace=namespace,
                    api_version=api_version,
                    operation=operation,
                    resource=None,
                )

            # Get Kubernetes client for the cluster
            k8s_client = self.get_client(cluster_name)

            # Call the manage_resource method
            response = k8s_client.manage_resource(
                operation_enum,
                kind,
                api_version,
                name=name,
                namespace=namespace,
                body=body,
            )

            # Format resource name for logging
            resource_name = f'{namespace + "/" if namespace else ""}{name}'

            # Log success
            operation_past_tense = {
                Operation.CREATE.value: 'created',
                Operation.REPLACE.value: 'replaced',
                Operation.PATCH.value: 'patched',
                Operation.DELETE.value: 'deleted',
                Operation.READ.value: 'retrieved',
            }[operation_enum.value]

            log_with_request_id(
                ctx, LogLevel.INFO, f'{operation_past_tense.capitalize()} {kind} {resource_name}'
            )

            # For read operation, convert response to dict and clean up the response
            resource_data = None
            if operation_enum == Operation.READ:
                resource_data = self.cleanup_resource_response(response.to_dict())
                log_with_request_id(
                    ctx,
                    LogLevel.INFO,
                    f'Cleaned up resource response for {kind} {resource_name}',
                )

            # Return success response
            return KubernetesResourceResponse(
                isError=False,
                content=[
                    TextContent(
                        type='text',
                        text=f'Successfully {operation_past_tense} {kind} {resource_name}',
                    )
                ],
                kind=kind,
                name=name or '',
                namespace=namespace,
                api_version=api_version,
                operation=operation,
                resource=resource_data,
            )

        except Exception as e:
            # Log error
            resource_name = f'{namespace + "/" if namespace else ""}{name or ""}'
            error_msg = f'Failed to {operation} {kind} {resource_name}: {str(e)}'
            log_with_request_id(ctx, LogLevel.ERROR, error_msg)

            # Return error response
            return KubernetesResourceResponse(
                isError=True,
                content=[TextContent(type='text', text=error_msg)],
                kind=kind,
                name=name or '',
                namespace=namespace,
                api_version=api_version,
                operation=operation,
                resource=None,
            )

    async def list_k8s_resources(
        self,
        ctx: Context,
        cluster_name: str = Field(
            ..., description='Name of the EKS cluster where the resources are located.'
        ),
        kind: str = Field(
            ...,
            description="""Kind of the Kubernetes resources to list (e.g., 'Pod', 'Service', 'Deployment').
            Use the list_api_versions tool to find available resource kinds.""",
        ),
        api_version: str = Field(
            ...,
            description="""API version of the Kubernetes resources (e.g., 'v1', 'apps/v1', 'networking.k8s.io/v1').
            Use the list_api_versions tool to find available API versions.""",
        ),
        namespace: Optional[str] = Field(
            None,
            description="""Namespace of the Kubernetes resources to list.
            If not provided, resources will be listed across all namespaces (for namespaced resources).""",
        ),
        label_selector: Optional[str] = Field(
            None,
            description="""Label selector to filter resources (e.g., 'app=nginx,tier=frontend').
            Uses the same syntax as kubectl's --selector flag.""",
        ),
        field_selector: Optional[str] = Field(
            None,
            description="""Field selector to filter resources (e.g., 'metadata.name=my-pod,status.phase=Running').
            Uses the same syntax as kubectl's --field-selector flag.""",
        ),
    ) -> KubernetesResourceListResponse:
        """List Kubernetes resources of a specific kind.

        This tool lists Kubernetes resources of a specified kind in an EKS cluster,
        with options to filter by namespace, labels, and fields. It returns a summary
        of each resource including name, namespace, creation time, and metadata, useful
        for listing pods in a namespace, finding services with specific labels, or
        checking resources in a specific state.

        ## Response Information
        The response includes a summary of each resource with name, namespace, creation timestamp,
        labels, and annotations.

        ## Usage Tips
        - Use the list_api_versions tool first to find available API versions
        - For non-namespaced resources (like Nodes), the namespace parameter is ignored
        - Combine label and field selectors for more precise filtering
        - Results are summarized to avoid overwhelming responses

        Args:
            ctx: MCP context
            cluster_name: Name of the EKS cluster
            kind: Kind of the Kubernetes resources (e.g., 'Pod', 'Service')
            api_version: API version of the Kubernetes resources (e.g., 'v1', 'apps/v1')
            namespace: Namespace of the Kubernetes resources (optional)
            label_selector: Label selector to filter resources (optional)
            field_selector: Field selector to filter resources (optional)

        Returns:
            KubernetesResourceListResponse with operation result
        """
        try:
            # Get Kubernetes client for the cluster
            k8s_client = self.get_client(cluster_name)

            # List resources
            response = k8s_client.list_resources(
                kind,
                api_version,
                namespace=namespace,
                label_selector=label_selector,
                field_selector=field_selector,
            )

            # Extract summaries from items and clean up the responses
            summaries = []
            for item in response.items:
                item_dict = self.cleanup_resource_response(item.to_dict())
                metadata = item_dict.get('metadata', {})

                # Dynamic client uses camelCase field names
                creation_timestamp = metadata.get('creationTimestamp')
                if creation_timestamp is not None:
                    creation_timestamp = str(creation_timestamp)

                summary = ResourceSummary(
                    name=metadata.get('name', ''),
                    namespace=metadata.get('namespace'),
                    creation_timestamp=creation_timestamp,
                    labels=metadata.get('labels'),
                    annotations=metadata.get('annotations'),
                )
                summaries.append(summary)

            log_with_request_id(
                ctx, LogLevel.INFO, f'Cleaned up resource responses for {kind} resources'
            )

            # Log success
            resource_location = f'in {namespace + "/" if namespace else ""}all namespaces'
            log_with_request_id(
                ctx, LogLevel.INFO, f'Listed {len(summaries)} {kind} resources {resource_location}'
            )

            # Return success response
            return KubernetesResourceListResponse(
                isError=False,
                content=[
                    TextContent(
                        type='text',
                        text=f'Successfully listed {len(summaries)} {kind} resources {resource_location}',
                    )
                ],
                kind=kind,
                api_version=api_version,
                namespace=namespace,
                count=len(summaries),
                items=summaries,
            )

        except Exception as e:
            # Log error
            error_msg = f'Failed to list {kind} resources: {str(e)}'
            log_with_request_id(ctx, LogLevel.ERROR, error_msg)

            # Return error response
            return KubernetesResourceListResponse(
                isError=True,
                content=[TextContent(type='text', text=error_msg)],
                kind=kind,
                api_version=api_version,
                namespace=namespace,
                count=0,
                items=[],
            )

    async def generate_app_manifest(
        self,
        ctx: Context,
        app_name: str = Field(
            ...,
            description='Name of the application. Used for deployment and service names, and for labels.',
        ),
        image_uri: str = Field(
            ...,
            description="""Full ECR image URI with tag (e.g., 123456789012.dkr.ecr.region.amazonaws.com/repo:tag).
            Must include the full repository path and tag.""",
        ),
        output_dir: str = Field(
            ..., description='Absolute path to the directory to save the manifest file'
        ),
        port: int = Field(80, description='Container port that the application listens on'),
        replicas: int = Field(2, description='Number of replicas to deploy'),
        cpu: str = Field(
            '100m',
            description='CPU request for each container (e.g., "100m" for 0.1 CPU cores, "500m" for half a core).',
        ),
        memory: str = Field(
            '128Mi',
            description='Memory request for each container (e.g., "128Mi" for 128 MiB, "1Gi" for 1 GiB).',
        ),
        namespace: str = Field(
            'default',
            description='Kubernetes namespace to deploy the application to. Default: "default"',
        ),
        load_balancer_scheme: str = Field(
            'internal',
            description='AWS load balancer scheme. Options: "internal" (private VPC only) or "internet-facing" (public access).',
        ),
    ) -> GenerateAppManifestResponse:
        """Generate Kubernetes manifest for a deployment and service.

        This tool generates Kubernetes manifests for deploying an application to an EKS cluster,
        creating both a Deployment and a LoadBalancer Service. The generated manifest can be
        applied to a cluster using the apply_yaml tool, useful for deploying containerized
        applications, creating load-balanced services, and standardizing deployment configurations.

        ## Requirements
        - The server must be run with the `--allow-write` flag

        ## Generated Resources
        - **Deployment**: Manages the application pods with specified replicas and resource requests
        - **Service**: LoadBalancer type service that exposes the application externally

        ## Usage Tips
        - Use 2 or more replicas for production workloads
        - Set appropriate resource requests based on application needs
        - Use internal load balancers for services that should only be accessible within the VPC
        - The generated manifest can be modified before applying if needed

        Args:
            ctx: MCP context
            app_name: Name of the application (used for deployment and service names)
            image_uri: Full ECR image URI with tag
            port: Container port that the application listens on
            replicas: Number of replicas to deploy
            cpu: CPU request for each container
            memory: Memory request for each container
            namespace: Kubernetes namespace to deploy to
            load_balancer_scheme: AWS load balancer scheme (internal or internet-facing)
            output_dir: Directory to save the manifest file

        Returns:
            GenerateAppManifestResponse: The complete Kubernetes manifest content and output file path
        """
        try:
            # Check if write access is disabled
            if not self.allow_write:
                error_msg = 'Operation generate_app_manifest is not allowed without write access'
                log_with_request_id(ctx, LogLevel.ERROR, error_msg)
                return GenerateAppManifestResponse(
                    isError=True,
                    content=[TextContent(type='text', text=error_msg)],
                    output_file_path='',
                )

            # Validate that the path is absolute
            if not os.path.isabs(output_dir):
                error_msg = f'Output directory path must be absolute: {output_dir}'
                log_with_request_id(ctx, LogLevel.ERROR, error_msg)
                return GenerateAppManifestResponse(
                    isError=True,
                    content=[TextContent(type='text', text=error_msg)],
                    output_file_path='',
                )

            log_with_request_id(
                ctx,
                LogLevel.INFO,
                f'Generating YAML for application {app_name} using image {image_uri}',
            )

            # List of template files to process
            template_files = ['deployment.yaml', 'service.yaml']

            # Prepare template values
            template_values = {
                'APP_NAME': app_name,
                'NAMESPACE': namespace,
                'REPLICAS': str(replicas),  # Convert to string for template substitution
                'IMAGE_URI': image_uri,
                'PORT': str(port),
                'CPU': cpu,
                'MEMORY': memory,
                'LOAD_BALANCER_SCHEME': load_balancer_scheme,
            }

            # Get the combined manifest using the template files
            combined_yaml = self._load_yaml_template(template_files, template_values)

            # Ensure output directory exists
            os.makedirs(output_dir, exist_ok=True)

            # Define output file path (using absolute path)
            output_file_path = os.path.abspath(
                os.path.join(output_dir, f'{app_name}-manifest.yaml')
            )

            # Write the manifest to the output file
            with open(output_file_path, 'w') as f:
                f.write(combined_yaml)

            success_message = (
                f'Successfully generated YAML for {app_name} application with image {image_uri} '
                f'and saved to {output_file_path}'
            )

            log_with_request_id(ctx, LogLevel.INFO, success_message)

            return GenerateAppManifestResponse(
                isError=False,
                content=[TextContent(type='text', text=success_message)],
                output_file_path=output_file_path,
            )

        except Exception as e:
            error_message = f'Failed to generate YAML: {str(e)}'
            log_with_request_id(ctx, LogLevel.ERROR, error_message)

            return GenerateAppManifestResponse(
                isError=True,
                content=[TextContent(type='text', text=error_message)],
                output_file_path='',
            )

    def _remove_checkov_skip_annotations(self, content: str) -> str:
        """Remove checkov skip annotations from YAML content.

        Args:
            content: YAML content as string

        Returns:
            YAML content with checkov skip annotations removed
        """
        # Use yaml to parse and modify the content
        yaml_content = yaml.safe_load(content)
        if (
            yaml_content
            and 'metadata' in yaml_content
            and 'annotations' in yaml_content['metadata']
        ):
            # Remove all checkov skip annotations
            annotations = yaml_content['metadata']['annotations']
            checkov_keys = [key for key in annotations.keys() if key.startswith('checkov.io/skip')]
            for key in checkov_keys:
                del annotations[key]

            # If annotations is now empty, remove it
            if not annotations:
                del yaml_content['metadata']['annotations']

            # Convert back to YAML string
            content = yaml.dump(yaml_content, default_flow_style=False)

        return content

    def _load_yaml_template(self, template_files: list, values: Dict[str, Any]) -> str:
        """Load and process Kubernetes template files.

        Args:
            template_files: List of template filenames to process
            values: Dictionary of values to substitute into the templates

        Returns:
            A string containing the combined YAML content with variables substituted
        """
        templates_dir = os.path.join(os.path.dirname(__file__), 'templates', 'k8s-templates')
        template_contents = []

        # Process each template file
        for template_file in template_files:
            template_path = os.path.join(templates_dir, template_file)

            with open(template_path, 'r') as f:
                content = f.read()

            # Replace variables in the template
            for key, value in values.items():
                content = content.replace(key, value)

            # Remove checkov skip annotations if present
            if template_file == 'deployment.yaml':
                content = self._remove_checkov_skip_annotations(content)

            template_contents.append(content)

        # Combine templates into a single YAML document with separator
        return '\n---\n'.join(template_contents)

    async def get_pod_logs(
        self,
        ctx: Context,
        cluster_name: str = Field(
            ..., description='Name of the EKS cluster where the pod is running.'
        ),
        namespace: str = Field(..., description='Kubernetes namespace where the pod is located.'),
        pod_name: str = Field(..., description='Name of the pod to retrieve logs from.'),
        container_name: Optional[str] = Field(
            None,
            description='Name of the specific container to get logs from. Required only if the pod contains multiple containers.',
        ),
        since_seconds: Optional[int] = Field(
            None,
            description='Only return logs newer than this many seconds. Useful for getting recent logs without retrieving the entire history.',
        ),
        tail_lines: int = Field(
            100,
            description='Number of lines to return from the end of the logs. Default: 100. Use higher values for more context.',
        ),
        limit_bytes: int = Field(
            10240,
            description='Maximum number of bytes to return. Default: 10KB (10240 bytes). Prevents retrieving extremely large log files.',
        ),
    ) -> PodLogsResponse:
        """Get logs from a pod in a Kubernetes cluster.

        This tool retrieves logs from a specified pod in an EKS cluster, with options
        to filter by container, time range, and size. It's useful for debugging application
        issues, monitoring behavior, investigating crashes, and verifying startup configuration.

        ## Requirements
        - The server must be run with the `--allow-sensitive-data-access` flag
        - The pod must exist and be accessible in the specified namespace
        - The EKS cluster must exist and be accessible

        ## Response Information
        The response includes pod name, namespace, container name (if specified),
        and log lines as an array of strings.

        Args:
            ctx: MCP context
            cluster_name: Name of the EKS cluster
            namespace: Namespace of the pod
            pod_name: Name of the pod
            container_name: Container name (optional, if pod contains more than one container)
            since_seconds: Only return logs newer than this many seconds (optional)
            tail_lines: Number of lines to return from the end of the logs (defaults to 100)
            limit_bytes: Maximum number of bytes to return (defaults to 10KB)

        Returns:
            PodLogsResponse with pod logs
        """
        # Check if sensitive data access is disabled
        if not self.allow_sensitive_data_access:
            error_msg = 'Access to pod logs requires --allow-sensitive-data-access flag'
            log_with_request_id(ctx, LogLevel.ERROR, error_msg)
            return PodLogsResponse(
                isError=True,
                content=[TextContent(type='text', text=error_msg)],
                pod_name=pod_name,
                namespace=namespace,
                container_name=container_name,
                log_lines=[],
            )

        try:
            # Get Kubernetes client for the cluster
            k8s_client = self.get_client(cluster_name)

            # Get pod logs
            logs = k8s_client.get_pod_logs(
                pod_name=pod_name,
                namespace=namespace,
                container_name=container_name,
                since_seconds=since_seconds,
                tail_lines=tail_lines,
                limit_bytes=limit_bytes,
            )

            # Split logs into lines
            log_lines = logs.splitlines(keepends=False)

            # Add an empty string at the end if the logs end with a newline
            if logs.endswith('\n'):
                log_lines.append('')

            # Format container info for logging
            container_info = f' (container: {container_name})' if container_name else ''

            # Log success
            log_with_request_id(
                ctx,
                LogLevel.INFO,
                f'Retrieved {len(log_lines)} log lines from pod {namespace}/{pod_name}{container_info}',
            )

            # Return success response
            return PodLogsResponse(
                isError=False,
                content=[
                    TextContent(
                        type='text',
                        text=f'Successfully retrieved {len(log_lines)} log lines from pod {namespace}/{pod_name}{container_info}',
                    )
                ],
                pod_name=pod_name,
                namespace=namespace,
                container_name=container_name,
                log_lines=log_lines,
            )

        except Exception as e:
            # Format container info for error message
            container_info = f' (container: {container_name})' if container_name else ''

            # Log error
            error_msg = (
                f'Failed to get logs from pod {namespace}/{pod_name}{container_info}: {str(e)}'
            )
            log_with_request_id(ctx, LogLevel.ERROR, error_msg)

            # Return error response
            return PodLogsResponse(
                isError=True,
                content=[TextContent(type='text', text=error_msg)],
                pod_name=pod_name,
                namespace=namespace,
                container_name=container_name,
                log_lines=[],
            )

    async def get_k8s_events(
        self,
        ctx: Context,
        cluster_name: str = Field(
            ..., description='Name of the EKS cluster where the resource is located.'
        ),
        kind: str = Field(
            ...,
            description='Kind of the involved object (e.g., "Pod", "Deployment", "Service"). Must match the resource kind exactly.',
        ),
        name: str = Field(..., description='Name of the involved object to get events for.'),
        namespace: Optional[str] = Field(
            None,
            description="""Namespace of the involved object. Required for namespaced resources (like Pods, Deployments).
            Not required for cluster-scoped resources (like Nodes, PersistentVolumes).""",
        ),
    ) -> EventsResponse:
        """Get events related to a specific Kubernetes resource.

        This tool retrieves Kubernetes events related to a specific resource, providing
        detailed information about what has happened to the resource over time. Events
        are useful for troubleshooting pod startup failures, investigating deployment issues,
        understanding resource modifications, and diagnosing scheduling problems.

        ## Requirements
        - The server must be run with the `--allow-sensitive-data-access` flag
        - The resource must exist and be accessible in the specified namespace

        ## Response Information
        The response includes events with timestamps (first and last), occurrence counts,
        messages, reasons, reporting components, and event types (Normal or Warning).

        ## Usage Tips
        - Warning events often indicate problems that need attention
        - Normal events provide information about expected lifecycle operations
        - The count field shows how many times the same event has occurred
        - Recent events are most relevant for current issues

        Args:
            ctx: MCP context
            cluster_name: Name of the EKS cluster
            kind: Kind of the involved object
            name: Name of the involved object
            namespace: Namespace of the involved object (optional for non-namespaced resources)

        Returns:
            EventsResponse with events related to the specified object
        """
        # Check if sensitive data access is disabled
        if not self.allow_sensitive_data_access:
            error_msg = 'Access to Kubernetes events requires --allow-sensitive-data-access flag'
            log_with_request_id(ctx, LogLevel.ERROR, error_msg)
            return EventsResponse(
                isError=True,
                content=[TextContent(type='text', text=error_msg)],
                involved_object_kind=kind,
                involved_object_name=name,
                involved_object_namespace=namespace,
                count=0,
                events=[],
            )

        try:
            # Get Kubernetes client for the cluster
            k8s_client = self.get_client(cluster_name)

            # Get events
            events = k8s_client.get_events(
                kind=kind,
                name=name,
                namespace=namespace,
            )

            # Format resource name for logging
            resource_name = f'{namespace + "/" if namespace else ""}{name}'

            # Clean up events and create event items
            cleaned_events = [self.cleanup_resource_response(event) for event in events]
            event_items = [
                EventItem(
                    first_timestamp=event['first_timestamp'],
                    last_timestamp=event['last_timestamp'],
                    count=event['count'],
                    message=event['message'],
                    reason=event['reason'],
                    reporting_component=event['reporting_component'],
                    type=event['type'],
                )
                for event in cleaned_events
            ]

            log_with_request_id(
                ctx, LogLevel.INFO, f'Cleaned up events for {kind} {resource_name}'
            )

            # Log success
            log_with_request_id(
                ctx, LogLevel.INFO, f'Retrieved {len(events)} events for {kind} {resource_name}'
            )

            # Return success response
            return EventsResponse(
                isError=False,
                content=[
                    TextContent(
                        type='text',
                        text=f'Successfully retrieved {len(events)} events for {kind} {resource_name}',
                    )
                ],
                involved_object_kind=kind,
                involved_object_name=name,
                involved_object_namespace=namespace,
                count=len(events),
                events=event_items,
            )

        except Exception as e:
            # Format resource name for error message
            resource_name = f'{namespace + "/" if namespace else ""}{name}'

            # Log error
            error_msg = f'Failed to get events for {kind} {resource_name}: {str(e)}'
            log_with_request_id(ctx, LogLevel.ERROR, error_msg)

            # Return error response
            return EventsResponse(
                isError=True,
                content=[TextContent(type='text', text=error_msg)],
                involved_object_kind=kind,
                involved_object_name=name or '',
                involved_object_namespace=namespace,
                count=0,
                events=[],
            )

    async def list_api_versions(
        self,
        ctx: Context,
        cluster_name: str = Field(
            ..., description='Name of the EKS cluster to query for available API versions.'
        ),
    ) -> ApiVersionsResponse:
        """List all available API versions in the Kubernetes cluster.

        This tool discovers all available API versions on the Kubernetes cluster,
        which is helpful for determining the correct apiVersion to use when
        managing Kubernetes resources. It returns both core APIs and API groups,
        useful for verifying API compatibility and discovering available resources.

        ## Response Information
        The response includes core APIs (like 'v1'), API groups with versions
        (like 'apps/v1'), extension APIs (like 'networking.k8s.io/v1'), and
        any Custom Resource Definition (CRD) APIs installed in the cluster.

        ## Usage Tips
        - Use this tool before creating or updating resources to ensure API compatibility
        - Different Kubernetes versions may have different available APIs
        - Some APIs may be deprecated or removed in newer Kubernetes versions
        - Custom resources will only appear if their CRDs are installed in the cluster

        Args:
            ctx: MCP context
            cluster_name: Name of the EKS cluster

        Returns:
            ApiVersionsResponse with list of available API versions
        """
        try:
            # Get Kubernetes client for the cluster
            k8s_client = self.get_client(cluster_name)

            # Get API versions from the cluster (excluding core APIs)
            api_versions = k8s_client.get_api_versions()

            # Log success
            log_with_request_id(
                ctx,
                LogLevel.INFO,
                f'Retrieved {len(api_versions)} API versions from cluster {cluster_name}',
            )

            # Return success response
            return ApiVersionsResponse(
                isError=False,
                content=[
                    TextContent(
                        type='text',
                        text=f'Successfully retrieved {len(api_versions)} API versions from cluster {cluster_name}',
                    )
                ],
                cluster_name=cluster_name,
                api_versions=api_versions,
                count=len(api_versions),
            )

        except Exception as e:
            # Log error
            error_msg = f'Failed to get API versions from cluster {cluster_name}: {str(e)}'
            log_with_request_id(ctx, LogLevel.ERROR, error_msg)

            # Return error response
            return ApiVersionsResponse(
                isError=True,
                content=[TextContent(type='text', text=error_msg)],
                cluster_name=cluster_name,
                api_versions=[],
                count=0,
            )
