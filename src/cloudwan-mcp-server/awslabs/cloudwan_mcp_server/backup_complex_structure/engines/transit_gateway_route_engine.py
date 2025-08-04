"""
Transit Gateway Route Analysis Engine.

This engine provides comprehensive Transit Gateway route analysis capabilities,
implementing proven patterns from legacy scripts with modern async/await interfaces
and enhanced error handling.

Features:
- Route precedence and longest-prefix matching algorithms
- Route state analysis (active, blackhole, pending)
- CIDR filtering and route categorization
- Multi-region concurrent route analysis
- Route conflict and overlap detection
- Performance optimized with caching
"""

import asyncio
import ipaddress
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

from botocore.exceptions import ClientError

from ..aws.client_manager import AWSClientManager
from ..config import CloudWANConfig
from .async_executor_bridge import AsyncExecutorBridge


class RouteState(str, Enum):
    """Transit Gateway route states."""

    ACTIVE = "active"
    BLACKHOLE = "blackhole"
    PENDING = "pending"
    FAILED = "failed"


class RouteType(str, Enum):
    """Transit Gateway route types."""

    STATIC = "static"
    PROPAGATED = "propagated"
    CONNECT = "connect"
    PEERING = "peering"


@dataclass
class RouteEntry:
    """Enhanced route entry with analysis metadata."""

    destination_cidr: str
    state: RouteState
    route_type: RouteType
    prefix_length: int
    target_type: Optional[str] = None
    target_id: Optional[str] = None
    origin: Optional[str] = None
    attachment_id: Optional[str] = None
    priority: int = 0  # Route priority for conflict resolution
    created_time: Optional[datetime] = None
    last_updated: Optional[datetime] = None
    is_best_path: bool = False
    conflicts: List[str] = field(default_factory=list)

    def __post_init__(self):
        """Calculate prefix length and priority after initialization."""
        if not self.prefix_length:
            self.prefix_length = self._calculate_prefix_length()
        if not self.priority:
            self.priority = self._calculate_priority()

    def _calculate_prefix_length(self) -> int:
        """Calculate prefix length from CIDR."""
        try:
            return int(self.destination_cidr.split("/")[1]) if "/" in self.destination_cidr else 32
        except (ValueError, IndexError):
            return 32

    def _calculate_priority(self) -> int:
        """Calculate route priority for longest-prefix matching."""
        # Higher prefix length = higher priority (more specific)
        base_priority = self.prefix_length * 100

        # Route type priorities
        type_priorities = {
            RouteType.STATIC: 1000,
            RouteType.CONNECT: 800,
            RouteType.PEERING: 600,
            RouteType.PROPAGATED: 400,
        }

        return base_priority + type_priorities.get(self.route_type, 0)


@dataclass
class RouteTableAnalysis:
    """Comprehensive route table analysis results."""

    route_table_id: str
    transit_gateway_id: str
    region: str
    route_entries: List[RouteEntry] = field(default_factory=list)
    associations: List[Dict[str, Any]] = field(default_factory=list)
    propagations: List[Dict[str, Any]] = field(default_factory=list)
    route_conflicts: List[Dict[str, Any]] = field(default_factory=list)
    route_summary: Dict[str, int] = field(default_factory=dict)
    performance_metrics: Dict[str, Any] = field(default_factory=dict)
    last_analyzed: Optional[datetime] = None


