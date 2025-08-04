"""
VPC topology discovery tool for CloudWAN MCP server.

This module provides tools for discovering and analyzing AWS VPC topology
including CloudWAN attachments, subnet organization, and interconnection patterns.
"""

import logging
import asyncio
from typing import Any, Dict, List, Optional
from pydantic import Field, BaseModel

from ...aws.client_manager import AWSClientManager
from ...config import CloudWANConfig
from ...models.base import AttachmentInfo
from ...models.network import VPCInfo, VPCDiscoveryResponse
from ..base import (
    BaseMCPTool,
    handle_errors,
    AWSOperationError,
    validate_regions,
)


class VPCTopologyInput(BaseModel):
    """Input schema for VPC topology discovery."""

    regions: Optional[List[str]] = Field(
        default=None,
        description="AWS regions to search in (default: all configured regions)",
    )
    include_tags: bool = Field(default=True, description="Include resource tags in the response")
    vpc_ids: Optional[List[str]] = Field(
        default=None, description="Specific VPC IDs to analyze (default: all VPCs)"
    )
    include_subnets: bool = Field(
        default=False, description="Include subnet details in the response"
    )
    include_cloudwan_attachments: bool = Field(
        default=True, description="Check for CloudWAN attachments"
    )
    include_transit_gateway_attachments: bool = Field(
        default=False, description="Check for Transit Gateway attachments"
    )


class SubnetInfo(BaseModel):
    """Subnet information."""

    subnet_id: str
    vpc_id: str
    cidr_block: str
    availability_zone: str
    state: str
    available_ip_address_count: Optional[int] = None
    default_for_az: bool = False
    map_public_ip_on_launch: bool = False
    tags: Dict[str, str] = Field(default_factory=dict)


