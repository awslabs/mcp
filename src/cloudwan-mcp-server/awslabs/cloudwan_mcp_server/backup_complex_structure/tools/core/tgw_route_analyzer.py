"""
Transit Gateway Route Analysis MCP Tool.

This tool provides comprehensive Transit Gateway route analysis capabilities,
including route overlap detection, blackhole route identification, cross-region
routing path analysis, and summary statistics generation.

Features:
- Multi-region TGW discovery and analysis
- Route overlap detection and categorization
- Blackhole route identification and impact assessment
- Cross-region routing path analysis via peering connections
- Detailed summary statistics for routes across transit gateways
"""

import asyncio
import ipaddress
import logging
import re
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import Any, Dict, List, Optional

from botocore.exceptions import ClientError

from ...aws.client_manager import AWSClientManager
from ...config import CloudWANConfig
from ...models.network import (
    AttachmentInfo,
    BlackholeRouteInfo,
    CrossRegionRouteInfo,
    RouteInfo,
    RouteOverlapInfo,
    RouteSummaryStats,
    TGWPeeringInfo,
    TGWRouteAnalysisResponse,
    TGWRouteTableInfo,
)
from ..base import (
    BaseMCPTool,
    handle_errors,
    validate_regions,
    ValidationError,
    AWSOperationError,
)


