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

"""Hybrid Nodes handler for the EKS MCP Server."""

from awslabs.eks_mcp_server.aws_helper import AwsHelper
from awslabs.eks_mcp_server.k8s_apis import K8sApis
from awslabs.eks_mcp_server.logging_helper import LogLevel, log_with_request_id
from awslabs.eks_mcp_server.models import (
    EksVpcConfigResponse,
    EksInsightsResponse,
    EksInsightItem,
    EksInsightStatus
)
from mcp.server.fastmcp import Context
from mcp.types import TextContent
from pydantic import Field
from typing import Dict, List, Optional, Any, Union, cast
from datetime import datetime


class HybridNodesHandler:
    """Handler for Amazon EKS Hybrid Node diagnostics.
    
    This class provides tools for diagnosing and troubleshooting issues
    with hybrid nodes in EKS clusters.
    """

    def __init__(
        self,
        mcp,
        allow_write: bool = False,
        allow_sensitive_data_access: bool = False,
    ):
        """Initialize the Hybrid Nodes handler.

        Args:
            mcp: The MCP server instance
            allow_write: Whether to enable write access (default: False)
            allow_sensitive_data_access: Whether to allow access to sensitive data (default: False)
        """
        self.mcp = mcp
        self.allow_write = allow_write
        self.allow_sensitive_data_access = allow_sensitive_data_access
        
        # Register tools
        self.mcp.tool(name='get_eks_vpc_config')(self.get_eks_vpc_config)
        self.mcp.tool(name='get_eks_insights')(self.get_eks_insights)

         # Initialize AWS clients
        self.ec2_client = AwsHelper.create_boto3_client('ec2')
        self.eks_client = AwsHelper.create_boto3_client('eks')
        self.ssm_client = AwsHelper.create_boto3_client('ssm')
        


