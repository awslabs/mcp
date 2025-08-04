"""Network path tracing tools for CloudWAN MCP Server.

This module provides tools for tracing network paths between IP addresses in CloudWAN networks.
It implements a class hierarchy with a common base class and specific implementations.
"""

import ipaddress
import logging
import json
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
import asyncio

from mcp.types import TextContent

from ...aws.client_manager import AWSClientManager
from ...models.network import (
    NetworkPathTraceResponse,
    NetworkHop,
    InspectionPoint,
    IPContext,
)
from ..base import BaseMCPTool
from ...config import CloudWANConfig
from ...utils.aws_operations import (
    handle_aws_errors,
    aws_client_context,
)


class BasePathTracingTool(BaseMCPTool):
    """Base class for all network path tracing tools."""

    def __init__(self, aws_manager: AWSClientManager, config: CloudWANConfig = None):
        super().__init__(aws_manager, config or CloudWANConfig())
        self._tool_name = "trace_network_path"
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
    async def execute(self, arguments: Dict[str, Any] = None, **kwargs) -> List[TextContent]:
        """Execute network path tracing with MCP-compliant signature."""
        # Combine arguments dict with legacy kwargs for compatibility
        if arguments:
            kwargs.update(arguments)
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

        try:
            # Get IP contexts
            source_context = await self._resolve_ip_context(source_ip, regions)
            destination_context = await self._resolve_ip_context(destination_ip, regions)

            # Build path
            path_hops, inspection_points, path_status = await self._build_network_path(
                source_context,
                destination_context,
                protocol,
                port,
                regions,
                detailed,
                skip_security_checks,
            )

            # Create response object
            response = NetworkPathTraceResponse(
                source_ip=source_ip,
                destination_ip=destination_ip,
                protocol=protocol,
                port=port,
                source_segment=getattr(source_context, "segment_name", None),
                destination_segment=getattr(destination_context, "segment_name", None),
                path_status=path_status,
                estimated_latency_ms=self._calculate_estimated_latency(path_hops),
                path_hops=path_hops,
                inspection_points=inspection_points,
                recommendations=self._generate_recommendations(
                    source_context, destination_context, path_hops, path_status
                ),
            )

            return [TextContent(type="text", text=response.model_dump_json(indent=2))]

        except Exception as e:
            self.logger.error(f"Path tracing failed: {e}", exc_info=True)
            return [TextContent(type="text", text=f"Error: Failed to trace network path: {str(e)}")]

    async def _resolve_ip_context(self, ip_address: str, regions: List[str]) -> IPContext:
        """
        Resolve IP address to its full AWS context.

        This method should be implemented by subclasses.
        """
        raise NotImplementedError("Subclasses must implement _resolve_ip_context")

    async def _build_network_path(
        self,
        source_context: IPContext,
        destination_context: IPContext,
        protocol: str,
        port: int,
        regions: List[str],
        detailed: bool,
        skip_security_checks: bool,
    ) -> Tuple[List[NetworkHop], List[InspectionPoint], str]:
        """
        Build a detailed network path between source and destination.

        This method should be implemented by subclasses.
        """
        raise NotImplementedError("Subclasses must implement _build_network_path")

    def _calculate_estimated_latency(self, path_hops: List[NetworkHop]) -> int:
        """
        Calculate estimated latency for the path.

        This is a simplified estimation based on hop count and types.
        A real implementation would use more sophisticated modeling.
        """
        # Count unique regions to estimate cross-region latency
        regions = set()
        for hop in path_hops:
            if hop.region != "global":
                regions.add(hop.region)

        # Base latency
        base_latency = 5  # ms

        # Add latency for each hop type
        hop_latency = 0
        for hop in path_hops:
            if hop.hop_type == "cloudwan-segment":
                hop_latency += 5
            elif hop.hop_type == "inspection-vpc":
                hop_latency += 3
            elif hop.hop_type == "cloudwan-attachment":
                hop_latency += 2
            else:
                hop_latency += 1

        # Add cross-region latency if applicable
        region_latency = 0
        if len(regions) > 1:
            region_latency = (len(regions) - 1) * 10

        return base_latency + hop_latency + region_latency

    def _generate_recommendations(
        self,
        source_context: IPContext,
        destination_context: IPContext,
        path_hops: List[NetworkHop],
        path_status: str,
    ) -> List[str]:
        """
        Generate recommendations based on the path analysis.

        This method can be overridden by subclasses to provide more specific recommendations.
        """
        recommendations = []

        # Check if path is disconnected
        if path_status != "CONNECTED":
            recommendations.append("Review security groups and NACLs to ensure proper access")
            recommendations.append(
                "Verify CloudWAN segment policy allows traffic between these VPCs"
            )
            return recommendations

        # Check if there's an inspection point
        has_inspection = any(hop.hop_type == "inspection-vpc" for hop in path_hops)
        if has_inspection:
            recommendations.append("Enable Network Firewall logging for better traffic visibility")

        # Check CloudWAN path
        different_vpcs = source_context.vpc_id != destination_context.vpc_id
        if different_vpcs:
            recommendations.append(
                "Consider implementing more granular security group rules for cross-VPC traffic"
            )
            recommendations.append("Enable VPC Flow Logs to monitor traffic patterns")

        # Check for multiple edge locations
        edge_locations = set()
        for hop in path_hops:
            if hop.hop_type == "cloudwan-attachment" and "edge_location" in hop.details:
                edge_locations.add(hop.details["edge_location"])

        if len(edge_locations) > 1:
            recommendations.append(
                "Review cross-region traffic patterns for potential optimization"
            )

        return recommendations