class TransitGatewayRouteEngine:
    """
    High-performance Transit Gateway route analysis engine.

    Provides comprehensive route analysis with longest-prefix matching,
    conflict detection, and performance optimization through caching.
    """

    def __init__(self, aws_manager: AWSClientManager, config: CloudWANConfig):
        """
        Initialize the route engine.

        Args:
            aws_manager: AWS client manager instance
            config: CloudWAN configuration
        """
        self.aws_manager = aws_manager
        self.config = config
        self.legacy_adapter = AsyncExecutorBridge(aws_manager, config)

        # Performance optimization
        self._route_cache: Dict[str, Tuple[RouteTableAnalysis, datetime]] = {}
        self._cache_ttl = timedelta(minutes=5)  # Cache for 5 minutes

        # Thread pool for CPU-intensive route analysis
        self._executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="TGWRoute")

    async def analyze_route_tables(
        self,
        transit_gateway_id: str,
        region: str,
        cidr_filter: Optional[str] = None,
        include_associations: bool = True,
        enable_caching: bool = True,
    ) -> List[RouteTableAnalysis]:
        """
        Analyze all route tables for a Transit Gateway.

        Args:
            transit_gateway_id: TGW ID to analyze
            region: AWS region
            cidr_filter: Optional CIDR filter
            include_associations: Include associations and propagations
            enable_caching: Enable result caching

        Returns:
            List of route table analyses
        """
        start_time = datetime.now()

        try:
            # Check cache first
            cache_key = f"{transit_gateway_id}:{region}:{cidr_filter or 'all'}"
            if enable_caching and cache_key in self._route_cache:
                cached_result, cached_time = self._route_cache[cache_key]
                if datetime.now() - cached_time < self._cache_ttl:
                    return [cached_result]

            # Get EC2 client
            ec2_client = await self.aws_manager.get_client("ec2", region)

            # Get route tables for TGW
            route_tables_response = await ec2_client.describe_transit_gateway_route_tables(
                Filters=[{"Name": "transit-gateway-id", "Values": [transit_gateway_id]}]
            )
            route_tables = route_tables_response.get("TransitGatewayRouteTables", [])

            # Analyze each route table concurrently
            analysis_tasks = []
            for rt in route_tables:
                task = self._analyze_single_route_table(
                    ec2_client=ec2_client,
                    route_table_id=rt["TransitGatewayRouteTableId"],
                    transit_gateway_id=transit_gateway_id,
                    region=region,
                    cidr_filter=cidr_filter,
                    include_associations=include_associations,
                )
                analysis_tasks.append(task)

            # Execute concurrent analysis
            analyses = await asyncio.gather(*analysis_tasks, return_exceptions=True)

            # Filter out exceptions and process results
            valid_analyses = []
            for analysis in analyses:
                if isinstance(analysis, Exception):
                    continue

                # Perform route conflict detection
                await self._detect_route_conflicts(analysis)

                # Update performance metrics
                analysis.performance_metrics = {
                    "analysis_duration_ms": (datetime.now() - start_time).total_seconds() * 1000,
                    "route_count": len(analysis.route_entries),
                    "conflict_count": len(analysis.route_conflicts),
                }
                analysis.last_analyzed = datetime.now()

                valid_analyses.append(analysis)

                # Cache the result
                if enable_caching:
                    self._route_cache[cache_key] = (analysis, datetime.now())

            return valid_analyses

        except Exception as e:
            raise RuntimeError(f"Route table analysis failed: {str(e)}")

    async def _analyze_single_route_table(
        self,
        ec2_client: Any,
        route_table_id: str,
        transit_gateway_id: str,
        region: str,
        cidr_filter: Optional[str] = None,
        include_associations: bool = True,
    ) -> RouteTableAnalysis:
        """
        Analyze a single route table with comprehensive route processing.

        Args:
            ec2_client: EC2 client instance
            route_table_id: Route table ID
            transit_gateway_id: TGW ID
            region: AWS region
            cidr_filter: Optional CIDR filter
            include_associations: Include associations and propagations

        Returns:
            Route table analysis
        """
        analysis = RouteTableAnalysis(
            route_table_id=route_table_id,
            transit_gateway_id=transit_gateway_id,
            region=region,
        )

        try:
            # Get routes with concurrent processing
            routes_task = self._get_route_entries(ec2_client, route_table_id, cidr_filter)

            # Get associations and propagations if requested
            associations_task = None
            propagations_task = None
            if include_associations:
                associations_task = self._get_route_table_associations(ec2_client, route_table_id)
                propagations_task = self._get_route_table_propagations(ec2_client, route_table_id)

            # Execute concurrent operations
            route_entries = await routes_task

            if associations_task and propagations_task:
                associations, propagations = await asyncio.gather(
                    associations_task, propagations_task, return_exceptions=True
                )

                analysis.associations = (
                    associations if not isinstance(associations, Exception) else []
                )
                analysis.propagations = (
                    propagations if not isinstance(propagations, Exception) else []
                )

            # Process and enhance route entries
            analysis.route_entries = await self._process_route_entries(route_entries)

            # Calculate route summary
            analysis.route_summary = self._calculate_route_summary(analysis.route_entries)

            return analysis

        except Exception as e:
            raise RuntimeError(f"Single route table analysis failed for {route_table_id}: {str(e)}")

    async def _get_route_entries(
        self, ec2_client: Any, route_table_id: str, cidr_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get route entries from a route table with filtering.

        Args:
            ec2_client: EC2 client
            route_table_id: Route table ID
            cidr_filter: Optional CIDR filter

        Returns:
            List of raw route entries
        """
        try:
            response = await ec2_client.search_transit_gateway_routes(
                TransitGatewayRouteTableId=route_table_id,
                Filters=[{"Name": "state", "Values": ["active", "blackhole", "pending"]}],
            )

            routes = response.get("Routes", [])

            # Apply CIDR filter if specified
            if cidr_filter:
                filtered_routes = []
                for route in routes:
                    if self._matches_cidr_filter(
                        route.get("DestinationCidrBlock", ""), cidr_filter
                    ):
                        filtered_routes.append(route)
                routes = filtered_routes

            return routes

        except ClientError as e:
            if e.response.get("Error", {}).get("Code") == "InvalidRouteTableID.NotFound":
                return []
            raise

    async def _get_route_table_associations(
        self, ec2_client: Any, route_table_id: str
    ) -> List[Dict[str, Any]]:
        """Get route table associations."""
        try:
            response = await ec2_client.get_transit_gateway_route_table_associations(
                TransitGatewayRouteTableId=route_table_id
            )
            return response.get("Associations", [])
        except ClientError:
            return []

    async def _get_route_table_propagations(
        self, ec2_client: Any, route_table_id: str
    ) -> List[Dict[str, Any]]:
        """Get route table propagations."""
        try:
            response = await ec2_client.get_transit_gateway_route_table_propagations(
                TransitGatewayRouteTableId=route_table_id
            )
            return response.get("TransitGatewayRouteTablePropagations", [])
        except ClientError:
            return []

    async def _process_route_entries(self, raw_routes: List[Dict[str, Any]]) -> List[RouteEntry]:
        """
        Process raw route entries into enhanced RouteEntry objects.

        Args:
            raw_routes: Raw route data from AWS API

        Returns:
            List of processed route entries
        """
        # Use thread pool for CPU-intensive route processing
        loop = asyncio.get_event_loop()

        async def process_route(route_data: Dict[str, Any]) -> List[RouteEntry]:
            """Process a single route which may have multiple attachments."""
            entries = []

            destination_cidr = route_data.get("DestinationCidrBlock", "")
            state = RouteState(route_data.get("State", "pending").lower())
            route_type = RouteType(route_data.get("Type", "propagated").lower())

            attachments = route_data.get("TransitGatewayAttachments", [])

            if attachments:
                for attachment in attachments:
                    entry = RouteEntry(
                        destination_cidr=destination_cidr,
                        state=state,
                        route_type=route_type,
                        prefix_length=0,  # Will be calculated in __post_init__
                        target_type=attachment.get("ResourceType"),
                        target_id=attachment.get("ResourceId"),
                        attachment_id=attachment.get("TransitGatewayAttachmentId"),
                        origin=route_data.get("PrefixListId"),  # For prefix list routes
                    )
                    entries.append(entry)
            else:
                # Route without specific attachments
                entry = RouteEntry(
                    destination_cidr=destination_cidr,
                    state=state,
                    route_type=route_type,
                    prefix_length=0,  # Will be calculated in __post_init__
                )
                entries.append(entry)

            return entries

        # Process routes concurrently
        tasks = [process_route(route) for route in raw_routes]
        results = await asyncio.gather(*tasks)

        # Flatten results
        all_entries = []
        for entry_list in results:
            all_entries.extend(entry_list)

        # Apply longest-prefix matching to determine best paths
        await self._apply_longest_prefix_matching(all_entries)

        return all_entries

    async def _apply_longest_prefix_matching(self, route_entries: List[RouteEntry]) -> None:
        """
        Apply longest-prefix matching algorithm to determine best paths.

        Args:
            route_entries: List of route entries to process
        """
        # Group routes by destination to find conflicts
        route_groups: Dict[str, List[RouteEntry]] = {}

        for entry in route_entries:
            if entry.destination_cidr not in route_groups:
                route_groups[entry.destination_cidr] = []
            route_groups[entry.destination_cidr].append(entry)

        # For each group, determine the best path
        for destination, entries in route_groups.items():
            if len(entries) == 1:
                entries[0].is_best_path = True
                continue

            # Sort by priority (highest first)
            entries.sort(key=lambda x: x.priority, reverse=True)

            # Mark the highest priority route as best path
            entries[0].is_best_path = True

            # Mark conflicts for lower priority routes
            for i, entry in enumerate(entries[1:], 1):
                entry.conflicts.append(
                    f"Lower priority than {entries[0].attachment_id or 'primary'}"
                )

    async def _detect_route_conflicts(self, analysis: RouteTableAnalysis) -> None:
        """
        Detect route conflicts and overlaps.

        Args:
            analysis: Route table analysis to check for conflicts
        """
        conflicts = []

        # Check for overlapping CIDR blocks
        for i, entry1 in enumerate(analysis.route_entries):
            for j, entry2 in enumerate(analysis.route_entries[i + 1 :], i + 1):
                if self._routes_overlap(entry1.destination_cidr, entry2.destination_cidr):
                    conflict = {
                        "type": "cidr_overlap",
                        "route1": {
                            "cidr": entry1.destination_cidr,
                            "attachment": entry1.attachment_id,
                            "priority": entry1.priority,
                        },
                        "route2": {
                            "cidr": entry2.destination_cidr,
                            "attachment": entry2.attachment_id,
                            "priority": entry2.priority,
                        },
                        "severity": (
                            "high"
                            if entry1.state == RouteState.ACTIVE
                            and entry2.state == RouteState.ACTIVE
                            else "medium"
                        ),
                    }
                    conflicts.append(conflict)

        # Check for blackhole routes that might affect connectivity
        blackhole_routes = [e for e in analysis.route_entries if e.state == RouteState.BLACKHOLE]
        for blackhole in blackhole_routes:
            # Check if there are active routes that might be affected
            affected_routes = [
                e
                for e in analysis.route_entries
                if e.state == RouteState.ACTIVE
                and self._route_could_be_affected(e.destination_cidr, blackhole.destination_cidr)
            ]

            if affected_routes:
                conflict = {
                    "type": "blackhole_impact",
                    "blackhole_route": blackhole.destination_cidr,
                    "affected_routes": [r.destination_cidr for r in affected_routes],
                    "severity": "critical",
                }
                conflicts.append(conflict)

        analysis.route_conflicts = conflicts

    def _matches_cidr_filter(self, destination_cidr: str, cidr_filter: str) -> bool:
        """Check if destination CIDR matches the filter."""
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

    def _routes_overlap(self, cidr1: str, cidr2: str) -> bool:
        """Check if two CIDR blocks overlap."""
        try:
            network1 = ipaddress.ip_network(cidr1)
            network2 = ipaddress.ip_network(cidr2)
            return network1.overlaps(network2)
        except ValueError:
            return False

    def _route_could_be_affected(self, active_cidr: str, blackhole_cidr: str) -> bool:
        """Check if an active route could be affected by a blackhole route."""
        try:
            active_network = ipaddress.ip_network(active_cidr)
            blackhole_network = ipaddress.ip_network(blackhole_cidr)

            # Check if blackhole is more specific (longer prefix)
            return (
                blackhole_network.subnet_of(active_network)
                and blackhole_network.prefixlen > active_network.prefixlen
            )
        except ValueError:
            return False

    def _calculate_route_summary(self, route_entries: List[RouteEntry]) -> Dict[str, int]:
        """Calculate summary statistics for route entries."""
        summary = {
            "total_routes": len(route_entries),
            "active_routes": 0,
            "blackhole_routes": 0,
            "pending_routes": 0,
            "static_routes": 0,
            "propagated_routes": 0,
            "best_paths": 0,
            "conflicted_routes": 0,
        }

        for entry in route_entries:
            # Count by state
            if entry.state == RouteState.ACTIVE:
                summary["active_routes"] += 1
            elif entry.state == RouteState.BLACKHOLE:
                summary["blackhole_routes"] += 1
            elif entry.state == RouteState.PENDING:
                summary["pending_routes"] += 1

            # Count by type
            if entry.route_type == RouteType.STATIC:
                summary["static_routes"] += 1
            elif entry.route_type == RouteType.PROPAGATED:
                summary["propagated_routes"] += 1

            # Count best paths and conflicts
            if entry.is_best_path:
                summary["best_paths"] += 1
            if entry.conflicts:
                summary["conflicted_routes"] += 1

        return summary

    async def find_longest_prefix_match(
        self, target_ip: str, route_entries: List[RouteEntry]
    ) -> Optional[RouteEntry]:
        """
        Find the longest prefix match for a target IP address.

        Args:
            target_ip: Target IP address
            route_entries: List of route entries to search

        Returns:
            Best matching route entry or None
        """
        try:
            target_addr = ipaddress.ip_address(target_ip)
            best_match = None
            longest_prefix = -1

            for entry in route_entries:
                if entry.state != RouteState.ACTIVE:
                    continue

                try:
                    network = ipaddress.ip_network(entry.destination_cidr)
                    if target_addr in network and network.prefixlen > longest_prefix:
                        longest_prefix = network.prefixlen
                        best_match = entry
                except ValueError:
                    continue

            return best_match

        except ValueError:
            return None

    async def cleanup(self):
        """Cleanup resources."""
        if self._executor:
            self._executor.shutdown(wait=True)
        self._route_cache.clear()