# -------------------------------------------------------------------------------------------------------------------------------------------- # 
    # VPC configuration tool 
    async def get_eks_vpc_config(
        self,
        ctx: Context,
        cluster_name: str = Field(
            ...,
            description='Name of the EKS cluster to get VPC configuration for',
        ),
        vpc_id: Optional[str] = Field(
            None,
            description='ID of the specific VPC to query (optional, will use cluster VPC if not specified)',
        ),
    ) -> EksVpcConfigResponse:
        """Get VPC configuration for an EKS cluster.

        This tool retrieves comprehensive VPC configuration details for any EKS cluster,
        including CIDR blocks and route tables which are essential for understanding
        network connectivity. For hybrid node setups, it also automatically identifies
        and includes remote node and pod CIDR configurations.

        ## Response Information
        The response includes VPC CIDR blocks, route tables, and when available,
        remote CIDR configurations for hybrid node connectivity.

        ## Usage Tips
        - Understand VPC networking configuration for any EKS cluster
        - Examine route tables to verify proper network connectivity
        - For hybrid setups: Check that remote node CIDR blocks are correctly configured
        - For hybrid setups: Verify that VPC route tables include routes for hybrid node CIDRs

        Args:
            ctx: MCP context
            cluster_name: Name of the EKS cluster
            vpc_id: Optional ID of the specific VPC to query

        Returns:
            EksVpcConfigResponse with VPC configuration details
        """
        # Extract values from Field objects before passing them to the implementation method
        vpc_id_value = None if vpc_id is None else str(vpc_id)
        
        # Delegate to the implementation method with extracted values
        return await self._get_eks_vpc_config_impl(ctx, cluster_name, vpc_id_value)
        
    async def _get_eks_vpc_config_impl(
        self,
        ctx: Context,
        cluster_name: str,
        vpc_id: Optional[str] = None
    ) -> EksVpcConfigResponse:
        """Internal implementation of get_eks_vpc_config."""
        try:
            # Get the VPC ID for the cluster if not provided
            if not vpc_id:
                # Get cluster information to determine VPC ID
                try:
                    cluster_response = self.eks_client.describe_cluster(name=cluster_name)
                    vpc_id = cluster_response['cluster'].get('resourcesVpcConfig', {}).get('vpcId')
                    
                    if not vpc_id:
                        error_message = f"Could not determine VPC ID for cluster {cluster_name}"
                        log_with_request_id(ctx, LogLevel.ERROR, error_message)
                        return EksVpcConfigResponse(
                            isError=True,
                            content=[TextContent(type='text', text=error_message)],
                            vpc_id="",
                            cidr_block="",
                            routes=[],
                            remote_node_cidr_blocks=[],
                            remote_pod_cidr_blocks=[],
                            subnets=[],
                            cluster_name=cluster_name
                        )
                except Exception as eks_error:
                    error_message = f"Error getting cluster VPC information: {str(eks_error)}"
                    log_with_request_id(ctx, LogLevel.ERROR, error_message)
                    return EksVpcConfigResponse(
                        isError=True,
                        content=[TextContent(type='text', text=error_message)],
                        vpc_id="",
                        cidr_block="",
                        routes=[],
                        remote_node_cidr_blocks=[],
                        remote_pod_cidr_blocks=[],
                        subnets=[],
                        cluster_name=cluster_name
                    )
            
            # Get VPC details
            vpc_response = self.ec2_client.describe_vpcs(VpcIds=[vpc_id])
            
            if not vpc_response['Vpcs']:
                error_message = f"VPC {vpc_id} not found"
                log_with_request_id(ctx, LogLevel.ERROR, error_message)
                return EksVpcConfigResponse(
                    isError=True,
                    content=[TextContent(type='text', text=error_message)],
                    vpc_id="",
                    cidr_block="",
                    routes=[],
                    remote_node_cidr_blocks=[],
                    remote_pod_cidr_blocks=[],
                    subnets=[],
                    cluster_name=cluster_name
                )
            
            # Extract VPC information
            vpc = vpc_response['Vpcs'][0]
            cidr_block = vpc.get('CidrBlock', '')
            additional_cidr_blocks = [cidr_association.get('CidrBlock', '') for cidr_association in vpc.get('CidrBlockAssociationSet', [])[1:] if 'CidrBlock' in cidr_association]
            
            # Get subnets for the VPC
            subnets_response = self.ec2_client.describe_subnets(
                Filters=[{'Name': 'vpc-id', 'Values': [vpc_id]}]
            )
            
            subnets = []
            for subnet in subnets_response.get('Subnets', []):
                # Calculate subnet information
                subnet_cidr_block = subnet.get('CidrBlock', '')
                available_ips = subnet.get('AvailableIpAddressCount', 0)
                is_public = subnet.get('MapPublicIpOnLaunch', False)
                assign_ipv6 = subnet.get('AssignIpv6AddressOnCreation', False)
                az_id = subnet.get('AvailabilityZoneId', '')
                
                # Check for disallowed AZs
                disallowed_azs = ['use1-az3', 'usw1-az2', 'cac1-az3']
                in_disallowed_az = az_id in disallowed_azs
                
                # Store subnet information
                subnet_info = {
                    'subnet_id': subnet.get('SubnetId', ''),
                    'cidr_block': subnet_cidr_block,
                    'az_id': az_id,
                    'az_name': subnet.get('AvailabilityZone', ''),
                    'available_ips': available_ips,
                    'is_public': is_public,
                    'assign_ipv6': assign_ipv6,
                    'in_disallowed_az': in_disallowed_az,
                    'has_sufficient_ips': available_ips >= 16  # AWS recommends 16
                }
                subnets.append(subnet_info)
            
            # Get route tables for the VPC
            route_tables_response = self.ec2_client.describe_route_tables(
                Filters=[{'Name': 'vpc-id', 'Values': [vpc_id]}]
            )
            
            # Extract route information from the main route table
            routes = []
            for rt in route_tables_response.get('RouteTables', []):
                # Check if this is the main route table
                is_main = False
                for association in rt.get('Associations', []):
                    if association.get('Main', False):
                        is_main = True
                        break
                
                if is_main:
                    for route in rt.get('Routes', []):
                        # Skip the local route
                        if route.get('GatewayId') == 'local':
                            continue
                        
                        # Determine the target type and ID
                        target_type = None
                        target_id = None
                        
                        for target_field in ['GatewayId', 'NatGatewayId', 'TransitGatewayId', 'NetworkInterfaceId', 'VpcPeeringConnectionId']:
                            if target_field in route and route[target_field]:
                                target_type = target_field.replace('Id', '').lower()
                                target_id = route[target_field]
                                break
                        
                        route_info = {
                            'destination_cidr_block': route.get('DestinationCidrBlock', ''),
                            'target_type': target_type or 'unknown',
                            'target_id': target_id or 'unknown',
                            'state': route.get('State', '')
                        }
                        routes.append(route_info)
            
            # Determine remote node and pod CIDR blocks from the EKS API
            remote_node_cidr_blocks = []
            remote_pod_cidr_blocks = []
            
            # Only try to fetch remote networks if not using explicit VPC ID
            # When an explicit VPC ID is provided, we skip fetching remote networks completely
            if vpc_id and 'cluster_response' in locals():
                # We already have the cluster response, use it without making a new call
                if 'remoteNetworkConfig' in locals().get('cluster_response', {}).get('cluster', {}):
                    remote_config = cluster_response['cluster']['remoteNetworkConfig']
                    
                    # Extract remote node CIDRs
                    if 'remoteNodeNetworks' in remote_config:
                        for network in remote_config['remoteNodeNetworks']:
                            if 'cidrs' in network:
                                for cidr in network['cidrs']:
                                    if cidr not in remote_node_cidr_blocks:
                                        remote_node_cidr_blocks.append(cidr)
                                        log_with_request_id(ctx, LogLevel.INFO, f"Found remote node CIDR in remoteNetworkConfig: {cidr}")
                    
                    # Extract remote pod CIDRs
                    if 'remotePodNetworks' in remote_config:
                        for network in remote_config['remotePodNetworks']:
                            if 'cidrs' in network:
                                for cidr in network['cidrs']:
                                    if cidr not in remote_pod_cidr_blocks:
                                        remote_pod_cidr_blocks.append(cidr)
                                        log_with_request_id(ctx, LogLevel.INFO, f"Found remote pod CIDR in remoteNetworkConfig: {cidr}")
            # Only try to fetch remote networks if vpc_id was not provided explicitly
            elif not vpc_id:
                try:
                    # Check EKS API remoteNetworkConfig
                    cluster_detail_response = self.eks_client.describe_cluster(name=cluster_name)
                except Exception as config_error:
                    log_with_request_id(ctx, LogLevel.WARNING, f"Error getting remote CIDR information from EKS API: {str(config_error)}")
            elif 'cluster' in locals().get('cluster_response', {}):
                # We already have the cluster response, no need to call describe_cluster again
                if 'remoteNetworkConfig' in locals().get('cluster_response', {}).get('cluster', {}):
                    remote_config = cluster_response['cluster']['remoteNetworkConfig']
                    
                    # Extract remote node CIDRs
                    if 'remoteNodeNetworks' in remote_config:
                        for network in remote_config['remoteNodeNetworks']:
                            if 'cidrs' in network:
                                for cidr in network['cidrs']:
                                    if cidr not in remote_node_cidr_blocks:
                                        remote_node_cidr_blocks.append(cidr)
                                        log_with_request_id(ctx, LogLevel.INFO, f"Found remote node CIDR in remoteNetworkConfig: {cidr}")
                    
                    # Extract remote pod CIDRs
                    if 'remotePodNetworks' in remote_config:
                        for network in remote_config['remotePodNetworks']:
                            if 'cidrs' in network:
                                for cidr in network['cidrs']:
                                    if cidr not in remote_pod_cidr_blocks:
                                        remote_pod_cidr_blocks.append(cidr)
                                        log_with_request_id(ctx, LogLevel.INFO, f"Found remote pod CIDR in remoteNetworkConfig: {cidr}")
            
            
            # Log summary of detected CIDRs
            if remote_node_cidr_blocks:
                log_with_request_id(ctx, LogLevel.INFO, f"Detected remote node CIDRs: {', '.join(remote_node_cidr_blocks)}")
            else:
                log_with_request_id(ctx, LogLevel.WARNING, "No remote node CIDRs detected")
                
            if remote_pod_cidr_blocks:
                log_with_request_id(ctx, LogLevel.INFO, f"Detected remote pod CIDRs: {', '.join(remote_pod_cidr_blocks)}")
            else:
                log_with_request_id(ctx, LogLevel.WARNING, "No remote pod CIDRs detected")
            
            # Create the response 
            success_message = f"Retrieved VPC configuration for {vpc_id} (cluster {cluster_name})"
            log_with_request_id(ctx, LogLevel.INFO, success_message)
            
            return EksVpcConfigResponse(
                isError=False,
                content=[TextContent(type='text', text=success_message)],
                vpc_id=vpc_id,
                cidr_block=cidr_block,
                additional_cidr_blocks=additional_cidr_blocks,
                routes=routes,
                remote_node_cidr_blocks=remote_node_cidr_blocks,
                remote_pod_cidr_blocks=remote_pod_cidr_blocks,
                subnets=subnets,
                cluster_name=cluster_name
            )
            
        except Exception as e:
            error_message = f"Error retrieving VPC configuration: {str(e)}"
            log_with_request_id(ctx, LogLevel.ERROR, error_message)
            return EksVpcConfigResponse(
                isError=True,
                content=[TextContent(type='text', text=error_message)],
                vpc_id="",
                cidr_block="",
                routes=[],
                remote_node_cidr_blocks=[],
                remote_pod_cidr_blocks=[],
                subnets=[],
                cluster_name=cluster_name
            )            
    
 # -------------------------------------------------------------------------------------------------------------------------------------------- #  

    # EKS Insights tool
    async def get_eks_insights(
        self,
        ctx: Context,
        cluster_name: str = Field(..., description='Name of the EKS cluster'),
        insight_id: Optional[str] = Field(
            None,
            description='ID of a specific insight to get detailed information for. If provided, returns detailed information about this specific insight.',
        ),
        category: Optional[str] = Field(
            None,
            description='Filter insights by category (e.g., "CONFIGURATION" or "UPGRADE_READINESS")',
        ),
        region: Optional[str] = Field(
            None,
            description='AWS region code (e.g., "us-west-2"). If not provided, uses the default region from AWS configuration.',
        ),
    ) -> EksInsightsResponse:
        """Get EKS Insights for cluster configuration and upgrade readiness.
        
        This tool retrieves Amazon EKS Insights that identify potential issues with 
        your EKS cluster. These insights help identify both cluster configuration issues
        and upgrade readiness concerns that might affect hybrid nodes functionality.
        
        Amazon EKS provides two types of insights:
        - CONFIGURATION insights: Identify misconfigurations in your EKS cluster setup
        - UPGRADE_READINESS insights: Identify issues that could prevent successful cluster upgrades
        
        When used without an insight_id, it returns a list of all insights.
        When used with an insight_id, it returns detailed information about 
        that specific insight, including recommendations.
        
        ## Response Information
        The response includes insight details such as status, description, and 
        recommendations for addressing identified issues.
        
        ## Usage Tips
        - Review CONFIGURATION insights to identify cluster misconfigurations
        - Check UPGRADE_READINESS insights before upgrading your cluster
        - Pay special attention to insights with FAILING status
        - Focus on insights related to node and network configuration for hybrid nodes
        
        Args:
            ctx: MCP context
            cluster_name: Name of the EKS cluster
            insight_id: Optional ID of a specific insight to get detailed information for
            category: Optional category to filter insights by (e.g., "CONFIGURATION" or "UPGRADE_READINESS")
            region: Optional AWS region code. If not provided, uses the default region from AWS configuration
            
        Returns:
            EksInsightsResponse with insights information
        """
        # Extract values from Field objects before passing them to the implementation method
        cluster_name_value = cluster_name
        insight_id_value = insight_id
        category_value = category
        region_value = region
        
        # Delegate to the implementation method with extracted values
        return await self._get_eks_insights_impl(ctx, cluster_name_value, insight_id_value, category_value, region_value)
    
    async def _get_eks_insights_impl(
        self,
        ctx: Context,
        cluster_name: str,
        insight_id: Optional[str] = None,
        category: Optional[str] = None,
        region: Optional[str] = None
    ) -> EksInsightsResponse:
        """Internal implementation of get_eks_insights."""
        try:
            # Create EKS client - use region-specific if provided
            eks_client = self.eks_client
            if region:
                log_with_request_id(ctx, LogLevel.INFO, f"Using specified region: {region}")
                eks_client = AwsHelper.create_boto3_client('eks', region_name=region)
            
            # Determine operation mode based on whether insight_id is provided
            detail_mode = insight_id is not None
            
            if detail_mode:
                # Get details for a specific insight
                return await self._get_insight_detail(ctx, eks_client, cluster_name, insight_id)
            else:
                # List all insights with optional category filter
                return await self._list_insights(ctx, eks_client, cluster_name, category)
                
        except Exception as e:
            error_message = f"Error processing EKS insights request: {str(e)}"
            log_with_request_id(ctx, LogLevel.ERROR, error_message)
            return EksInsightsResponse(
                isError=True,
                content=[TextContent(type='text', text=error_message)],
                cluster_name=cluster_name,
                insights=[],
                detail_mode=(insight_id is not None)
            )
    
    async def _get_insight_detail(
        self,
        ctx: Context,
        eks_client,
        cluster_name: str,
        insight_id: str
    ) -> EksInsightsResponse:
        """Get details for a specific EKS insight."""
        log_with_request_id(ctx, LogLevel.INFO, f"Getting details for insight {insight_id} in cluster {cluster_name}")
        
        try:
            response = eks_client.describe_insight(
                id=insight_id, 
                clusterName=cluster_name
            )
            
            # Extract and format the insight details
            if 'insight' in response:
                insight_data = response['insight']
                
                # Create insight status object
                status_obj = EksInsightStatus(
                    status=insight_data.get('insightStatus', {}).get('status', 'UNKNOWN'),
                    reason=insight_data.get('insightStatus', {}).get('reason', '')
                )
                
                # Handle datetime objects for timestamps
                last_refresh_time = insight_data.get('lastRefreshTime', 0)
                if isinstance(last_refresh_time, datetime):
                    last_refresh_time = last_refresh_time.timestamp()
                    
                last_transition_time = insight_data.get('lastTransitionTime', 0)
                if isinstance(last_transition_time, datetime):
                    last_transition_time = last_transition_time.timestamp()
                
                # Convert insight to EksInsightItem format
                insight_item = EksInsightItem(
                    id=insight_data.get('id', ''),
                    name=insight_data.get('name', ''),
                    category=insight_data.get('category', ''),
                    kubernetes_version=insight_data.get('kubernetesVersion'),
                    last_refresh_time=last_refresh_time,
                    last_transition_time=last_transition_time,
                    description=insight_data.get('description', ''),
                    insight_status=status_obj,
                    recommendation=insight_data.get('recommendation'),
                    additional_info=insight_data.get('additionalInfo', {}),
                    resources=insight_data.get('resources', []),
                    category_specific_summary=insight_data.get('categorySpecificSummary', {})
                )
                
                success_message = f"Successfully retrieved details for insight {insight_id}"
                return EksInsightsResponse(
                    isError=False,
                    content=[TextContent(type='text', text=success_message)],
                    cluster_name=cluster_name,
                    insights=[insight_item],
                    detail_mode=True
                )
            else:
                error_message = f"No insight details found for ID {insight_id}"
                log_with_request_id(ctx, LogLevel.WARNING, error_message)
                return EksInsightsResponse(
                    isError=True,
                    content=[TextContent(type='text', text=error_message)],
                    cluster_name=cluster_name,
                    insights=[],
                    detail_mode=True
                )
                
        except Exception as e:
            error_message = f"Error retrieving insight details: {str(e)}"
            log_with_request_id(ctx, LogLevel.ERROR, error_message)
            return EksInsightsResponse(
                isError=True,
                content=[TextContent(type='text', text=error_message)],
                cluster_name=cluster_name,
                insights=[],
                detail_mode=True
            )
    
    async def _list_insights(
        self,
        ctx: Context,
        eks_client,
        cluster_name: str,
        category: Optional[str] = None
    ) -> EksInsightsResponse:
        """List EKS insights for a cluster with optional category filtering."""
        log_with_request_id(ctx, LogLevel.INFO, f"Listing insights for cluster {cluster_name}")
        
        try:
            # Build the list_insights parameters
            list_params = {
                'clusterName': cluster_name
            }
            
            # Add category filter if provided
            if category:
                log_with_request_id(ctx, LogLevel.INFO, f"Filtering insights by category: {category}")
                list_params['categories'] = [category]
            
            response = eks_client.list_insights(**list_params)
            
            # Extract and format the insights
            insight_items = []
            
            if 'insights' in response:
                for insight_data in response['insights']:
                    # Create insight status object
                    status_obj = EksInsightStatus(
                        status=insight_data.get('insightStatus', {}).get('status', 'UNKNOWN'),
                        reason=insight_data.get('insightStatus', {}).get('reason', '')
                    )
                    
                    # Handle datetime objects for timestamps
                    last_refresh_time = insight_data.get('lastRefreshTime', 0)
                    if isinstance(last_refresh_time, datetime):
                        last_refresh_time = last_refresh_time.timestamp()
                        
                    last_transition_time = insight_data.get('lastTransitionTime', 0)
                    if isinstance(last_transition_time, datetime):
                        last_transition_time = last_transition_time.timestamp()
                    
                    # Convert insight to EksInsightItem format
                    insight_item = EksInsightItem(
                        id=insight_data.get('id', ''),
                        name=insight_data.get('name', ''),
                        category=insight_data.get('category', ''),
                        kubernetes_version=insight_data.get('kubernetesVersion'),
                        last_refresh_time=last_refresh_time,
                        last_transition_time=last_transition_time,
                        description=insight_data.get('description', ''),
                        insight_status=status_obj,
                        # List mode doesn't include these fields
                        recommendation=None,
                        additional_info=None,
                        resources=None,
                        category_specific_summary=None
                    )
                    
                    insight_items.append(insight_item)
            
            success_message = f"Successfully retrieved {len(insight_items)} insights for cluster {cluster_name}"
            return EksInsightsResponse(
                isError=False,
                content=[TextContent(type='text', text=success_message)],
                cluster_name=cluster_name,
                insights=insight_items,
                next_token=response.get('nextToken'),
                detail_mode=False
            )
            
        except Exception as e:
            error_message = f"Error listing insights: {str(e)}"
            log_with_request_id(ctx, LogLevel.ERROR, error_message)
            return EksInsightsResponse(
                isError=True,
                content=[TextContent(type='text', text=error_message)],
                cluster_name=cluster_name,
                insights=[],
                detail_mode=False
            )