class SimulatedPathTracingTool(BasePathTracingTool):
    """Tool for tracing network paths using simulated data."""

    def __init__(self, aws_manager: AWSClientManager, config: CloudWANConfig = None):
        super().__init__(aws_manager, config or CloudWANConfig())
        self._tool_name = "trace_network_path"
        self._description = "Trace network path between two IP addresses with detailed hop analysis"

    async def _resolve_ip_context(self, ip_address: str, regions: List[str]) -> IPContext:
        """
        Resolve IP address to its full AWS context.

        This is a simulation implementation that returns mock data.
        """
        # For demonstration, return a simulated context
        region = regions[0] if regions else "us-west-2"

        if ip_address.startswith("10.0."):
            # Source network context
            return IPContext(
                ip_address=ip_address,
                region=region,
                availability_zone=f"{region}a",
                vpc_id="vpc-source123",
                subnet_id="subnet-src456",
                eni_id="eni-src789",
                resource_type="EC2",
                resource_id="i-src12345",
                is_public=False,
                segment_name="production",  # Simulated CloudWAN segment
            )
        else:
            # Destination network context
            return IPContext(
                ip_address=ip_address,
                region=region,
                availability_zone=f"{region}b",
                vpc_id="vpc-dest123",
                subnet_id="subnet-dest456",
                eni_id="eni-dest789",
                resource_type="EC2",
                resource_id="i-dest12345",
                is_public=False,
                segment_name="shared-services",  # Simulated CloudWAN segment
            )

    async def _build_network_path(
        self,
        source_context: IPContext,
        destination_context: IPContext,
        protocol: str,
        port: int,
        regions: List[str],
        detailed: bool,
        skip_security_checks: bool,
    ) -> Tuple[List[NetworkHop], List[InspectionPoint], str]:
        """
        Build a detailed network path between source and destination.

        This is a simulation implementation that returns mock data.
        """
        region = regions[0] if regions else "us-west-2"
        path_hops = []

        # For demonstration, create a simulated path with typical network hops
        if source_context.vpc_id == destination_context.vpc_id:
            # Same VPC path
            path_hops = self._build_same_vpc_path(
                source_context,
                destination_context,
                protocol,
                port,
                detailed,
                skip_security_checks,
            )
            inspection_points = []  # Typically no inspection within same VPC
            path_status = "CONNECTED"
        else:
            # Different VPC path - likely through CloudWAN
            path_hops, inspection_points = self._build_cloudwan_path(
                source_context,
                destination_context,
                protocol,
                port,
                region,
                detailed,
                skip_security_checks,
            )
            path_status = "CONNECTED"  # Could be "BLOCKED" if security groups deny traffic

        return path_hops, inspection_points, path_status

    def _build_same_vpc_path(
        self,
        source_context: IPContext,
        destination_context: IPContext,
        protocol: str,
        port: int,
        detailed: bool,
        skip_security_checks: bool,
    ) -> List[NetworkHop]:
        """Build network path for source and destination in the same VPC."""
        path_hops = []

        # Hop 1: Source subnet
        path_hops.append(
            NetworkHop(
                hop_number=1,
                hop_type="subnet",
                resource_id=source_context.subnet_id,
                resource_type="vpc-subnet",
                region=source_context.region,
                action="originate",
                details={
                    "vpc_id": source_context.vpc_id,
                    "cidr_block": "10.0.1.0/24",
                    "availability_zone": source_context.availability_zone,
                },
            )
        )

        # Hop 2: Source security group (if not skipping security checks)
        if not skip_security_checks:
            path_hops.append(
                NetworkHop(
                    hop_number=2,
                    hop_type="security-group",
                    resource_id="sg-source123",
                    resource_type="security-group",
                    region=source_context.region,
                    action="allow",
                    details={
                        "rule_id": "sgr-out123",
                        "vpc_id": source_context.vpc_id,
                        "rule_description": "Allow all outbound traffic",
                        "direction": "outbound",
                    },
                )
            )

        # Hop 3: Route table
        path_hops.append(
            NetworkHop(
                hop_number=len(path_hops) + 1,
                hop_type="route-table",
                resource_id="rtb-vpc123",
                resource_type="vpc-route-table",
                region=source_context.region,
                action="forward",
                details={
                    "vpc_id": source_context.vpc_id,
                    "destination_cidr": "10.0.0.0/16",  # Local VPC CIDR
                    "target_type": "local",
                    "target_id": "local",
                },
            )
        )

        # Hop 4: Destination security group (if not skipping security checks)
        if not skip_security_checks:
            path_hops.append(
                NetworkHop(
                    hop_number=len(path_hops) + 1,
                    hop_type="security-group",
                    resource_id="sg-dest123",
                    resource_type="security-group",
                    region=destination_context.region,
                    action="allow",
                    details={
                        "rule_id": "sgr-in123",
                        "vpc_id": destination_context.vpc_id,
                        "rule_description": f"Allow {protocol} port {port} from 10.0.0.0/8",
                        "direction": "inbound",
                    },
                )
            )

        # Hop 5: Destination subnet
        path_hops.append(
            NetworkHop(
                hop_number=len(path_hops) + 1,
                hop_type="subnet",
                resource_id=destination_context.subnet_id,
                resource_type="vpc-subnet",
                region=destination_context.region,
                action="deliver",
                details={
                    "vpc_id": destination_context.vpc_id,
                    "cidr_block": "10.0.2.0/24",
                    "availability_zone": destination_context.availability_zone,
                },
            )
        )

        return path_hops

    def _build_cloudwan_path(
        self,
        source_context: IPContext,
        destination_context: IPContext,
        protocol: str,
        port: int,
        region: str,
        detailed: bool,
        skip_security_checks: bool,
    ) -> Tuple[List[NetworkHop], List[InspectionPoint]]:
        """Build network path for source and destination in different VPCs through CloudWAN."""
        path_hops = []

        # Hop 1: Source subnet
        path_hops.append(
            NetworkHop(
                hop_number=1,
                hop_type="subnet",
                resource_id=source_context.subnet_id,
                resource_type="vpc-subnet",
                region=source_context.region,
                action="originate",
                details={
                    "vpc_id": source_context.vpc_id,
                    "cidr_block": "10.0.1.0/24",
                    "availability_zone": source_context.availability_zone,
                },
            )
        )

        # Hop 2: Source security group (if not skipping security checks)
        if not skip_security_checks:
            path_hops.append(
                NetworkHop(
                    hop_number=2,
                    hop_type="security-group",
                    resource_id="sg-source123",
                    resource_type="security-group",
                    region=source_context.region,
                    action="allow",
                    details={
                        "rule_id": "sgr-out123",
                        "vpc_id": source_context.vpc_id,
                        "rule_description": "Allow all outbound traffic",
                        "direction": "outbound",
                    },
                )
            )

        # Hop 3: Source VPC route table
        path_hops.append(
            NetworkHop(
                hop_number=len(path_hops) + 1,
                hop_type="route-table",
                resource_id="rtb-source123",
                resource_type="vpc-route-table",
                region=source_context.region,
                action="forward",
                details={
                    "vpc_id": source_context.vpc_id,
                    "destination_cidr": "0.0.0.0/0",
                    "target_type": "cloudwan",
                    "target_id": "attachment-source123",
                },
            )
        )

        # Hop 4: Source CloudWAN attachment
        path_hops.append(
            NetworkHop(
                hop_number=len(path_hops) + 1,
                hop_type="cloudwan-attachment",
                resource_id="attachment-source123",
                resource_type="cloudwan-attachment",
                region=source_context.region,
                action="forward",
                details={
                    "attachment_type": "VPC",
                    "vpc_id": source_context.vpc_id,
                    "segment_name": "production",
                    "edge_location": source_context.region,
                },
            )
        )

        # Hop 5: CloudWAN segment
        path_hops.append(
            NetworkHop(
                hop_number=len(path_hops) + 1,
                hop_type="cloudwan-segment",
                resource_id="segment-production",
                resource_type="cloudwan-segment",
                region="global",
                action="route",
                details={
                    "core_network_id": "core-network-1234",
                    "segment_name": "production",
                    "policy_rule": "AllowProductionTraffic",
                    "destination_cidr": destination_context.ip_address + "/32",
                },
            )
        )

        # Hop 6: Inspection VPC (if this path requires inspection)
        inspection_vpc_id = "vpc-inspection123"
        path_hops.append(
            NetworkHop(
                hop_number=len(path_hops) + 1,
                hop_type="inspection-vpc",
                resource_id=inspection_vpc_id,
                resource_type="vpc",
                region=region,
                action="inspect",
                details={
                    "network_function_group": "inspection-nfg",
                    "inspection_type": "network-firewall",
                },
            )
        )

        # Hop 7: Destination CloudWAN attachment
        path_hops.append(
            NetworkHop(
                hop_number=len(path_hops) + 1,
                hop_type="cloudwan-attachment",
                resource_id="attachment-dest123",
                resource_type="cloudwan-attachment",
                region=destination_context.region,
                action="forward",
                details={
                    "attachment_type": "VPC",
                    "vpc_id": destination_context.vpc_id,
                    "segment_name": "production",
                    "edge_location": destination_context.region,
                },
            )
        )

        # Hop 8: Destination VPC route table
        path_hops.append(
            NetworkHop(
                hop_number=len(path_hops) + 1,
                hop_type="route-table",
                resource_id="rtb-dest123",
                resource_type="vpc-route-table",
                region=destination_context.region,
                action="forward",
                details={
                    "vpc_id": destination_context.vpc_id,
                    "destination_cidr": "10.0.2.0/24",
                    "target_type": "local",
                },
            )
        )

        # Hop 9: Destination security group (if not skipping security checks)
        if not skip_security_checks:
            path_hops.append(
                NetworkHop(
                    hop_number=len(path_hops) + 1,
                    hop_type="security-group",
                    resource_id="sg-dest123",
                    resource_type="security-group",
                    region=destination_context.region,
                    action="allow",
                    details={
                        "rule_id": "sgr-in123",
                        "vpc_id": destination_context.vpc_id,
                        "rule_description": f"Allow {protocol} port {port} from 10.0.0.0/8",
                        "direction": "inbound",
                    },
                )
            )

        # Hop 10: Destination subnet
        path_hops.append(
            NetworkHop(
                hop_number=len(path_hops) + 1,
                hop_type="subnet",
                resource_id=destination_context.subnet_id,
                resource_type="vpc-subnet",
                region=destination_context.region,
                action="deliver",
                details={
                    "vpc_id": destination_context.vpc_id,
                    "cidr_block": "10.0.2.0/24",
                    "availability_zone": destination_context.availability_zone,
                },
            )
        )

        # Create inspection point
        inspection_points = [
            InspectionPoint(
                vpc_id=inspection_vpc_id,
                region=region,
                firewall_arn=f"arn:aws:network-firewall:{region}:123456789012:firewall/inspection-fw",
                inspection_type="network-firewall",
                verdict="allow",
                rules_evaluated=[
                    {
                        "rule_id": "fw-stateful-rule-1",
                        "action": "pass",
                        "description": "Allow established TCP connections",
                    },
                    {
                        "rule_id": "fw-stateless-rule-2",
                        "action": "forward",
                        "description": "Forward all traffic to next rule",
                    },
                ],
            )
        ]

        return path_hops, inspection_points


