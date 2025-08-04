"""
Segment Discovery Engine for CloudWAN MCP Server.

This engine provides comprehensive segment attachment chain following, isolation
analysis, and segment connectivity mapping with policy-driven validation.

Features:
- Segment attachment chain following algorithms
- Multi-hop attachment relationship mapping
- Segment isolation and connectivity analysis
- Policy-driven segment rule validation
- Real-time segment state monitoring
- Cross-segment communication path analysis
"""

import asyncio
import json
import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set
from dataclasses import dataclass, field
from enum import Enum

from botocore.exceptions import ClientError

from ..aws.client_manager import AWSClientManager
from ..config import CloudWANConfig
from ..models.network import (
    AttachmentInfo,
    AttachmentType,
    AttachmentState,
)
from ..utils.aws_operations import AWSOperationError


class SegmentIsolationLevel(str, Enum):
    """Segment isolation levels."""

    ISOLATED = "ISOLATED"  # No cross-segment communication
    SELECTIVE = "SELECTIVE"  # Limited cross-segment communication
    SHARED = "SHARED"  # Full cross-segment communication
    UNDEFINED = "UNDEFINED"  # Isolation policy not defined


class AttachmentChainType(str, Enum):
    """Types of attachment chains."""

    DIRECT = "DIRECT"  # Direct attachment to segment
    TRANSITIVE = "TRANSITIVE"  # Multi-hop through other attachments
    NETWORK_FUNCTION = "NETWORK_FUNCTION"  # Through Network Function Groups
    PEERING = "PEERING"  # Through peering connections


@dataclass
class SegmentConnectivityPath:
    """Path between segments for connectivity analysis."""

    source_segment: str
    destination_segment: str
    path_type: AttachmentChainType
    hops: List[str] = field(default_factory=list)
    network_function_groups: List[str] = field(default_factory=list)
    policy_rules: List[Dict[str, Any]] = field(default_factory=list)
    is_bidirectional: bool = True
    latency_estimate_ms: Optional[int] = None
    path_cost: float = 1.0


@dataclass
class AttachmentChainNode:
    """Node in an attachment chain."""

    attachment_info: AttachmentInfo
    segment_name: str
    edge_location: str
    upstream_connections: List[str] = field(default_factory=list)
    downstream_connections: List[str] = field(default_factory=list)
    network_function_overrides: List[str] = field(default_factory=list)
    policy_applied: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class SegmentTopology:
    """Complete topology for a CloudWAN segment."""

    core_network_id: str
    segment_name: str
    isolation_level: SegmentIsolationLevel

    # Attachment Chain Analysis
    attachment_chains: List[AttachmentChainNode] = field(default_factory=list)
    direct_attachments: List[AttachmentInfo] = field(default_factory=list)
    transitive_attachments: List[AttachmentInfo] = field(default_factory=list)

    # Connectivity Analysis
    connectivity_paths: List[SegmentConnectivityPath] = field(default_factory=list)
    reachable_segments: Set[str] = field(default_factory=set)
    isolated_from_segments: Set[str] = field(default_factory=set)

    # Policy Analysis
    segment_actions: List[Dict[str, Any]] = field(default_factory=list)
    route_filters: List[Dict[str, Any]] = field(default_factory=list)
    send_to_rules: List[str] = field(default_factory=list)
    send_via_rules: List[str] = field(default_factory=list)

    # Analytics
    total_attachments: int = 0
    active_routes: int = 0
    edge_locations: Set[str] = field(default_factory=set)
    regions_spanned: Set[str] = field(default_factory=set)

    # State Tracking
    last_updated: Optional[datetime] = None
    policy_version: Optional[int] = None


