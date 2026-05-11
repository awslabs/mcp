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

"""Kubernetes/OpenShift operations handler using the kubernetes Python library.

Connects to ROSA clusters by fetching kubeconfig from the OCM API, then
performs operations via the kubernetes client library.
"""

import json
import tempfile
import yaml
from awslabs.rosa_mcp_server.ocm_client import OCMClient
from kubernetes import client as k8s_client
from kubernetes import config as k8s_config
from mcp.server.fastmcp import Context
from mcp.types import TextContent
from typing import Optional


class K8sHandler:
    """Handler for Kubernetes/OpenShift operations via kubernetes Python library."""

    def __init__(
        self,
        mcp,
        ocm_client: OCMClient,
        allow_write: bool = False,
        allow_sensitive_data_access: bool = False,
    ):
        """Initialize the handler.

        Args:
            mcp: The FastMCP server instance.
            ocm_client: Shared OCM API client for fetching cluster credentials.
            allow_write: Whether write operations are permitted.
            allow_sensitive_data_access: Whether sensitive data access is permitted.
        """
        self.mcp = mcp
        self.ocm = ocm_client
        self.allow_write = allow_write
        self.allow_sensitive_data_access = allow_sensitive_data_access

        self.mcp.tool(name='rosa_list_resources')(self.rosa_list_resources)
        self.mcp.tool(name='rosa_get_pod_logs')(self.rosa_get_pod_logs)
        self.mcp.tool(name='rosa_get_events')(self.rosa_get_events)
        self.mcp.tool(name='rosa_apply_yaml')(self.rosa_apply_yaml)
        self.mcp.tool(name='rosa_get_nodes')(self.rosa_get_nodes)

    async def _get_k8s_client(self, cluster_id: str) -> k8s_client.ApiClient:
        """Get a configured kubernetes API client for the given cluster.

        Fetches the kubeconfig from OCM and creates an API client.

        Args:
            cluster_id: The OCM cluster ID.

        Returns:
            Configured kubernetes ApiClient.
        """
        creds = await self.ocm.get_cluster_credentials(cluster_id)
        kubeconfig_data = creds.get('kubeconfig', '')

        if not kubeconfig_data:
            raise ValueError(
                f'No kubeconfig available for cluster {cluster_id}. '
                'Cluster may still be provisioning or credentials are not accessible.'
            )

        # Write kubeconfig to a temp file and load it
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as tmp:
            tmp.write(kubeconfig_data)
            tmp_path = tmp.name

        api_client = k8s_config.new_client_from_config(config_file=tmp_path)
        return api_client

    async def rosa_list_resources(
        self,
        ctx: Context,
        cluster_id: str,
        kind: str,
        namespace: Optional[str] = None,
        label_selector: Optional[str] = None,
        field_selector: Optional[str] = None,
    ) -> list[TextContent]:
        """List Kubernetes/OpenShift resources in a ROSA cluster.

        Args:
            ctx: MCP context.
            cluster_id: The OCM cluster ID.
            kind: Kind of Kubernetes resource (e.g., Pod, Deployment, Service, Route).
            namespace: Namespace to list from. If omitted, lists across all namespaces.
            label_selector: Label selector to filter resources (e.g., "app=myapp").
            field_selector: Field selector to filter resources (e.g., "status.phase=Running").
        """
        api_client = await self._get_k8s_client(cluster_id)

        try:
            # Use dynamic client for flexibility with any resource kind
            from kubernetes.client import AppsV1Api, CoreV1Api, CustomObjectsApi

            kwargs = {}
            if label_selector:
                kwargs['label_selector'] = label_selector
            if field_selector:
                kwargs['field_selector'] = field_selector

            # Map common kinds to their API calls
            kind_lower = kind.lower()
            core_v1 = CoreV1Api(api_client)
            apps_v1 = AppsV1Api(api_client)

            result = None
            if kind_lower == 'pod':
                if namespace:
                    result = core_v1.list_namespaced_pod(namespace, **kwargs)
                else:
                    result = core_v1.list_pod_for_all_namespaces(**kwargs)
            elif kind_lower == 'service':
                if namespace:
                    result = core_v1.list_namespaced_service(namespace, **kwargs)
                else:
                    result = core_v1.list_service_for_all_namespaces(**kwargs)
            elif kind_lower == 'node':
                result = core_v1.list_node(**kwargs)
            elif kind_lower == 'namespace':
                result = core_v1.list_namespace(**kwargs)
            elif kind_lower == 'deployment':
                if namespace:
                    result = apps_v1.list_namespaced_deployment(namespace, **kwargs)
                else:
                    result = apps_v1.list_deployment_for_all_namespaces(**kwargs)
            elif kind_lower == 'configmap':
                if namespace:
                    result = core_v1.list_namespaced_config_map(namespace, **kwargs)
                else:
                    result = core_v1.list_config_map_for_all_namespaces(**kwargs)
            elif kind_lower == 'secret':
                if namespace:
                    result = core_v1.list_namespaced_secret(namespace, **kwargs)
                else:
                    result = core_v1.list_secret_for_all_namespaces(**kwargs)
            elif kind_lower == 'event':
                if namespace:
                    result = core_v1.list_namespaced_event(namespace, **kwargs)
                else:
                    result = core_v1.list_event_for_all_namespaces(**kwargs)
            else:
                # Fallback: try using the dynamic/custom objects API
                CustomObjectsApi(api_client)
                # For custom resources, caller should use the full group/version
                # For now, return an informative message
                return [TextContent(
                    type='text',
                    text=json.dumps({
                        'error': (
                            f'Resource kind "{kind}" is not directly supported. '
                            'Supported kinds: Pod, Service, Node, Namespace, Deployment, '
                            'ConfigMap, Secret, Event. For custom resources, use the '
                            'OpenShift API directly.'
                        ),
                    }),
                )]

            # Serialize the response
            data = api_client.sanitize_for_serialization(result)
            return [TextContent(type='text', text=json.dumps(data, indent=2))]

        finally:
            await api_client.close() if hasattr(api_client, 'close') else None

    async def rosa_get_pod_logs(
        self,
        ctx: Context,
        cluster_id: str,
        pod_name: str,
        namespace: str = 'default',
        container: Optional[str] = None,
        tail_lines: int = 100,
        previous: bool = False,
        since_seconds: Optional[int] = None,
    ) -> list[TextContent]:
        """Get logs from a pod in a ROSA cluster.

        Args:
            ctx: MCP context.
            cluster_id: The OCM cluster ID.
            pod_name: Name of the pod to get logs from.
            namespace: Namespace where the pod is located.
            container: Specific container name (required for multi-container pods).
            tail_lines: Number of recent log lines to retrieve.
            previous: Get logs from the previous container instance.
            since_seconds: Only return logs newer than this many seconds.
        """
        if not self.allow_sensitive_data_access:
            raise ValueError(
                'Sensitive data access is not allowed. '
                'Start the server with --allow-sensitive-data-access to enable log retrieval.'
            )

        api_client = await self._get_k8s_client(cluster_id)

        try:
            core_v1 = k8s_client.CoreV1Api(api_client)

            kwargs = {
                'name': pod_name,
                'namespace': namespace,
                'tail_lines': tail_lines,
                'previous': previous,
            }
            if container:
                kwargs['container'] = container
            if since_seconds:
                kwargs['since_seconds'] = since_seconds

            logs = core_v1.read_namespaced_pod_log(**kwargs)
            return [TextContent(type='text', text=logs or '(no logs available)')]

        finally:
            await api_client.close() if hasattr(api_client, 'close') else None

    async def rosa_get_events(
        self,
        ctx: Context,
        cluster_id: str,
        namespace: str = 'default',
        resource_name: Optional[str] = None,
        resource_kind: Optional[str] = None,
    ) -> list[TextContent]:
        """Get Kubernetes events from a ROSA cluster.

        Args:
            ctx: MCP context.
            cluster_id: The OCM cluster ID.
            namespace: Namespace to get events from.
            resource_name: Filter events for a specific resource by name.
            resource_kind: Filter events for a specific resource kind.
        """
        if not self.allow_sensitive_data_access:
            raise ValueError(
                'Sensitive data access is not allowed. '
                'Start the server with --allow-sensitive-data-access to enable event retrieval.'
            )

        api_client = await self._get_k8s_client(cluster_id)

        try:
            core_v1 = k8s_client.CoreV1Api(api_client)

            kwargs = {}
            field_parts = []
            if resource_name:
                field_parts.append(f'involvedObject.name={resource_name}')
            if resource_kind:
                field_parts.append(f'involvedObject.kind={resource_kind}')
            if field_parts:
                kwargs['field_selector'] = ','.join(field_parts)

            events = core_v1.list_namespaced_event(namespace, **kwargs)
            data = api_client.sanitize_for_serialization(events)
            return [TextContent(type='text', text=json.dumps(data, indent=2))]

        finally:
            await api_client.close() if hasattr(api_client, 'close') else None

    async def rosa_apply_yaml(
        self,
        ctx: Context,
        cluster_id: str,
        yaml_content: str,
        namespace: Optional[str] = None,
    ) -> list[TextContent]:
        """Apply a YAML manifest to a ROSA cluster.

        Args:
            ctx: MCP context.
            cluster_id: The OCM cluster ID.
            yaml_content: The YAML manifest content to apply.
            namespace: Namespace to apply the manifest to. If omitted, uses manifest namespace.
        """
        if not self.allow_write:
            raise ValueError(
                'Write operations disabled. Start the server with --allow-write.'
            )

        api_client = await self._get_k8s_client(cluster_id)

        try:
            from kubernetes import utils as k8s_utils

            # Parse YAML documents
            docs = list(yaml.safe_load_all(yaml_content))
            results = []

            for doc in docs:
                if not doc:
                    continue

                # Override namespace if specified
                if namespace:
                    doc.setdefault('metadata', {})['namespace'] = namespace

                # Use kubernetes utils to create from dict
                k8s_utils.create_from_dict(api_client, doc)
                kind = doc.get('kind', 'Unknown')
                name = doc.get('metadata', {}).get('name', 'unknown')
                results.append(f'{kind}/{name} applied')

            return [TextContent(
                type='text',
                text=json.dumps({
                    'message': 'YAML applied successfully.',
                    'resources': results,
                }),
            )]

        finally:
            await api_client.close() if hasattr(api_client, 'close') else None

    async def rosa_get_nodes(
        self,
        ctx: Context,
        cluster_id: str,
        label_selector: Optional[str] = None,
    ) -> list[TextContent]:
        """Get the status of cluster nodes in a ROSA cluster.

        Args:
            ctx: MCP context.
            cluster_id: The OCM cluster ID.
            label_selector: Label selector to filter nodes (e.g., "node-role.kubernetes.io/worker=").
        """
        api_client = await self._get_k8s_client(cluster_id)

        try:
            core_v1 = k8s_client.CoreV1Api(api_client)

            kwargs = {}
            if label_selector:
                kwargs['label_selector'] = label_selector

            nodes = core_v1.list_node(**kwargs)
            data = api_client.sanitize_for_serialization(nodes)
            return [TextContent(type='text', text=json.dumps(data, indent=2))]

        finally:
            await api_client.close() if hasattr(api_client, 'close') else None
