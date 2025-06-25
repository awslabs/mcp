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

"""ROSA cluster management handler for the ROSA MCP Server."""

import json
import subprocess
from awslabs.rosa_mcp_server.aws_helper import AwsHelper
from awslabs.rosa_mcp_server.consts import (
    DEFAULT_MACHINE_TYPE,
    DEFAULT_OPENSHIFT_VERSION,
    DEFAULT_REPLICAS,
    MCP_CLUSTER_NAME_TAG_KEY,
    MCP_MANAGED_TAG_KEY,
    MCP_MANAGED_TAG_VALUE,
    ROSA_CLUSTER_CREATE_TIMEOUT,
    ROSA_CLUSTER_DELETE_TIMEOUT,
    ROSA_CLUSTER_READY_STATE,
)
from awslabs.rosa_mcp_server.logging_helper import LogLevel, log_with_request_id
from awslabs.rosa_mcp_server.models import (
    MachinePoolListResponse,
    MachinePoolResponse,
    MachinePoolSummary,
    ROSAClusterListResponse,
    ROSAClusterResponse,
    ROSAClusterSummary,
    ROSACredentialsResponse,
)
# Import enhancement modules
from awslabs.rosa_mcp_server.validation_helpers import (
    validate_cluster_configuration,
    recommend_instance_type,
    validate_networking_config,
    calculate_cluster_cost_estimate,
    generate_troubleshooting_steps,
)
from awslabs.rosa_mcp_server.workflow_helpers import (
    create_production_ready_cluster,
    generate_day2_operations_checklist,
    generate_migration_plan,
)
from loguru import logger
from mcp.server.fastmcp import Context, FastMCP
from mcp.types import CallToolResult
from pydantic import Field
from typing import Dict, List, Optional