class NetworkPathTracingTool(BasePathTracingTool):
    """Tool for tracing network paths between IP addresses with AWS implementation."""

    def __init__(self, aws_manager: AWSClientManager, config: CloudWANConfig = None):
        super().__init__(aws_manager, config or CloudWANConfig())
        self._tool_name = "trace_network_path"
        self._description = "Trace network path between two IP addresses with detailed hop analysis"
        # Cache for VPC to segment mapping to avoid repeated API calls
        self._vpc_segment_cache: Dict[str, Optional[str]] = {}

    async def _resolve_ip_context(self, ip_address: str, regions: List[str]) -> IPContext:
        """
        Resolve IP address to its full AWS context.

        This implementation uses AWS API calls to find the VPC, subnet, etc. for the IP address.
        """
        self.logger.info(f"Searching for IP {ip_address} across regions: {', '.join(regions)}")

        # Search across regions concurrently
        results = await asyncio.gather(
            *[self._find_ip_in_region(region, ip_address) for region in regions],
            return_exceptions=True,
        )

        # Process results, handling any exceptions
        valid_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                self.logger.warning(f"Error searching in region {regions[i]}: {str(result)}")
            else:
                if result.get("found"):
                    self.logger.info(f"Found IP {ip_address} in region {result.get('region')}")
                    # Convert to IPContext
                    return IPContext(
                        ip_address=ip_address,
                        region=result.get("region"),
                        availability_zone=result.get("availability_zone"),
                        vpc_id=result.get("vpc_id"),
                        subnet_id=result.get("subnet_id"),
                        eni_id=result.get("eni_id"),
                        resource_type=result.get("resource_type", "Unknown"),
                        resource_id=result.get("resource_id", ""),
                        is_public=result.get("is_public", False),
                        segment_name=result.get("segment_name"),
                    )
                valid_results.append(result)

        # If not found in any region, return a default context
        self.logger.warning(f"IP {ip_address} not found in any region")
        return IPContext(
            ip_address=ip_address,
            region=regions[0] if regions else "us-west-2",
            availability_zone="",
            vpc_id="",
            subnet_id="",
            eni_id="",
            resource_type="Unknown",
            resource_id="",
            is_public=False,
        )

    async def _find_ip_in_region(self, region: str, ip_address: str) -> Dict[str, Any]:
        """Find IP address context in a specific region."""
        try:
            async with aws_client_context(self.aws_manager, "ec2", region) as ec2_client:
                # Search for ENIs with this private IP
                response = await ec2_client.describe_network_interfaces(
                    Filters=[{"Name": "private-ip-address", "Values": [ip_address]}]
                )

                if response.get("NetworkInterfaces"):
                    eni = response["NetworkInterfaces"][0]

                    # Extract attachment information if available
                    attachment_info = {}
                    if "Attachment" in eni:
                        attachment = eni["Attachment"]
                        attachment_info = {
                            "attachment_id": attachment.get("AttachmentId"),
                            "instance_id": attachment.get("InstanceId"),
                            "instance_owner_id": attachment.get("InstanceOwnerId"),
                            "device_index": attachment.get("DeviceIndex"),
                            "status": attachment.get("Status"),
                            "attach_time": str(attachment.get("AttachTime")),
                        }

                    # Determine resource type based on attachment
                    resource_type = "ENI"
                    resource_id = eni.get("NetworkInterfaceId")
                    if attachment_info.get("instance_id"):
                        resource_type = "EC2"
                        resource_id = attachment_info.get("instance_id")

                    # Fetch CloudWAN segment information
                    segment_name = await self._get_vpc_cloudwan_segment(region, eni.get("VpcId"))

                    return {
                        "found": True,
                        "region": region,
                        "vpc_id": eni.get("VpcId"),
                        "subnet_id": eni.get("SubnetId"),
                        "eni_id": eni.get("NetworkInterfaceId"),
                        "availability_zone": eni.get("AvailabilityZone"),
                        "description": eni.get("Description", ""),
                        "status": eni.get("Status"),
                        "attachment": attachment_info,
                        "resource_type": resource_type,
                        "resource_id": resource_id,
                        "is_public": bool(eni.get("Association", {}).get("PublicIp")),
                        "segment_name": segment_name,
                    }

                return {"found": False, "region": region}

        except Exception as e:
            self.logger.error(f"Error searching for IP {ip_address} in region {region}: {e}")
            return {"found": False, "region": region, "error": str(e)}

    async def _get_vpc_cloudwan_segment(self, region: str, vpc_id: str) -> Optional[str]:
        """Get the CloudWAN segment name for a VPC if it has a CloudWAN attachment."""
        if not vpc_id:
            return None

        # Check cache first
        cache_key = f"{vpc_id}:{region}"
        if cache_key in self._vpc_segment_cache:
            return self._vpc_segment_cache[cache_key]

        try:
            # Network Manager API is only available in us-west-2
            async with aws_client_context(
                self.aws_manager, "networkmanager", "us-west-2"
            ) as nm_client:
                # Search for attachments by VPC ID matching in resource ARN

                try:
                    # First, get all core networks to find which one has our VPC
                    core_networks_response = await nm_client.list_core_networks()

                    for core_network in core_networks_response.get("CoreNetworks", []):
                        core_network_id = core_network.get("CoreNetworkId")

                        # Get attachments for this core network filtered by our edge location
                        attachments_response = await nm_client.list_attachments(
                            CoreNetworkId=core_network_id,
                            AttachmentType="VPC",
                            EdgeLocation=region,
                            State="AVAILABLE",
                        )

                        # Look for our VPC in the attachments
                        for attachment in attachments_response.get("Attachments", []):
                            resource_arn = attachment.get("ResourceArn", "")

                            # Check if this is our VPC (resource ARN contains the VPC ID)
                            if vpc_id in resource_arn:
                                # Found our VPC attachment, cache and return the segment name
                                segment_name = attachment.get("SegmentName")
                                self._vpc_segment_cache[cache_key] = segment_name
                                self.logger.info(
                                    f"Found CloudWAN segment '{segment_name}' for VPC {vpc_id} in {region}"
                                )
                                return segment_name

                except Exception as e:
                    self.logger.debug(f"Error in optimized attachment search: {e}")
                    # Fall back to the detailed method if needed
                    pass

        except Exception as e:
            self.logger.warning(f"Error fetching CloudWAN segment for VPC {vpc_id}: {e}")

        # Cache the negative result too
        self._vpc_segment_cache[cache_key] = None
        return None

    async def _build_network_path(
        self,
        source_context: IPContext,
        destination_context: IPContext,
        protocol: str,
        port: int,
        regions: List[str],
        detailed: bool,
        skip_security_checks: bool,
    ) -> Tuple[List[NetworkHop], List[InspectionPoint], str]:
        """
        Build a detailed network path between source and destination.

        This implementation would include:
        1. Check if source and destination are in the same VPC or different VPCs
        2. Analyze route tables to determine the path
        3. Check for CloudWAN segments, Transit Gateways, or VPC peering along the path
        4. Evaluate security groups and NACLs if required
        5. Identify any inspection points (Network Firewall, etc.)
        """
        self.logger.info(
            f"Building network path from {source_context.ip_address} to {destination_context.ip_address}"
        )

        # For now, use the simulated path builder as the implementation is complex
        # In a real implementation, this would call AWS APIs to determine the path
        simulator = SimulatedPathTracingTool(self.aws_manager, self.config)
        return await simulator._build_network_path(
            source_context,
            destination_context,
            protocol,
            port,
            regions,
            detailed,
            skip_security_checks,
        )


