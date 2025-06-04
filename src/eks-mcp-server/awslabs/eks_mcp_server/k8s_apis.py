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

"""Kubernetes API client for the EKS MCP Server."""

import base64
import os
import tempfile
from awslabs.eks_mcp_server.models import Operation
from loguru import logger
from typing import Any, Dict, List, Optional


class K8sApis:
    """Class for managing Kubernetes API client.

    This class provides a simplified interface for interacting with the Kubernetes API
    using the official Kubernetes Python client.
    """

    def __init__(self, endpoint, token, ca_data):
        """Initialize Kubernetes API client.

        Args:
            endpoint: Kubernetes API endpoint
            token: Authentication token
            ca_data: CA certificate data (base64 encoded) - required for SSL verification
        """
        try:
            from kubernetes import client, dynamic

            configuration = client.Configuration()
            configuration.host = endpoint
            configuration.api_key = {'authorization': f'Bearer {token}'}

            # Store the CA cert file path for cleanup
            self._ca_cert_file_path = None

            # Always enable SSL verification with CA data
            configuration.verify_ssl = True

            # Create a temporary file for the CA certificate using a context manager
            try:
                with tempfile.NamedTemporaryFile(delete=False) as ca_cert_file:
                    ca_cert_data = base64.b64decode(ca_data)
                    ca_cert_file.write(ca_cert_data)
                    # File is automatically closed when exiting the with block

                    # Store the path for cleanup and set the SSL CA cert
                    self._ca_cert_file_path = ca_cert_file.name
                    # Set the SSL CA cert to the temporary file path
                    # Use setattr to avoid potential attribute access issues
                    setattr(configuration, 'ssl_ca_cert', ca_cert_file.name)
            except Exception as e:
                # If we have a path and the file exists, clean it up
                if (
                    hasattr(self, '_ca_cert_file_path')
                    and self._ca_cert_file_path
                    and os.path.exists(self._ca_cert_file_path)
                ):
                    os.unlink(self._ca_cert_file_path)
                raise e

            # Create base API client
            self.api_client = client.ApiClient(configuration)

            # Create dynamic client
            self.dynamic_client = dynamic.DynamicClient(self.api_client)

        except ImportError:
            logger.error('kubernetes package not installed')
            raise

    def _patch_resource(
        self,
        resource,
        body: Optional[Dict[str, Any]],
        name: Optional[str],
        namespace: Optional[str] = None,
        **kwargs,
    ) -> Any:
        """Patch a resource with strategic merge patch, falling back to merge patch if needed.

        Args:
            resource: The dynamic resource object
            body: The resource body to patch with
            name: Name of the resource
            namespace: Namespace of the resource (if namespaced)
            **kwargs: Additional arguments for the API call

        Returns:
            The API response
        """
        try:
            # First try with strategic merge patch (default)
            return resource.patch(
                body=body,
                name=name,
                namespace=namespace,
                content_type='application/strategic-merge-patch+json',
                **kwargs,
            )
        except Exception as e:
            # If we get a 415 error, try with merge patch
            if '415' in str(e) or 'Unsupported Media Type' in str(e):
                logger.warning(
                    f'Strategic merge patch not supported for {resource.kind}, falling back to merge patch'
                )
                return resource.patch(
                    body=body,
                    name=name,
                    namespace=namespace,
                    content_type='application/merge-patch+json',
                    **kwargs,
                )
            # Re-raise other errors
            raise

    def manage_resource(
        self,
        operation: Operation,
        kind: str,
        api_version: str,
        name: Optional[str] = None,
        namespace: Optional[str] = None,
        body: Optional[dict] = None,
        **kwargs,
    ) -> Any:
        """Manage a single Kubernetes resource with the specified operation using dynamic client.

        Args:
            operation: Operation to perform (Operation.CREATE, Operation.REPLACE, etc.)
            kind: Resource kind (e.g., 'Pod', 'Service')
            api_version: API version (e.g., 'v1', 'apps/v1')
            name: Resource name (required for replace, patch, delete, read)
            namespace: Namespace of the resource (optional)
            body: Resource body (required for create, replace, patch)
            **kwargs: Additional arguments for the API call

        Returns:
            The API response
        """
        # Validate parameters based on operation
        if (
            operation in [Operation.REPLACE, Operation.PATCH, Operation.DELETE, Operation.READ]
            and not name
        ):
            raise ValueError(f'Resource name is required for {operation.value} operation')

        if operation in [Operation.CREATE, Operation.REPLACE, Operation.PATCH] and not body:
            raise ValueError(f'Resource body is required for {operation.value} operation')

        try:
            # Get the API resource
            resource = self.dynamic_client.resources.get(api_version=api_version, kind=kind)

            # Set kind and apiVersion in the body if provided
            if body:
                body['kind'] = kind
                body['apiVersion'] = api_version

                # Set name and namespace in metadata if provided
                if name:
                    if 'metadata' not in body:
                        body['metadata'] = {}
                    body['metadata']['name'] = name
                if namespace:
                    if 'metadata' not in body:
                        body['metadata'] = {}
                    body['metadata']['namespace'] = namespace

            # Perform the operation based on the operation type
            if operation == Operation.CREATE:
                return resource.create(body=body, namespace=namespace, **kwargs)
            elif operation == Operation.REPLACE:
                return resource.replace(body=body, name=name, namespace=namespace, **kwargs)
            elif operation == Operation.PATCH:
                return self._patch_resource(resource, body, name, namespace, **kwargs)
            elif operation == Operation.DELETE:
                return resource.delete(name=name, namespace=namespace, **kwargs)
            elif operation == Operation.READ:
                return resource.get(name=name, namespace=namespace, **kwargs)
            else:
                raise ValueError(f'Unsupported operation: {operation.value}')

        except Exception as e:
            # Re-raise with more context
            raise ValueError(f'Error managing {kind} resource: {str(e)}')

    def list_resources(
        self,
        kind: str,
        api_version: str,
        namespace: Optional[str] = None,
        label_selector: Optional[str] = None,
        field_selector: Optional[str] = None,
        **kwargs,
    ) -> Any:
        """List Kubernetes resources of a specific kind using dynamic client.

        Args:
            kind: Resource kind (e.g., 'Pod', 'Service')
            api_version: API version (e.g., 'v1', 'apps/v1')
            namespace: Namespace to list resources from (optional)
            label_selector: Label selector to filter resources (optional)
            field_selector: Field selector to filter resources (optional)
            **kwargs: Additional arguments for the API call

        Returns:
            The API response containing the list of resources
        """
        try:
            # Get the API resource
            resource = self.dynamic_client.resources.get(api_version=api_version, kind=kind)

            # Prepare kwargs for the list operation
            list_kwargs = {}
            if label_selector:
                list_kwargs['label_selector'] = label_selector
            if field_selector:
                list_kwargs['field_selector'] = field_selector

            # Add any additional kwargs
            list_kwargs.update(kwargs)

            # List resources
            if namespace:
                return resource.get(namespace=namespace, **list_kwargs)
            else:
                return resource.get(**list_kwargs)

        except Exception as e:
            # Re-raise with more context
            raise ValueError(f'Error listing {kind} resources: {str(e)}')

    def apply_from_yaml(
        self, yaml_objects: list, namespace: str = 'default', force: bool = True, **kwargs
    ) -> tuple:
        """Apply YAML objects to the cluster with support for custom resources and updates.

        This method improves upon the standard create_from_yaml by:
        1. Supporting custom resources through the dynamic client
        2. Supporting updates to existing resources when force=True

        Args:
            yaml_objects: List of YAML objects to apply
            namespace: Default namespace to use for namespaced resources
            force: Whether to update resources if they already exist (like kubectl apply)
            **kwargs: Additional arguments for the API calls

        Returns:
            Tuple of (results, created_count, updated_count)
        """
        results = []
        created_count = 0
        updated_count = 0

        for obj in yaml_objects:
            if not obj:
                continue

            # Extract key information from the object
            kind = obj.get('kind')
            api_version = obj.get('apiVersion')
            metadata = obj.get('metadata', {})
            name = metadata.get('name')
            obj_namespace = metadata.get('namespace', namespace)

            if not kind or not api_version or not name:
                raise ValueError('Invalid resource: missing kind, apiVersion, or name')

            try:
                # Get the API resource
                resource = self.dynamic_client.resources.get(api_version=api_version, kind=kind)

                # Check if resource exists
                exists = False
                if force:
                    try:
                        resource.get(
                            name=name, namespace=obj_namespace if resource.namespaced else None
                        )
                        exists = True
                    except Exception:
                        # Resource doesn't exist, will be created
                        exists = False

                # Apply the resource
                if exists and force:
                    # Update existing resource - use patch only
                    result = self._patch_resource(
                        resource,
                        obj,
                        name,
                        obj_namespace if resource.namespaced else None,
                        **kwargs,
                    )
                    updated_count += 1
                else:
                    # Create new resource
                    result = resource.create(
                        body=obj,
                        namespace=obj_namespace if resource.namespaced else None,
                        **kwargs,
                    )
                    created_count += 1

                results.append(result)

            except Exception as e:
                # Add context to the error
                resource_name = f'{obj_namespace}/{name}' if obj_namespace else name
                raise ValueError(f'Error applying {kind} {resource_name}: {str(e)}')

        return results, created_count, updated_count

    def get_events(
        self,
        kind: str,
        name: str,
        namespace: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Get events related to a specific Kubernetes resource.

        Args:
            kind: Kind of the involved object (e.g., 'Pod', 'Deployment')
            name: Name of the involved object
            namespace: Namespace of the involved object (optional for non-namespaced resources)

        Returns:
            List of events related to the specified object
        """
        try:
            # Get the Event resource using the dynamic client
            event_resource = self.dynamic_client.resources.get(api_version='v1', kind='Event')

            # Prepare field selector to filter events
            field_selector = f'involvedObject.kind={kind},involvedObject.name={name}'

            # If namespace is provided, get events from that namespace
            # Otherwise, search across all namespaces
            if namespace:
                events_response = event_resource.get(
                    namespace=namespace, field_selector=field_selector
                )
            else:
                events_response = event_resource.get(field_selector=field_selector)

            # Process events
            result = []
            for event in events_response.items:
                # Dynamic client resources always have to_dict()
                event_dict = event.to_dict()

                # Extract relevant fields and handle camelCase field names
                first_timestamp = event_dict.get('firstTimestamp')
                last_timestamp = event_dict.get('lastTimestamp')
                source = event_dict.get('source', {})

                result.append(
                    {
                        'first_timestamp': str(first_timestamp) if first_timestamp else None,
                        'last_timestamp': str(last_timestamp) if last_timestamp else None,
                        'count': event_dict.get('count'),
                        'message': event_dict.get('message', ''),
                        'reason': event_dict.get('reason'),
                        'reporting_component': source.get('component'),
                        'type': event_dict.get('type'),
                    }
                )

            return result

        except Exception as e:
            # Re-raise with more context
            resource_name = f'{namespace + "/" if namespace else ""}{name}'
            raise ValueError(f'Error getting events for {kind} {resource_name}: {str(e)}')

    def get_pod_logs(
        self,
        pod_name: str,
        namespace: str,
        container_name: Optional[str] = None,
        since_seconds: Optional[int] = None,
        tail_lines: Optional[int] = None,
        limit_bytes: Optional[int] = None,
    ) -> str:
        """Get logs from a pod.

        Args:
            pod_name: Name of the pod
            namespace: Namespace of the pod
            container_name: Container name (optional, if pod contains more than one container)
            since_seconds: Only return logs newer than this many seconds (optional)
            tail_lines: Number of lines to return from the end of the logs (optional)
            limit_bytes: Maximum number of bytes to return (optional)

        Returns:
            Pod logs as a string
        """
        try:
            from kubernetes import client

            # Create CoreV1Api client
            core_v1_api = client.CoreV1Api(self.api_client)

            # Prepare parameters for the read_namespaced_pod_log method
            params = {}
            if container_name:
                params['container'] = container_name
            if since_seconds:
                params['since_seconds'] = since_seconds
            if tail_lines:
                params['tail_lines'] = tail_lines
            if limit_bytes:
                params['limit_bytes'] = limit_bytes

            # Call the read_namespaced_pod_log method
            logs_response = core_v1_api.read_namespaced_pod_log(
                name=pod_name, namespace=namespace, **params
            )

            return logs_response

        except Exception as e:
            # Re-raise with more context
            raise ValueError(f'Error getting logs from pod {namespace}/{pod_name}: {str(e)}')

    def get_api_versions(self) -> List[str]:
        """Get preferred API versions from the Kubernetes cluster.

        Returns only the preferred (stable) API version for each group, avoiding alpha/beta versions
        when stable versions are available.

        Returns:
            List of preferred API versions (e.g., ['v1', 'apps/v1', 'networking.k8s.io/v1'])
        """
        try:
            from kubernetes import client

            api_versions: set[str] = set()

            # Get core API version (v1)
            try:
                core_api = client.CoreApi(self.api_client)
                core_version_obj = core_api.get_api_versions()

                # Extract versions safely
                if core_version_obj is not None:
                    # Try to get versions as a list of strings
                    versions = getattr(core_version_obj, 'versions', None)
                    if versions is not None and isinstance(versions, list):
                        for version in versions:
                            if isinstance(version, str):
                                api_versions.add(version)
            except Exception as e:
                logger.warning(f'Error getting core API versions: {str(e)}')
                raise ValueError(f'Error getting API versions: {str(e)}')

            # Get API groups and their preferred versions
            try:
                apis_api = client.ApisApi(self.api_client)
                api_groups_obj = apis_api.get_api_versions()

                # Extract groups safely
                if api_groups_obj is not None:
                    groups = getattr(api_groups_obj, 'groups', None)
                    if groups is not None and isinstance(groups, list):
                        for group in groups:
                            if group is not None:
                                # Try to get preferred version
                                preferred_version = getattr(group, 'preferred_version', None)
                                if preferred_version is not None:
                                    group_version = getattr(
                                        preferred_version, 'group_version', None
                                    )
                                    if group_version is not None and isinstance(
                                        group_version, str
                                    ):
                                        api_versions.add(group_version)
            except Exception as e:
                logger.warning(f'Error getting API groups: {str(e)}')

            # Convert to sorted list
            return sorted(api_versions)

        except Exception as e:
            # Re-raise with more context
            raise ValueError(f'Error getting API versions: {str(e)}')

    def __del__(self):
        """Clean up temporary files when the object is garbage collected."""
        if (
            hasattr(self, '_ca_cert_file_path')
            and self._ca_cert_file_path
            and os.path.exists(self._ca_cert_file_path)
        ):
            try:
                os.unlink(self._ca_cert_file_path)
            except Exception:
                # Ignore errors during cleanup
                pass
