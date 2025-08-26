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

"""VPC Configuration handler for the EKS MCP Server."""

from awslabs.eks_mcp_server.aws_helper import AwsHelper
from awslabs.eks_mcp_server.logging_helper import LogLevel, log_with_request_id
from awslabs.eks_mcp_server.models import EksVpcConfigResponse
from mcp.server.fastmcp import Context
from mcp.types import TextContent
from pydantic import Field
from typing import Optional


class VpcConfigHandler:
    """Handler for Amazon EKS VPC configuration.

    This class provides tools for retrieving and analyzing VPC configurations
    for EKS clusters, with special support for hybrid node setups.
    """

    def __init__(
        self,
        mcp,
        allow_sensitive_data_access: bool = False,
    ):
        """Initialize the VPC Config handler.

        Args:
            mcp: The MCP server instance
            allow_sensitive_data_access: Whether to allow access to sensitive data (default: False)
        """
        self.mcp = mcp
        self.allow_sensitive_data_access = allow_sensitive_data_access

        # Register tools
        self.mcp.tool(name='get_eks_vpc_config')(self.get_eks_vpc_config)

        # Initialize AWS clients
        self.ec2_client = AwsHelper.create_boto3_client('ec2')
        self.eks_client = AwsHelper.create_boto3_client('eks')

    # VPC tool
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

        ## Requirements
        - The server must be run with the `--allow-sensitive-data-access` flag

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

    async def _get_vpc_id_for_cluster(self, ctx: Context, cluster_name: str) -> tuple[str, dict]:
        """Get the VPC ID for a cluster.

        Args:
            ctx: MCP context
            cluster_name: Name of the EKS cluster

        Returns:
            Tuple of (vpc_id, cluster_response)

        Raises:
            Exception: If the VPC ID cannot be determined
        """
        # Get cluster information to determine VPC ID
        cluster_response = self.eks_client.describe_cluster(name=cluster_name)
        vpc_id = cluster_response['cluster'].get('resourcesVpcConfig', {}).get('vpcId')

        if not vpc_id:
            error_message = f'Could not determine VPC ID for cluster {cluster_name}'
            log_with_request_id(ctx, LogLevel.ERROR, error_message)
            raise Exception(error_message)

        return vpc_id, cluster_response

    async def _get_vpc_details(self, ctx: Context, vpc_id: str) -> tuple[str, list[str]]:
        """Get VPC details using the VPC ID.

        Args:
            ctx: MCP context
            vpc_id: ID of the VPC to query

        Returns:
            Tuple of (cidr_block, additional_cidr_blocks)

        Raises:
            Exception: If the VPC is not found
        """
        # Get VPC details
        vpc_response = self.ec2_client.describe_vpcs(VpcIds=[vpc_id])

        if not vpc_response['Vpcs']:
            error_message = f'VPC {vpc_id} not found'
            log_with_request_id(ctx, LogLevel.ERROR, error_message)
            raise Exception(error_message)

        # Extract VPC information
        vpc = vpc_response['Vpcs'][0]
        cidr_block = vpc.get('CidrBlock', '')
        additional_cidr_blocks = [
            cidr_association.get('CidrBlock', '')
            for cidr_association in vpc.get('CidrBlockAssociationSet', [])[1:]
            if 'CidrBlock' in cidr_association
        ]

        return cidr_block, additional_cidr_blocks

    async def _get_subnet_information(self, ctx: Context, vpc_id: str) -> list[dict]:
        """Get subnet information for a VPC.

        Args:
            ctx: MCP context
            vpc_id: ID of the VPC to query

        Returns:
            List of subnet information dictionaries
        """
        # Get subnets for the VPC
        subnets_response = self.ec2_client.describe_subnets(
            Filters=[{'Name': 'vpc-id', 'Values': [vpc_id]}]
        )

        subnets = []
        for subnet in subnets_response.get('Subnets', []):
            # Extract all subnet information to variables first
            subnet_id = subnet.get('SubnetId', '')
            subnet_cidr_block = subnet.get('CidrBlock', '')
            az_id = subnet.get('AvailabilityZoneId', '')
            az_name = subnet.get('AvailabilityZone', '')
            available_ips = subnet.get('AvailableIpAddressCount', 0)
            is_public = subnet.get('MapPublicIpOnLaunch', False)
            assign_ipv6 = subnet.get('AssignIpv6AddressOnCreation', False)

            # Check for disallowed AZs
            disallowed_azs = ['use1-az3', 'usw1-az2', 'cac1-az3']
            in_disallowed_az = az_id in disallowed_azs
            has_sufficient_ips = available_ips >= 16  # AWS recommends 16

            # Store subnet information
            subnet_info = {
                'subnet_id': subnet_id,
                'cidr_block': subnet_cidr_block,
                'az_id': az_id,
                'az_name': az_name,
                'available_ips': available_ips,
                'is_public': is_public,
                'assign_ipv6': assign_ipv6,
                'in_disallowed_az': in_disallowed_az,
                'has_sufficient_ips': has_sufficient_ips,
            }
            subnets.append(subnet_info)

        return subnets

    async def _get_route_table_information(self, ctx: Context, vpc_id: str) -> list[dict]:
        """Get route table information for a VPC.

        Args:
            ctx: MCP context
            vpc_id: ID of the VPC to query

        Returns:
            List of route information dictionaries
        """
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

                    for target_field in [
                        'GatewayId',
                        'NatGatewayId',
                        'TransitGatewayId',
                        'NetworkInterfaceId',
                        'VpcPeeringConnectionId',
                    ]:
                        if target_field in route and route[target_field]:
                            target_type = target_field.replace('Id', '').lower()
                            target_id = route[target_field]
                            break

                    route_info = {
                        'destination_cidr_block': route.get('DestinationCidrBlock', ''),
                        'target_type': target_type or 'unknown',
                        'target_id': target_id or 'unknown',
                        'state': route.get('State', ''),
                    }
                    routes.append(route_info)

        return routes

    async def _get_remote_cidr_blocks(
        self, ctx: Context, cluster_name: str, cluster_response: Optional[dict] = None
    ) -> tuple[list[str], list[str]]:
        """Get remote node and pod CIDR blocks.

        Args:
            ctx: MCP context
            cluster_name: Name of the EKS cluster
            cluster_response: Cluster response from a previous API call

        Returns:
            Tuple of (remote_node_cidr_blocks, remote_pod_cidr_blocks)
        """
        remote_node_cidr_blocks = []
        remote_pod_cidr_blocks = []

        # Extract remote network config from the cluster response
        if cluster_response and 'cluster' in cluster_response:
            if 'remoteNetworkConfig' in cluster_response['cluster']:
                remote_config = cluster_response['cluster']['remoteNetworkConfig']

                # Extract remote node CIDRs
                if 'remoteNodeNetworks' in remote_config:
                    for network in remote_config['remoteNodeNetworks']:
                        if 'cidrs' in network:
                            for cidr in network['cidrs']:
                                if cidr not in remote_node_cidr_blocks:
                                    remote_node_cidr_blocks.append(cidr)
                                    log_with_request_id(
                                        ctx,
                                        LogLevel.INFO,
                                        f'Found remote node CIDR in remoteNetworkConfig: {cidr}',
                                    )

                # Extract remote pod CIDRs
                if 'remotePodNetworks' in remote_config:
                    for network in remote_config['remotePodNetworks']:
                        if 'cidrs' in network:
                            for cidr in network['cidrs']:
                                if cidr not in remote_pod_cidr_blocks:
                                    remote_pod_cidr_blocks.append(cidr)
                                    log_with_request_id(
                                        ctx,
                                        LogLevel.INFO,
                                        f'Found remote pod CIDR in remoteNetworkConfig: {cidr}',
                                    )

        # Log summary of detected CIDRs
        if remote_node_cidr_blocks:
            log_with_request_id(
                ctx,
                LogLevel.INFO,
                f'Detected remote node CIDRs: {", ".join(remote_node_cidr_blocks)}',
            )
        else:
            log_with_request_id(ctx, LogLevel.WARNING, 'No remote node CIDRs detected')

        if remote_pod_cidr_blocks:
            log_with_request_id(
                ctx,
                LogLevel.INFO,
                f'Detected remote pod CIDRs: {", ".join(remote_pod_cidr_blocks)}',
            )
        else:
            log_with_request_id(ctx, LogLevel.WARNING, 'No remote pod CIDRs detected')

        return remote_node_cidr_blocks, remote_pod_cidr_blocks

    async def _get_eks_vpc_config_impl(
        self, ctx: Context, cluster_name: str, vpc_id: Optional[str] = None
    ) -> EksVpcConfigResponse:
        """Internal implementation of get_eks_vpc_config."""
        try:
            # Always get the cluster response for remote CIDR information
            cluster_response = None
            try:
                if not vpc_id:
                    # Get both VPC ID and cluster response
                    vpc_id, cluster_response = await self._get_vpc_id_for_cluster(
                        ctx, cluster_name
                    )
                else:
                    # Just get the cluster response when VPC ID is provided
                    _, cluster_response = await self._get_vpc_id_for_cluster(ctx, cluster_name)
            except Exception as eks_error:
                error_message = f'Error getting cluster information: {str(eks_error)}'
                log_with_request_id(ctx, LogLevel.ERROR, error_message)
                return EksVpcConfigResponse(
                    isError=True,
                    content=[TextContent(type='text', text=error_message)],
                    vpc_id='',
                    cidr_block='',
                    additional_cidr_blocks=[],  # Add missing parameter
                    routes=[],
                    remote_node_cidr_blocks=[],
                    remote_pod_cidr_blocks=[],
                    subnets=[],
                    cluster_name=cluster_name,
                )

            try:
                # Get VPC details
                cidr_block, additional_cidr_blocks = await self._get_vpc_details(ctx, vpc_id)

                # Get subnet information
                subnets = await self._get_subnet_information(ctx, vpc_id)

                # Get route table information
                routes = await self._get_route_table_information(ctx, vpc_id)

                # Get remote CIDR blocks
                (
                    remote_node_cidr_blocks,
                    remote_pod_cidr_blocks,
                ) = await self._get_remote_cidr_blocks(ctx, cluster_name, cluster_response)

                # Create the response
                success_message = (
                    f'Retrieved VPC configuration for {vpc_id} (cluster {cluster_name})'
                )
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
                    cluster_name=cluster_name,
                )
            except Exception as e:
                error_message = f'Error retrieving VPC configuration: {str(e)}'
                log_with_request_id(ctx, LogLevel.ERROR, error_message)
                return EksVpcConfigResponse(
                    isError=True,
                    content=[TextContent(type='text', text=error_message)],
                    vpc_id='',
                    cidr_block='',
                    additional_cidr_blocks=[],  # Add missing parameter
                    routes=[],
                    remote_node_cidr_blocks=[],
                    remote_pod_cidr_blocks=[],
                    subnets=[],
                    cluster_name=cluster_name,
                )

        except Exception as e:
            error_message = f'Error retrieving VPC configuration: {str(e)}'
            log_with_request_id(ctx, LogLevel.ERROR, error_message)
            return EksVpcConfigResponse(
                isError=True,
                content=[TextContent(type='text', text=error_message)],
                vpc_id='',
                cidr_block='',
                additional_cidr_blocks=[],  # Add missing parameter
                routes=[],
                remote_node_cidr_blocks=[],
                remote_pod_cidr_blocks=[],
                subnets=[],
                cluster_name=cluster_name,
            )