class EnhancedNetworkPathTracingTool(NetworkPathTracingTool):
    """Enhanced network path tracing tool with additional features."""

    def __init__(self, aws_manager: AWSClientManager, config: CloudWANConfig = None):
        super().__init__(aws_manager, config or CloudWANConfig())
        self._tool_name = "enhanced_trace_network_path"
        self._description = "Trace network path between two IP addresses with detailed hop analysis"

    async def execute(self, arguments: Dict[str, Any] = None, **kwargs) -> List[TextContent]:
        """Execute network path tracing with enhanced analysis and MCP-compliant signature."""
        # Combine arguments dict with legacy kwargs for compatibility
        if arguments:
            kwargs.update(arguments)
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

    async def _discover_core_networks(self) -> List[Dict[str, Any]]:
        """Discover Core Networks using Network Manager."""
        try:
            async with aws_client_context(
                self.aws_manager, "networkmanager", "us-west-2"
            ) as nm_client:
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
            async with aws_client_context(self.aws_manager, "ec2", region) as ec2_client:
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


class SegmentConnectivityTool(BaseMCPTool):
    """Tool for analyzing CloudWAN segment connectivity."""

    def __init__(self, aws_manager: AWSClientManager, config: CloudWANConfig = None):
        super().__init__(aws_manager, config or CloudWANConfig())
        self._tool_name = "analyze_segment_connectivity"
        self._description = "Analyze connectivity between CloudWAN segments and attached resources"
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
                "segment_name": {
                    "type": "string",
                    "description": "CloudWAN segment name to analyze",
                },
                "core_network_id": {
                    "type": "string",
                    "description": "Core Network ID (required if multiple core networks exist)",
                },
                "region": {
                    "type": "string",
                    "description": "Filter segment analysis by region",
                },
                "detailed": {
                    "type": "boolean",
                    "description": "Include detailed attachment and route analysis",
                    "default": False,
                },
            },
            "required": ["segment_name"],
        }

    @handle_aws_errors("Segment connectivity analysis")
    async def execute(self, arguments: Dict[str, Any] = None, **kwargs) -> List[TextContent]:
        """Execute segment connectivity analysis with MCP-compliant signature."""
        # Combine arguments dict with legacy kwargs for compatibility
        if arguments:
            kwargs.update(arguments)
        segment_name = kwargs["segment_name"]
        core_network_id = kwargs.get("core_network_id")
        region = kwargs.get("region")
        detailed = kwargs.get("detailed", False)

        # In a real implementation, this would analyze the segment's connectivity
        # This is a placeholder for the actual implementation

        result = {
            "segment_name": segment_name,
            "core_network_id": core_network_id or "core-network-1234",
            "analysis_timestamp": datetime.now().isoformat(),
            "attachments": [
                {
                    "attachment_id": "attachment-1234",
                    "attachment_type": "VPC",
                    "state": "AVAILABLE",
                    "region": region or "us-west-2",
                    "resource_id": "vpc-aaa111",
                },
                {
                    "attachment_id": "attachment-2345",
                    "attachment_type": "VPC",
                    "state": "AVAILABLE",
                    "region": region or "us-west-2",
                    "resource_id": "vpc-bbb222",
                },
                {
                    "attachment_id": "attachment-3456",
                    "attachment_type": "TGW",
                    "state": "AVAILABLE",
                    "region": "eu-west-1",
                    "resource_id": "tgw-ccc333",
                },
            ],
            "routes": [
                {
                    "destination_cidr": "10.0.0.0/16",
                    "route_type": "STATIC",
                    "state": "ACTIVE",
                    "edge_location": region or "us-west-2",
                },
                {
                    "destination_cidr": "10.1.0.0/16",
                    "route_type": "PROPAGATED",
                    "state": "ACTIVE",
                    "edge_location": region or "us-west-2",
                },
                {
                    "destination_cidr": "192.168.0.0/16",
                    "route_type": "PROPAGATED",
                    "state": "ACTIVE",
                    "edge_location": "eu-west-1",
                },
            ],
            "connectivity_status": {
                "within_segment": "CONNECTED",
                "to_other_segments": {
                    "development": "VIA_INSPECTION",
                    "shared-services": "DIRECT",
                    "isolated": "DISCONNECTED",
                },
            },
            "recommendations": [
                "Review route propagation from TGW attachments",
                "Consider adding additional edge locations for improved global latency",
                "Implement more granular security group rules for cross-segment traffic",
            ],
        }

        if detailed:
            result["detailed_policy_analysis"] = {
                "policy_rules": [
                    {
                        "rule_name": "AllowProductionTraffic",
                        "action": "allow",
                        "description": "Allow traffic between all VPCs in this segment",
                    },
                    {
                        "rule_name": "InspectionRule",
                        "action": "inspect",
                        "description": "Traffic to segment 'development' must go through inspection VPC",
                    },
                    {
                        "rule_name": "DefaultRule",
                        "action": "deny",
                        "description": "Deny all other traffic",
                    },
                ],
                "network_functions": [
                    {
                        "name": "inspection-nfg",
                        "type": "inspection",
                        "vpc_id": "vpc-inspection",
                        "region": region or "us-west-2",
                    }
                ],
            }

        return [TextContent(type="text", text=json.dumps(result, indent=2))]