class ROSAClusterHandler:
    """Handler for ROSA cluster operations."""

    def __init__(self, mcp: FastMCP, allow_write: bool = False):
        """Initialize the ROSA cluster handler."""
        self.mcp = mcp
        self.allow_write = allow_write
        self._register_tools()

    def _register_tools(self):
        """Register ROSA cluster tools with the MCP server."""
        # List clusters
        @self.mcp.tool()
        async def list_rosa_clusters(
            ctx: Context,
            region: Optional[str] = Field(None, description='AWS region to list clusters in'),
        ) -> ROSAClusterListResponse:
            """List all ROSA clusters in the specified region or all regions.

            This tool lists ROSA clusters and their current status.

            Args:
                ctx: MCP context
                region: Optional AWS region to filter clusters

            Returns:
                ROSAClusterListResponse with list of clusters

            Example:
                list_rosa_clusters(region="us-east-1")
            """
            log_with_request_id(ctx, LogLevel.INFO, 'Listing ROSA clusters', region=region)
            
            try:
                cmd = ['rosa', 'list', 'clusters', '--output', 'json']
                if region:
                    cmd.extend(['--region', region])
                
                result = subprocess.run(cmd, capture_output=True, text=True, check=True)
                clusters_data = json.loads(result.stdout) if result.stdout else []
                
                clusters = []
                for cluster in clusters_data:
                    cluster_summary = ROSAClusterSummary(
                        id=cluster.get('id', ''),
                        name=cluster.get('name', ''),
                        state=cluster.get('state', ''),
                        version=cluster.get('version', {}).get('id', ''),
                        region=cluster.get('region', {}).get('id', ''),
                        multi_az=cluster.get('multi_az', False),
                        api_url=cluster.get('api', {}).get('url', ''),
                        console_url=cluster.get('console', {}).get('url', ''),
                        created_at=cluster.get('creation_timestamp', ''),
                        nodes={
                            'control_plane': cluster.get('nodes', {}).get('master', 0),
                            'infra': cluster.get('nodes', {}).get('infra', 0),
                            'worker': cluster.get('nodes', {}).get('compute', 0),
                        }
                    )
                    clusters.append(cluster_summary)
                
                return ROSAClusterListResponse(
                    count=len(clusters),
                    clusters=clusters,
                    success=True,
                    content=f'Found {len(clusters)} ROSA clusters'
                )
                
            except subprocess.CalledProcessError as e:
                error_msg = f'Failed to list ROSA clusters: {e.stderr}'
                log_with_request_id(ctx, LogLevel.ERROR, error_msg)
                return ROSAClusterListResponse(
                    count=0,
                    clusters=[],
                    success=False,
                    content=error_msg
                )

        # Describe cluster
        @self.mcp.tool()
        async def describe_rosa_cluster(
            ctx: Context,
            cluster_name: str = Field(..., description='Name of the ROSA cluster'),
        ) -> ROSAClusterResponse:
            """Get detailed information about a specific ROSA cluster.

            This tool retrieves comprehensive details about a ROSA cluster including
            its state, endpoints, and configuration.

            Args:
                ctx: MCP context
                cluster_name: Name of the cluster to describe

            Returns:
                ROSAClusterResponse with cluster details

            Example:
                describe_rosa_cluster(cluster_name="my-rosa-cluster")
            """
            log_with_request_id(ctx, LogLevel.INFO, 'Describing ROSA cluster', cluster_name=cluster_name)
            
            try:
                cmd = ['rosa', 'describe', 'cluster', '--cluster', cluster_name, '--output', 'json']
                result = subprocess.run(cmd, capture_output=True, text=True, check=True)
                cluster_data = json.loads(result.stdout) if result.stdout else {}
                
                cluster_summary = ROSAClusterSummary(
                    id=cluster_data.get('id', ''),
                    name=cluster_data.get('name', ''),
                    state=cluster_data.get('state', ''),
                    version=cluster_data.get('version', {}).get('id', ''),
                    region=cluster_data.get('region', {}).get('id', ''),
                    multi_az=cluster_data.get('multi_az', False),
                    api_url=cluster_data.get('api', {}).get('url', ''),
                    console_url=cluster_data.get('console', {}).get('url', ''),
                    created_at=cluster_data.get('creation_timestamp', ''),
                    nodes={
                        'control_plane': cluster_data.get('nodes', {}).get('master', 0),
                        'infra': cluster_data.get('nodes', {}).get('infra', 0),
                        'worker': cluster_data.get('nodes', {}).get('compute', 0),
                    }
                )
                
                # Add troubleshooting suggestions if cluster is not ready
                if cluster_summary.state != ROSA_CLUSTER_READY_STATE:
                    error_type = 'installation_timeout' if 'install' in cluster_summary.state.lower() else 'node_not_ready'
                    troubleshooting = generate_troubleshooting_steps(error_type)
                    log_with_request_id(ctx, LogLevel.INFO, 
                        f'Cluster not ready. Troubleshooting steps: {troubleshooting}')
                
                return ROSAClusterResponse(
                    cluster=cluster_summary,
                    operation='describe',
                    success=True,
                    content=f'Successfully retrieved details for cluster {cluster_name}'
                )
                
            except subprocess.CalledProcessError as e:
                error_msg = f'Failed to describe cluster {cluster_name}: {e.stderr}'
                log_with_request_id(ctx, LogLevel.ERROR, error_msg)
                return CallToolResult(success=False, content=error_msg)

        # Create cluster
        @self.mcp.tool()
        async def create_rosa_cluster(
            ctx: Context,
            cluster_name: str = Field(..., description='Name for the new ROSA cluster'),
            region: str = Field(..., description='AWS region for the cluster'),
            version: Optional[str] = Field(DEFAULT_OPENSHIFT_VERSION, description='OpenShift version'),
            multi_az: bool = Field(True, description='Enable multi-AZ deployment'),
            replicas: int = Field(DEFAULT_REPLICAS, description='Number of worker nodes'),
            machine_type: str = Field(DEFAULT_MACHINE_TYPE, description='EC2 instance type for workers'),
            private_link: bool = Field(False, description='Use AWS PrivateLink'),
            sts: bool = Field(True, description='Use STS (recommended)'),
            tags: Optional[Dict[str, str]] = Field(None, description='Additional tags for the cluster'),
        ) -> ROSAClusterResponse:
            """Create a new ROSA cluster.

            This tool creates a new Red Hat OpenShift Service on AWS cluster with the specified configuration.
            The cluster creation process can take 30-45 minutes to complete.

            Args:
                ctx: MCP context
                cluster_name: Name for the new cluster
                region: AWS region for deployment
                version: OpenShift version to install
                multi_az: Whether to deploy across multiple availability zones
                replicas: Number of worker nodes
                machine_type: EC2 instance type for worker nodes
                private_link: Use AWS PrivateLink for private cluster
                sts: Use STS mode (recommended for security)
                tags: Additional tags to apply to the cluster

            Returns:
                ROSAClusterResponse with created cluster details

            Example:
                create_rosa_cluster(
                    cluster_name="production-cluster",
                    region="us-east-1",
                    version="4.14.0",
                    multi_az=True,
                    replicas=3
                )
            """
            if not self.allow_write:
                return CallToolResult(
                    success=False,
                    content='Write access is required to create clusters. Run with --allow-write flag.'
                )
            
            log_with_request_id(ctx, LogLevel.INFO, 'Creating ROSA cluster', cluster_name=cluster_name)
            
            # Validate cluster configuration based on e-book best practices
            is_valid, error_msg = validate_cluster_configuration(
                cluster_name, version, multi_az, replicas, machine_type
            )
            if not is_valid:
                return CallToolResult(success=False, content=f'Validation error: {error_msg}')
            
            # Calculate and show cost estimate
            cost_estimate = calculate_cluster_cost_estimate(
                region, machine_type, replicas, multi_az
            )
            log_with_request_id(ctx, LogLevel.INFO, 
                f'Estimated monthly cost: ${cost_estimate["total_monthly"]:.2f} '
                f'(${cost_estimate["total_hourly"]:.3f}/hour)'
            )
            
            try:
                # Build create command
                cmd = [
                    'rosa', 'create', 'cluster',
                    '--cluster-name', cluster_name,
                    '--region', region,
                    '--version', version,
                    '--replicas', str(replicas),
                    '--compute-machine-type', machine_type,
                    '--yes'  # Non-interactive mode
                ]
                
                if multi_az:
                    cmd.append('--multi-az')
                
                if private_link:
                    cmd.append('--private-link')
                
                if sts:
                    cmd.append('--sts')
                
                # Add MCP tags
                all_tags = {
                    MCP_MANAGED_TAG_KEY: MCP_MANAGED_TAG_VALUE,
                    MCP_CLUSTER_NAME_TAG_KEY: cluster_name
                }
                if tags:
                    all_tags.update(tags)
                
                tag_str = ','.join([f'{k}={v}' for k, v in all_tags.items()])
                cmd.extend(['--tags', tag_str])
                
                # Execute cluster creation
                result = subprocess.run(cmd, capture_output=True, text=True, check=True)
                
                # Get cluster details
                describe_result = await describe_rosa_cluster(ctx, cluster_name=cluster_name)
                
                return ROSAClusterResponse(
                    cluster=describe_result.cluster if hasattr(describe_result, 'cluster') else ROSAClusterSummary(
                        id='pending',
                        name=cluster_name,
                        state='installing',
                        version=version,
                        region=region,
                        multi_az=multi_az
                    ),
                    operation='create',
                    success=True,
                    content=f'Successfully initiated creation of ROSA cluster {cluster_name}. Installation will take 30-45 minutes.'
                )
                
            except subprocess.CalledProcessError as e:
                error_msg = f'Failed to create cluster {cluster_name}: {e.stderr}'
                log_with_request_id(ctx, LogLevel.ERROR, error_msg)
                return CallToolResult(success=False, content=error_msg)

        # Delete cluster
        @self.mcp.tool()
        async def delete_rosa_cluster(
            ctx: Context,
            cluster_name: str = Field(..., description='Name of the ROSA cluster to delete'),
            force: bool = Field(False, description='Force deletion without confirmation'),
        ) -> CallToolResult:
            """Delete a ROSA cluster.

            This tool deletes a ROSA cluster and all associated resources.
            Deletion can take 15-30 minutes to complete.

            Args:
                ctx: MCP context
                cluster_name: Name of the cluster to delete
                force: Skip confirmation prompts

            Returns:
                CallToolResult indicating success or failure

            Example:
                delete_rosa_cluster(cluster_name="old-cluster", force=True)
            """
            if not self.allow_write:
                return CallToolResult(
                    success=False,
                    content='Write access is required to delete clusters. Run with --allow-write flag.'
                )
            
            log_with_request_id(ctx, LogLevel.INFO, 'Deleting ROSA cluster', cluster_name=cluster_name)
            
            try:
                cmd = ['rosa', 'delete', 'cluster', '--cluster', cluster_name, '--yes']
                
                result = subprocess.run(cmd, capture_output=True, text=True, check=True)
                
                return CallToolResult(
                    success=True,
                    content=f'Successfully initiated deletion of ROSA cluster {cluster_name}. Deletion will take 15-30 minutes.'
                )
                
            except subprocess.CalledProcessError as e:
                error_msg = f'Failed to delete cluster {cluster_name}: {e.stderr}'
                log_with_request_id(ctx, LogLevel.ERROR, error_msg)
                return CallToolResult(success=False, content=error_msg)

        # Get cluster credentials
        @self.mcp.tool()
        async def get_rosa_cluster_credentials(
            ctx: Context,
            cluster_name: str = Field(..., description='Name of the ROSA cluster'),
        ) -> ROSACredentialsResponse:
            """Get access credentials for a ROSA cluster.

            This tool retrieves the API endpoint and admin credentials for accessing
            a ROSA cluster. For STS clusters, it will create temporary admin credentials.

            Args:
                ctx: MCP context
                cluster_name: Name of the cluster

            Returns:
                ROSACredentialsResponse with access details

            Example:
                get_rosa_cluster_credentials(cluster_name="my-cluster")
            """
            log_with_request_id(ctx, LogLevel.INFO, 'Getting cluster credentials', cluster_name=cluster_name)
            
            try:
                # First get cluster details
                describe_cmd = ['rosa', 'describe', 'cluster', '--cluster', cluster_name, '--output', 'json']
                describe_result = subprocess.run(describe_cmd, capture_output=True, text=True, check=True)
                cluster_data = json.loads(describe_result.stdout) if describe_result.stdout else {}
                
                api_url = cluster_data.get('api', {}).get('url', '')
                
                # Try to create admin user
                admin_cmd = ['rosa', 'create', 'admin', '--cluster', cluster_name, '--yes']
                admin_result = subprocess.run(admin_cmd, capture_output=True, text=True)
                
                username = None
                password = None
                
                if admin_result.returncode == 0:
                    # Parse admin credentials from output
                    for line in admin_result.stdout.split('\n'):
                        if 'username:' in line.lower():
                            username = line.split(':', 1)[1].strip()
                        elif 'password:' in line.lower():
                            password = line.split(':', 1)[1].strip()
                
                # Generate kubeconfig
                kubeconfig_path = f'/tmp/kubeconfig-{cluster_name}'
                login_cmd = ['rosa', 'create', 'kubeconfig', '--cluster', cluster_name, '--output', kubeconfig_path]
                subprocess.run(login_cmd, capture_output=True, text=True)
                
                return ROSACredentialsResponse(
                    api_url=api_url,
                    username=username,
                    password=password,
                    kubeconfig_path=kubeconfig_path if username else None,
                    success=True,
                    content='Successfully retrieved cluster credentials'
                )
                
            except subprocess.CalledProcessError as e:
                error_msg = f'Failed to get credentials for cluster {cluster_name}: {e.stderr}'
                log_with_request_id(ctx, LogLevel.ERROR, error_msg)
                return CallToolResult(success=False, content=error_msg)

        # List machine pools
        @self.mcp.tool()
        async def list_rosa_machine_pools(
            ctx: Context,
            cluster_name: str = Field(..., description='Name of the ROSA cluster'),
        ) -> MachinePoolListResponse:
            """List all machine pools in a ROSA cluster.

            This tool lists all machine pools (node pools) configured in a ROSA cluster,
            including their size, instance types, and configuration.

            Args:
                ctx: MCP context
                cluster_name: Name of the cluster

            Returns:
                MachinePoolListResponse with list of machine pools

            Example:
                list_rosa_machine_pools(cluster_name="my-cluster")
            """
            log_with_request_id(ctx, LogLevel.INFO, 'Listing machine pools', cluster_name=cluster_name)
            
            try:
                cmd = ['rosa', 'list', 'machinepools', '--cluster', cluster_name, '--output', 'json']
                result = subprocess.run(cmd, capture_output=True, text=True, check=True)
                pools_data = json.loads(result.stdout) if result.stdout else []
                
                machine_pools = []
                for pool in pools_data:
                    pool_summary = MachinePoolSummary(
                        id=pool.get('id', ''),
                        name=pool.get('id', ''),  # ROSA uses ID as name
                        replicas=pool.get('replicas', 0),
                        instance_type=pool.get('instance_type', ''),
                        labels=pool.get('labels', {}),
                        taints=pool.get('taints', []),
                        availability_zones=pool.get('availability_zones', []),
                        autoscaling=pool.get('autoscaling', {})
                    )
                    machine_pools.append(pool_summary)
                
                return MachinePoolListResponse(
                    cluster_name=cluster_name,
                    count=len(machine_pools),
                    machine_pools=machine_pools,
                    success=True,
                    content=f'Found {len(machine_pools)} machine pools'
                )
                
            except subprocess.CalledProcessError as e:
                error_msg = f'Failed to list machine pools: {e.stderr}'
                log_with_request_id(ctx, LogLevel.ERROR, error_msg)
                return MachinePoolListResponse(
                    cluster_name=cluster_name,
                    count=0,
                    machine_pools=[],
                    success=False,
                    content=error_msg
                )

        # Create machine pool
        @self.mcp.tool()
        async def create_rosa_machine_pool(
            ctx: Context,
            cluster_name: str = Field(..., description='Name of the ROSA cluster'),
            name: str = Field(..., description='Name for the machine pool'),
            replicas: int = Field(..., description='Number of machines in the pool'),
            instance_type: str = Field(DEFAULT_MACHINE_TYPE, description='EC2 instance type'),
            labels: Optional[Dict[str, str]] = Field(None, description='Labels to apply to nodes'),
            taints: Optional[List[Dict[str, str]]] = Field(None, description='Taints to apply to nodes'),
            autoscaling_min: Optional[int] = Field(None, description='Minimum nodes for autoscaling'),
            autoscaling_max: Optional[int] = Field(None, description='Maximum nodes for autoscaling'),
            workload_type: Optional[str] = Field('general', description='Type of workload (general, memory, compute, gpu)'),
        ) -> MachinePoolResponse:
            """Create a new machine pool in a ROSA cluster.

            This tool creates a new machine pool (node pool) with the specified configuration.
            Machine pools allow you to manage groups of worker nodes with different configurations.

            Args:
                ctx: MCP context
                cluster_name: Name of the cluster
                name: Name for the new machine pool
                replicas: Number of machines (ignored if autoscaling is enabled)
                instance_type: EC2 instance type for the machines
                labels: Labels to apply to nodes in this pool
                taints: Taints to apply to nodes for pod scheduling
                autoscaling_min: Minimum nodes for autoscaling
                autoscaling_max: Maximum nodes for autoscaling
                workload_type: Type of workload for instance recommendations

            Returns:
                MachinePoolResponse with created machine pool details

            Example:
                create_rosa_machine_pool(
                    cluster_name="my-cluster",
                    name="gpu-workers",
                    replicas=2,
                    instance_type="p3.2xlarge",
                    labels={"workload": "gpu"}
                )
            """
            if not self.allow_write:
                return CallToolResult(
                    success=False,
                    content='Write access is required to create machine pools. Run with --allow-write flag.'
                )
            
            log_with_request_id(ctx, LogLevel.INFO, 'Creating machine pool', 
                              cluster_name=cluster_name, name=name)
            
            # If workload type is specified but no instance type, recommend one
            if workload_type != 'general' and instance_type == DEFAULT_MACHINE_TYPE:
                # Estimate requirements based on workload type
                memory_req = 16 if workload_type == 'memory' else 8
                cpu_req = 8 if workload_type == 'compute' else 4
                instance_type = recommend_instance_type(workload_type, memory_req, cpu_req)
                log_with_request_id(ctx, LogLevel.INFO, 
                    f'Recommended instance type for {workload_type} workload: {instance_type}')
            
            try:
                cmd = [
                    'rosa', 'create', 'machinepool',
                    '--cluster', cluster_name,
                    '--name', name,
                    '--instance-type', instance_type
                ]
                
                # Handle autoscaling vs fixed size
                if autoscaling_min is not None and autoscaling_max is not None:
                    cmd.extend(['--enable-autoscaling', 
                              '--min-replicas', str(autoscaling_min),
                              '--max-replicas', str(autoscaling_max)])
                else:
                    cmd.extend(['--replicas', str(replicas)])
                
                # Add labels
                if labels:
                    label_str = ','.join([f'{k}={v}' for k, v in labels.items()])
                    cmd.extend(['--labels', label_str])
                
                # Add taints
                if taints:
                    taint_strs = []
                    for taint in taints:
                        taint_str = f"{taint['key']}={taint.get('value', '')}:{taint.get('effect', 'NoSchedule')}"
                        taint_strs.append(taint_str)
                    cmd.extend(['--taints', ','.join(taint_strs)])
                
                result = subprocess.run(cmd, capture_output=True, text=True, check=True)
                
                # Get created machine pool details
                pool_summary = MachinePoolSummary(
                    id=name,
                    name=name,
                    replicas=replicas,
                    instance_type=instance_type,
                    labels=labels or {},
                    taints=taints or [],
                    autoscaling={'min': autoscaling_min, 'max': autoscaling_max} if autoscaling_min else None
                )
                
                return MachinePoolResponse(
                    machine_pool=pool_summary,
                    cluster_name=cluster_name,
                    operation='create',
                    success=True,
                    content=f'Successfully created machine pool {name}'
                )
                
            except subprocess.CalledProcessError as e:
                error_msg = f'Failed to create machine pool {name}: {e.stderr}'
                log_with_request_id(ctx, LogLevel.ERROR, error_msg)
                return CallToolResult(success=False, content=error_msg)

        # Update machine pool
        @self.mcp.tool()
        async def update_rosa_machine_pool(
            ctx: Context,
            cluster_name: str = Field(..., description='Name of the ROSA cluster'),
            name: str = Field(..., description='Name of the machine pool to update'),
            replicas: Optional[int] = Field(None, description='New number of replicas'),
            autoscaling_min: Optional[int] = Field(None, description='New minimum for autoscaling'),
            autoscaling_max: Optional[int] = Field(None, description='New maximum for autoscaling'),
        ) -> MachinePoolResponse:
            """Update an existing machine pool in a ROSA cluster.

            This tool updates the size or autoscaling configuration of a machine pool.

            Args:
                ctx: MCP context
                cluster_name: Name of the cluster
                name: Name of the machine pool to update
                replicas: New number of replicas (for non-autoscaling pools)
                autoscaling_min: New minimum for autoscaling
                autoscaling_max: New maximum for autoscaling

            Returns:
                MachinePoolResponse with updated machine pool details

            Example:
                update_rosa_machine_pool(
                    cluster_name="my-cluster",
                    name="workers",
                    replicas=5
                )
            """
            if not self.allow_write:
                return CallToolResult(
                    success=False,
                    content='Write access is required to update machine pools. Run with --allow-write flag.'
                )
            
            log_with_request_id(ctx, LogLevel.INFO, 'Updating machine pool', 
                              cluster_name=cluster_name, name=name)
            
            try:
                cmd = [
                    'rosa', 'update', 'machinepool',
                    '--cluster', cluster_name,
                    name
                ]
                
                # Update replicas or autoscaling
                if autoscaling_min is not None and autoscaling_max is not None:
                    cmd.extend(['--enable-autoscaling',
                              '--min-replicas', str(autoscaling_min),
                              '--max-replicas', str(autoscaling_max)])
                elif replicas is not None:
                    cmd.extend(['--replicas', str(replicas)])
                
                result = subprocess.run(cmd, capture_output=True, text=True, check=True)
                
                # Get updated details
                list_result = await list_rosa_machine_pools(ctx, cluster_name=cluster_name)
                updated_pool = None
                for pool in list_result.machine_pools:
                    if pool.name == name:
                        updated_pool = pool
                        break
                
                if updated_pool:
                    return MachinePoolResponse(
                        machine_pool=updated_pool,
                        cluster_name=cluster_name,
                        operation='update',
                        success=True,
                        content=f'Successfully updated machine pool {name}'
                    )
                else:
                    return CallToolResult(
                        success=False,
                        content=f'Machine pool {name} not found after update'
                    )
                
            except subprocess.CalledProcessError as e:
                error_msg = f'Failed to update machine pool {name}: {e.stderr}'
                log_with_request_id(ctx, LogLevel.ERROR, error_msg)
                return CallToolResult(success=False, content=error_msg)

        # Delete machine pool
        @self.mcp.tool()
        async def delete_rosa_machine_pool(
            ctx: Context,
            cluster_name: str = Field(..., description='Name of the ROSA cluster'),
            name: str = Field(..., description='Name of the machine pool to delete'),
        ) -> CallToolResult:
            """Delete a machine pool from a ROSA cluster.

            This tool deletes a machine pool and all its nodes. The default machine pool
            cannot be deleted.

            Args:
                ctx: MCP context
                cluster_name: Name of the cluster
                name: Name of the machine pool to delete

            Returns:
                CallToolResult indicating success or failure

            Example:
                delete_rosa_machine_pool(cluster_name="my-cluster", name="extra-workers")
            """
            if not self.allow_write:
                return CallToolResult(
                    success=False,
                    content='Write access is required to delete machine pools. Run with --allow-write flag.'
                )
            
            log_with_request_id(ctx, LogLevel.INFO, 'Deleting machine pool', 
                              cluster_name=cluster_name, name=name)
            
            try:
                cmd = [
                    'rosa', 'delete', 'machinepool',
                    '--cluster', cluster_name,
                    name,
                    '--yes'
                ]
                
                result = subprocess.run(cmd, capture_output=True, text=True, check=True)
                
                return CallToolResult(
                    success=True,
                    content=f'Successfully deleted machine pool {name}'
                )
                
            except subprocess.CalledProcessError as e:
                error_msg = f'Failed to delete machine pool {name}: {e.stderr}'
                log_with_request_id(ctx, LogLevel.ERROR, error_msg)
                return CallToolResult(success=False, content=error_msg)

        # Get cluster logs
        @self.mcp.tool()
        async def get_rosa_cluster_logs(
            ctx: Context,
            cluster_name: str = Field(..., description='Name of the ROSA cluster'),
            install: bool = Field(False, description='Get installation logs'),
            uninstall: bool = Field(False, description='Get uninstallation logs'),
        ) -> CallToolResult:
            """Get logs for a ROSA cluster.

            This tool retrieves installation or uninstallation logs for a ROSA cluster,
            which is useful for troubleshooting cluster deployment issues.

            Args:
                ctx: MCP context
                cluster_name: Name of the cluster
                install: Get installation logs
                uninstall: Get uninstallation logs

            Returns:
                CallToolResult with log content

            Example:
                get_rosa_cluster_logs(cluster_name="my-cluster", install=True)
            """
            log_with_request_id(ctx, LogLevel.INFO, 'Getting cluster logs', 
                              cluster_name=cluster_name)
            
            try:
                cmd = ['rosa', 'logs', cluster_name]
                
                if install:
                    cmd.append('--install')
                elif uninstall:
                    cmd.append('--uninstall')
                
                result = subprocess.run(cmd, capture_output=True, text=True, check=True)
                
                return CallToolResult(
                    success=True,
                    content=result.stdout
                )
                
            except subprocess.CalledProcessError as e:
                error_msg = f'Failed to get logs for cluster {cluster_name}: {e.stderr}'
                log_with_request_id(ctx, LogLevel.ERROR, error_msg)
                return CallToolResult(success=False, content=error_msg)

        # Production-ready cluster workflow
        @self.mcp.tool()
        async def create_production_rosa_cluster(
            ctx: Context,
            cluster_name: str = Field(..., description='Name for the production cluster'),
            region: str = Field(..., description='AWS region for the cluster'),
            environment: str = Field('production', description='Environment type (production, staging, development)'),
        ) -> CallToolResult:
            """Create a production-ready ROSA cluster with best practices.

            This tool creates a ROSA cluster following e-book recommended configurations
            for different environments, including proper sizing, networking, and security settings.

            Args:
                ctx: MCP context
                cluster_name: Name for the new cluster
                region: AWS region for deployment
                environment: Environment type (affects sizing and configuration)

            Returns:
                CallToolResult with workflow details

            Example:
                create_production_rosa_cluster(
                    cluster_name="prod-cluster",
                    region="us-east-1",
                    environment="production"
                )
            """
            if not self.allow_write:
                return CallToolResult(
                    success=False,
                    content='Write access is required to create clusters. Run with --allow-write flag.'
                )
            
            log_with_request_id(ctx, LogLevel.INFO, 'Creating production-ready cluster', 
                              cluster_name=cluster_name, environment=environment)
            
            # Generate workflow
            workflow = await create_production_ready_cluster(cluster_name, region, environment)
            
            return CallToolResult(
                success=True,
                content=json.dumps(workflow, indent=2)
            )

        # Day 2 operations checklist
        @self.mcp.tool()
        async def get_day2_operations_checklist(
            ctx: Context,
            cluster_name: str = Field(..., description='Name of the ROSA cluster'),
        ) -> CallToolResult:
            """Get Day 2 operations checklist for a ROSA cluster.

            This tool generates a comprehensive checklist for Day 2 operations
            based on ROSA best practices, including monitoring, security, backup,
            performance, and maintenance tasks.

            Args:
                ctx: MCP context
                cluster_name: Name of the cluster

            Returns:
                CallToolResult with operations checklist

            Example:
                get_day2_operations_checklist(cluster_name="my-cluster")
            """
            log_with_request_id(ctx, LogLevel.INFO, 'Generating Day 2 operations checklist', 
                              cluster_name=cluster_name)
            
            checklist = generate_day2_operations_checklist(cluster_name)
            
            return CallToolResult(
                success=True,
                content=json.dumps(checklist, indent=2)
            )

        # Migration plan generator
        @self.mcp.tool()
        async def generate_rosa_migration_plan(
            ctx: Context,
            source_platform: str = Field(..., description='Source platform (kubernetes, openshift3, ecs, ec2)'),
            target_cluster: str = Field(..., description='Target ROSA cluster name'),
            applications: List[str] = Field(..., description='List of applications to migrate'),
        ) -> CallToolResult:
            """Generate a migration plan for moving applications to ROSA.

            This tool creates a detailed migration plan based on the source platform
            and target ROSA cluster, including strategies, tools, and timeline.

            Args:
                ctx: MCP context
                source_platform: Platform to migrate from
                target_cluster: Target ROSA cluster name
                applications: List of applications to migrate

            Returns:
                CallToolResult with migration plan

            Example:
                generate_rosa_migration_plan(
                    source_platform="kubernetes",
                    target_cluster="rosa-cluster",
                    applications=["web-app", "api-service", "database"]
                )
            """
            log_with_request_id(ctx, LogLevel.INFO, 'Generating migration plan', 
                              source=source_platform, target=target_cluster)
            
            plan = generate_migration_plan(source_platform, target_cluster, applications)
            
            return CallToolResult(
                success=True,
                content=json.dumps(plan, indent=2)
            )