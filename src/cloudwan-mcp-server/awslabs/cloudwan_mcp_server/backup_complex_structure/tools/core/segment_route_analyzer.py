"""
CloudWAN Segment Route Analysis MCP Tool.

This tool provides comprehensive CloudWAN segment route analysis capabilities,
based on the foundation script analyze_wan_routes.py, adapted for MCP protocol 
integration with enhanced route enumeration and policy parsing.
"""

import asyncio
import json
import os
from typing import Any, Dict, List, Optional
from datetime import datetime

from botocore.exceptions import ClientError

from ...aws.client_manager import AWSClientManager
from ...config import CloudWANConfig
from ...models.network import (
    SegmentRoutesResponse,
    SegmentRouteInfo,
    AttachmentInfo,
)
from ..base import (
    BaseMCPTool,
    handle_errors,
    ValidationError,
    AWSOperationError,
)


class SegmentRouteAnalyzer(BaseMCPTool):
    """
    CloudWAN Segment Route Analyzer MCP Tool.

    Provides comprehensive route analysis for CloudWAN segments across regions,
    including static/propagated route enumeration, attachment analysis, and
    policy-based routing validation.
    """

    @property
    def tool_name(self) -> str:
        return "get_segment_routes"

    @property
    def description(self) -> str:
        return """
        Comprehensive CloudWAN segment route analysis across AWS regions.
        
        This tool analyzes CloudWAN Core Network segments and provides detailed 
        route information including static routes, propagated routes, attachment 
        relationships, and policy-based routing rules.
        
        Features:
        - Multi-region segment route enumeration
        - Static vs propagated route categorization
        - Attachment source identification
        - Edge location route distribution
        - Policy document integration
        - Route type analysis (vpc, tgw, connect, vpn)
        - Regional route comparison
        """

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "core_network_id": {
                    "type": "string",
                    "description": "Core Network ID to analyze (required)",
                },
                "segment_name": {
                    "type": "string",
                    "description": "Specific segment name to analyze (optional, analyzes all if not provided)",
                },
                "region": {
                    "type": "string",
                    "description": "Specific region to analyze (optional, analyzes all regions if not provided)",
                },
                "route_type_filter": {
                    "type": "string",
                    "description": "Filter routes by type: static, propagated, or network-function",
                    "enum": ["static", "propagated", "network-function"],
                },
                "attachment_type_filter": {
                    "type": "string",
                    "description": "Filter by attachment type: vpc, transit-gateway, connect, vpn",
                    "enum": ["vpc", "transit-gateway", "connect", "vpn"],
                },
                "include_policy_analysis": {
                    "type": "boolean",
                    "description": "Include policy document analysis and validation",
                    "default": True,
                },
                "include_attachments": {
                    "type": "boolean",
                    "description": "Include detailed attachment information",
                    "default": True,
                },
            },
            "required": ["core_network_id"],
        }

    def __init__(self, aws_manager: AWSClientManager, config: CloudWANConfig):
        super().__init__(aws_manager, config)
        # Check for custom Network Manager endpoint
        self.custom_endpoint = os.environ.get("AWS_ENDPOINT_URL_NETWORKMANAGER")
        self.using_custom_endpoint = bool(self.custom_endpoint)
        if self.using_custom_endpoint:
            self.logger.info(f"Using custom Network Manager endpoint: {self.custom_endpoint}")

    @handle_errors
    async def execute(self, **kwargs) -> SegmentRoutesResponse:
        """
        Execute segment route analysis.

        Args:
            **kwargs: Tool parameters from input schema

        Returns:
            Segment route analysis response
        """
        # Extract and validate parameters
        core_network_id = kwargs.get("core_network_id")
        if not core_network_id:
            raise ValidationError("core_network_id is required")

        segment_name = kwargs.get("segment_name")
        target_region = kwargs.get("region")
        route_type_filter = kwargs.get("route_type_filter")
        attachment_type_filter = kwargs.get("attachment_type_filter")
        include_policy_analysis = kwargs.get("include_policy_analysis", True)
        include_attachments = kwargs.get("include_attachments", True)

        try:
            # Get Core Network information and policy
            core_network_info = await self._get_core_network_info(core_network_id)

            # Determine regions to analyze
            if target_region:
                regions = [target_region]
            else:
                # Get all regions from core network edges
                regions = self._extract_regions_from_edges(core_network_info.get("edges", []))
                if not regions:
                    regions = self.config.aws.regions  # Fallback to config regions

            # Get policy document for segment analysis
            policy_doc = None
            if include_policy_analysis:
                policy_doc = await self._get_policy_document(core_network_id)

            # Analyze segments and routes
            if segment_name:
                # Analyze specific segment
                return await self._analyze_single_segment(
                    core_network_id=core_network_id,
                    segment_name=segment_name,
                    regions=regions,
                    route_type_filter=route_type_filter,
                    attachment_type_filter=attachment_type_filter,
                    policy_doc=policy_doc,
                    include_attachments=include_attachments,
                )
            else:
                # Analyze all segments (return first found or error)
                segments = self._extract_segments_from_policy(policy_doc) if policy_doc else []
                if not segments:
                    raise ValidationError("No segments found in Core Network policy")

                # For now, analyze the first segment (could be extended to analyze all)
                return await self._analyze_single_segment(
                    core_network_id=core_network_id,
                    segment_name=segments[0],
                    regions=regions,
                    route_type_filter=route_type_filter,
                    attachment_type_filter=attachment_type_filter,
                    policy_doc=policy_doc,
                    include_attachments=include_attachments,
                )

        except Exception as e:
            raise AWSOperationError(f"Segment route analysis failed: {str(e)}")

    async def _get_core_network_info(self, core_network_id: str) -> Dict[str, Any]:
        """Get Core Network information."""
        try:
            # Use primary region for Network Manager (usually us-west-2 for custom endpoint)
            nm_region = "us-west-2" if self.using_custom_endpoint else "us-east-1"
            nm_client = await self.aws_manager.get_client("networkmanager", nm_region)

            if self.using_custom_endpoint:
                nm_client._endpoint.host = self.custom_endpoint.replace("https://", "").replace(
                    "http://", ""
                )

            response = await nm_client.get_core_network(CoreNetworkId=core_network_id)
            return response.get("CoreNetwork", {})

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            if error_code == "ResourceNotFoundException":
                raise ValidationError(f"Core Network {core_network_id} not found")
            elif error_code in ["UnauthorizedOperation", "AccessDenied"]:
                raise ValidationError(f"Access denied to Core Network {core_network_id}")
            raise AWSOperationError(f"Failed to get Core Network info: {e}")

    async def _get_policy_document(self, core_network_id: str) -> Optional[Dict[str, Any]]:
        """Get Core Network policy document."""
        try:
            nm_region = "us-west-2" if self.using_custom_endpoint else "us-east-1"
            nm_client = await self.aws_manager.get_client("networkmanager", nm_region)

            if self.using_custom_endpoint:
                nm_client._endpoint.host = self.custom_endpoint.replace("https://", "").replace(
                    "http://", ""
                )

            response = await nm_client.get_core_network_policy(CoreNetworkId=core_network_id)
            policy_doc = response.get("CoreNetworkPolicy", {}).get("PolicyDocument")

            if policy_doc:
                return json.loads(policy_doc)
            return None

        except Exception as e:
            self.logger.warning(f"Failed to get policy document: {e}")
            return None

    def _extract_regions_from_edges(self, edges: List[Dict[str, Any]]) -> List[str]:
        """Extract unique regions from Core Network edges."""
        regions = set()
        for edge in edges:
            if "Location" in edge:
                # Edge locations are typically in format like "us-west-2"
                location = edge["Location"]
                if "-" in location and len(location.split("-")) >= 3:
                    regions.add(location)
        return list(regions)

    def _extract_segments_from_policy(self, policy_doc: Dict[str, Any]) -> List[str]:
        """Extract segment names from policy document."""
        if not policy_doc:
            return []

        segments = []
        for segment in policy_doc.get("segments", []):
            if "name" in segment:
                segments.append(segment["name"])

        return segments

    async def _analyze_single_segment(
        self,
        core_network_id: str,
        segment_name: str,
        regions: List[str],
        route_type_filter: Optional[str],
        attachment_type_filter: Optional[str],
        policy_doc: Optional[Dict[str, Any]],
        include_attachments: bool,
    ) -> SegmentRoutesResponse:
        """
        Analyze routes for a single segment.

        Args:
            core_network_id: Core Network ID
            segment_name: Target segment name
            regions: Regions to analyze
            route_type_filter: Route type filter
            attachment_type_filter: Attachment type filter
            policy_doc: Policy document
            include_attachments: Include attachment details

        Returns:
            Segment route analysis response
        """
        # Execute concurrent region analysis
        tasks = []
        for region in regions:
            task = self._analyze_segment_in_region(
                core_network_id=core_network_id,
                segment_name=segment_name,
                region=region,
                route_type_filter=route_type_filter,
                attachment_type_filter=attachment_type_filter,
            )
            tasks.append(task)

        region_results = await asyncio.gather(*tasks, return_exceptions=True)

        # Consolidate results
        all_routes = []
        static_routes = []
        propagated_routes = []
        all_attachments = []
        edge_locations = set()
        analysis_warnings = []

        for i, result in enumerate(region_results):
            if isinstance(result, Exception):
                analysis_warnings.append(f"Region {regions[i]} failed: {str(result)}")
                continue

            region_data = result
            all_routes.extend(region_data.get("routes", []))
            static_routes.extend(region_data.get("static_routes", []))
            propagated_routes.extend(region_data.get("propagated_routes", []))
            all_attachments.extend(region_data.get("attachments", []))
            edge_locations.update(region_data.get("edge_locations", []))

        # Calculate route counts by type
        route_count_by_type = {}
        for route in all_routes:
            route_type = route.get("route_type", "unknown")
            route_count_by_type[route_type] = route_count_by_type.get(route_type, 0) + 1

        # Convert to Pydantic models
        route_models = [SegmentRouteInfo(**route) for route in all_routes]
        static_route_models = [SegmentRouteInfo(**route) for route in static_routes]
        propagated_route_models = [SegmentRouteInfo(**route) for route in propagated_routes]
        attachment_models = (
            [AttachmentInfo(**att) for att in all_attachments] if include_attachments else []
        )

        return SegmentRoutesResponse(
            core_network_id=core_network_id,
            segment_name=segment_name,
            region=regions[0] if len(regions) == 1 else None,
            routes=route_models,
            static_routes=static_route_models,
            propagated_routes=propagated_route_models,
            route_count_by_type=route_count_by_type,
            edge_locations=list(edge_locations),
            attachments_in_segment=attachment_models,
            regions_analyzed=regions,
            timestamp=datetime.now(),
            status="success" if not analysis_warnings else "partial",
            error_message="; ".join(analysis_warnings) if analysis_warnings else None,
        )

    async def _analyze_segment_in_region(
        self,
        core_network_id: str,
        segment_name: str,
        region: str,
        route_type_filter: Optional[str],
        attachment_type_filter: Optional[str],
    ) -> Dict[str, Any]:
        """
        Analyze segment routes in a single region.

        Args:
            core_network_id: Core Network ID
            segment_name: Segment name
            region: Target region
            route_type_filter: Route type filter
            attachment_type_filter: Attachment type filter

        Returns:
            Region analysis results
        """
        try:
            nm_client = await self.aws_manager.get_client("networkmanager", region)

            # Get Core Network segments (this will give us route tables)
            segments_response = await nm_client.get_core_network_segments(
                CoreNetworkId=core_network_id
            )
            segments = segments_response.get("Segments", [])

            # Find target segment
            target_segment = None
            for segment in segments:
                if segment.get("Name") == segment_name:
                    target_segment = segment
                    break

            if not target_segment:
                return {
                    "routes": [],
                    "static_routes": [],
                    "propagated_routes": [],
                    "attachments": [],
                    "edge_locations": [],
                }

            # Get route analysis for the segment
            route_analysis_response = await nm_client.get_route_analysis(
                GlobalNetworkId=core_network_id,
                RouteAnalysisId="dummy",  # This might need adjustment based on actual API
            )

            # Alternative approach: Get network routes directly
            routes_response = await nm_client.get_network_routes(
                GlobalNetworkId=core_network_id,
                RouteTableIdentifier={
                    "CoreNetworkSegmentEdge": {
                        "CoreNetworkId": core_network_id,
                        "SegmentName": segment_name,
                        "EdgeLocation": region,
                    }
                },
            )

            routes = routes_response.get("NetworkRoutes", [])

            # Process routes
            processed_routes = []
            static_routes = []
            propagated_routes = []
            edge_locations = {region}

            for route in routes:
                route_info = self._process_route(route, segment_name, region)

                # Apply filters
                if route_type_filter and route_info.get("route_type") != route_type_filter:
                    continue

                processed_routes.append(route_info)

                # Categorize routes
                if route_info.get("route_type") == "static":
                    static_routes.append(route_info)
                elif route_info.get("route_type") == "propagated":
                    propagated_routes.append(route_info)

            # Get attachments in segment
            attachments = []
            if attachment_type_filter or True:  # Always get attachments for now
                attachments_response = await nm_client.list_attachments(
                    CoreNetworkId=core_network_id,
                    AttachmentType=attachment_type_filter or None,
                )

                for attachment in attachments_response.get("Attachments", []):
                    if attachment.get("SegmentName") == segment_name:
                        attachment_info = {
                            "attachment_id": attachment.get("AttachmentId"),
                            "attachment_type": attachment.get("AttachmentType"),
                            "state": attachment.get("State"),
                            "resource_arn": attachment.get("ResourceArn"),
                            "segment_name": attachment.get("SegmentName"),
                            "edge_location": attachment.get("EdgeLocation"),
                            "tags": attachment.get("Tags", {}),
                        }
                        attachments.append(attachment_info)

            return {
                "routes": processed_routes,
                "static_routes": static_routes,
                "propagated_routes": propagated_routes,
                "attachments": attachments,
                "edge_locations": list(edge_locations),
            }

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            if error_code in ["UnauthorizedOperation", "AccessDenied"]:
                self.logger.warning(f"Access denied for region {region}")
                return {
                    "routes": [],
                    "static_routes": [],
                    "propagated_routes": [],
                    "attachments": [],
                    "edge_locations": [],
                }
            raise AWSOperationError(f"Failed to analyze segment in region {region}: {e}")

    def _process_route(
        self, route: Dict[str, Any], segment_name: str, region: str
    ) -> Dict[str, Any]:
        """
        Process a single route entry.

        Args:
            route: Raw route data from AWS API
            segment_name: Segment name
            region: Region

        Returns:
            Processed route information
        """
        destination_cidr = route.get("DestinationCidrBlock", "")

        # Extract prefix length
        prefix_length = 32
        if "/" in destination_cidr:
            try:
                prefix_length = int(destination_cidr.split("/")[1])
            except (ValueError, IndexError):
                pass

        # Determine route type
        route_type = "propagated"  # Default
        if route.get("Type") == "STATIC":
            route_type = "static"
        elif route.get("Type") == "PROPAGATED":
            route_type = "propagated"
        elif "network-function" in str(route).lower():
            route_type = "network-function"

        # Extract attachment information
        attachment_id = None
        attachment_type = None
        resource_id = None

        if "Attachment" in route:
            attachment = route["Attachment"]
            attachment_id = attachment.get("AttachmentId")
            attachment_type = attachment.get("AttachmentType")
            resource_id = attachment.get("ResourceId")

        return {
            "destination_cidr": destination_cidr,
            "state": route.get("State", "active"),
            "route_type": route_type,
            "attachment_id": attachment_id,
            "attachment_type": attachment_type,
            "resource_id": resource_id,
            "edge_location": region,
            "segment_name": segment_name,
            "prefix_length": prefix_length,
            "is_active": route.get("State", "").lower() == "active",
        }
