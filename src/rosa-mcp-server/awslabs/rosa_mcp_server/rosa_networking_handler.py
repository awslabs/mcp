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

"""ROSA networking configuration handler for the ROSA MCP Server."""

import json
import subprocess
from awslabs.rosa_mcp_server.logging_helper import LogLevel, log_with_request_id
from awslabs.rosa_mcp_server.validation_helpers import validate_networking_config
from loguru import logger
from mcp.server.fastmcp import Context, FastMCP
from mcp.types import CallToolResult
from pydantic import Field
from typing import Dict, List, Optional


class ROSANetworkingHandler:
    """Handler for ROSA networking and ingress operations."""

    def __init__(self, mcp: FastMCP, allow_write: bool = False):
        """Initialize the ROSA networking handler."""
        self.mcp = mcp
        self.allow_write = allow_write
        self._register_tools()

    def _register_tools(self):
        """Register ROSA networking tools with the MCP server."""
        
        # Edit cluster network settings
        @self.mcp.tool()
        async def edit_rosa_cluster_network(
            ctx: Context,
            cluster_name: str = Field(..., description='Name of the ROSA cluster'),
            additional_trust_bundle: Optional[str] = Field(None, description='Path to additional CA bundle file'),
            http_proxy: Optional[str] = Field(None, description='HTTP proxy URL'),
            https_proxy: Optional[str] = Field(None, description='HTTPS proxy URL'),
            no_proxy: Optional[List[str]] = Field(None, description='List of domains to exclude from proxy'),
            private_link: bool = Field(False, description='Whether cluster uses AWS PrivateLink'),
        ) -> CallToolResult:
            """Edit network settings for a ROSA cluster.

            This tool updates proxy and CA trust bundle settings for an existing cluster.

            Args:
                ctx: MCP context
                cluster_name: Name of the cluster
                additional_trust_bundle: Path to CA bundle file for custom certificates
                http_proxy: HTTP proxy URL
                https_proxy: HTTPS proxy URL
                no_proxy: Domains to exclude from proxy

            Returns:
                CallToolResult indicating success or failure

            Example:
                edit_rosa_cluster_network(
                    cluster_name="my-cluster",
                    http_proxy="http://proxy.example.com:3128",
                    https_proxy="https://proxy.example.com:3128",
                    no_proxy=["internal.example.com", "10.0.0.0/8"]
                )
            """
            if not self.allow_write:
                return CallToolResult(
                    success=False,
                    content='Write access is required to edit network settings. Run with --allow-write flag.'
                )
            
            log_with_request_id(ctx, LogLevel.INFO, 'Editing cluster network settings', 
                              cluster_name=cluster_name)
            
            # Validate networking configuration
            is_valid, error_msg = validate_networking_config(
                private_link, http_proxy, https_proxy, no_proxy
            )
            if not is_valid:
                return CallToolResult(success=False, content=f'Validation error: {error_msg}')
            
            try:
                cmd = ['rosa', 'edit', 'cluster', '--cluster', cluster_name]
                
                if additional_trust_bundle:
                    cmd.extend(['--additional-trust-bundle-file', additional_trust_bundle])
                
                if http_proxy:
                    cmd.extend(['--http-proxy', http_proxy])
                
                if https_proxy:
                    cmd.extend(['--https-proxy', https_proxy])
                
                if no_proxy:
                    cmd.extend(['--no-proxy', ','.join(no_proxy)])
                
                result = subprocess.run(cmd, capture_output=True, text=True, check=True)
                
                return CallToolResult(
                    success=True,
                    content=f'Successfully updated network settings for cluster {cluster_name}'
                )
                
            except subprocess.CalledProcessError as e:
                error_msg = f'Failed to update network settings: {e.stderr}'
                log_with_request_id(ctx, LogLevel.ERROR, error_msg)
                return CallToolResult(success=False, content=error_msg)

        # List ingress controllers
        @self.mcp.tool()
        async def list_rosa_ingresses(
            ctx: Context,
            cluster_name: str = Field(..., description='Name of the ROSA cluster'),
        ) -> CallToolResult:
            """List all ingress controllers for a ROSA cluster.

            This tool lists all ingress controllers configured for the cluster,
            including their endpoints and load balancer settings.

            Args:
                ctx: MCP context
                cluster_name: Name of the cluster

            Returns:
                CallToolResult with ingress controller list

            Example:
                list_rosa_ingresses(cluster_name="my-cluster")
            """
            log_with_request_id(ctx, LogLevel.INFO, 'Listing ingress controllers', 
                              cluster_name=cluster_name)
            
            try:
                cmd = ['rosa', 'list', 'ingresses', '--cluster', cluster_name, '--output', 'json']
                result = subprocess.run(cmd, capture_output=True, text=True, check=True)
                
                ingresses = json.loads(result.stdout) if result.stdout else []
                
                # Format the output
                formatted_ingresses = []
                for ingress in ingresses:
                    formatted_ingresses.append({
                        'id': ingress.get('id', ''),
                        'listening': ingress.get('listening', ''),
                        'default': ingress.get('default', False),
                        'dns_name': ingress.get('dns_name', ''),
                        'lb_type': ingress.get('lb_type', 'classic'),
                        'route_selectors': ingress.get('route_selectors', {}),
                        'excluded_namespaces': ingress.get('excluded_namespaces', [])
                    })
                
                return CallToolResult(
                    success=True,
                    content=json.dumps(formatted_ingresses, indent=2)
                )
                
            except subprocess.CalledProcessError as e:
                error_msg = f'Failed to list ingress controllers: {e.stderr}'
                log_with_request_id(ctx, LogLevel.ERROR, error_msg)
                return CallToolResult(success=False, content=error_msg)

        # Create ingress controller
        @self.mcp.tool()
        async def create_rosa_ingress(
            ctx: Context,
            cluster_name: str = Field(..., description='Name of the ROSA cluster'),
            listening: str = Field('external', description='Listening mode: external or internal'),
            lb_type: str = Field('nlb', description='Load balancer type: classic or nlb'),
            replicas: int = Field(2, description='Number of ingress controller replicas'),
            route_selectors: Optional[Dict[str, str]] = Field(None, description='Route label selectors'),
            excluded_namespaces: Optional[List[str]] = Field(None, description='Namespaces to exclude'),
        ) -> CallToolResult:
            """Create a new ingress controller for a ROSA cluster.

            This tool creates an additional ingress controller with custom configuration.
            Each cluster has a default ingress controller, but you can add more for
            different routing needs.

            Args:
                ctx: MCP context
                cluster_name: Name of the cluster
                listening: Whether ingress is external or internal
                lb_type: Type of AWS load balancer (classic or nlb)
                replicas: Number of controller replicas
                route_selectors: Label selectors for routes
                excluded_namespaces: Namespaces to exclude from ingress

            Returns:
                CallToolResult indicating success or failure

            Example:
                create_rosa_ingress(
                    cluster_name="my-cluster",
                    listening="internal",
                    lb_type="nlb",
                    route_selectors={"app": "internal"}
                )
            """
            if not self.allow_write:
                return CallToolResult(
                    success=False,
                    content='Write access is required to create ingress controllers. Run with --allow-write flag.'
                )
            
            log_with_request_id(ctx, LogLevel.INFO, 'Creating ingress controller', 
                              cluster_name=cluster_name)
            
            try:
                cmd = [
                    'rosa', 'create', 'ingress',
                    '--cluster', cluster_name,
                    '--listening', listening,
                    '--lb-type', lb_type,
                    '--replicas', str(replicas)
                ]
                
                if route_selectors:
                    selector_str = ','.join([f'{k}={v}' for k, v in route_selectors.items()])
                    cmd.extend(['--route-selector', selector_str])
                
                if excluded_namespaces:
                    cmd.extend(['--excluded-namespaces', ','.join(excluded_namespaces)])
                
                result = subprocess.run(cmd, capture_output=True, text=True, check=True)
                
                return CallToolResult(
                    success=True,
                    content=f'Successfully created {listening} ingress controller with {lb_type} load balancer'
                )
                
            except subprocess.CalledProcessError as e:
                error_msg = f'Failed to create ingress controller: {e.stderr}'
                log_with_request_id(ctx, LogLevel.ERROR, error_msg)
                return CallToolResult(success=False, content=error_msg)

        # Edit ingress controller
        @self.mcp.tool()
        async def edit_rosa_ingress(
            ctx: Context,
            cluster_name: str = Field(..., description='Name of the ROSA cluster'),
            ingress_id: str = Field(..., description='ID of the ingress controller'),
            replicas: Optional[int] = Field(None, description='New number of replicas'),
            route_selectors: Optional[Dict[str, str]] = Field(None, description='New route selectors'),
            excluded_namespaces: Optional[List[str]] = Field(None, description='New excluded namespaces'),
        ) -> CallToolResult:
            """Edit an existing ingress controller configuration.

            This tool updates the configuration of an ingress controller, such as
            replica count or route selectors.

            Args:
                ctx: MCP context
                cluster_name: Name of the cluster
                ingress_id: ID of the ingress controller to edit
                replicas: New replica count
                route_selectors: New route label selectors
                excluded_namespaces: New list of excluded namespaces

            Returns:
                CallToolResult indicating success or failure

            Example:
                edit_rosa_ingress(
                    cluster_name="my-cluster",
                    ingress_id="abc123",
                    replicas=3
                )
            """
            if not self.allow_write:
                return CallToolResult(
                    success=False,
                    content='Write access is required to edit ingress controllers. Run with --allow-write flag.'
                )
            
            log_with_request_id(ctx, LogLevel.INFO, 'Editing ingress controller', 
                              cluster_name=cluster_name, ingress_id=ingress_id)
            
            try:
                cmd = [
                    'rosa', 'edit', 'ingress',
                    '--cluster', cluster_name,
                    ingress_id
                ]
                
                if replicas is not None:
                    cmd.extend(['--replicas', str(replicas)])
                
                if route_selectors:
                    selector_str = ','.join([f'{k}={v}' for k, v in route_selectors.items()])
                    cmd.extend(['--route-selector', selector_str])
                
                if excluded_namespaces is not None:
                    cmd.extend(['--excluded-namespaces', ','.join(excluded_namespaces)])
                
                result = subprocess.run(cmd, capture_output=True, text=True, check=True)
                
                return CallToolResult(
                    success=True,
                    content=f'Successfully updated ingress controller {ingress_id}'
                )
                
            except subprocess.CalledProcessError as e:
                error_msg = f'Failed to edit ingress controller: {e.stderr}'
                log_with_request_id(ctx, LogLevel.ERROR, error_msg)
                return CallToolResult(success=False, content=error_msg)

        # Delete ingress controller
        @self.mcp.tool()
        async def delete_rosa_ingress(
            ctx: Context,
            cluster_name: str = Field(..., description='Name of the ROSA cluster'),
            ingress_id: str = Field(..., description='ID of the ingress controller to delete'),
        ) -> CallToolResult:
            """Delete an ingress controller from a ROSA cluster.

            This tool deletes a non-default ingress controller. The default ingress
            controller cannot be deleted.

            Args:
                ctx: MCP context
                cluster_name: Name of the cluster
                ingress_id: ID of the ingress controller to delete

            Returns:
                CallToolResult indicating success or failure

            Example:
                delete_rosa_ingress(cluster_name="my-cluster", ingress_id="abc123")
            """
            if not self.allow_write:
                return CallToolResult(
                    success=False,
                    content='Write access is required to delete ingress controllers. Run with --allow-write flag.'
                )
            
            log_with_request_id(ctx, LogLevel.INFO, 'Deleting ingress controller', 
                              cluster_name=cluster_name, ingress_id=ingress_id)
            
            try:
                cmd = [
                    'rosa', 'delete', 'ingress',
                    '--cluster', cluster_name,
                    ingress_id,
                    '--yes'
                ]
                
                result = subprocess.run(cmd, capture_output=True, text=True, check=True)
                
                return CallToolResult(
                    success=True,
                    content=f'Successfully deleted ingress controller {ingress_id}'
                )
                
            except subprocess.CalledProcessError as e:
                error_msg = f'Failed to delete ingress controller: {e.stderr}'
                log_with_request_id(ctx, LogLevel.ERROR, error_msg)
                return CallToolResult(success=False, content=error_msg)

        # Configure cluster autoscaling
        @self.mcp.tool()
        async def configure_rosa_autoscaling(
            ctx: Context,
            cluster_name: str = Field(..., description='Name of the ROSA cluster'),
            enable: bool = Field(True, description='Enable or disable autoscaling'),
            min_nodes: Optional[int] = Field(None, description='Minimum number of nodes'),
            max_nodes: Optional[int] = Field(None, description='Maximum number of nodes'),
        ) -> CallToolResult:
            """Configure cluster autoscaling for a ROSA cluster.

            This tool enables or disables cluster autoscaling and sets the node limits.

            Args:
                ctx: MCP context
                cluster_name: Name of the cluster
                enable: Whether to enable autoscaling
                min_nodes: Minimum number of nodes (when enabling)
                max_nodes: Maximum number of nodes (when enabling)

            Returns:
                CallToolResult indicating success or failure

            Example:
                configure_rosa_autoscaling(
                    cluster_name="my-cluster",
                    enable=True,
                    min_nodes=3,
                    max_nodes=10
                )
            """
            if not self.allow_write:
                return CallToolResult(
                    success=False,
                    content='Write access is required to configure autoscaling. Run with --allow-write flag.'
                )
            
            log_with_request_id(ctx, LogLevel.INFO, 'Configuring cluster autoscaling', 
                              cluster_name=cluster_name, enable=enable)
            
            try:
                if enable:
                    if min_nodes is None or max_nodes is None:
                        return CallToolResult(
                            success=False,
                            content='min_nodes and max_nodes are required when enabling autoscaling'
                        )
                    
                    cmd = [
                        'rosa', 'edit', 'cluster',
                        '--cluster', cluster_name,
                        '--enable-autoscaling',
                        '--min-replicas', str(min_nodes),
                        '--max-replicas', str(max_nodes)
                    ]
                else:
                    cmd = [
                        'rosa', 'edit', 'cluster',
                        '--cluster', cluster_name,
                        '--disable-autoscaling'
                    ]
                
                result = subprocess.run(cmd, capture_output=True, text=True, check=True)
                
                status = 'enabled' if enable else 'disabled'
                return CallToolResult(
                    success=True,
                    content=f'Successfully {status} autoscaling for cluster {cluster_name}'
                )
                
            except subprocess.CalledProcessError as e:
                error_msg = f'Failed to configure autoscaling: {e.stderr}'
                log_with_request_id(ctx, LogLevel.ERROR, error_msg)
                return CallToolResult(success=False, content=error_msg)

        # Update cluster privacy
        @self.mcp.tool()
        async def update_rosa_cluster_privacy(
            ctx: Context,
            cluster_name: str = Field(..., description='Name of the ROSA cluster'),
            private: bool = Field(..., description='Make cluster API private'),
        ) -> CallToolResult:
            """Update the privacy settings of a ROSA cluster.

            This tool changes whether the cluster API endpoint is publicly accessible
            or only accessible within the VPC.

            Args:
                ctx: MCP context
                cluster_name: Name of the cluster
                private: Whether to make the API endpoint private

            Returns:
                CallToolResult indicating success or failure

            Example:
                update_rosa_cluster_privacy(cluster_name="my-cluster", private=True)
            """
            if not self.allow_write:
                return CallToolResult(
                    success=False,
                    content='Write access is required to update privacy settings. Run with --allow-write flag.'
                )
            
            log_with_request_id(ctx, LogLevel.INFO, 'Updating cluster privacy', 
                              cluster_name=cluster_name, private=private)
            
            try:
                cmd = [
                    'rosa', 'edit', 'cluster',
                    '--cluster', cluster_name
                ]
                
                if private:
                    cmd.append('--private')
                else:
                    cmd.append('--public')
                
                result = subprocess.run(cmd, capture_output=True, text=True, check=True)
                
                visibility = 'private' if private else 'public'
                return CallToolResult(
                    success=True,
                    content=f'Successfully updated cluster {cluster_name} to {visibility} access'
                )
                
            except subprocess.CalledProcessError as e:
                error_msg = f'Failed to update cluster privacy: {e.stderr}'
                log_with_request_id(ctx, LogLevel.ERROR, error_msg)
                return CallToolResult(success=False, content=error_msg)