class TGWRouteAnalyzer(BaseMCPTool):
    """
    Transit Gateway Route Analyzer MCP Tool.

    Provides comprehensive route analysis for Transit Gateways across regions,
    including route table enumeration, overlap detection, blackhole route
    identification, cross-region routing path analysis, and summary statistics.
    """

    @property
    def tool_name(self) -> str:
        """Get tool name for MCP registration."""
        return "analyze_tgw_routes"

    @property
    def description(self) -> str:
        """Get tool description for MCP registration."""
        return """
        Comprehensive Transit Gateway route analysis across multiple AWS regions.
        
        This tool discovers Transit Gateways and provides detailed route analysis including:
        - Route table enumeration with state analysis
        - Route overlap detection and categorization
        - Blackhole route identification and impact assessment
        - Cross-region routing path analysis via peering connections
        - Detailed summary statistics for routes
        
        The analysis helps identify potential issues in Transit Gateway routing configurations,
        such as conflicting routes, unintended blackhole routes, or inefficient cross-region
        routing paths that could impact network performance and availability.
        """

    @property
    def input_schema(self) -> Dict[str, Any]:
        """Get tool input schema for MCP registration."""
        return {
            "type": "object",
            "properties": {
                "regions": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "AWS regions to analyze (defaults to config regions)",
                    "default": [],
                },
                "tgw_id": {
                    "type": "string",
                    "description": "Specific Transit Gateway ID to analyze (optional)",
                },
                "tgw_name_filter": {
                    "type": "string",
                    "description": "Filter TGWs by name pattern (supports wildcards like 'prod-*')",
                },
                "cidr_filter": {
                    "type": "string",
                    "description": "Filter routes by destination CIDR (supports partial matching)",
                },
                "include_route_details": {
                    "type": "boolean",
                    "description": "Include detailed route information",
                    "default": True,
                },
                "detect_overlaps": {
                    "type": "boolean",
                    "description": "Detect and analyze route overlaps",
                    "default": True,
                },
                "analyze_blackholes": {
                    "type": "boolean",
                    "description": "Identify and analyze blackhole routes",
                    "default": True,
                },
                "analyze_cross_region": {
                    "type": "boolean",
                    "description": "Analyze cross-region routing paths",
                    "default": True,
                },
                "generate_stats": {
                    "type": "boolean",
                    "description": "Generate detailed route statistics",
                    "default": True,
                },
                "include_cross_account": {
                    "type": "boolean",
                    "description": "Include cross-account peering analysis",
                    "default": True,
                },
            },
            "required": [],
        }

    def __init__(self, aws_manager: AWSClientManager, config: CloudWANConfig):
        """
        Initialize the Transit Gateway Route Analyzer tool.

        Args:
            aws_manager: AWS client manager for multi-region API calls
            config: CloudWAN configuration
        """
        super().__init__(aws_manager, config)
        self.logger = logging.getLogger(__name__)
        self.executor = ThreadPoolExecutor(max_workers=10)

    @handle_errors
    async def execute(self, **kwargs) -> TGWRouteAnalysisResponse:
        """
        Execute TGW route analysis.

        This method is the main entry point for the tool, coordinating
        the multi-region TGW discovery and analysis process.

        Args:
            **kwargs: Tool parameters from input schema
                regions (List[str]): AWS regions to analyze
                tgw_id (str): Specific Transit Gateway ID to analyze
                tgw_name_filter (str): Filter TGWs by name pattern
                cidr_filter (str): Filter routes by destination CIDR
                include_route_details (bool): Include detailed route information
                detect_overlaps (bool): Detect and analyze route overlaps
                analyze_blackholes (bool): Identify and analyze blackhole routes
                analyze_cross_region (bool): Analyze cross-region routing paths
                generate_stats (bool): Generate detailed route statistics
                include_cross_account (bool): Include cross-account peering analysis

        Returns:
            TGWRouteAnalysisResponse: Analysis results including route overlaps,
                                     blackhole routes, cross-region paths, and statistics

        Raises:
            ValidationError: If input parameters are invalid
            AWSOperationError: If AWS API operations fail
        """
        # Extract and validate parameters
        regions = validate_regions(kwargs.get("regions"), self.config)
        tgw_id = kwargs.get("tgw_id")
        tgw_name_filter = kwargs.get("tgw_name_filter")
        cidr_filter = kwargs.get("cidr_filter")
        include_route_details = kwargs.get("include_route_details", True)
        detect_overlaps = kwargs.get("detect_overlaps", True)
        analyze_blackholes = kwargs.get("analyze_blackholes", True)
        analyze_cross_region = kwargs.get("analyze_cross_region", True)
        generate_stats = kwargs.get("generate_stats", True)
        include_cross_account = kwargs.get("include_cross_account", True)

        # Validate CIDR filter if provided
        if cidr_filter:
            try:
                ipaddress.ip_network(cidr_filter, strict=False)
            except ValueError:
                # Allow partial matching for non-CIDR filters
                pass

        # Compile TGW name filter regex if provided
        tgw_name_pattern = None
        if tgw_name_filter:
            try:
                pattern = tgw_name_filter.replace("*", ".*").replace("?", ".")
                tgw_name_pattern = re.compile(pattern, re.IGNORECASE)
            except re.error as e:
                raise ValidationError(f"Invalid TGW name filter pattern: {e}")

        try:
            # Execute multi-region analysis
            results = await self._analyze_regions(
                regions=regions,
                tgw_id=tgw_id,
                tgw_name_pattern=tgw_name_pattern,
                cidr_filter=cidr_filter,
                include_route_details=include_route_details,
                detect_overlaps=detect_overlaps,
                analyze_blackholes=analyze_blackholes,
                analyze_cross_region=analyze_cross_region,
                generate_stats=generate_stats,
                include_cross_account=include_cross_account,
            )

            return results

        except Exception as e:
            raise AWSOperationError(f"TGW route analysis failed: {str(e)}")

    async def _analyze_regions(
        self,
        regions: List[str],
        tgw_id: Optional[str],
        tgw_name_pattern: Optional[re.Pattern],
        cidr_filter: Optional[str],
        include_route_details: bool,
        detect_overlaps: bool,
        analyze_blackholes: bool,
        analyze_cross_region: bool,
        generate_stats: bool,
        include_cross_account: bool,
    ) -> TGWRouteAnalysisResponse:
        """
        Analyze Transit Gateways across multiple regions.

        Args:
            regions: Target regions
            tgw_id: Specific TGW ID filter
            tgw_name_pattern: TGW name filter pattern
            cidr_filter: CIDR filter
            include_route_details: Include detailed route info
            detect_overlaps: Detect and analyze route overlaps
            analyze_blackholes: Identify blackhole routes
            analyze_cross_region: Analyze cross-region routing
            generate_stats: Generate summary statistics
            include_cross_account: Include cross-account analysis

        Returns:
            Consolidated analysis response
        """
        # Execute concurrent region analysis
        tasks = []
        for region in regions:
            task = self._analyze_region(
                region=region,
                tgw_id=tgw_id,
                tgw_name_pattern=tgw_name_pattern,
                cidr_filter=cidr_filter,
                include_route_details=include_route_details,
            )
            tasks.append(task)

        region_results = await asyncio.gather(*tasks, return_exceptions=True)

        # Consolidate results
        all_tgws = []
        all_peering_connections = []
        all_attachments = []
        all_route_tables = []
        analysis_warnings = []

        for i, result in enumerate(region_results):
            if isinstance(result, Exception):
                analysis_warnings.append(f"Region {regions[i]} failed: {str(result)}")
                continue

            region_data = result
            all_tgws.extend(region_data.get("tgws", []))
            all_peering_connections.extend(region_data.get("peering_connections", []))
            all_attachments.extend(region_data.get("attachments", []))

            # Extract route tables for analysis
            for tgw in region_data.get("tgws", []):
                for rt in tgw.get("route_tables", []):
                    rt_with_region = {**rt, "region": regions[i]}
                    all_route_tables.append(rt_with_region)

            analysis_warnings.extend(region_data.get("warnings", []))

        # If specific TGW requested, filter results
        if tgw_id:
            target_tgws = [tgw for tgw in all_tgws if tgw.get("transit_gateway_id") == tgw_id]
            if not target_tgws:
                raise ValidationError(f"Transit Gateway {tgw_id} not found in specified regions")

            all_tgws = target_tgws
            all_route_tables = [
                rt
                for rt in all_route_tables
                if any(tgw.get("transit_gateway_id") == tgw_id for tgw in target_tgws)
            ]

        # Perform enhanced analysis
        route_overlaps = []
        blackhole_routes = []
        cross_region_routes = []
        detailed_stats = None

        if detect_overlaps:
            route_overlaps = self._detect_route_overlaps(all_route_tables)

        if analyze_blackholes:
            blackhole_routes = self._identify_blackhole_routes(all_route_tables)

        if analyze_cross_region and len(regions) > 1:
            cross_region_routes = await self._analyze_cross_region_routing(
                all_route_tables, all_peering_connections, regions
            )

        if generate_stats:
            detailed_stats = self._generate_route_statistics(
                all_route_tables,
                route_overlaps,
                blackhole_routes,
                cross_region_routes,
                regions,
            )

        # Build response
        return self._create_consolidated_response(
            all_tgws=all_tgws,
            all_peering_connections=all_peering_connections,
            all_attachments=all_attachments,
            route_overlaps=route_overlaps,
            blackhole_routes=blackhole_routes,
            cross_region_routes=cross_region_routes,
            detailed_stats=detailed_stats,
            analysis_warnings=analysis_warnings,
            regions=regions,
        )

    async def _analyze_region(
        self,
        region: str,
        tgw_id: Optional[str],
        tgw_name_pattern: Optional[re.Pattern],
        cidr_filter: Optional[str],
        include_route_details: bool,
    ) -> Dict[str, Any]:
        """
        Analyze Transit Gateways in a single region.

        Args:
            region: Target region
            tgw_id: Specific TGW ID filter
            tgw_name_pattern: TGW name filter pattern
            cidr_filter: CIDR filter
            include_route_details: Include detailed route info

        Returns:
            Region analysis results
        """
        try:
            ec2_client = await self.aws_manager.get_client("ec2", region)

            # Get Transit Gateways
            describe_params = {}
            if tgw_id:
                describe_params["TransitGatewayIds"] = [tgw_id]

            tgws_response = await ec2_client.describe_transit_gateways(**describe_params)
            tgws = tgws_response.get("TransitGateways", [])

            # Filter by name pattern if specified
            if tgw_name_pattern:
                filtered_tgws = []
                for tgw in tgws:
                    tgw_name = self._get_tgw_name(tgw)
                    if tgw_name_pattern.search(tgw_name):
                        filtered_tgws.append(tgw)
                tgws = filtered_tgws

            # Analyze each TGW
            tgw_results = []
            all_peering = []
            all_attachments = []
            warnings = []

            for tgw in tgws:
                try:
                    tgw_analysis = await self._analyze_single_tgw(
                        ec2_client, tgw, cidr_filter, include_route_details
                    )
                    tgw_results.append(tgw_analysis["tgw_data"])
                    all_peering.extend(tgw_analysis["peering_connections"])
                    all_attachments.extend(tgw_analysis["attachments"])
                    warnings.extend(tgw_analysis["warnings"])
                except Exception as e:
                    warnings.append(
                        f"Failed to analyze TGW {tgw.get('TransitGatewayId', 'unknown')} in {region}: {e}"
                    )

            return {
                "tgws": tgw_results,
                "peering_connections": all_peering,
                "attachments": all_attachments,
                "warnings": warnings,
                "region": region,
            }

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            if error_code in ["UnauthorizedOperation", "AccessDenied"]:
                return {
                    "tgws": [],
                    "peering_connections": [],
                    "attachments": [],
                    "warnings": [f"Access denied for region {region}: {e}"],
                    "region": region,
                }
            raise AWSOperationError(f"Failed to analyze region {region}: {e}")

    async def _analyze_single_tgw(
        self,
        ec2_client: Any,
        tgw: Dict[str, Any],
        cidr_filter: Optional[str],
        include_route_details: bool,
    ) -> Dict[str, Any]:
        """
        Analyze a single Transit Gateway.

        Args:
            ec2_client: EC2 client
            tgw: TGW data from AWS API
            cidr_filter: CIDR filter
            include_route_details: Include detailed route info

        Returns:
            Single TGW analysis results
        """
        tgw_id = tgw["TransitGatewayId"]

        # Get route tables
        route_tables_response = await ec2_client.describe_transit_gateway_route_tables(
            Filters=[{"Name": "transit-gateway-id", "Values": [tgw_id]}]
        )
        route_tables = route_tables_response.get("TransitGatewayRouteTables", [])

        # Get attachments
        attachments_response = await ec2_client.describe_transit_gateway_attachments(
            Filters=[{"Name": "transit-gateway-id", "Values": [tgw_id]}]
        )
        attachments = attachments_response.get("TransitGatewayAttachments", [])

        # Get peering connections
        peering_response = await ec2_client.describe_transit_gateway_peering_attachments(
            Filters=[
                {"Name": "transit-gateway-id", "Values": [tgw_id]},
                {"Name": "state", "Values": ["available", "pending-acceptance"]},
            ]
        )
        peering_connections = peering_response.get("TransitGatewayPeeringAttachments", [])

        # Process route tables
        processed_route_tables = []
        warnings = []

        if include_route_details:
            for rt in route_tables:
                try:
                    rt_analysis = await self._analyze_route_table(ec2_client, rt, cidr_filter)
                    processed_route_tables.append(rt_analysis)
                except Exception as e:
                    warnings.append(
                        f"Failed to analyze route table {rt.get('TransitGatewayRouteTableId')}: {e}"
                    )

        # Create TGW data structure
        tgw_data = {
            "transit_gateway_id": tgw_id,
            "transit_gateway_arn": tgw.get("TransitGatewayArn"),
            "region": tgw.get("AvailabilityZones", [{}])[0].get("Region", "unknown"),
            "asn": tgw.get("Options", {}).get("AmazonSideAsn"),
            "state": tgw.get("State"),
            "route_tables": processed_route_tables,
            "description": tgw.get("Description", ""),
            "tags": {tag["Key"]: tag["Value"] for tag in tgw.get("Tags", [])},
        }

        # Process peering connections
        processed_peering = []
        for peering in peering_connections:
            processed_peering.append(
                {
                    "peering_attachment_id": peering.get("TransitGatewayAttachmentId"),
                    "requester_tgw_id": peering.get("RequesterTgwInfo", {}).get("TransitGatewayId"),
                    "accepter_tgw_id": peering.get("AccepterTgwInfo", {}).get("TransitGatewayId"),
                    "requester_region": peering.get("RequesterTgwInfo", {}).get("Region"),
                    "accepter_region": peering.get("AccepterTgwInfo", {}).get("Region"),
                    "state": peering.get("State"),
                    "status_code": peering.get("Status", {}).get("Code"),
                    "status_message": peering.get("Status", {}).get("Message"),
                    "creation_time": (
                        peering.get("CreationTime", "").isoformat()
                        if peering.get("CreationTime")
                        else None
                    ),
                    "tags": {tag["Key"]: tag["Value"] for tag in peering.get("Tags", [])},
                }
            )

        # Process attachments
        processed_attachments = []
        for attachment in attachments:
            processed_attachments.append(
                {
                    "attachment_id": attachment.get("TransitGatewayAttachmentId"),
                    "attachment_type": attachment.get("ResourceType"),
                    "state": attachment.get("State"),
                    "resource_arn": attachment.get("ResourceId"),
                    "tags": {tag["Key"]: tag["Value"] for tag in attachment.get("Tags", [])},
                }
            )

        return {
            "tgw_data": tgw_data,
            "peering_connections": processed_peering,
            "attachments": processed_attachments,
            "warnings": warnings,
        }

    async def _analyze_route_table(
        self, ec2_client: Any, route_table: Dict[str, Any], cidr_filter: Optional[str]
    ) -> Dict[str, Any]:
        """
        Analyze a single route table.

        Args:
            ec2_client: EC2 client
            route_table: Route table data
            cidr_filter: CIDR filter

        Returns:
            Route table analysis
        """
        rt_id = route_table["TransitGatewayRouteTableId"]

        # Get routes
        routes_response = await ec2_client.search_transit_gateway_routes(
            TransitGatewayRouteTableId=rt_id,
            Filters=[{"Name": "state", "Values": ["active", "blackhole"]}],
        )
        routes = routes_response.get("Routes", [])

        # Filter routes by CIDR if specified
        if cidr_filter:
            filtered_routes = []
            for route in routes:
                if self._matches_cidr_filter(route.get("DestinationCidrBlock", ""), cidr_filter):
                    filtered_routes.append(route)
            routes = filtered_routes

        # Get associations
        associations_response = await ec2_client.get_transit_gateway_route_table_associations(
            TransitGatewayRouteTableId=rt_id
        )
        associations = associations_response.get("Associations", [])

        # Get propagations
        propagations_response = await ec2_client.get_transit_gateway_route_table_propagations(
            TransitGatewayRouteTableId=rt_id
        )
        propagations = propagations_response.get("TransitGatewayRouteTablePropagations", [])

        # Process routes
        processed_routes = []
        for route in routes:
            route_info = {
                "destination_cidr": route.get("DestinationCidrBlock", ""),
                "state": route.get("State", ""),
                "route_type": route.get("Type", ""),
                "prefix_length": self._get_prefix_length(route.get("DestinationCidrBlock", "")),
                "target_type": None,
                "target_id": None,
                "origin": None,
            }

            # Extract target information
            attachments = route.get("TransitGatewayAttachments", [])
            if attachments:
                attachment = attachments[0]  # Use first attachment
                route_info["target_type"] = attachment.get("ResourceType")
                route_info["target_id"] = attachment.get("ResourceId")
                route_info["origin"] = attachment.get("TransitGatewayAttachmentId")

            processed_routes.append(route_info)

        return {
            "route_table_id": rt_id,
            "route_table_type": route_table.get("Type", ""),
            "state": route_table.get("State", ""),
            "default_association_route_table": route_table.get(
                "DefaultAssociationRouteTable", False
            ),
            "default_propagation_route_table": route_table.get(
                "DefaultPropagationRouteTable", False
            ),
            "creation_time": (
                route_table.get("CreationTime", "").isoformat()
                if route_table.get("CreationTime")
                else None
            ),
            "routes": processed_routes,
            "associations": [
                {
                    "attachment_id": a.get("TransitGatewayAttachmentId"),
                    "state": a.get("State"),
                }
                for a in associations
            ],
            "propagations": [
                {
                    "attachment_id": p.get("TransitGatewayAttachmentId"),
                    "state": p.get("State"),
                }
                for p in propagations
            ],
        }

    def _detect_route_overlaps(self, route_tables: List[Dict[str, Any]]) -> List[RouteOverlapInfo]:
        """
        Detect overlapping routes within Transit Gateway route tables.

        This method analyzes route tables to identify routes with overlapping CIDR blocks,
        which could lead to unpredictable routing behavior based on the longest prefix match.

        Args:
            route_tables: List of route tables with routes

        Returns:
            List of detected route overlaps with severity assessment
        """
        overlaps = []

        for rt in route_tables:
            rt_id = rt.get("route_table_id")
            region = rt.get("region")
            routes = rt.get("routes", [])

            # Analyze route pairs within the same route table
            for i, route1 in enumerate(routes):
                # Skip blackhole routes in source (these are intentional)
                if route1.get("state") == "blackhole":
                    continue

                # Convert CIDR to network for comparison
                try:
                    cidr1 = route1.get("destination_cidr", "")
                    if not cidr1:
                        continue
                    network1 = ipaddress.ip_network(cidr1)
                except ValueError:
                    continue

                # Compare with other routes
                for j in range(i + 1, len(routes)):
                    route2 = routes[j]

                    # Skip blackhole routes in target if we're looking at specific overlaps
                    # (blackhole detection is handled separately)
                    if route2.get("state") == "blackhole":
                        continue

                    # Convert CIDR to network for comparison
                    try:
                        cidr2 = route2.get("destination_cidr", "")
                        if not cidr2:
                            continue
                        network2 = ipaddress.ip_network(cidr2)
                    except ValueError:
                        continue

                    # Check for overlap
                    if (
                        network1.overlaps(network2)
                        or network2.overlaps(network1)
                        or network1 == network2
                    ):

                        # Determine overlap type and severity
                        overlap_type = "exact"
                        severity = "high"

                        if network1 == network2:
                            overlap_type = "exact"
                            severity = "high"
                        elif network1.subnet_of(network2):
                            overlap_type = "subset"
                            severity = "medium"  # Less severe as longest prefix wins
                        elif network2.subnet_of(network1):
                            overlap_type = "superset"
                            severity = "medium"
                        else:
                            overlap_type = "partial"
                            severity = "high"  # Partial overlaps can be problematic

                        # Create RouteInfo models
                        route_model1 = RouteInfo(
                            destination_cidr=route1.get("destination_cidr"),
                            state=route1.get("state"),
                            route_type=route1.get("route_type"),
                            target_type=route1.get("target_type"),
                            target_id=route1.get("target_id"),
                            origin=route1.get("origin"),
                            prefix_length=route1.get("prefix_length", 0),
                        )

                        route_model2 = RouteInfo(
                            destination_cidr=route2.get("destination_cidr"),
                            state=route2.get("state"),
                            route_type=route2.get("route_type"),
                            target_type=route2.get("target_type"),
                            target_id=route2.get("target_id"),
                            origin=route2.get("origin"),
                            prefix_length=route2.get("prefix_length", 0),
                        )

                        # Create overlap info
                        overlap = RouteOverlapInfo(
                            route1=route_model1,
                            route2=route_model2,
                            overlap_type=overlap_type,
                            route_table_id=rt_id,
                            region=region,
                            severity=severity,
                        )

                        overlaps.append(overlap)

        return overlaps

    def _identify_blackhole_routes(
        self, route_tables: List[Dict[str, Any]]
    ) -> List[BlackholeRouteInfo]:
        """
        Identify blackhole routes and assess their impact.

        This method analyzes route tables to identify blackhole routes and determine
        which CIDRs might be affected by them, especially in cases where more specific
        routes are being overridden by blackhole routes.

        Args:
            route_tables: List of route tables with routes

        Returns:
            List of blackhole routes with impact assessment
        """
        blackhole_infos = []

        for rt in route_tables:
            rt_id = rt.get("route_table_id")
            region = rt.get("region")
            routes = rt.get("routes", [])

            # Find blackhole routes
            for route in routes:
                if route.get("state") != "blackhole":
                    continue

                # Convert CIDR to network for comparison
                try:
                    cidr = route.get("destination_cidr", "")
                    if not cidr:
                        continue
                    network = ipaddress.ip_network(cidr)
                except ValueError:
                    continue

                # Find affected prefixes (routes that might be overridden)
                affected_prefixes = []

                for other_route in routes:
                    if other_route.get("state") == "blackhole":
                        continue

                    try:
                        other_cidr = other_route.get("destination_cidr", "")
                        if not other_cidr:
                            continue
                        other_network = ipaddress.ip_network(other_cidr)
                    except ValueError:
                        continue

                    # Check if other route is affected by this blackhole
                    if other_network.subnet_of(network) and other_network != network:
                        affected_prefixes.append(other_cidr)

                # Determine impact level
                impact_level = "low"
                if affected_prefixes:
                    impact_level = "high"
                elif network.prefixlen < 16:  # Large CIDR blocks
                    impact_level = "medium"

                # Create RouteInfo model
                route_model = RouteInfo(
                    destination_cidr=route.get("destination_cidr"),
                    state=route.get("state"),
                    route_type=route.get("route_type"),
                    target_type=route.get("target_type"),
                    target_id=route.get("target_id"),
                    origin=route.get("origin"),
                    prefix_length=route.get("prefix_length", 0),
                )

                # Create blackhole info
                blackhole_info = BlackholeRouteInfo(
                    route=route_model,
                    route_table_id=rt_id,
                    region=region,
                    impact_level=impact_level,
                    affected_prefixes=affected_prefixes,
                )

                blackhole_infos.append(blackhole_info)

        return blackhole_infos

    async def _analyze_cross_region_routing(
        self,
        route_tables: List[Dict[str, Any]],
        peering_connections: List[Dict[str, Any]],
        regions: List[str],
    ) -> List[CrossRegionRouteInfo]:
        """
        Analyze cross-region routing paths via Transit Gateway peering.

        This method identifies routes that traverse region boundaries via
        Transit Gateway peering connections and analyzes the routing path.

        Args:
            route_tables: List of route tables with routes
            peering_connections: List of peering connections
            regions: List of regions being analyzed

        Returns:
            List of cross-region routes with path information
        """
        cross_region_routes = []

        # Map peering connections by attachment ID for lookup
        peering_by_attachment = {}
        for peering in peering_connections:
            attachment_id = peering.get("peering_attachment_id")
            if attachment_id:
                peering_by_attachment[attachment_id] = peering

        # Find routes that target peering attachments
        for rt in route_tables:
            rt_id = rt.get("route_table_id")
            source_region = rt.get("region")
            routes = rt.get("routes", [])

            for route in routes:
                # Check if this route targets a peering attachment
                origin = route.get("origin")
                if not origin or origin not in peering_by_attachment:
                    continue

                # Get the peering connection details
                peering = peering_by_attachment[origin]
                target_region = None

                # Determine the target region
                if peering.get("requester_region") == source_region:
                    target_region = peering.get("accepter_region")
                    target_tgw_id = peering.get("accepter_tgw_id")
                else:
                    target_region = peering.get("requester_region")
                    target_tgw_id = peering.get("requester_tgw_id")

                # Skip if target region not in our analysis
                if target_region not in regions:
                    continue

                # Create RouteInfo model
                route_model = RouteInfo(
                    destination_cidr=route.get("destination_cidr"),
                    state=route.get("state"),
                    route_type=route.get("route_type"),
                    target_type=route.get("target_type"),
                    target_id=route.get("target_id"),
                    origin=origin,
                    prefix_length=route.get("prefix_length", 0),
                )

                # Create cross-region route info
                cross_region_info = CrossRegionRouteInfo(
                    source_region=source_region,
                    destination_region=target_region,
                    route=route_model,
                    route_table_id=rt_id,
                    peering_attachment_id=origin,
                    target_tgw_id=target_tgw_id,
                    hops_count=1,  # Basic hop count, could be enhanced with path tracing
                )

                cross_region_routes.append(cross_region_info)

        return cross_region_routes

    def _generate_route_statistics(
        self,
        route_tables: List[Dict[str, Any]],
        route_overlaps: List[RouteOverlapInfo],
        blackhole_routes: List[BlackholeRouteInfo],
        cross_region_routes: List[CrossRegionRouteInfo],
        regions: List[str],
    ) -> RouteSummaryStats:
        """
        Generate comprehensive route statistics.

        This method compiles statistics on routes across Transit Gateways,
        including counts by type, state, and analysis of routing issues.

        Args:
            route_tables: List of route tables with routes
            route_overlaps: List of detected route overlaps
            blackhole_routes: List of blackhole routes
            cross_region_routes: List of cross-region routes
            regions: List of regions analyzed

        Returns:
            Detailed route statistics
        """
        stats = RouteSummaryStats(regions_analyzed=regions)

        # Route table count
        stats.route_tables_analyzed = len(route_tables)

        # Initialize counters
        total_routes = 0
        active_routes = 0
        blackhole_count = 0
        pending_routes = 0
        static_routes = 0
        propagated_routes = 0

        # Track most/least specific prefixes
        min_prefix_length = 32
        max_prefix_length = 0
        most_specific_cidr = None
        least_specific_cidr = None

        # Process routes
        for rt in route_tables:
            routes = rt.get("routes", [])
            for route in routes:
                total_routes += 1

                # Count by state
                state = route.get("state", "").lower()
                if state == "active":
                    active_routes += 1
                elif state == "blackhole":
                    blackhole_count += 1
                elif state == "pending":
                    pending_routes += 1

                # Count by type
                route_type = route.get("route_type", "").lower()
                if route_type == "static":
                    static_routes += 1
                elif route_type == "propagated":
                    propagated_routes += 1

                # Track prefix specificity
                prefix_length = route.get("prefix_length", 0)
                cidr = route.get("destination_cidr", "")

                if prefix_length < min_prefix_length and cidr:
                    min_prefix_length = prefix_length
                    least_specific_cidr = cidr

                if prefix_length > max_prefix_length and cidr:
                    max_prefix_length = prefix_length
                    most_specific_cidr = cidr

        # Set statistics
        stats.total_routes = total_routes
        stats.active_routes = active_routes
        stats.blackhole_routes = blackhole_count
        stats.pending_routes = pending_routes
        stats.static_routes = static_routes
        stats.propagated_routes = propagated_routes
        stats.cross_region_routes = len(cross_region_routes)
        stats.overlapping_routes = len(route_overlaps)
        stats.most_specific_prefix = most_specific_cidr
        stats.least_specific_prefix = least_specific_cidr

        return stats

    def _matches_cidr_filter(self, destination_cidr: str, cidr_filter: str) -> bool:
        """
        Check if destination CIDR matches the filter.

        Args:
            destination_cidr: CIDR to check
            cidr_filter: CIDR filter to match against

        Returns:
            True if CIDR matches filter, False otherwise
        """
        if not cidr_filter or not destination_cidr:
            return True

        try:
            # Exact match
            if destination_cidr == cidr_filter:
                return True

            # Network containment check
            dest_network = ipaddress.ip_network(destination_cidr)
            filter_network = ipaddress.ip_network(cidr_filter, strict=False)

            return dest_network.subnet_of(filter_network) or filter_network.subnet_of(dest_network)
        except ValueError:
            # Fallback to string matching
            return cidr_filter.lower() in destination_cidr.lower()

    def _get_prefix_length(self, cidr: str) -> int:
        """
        Extract prefix length from CIDR block.

        Args:
            cidr: CIDR block string (e.g., "10.0.0.0/16")

        Returns:
            int: Prefix length as integer (e.g., 16), or 32 if not specified
        """
        try:
            return int(cidr.split("/")[1]) if "/" in cidr else 32
        except (ValueError, IndexError):
            return 32

    def _get_tgw_name(self, tgw: Dict[str, Any]) -> str:
        """
        Get Transit Gateway name from tags or ID.

        Args:
            tgw: Transit Gateway data

        Returns:
            Transit Gateway name or ID if name not found
        """
        tags = tgw.get("Tags", [])
        for tag in tags:
            if tag.get("Key", "").lower() == "name":
                return tag.get("Value", "")
        return tgw.get("TransitGatewayId", "")

    def _create_consolidated_response(
        self,
        all_tgws: List[Dict[str, Any]],
        all_peering_connections: List[Dict[str, Any]],
        all_attachments: List[Dict[str, Any]],
        route_overlaps: List[RouteOverlapInfo],
        blackhole_routes: List[BlackholeRouteInfo],
        cross_region_routes: List[CrossRegionRouteInfo],
        detailed_stats: Optional[RouteSummaryStats],
        analysis_warnings: List[str],
        regions: List[str],
    ) -> TGWRouteAnalysisResponse:
        """
        Create consolidated response for multiple TGWs.

        Args:
            all_tgws: List of TGWs analyzed
            all_peering_connections: List of peering connections
            all_attachments: List of attachments
            route_overlaps: List of route overlaps
            blackhole_routes: List of blackhole routes
            cross_region_routes: List of cross-region routes
            detailed_stats: Detailed route statistics
            analysis_warnings: List of analysis warnings
            regions: List of regions analyzed

        Returns:
            Consolidated TGW route analysis response
        """
        if not all_tgws:
            raise ValidationError("No Transit Gateways found matching the specified criteria")

        # Use first TGW as primary for response structure
        primary_tgw = all_tgws[0]

        # Calculate combined route summary
        route_summary = {"active": 0, "blackhole": 0, "pending": 0}
        for tgw in all_tgws:
            for rt in tgw.get("route_tables", []):
                for route in rt.get("routes", []):
                    state = route.get("state", "").lower()
                    if state in route_summary:
                        route_summary[state] += 1

        # Build consolidated response model
        primary_region = primary_tgw.get("region", "multiple")
        is_multi_region = len(regions) > 1

        # Create route table models
        route_tables = []
        for tgw in all_tgws:
            for rt_data in tgw.get("route_tables", []):
                routes = [RouteInfo(**route) for route in rt_data.get("routes", [])]
                route_tables.append(
                    TGWRouteTableInfo(
                        route_table_id=rt_data["route_table_id"],
                        route_table_type=rt_data["route_table_type"],
                        state=rt_data["state"],
                        default_association_route_table=rt_data.get(
                            "default_association_route_table", False
                        ),
                        default_propagation_route_table=rt_data.get(
                            "default_propagation_route_table", False
                        ),
                        creation_time=rt_data.get("creation_time"),
                        routes=routes,
                        associations=rt_data.get("associations", []),
                        propagations=rt_data.get("propagations", []),
                    )
                )

        # Create attachment models
        peering_models = [TGWPeeringInfo(**pc) for pc in all_peering_connections]
        attachment_models = [AttachmentInfo(**att) for att in all_attachments]

        # Create response model
        return TGWRouteAnalysisResponse(
            transit_gateway_id=(
                primary_tgw["transit_gateway_id"]
                if len(all_tgws) == 1
                else f"MULTIPLE_TGWS_{len(all_tgws)}"
            ),
            transit_gateway_arn=(
                primary_tgw["transit_gateway_arn"]
                if len(all_tgws) == 1
                else "arn:aws:ec2::multiple"
            ),
            region=primary_region if not is_multi_region else "multiple",
            asn=primary_tgw.get("asn") if len(all_tgws) == 1 else None,
            state=primary_tgw["state"] if len(all_tgws) == 1 else "multiple",
            route_tables=route_tables,
            peering_connections=peering_models,
            attachments=attachment_models,
            route_summary=route_summary,
            cross_account_routes=[],  # Placeholder for future implementation
            analysis_warnings=analysis_warnings,
            route_overlaps=route_overlaps,
            blackhole_routes=blackhole_routes,
            cross_region_routes=cross_region_routes,
            detailed_stats=detailed_stats,
            regions_analyzed=regions,
            timestamp=datetime.now(),
            status="success" if not analysis_warnings else "partial",
        )