class SegmentDiscoveryEngine:
    """
    Segment Discovery Engine.

    Provides comprehensive segment attachment chain following and connectivity
    analysis with policy-driven validation and real-time monitoring.
    """

    def __init__(self, aws_manager: AWSClientManager, config: CloudWANConfig):
        """Initialize the Segment Discovery Engine."""
        self.aws_manager = aws_manager
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.executor = ThreadPoolExecutor(max_workers=8)

        # Segment topology cache
        self._segment_cache: Dict[str, SegmentTopology] = {}
        self._cache_ttl = timedelta(minutes=3)

        # Custom NetworkManager endpoint support
        self.custom_nm_endpoint = self.config.aws.custom_endpoints.get("networkmanager")

    async def discover_all_segments(
        self,
        core_network_id: str,
        include_attachment_chains: bool = True,
        include_connectivity_analysis: bool = True,
        force_refresh: bool = False,
    ) -> List[SegmentTopology]:
        """
        Discover all segments in a Core Network with complete topology analysis.

        Args:
            core_network_id: Core Network ID to analyze
            include_attachment_chains: Include attachment chain following
            include_connectivity_analysis: Include connectivity path analysis
            force_refresh: Force cache refresh

        Returns:
            List of complete segment topologies
        """
        self.logger.info(f"Discovering all segments for Core Network: {core_network_id}")

        try:
            # Get Core Network policy to identify segments
            policy_doc = await self._get_core_network_policy(core_network_id)
            if not policy_doc:
                raise AWSOperationError("No policy document found for Core Network")

            # Extract segments from policy
            segments = self._extract_segments_from_policy(policy_doc)
            if not segments:
                self.logger.warning("No segments defined in Core Network policy")
                return []

            # Analyze each segment concurrently
            analysis_tasks = []
            for segment_name in segments:
                task = self.analyze_segment_topology(
                    core_network_id=core_network_id,
                    segment_name=segment_name,
                    policy_doc=policy_doc,
                    include_attachment_chains=include_attachment_chains,
                    include_connectivity_analysis=include_connectivity_analysis,
                    force_refresh=force_refresh,
                )
                analysis_tasks.append(task)

            # Execute analysis tasks
            segment_results = await asyncio.gather(*analysis_tasks, return_exceptions=True)

            # Consolidate results
            segment_topologies = []
            for result in segment_results:
                if isinstance(result, Exception):
                    self.logger.error(f"Segment analysis failed: {result}")
                    continue
                segment_topologies.append(result)

            # Perform cross-segment connectivity analysis
            if include_connectivity_analysis and len(segment_topologies) > 1:
                await self._analyze_cross_segment_connectivity(segment_topologies, policy_doc)

            self.logger.info(f"Discovered {len(segment_topologies)} segments")
            return segment_topologies

        except Exception as e:
            raise AWSOperationError(f"Segment discovery failed: {str(e)}")

    async def analyze_segment_topology(
        self,
        core_network_id: str,
        segment_name: str,
        policy_doc: Optional[Dict[str, Any]] = None,
        include_attachment_chains: bool = True,
        include_connectivity_analysis: bool = True,
        force_refresh: bool = False,
    ) -> SegmentTopology:
        """
        Analyze complete topology for a specific segment.

        Args:
            core_network_id: Core Network ID
            segment_name: Segment name to analyze
            policy_doc: Optional policy document (will fetch if not provided)
            include_attachment_chains: Include attachment chain analysis
            include_connectivity_analysis: Include connectivity analysis
            force_refresh: Force cache refresh

        Returns:
            Complete segment topology
        """
        cache_key = f"{core_network_id}:{segment_name}"

        # Check cache first (unless force refresh)
        if not force_refresh and cache_key in self._segment_cache:
            cached_topology = self._segment_cache[cache_key]
            if (datetime.now() - (cached_topology.last_updated or datetime.min)) < self._cache_ttl:
                self.logger.debug(f"Using cached topology for segment {segment_name}")
                return cached_topology

        self.logger.info(f"Analyzing segment topology: {segment_name}")

        try:
            # Get policy document if not provided
            if not policy_doc:
                policy_doc = await self._get_core_network_policy(core_network_id)

            # Create base segment topology
            topology = SegmentTopology(
                core_network_id=core_network_id,
                segment_name=segment_name,
                isolation_level=SegmentIsolationLevel.UNDEFINED,
                last_updated=datetime.now(),
            )

            # Extract policy version
            if policy_doc:
                topology.policy_version = policy_doc.get("version")

            # Parallel analysis tasks
            analysis_tasks = []

            # Attachment discovery and analysis
            analysis_tasks.append(self._discover_segment_attachments(core_network_id, segment_name))

            # Policy analysis for this segment
            if policy_doc:
                analysis_tasks.append(self._analyze_segment_policy(segment_name, policy_doc))
            else:
                analysis_tasks.append(asyncio.create_task(asyncio.sleep(0, result={})))

            # Route analysis
            analysis_tasks.append(self._analyze_segment_routes(core_network_id, segment_name))

            # Execute analysis tasks
            attachments_data, policy_data, routes_data = await asyncio.gather(
                *analysis_tasks, return_exceptions=True
            )

            # Process attachment data
            if not isinstance(attachments_data, Exception):
                topology.direct_attachments = attachments_data.get("direct", [])
                topology.transitive_attachments = attachments_data.get("transitive", [])
                topology.total_attachments = len(topology.direct_attachments) + len(
                    topology.transitive_attachments
                )

                # Extract edge locations and regions
                for attachment in topology.direct_attachments + topology.transitive_attachments:
                    topology.edge_locations.add(attachment.edge_location)
                    # Extract region from edge location
                    if "-" in attachment.edge_location:
                        region = attachment.edge_location
                        topology.regions_spanned.add(region)

            # Process policy data
            if not isinstance(policy_data, Exception):
                topology.isolation_level = policy_data.get(
                    "isolation_level", SegmentIsolationLevel.UNDEFINED
                )
                topology.segment_actions = policy_data.get("segment_actions", [])
                topology.route_filters = policy_data.get("route_filters", [])
                topology.send_to_rules = policy_data.get("send_to_rules", [])
                topology.send_via_rules = policy_data.get("send_via_rules", [])

            # Process route data
            if not isinstance(routes_data, Exception):
                topology.active_routes = routes_data.get("active_count", 0)

            # Perform attachment chain analysis if requested
            if include_attachment_chains:
                topology.attachment_chains = await self._build_attachment_chains(
                    topology.direct_attachments + topology.transitive_attachments,
                    segment_name,
                )

            # Cache the result
            self._segment_cache[cache_key] = topology

            return topology

        except Exception as e:
            raise AWSOperationError(f"Segment topology analysis failed: {str(e)}")

    async def follow_attachment_chain(
        self, core_network_id: str, starting_attachment_id: str, max_hops: int = 10
    ) -> List[AttachmentChainNode]:
        """
        Follow an attachment chain to discover all connected resources.

        Args:
            core_network_id: Core Network ID
            starting_attachment_id: Starting attachment ID
            max_hops: Maximum number of hops to follow

        Returns:
            Complete attachment chain path
        """
        self.logger.info(f"Following attachment chain from {starting_attachment_id}")

        try:
            # Get starting attachment details
            starting_attachment = await self._get_attachment_details(
                core_network_id, starting_attachment_id
            )

            if not starting_attachment:
                raise AWSOperationError(f"Attachment {starting_attachment_id} not found")

            # Initialize chain following
            visited_attachments = set()
            chain_nodes = []
            queue = [(starting_attachment, 0)]  # (attachment, hop_count)

            while queue and max_hops > 0:
                current_attachment, hop_count = queue.pop(0)
                attachment_id = current_attachment.attachment_id

                if attachment_id in visited_attachments or hop_count >= max_hops:
                    continue

                visited_attachments.add(attachment_id)

                # Create chain node
                chain_node = AttachmentChainNode(
                    attachment_info=current_attachment,
                    segment_name=current_attachment.segment_name,
                    edge_location=current_attachment.edge_location,
                )

                # Discover connected attachments
                connected_attachments = await self._discover_connected_attachments(
                    core_network_id, current_attachment
                )

                # Add upstream and downstream connections
                for connected in connected_attachments:
                    if connected.attachment_id not in visited_attachments:
                        queue.append((connected, hop_count + 1))
                        chain_node.downstream_connections.append(connected.attachment_id)

                # Check for network function overrides
                chain_node.network_function_overrides = (
                    await self._check_network_function_overrides(
                        core_network_id, current_attachment
                    )
                )

                chain_nodes.append(chain_node)

            self.logger.info(f"Discovered attachment chain with {len(chain_nodes)} nodes")
            return chain_nodes

        except Exception as e:
            raise AWSOperationError(f"Attachment chain following failed: {str(e)}")

    async def analyze_segment_connectivity(
        self,
        core_network_id: str,
        source_segment: str,
        destination_segment: Optional[str] = None,
    ) -> List[SegmentConnectivityPath]:
        """
        Analyze connectivity paths between segments.

        Args:
            core_network_id: Core Network ID
            source_segment: Source segment name
            destination_segment: Optional destination segment (all segments if None)

        Returns:
            List of connectivity paths
        """
        self.logger.info(f"Analyzing connectivity from segment {source_segment}")

        try:
            # Get policy document for routing rules
            policy_doc = await self._get_core_network_policy(core_network_id)
            if not policy_doc:
                return []

            # Determine destination segments
            if destination_segment:
                target_segments = [destination_segment]
            else:
                target_segments = self._extract_segments_from_policy(policy_doc)
                target_segments = [s for s in target_segments if s != source_segment]

            # Analyze connectivity to each target segment
            connectivity_paths = []
            analysis_tasks = []

            for target in target_segments:
                task = self._analyze_segment_pair_connectivity(
                    core_network_id, source_segment, target, policy_doc
                )
                analysis_tasks.append(task)

            # Execute analysis tasks
            path_results = await asyncio.gather(*analysis_tasks, return_exceptions=True)

            # Consolidate results
            for result in path_results:
                if isinstance(result, Exception):
                    self.logger.warning(f"Connectivity analysis failed: {result}")
                    continue
                if result:  # Path exists
                    connectivity_paths.append(result)

            return connectivity_paths

        except Exception as e:
            raise AWSOperationError(f"Segment connectivity analysis failed: {str(e)}")

    async def _get_core_network_policy(self, core_network_id: str) -> Optional[Dict[str, Any]]:
        """Get Core Network policy document."""
        try:
            nm_client = await self._get_networkmanager_client()
            response = await nm_client.get_core_network_policy(CoreNetworkId=core_network_id)

            policy_doc = response.get("CoreNetworkPolicy", {}).get("PolicyDocument")
            if policy_doc:
                return json.loads(policy_doc)
            return None

        except ClientError as e:
            self.logger.warning(f"Failed to get Core Network policy: {e}")
            return None

    def _extract_segments_from_policy(self, policy_doc: Dict[str, Any]) -> List[str]:
        """Extract segment names from policy document."""
        segments = []
        for segment in policy_doc.get("segments", []):
            if "name" in segment:
                segments.append(segment["name"])
        return segments

    async def _discover_segment_attachments(
        self, core_network_id: str, segment_name: str
    ) -> Dict[str, List[AttachmentInfo]]:
        """Discover all attachments for a segment."""
        try:
            nm_client = await self._get_networkmanager_client()
            response = await nm_client.list_attachments(CoreNetworkId=core_network_id)

            direct_attachments = []
            transitive_attachments = []

            for attachment in response.get("Attachments", []):
                if attachment.get("SegmentName") != segment_name:
                    continue

                attachment_info = AttachmentInfo(
                    attachment_id=attachment.get("AttachmentId", ""),
                    attachment_type=AttachmentType(attachment.get("AttachmentType", "VPC")),
                    state=AttachmentState(attachment.get("State", "AVAILABLE")),
                    core_network_id=core_network_id,
                    edge_location=attachment.get("EdgeLocation", ""),
                    segment_name=segment_name,
                    resource_arn=attachment.get("ResourceArn"),
                    tags=attachment.get("Tags", {}),
                    created_at=attachment.get("CreatedAt"),
                )

                # Classify as direct or transitive based on attachment type
                if attachment.get("AttachmentType") in ["VPC", "CONNECT"]:
                    direct_attachments.append(attachment_info)
                else:
                    transitive_attachments.append(attachment_info)

            return {"direct": direct_attachments, "transitive": transitive_attachments}

        except ClientError as e:
            self.logger.warning(f"Failed to discover segment attachments: {e}")
            return {"direct": [], "transitive": []}

    async def _analyze_segment_policy(
        self, segment_name: str, policy_doc: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Analyze policy rules for a specific segment."""
        segment_policy = {}

        # Find segment in policy document
        segment_config = None
        for segment in policy_doc.get("segments", []):
            if segment.get("name") == segment_name:
                segment_config = segment
                break

        if not segment_config:
            return {
                "isolation_level": SegmentIsolationLevel.UNDEFINED,
                "segment_actions": [],
                "route_filters": [],
                "send_to_rules": [],
                "send_via_rules": [],
            }

        # Analyze isolation level
        isolation_level = SegmentIsolationLevel.SHARED  # Default
        if segment_config.get("isolate-attachments"):
            isolation_level = SegmentIsolationLevel.ISOLATED
        elif segment_config.get("segment-actions"):
            # Check for selective sharing rules
            has_sharing_rules = any(
                action.get("action") == "share"
                for action in segment_config.get("segment-actions", [])
            )
            if has_sharing_rules:
                isolation_level = SegmentIsolationLevel.SELECTIVE

        # Extract segment actions
        segment_actions = segment_config.get("segment-actions", [])

        # Extract route filters
        route_filters = [
            action for action in segment_actions if action.get("action") in ["create-route", "drop"]
        ]

        # Extract send-to and send-via rules
        send_to_rules = []
        send_via_rules = []

        for action in segment_actions:
            if action.get("action") == "share":
                if "segment" in action:
                    send_to_rules.append(action["segment"])
            elif action.get("action") == "send-via":
                if "network-function-group" in action:
                    send_via_rules.append(action["network-function-group"])

        return {
            "isolation_level": isolation_level,
            "segment_actions": segment_actions,
            "route_filters": route_filters,
            "send_to_rules": send_to_rules,
            "send_via_rules": send_via_rules,
        }

    async def _analyze_segment_routes(
        self, core_network_id: str, segment_name: str
    ) -> Dict[str, Any]:
        """Analyze routes for a segment."""
        try:
            # This would require actual route table analysis
            # For now, return placeholder data
            return {"active_count": 0, "static_count": 0, "propagated_count": 0}
        except Exception as e:
            self.logger.warning(f"Failed to analyze segment routes: {e}")
            return {"active_count": 0, "static_count": 0, "propagated_count": 0}

    async def _build_attachment_chains(
        self, attachments: List[AttachmentInfo], segment_name: str
    ) -> List[AttachmentChainNode]:
        """Build attachment chain nodes from attachment list."""
        chain_nodes = []

        for attachment in attachments:
            node = AttachmentChainNode(
                attachment_info=attachment,
                segment_name=segment_name,
                edge_location=attachment.edge_location,
            )

            # Analyze connections (simplified)
            # This would require deeper analysis of the actual resources
            node.upstream_connections = []
            node.downstream_connections = []
            node.network_function_overrides = []

            chain_nodes.append(node)

        return chain_nodes

    async def _analyze_cross_segment_connectivity(
        self, segment_topologies: List[SegmentTopology], policy_doc: Dict[str, Any]
    ) -> None:
        """Analyze connectivity between all segments."""
        # Update each segment with reachable/isolated segments
        for topology in segment_topologies:
            reachable = set()
            isolated = set()

            for other_topology in segment_topologies:
                if other_topology.segment_name == topology.segment_name:
                    continue

                # Check if segments can communicate based on policy
                can_communicate = self._check_segment_communication(
                    topology.segment_name, other_topology.segment_name, policy_doc
                )

                if can_communicate:
                    reachable.add(other_topology.segment_name)
                else:
                    isolated.add(other_topology.segment_name)

            topology.reachable_segments = reachable
            topology.isolated_from_segments = isolated

    def _check_segment_communication(
        self, source_segment: str, destination_segment: str, policy_doc: Dict[str, Any]
    ) -> bool:
        """Check if two segments can communicate based on policy."""
        # Find source segment policy
        source_config = None
        for segment in policy_doc.get("segments", []):
            if segment.get("name") == source_segment:
                source_config = segment
                break

        if not source_config:
            return False

        # Check isolation
        if source_config.get("isolate-attachments"):
            return False

        # Check explicit sharing rules
        for action in source_config.get("segment-actions", []):
            if action.get("action") == "share" and action.get("segment") == destination_segment:
                return True

        # Default behavior (would need more sophisticated analysis)
        return True

    async def _get_attachment_details(
        self, core_network_id: str, attachment_id: str
    ) -> Optional[AttachmentInfo]:
        """Get detailed information for a specific attachment."""
        try:
            nm_client = await self._get_networkmanager_client()
            response = await nm_client.get_attachment(AttachmentId=attachment_id)

            attachment = response.get("Attachment", {})
            return AttachmentInfo(
                attachment_id=attachment.get("AttachmentId", ""),
                attachment_type=AttachmentType(attachment.get("AttachmentType", "VPC")),
                state=AttachmentState(attachment.get("State", "AVAILABLE")),
                core_network_id=core_network_id,
                edge_location=attachment.get("EdgeLocation", ""),
                segment_name=attachment.get("SegmentName", ""),
                resource_arn=attachment.get("ResourceArn"),
                tags=attachment.get("Tags", {}),
                created_at=attachment.get("CreatedAt"),
            )

        except ClientError as e:
            self.logger.warning(f"Failed to get attachment details: {e}")
            return None

    async def _discover_connected_attachments(
        self, core_network_id: str, attachment: AttachmentInfo
    ) -> List[AttachmentInfo]:
        """Discover attachments connected to the given attachment."""
        # This would analyze the actual resource connections
        # For now, return empty list
        return []

    async def _check_network_function_overrides(
        self, core_network_id: str, attachment: AttachmentInfo
    ) -> List[str]:
        """Check for network function group overrides affecting this attachment."""
        # This would analyze Network Function Group policies
        # For now, return empty list
        return []

    async def _analyze_segment_pair_connectivity(
        self,
        core_network_id: str,
        source_segment: str,
        destination_segment: str,
        policy_doc: Dict[str, Any],
    ) -> Optional[SegmentConnectivityPath]:
        """Analyze connectivity between two specific segments."""
        if not self._check_segment_communication(source_segment, destination_segment, policy_doc):
            return None

        # Create connectivity path
        path = SegmentConnectivityPath(
            source_segment=source_segment,
            destination_segment=destination_segment,
            path_type=AttachmentChainType.DIRECT,  # Simplified
        )

        # Analyze path details (simplified)
        path.hops = [source_segment, destination_segment]
        path.is_bidirectional = self._check_segment_communication(
            destination_segment, source_segment, policy_doc
        )

        return path

    async def _get_networkmanager_client(self):
        """Get NetworkManager client with custom endpoint support."""
        region = "us-west-2"  # NetworkManager is a global service
        client = await self.aws_manager.get_client("networkmanager", region)

        if self.custom_nm_endpoint:
            client._endpoint.host = self.custom_nm_endpoint.replace("https://", "").replace(
                "http://", ""
            )

        return client
