"""Enhanced network path tracing for CloudWAN MCP Server.

This module provides comprehensive path tracing capabilities for CloudWAN networks,
including IP discovery, segment resolution, and Transit Gateway analysis.
"""

import asyncio
import ipaddress
import logging
from typing import Dict, List, Any
import json


from mcp.types import TextContent

from ...aws.client_manager import AWSClientManager
from ..base import BaseMCPTool
from ...config import CloudWANConfig
from ...utils.aws_operations import (
    handle_aws_errors,
    aws_client_context,
)


class EnhancedNetworkPathTracingTool(BaseMCPTool):
    """Enhanced tool for tracing network paths between IP addresses."""

    def __init__(self, aws_manager: AWSClientManager, config: CloudWANConfig = None):
        super().__init__(aws_manager, config or CloudWANConfig())
        self._tool_name = "enhanced_trace_network_path"
        self._description = "Trace network path between two IP addresses with detailed hop analysis"
        self.logger = logging.getLogger(__name__)

    @property
    def tool_name(self) -> str:
        return self._tool_name

    @property
    def description(self) -> str:
        return self._description

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "source_ip": {"type": "string", "description": "Source IP address"},
                "destination_ip": {
                    "type": "string",
                    "description": "Destination IP address",
                },
                "protocol": {
                    "type": "string",
                    "enum": ["tcp", "udp", "icmp"],
                    "description": "Protocol for the connection",
                    "default": "tcp",
                },
                "port": {
                    "type": "integer",
                    "description": "Destination port for TCP/UDP",
                    "default": 443,
                },
                "regions": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "AWS regions to search (default: all configured regions)",
                    "default": [],
                },
                "detailed": {
                    "type": "boolean",
                    "description": "Include detailed hop analysis and security checks",
                    "default": True,
                },
                "skip_security_checks": {
                    "type": "boolean",
                    "description": "Skip security group and NACL evaluation",
                    "default": False,
                },
            },
            "required": ["source_ip", "destination_ip"],
        }

    @handle_aws_errors("Network path tracing")
    async def execute(self, **kwargs) -> List[TextContent]:
        """Execute network path tracing."""
        source_ip = kwargs["source_ip"]
        destination_ip = kwargs["destination_ip"]
        protocol = kwargs.get("protocol", "tcp")
        port = kwargs.get("port", 443)
        regions = kwargs.get("regions") or self.config.aws.regions
        detailed = kwargs.get("detailed", True)
        skip_security_checks = kwargs.get("skip_security_checks", False)

        # Validate IP addresses
        try:
            ipaddress.ip_address(source_ip)
            ipaddress.ip_address(destination_ip)
        except ValueError as e:
            return [TextContent(type="text", text=f"Error: Invalid IP address format: {str(e)}")]

        self.logger.info(f"Starting path trace from {source_ip} to {destination_ip}")

        try:
            # Step 1: Find IP contexts
            source_context = await self._find_ip_context(source_ip, regions)
            destination_context = await self._find_ip_context(destination_ip, regions)

            # Step 2: Discover Core Networks
            core_networks = await self._discover_core_networks()

            # Step 3: Analyze TGWs in relevant regions
            tgw_regions = set([source_context.get("region"), destination_context.get("region")])
            tgw_regions = [r for r in tgw_regions if r]  # Remove None values

            tgw_analysis = {}
            for region in tgw_regions:
                tgw_analysis[region] = await self._analyze_transit_gateways_in_region(region)

            # Step 4: Find routing
            routing_analysis = {}
            if source_context.get("found") and source_context.get("route_tables"):
                matching_routes = self._find_matching_routes(
                    destination_ip, source_context["route_tables"]
                )
                routing_analysis = {
                    "matching_routes": matching_routes,
                    "route_count": len(matching_routes),
                }

            # Step 5: Determine path type and connection method
            path_analysis = self._analyze_path(source_context, destination_context)

            # Compile results
            analysis_result = {
                "source_ip": source_ip,
                "destination_ip": destination_ip,
                "source_context": source_context,
                "destination_context": destination_context,
                "core_networks": core_networks,
                "transit_gateway_analysis": tgw_analysis,
                "routing_analysis": routing_analysis,
                "path_analysis": path_analysis,
                "protocol": protocol,
                "port": port,
            }

            # Convert to JSON response
            # For a rich output, you could also format this better with tables, etc.
            result_json = json.dumps(analysis_result, default=str, indent=2)

            return [TextContent(type="text", text=result_json)]

        except Exception as e:
            self.logger.error(f"Path tracing failed: {e}", exc_info=True)
            return [TextContent(type="text", text=f"Error: Failed to trace network path: {str(e)}")]

    async def _find_ip_context(self, ip_address: str, regions: List[str]) -> Dict[str, Any]:
        """Find IP context across all regions."""
        self.logger.info(f"Searching for IP {ip_address} across regions: {', '.join(regions)}")

        # Search across regions concurrently
        results = await asyncio.gather(
            *[self._find_ip_in_region(region, ip_address) for region in regions]
        )

        # Find first result where IP was found
        for result in results:
            if result.get("found"):
                self.logger.info(f"Found IP {ip_address} in region {result.get('region')}")
                return result

        self.logger.warning(f"IP {ip_address} not found in any region")
        return {"found": False}

    async def _find_ip_in_region(self, region: str, ip_address: str) -> Dict[str, Any]:
        """Find IP address context in a specific region."""
        try:
            with aws_client_context(self.aws_manager, "ec2", region) as ec2_client:
                # Search for ENIs with this private IP
                response = await ec2_client.describe_network_interfaces(
                    Filters=[{"Name": "private-ip-address", "Values": [ip_address]}]
                )

                if response.get("NetworkInterfaces"):
                    eni = response["NetworkInterfaces"][0]

                    # Get VPC and subnet info
                    vpc_id = eni.get("VpcId")
                    subnet_id = eni.get("SubnetId")

                    # Get route tables for this subnet
                    route_tables = await self._get_route_tables_for_subnet(ec2_client, subnet_id)

                    # Get VPC details
                    vpc_info = await self._get_vpc_details(ec2_client, vpc_id)

                    # Get CloudWAN segment information
                    segment_info = await self._get_cloudwan_segment_for_vpc(vpc_id, region)

                    return {
                        "found": True,
                        "region": region,
                        "vpc_id": vpc_id,
                        "subnet_id": subnet_id,
                        "eni_id": eni.get("NetworkInterfaceId"),
                        "availability_zone": eni.get("AvailabilityZone"),
                        "description": eni.get("Description", ""),
                        "status": eni.get("Status"),
                        "route_tables": route_tables,
                        "vpc_info": vpc_info,
                        "segment_info": segment_info,
                    }

                return {"found": False, "region": region}

        except Exception as e:
            self.logger.error(f"Error searching for IP {ip_address} in region {region}: {e}")
            return {"found": False, "region": region, "error": str(e)}

    async def _get_vpc_details(self, ec2_client, vpc_id: str) -> Dict[str, Any]:
        """Get VPC details."""
        try:
            response = await ec2_client.describe_vpcs(VpcIds=[vpc_id])
            if response.get("Vpcs"):
                vpc = response["Vpcs"][0]
                return {
                    "cidr_block": vpc.get("CidrBlock"),
                    "state": vpc.get("State"),
                    "is_default": vpc.get("IsDefault", False),
                    "tags": {tag["Key"]: tag["Value"] for tag in vpc.get("Tags", [])},
                }
        except Exception as e:
            self.logger.warning(f"Could not get VPC details for {vpc_id}: {e}")

        return {}

    async def _get_cloudwan_segment_for_vpc(self, vpc_id: str, region: str) -> Dict[str, Any]:
        """Find which CloudWAN segment a VPC belongs to."""
        try:
            # Use us-west-2 for NetworkManager API calls
            with aws_client_context(self.aws_manager, "networkmanager", "us-west-2") as nm_client:
                # First, get all core networks
                core_networks_response = await nm_client.list_core_networks()

                for core_network in core_networks_response.get("CoreNetworks", []):
                    core_network_id = core_network.get("CoreNetworkId")

                    try:
                        # Get VPC attachments for this core network
                        attachments_response = await nm_client.list_attachments(
                            CoreNetworkId=core_network_id, AttachmentType="VPC"
                        )

                        # Check if our VPC is attached
                        for attachment in attachments_response.get("Attachments", []):
                            if (
                                attachment.get("ResourceArn", "").endswith(f"/{vpc_id}")
                                and attachment.get("EdgeLocation") == region
                            ):

                                # Get segment name from attachment
                                segment_name = attachment.get("SegmentName", "Unknown")
                                attachment_id = attachment.get("AttachmentId")
                                state = attachment.get("State")

                                return {
                                    "segment_name": segment_name,
                                    "core_network_id": core_network_id,
                                    "attachment_id": attachment_id,
                                    "state": state,
                                    "edge_location": region,
                                    "found": True,
                                }

                    except Exception as e:
                        self.logger.warning(
                            f"Could not get attachments for core network {core_network_id}: {e}"
                        )
                        continue

                return {
                    "found": False,
                    "segment_name": "Not Attached",
                    "core_network_id": None,
                }

        except Exception as e:
            self.logger.warning(f"Could not discover CloudWAN segment for VPC {vpc_id}: {e}")
            return {"found": False, "segment_name": "Unknown", "core_network_id": None}

    async def _get_route_tables_for_subnet(
        self, ec2_client, subnet_id: str
    ) -> List[Dict[str, Any]]:
        """Get route tables associated with a subnet."""
        try:
            # Get route tables associated with the subnet
            response = await ec2_client.describe_route_tables(
                Filters=[{"Name": "association.subnet-id", "Values": [subnet_id]}]
            )

            route_tables = []
            for rt in response.get("RouteTables", []):
                routes = []
                for route in rt.get("Routes", []):
                    target = (
                        route.get("GatewayId")
                        or route.get("TransitGatewayId")
                        or route.get("NetworkInterfaceId")
                        or route.get("VpcPeeringConnectionId")
                        or route.get("NatGatewayId")
                        or "local"
                    )

                    routes.append(
                        {
                            "destination_cidr": route.get("DestinationCidrBlock", ""),
                            "target": target,
                            "state": route.get("State"),
                            "origin": route.get("Origin"),
                        }
                    )

                route_tables.append(
                    {
                        "route_table_id": rt.get("RouteTableId"),
                        "routes": routes,
                        "main": any(
                            assoc.get("Main", False) for assoc in rt.get("Associations", [])
                        ),
                    }
                )

            return route_tables

        except Exception as e:
            self.logger.warning(f"Could not get route tables for subnet {subnet_id}: {e}")
            return []

    async def _discover_core_networks(self) -> List[Dict[str, Any]]:
        """Discover Core Networks using Network Manager."""
        try:
            with aws_client_context(self.aws_manager, "networkmanager", "us-west-2") as nm_client:
                self.logger.info("Discovering Core Networks...")
                response = await nm_client.list_core_networks()

                core_networks = []
                for cn in response.get("CoreNetworks", []):
                    core_networks.append(
                        {
                            "core_network_id": cn.get("CoreNetworkId"),
                            "global_network_id": cn.get("GlobalNetworkId"),
                            "state": cn.get("State"),
                            "description": cn.get("Description", ""),
                            "policy_version_id": cn.get("PolicyVersionId"),
                        }
                    )

                self.logger.info(f"Found {len(core_networks)} Core Networks")
                return core_networks

        except Exception as e:
            self.logger.error(f"Core Network discovery failed: {e}")
            return []

    async def _analyze_transit_gateways_in_region(self, region: str) -> Dict[str, Any]:
        """Analyze Transit Gateways in a specific region."""
        try:
            with aws_client_context(self.aws_manager, "ec2", region) as ec2_client:
                # Get Transit Gateways
                response = await ec2_client.describe_transit_gateways()
                tgws = response.get("TransitGateways", [])

                tgw_analysis = []
                for tgw in tgws:
                    tgw_id = tgw.get("TransitGatewayId")

                    # Get TGW name from tags
                    tgw_name = tgw_id
                    for tag in tgw.get("Tags", []):
                        if tag.get("Key", "").lower() == "name":
                            tgw_name = tag.get("Value", tgw_id)
                            break

                    # Get peering attachments
                    peering_response = (
                        await ec2_client.describe_transit_gateway_peering_attachments(
                            Filters=[{"Name": "transit-gateway-id", "Values": [tgw_id]}]
                        )
                    )
                    peering_count = len(
                        peering_response.get("TransitGatewayPeeringAttachments", [])
                    )

                    tgw_analysis.append(
                        {
                            "transit_gateway_id": tgw_id,
                            "name": tgw_name,
                            "state": tgw.get("State"),
                            "asn": tgw.get("Options", {}).get("AmazonSideAsn"),
                            "peering_connections": peering_count,
                            "region": region,
                        }
                    )

                return {
                    "region": region,
                    "transit_gateways": tgw_analysis,
                    "count": len(tgw_analysis),
                }

        except Exception as e:
            self.logger.error(f"TGW analysis failed in region {region}: {e}")
            return {
                "region": region,
                "transit_gateways": [],
                "count": 0,
                "error": str(e),
            }

    def _find_matching_routes(
        self, destination_ip: str, route_tables: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Find routes that match the destination IP."""
        matching_routes = []
        dest_ip = ipaddress.ip_address(destination_ip)

        for rt in route_tables:
            for route in rt.get("routes", []):
                dest_cidr = route.get("destination_cidr", "")
                if dest_cidr and dest_cidr != "0.0.0.0/0":
                    try:
                        network = ipaddress.ip_network(dest_cidr, strict=False)
                        if dest_ip in network:
                            matching_routes.append(
                                {
                                    "route_table_id": rt.get("route_table_id"),
                                    "destination_cidr": dest_cidr,
                                    "target": route.get("target"),
                                    "state": route.get("state"),
                                    "origin": route.get("origin"),
                                    "prefix_length": network.prefixlen,
                                    "is_main_table": rt.get("main", False),
                                }
                            )
                    except ValueError:
                        continue

        # Sort by most specific (longest prefix)
        matching_routes.sort(key=lambda x: x.get("prefix_length", 0), reverse=True)
        return matching_routes

    def _analyze_path(
        self, source_context: Dict[str, Any], dest_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Analyze the path between source and destination."""
        path_summary = {}

        # Connectivity status
        if source_context.get("found") and dest_context.get("found"):
            if source_context.get("vpc_id") == dest_context.get("vpc_id"):
                path_summary["path_type"] = "Intra-VPC communication"
            elif source_context.get("region") == dest_context.get("region"):
                path_summary["path_type"] = "Inter-VPC, same region"
            else:
                path_summary["path_type"] = "Inter-VPC, cross-region"

            # Add CloudWAN segment analysis
            source_segment = source_context.get("segment_info", {}).get("segment_name", "Unknown")
            dest_segment = dest_context.get("segment_info", {}).get("segment_name", "Unknown")

            if source_segment != "Unknown" and dest_segment != "Unknown":
                if source_segment == dest_segment:
                    path_summary["cloudwan_path_type"] = "Intra-segment"
                    path_summary["cloudwan_segments"] = source_segment
                else:
                    path_summary["cloudwan_path_type"] = "Inter-segment"
                    path_summary["cloudwan_segments"] = f"{source_segment} → {dest_segment}"
            elif source_segment != "Unknown" or dest_segment != "Unknown":
                path_summary["cloudwan_path_type"] = "Partial-segment"
                if source_segment != "Unknown":
                    path_summary["source_segment"] = source_segment
                if dest_segment != "Unknown":
                    path_summary["destination_segment"] = dest_segment
        else:
            path_summary["path_type"] = "Unknown - IP(s) not found"

        return path_summary
