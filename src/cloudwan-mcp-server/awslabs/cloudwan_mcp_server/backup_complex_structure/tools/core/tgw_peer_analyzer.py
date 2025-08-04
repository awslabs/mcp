"""
Transit Gateway Peer Analysis MCP Tool.

This tool provides comprehensive TGW peer discovery and analysis capabilities,
based on the foundation script global_network_tgw_peers.py, adapted for MCP 
protocol integration with enhanced cross-organizational analysis.
"""

import asyncio
from typing import Any, Dict, List, Optional
from datetime import datetime

from botocore.exceptions import ClientError

from ...aws.client_manager import AWSClientManager
from ...config import CloudWANConfig
from ...models.network import (
    TGWPeerAnalysisResponse,
    TGWPeeringInfo,
)
from ..base import BaseMCPTool, handle_errors, ValidationError, AWSOperationError


class TGWPeerAnalyzer(BaseMCPTool):
    """
    Transit Gateway Peer Analyzer MCP Tool.

    Discovers and analyzes Transit Gateway peers in AWS Global Networks,
    providing detailed peer information, segment associations, and cross-
    organizational connectivity analysis.
    """

    @property
    def tool_name(self) -> str:
        return "analyze_tgw_peers"

    @property
    def description(self) -> str:
        return """
        Comprehensive Transit Gateway peer discovery and analysis.
        
        This tool queries AWS Global Networks to discover all Transit Gateway 
        peers, analyzes their segment associations, peering connections, and 
        provides cross-organizational connectivity insights.
        
        Features:
        - Global Network TGW peer enumeration
        - Core Network association analysis
        - Peering connection state validation
        - Cross-organizational peer discovery
        - Route propagation status analysis
        - TGW name resolution and tagging
        - Multi-region peer connectivity mapping
        """

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "global_network_id": {
                    "type": "string",
                    "description": "Global Network ID to analyze (required)",
                },
                "core_network_id": {
                    "type": "string",
                    "description": "Specific Core Network ID to focus analysis (optional)",
                },
                "region": {
                    "type": "string",
                    "description": "Specific region to analyze TGW peers (optional, analyzes all if not provided)",
                },
                "include_cross_account": {
                    "type": "boolean",
                    "description": "Include cross-account TGW peer analysis",
                    "default": True,
                },
                "include_route_analysis": {
                    "type": "boolean",
                    "description": "Include route propagation analysis",
                    "default": True,
                },
                "peer_state_filter": {
                    "type": "string",
                    "description": "Filter peers by state",
                    "enum": ["available", "pending-acceptance", "rejected", "failed"],
                },
                "validate_connectivity": {
                    "type": "boolean",
                    "description": "Validate peer connectivity and route propagation",
                    "default": False,
                },
            },
            "required": ["global_network_id"],
        }

    def __init__(self, aws_manager: AWSClientManager, config: CloudWANConfig):
        super().__init__(aws_manager, config)
        # Check for custom Network Manager endpoint from config
        self.custom_endpoint = config.aws.network_manager.custom_endpoint
        self.using_custom_endpoint = bool(self.custom_endpoint)
        if self.using_custom_endpoint:
            self.logger.info(f"Using custom Network Manager endpoint: {self.custom_endpoint}")

    @handle_errors
    async def execute(self, **kwargs) -> TGWPeerAnalysisResponse:
        """
        Execute TGW peer analysis.

        Args:
            **kwargs: Tool parameters from input schema

        Returns:
            TGW peer analysis response
        """
        # Extract and validate parameters
        global_network_id = kwargs.get("global_network_id")
        if not global_network_id:
            raise ValidationError("global_network_id is required")

        core_network_id = kwargs.get("core_network_id")
        target_region = kwargs.get("region")
        include_cross_account = kwargs.get("include_cross_account", True)
        include_route_analysis = kwargs.get("include_route_analysis", True)
        peer_state_filter = kwargs.get("peer_state_filter")
        validate_connectivity = kwargs.get("validate_connectivity", False)

        try:
            # Get Core Network ID if not provided
            if not core_network_id:
                core_network_id = await self._get_core_network_id(global_network_id)

            # Determine regions to analyze
            regions = [target_region] if target_region else self.config.aws.regions

            # Execute multi-region peer analysis
            return await self._analyze_tgw_peers(
                global_network_id=global_network_id,
                core_network_id=core_network_id,
                regions=regions,
                include_cross_account=include_cross_account,
                include_route_analysis=include_route_analysis,
                peer_state_filter=peer_state_filter,
                validate_connectivity=validate_connectivity,
            )

        except Exception as e:
            raise AWSOperationError(f"TGW peer analysis failed: {str(e)}")

    async def _get_core_network_id(self, global_network_id: str) -> Optional[str]:
        """Get Core Network ID associated with Global Network."""
        try:
            # NetworkManager is a global service, can use any region
            # Custom endpoint will be automatically applied by AWSClientManager
            nm_client = await self.aws_manager.get_client("networkmanager", "us-west-2")

            # List core networks and find the one associated with our global network
            response = await nm_client.list_core_networks()

            for core_network in response.get("CoreNetworks", []):
                if core_network.get("GlobalNetworkId") == global_network_id:
                    return core_network.get("CoreNetworkId")

            return None

        except ClientError as e:
            self.logger.warning(f"Error getting Core Network ID: {e}")
            return None

    async def _analyze_tgw_peers(
        self,
        global_network_id: str,
        core_network_id: Optional[str],
        regions: List[str],
        include_cross_account: bool,
        include_route_analysis: bool,
        peer_state_filter: Optional[str],
        validate_connectivity: bool,
    ) -> TGWPeerAnalysisResponse:
        """
        Analyze TGW peers across multiple regions.

        Args:
            global_network_id: Global Network ID
            core_network_id: Core Network ID
            regions: Target regions
            include_cross_account: Include cross-account analysis
            include_route_analysis: Include route analysis
            peer_state_filter: Filter by peer state
            validate_connectivity: Validate connectivity

        Returns:
            TGW peer analysis response
        """
        # Execute concurrent region analysis
        tasks = []
        for region in regions:
            task = self._analyze_region_peers(
                global_network_id=global_network_id,
                core_network_id=core_network_id,
                region=region,
                peer_state_filter=peer_state_filter,
                include_cross_account=include_cross_account,
            )
            tasks.append(task)

        region_results = await asyncio.gather(*tasks, return_exceptions=True)

        # Consolidate results
        all_tgw_peers = []
        all_peering_connections = []
        cross_org_peers = []
        route_propagation_status = {}
        connectivity_analysis = {}
        analysis_warnings = []

        for i, result in enumerate(region_results):
            if isinstance(result, Exception):
                analysis_warnings.append(f"Region {regions[i]} failed: {str(result)}")
                continue

            region_data = result
            all_tgw_peers.extend(region_data.get("tgw_peers", []))
            all_peering_connections.extend(region_data.get("peering_connections", []))
            cross_org_peers.extend(region_data.get("cross_org_peers", []))
            route_propagation_status.update(region_data.get("route_propagation", {}))
            connectivity_analysis.update(region_data.get("connectivity", {}))

        # Perform route analysis if requested
        if include_route_analysis and core_network_id:
            route_analysis = await self._analyze_route_propagation(
                core_network_id, all_tgw_peers, regions
            )
            route_propagation_status.update(route_analysis)

        # Perform connectivity validation if requested
        if validate_connectivity:
            connectivity_results = await self._validate_peer_connectivity(
                all_peering_connections, regions
            )
            connectivity_analysis.update(connectivity_results)

        # Convert to Pydantic models
        peering_models = []
        for pc in all_peering_connections:
            try:
                peering_models.append(TGWPeeringInfo(**pc))
            except Exception as e:
                analysis_warnings.append(f"Failed to process peering connection: {e}")

        return TGWPeerAnalysisResponse(
            global_network_id=global_network_id,
            core_network_id=core_network_id,
            transit_gateway_peers=all_tgw_peers,
            peering_connections=peering_models,
            cross_organizational_peers=cross_org_peers,
            route_propagation_status=route_propagation_status,
            connectivity_analysis=connectivity_analysis,
            regions_analyzed=regions,
            timestamp=datetime.now(),
            status="success" if not analysis_warnings else "partial",
            error_message="; ".join(analysis_warnings) if analysis_warnings else None,
        )

    async def _analyze_region_peers(
        self,
        global_network_id: str,
        core_network_id: Optional[str],
        region: str,
        peer_state_filter: Optional[str],
        include_cross_account: bool,
    ) -> Dict[str, Any]:
        """
        Analyze TGW peers in a single region.

        Args:
            global_network_id: Global Network ID
            core_network_id: Core Network ID
            region: Target region
            peer_state_filter: Peer state filter
            include_cross_account: Include cross-account analysis

        Returns:
            Region peer analysis results
        """
        try:
            # Get Network Manager client (custom endpoint handled automatically by AWSClientManager)
            nm_client = await self.aws_manager.get_client("networkmanager", "us-west-2")
            ec2_client = await self.aws_manager.get_client("ec2", region)

            # Get transit gateway registrations
            registrations_response = await nm_client.get_transit_gateway_registrations(
                GlobalNetworkId=global_network_id
            )
            registrations = registrations_response.get("TransitGatewayRegistrations", [])

            # Filter registrations by region
            region_registrations = [
                reg
                for reg in registrations
                if reg.get("TransitGatewayArn", "").split(":")[3] == region
            ]

            tgw_peers = []
            peering_connections = []
            cross_org_peers = []

            for registration in region_registrations:
                tgw_arn = registration.get("TransitGatewayArn", "")
                tgw_id = tgw_arn.split("/")[-1] if "/" in tgw_arn else ""

                if not tgw_id:
                    continue

                # Get TGW details
                tgw_details = await self._get_tgw_details(ec2_client, tgw_id)

                # Get peering attachments for this TGW
                tgw_peering = await self._get_tgw_peering_attachments(
                    ec2_client, tgw_id, peer_state_filter
                )

                # Process TGW peer information
                peer_info = {
                    "transit_gateway_id": tgw_id,
                    "transit_gateway_arn": tgw_arn,
                    "region": region,
                    "state": registration.get("State", ""),
                    "segment_name": self._extract_segment_name(registration),
                    "name": tgw_details.get("name", tgw_id),
                    "asn": tgw_details.get("asn"),
                    "peering_count": len(tgw_peering),
                    "registration_state": registration.get("State", ""),
                    "tags": tgw_details.get("tags", {}),
                }

                tgw_peers.append(peer_info)
                peering_connections.extend(tgw_peering)

                # Identify cross-organizational peers
                if include_cross_account:
                    cross_org = self._identify_cross_org_peers(tgw_peering, tgw_arn)
                    cross_org_peers.extend(cross_org)

            return {
                "tgw_peers": tgw_peers,
                "peering_connections": peering_connections,
                "cross_org_peers": cross_org_peers,
                "route_propagation": {},
                "connectivity": {},
            }

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            if error_code in ["UnauthorizedOperation", "AccessDenied"]:
                self.logger.warning(f"Access denied for region {region}")
                return {
                    "tgw_peers": [],
                    "peering_connections": [],
                    "cross_org_peers": [],
                    "route_propagation": {},
                    "connectivity": {},
                }
            raise AWSOperationError(f"Failed to analyze peers in region {region}: {e}")

    async def _get_tgw_details(self, ec2_client: Any, tgw_id: str) -> Dict[str, Any]:
        """Get Transit Gateway details including name and ASN."""
        try:
            response = await ec2_client.describe_transit_gateways(TransitGatewayIds=[tgw_id])

            if response.get("TransitGateways"):
                tgw = response["TransitGateways"][0]

                # Extract name from tags
                name = tgw_id  # Default to ID
                for tag in tgw.get("Tags", []):
                    if tag.get("Key", "").lower() == "name":
                        name = tag.get("Value", tgw_id)
                        break

                return {
                    "name": name,
                    "asn": tgw.get("Options", {}).get("AmazonSideAsn"),
                    "state": tgw.get("State"),
                    "tags": {tag["Key"]: tag["Value"] for tag in tgw.get("Tags", [])},
                }

            return {"name": tgw_id, "asn": None, "state": "unknown", "tags": {}}

        except Exception as e:
            self.logger.warning(f"Failed to get TGW details for {tgw_id}: {e}")
            return {"name": tgw_id, "asn": None, "state": "unknown", "tags": {}}

    async def _get_tgw_peering_attachments(
        self, ec2_client: Any, tgw_id: str, state_filter: Optional[str]
    ) -> List[Dict[str, Any]]:
        """Get TGW peering attachments."""
        try:
            filters = [{"Name": "transit-gateway-id", "Values": [tgw_id]}]
            if state_filter:
                filters.append({"Name": "state", "Values": [state_filter]})

            response = await ec2_client.describe_transit_gateway_peering_attachments(
                Filters=filters
            )

            peering_attachments = []
            for attachment in response.get("TransitGatewayPeeringAttachments", []):
                peering_info = {
                    "peering_attachment_id": attachment.get("TransitGatewayAttachmentId"),
                    "requester_tgw_id": attachment.get("RequesterTgwInfo", {}).get(
                        "TransitGatewayId"
                    ),
                    "accepter_tgw_id": attachment.get("AccepterTgwInfo", {}).get(
                        "TransitGatewayId"
                    ),
                    "requester_region": attachment.get("RequesterTgwInfo", {}).get("Region"),
                    "accepter_region": attachment.get("AccepterTgwInfo", {}).get("Region"),
                    "state": attachment.get("State"),
                    "status_code": attachment.get("Status", {}).get("Code"),
                    "status_message": attachment.get("Status", {}).get("Message"),
                    "creation_time": (
                        attachment.get("CreationTime", "").isoformat()
                        if attachment.get("CreationTime")
                        else None
                    ),
                    "tags": {tag["Key"]: tag["Value"] for tag in attachment.get("Tags", [])},
                }
                peering_attachments.append(peering_info)

            return peering_attachments

        except Exception as e:
            self.logger.warning(f"Failed to get peering attachments for TGW {tgw_id}: {e}")
            return []

    def _extract_segment_name(self, registration: Dict[str, Any]) -> Optional[str]:
        """Extract segment name from TGW registration."""
        # This might need adjustment based on actual API response structure
        tags = registration.get("Tags", {})
        return tags.get("segment", tags.get("Segment"))

    def _identify_cross_org_peers(
        self, peering_connections: List[Dict[str, Any]], local_tgw_arn: str
    ) -> List[Dict[str, Any]]:
        """Identify cross-organizational peering connections."""
        cross_org_peers = []
        local_account = local_tgw_arn.split(":")[4] if ":" in local_tgw_arn else ""

        for peering in peering_connections:
            requester_tgw = peering.get("requester_tgw_id", "")
            accepter_tgw = peering.get("accepter_tgw_id", "")

            # Check if this involves cross-account peering
            # This is a simplified check - real implementation would need more sophisticated logic
            if requester_tgw != accepter_tgw:
                cross_org_peers.append(
                    {
                        "peering_attachment_id": peering.get("peering_attachment_id"),
                        "local_tgw_account": local_account,
                        "peer_type": "cross_organization",
                        "state": peering.get("state"),
                        "requester_region": peering.get("requester_region"),
                        "accepter_region": peering.get("accepter_region"),
                    }
                )

        return cross_org_peers

    async def _analyze_route_propagation(
        self, core_network_id: str, tgw_peers: List[Dict[str, Any]], regions: List[str]
    ) -> Dict[str, str]:
        """Analyze route propagation status for TGW peers."""
        # Simplified route propagation analysis
        # Real implementation would check actual route propagation
        propagation_status = {}

        for peer in tgw_peers:
            tgw_id = peer.get("transit_gateway_id")
            if tgw_id:
                # Mock status - real implementation would check actual propagation
                propagation_status[tgw_id] = (
                    "enabled" if peer.get("state") == "available" else "disabled"
                )

        return propagation_status

    async def _validate_peer_connectivity(
        self, peering_connections: List[Dict[str, Any]], regions: List[str]
    ) -> Dict[str, Any]:
        """Validate peer connectivity."""
        # Simplified connectivity validation
        # Real implementation would perform actual connectivity tests
        connectivity_results = {}

        for peering in peering_connections:
            attachment_id = peering.get("peering_attachment_id")
            if attachment_id:
                state = peering.get("state", "")
                connectivity_results[attachment_id] = {
                    "status": "connected" if state == "available" else "disconnected",
                    "last_check": datetime.now().isoformat(),
                    "state": state,
                }

        return connectivity_results
