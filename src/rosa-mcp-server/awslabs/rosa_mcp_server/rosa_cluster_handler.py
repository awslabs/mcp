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

"""ROSA cluster lifecycle handler using the OCM REST API."""

import json
from awslabs.rosa_mcp_server.ocm_client import OCMClient
from mcp.server.fastmcp import Context
from mcp.types import TextContent
from typing import Optional


class RosaClusterHandler:
    """Handler for ROSA cluster lifecycle operations via OCM API."""

    def __init__(self, mcp, ocm_client: OCMClient, allow_write: bool = False):
        """Initialize the handler.

        Args:
            mcp: The FastMCP server instance.
            ocm_client: Shared OCM API client.
            allow_write: Whether write operations are permitted.
        """
        self.mcp = mcp
        self.ocm = ocm_client
        self.allow_write = allow_write

        self.mcp.tool(name='rosa_list_clusters')(self.rosa_list_clusters)
        self.mcp.tool(name='rosa_describe_cluster')(self.rosa_describe_cluster)
        self.mcp.tool(name='rosa_create_cluster')(self.rosa_create_cluster)
        self.mcp.tool(name='rosa_delete_cluster')(self.rosa_delete_cluster)
        self.mcp.tool(name='rosa_list_versions')(self.rosa_list_versions)
        self.mcp.tool(name='rosa_list_upgrades')(self.rosa_list_upgrades)
        self.mcp.tool(name='rosa_upgrade_cluster')(self.rosa_upgrade_cluster)
        self.mcp.tool(name='rosa_get_cluster_credentials')(self.rosa_get_cluster_credentials)
        self.mcp.tool(name='rosa_get_install_logs')(self.rosa_get_install_logs)

    async def rosa_list_clusters(
        self,
        ctx: Context,
        search: Optional[str] = None,
    ) -> list[TextContent]:
        """List all ROSA clusters in the current account.

        Args:
            ctx: MCP context.
            search: Optional OCM search filter (e.g., "state = 'ready'", "name like 'prod%'").
        """
        data = await self.ocm.list_clusters(search=search or "product.id = 'rosa'")
        return [TextContent(type='text', text=json.dumps(data, indent=2))]

    async def rosa_describe_cluster(
        self,
        ctx: Context,
        cluster_id: str,
    ) -> list[TextContent]:
        """Get detailed information about a specific ROSA cluster.

        Args:
            ctx: MCP context.
            cluster_id: The OCM cluster ID.
        """
        data = await self.ocm.get_cluster(cluster_id)
        return [TextContent(type='text', text=json.dumps(data, indent=2))]

    async def rosa_create_cluster(
        self,
        ctx: Context,
        name: str,
        region: str,
        aws_account_id: str,
        version: Optional[str] = None,
        multi_az: bool = False,
        compute_nodes: int = 2,
        compute_machine_type: str = 'm5.xlarge',
        pod_cidr: str = '10.128.0.0/14',
        service_cidr: str = '172.30.0.0/16',
        machine_cidr: str = '10.0.0.0/16',
        host_prefix: int = 23,
        private: bool = False,
        subnet_ids: Optional[list[str]] = None,
        installer_role_arn: Optional[str] = None,
        support_role_arn: Optional[str] = None,
        controlplane_role_arn: Optional[str] = None,
        worker_role_arn: Optional[str] = None,
        operator_role_prefix: Optional[str] = None,
        oidc_config_id: Optional[str] = None,
        etcd_encryption: bool = False,
        fips: bool = False,
        tags: Optional[dict[str, str]] = None,
    ) -> list[TextContent]:
        """Create a new ROSA cluster via OCM API.

        Args:
            ctx: MCP context.
            name: Cluster name (2-54 chars, lowercase alphanumeric/hyphens).
            region: AWS region (e.g., us-east-1).
            aws_account_id: 12-digit AWS account ID.
            version: OpenShift version (e.g., '4.14.5'). Omit for latest.
            multi_az: Deploy across multiple availability zones.
            compute_nodes: Number of worker nodes.
            compute_machine_type: EC2 instance type for workers.
            pod_cidr: CIDR for pod network.
            service_cidr: CIDR for service network.
            machine_cidr: CIDR for machine network.
            host_prefix: Host prefix length for pod CIDR allocation per node.
            private: Make cluster private (PrivateLink).
            subnet_ids: Existing VPC subnet IDs for BYO VPC.
            installer_role_arn: ARN of the ROSA installer IAM role (STS mode).
            support_role_arn: ARN of the ROSA support IAM role (STS mode).
            controlplane_role_arn: ARN of the control plane IAM role (STS mode).
            worker_role_arn: ARN of the worker IAM role (STS mode).
            operator_role_prefix: Prefix for operator IAM roles (STS mode).
            oidc_config_id: OIDC config ID for STS mode.
            etcd_encryption: Enable etcd encryption.
            fips: Enable FIPS mode.
            tags: AWS resource tags.
        """
        if not self.allow_write:
            raise ValueError(
                'Write operations disabled. Start the server with --allow-write.'
            )

        body: dict = {
            'name': name,
            'product': {'id': 'rosa'},
            'cloud_provider': {'id': 'aws'},
            'region': {'id': region},
            'multi_az': multi_az,
            'ccs': {'enabled': True},
            'aws': {
                'account_id': aws_account_id,
            },
            'nodes': {
                'compute': compute_nodes,
                'compute_machine_type': {'id': compute_machine_type},
            },
            'network': {
                'type': 'OVNKubernetes',
                'pod_cidr': pod_cidr,
                'service_cidr': service_cidr,
                'machine_cidr': machine_cidr,
                'host_prefix': host_prefix,
            },
            'fips': fips,
            'etcd_encryption': etcd_encryption,
        }

        if version:
            body['version'] = {'id': f'openshift-v{version}', 'channel_group': 'stable'}

        if subnet_ids:
            body['aws']['subnet_ids'] = subnet_ids

        if private:
            body['aws']['private_link'] = True

        if tags:
            body['aws']['tags'] = tags

        # STS configuration
        if installer_role_arn:
            body['aws']['sts'] = {
                'enabled': True,
                'role_arn': installer_role_arn,
                'support_role_arn': support_role_arn or '',
                'instance_iam_roles': {
                    'master_role_arn': controlplane_role_arn or '',
                    'worker_role_arn': worker_role_arn or '',
                },
            }
            if operator_role_prefix:
                body['aws']['sts']['operator_role_prefix'] = operator_role_prefix
            if oidc_config_id:
                body['aws']['sts']['oidc_config'] = {'id': oidc_config_id}

        data = await self.ocm.create_cluster(body)
        return [TextContent(type='text', text=json.dumps(data, indent=2))]

    async def rosa_delete_cluster(
        self,
        ctx: Context,
        cluster_id: str,
        deprovision: bool = True,
    ) -> list[TextContent]:
        """Delete a ROSA cluster.

        Args:
            ctx: MCP context.
            cluster_id: The OCM cluster ID to delete.
            deprovision: Whether to remove AWS infrastructure (default True).
        """
        if not self.allow_write:
            raise ValueError(
                'Write operations disabled. Start the server with --allow-write.'
            )

        status_code = await self.ocm.delete_cluster(cluster_id, deprovision=deprovision)
        return [TextContent(
            type='text',
            text=json.dumps({'status': 'deletion_initiated', 'http_status': status_code}),
        )]

    async def rosa_list_versions(
        self,
        ctx: Context,
        channel_group: str = 'stable',
        hosted_cp_only: bool = False,
    ) -> list[TextContent]:
        """List available ROSA OpenShift versions.

        Args:
            ctx: MCP context.
            channel_group: Version channel (stable, candidate, nightly).
            hosted_cp_only: Only show HCP-enabled versions.
        """
        search_parts = ["rosa_enabled = 'true'", "enabled = 'true'"]
        search_parts.append(f"channel_group = '{channel_group}'")
        if hosted_cp_only:
            search_parts.append("hosted_control_plane_enabled = 'true'")

        data = await self.ocm.list_versions(search=' AND '.join(search_parts))
        return [TextContent(type='text', text=json.dumps(data, indent=2))]

    async def rosa_list_upgrades(
        self,
        ctx: Context,
        cluster_id: str,
    ) -> list[TextContent]:
        """List available upgrades for a ROSA cluster.

        Args:
            ctx: MCP context.
            cluster_id: The OCM cluster ID.
        """
        cluster = await self.ocm.get_cluster(cluster_id)
        current_version = cluster.get('version', {}).get('raw_id', 'unknown')
        available = cluster.get('version', {}).get('available_upgrades', [])
        result = {
            'cluster_id': cluster_id,
            'current_version': current_version,
            'available_upgrades': available,
        }
        return [TextContent(type='text', text=json.dumps(result, indent=2))]

    async def rosa_upgrade_cluster(
        self,
        ctx: Context,
        cluster_id: str,
        version: str,
        schedule: Optional[str] = None,
    ) -> list[TextContent]:
        """Schedule an upgrade for a ROSA cluster.

        Args:
            ctx: MCP context.
            cluster_id: The OCM cluster ID.
            version: Target OpenShift version (e.g., '4.14.6').
            schedule: Cron expression for scheduled upgrade (e.g., '0 2 * * *').
                     If omitted, the upgrade runs immediately.
        """
        if not self.allow_write:
            raise ValueError(
                'Write operations disabled. Start the server with --allow-write.'
            )

        body: dict = {
            'version': version,
            'schedule_type': 'manual',
            'upgrade_type': 'OSD',
        }
        if schedule:
            body['schedule'] = schedule
            body['schedule_type'] = 'automatic'

        data = await self.ocm.create_upgrade_policy(cluster_id, body)
        return [TextContent(type='text', text=json.dumps(data, indent=2))]

    async def rosa_get_cluster_credentials(
        self,
        ctx: Context,
        cluster_id: str,
    ) -> list[TextContent]:
        """Get cluster credentials (kubeconfig and admin password).

        Args:
            ctx: MCP context.
            cluster_id: The OCM cluster ID.
        """
        data = await self.ocm.get_cluster_credentials(cluster_id)
        return [TextContent(type='text', text=json.dumps(data, indent=2))]

    async def rosa_get_install_logs(
        self,
        ctx: Context,
        cluster_id: str,
        tail: Optional[int] = None,
    ) -> list[TextContent]:
        """Get cluster installation logs.

        Args:
            ctx: MCP context.
            cluster_id: The OCM cluster ID.
            tail: Number of lines from end to return.
        """
        data = await self.ocm.get_install_logs(cluster_id, tail=tail)
        return [TextContent(type='text', text=json.dumps(data, indent=2))]