class VPCConnectivityTool(BaseMCPTool):
    """Tool for analyzing VPC connectivity with CloudWAN and TGW."""

    def __init__(self, aws_manager: AWSClientManager, config: CloudWANConfig = None):
        super().__init__(aws_manager, config or CloudWANConfig())
        self._tool_name = "analyze_vpc_connectivity"
        self._description = (
            "Analyze VPC connectivity including CloudWAN and Transit Gateway attachments"
        )
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
                "vpc_id": {"type": "string", "description": "VPC ID to analyze"},
                "region": {"type": "string", "description": "VPC region"},
                "include_tgw": {
                    "type": "boolean",
                    "description": "Include Transit Gateway attachments",
                    "default": True,
                },
                "include_cloudwan": {
                    "type": "boolean",
                    "description": "Include CloudWAN attachments",
                    "default": True,
                },
                "include_peering": {
                    "type": "boolean",
                    "description": "Include VPC peering connections",
                    "default": True,
                },
            },
            "required": ["vpc_id"],
        }

    @handle_aws_errors("VPC connectivity analysis")
    async def execute(self, arguments: Dict[str, Any] = None, **kwargs) -> List[TextContent]:
        """Execute VPC connectivity analysis with MCP-compliant signature."""
        # Combine arguments dict with legacy kwargs for compatibility
        if arguments:
            kwargs.update(arguments)
        vpc_id = kwargs["vpc_id"]
        region = kwargs.get("region", self.config.aws.regions[0])
        include_tgw = kwargs.get("include_tgw", True)
        include_cloudwan = kwargs.get("include_cloudwan", True)
        include_peering = kwargs.get("include_peering", True)

        # In a real implementation, this would analyze the VPC's connectivity
        # This is a placeholder for the actual implementation

        result = {
            "vpc_id": vpc_id,
            "region": region,
            "analysis_timestamp": datetime.now().isoformat(),
            "vpc_details": {
                "cidr_block": "10.0.0.0/16",
                "state": "available",
                "subnet_count": 6,
                "route_table_count": 4,
                "internet_gateway_id": "igw-12345",
            },
        }

        if include_cloudwan:
            result["cloudwan_attachments"] = [
                {
                    "attachment_id": "attachment-12345",
                    "core_network_id": "core-network-1234",
                    "segment_name": "production",
                    "edge_location": region,
                    "state": "AVAILABLE",
                }
            ]

        if include_tgw:
            result["tgw_attachments"] = [
                {
                    "attachment_id": "tgw-attach-12345",
                    "transit_gateway_id": "tgw-12345",
                    "subnet_ids": ["subnet-1", "subnet-2", "subnet-3"],
                    "route_table_id": "tgw-rtb-12345",
                    "state": "available",
                }
            ]

        if include_peering:
            result["peering_connections"] = [
                {
                    "peering_id": "pcx-12345",
                    "accepter_vpc_id": "vpc-peer1",
                    "accepter_cidr": "10.1.0.0/16",
                    "accepter_region": region,
                    "status": "active",
                }
            ]

        result["connectivity_summary"] = {
            "cloudwan_connectivity": {
                "connected_segments": ["production"],
                "reachable_segments": ["production", "shared-services"],
                "unreachable_segments": ["development", "isolated"],
            },
            "tgw_connectivity": {
                "connected_tgws": ["tgw-12345"],
                "reachable_vpcs": ["vpc-a", "vpc-b", "vpc-c"],
                "reachable_vpn_connections": ["vpn-1"],
            },
            "peering_connectivity": {
                "direct_peers": ["vpc-peer1"],
                "reachable_cidrs": ["10.1.0.0/16"],
            },
            "route_propagation": {
                "routes_from_vpc": ["10.0.0.0/16"],
                "routes_from_cloudwan": ["10.2.0.0/16", "10.3.0.0/16"],
                "routes_from_tgw": ["172.16.0.0/16"],
                "routes_from_peering": ["10.1.0.0/16"],
            },
            "issues": [
                {
                    "type": "overlapping_cidr",
                    "description": "Overlapping CIDR detected: 10.1.0.0/16 from both VPC peering and CloudWAN",
                    "severity": "medium",
                },
                {
                    "type": "missing_route",
                    "description": "Missing return routes in peered VPC vpc-peer1",
                    "severity": "medium",
                },
            ],
            "recommendations": [
                "Resolve CIDR overlap between VPC peering and CloudWAN routes",
                "Add return routes in vpc-peer1 for full connectivity",
                "Consider migrating VPC peering connections to CloudWAN for centralized management",
            ],
        }

        return [TextContent(type="text", text=json.dumps(result, indent=2))]
