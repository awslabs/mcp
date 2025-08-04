"""
BGP topology models for CloudWAN MCP Server.

This module implements BGP-specific topology models that integrate with the
existing network topology infrastructure. It provides comprehensive BGP
routing topology modeling with ASN relationships, routing policies, and
session state management.

Key Features:
- BGP topology model with ASN relationships using networkx
- BGP peer model with session states and route advertisements
- BGP route model with prefix information and path attributes
- Integration with existing NetworkTopology and NetworkElement models
- Adapter patterns for legacy topology format compatibility
- Session state management following RFC 4271 BGP FSM
- Route origin validation and RPKI integration

References:
- RFC 4271: A Border Gateway Protocol 4 (BGP-4)
- RFC 4760: Multiprotocol Extensions for BGP-4
- RFC 6811: BGP Prefix Origin Validation
- AWS CloudWAN BGP Integration
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set
from enum import Enum
from uuid import uuid4
import logging
from ipaddress import ip_network, ip_address
from collections import defaultdict

from pydantic import Field, field_validator, model_validator, ConfigDict
import networkx as nx

from .topology import NetworkTopology
from ..shared.base import TimestampMixin, PerformanceMetrics
from ..shared.enums import (
    BGPPeerState, BGPRouteType, CloudWANBGPPeerState, 
    BGPSecurityViolationType, RPKIValidationStatus,
    SecurityThreatLevel, HealthStatus
)

logger = logging.getLogger(__name__)


class BGPSessionDirection(str, Enum):
    """BGP session direction for peer relationships."""
    INBOUND = "inbound"
    OUTBOUND = "outbound"
    BIDIRECTIONAL = "bidirectional"


class BGPAddressFamily(str, Enum):
    """BGP address families for multiprotocol support."""
    IPV4_UNICAST = "ipv4-unicast"
    IPV6_UNICAST = "ipv6-unicast"
    IPV4_MULTICAST = "ipv4-multicast"
    IPV6_MULTICAST = "ipv6-multicast"
    VPN_IPV4 = "vpn-ipv4"
    VPN_IPV6 = "vpn-ipv6"
    FLOWSPEC_IPV4 = "flowspec-ipv4"
    FLOWSPEC_IPV6 = "flowspec-ipv6"


class BGPRouteModel(TimestampMixin):
    """
    BGP route model with prefix information and path attributes.
    
    Models individual BGP routes with comprehensive path attributes,
    origin validation, and security assessment for route analysis.
    """
    
    model_config = ConfigDict(
        extra="allow",
        validate_assignment=True,
        use_enum_values=True
    )
    
    # Core route identity
    route_id: str = Field(
        default_factory=lambda: str(uuid4()),
        description="Unique route identifier"
    )
    prefix: str = Field(
        description="Route prefix in CIDR notation"
    )
    prefix_length: int = Field(
        description="Prefix length (subnet mask)"
    )
    next_hop: str = Field(
        description="Next hop IP address"
    )
    
    # BGP path attributes
    origin: BGPRouteType = Field(
        description="Route origin type"
    )
    as_path: List[int] = Field(
        default_factory=list,
        description="AS path sequence"
    )
    as_path_length: int = Field(
        default=0,
        description="AS path length"
    )
    local_preference: Optional[int] = Field(
        default=None,
        description="Local preference attribute"
    )
    multi_exit_discriminator: Optional[int] = Field(
        default=None,
        description="MED (Multi-Exit Discriminator) attribute"
    )
    atomic_aggregate: bool = Field(
        default=False,
        description="Atomic aggregate flag"
    )
    aggregator_as: Optional[int] = Field(
        default=None,
        description="Aggregator AS number"
    )
    aggregator_id: Optional[str] = Field(
        default=None,
        description="Aggregator router ID"
    )
    
    # Extended attributes
    communities: List[str] = Field(
        default_factory=list,
        description="BGP communities"
    )
    extended_communities: List[str] = Field(
        default_factory=list,
        description="Extended communities"
    )
    large_communities: List[str] = Field(
        default_factory=list,
        description="Large communities"
    )
    
    # Route characteristics
    address_family: BGPAddressFamily = Field(
        default=BGPAddressFamily.IPV4_UNICAST,
        description="Address family"
    )
    route_source: str = Field(
        description="Route source peer or system"
    )
    route_age: Optional[int] = Field(
        default=None,
        description="Route age in seconds"
    )
    weight: Optional[int] = Field(
        default=None,
        description="Route weight (Cisco-specific)"
    )
    
    # Validation and security
    rpki_validation: RPKIValidationStatus = Field(
        default=RPKIValidationStatus.UNKNOWN,
        description="RPKI validation status"
    )
    route_origin_as: Optional[int] = Field(
        default=None,
        description="Route origin AS number"
    )
    is_best_path: bool = Field(
        default=False,
        description="Whether this is the best path"
    )
    is_active: bool = Field(
        default=True,
        description="Whether route is active"
    )
    
    # Security analysis
    security_violations: List[BGPSecurityViolationType] = Field(
        default_factory=list,
        description="Detected security violations"
    )
    threat_level: SecurityThreatLevel = Field(
        default=SecurityThreatLevel.UNKNOWN,
        description="Security threat level"
    )
    
    # CloudWAN integration
    cloudwan_segment: Optional[str] = Field(
        default=None,
        description="Associated CloudWAN segment"
    )
    cloudwan_attachment_id: Optional[str] = Field(
        default=None,
        description="Associated CloudWAN attachment"
    )
    
    # Performance metrics
    route_flap_count: int = Field(
        default=0,
        description="Route flap count"
    )
    last_flap_time: Optional[datetime] = Field(
        default=None,
        description="Last route flap timestamp"
    )
    
    @field_validator('prefix')
    @classmethod
    def validate_prefix(cls, v):
        """Validate prefix format."""
        try:
            ip_network(v, strict=False)
        except ValueError:
            raise ValueError(f"Invalid prefix format: {v}")
        return v
    
    @field_validator('next_hop')
    @classmethod
    def validate_next_hop(cls, v):
        """Validate next hop IP address."""
        try:
            ip_address(v)
        except ValueError:
            raise ValueError(f"Invalid next hop IP: {v}")
        return v
    
    @model_validator(mode='after')
    def validate_as_path_length(self):
        """Validate AS path length consistency."""
        if self.as_path_length != len(self.as_path):
            self.as_path_length = len(self.as_path)
        return self
    
    def get_origin_as(self) -> Optional[int]:
        """Get origin AS from AS path."""
        if self.as_path:
            return self.as_path[-1]
        return self.route_origin_as
    
    def is_internal_route(self) -> bool:
        """Check if route is internal (originated locally)."""
        return self.origin == BGPRouteType.IGP
    
    def is_external_route(self) -> bool:
        """Check if route is external (learned from peers)."""
        return self.origin in (BGPRouteType.EGP, BGPRouteType.INCOMPLETE)
    
    def has_security_issues(self) -> bool:
        """Check if route has security violations."""
        return bool(self.security_violations) or self.threat_level.requires_immediate_action()
    
    def is_rpki_valid(self) -> bool:
        """Check if route is RPKI valid."""
        return self.rpki_validation == RPKIValidationStatus.VALID
    
    def calculate_route_priority(self) -> int:
        """Calculate route priority for path selection."""
        priority = 0
        
        # Local preference (higher is better)
        if self.local_preference:
            priority += self.local_preference
        
        # AS path length (shorter is better)
        priority -= self.as_path_length * 10
        
        # MED (lower is better)
        if self.multi_exit_discriminator:
            priority -= self.multi_exit_discriminator
        
        # Origin type preference
        origin_priority = {
            BGPRouteType.IGP: 30,
            BGPRouteType.EGP: 20,
            BGPRouteType.INCOMPLETE: 10
        }
        priority += origin_priority.get(self.origin, 0)
        
        # Weight (Cisco-specific, higher is better)
        if self.weight:
            priority += self.weight
        
        return priority
    
    def get_route_summary(self) -> Dict[str, Any]:
        """Get route summary for display."""
        return {
            "prefix": self.prefix,
            "next_hop": self.next_hop,
            "origin": self.origin.value,
            "as_path": self.as_path,
            "local_preference": self.local_preference,
            "med": self.multi_exit_discriminator,
            "is_best_path": self.is_best_path,
            "is_active": self.is_active,
            "rpki_status": self.rpki_validation.value,
            "threat_level": self.threat_level.value,
            "security_violations": [v.value for v in self.security_violations]
        }


class BGPPeerModel(TimestampMixin):
    """
    BGP peer model with session states and route advertisements.
    
    Models BGP peer relationships with comprehensive session management,
    route advertisement tracking, and security assessment.
    """
    
    model_config = ConfigDict(
        extra="allow",
        validate_assignment=True,
        use_enum_values=True
    )
    
    # Core peer identity
    peer_id: str = Field(
        default_factory=lambda: str(uuid4()),
        description="Unique peer identifier"
    )
    peer_ip: str = Field(
        description="Peer IP address"
    )
    peer_asn: int = Field(
        description="Peer AS number"
    )
    local_asn: int = Field(
        description="Local AS number"
    )
    local_ip: str = Field(
        description="Local IP address"
    )
    
    # Session characteristics
    peer_state: BGPPeerState = Field(
        default=BGPPeerState.IDLE,
        description="BGP FSM state"
    )
    session_direction: BGPSessionDirection = Field(
        default=BGPSessionDirection.BIDIRECTIONAL,
        description="Session direction"
    )
    address_families: Set[BGPAddressFamily] = Field(
        default_factory=lambda: {BGPAddressFamily.IPV4_UNICAST},
        description="Supported address families"
    )
    
    # Session configuration
    hold_time: int = Field(
        default=180,
        description="Hold time in seconds"
    )
    keepalive_interval: int = Field(
        default=60,
        description="Keepalive interval in seconds"
    )
    connect_retry_interval: int = Field(
        default=120,
        description="Connect retry interval in seconds"
    )
    
    # Route advertisement
    advertised_routes: Dict[str, BGPRouteModel] = Field(
        default_factory=dict,
        description="Routes advertised to this peer"
    )
    received_routes: Dict[str, BGPRouteModel] = Field(
        default_factory=dict,
        description="Routes received from this peer"
    )
    route_count_ipv4: int = Field(
        default=0,
        description="IPv4 route count"
    )
    route_count_ipv6: int = Field(
        default=0,
        description="IPv6 route count"
    )
    
    # Session statistics
    session_uptime: Optional[int] = Field(
        default=None,
        description="Session uptime in seconds"
    )
    session_flap_count: int = Field(
        default=0,
        description="Session flap count"
    )
    last_flap_time: Optional[datetime] = Field(
        default=None,
        description="Last session flap timestamp"
    )
    messages_sent: int = Field(
        default=0,
        description="Messages sent to peer"
    )
    messages_received: int = Field(
        default=0,
        description="Messages received from peer"
    )
    
    # Error tracking
    last_error: Optional[str] = Field(
        default=None,
        description="Last error message"
    )
    error_count: int = Field(
        default=0,
        description="Total error count"
    )
    notification_sent: int = Field(
        default=0,
        description="Notification messages sent"
    )
    notification_received: int = Field(
        default=0,
        description="Notification messages received"
    )
    
    # Security assessment
    security_violations: List[BGPSecurityViolationType] = Field(
        default_factory=list,
        description="Detected security violations"
    )
    threat_level: SecurityThreatLevel = Field(
        default=SecurityThreatLevel.UNKNOWN,
        description="Security threat level"
    )
    rpki_enabled: bool = Field(
        default=False,
        description="Whether RPKI validation is enabled"
    )
    
    # CloudWAN integration
    cloudwan_peer_state: Optional[CloudWANBGPPeerState] = Field(
        default=None,
        description="CloudWAN-specific peer state"
    )
    cloudwan_attachment_id: Optional[str] = Field(
        default=None,
        description="Associated CloudWAN attachment"
    )
    cloudwan_segment: Optional[str] = Field(
        default=None,
        description="Associated CloudWAN segment"
    )
    
    # Performance metrics
    performance_metrics: Optional[PerformanceMetrics] = Field(
        default=None,
        description="Performance metrics"
    )
    
    @field_validator('peer_ip', 'local_ip')
    @classmethod
    def validate_ip_address(cls, v):
        """Validate IP address format."""
        try:
            ip_address(v)
        except ValueError:
            raise ValueError(f"Invalid IP address: {v}")
        return v
    
    @field_validator('peer_asn', 'local_asn')
    @classmethod
    def validate_asn(cls, v):
        """Validate AS number range."""
        if not (1 <= v <= 4294967295):  # 32-bit ASN range
            raise ValueError(f"AS number out of range: {v}")
        return v
    
    def is_established(self) -> bool:
        """Check if peer session is established."""
        return self.peer_state == BGPPeerState.ESTABLISHED
    
    def is_external_peer(self) -> bool:
        """Check if peer is external (different AS)."""
        return self.peer_asn != self.local_asn
    
    def is_internal_peer(self) -> bool:
        """Check if peer is internal (same AS)."""
        return self.peer_asn == self.local_asn
    
    def add_advertised_route(self, route: BGPRouteModel) -> None:
        """Add route to advertised routes."""
        self.advertised_routes[route.route_id] = route
        self._update_route_counts()
        self.update_timestamp()
    
    def add_received_route(self, route: BGPRouteModel) -> None:
        """Add route to received routes."""
        self.received_routes[route.route_id] = route
        self._update_route_counts()
        self.update_timestamp()
    
    def _update_route_counts(self) -> None:
        """Update route counts by address family."""
        self.route_count_ipv4 = sum(
            1 for route in {**self.advertised_routes, **self.received_routes}.values()
            if route.address_family == BGPAddressFamily.IPV4_UNICAST
        )
        self.route_count_ipv6 = sum(
            1 for route in {**self.advertised_routes, **self.received_routes}.values()
            if route.address_family == BGPAddressFamily.IPV6_UNICAST
        )
    
    def update_session_state(self, new_state: BGPPeerState) -> None:
        """Update peer session state."""
        if new_state != self.peer_state:
            old_state = self.peer_state
            self.peer_state = new_state
            
            # Track session flaps
            if old_state == BGPPeerState.ESTABLISHED and new_state != BGPPeerState.ESTABLISHED:
                self.session_flap_count += 1
                self.last_flap_time = datetime.now(timezone.utc)
            
            # Reset uptime on state change
            if new_state == BGPPeerState.ESTABLISHED:
                self.session_uptime = 0
            
            self.update_timestamp()
    
    def calculate_session_health(self) -> float:
        """Calculate peer session health score."""
        score = 1.0
        
        # State penalty
        if self.peer_state != BGPPeerState.ESTABLISHED:
            score -= 0.4
        
        # Error penalty
        if self.error_count > 0:
            score -= min(0.3, self.error_count * 0.05)
        
        # Flap penalty
        if self.session_flap_count > 0:
            score -= min(0.2, self.session_flap_count * 0.1)
        
        # Security violation penalty
        if self.security_violations:
            score -= min(0.4, len(self.security_violations) * 0.1)
        
        return max(0.0, min(1.0, score))
    
    def get_peer_summary(self) -> Dict[str, Any]:
        """Get peer summary for display."""
        return {
            "peer_ip": self.peer_ip,
            "peer_asn": self.peer_asn,
            "local_asn": self.local_asn,
            "state": self.peer_state.value,
            "session_direction": self.session_direction.value,
            "address_families": [af.value for af in self.address_families],
            "route_count_ipv4": self.route_count_ipv4,
            "route_count_ipv6": self.route_count_ipv6,
            "session_uptime": self.session_uptime,
            "session_flap_count": self.session_flap_count,
            "health_score": self.calculate_session_health(),
            "threat_level": self.threat_level.value,
            "security_violations": [v.value for v in self.security_violations]
        }


class BGPTopologyModel(TimestampMixin):
    """
    BGP topology model with ASN relationships and routing policies.
    
    Comprehensive BGP topology representation that integrates with existing
    NetworkTopology infrastructure while providing BGP-specific functionality
    for routing analysis and policy management.
    """
    
    model_config = ConfigDict(
        extra="allow",
        validate_assignment=True,
        use_enum_values=True,
        arbitrary_types_allowed=True
    )
    
    # Core topology identity
    bgp_topology_id: str = Field(
        default_factory=lambda: str(uuid4()),
        description="Unique BGP topology identifier"
    )
    name: str = Field(
        description="BGP topology name"
    )
    description: Optional[str] = Field(
        default=None,
        description="BGP topology description"
    )
    
    # ASN and peer management
    autonomous_systems: Dict[int, Dict[str, Any]] = Field(
        default_factory=dict,
        description="Autonomous systems in topology"
    )
    bgp_peers: Dict[str, BGPPeerModel] = Field(
        default_factory=dict,
        description="BGP peers indexed by peer ID"
    )
    bgp_routes: Dict[str, BGPRouteModel] = Field(
        default_factory=dict,
        description="BGP routes indexed by route ID"
    )
    
    # Topology graphs
    asn_graph: Optional[nx.DiGraph] = Field(
        default=None,
        exclude=True,
        description="ASN relationship graph (not serialized)"
    )
    peer_graph: Optional[nx.MultiDiGraph] = Field(
        default=None,
        exclude=True,
        description="BGP peer relationship graph (not serialized)"
    )
    graph_stale: bool = Field(
        default=True,
        exclude=True,
        description="Whether graphs need rebuilding"
    )
    
    # Integration with base topology
    network_topology_id: Optional[str] = Field(
        default=None,
        description="Associated network topology ID"
    )
    network_topology: Optional[NetworkTopology] = Field(
        default=None,
        exclude=True,
        description="Associated network topology (not serialized)"
    )
    
    # Policy and configuration
    routing_policies: Dict[str, Dict[str, Any]] = Field(
        default_factory=dict,
        description="BGP routing policies"
    )
    route_filters: Dict[str, Dict[str, Any]] = Field(
        default_factory=dict,
        description="Route filtering policies"
    )
    
    # CloudWAN integration
    cloudwan_segments: Dict[str, Dict[str, Any]] = Field(
        default_factory=dict,
        description="CloudWAN segments with BGP integration"
    )
    cloudwan_attachments: Dict[str, Dict[str, Any]] = Field(
        default_factory=dict,
        description="CloudWAN attachments with BGP peers"
    )
    
    # Operational state
    health_status: HealthStatus = Field(
        default=HealthStatus.UNKNOWN,
        description="Overall BGP topology health"
    )
    last_update: Optional[datetime] = Field(
        default=None,
        description="Last topology update timestamp"
    )
    
    # Security assessment
    security_violations: List[BGPSecurityViolationType] = Field(
        default_factory=list,
        description="Global security violations"
    )
    threat_level: SecurityThreatLevel = Field(
        default=SecurityThreatLevel.UNKNOWN,
        description="Overall security threat level"
    )
    
    # Performance metrics
    total_routes: int = Field(
        default=0,
        description="Total route count"
    )
    total_peers: int = Field(
        default=0,
        description="Total peer count"
    )
    established_peers: int = Field(
        default=0,
        description="Established peer count"
    )
    
    def add_autonomous_system(self, asn: int, as_info: Dict[str, Any]) -> None:
        """Add autonomous system to topology."""
        self.autonomous_systems[asn] = {
            **as_info,
            "added_at": datetime.now(timezone.utc).isoformat()
        }
        self._mark_graphs_stale()
        self.update_timestamp()
    
    def add_bgp_peer(self, peer: BGPPeerModel) -> None:
        """Add BGP peer to topology."""
        self.bgp_peers[peer.peer_id] = peer
        
        # Update ASN information
        if peer.peer_asn not in self.autonomous_systems:
            self.autonomous_systems[peer.peer_asn] = {
                "asn": peer.peer_asn,
                "discovered_at": datetime.now(timezone.utc).isoformat(),
                "peer_count": 0
            }
        
        self.autonomous_systems[peer.peer_asn]["peer_count"] = len([
            p for p in self.bgp_peers.values() if p.peer_asn == peer.peer_asn
        ])
        
        self._update_statistics()
        self._mark_graphs_stale()
        self.update_timestamp()
    
    def add_bgp_route(self, route: BGPRouteModel) -> None:
        """Add BGP route to topology."""
        self.bgp_routes[route.route_id] = route
        self._update_statistics()
        self.update_timestamp()
    
    def remove_bgp_peer(self, peer_id: str) -> bool:
        """Remove BGP peer from topology."""
        if peer_id in self.bgp_peers:
            del self.bgp_peers[peer_id]
            self._update_statistics()
            self._mark_graphs_stale()
            self.update_timestamp()
            return True
        return False
    
    def remove_bgp_route(self, route_id: str) -> bool:
        """Remove BGP route from topology."""
        if route_id in self.bgp_routes:
            del self.bgp_routes[route_id]
            self._update_statistics()
            self.update_timestamp()
            return True
        return False
    
    def _update_statistics(self) -> None:
        """Update topology statistics."""
        self.total_peers = len(self.bgp_peers)
        self.established_peers = sum(
            1 for peer in self.bgp_peers.values() if peer.is_established()
        )
        self.total_routes = len(self.bgp_routes)
    
    def _mark_graphs_stale(self) -> None:
        """Mark graphs as needing rebuild."""
        self.graph_stale = True
    
    def _ensure_graphs_current(self) -> None:
        """Ensure graphs are up to date."""
        if self.graph_stale or self.asn_graph is None or self.peer_graph is None:
            self._build_graphs()
    
    def _build_graphs(self) -> None:
        """Build NetworkX graphs for topology analysis."""
        # Build ASN relationship graph
        self.asn_graph = nx.DiGraph()
        
        # Add ASN nodes
        for asn, as_info in self.autonomous_systems.items():
            self.asn_graph.add_node(asn, **as_info)
        
        # Add ASN edges based on peer relationships
        for peer in self.bgp_peers.values():
            if peer.local_asn != peer.peer_asn:
                self.asn_graph.add_edge(
                    peer.local_asn,
                    peer.peer_asn,
                    peer_count=1,
                    relationship_type="external"
                )
        
        # Build peer relationship graph
        self.peer_graph = nx.MultiDiGraph()
        
        # Add peer nodes
        for peer_id, peer in self.bgp_peers.values():
            self.peer_graph.add_node(
                peer_id,
                peer_ip=peer.peer_ip,
                peer_asn=peer.peer_asn,
                local_asn=peer.local_asn,
                state=peer.peer_state.value,
                **peer.model_dump(exclude={"advertised_routes", "received_routes"})
            )
        
        # Add peer edges (sessions)
        for peer in self.bgp_peers.values():
            # Add session edge
            self.peer_graph.add_edge(
                f"{peer.local_asn}:{peer.local_ip}",
                f"{peer.peer_asn}:{peer.peer_ip}",
                session_type="bgp",
                state=peer.peer_state.value,
                direction=peer.session_direction.value
            )
        
        self.graph_stale = False
    
    def get_asn_neighbors(self, asn: int) -> List[int]:
        """Get neighboring ASNs."""
        self._ensure_graphs_current()
        if asn in self.asn_graph:
            return list(self.asn_graph.neighbors(asn))
        return []
    
    def get_asn_path(self, source_asn: int, target_asn: int) -> Optional[List[int]]:
        """Find AS path between two ASNs."""
        self._ensure_graphs_current()
        try:
            return nx.shortest_path(self.asn_graph, source_asn, target_asn)
        except (nx.NetworkXNoPath, nx.NetworkXError):
            return None
    
    def get_established_peers(self) -> List[BGPPeerModel]:
        """Get all established BGP peers."""
        return [peer for peer in self.bgp_peers.values() if peer.is_established()]
    
    def get_external_peers(self) -> List[BGPPeerModel]:
        """Get all external BGP peers."""
        return [peer for peer in self.bgp_peers.values() if peer.is_external_peer()]
    
    def get_internal_peers(self) -> List[BGPPeerModel]:
        """Get all internal BGP peers."""
        return [peer for peer in self.bgp_peers.values() if peer.is_internal_peer()]
    
    def get_routes_by_prefix(self, prefix: str) -> List[BGPRouteModel]:
        """Get routes matching a prefix."""
        return [route for route in self.bgp_routes.values() if route.prefix == prefix]
    
    def get_routes_by_asn(self, asn: int) -> List[BGPRouteModel]:
        """Get routes from or through an ASN."""
        return [
            route for route in self.bgp_routes.values()
            if asn in route.as_path or route.get_origin_as() == asn
        ]
    
    def detect_security_violations(self) -> List[Dict[str, Any]]:
        """Detect BGP security violations."""
        violations = []
        
        # Check for prefix hijacking
        prefix_origins = defaultdict(set)
        for route in self.bgp_routes.values():
            prefix_origins[route.prefix].add(route.get_origin_as())
        
        for prefix, origin_asns in prefix_origins.items():
            if len(origin_asns) > 1:
                violations.append({
                    "type": BGPSecurityViolationType.PREFIX_HIJACKING,
                    "prefix": prefix,
                    "origin_asns": list(origin_asns),
                    "severity": SecurityThreatLevel.HIGH
                })
        
        # Check for RPKI invalid routes
        rpki_invalid = [
            route for route in self.bgp_routes.values()
            if route.rpki_validation == RPKIValidationStatus.INVALID
        ]
        
        if rpki_invalid:
            violations.append({
                "type": BGPSecurityViolationType.RPKI_INVALID,
                "route_count": len(rpki_invalid),
                "routes": [route.route_id for route in rpki_invalid],
                "severity": SecurityThreatLevel.HIGH
            })
        
        # Check for suspicious AS path lengths
        long_paths = [
            route for route in self.bgp_routes.values()
            if route.as_path_length > 10
        ]
        
        if long_paths:
            violations.append({
                "type": BGPSecurityViolationType.SUSPICIOUS_ANNOUNCEMENT,
                "description": "Routes with unusually long AS paths",
                "route_count": len(long_paths),
                "severity": SecurityThreatLevel.MEDIUM
            })
        
        return violations
    
    def calculate_topology_health(self) -> float:
        """Calculate overall topology health score."""
        if not self.bgp_peers:
            return 0.0
        
        # Peer health contribution (60% weight)
        peer_health_scores = [peer.calculate_session_health() for peer in self.bgp_peers.values()]
        peer_avg = sum(peer_health_scores) / len(peer_health_scores)
        
        # Established sessions ratio (30% weight)
        establishment_ratio = self.established_peers / self.total_peers if self.total_peers > 0 else 0
        
        # Security violations impact (10% weight)
        security_violations = self.detect_security_violations()
        security_penalty = min(0.5, len(security_violations) * 0.1)
        security_score = max(0.0, 1.0 - security_penalty)
        
        # Weighted average
        overall_score = (peer_avg * 0.6 + establishment_ratio * 0.3 + security_score * 0.1)
        
        return round(overall_score, 3)
    
    def update_health_status(self) -> None:
        """Update overall topology health status."""
        health_score = self.calculate_topology_health()
        
        if health_score >= 0.9:
            self.health_status = HealthStatus.HEALTHY
        elif health_score >= 0.7:
            self.health_status = HealthStatus.WARNING
        elif health_score >= 0.5:
            self.health_status = HealthStatus.DEGRADED
        elif health_score >= 0.3:
            self.health_status = HealthStatus.UNHEALTHY
        else:
            self.health_status = HealthStatus.CRITICAL
    
    def get_topology_summary(self) -> Dict[str, Any]:
        """Get comprehensive topology summary."""
        return {
            "bgp_topology_id": self.bgp_topology_id,
            "name": self.name,
            "description": self.description,
            "statistics": {
                "total_asns": len(self.autonomous_systems),
                "total_peers": self.total_peers,
                "established_peers": self.established_peers,
                "external_peers": len(self.get_external_peers()),
                "internal_peers": len(self.get_internal_peers()),
                "total_routes": self.total_routes,
                "health_score": self.calculate_topology_health()
            },
            "health_status": self.health_status.value,
            "threat_level": self.threat_level.value,
            "security_violations": len(self.detect_security_violations()),
            "last_update": self.last_update.isoformat() if self.last_update else None,
            "cloudwan_integration": {
                "segments": len(self.cloudwan_segments),
                "attachments": len(self.cloudwan_attachments)
            }
        }
    
    def integrate_with_network_topology(self, network_topology: NetworkTopology) -> None:
        """Integrate with base network topology."""
        self.network_topology = network_topology
        self.network_topology_id = network_topology.topology_id
        
        # Update network topology with BGP data
        if network_topology.bgp_topology_data is None:
            network_topology.bgp_topology_data = {}
        
        network_topology.bgp_topology_data.update({
            "bgp_topology_id": self.bgp_topology_id,
            "asn_count": len(self.autonomous_systems),
            "peer_count": self.total_peers,
            "route_count": self.total_routes,
            "health_score": self.calculate_topology_health()
        })
        
        # Update autonomous systems in network topology
        network_topology.autonomous_systems.update(self.autonomous_systems)
        
        self.update_timestamp()


# Export all classes
__all__ = [
    'BGPSessionDirection',
    'BGPAddressFamily',
    'BGPRouteModel',
    'BGPPeerModel',
    'BGPTopologyModel',
]