class VPCTopologyTool(BaseMCPTool):
    """
    Tool for discovering and analyzing VPC topology.

    This tool discovers VPCs across AWS regions and analyzes their topology,
    including CloudWAN attachments, subnet organization, and interconnection
    patterns. It provides a comprehensive view of the network architecture and
    how it integrates with CloudWAN.
    """

    def __init__(self, aws_manager: AWSClientManager, config: CloudWANConfig):
        """Initialize VPCTopologyTool."""
        super().__init__(aws_manager, config)
        self.logger = logging.getLogger(self.__class__.__name__)

    @property
    def tool_name(self) -> str:
        """Get tool name for MCP registration."""
        return "discover_vpc_topology"

    @property
    def description(self) -> str:
        """Get tool description for MCP registration."""
        return (
            "Discover VPC topology and CloudWAN attachments.\n\n"
            "This tool discovers VPCs across AWS regions and analyzes their topology, "
            "including CloudWAN attachments, subnet organization, and interconnection "
            "patterns. It provides a comprehensive view of the network architecture and "
            "how it integrates with CloudWAN."
        )

    @property
    def input_schema(self) -> Dict[str, Any]:
        """Get input schema for MCP registration."""
        return VPCTopologyInput.model_json_schema()

    async def _discover_vpcs_in_region(
        self,
        region: str,
        vpc_ids: Optional[List[str]] = None,
        include_tags: bool = True,
    ) -> List[VPCInfo]:
        """
        Discover VPCs in a specific region.

        Args:
            region: AWS region to search in
            vpc_ids: Optional list of specific VPC IDs to discover
            include_tags: Whether to include resource tags

        Returns:
            List of VPCInfo objects

        Raises:
            AWSOperationError: If EC2 API operation fails
        """
        vpcs = []

        try:
            async with self.aws_manager.client_context("ec2", region) as client:
                # Prepare filters if specific VPC IDs are provided
                filters = [{"Name": "vpc-id", "Values": vpc_ids}] if vpc_ids else []

                # Get VPCs
                response = await client.describe_vpcs(Filters=filters)

                for vpc in response.get("Vpcs", []):
                    # Collect VPC CIDR blocks
                    cidr_block = vpc.get("CidrBlock", "")
                    additional_cidr_blocks = []

                    # Handle additional CIDRs if present
                    for association in vpc.get("CidrBlockAssociationSet", []):
                        cidr = association.get("CidrBlock")
                        if cidr and cidr != cidr_block:
                            additional_cidr_blocks.append(cidr)

                    # Extract tags if requested
                    tags = {}
                    if include_tags:
                        tags = {
                            t["Key"]: t["Value"]
                            for t in vpc.get("Tags", [])
                            if "Key" in t and "Value" in t
                        }

                    # Create VPCInfo object
                    vpc_info = VPCInfo(
                        vpc_id=vpc.get("VpcId", ""),
                        region=region,
                        cidr_block=cidr_block,
                        additional_cidr_blocks=additional_cidr_blocks,
                        state=vpc.get("State", ""),
                        is_default=vpc.get("IsDefault", False),
                        dhcp_options_id=vpc.get("DhcpOptionsId"),
                        instance_tenancy=vpc.get("InstanceTenancy", "default"),
                        attachments=[],  # Will be populated later
                        tags=tags,
                    )

                    vpcs.append(vpc_info)

        except Exception as e:
            self.logger.error(f"Error discovering VPCs in {region}: {e}")
            raise AWSOperationError(f"Error discovering VPCs in {region}: {e}")

        return vpcs

    async def _get_subnets_for_vpc(
        self, vpc_id: str, region: str, include_tags: bool = True
    ) -> List[SubnetInfo]:
        """
        Get subnets for a specific VPC.

        Args:
            vpc_id: VPC ID to get subnets for
            region: AWS region
            include_tags: Whether to include resource tags

        Returns:
            List of SubnetInfo objects

        Raises:
            AWSOperationError: If EC2 API operation fails
        """
        subnets = []

        try:
            async with self.aws_manager.client_context("ec2", region) as client:
                response = await client.describe_subnets(
                    Filters=[{"Name": "vpc-id", "Values": [vpc_id]}]
                )

                for subnet in response.get("Subnets", []):
                    # Extract tags if requested
                    tags = {}
                    if include_tags:
                        tags = {
                            t["Key"]: t["Value"]
                            for t in subnet.get("Tags", [])
                            if "Key" in t and "Value" in t
                        }

                    # Create SubnetInfo object
                    subnet_info = SubnetInfo(
                        subnet_id=subnet.get("SubnetId", ""),
                        vpc_id=vpc_id,
                        cidr_block=subnet.get("CidrBlock", ""),
                        availability_zone=subnet.get("AvailabilityZone", ""),
                        state=subnet.get("State", ""),
                        available_ip_address_count=subnet.get("AvailableIpAddressCount"),
                        default_for_az=subnet.get("DefaultForAz", False),
                        map_public_ip_on_launch=subnet.get("MapPublicIpOnLaunch", False),
                        tags=tags,
                    )

                    subnets.append(subnet_info)

        except Exception as e:
            self.logger.error(f"Error getting subnets for VPC {vpc_id} in {region}: {e}")
            raise AWSOperationError(f"Error getting subnets for VPC {vpc_id} in {region}: {e}")

        return subnets

    async def _get_cloudwan_attachments_for_vpcs(
        self, vpc_ids: List[str], region: str
    ) -> Dict[str, List[AttachmentInfo]]:
        """
        Get CloudWAN attachments for specific VPCs.

        Args:
            vpc_ids: List of VPC IDs to check for attachments
            region: AWS region

        Returns:
            Dictionary mapping VPC IDs to lists of AttachmentInfo objects

        Raises:
            AWSOperationError: If Network Manager API operation fails
        """
        attachments_by_vpc = {vpc_id: [] for vpc_id in vpc_ids}

        try:
            async with self.aws_manager.client_context("networkmanager", region) as client:
                # List core networks
                core_networks_response = await client.list_core_networks()

                for core_network in core_networks_response.get("CoreNetworks", []):
                    core_network_id = core_network.get("CoreNetworkId")

                    # Get attachments for this core network
                    paginator = client.get_paginator("list_attachments")
                    page_iterator = paginator.paginate(
                        CoreNetworkId=core_network_id, AttachmentType="VPC"
                    )

                    async for page in page_iterator:
                        for attachment in page.get("Attachments", []):
                            # Check if this attachment is for any of our VPCs
                            resource_arn = attachment.get("ResourceArn", "")

                            for vpc_id in vpc_ids:
                                if vpc_id in resource_arn:
                                    # Create AttachmentInfo object
                                    attachment_info = AttachmentInfo(
                                        attachment_id=attachment.get("AttachmentId", ""),
                                        attachment_type=attachment.get("AttachmentType", ""),
                                        state=attachment.get("State", ""),
                                        resource_arn=resource_arn,
                                        core_network_id=core_network_id,
                                        segment_name=attachment.get("SegmentName"),
                                        edge_location=attachment.get("EdgeLocation"),
                                        tags={
                                            t["Key"]: t["Value"]
                                            for t in attachment.get("Tags", [])
                                            if "Key" in t and "Value" in t
                                        },
                                    )

                                    # Add to VPC's attachments
                                    attachments_by_vpc[vpc_id].append(attachment_info)

        except Exception as e:
            self.logger.error(f"Error getting CloudWAN attachments: {e}")
            # Don't fail the entire operation if this part fails
            self.logger.warning("Continuing without CloudWAN attachment information")

        return attachments_by_vpc

    async def _get_transit_gateway_attachments_for_vpcs(
        self, vpc_ids: List[str], region: str
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get Transit Gateway attachments for specific VPCs.

        Args:
            vpc_ids: List of VPC IDs to check for attachments
            region: AWS region

        Returns:
            Dictionary mapping VPC IDs to lists of TGW attachment dictionaries

        Raises:
            AWSOperationError: If EC2 API operation fails
        """
        attachments_by_vpc = {vpc_id: [] for vpc_id in vpc_ids}

        try:
            async with self.aws_manager.client_context("ec2", region) as client:
                # Describe Transit Gateway VPC attachments
                response = await client.describe_transit_gateway_vpc_attachments(
                    Filters=[{"Name": "vpc-id", "Values": vpc_ids}]
                )

                for attachment in response.get("TransitGatewayVpcAttachments", []):
                    vpc_id = attachment.get("VpcId")
                    if vpc_id in vpc_ids:
                        attachments_by_vpc[vpc_id].append(attachment)

        except Exception as e:
            self.logger.error(f"Error getting Transit Gateway attachments: {e}")
            # Don't fail the entire operation if this part fails
            self.logger.warning("Continuing without Transit Gateway attachment information")

        return attachments_by_vpc

    async def _process_region_vpc_topology(
        self,
        region: str,
        vpc_ids: Optional[List[str]] = None,
        include_tags: bool = True,
        include_subnets: bool = False,
        include_cloudwan_attachments: bool = True,
        include_transit_gateway_attachments: bool = False,
    ) -> Dict[str, Any]:
        """
        Process VPC topology for a specific region.

        Args:
            region: AWS region
            vpc_ids: Optional list of specific VPC IDs to analyze
            include_tags: Whether to include resource tags
            include_subnets: Whether to include subnet details
            include_cloudwan_attachments: Whether to check for CloudWAN attachments
            include_transit_gateway_attachments: Whether to check for TGW attachments

        Returns:
            Dictionary with region results
        """
        results = {
            "region": region,
            "vpcs": [],
            "subnets_by_vpc": {},
            "cloudwan_attachments": [],
            "tgw_attachments": [],
        }

        try:
            # Discover VPCs in this region
            vpcs = await self._discover_vpcs_in_region(
                region=region, vpc_ids=vpc_ids, include_tags=include_tags
            )

            # If we found VPCs, process additional details
            if vpcs:
                # Get VPC IDs
                discovered_vpc_ids = [vpc.vpc_id for vpc in vpcs]

                # Process subnets if requested
                if include_subnets:
                    for vpc_id in discovered_vpc_ids:
                        results["subnets_by_vpc"][vpc_id] = await self._get_subnets_for_vpc(
                            vpc_id=vpc_id, region=region, include_tags=include_tags
                        )

                # Process CloudWAN attachments if requested
                if include_cloudwan_attachments:
                    attachments_by_vpc = await self._get_cloudwan_attachments_for_vpcs(
                        vpc_ids=discovered_vpc_ids, region=region
                    )

                    # Add attachments to VPC objects and collect all attachments
                    for vpc in vpcs:
                        vpc_attachments = attachments_by_vpc.get(vpc.vpc_id, [])
                        vpc.attachments = vpc_attachments
                        results["cloudwan_attachments"].extend(vpc_attachments)

                # Process Transit Gateway attachments if requested
                if include_transit_gateway_attachments:
                    tgw_attachments_by_vpc = await self._get_transit_gateway_attachments_for_vpcs(
                        vpc_ids=discovered_vpc_ids, region=region
                    )

                    # Collect all TGW attachments
                    for vpc_id, attachments in tgw_attachments_by_vpc.items():
                        results["tgw_attachments"].extend(attachments)

                # Add VPCs to results
                results["vpcs"] = vpcs

        except Exception as e:
            self.logger.error(f"Error processing VPC topology in {region}: {e}")

        return results

    @handle_errors
    async def execute(self, **kwargs) -> VPCDiscoveryResponse:
        """
        Execute the VPC topology discovery tool.

        Args:
            **kwargs: Tool parameters
                - regions: Optional list of AWS regions to search
                - vpc_ids: Optional list of specific VPC IDs to analyze
                - include_tags: Whether to include resource tags
                - include_subnets: Whether to include subnet details
                - include_cloudwan_attachments: Whether to check for CloudWAN attachments
                - include_transit_gateway_attachments: Whether to check for TGW attachments

        Returns:
            VPCDiscoveryResponse with VPC topology information
        """
        # Parse and validate input
        input_model = VPCTopologyInput(**kwargs)

        # Validate regions
        regions = validate_regions(input_model.regions, self.config)

        # Process each region
        tasks = []
        for region in regions:
            tasks.append(
                self._process_region_vpc_topology(
                    region=region,
                    vpc_ids=input_model.vpc_ids,
                    include_tags=input_model.include_tags,
                    include_subnets=input_model.include_subnets,
                    include_cloudwan_attachments=input_model.include_cloudwan_attachments,
                    include_transit_gateway_attachments=input_model.include_transit_gateway_attachments,
                )
            )

        # Process all results
        region_results = await asyncio.gather(*tasks, return_exceptions=True)

        # Combine results from all regions
        all_vpcs = []
        all_cloudwan_attachments = []
        all_subnets_by_vpc = {}
        successful_regions = []
        failed_regions = []

        for result in region_results:
            if isinstance(result, Exception):
                self.logger.error(f"Error in region processing: {result}")
                continue

            all_vpcs.extend(result["vpcs"])
            all_cloudwan_attachments.extend(result["cloudwan_attachments"])
            all_subnets_by_vpc.update(result["subnets_by_vpc"])
            successful_regions.append(result["region"])

            # Include additional subnet information in response metadata
            if input_model.include_subnets and result["subnets_by_vpc"]:
                for vpc_id, subnets in result["subnets_by_vpc"].items():
                    # Add subnet count to VPC objects
                    for vpc in result["vpcs"]:
                        if vpc.vpc_id == vpc_id:
                            vpc.subnet_count = len(subnets)
                            break

        # Create response
        response = VPCDiscoveryResponse(
            vpcs=all_vpcs,
            total_count=len(all_vpcs),
            regions_searched=regions,
            cloudwan_attachments=all_cloudwan_attachments,
            regions_analyzed=successful_regions,
            status="success" if all_vpcs else "partial",
            error_message=None if all_vpcs else "No VPCs found in specified regions",
        )

        # Add subnet information to response if requested
        if input_model.include_subnets:
            # Add subnets as an additional field in the response model
            response.subnets_by_vpc = all_subnets_by_vpc

        return response
