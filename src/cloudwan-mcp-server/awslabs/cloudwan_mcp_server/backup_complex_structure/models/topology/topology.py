"""
Network topology models for CloudWAN MCP Server.

This module provides comprehensive network topology modeling that consolidates
all existing topology discovery components. The models are designed with 
research-backed AWS CloudWAN best practices, multi-region support, performance
optimization, and integration with BGP domain models.

Key Features:
- Complete network topology representation with hierarchical relationships
- CloudWAN Core Network, Segment, and Attachment modeling
- Multi-region topology support with cross-region connectivity
- Integration with BGP domain models for routing topology
- Performance optimization through lazy loading and caching
- Change tracking with versioning and audit trails
- Network health monitoring and metrics collection
- Graph-based topology operations using networkx

References:
- AWS CloudWAN Documentation
- RFC 4271: BGP-4 Protocol
- AWS Network Topology Best Practices
- Multi-Region Network Architecture Patterns
"""

from datetime import datetime, timezone
from typing import (
    Any, Dict, List, Optional, Set, Tuple, 
    TypeVar
)
from enum import Enum
from uuid import uuid4
import json
from collections import defaultdict
import logging

from pydantic import Field, ConfigDict
import networkx as nx

from ..shared.base import (
    TimestampMixin, EnhancedAWSResource,
    PerformanceMetrics
)
from ..shared.enums import (
    NetworkElementType, ConnectionType, HealthStatus, ValidationStatus
)

logger = logging.getLogger(__name__)

T = TypeVar('T')


class TopologyScope(str, Enum):
    """Scope of topology discovery and analysis."""
    
    GLOBAL = "global"           # Complete multi-region topology
    REGIONAL = "regional"       # Single region topology
    CORE_NETWORK = "core_network"  # CloudWAN core network only
    VPC_FOCUSED = "vpc_focused"    # VPC and immediate connections
    SECURITY_FOCUSED = "security_focused"  # Security group relationships
    BGP_FOCUSED = "bgp_focused"    # BGP routing topology


class TopologyFormat(str, Enum):
    """Topology serialization formats."""
    
    JSON = "json"
    GRAPHML = "graphml"
    DOT = "dot"
    CYTOSCAPE = "cytoscape"
    D3_JSON = "d3_json"


class ChangeOperation(str, Enum):
    """Types of topology change operations."""
    
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    MOVE = "move"
    CONNECT = "connect"
    DISCONNECT = "disconnect"
    MODIFY_ATTRIBUTES = "modify_attributes"


class NetworkElement(EnhancedAWSResource):
    """
    Enhanced network element model with comprehensive metadata.
    
    Extends the base AWS resource model with network-specific attributes,
    hierarchical relationships, and CloudWAN integration.
    """
    
    model_config = ConfigDict(
        extra="allow",
        validate_assignment=True,
        use_enum_values=True,
        arbitrary_types_allowed=True
    )
    
    # Core network identity
    element_type: NetworkElementType = Field(
        description="Type of network element"
    )
    element_subtype: Optional[str] = Field(
        default=None,
        description="Specific subtype for detailed classification"
    )
    
    # Network addressing
    ip_addresses: List[str] = Field(
        default_factory=list,
        description="IP addresses associated with this element"
    )
    cidr_blocks: List[str] = Field(
        default_factory=list,
        description="CIDR blocks for this element"
    )
    dns_names: List[str] = Field(
        default_factory=list,
        description="DNS names associated with this element"
    )
    
    # Hierarchical relationships
    parent_element_id: Optional[str] = Field(
        default=None,
        description="Parent element ID in topology hierarchy"
    )
    child_element_ids: Set[str] = Field(
        default_factory=set,
        description="Child element IDs"
    )
    
    # CloudWAN specific attributes
    global_network_id: Optional[str] = Field(
        default=None,
        description="Associated global network ID"
    )
    edge_locations: List[str] = Field(
        default_factory=list,
        description="CloudWAN edge locations for this element"
    )
    network_function_group_name: Optional[str] = Field(
        default=None,
        description="Associated network function group"
    )
    
    # Network characteristics
    bandwidth_capacity: Optional[str] = Field(
        default=None,
        description="Bandwidth capacity (e.g., '10 Gbps')"
    )
    latency_ms: Optional[float] = Field(
        default=None,
        description="Network latency in milliseconds"
    )
    mtu: Optional[int] = Field(
        default=None,
        description="Maximum transmission unit"
    )
    
    # Security attributes
    security_group_ids: List[str] = Field(
        default_factory=list,
        description="Associated security group IDs"
    )
    network_acl_ids: List[str] = Field(
        default_factory=list,
        description="Associated network ACL IDs"
    )
    security_posture: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="Security assessment data"
    )
    
    # Operational metrics
    operational_metrics: Dict[str, Any] = Field(
        default_factory=dict,
        description="Real-time operational metrics"
    )
    utilization_metrics: Dict[str, float] = Field(
        default_factory=dict,
        description="Resource utilization metrics"
    )
    
    # Business context
    business_criticality: str = Field(
        default="medium",
        description="Business criticality level"
    )
    environment: str = Field(
        default="unknown",
        description="Environment (prod, staging, dev, etc.)"
    )
    cost_allocation_tags: Dict[str, str] = Field(
        default_factory=dict,
        description="Cost allocation and billing tags"
    )

    def get_full_identifier(self) -> str:
        """Get fully qualified identifier for this element."""
        return f"{self.region}:{self.element_type.value}:{self.resource_id}"
    
    def is_cloudwan_element(self) -> bool:
        """Check if element is CloudWAN specific."""
        return self.element_type.is_cloudwan_element() or bool(
            self.core_network_id or 
            self.segment_name or 
            self.global_network_id or
            self.network_function_group_name
        )
    
    def is_cross_region_element(self) -> bool:
        """Check if element spans multiple regions."""
        return self.element_type in (
            NetworkElementType.GLOBAL_NETWORK,
            NetworkElementType.CORE_NETWORK,
            NetworkElementType.TRANSIT_GATEWAY
        )
    
    def add_child_element(self, child_id: str) -> None:
        """Add a child element relationship."""
        self.child_element_ids.add(child_id)
        self.update_timestamp()
    
    def remove_child_element(self, child_id: str) -> None:
        """Remove a child element relationship."""
        self.child_element_ids.discard(child_id)
        self.update_timestamp()
    
    def get_security_score(self) -> float:
        """Calculate security score based on security posture."""
        if not self.security_posture:
            return 0.5  # Default neutral score
        
        # Basic scoring algorithm
        score = 1.0
        if self.security_posture.get("has_internet_access"):
            score -= 0.2
        if not self.security_posture.get("encrypted_in_transit", True):
            score -= 0.3
        if not self.security_posture.get("encrypted_at_rest", True):
            score -= 0.2
        if self.security_posture.get("open_security_groups", 0) > 0:
            score -= 0.3
        
        return max(0.0, min(1.0, score))
    
    def calculate_utilization_score(self) -> float:
        """Calculate overall utilization score."""
        if not self.utilization_metrics:
            return 0.0
        
        # Weighted average of different metrics
        weights = {
            "cpu_utilization": 0.3,
            "memory_utilization": 0.25,
            "network_utilization": 0.25,
            "storage_utilization": 0.2
        }
        
        total_score = 0.0
        total_weight = 0.0
        
        for metric, weight in weights.items():
            if metric in self.utilization_metrics:
                total_score += self.utilization_metrics[metric] * weight
                total_weight += weight
        
        return total_score / total_weight if total_weight > 0 else 0.0


class NetworkConnection(TimestampMixin):
    """
    Represents a connection between network elements.
    
    Models various types of network connections with performance metrics,
    security attributes, and operational characteristics.
    """
    
    model_config = ConfigDict(
        extra="allow",
        validate_assignment=True,
        use_enum_values=True,
        arbitrary_types_allowed=True
    )
    
    # Core connection identity
    connection_id: str = Field(
        default_factory=lambda: str(uuid4()),
        description="Unique connection identifier"
    )
    source_element_id: str = Field(
        description="Source network element ID"
    )
    target_element_id: str = Field(
        description="Target network element ID"
    )
    connection_type: ConnectionType = Field(
        description="Type of network connection"
    )
    
    # Connection state
    state: str = Field(
        default="active",
        description="Current connection state"
    )
    health_status: HealthStatus = Field(
        default=HealthStatus.UNKNOWN,
        description="Connection health status"
    )
    
    # Performance characteristics
    bandwidth: Optional[str] = Field(
        default=None,
        description="Available bandwidth"
    )
    latency_ms: Optional[float] = Field(
        default=None,
        description="Connection latency in milliseconds"
    )
    packet_loss_rate: Optional[float] = Field(
        default=None,
        description="Packet loss rate (0.0-1.0)"
    )
    jitter_ms: Optional[float] = Field(
        default=None,
        description="Network jitter in milliseconds"
    )
    
    # CloudWAN specific
    attachment_id: Optional[str] = Field(
        default=None,
        description="CloudWAN attachment ID"
    )
    segment_name: Optional[str] = Field(
        default=None,
        description="CloudWAN segment name"
    )
    edge_location: Optional[str] = Field(
        default=None,
        description="CloudWAN edge location"
    )
    core_network_id: Optional[str] = Field(
        default=None,
        description="Associated core network ID"
    )
    
    # BGP specific attributes
    bgp_session_info: Optional[Dict[str, Any]] = Field(
        default=None,
        description="BGP session information if applicable"
    )
    routing_protocols: List[str] = Field(
        default_factory=list,
        description="Active routing protocols"
    )
    
    # Cost and business attributes
    connection_cost: Optional[int] = Field(
        default=None,
        description="Routing cost/weight for this connection"
    )
    business_priority: str = Field(
        default="medium",
        description="Business priority level"
    )
    
    # Operational attributes
    last_seen: Optional[datetime] = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Last time connection was observed"
    )
    failure_count: int = Field(
        default=0,
        description="Number of recent failures"
    )
    uptime_percentage: Optional[float] = Field(
        default=None,
        description="Connection uptime percentage"
    )
    
    # Additional metadata
    properties: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional connection properties"
    )
    monitoring_enabled: bool = Field(
        default=True,
        description="Whether connection monitoring is enabled"
    )

    def is_healthy(self) -> bool:
        """Check if connection is in healthy state."""
        return self.health_status in (HealthStatus.HEALTHY, HealthStatus.WARNING)
    
    def is_high_latency(self, threshold_ms: float = 100.0) -> bool:
        """Check if connection has high latency."""
        return self.latency_ms is not None and self.latency_ms > threshold_ms
    
    def has_packet_loss(self, threshold: float = 0.01) -> bool:
        """Check if connection has significant packet loss."""
        return (self.packet_loss_rate is not None and 
                self.packet_loss_rate > threshold)
    
    def is_bgp_connection(self) -> bool:
        """Check if connection uses BGP."""
        return (self.connection_type == ConnectionType.BGP_SESSION or
                "bgp" in self.routing_protocols)
    
    def calculate_quality_score(self) -> float:
        """Calculate connection quality score (0.0-1.0)."""
        score = 1.0
        
        # Penalty for high latency
        if self.latency_ms is not None:
            if self.latency_ms > 200:
                score -= 0.3
            elif self.latency_ms > 100:
                score -= 0.1
        
        # Penalty for packet loss
        if self.packet_loss_rate is not None:
            score -= min(0.4, self.packet_loss_rate * 10)
        
        # Penalty for poor uptime
        if self.uptime_percentage is not None:
            if self.uptime_percentage < 0.99:
                score -= 0.2
            elif self.uptime_percentage < 0.999:
                score -= 0.1
        
        # Penalty for recent failures
        if self.failure_count > 0:
            score -= min(0.3, self.failure_count * 0.1)
        
        return max(0.0, min(1.0, score))
    
    def update_health_status(self, new_status: HealthStatus) -> None:
        """Update connection health status."""
        if new_status != self.health_status:
            self.health_status = new_status
            self.last_seen = datetime.now(timezone.utc)
            self.update_timestamp()


class TopologySnapshot(TimestampMixin):
    """
    Point-in-time snapshot of network topology.
    
    Captures the complete state of a network topology at a specific moment,
    enabling comparison, rollback, and historical analysis.
    """
    
    model_config = ConfigDict(
        extra="allow",
        validate_assignment=True
    )
    
    # Snapshot identity
    snapshot_id: str = Field(
        default_factory=lambda: str(uuid4()),
        description="Unique snapshot identifier"
    )
    topology_id: str = Field(
        description="Associated topology identifier"
    )
    version: str = Field(
        description="Topology version at snapshot time"
    )
    
    # Snapshot metadata
    name: Optional[str] = Field(
        default=None,
        description="Human-readable snapshot name"
    )
    description: Optional[str] = Field(
        default=None,
        description="Snapshot description"
    )
    scope: TopologyScope = Field(
        default=TopologyScope.REGIONAL,
        description="Scope of this snapshot"
    )
    
    # Snapshot content
    elements_snapshot: Dict[str, Dict[str, Any]] = Field(
        default_factory=dict,
        description="Serialized network elements"
    )
    connections_snapshot: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Serialized network connections"
    )
    
    # Performance and statistics
    element_count: int = Field(
        default=0,
        description="Number of elements in snapshot"
    )
    connection_count: int = Field(
        default=0,
        description="Number of connections in snapshot"
    )
    regions_covered: Set[str] = Field(
        default_factory=set,
        description="AWS regions covered by this snapshot"
    )
    
    # Snapshot quality metrics
    data_completeness_score: float = Field(
        default=0.0,
        description="Data completeness score (0.0-1.0)"
    )
    validation_status: ValidationStatus = Field(
        default=ValidationStatus.UNKNOWN,
        description="Snapshot validation status"
    )
    validation_errors: List[str] = Field(
        default_factory=list,
        description="Validation error messages"
    )
    
    # Business context
    environment: str = Field(
        default="unknown",
        description="Environment this snapshot represents"
    )
    compliance_tags: Dict[str, str] = Field(
        default_factory=dict,
        description="Compliance and audit tags"
    )
    
    # Metadata
    capture_duration_ms: Optional[float] = Field(
        default=None,
        description="Time taken to capture this snapshot"
    )
    source_system: str = Field(
        default="cloudwan_mcp",
        description="System that created this snapshot"
    )
    
    def calculate_statistics(self) -> Dict[str, Any]:
        """Calculate comprehensive snapshot statistics."""
        stats = {
            "total_elements": self.element_count,
            "total_connections": self.connection_count,
            "regions_count": len(self.regions_covered),
            "data_completeness": self.data_completeness_score,
            "validation_status": self.validation_status.value,
            "element_types": defaultdict(int),
            "connection_types": defaultdict(int),
            "health_distribution": defaultdict(int),
        }
        
        # Analyze element types
        for element_data in self.elements_snapshot.values():
            element_type = element_data.get("element_type", "unknown")
            stats["element_types"][element_type] += 1
        
        # Analyze connection types
        for connection_data in self.connections_snapshot:
            conn_type = connection_data.get("connection_type", "unknown")
            stats["connection_types"][conn_type] += 1
        
        return dict(stats)
    
    def get_element_by_id(self, element_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve element data from snapshot by ID."""
        return self.elements_snapshot.get(element_id)
    
    def find_connections_for_element(self, element_id: str) -> List[Dict[str, Any]]:
        """Find all connections involving a specific element."""
        connections = []
        for conn_data in self.connections_snapshot:
            if (conn_data.get("source_element_id") == element_id or
                conn_data.get("target_element_id") == element_id):
                connections.append(conn_data)
        return connections
    
    def validate_integrity(self) -> Tuple[bool, List[str]]:
        """Validate snapshot data integrity."""
        errors = []
        
        # Check element references in connections
        element_ids = set(self.elements_snapshot.keys())
        for conn_data in self.connections_snapshot:
            source_id = conn_data.get("source_element_id")
            target_id = conn_data.get("target_element_id")
            
            if source_id and source_id not in element_ids:
                errors.append(f"Connection references missing source element: {source_id}")
            if target_id and target_id not in element_ids:
                errors.append(f"Connection references missing target element: {target_id}")
        
        # Check element count consistency
        if len(self.elements_snapshot) != self.element_count:
            errors.append("Element count mismatch with actual elements")
        
        if len(self.connections_snapshot) != self.connection_count:
            errors.append("Connection count mismatch with actual connections")
        
        self.validation_errors = errors
        self.validation_status = (ValidationStatus.PASS if not errors else 
                                ValidationStatus.FAIL)
        
        return len(errors) == 0, errors


class TopologyDelta(TimestampMixin):
    """
    Represents changes between topology states.
    
    Captures the differences between two topology snapshots or states,
    enabling incremental updates, change tracking, and audit trails.
    """
    
    model_config = ConfigDict(
        extra="allow",
        validate_assignment=True,
        use_enum_values=True,
        arbitrary_types_allowed=True
    )
    
    # Delta identity
    delta_id: str = Field(
        default_factory=lambda: str(uuid4()),
        description="Unique delta identifier"
    )
    topology_id: str = Field(
        description="Associated topology identifier"
    )
    
    # Version information
    from_version: str = Field(
        description="Source topology version"
    )
    to_version: str = Field(
        description="Target topology version"
    )
    from_snapshot_id: Optional[str] = Field(
        default=None,
        description="Source snapshot ID"
    )
    to_snapshot_id: Optional[str] = Field(
        default=None,
        description="Target snapshot ID"
    )
    
    # Change operations
    element_changes: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Changes to network elements"
    )
    connection_changes: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Changes to network connections"
    )
    
    # Change statistics
    elements_added: int = Field(default=0, description="Number of elements added")
    elements_modified: int = Field(default=0, description="Number of elements modified")
    elements_removed: int = Field(default=0, description="Number of elements removed")
    connections_added: int = Field(default=0, description="Number of connections added")
    connections_modified: int = Field(default=0, description="Number of connections modified")
    connections_removed: int = Field(default=0, description="Number of connections removed")
    
    # Impact analysis
    impacted_regions: Set[str] = Field(
        default_factory=set,
        description="Regions impacted by changes"
    )
    criticality_impact: str = Field(
        default="low",
        description="Overall criticality impact"
    )
    security_impact: bool = Field(
        default=False,
        description="Whether changes have security implications"
    )
    
    # Business context
    change_category: str = Field(
        default="operational",
        description="Category of changes (operational, security, compliance, etc.)"
    )
    risk_level: str = Field(
        default="low",
        description="Risk level of changes"
    )
    
    # Metadata
    change_source: str = Field(
        default="automatic",
        description="Source of changes (automatic, user, system, etc.)"
    )
    change_reason: Optional[str] = Field(
        default=None,
        description="Reason for changes"
    )
    
    def add_element_change(self, operation: ChangeOperation, element_id: str, 
                          before: Optional[Dict[str, Any]] = None,
                          after: Optional[Dict[str, Any]] = None) -> None:
        """Add an element change to the delta."""
        change_record = {
            "operation": operation.value,
            "element_id": element_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "before": before,
            "after": after
        }
        
        self.element_changes.append(change_record)
        
        # Update statistics
        if operation == ChangeOperation.CREATE:
            self.elements_added += 1
        elif operation == ChangeOperation.UPDATE:
            self.elements_modified += 1
        elif operation == ChangeOperation.DELETE:
            self.elements_removed += 1
        
        # Extract impacted region
        if after and "region" in after:
            self.impacted_regions.add(after["region"])
        elif before and "region" in before:
            self.impacted_regions.add(before["region"])
    
    def add_connection_change(self, operation: ChangeOperation, connection_id: str,
                            before: Optional[Dict[str, Any]] = None,
                            after: Optional[Dict[str, Any]] = None) -> None:
        """Add a connection change to the delta."""
        change_record = {
            "operation": operation.value,
            "connection_id": connection_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "before": before,
            "after": after
        }
        
        self.connection_changes.append(change_record)
        
        # Update statistics
        if operation == ChangeOperation.CREATE:
            self.connections_added += 1
        elif operation == ChangeOperation.UPDATE:
            self.connections_modified += 1
        elif operation == ChangeOperation.DELETE:
            self.connections_removed += 1
    
    def get_total_changes(self) -> int:
        """Get total number of changes in this delta."""
        return (self.elements_added + self.elements_modified + self.elements_removed +
                self.connections_added + self.connections_modified + self.connections_removed)
    
    def has_significant_changes(self, threshold: int = 5) -> bool:
        """Check if delta contains significant changes."""
        return self.get_total_changes() >= threshold
    
    def get_change_summary(self) -> Dict[str, Any]:
        """Get human-readable change summary."""
        return {
            "total_changes": self.get_total_changes(),
            "elements": {
                "added": self.elements_added,
                "modified": self.elements_modified,
                "removed": self.elements_removed
            },
            "connections": {
                "added": self.connections_added,
                "modified": self.connections_modified,
                "removed": self.connections_removed
            },
            "impacted_regions": list(self.impacted_regions),
            "risk_level": self.risk_level,
            "security_impact": self.security_impact,
            "change_category": self.change_category
        }


class NetworkTopology(TimestampMixin):
    """
    Complete network topology representation.
    
    The main topology model that aggregates all network elements, connections,
    and relationships. Supports multi-region topologies, CloudWAN integration,
    BGP routing information, and comprehensive operational monitoring.
    """
    
    model_config = ConfigDict(
        extra="allow",
        validate_assignment=True,
        use_enum_values=True,
        arbitrary_types_allowed=True
    )
    
    # Core topology identity
    topology_id: str = Field(
        default_factory=lambda: str(uuid4()),
        description="Unique topology identifier"
    )
    name: str = Field(
        description="Human-readable topology name"
    )
    description: Optional[str] = Field(
        default=None,
        description="Topology description"
    )
    version: str = Field(
        default="1.0.0",
        description="Topology version"
    )
    
    # Topology scope and configuration
    scope: TopologyScope = Field(
        default=TopologyScope.REGIONAL,
        description="Scope of this topology"
    )
    regions: Set[str] = Field(
        default_factory=set,
        description="AWS regions included in this topology"
    )
    account_ids: Set[str] = Field(
        default_factory=set,
        description="AWS account IDs included in this topology"
    )
    
    # Network elements and connections
    elements: Dict[str, NetworkElement] = Field(
        default_factory=dict,
        description="Network elements indexed by element ID"
    )
    connections: Dict[str, NetworkConnection] = Field(
        default_factory=dict,
        description="Network connections indexed by connection ID"
    )
    
    # CloudWAN specific
    global_network_ids: Set[str] = Field(
        default_factory=set,
        description="CloudWAN global network IDs"
    )
    core_network_ids: Set[str] = Field(
        default_factory=set,
        description="CloudWAN core network IDs"
    )
    segments: Dict[str, Dict[str, Any]] = Field(
        default_factory=dict,
        description="CloudWAN segments and their configurations"
    )
    network_function_groups: Dict[str, Dict[str, Any]] = Field(
        default_factory=dict,
        description="Network function groups"
    )
    
    # BGP integration
    bgp_topology_data: Optional[Dict[str, Any]] = Field(
        default=None,
        description="BGP routing topology information"
    )
    autonomous_systems: Dict[int, Dict[str, Any]] = Field(
        default_factory=dict,
        description="BGP Autonomous Systems in topology"
    )
    
    # Topology graph
    graph: Optional[nx.MultiDiGraph] = Field(
        default=None,
        exclude=True,
        description="NetworkX graph representation (not serialized)"
    )
    graph_stale: bool = Field(
        default=True,
        exclude=True,
        description="Whether graph needs rebuilding"
    )
    
    # Operational state
    health_status: HealthStatus = Field(
        default=HealthStatus.UNKNOWN,
        description="Overall topology health"
    )
    last_discovery: Optional[datetime] = Field(
        default=None,
        description="Last topology discovery timestamp"
    )
    discovery_in_progress: bool = Field(
        default=False,
        description="Whether discovery is currently in progress"
    )
    
    # Performance metrics
    performance_metrics: Optional[PerformanceMetrics] = Field(
        default=None,
        description="Topology performance metrics"
    )
    discovery_duration_ms: Optional[float] = Field(
        default=None,
        description="Last discovery duration in milliseconds"
    )
    
    # Quality and validation
    data_quality_score: float = Field(
        default=0.0,
        description="Overall data quality score (0.0-1.0)"
    )
    validation_status: ValidationStatus = Field(
        default=ValidationStatus.UNKNOWN,
        description="Topology validation status"
    )
    validation_errors: List[str] = Field(
        default_factory=list,
        description="Validation error messages"
    )
    
    # Change tracking
    change_history: List[str] = Field(
        default_factory=list,
        description="Recent change delta IDs"
    )
    last_change: Optional[datetime] = Field(
        default=None,
        description="Last change timestamp"
    )
    
    # Business and operational context
    environment: str = Field(
        default="unknown",
        description="Environment (prod, staging, dev, etc.)"
    )
    business_service: Optional[str] = Field(
        default=None,
        description="Associated business service"
    )
    cost_center: Optional[str] = Field(
        default=None,
        description="Cost center for this topology"
    )
    compliance_frameworks: List[str] = Field(
        default_factory=list,
        description="Applicable compliance frameworks"
    )
    
    # Metadata and configuration
    discovery_config: Dict[str, Any] = Field(
        default_factory=dict,
        description="Topology discovery configuration"
    )
    monitoring_config: Dict[str, Any] = Field(
        default_factory=dict,
        description="Monitoring configuration"
    )
    tags: Dict[str, str] = Field(
        default_factory=dict,
        description="Topology tags"
    )

    def add_element(self, element: NetworkElement) -> None:
        """Add a network element to the topology."""
        self.elements[element.get_full_identifier()] = element
        self.regions.add(element.region)
        if element.owner_account_id:
            self.account_ids.add(element.owner_account_id)
        self._mark_graph_stale()
        self.update_timestamp()
    
    def remove_element(self, element_id: str) -> bool:
        """Remove a network element from the topology."""
        if element_id in self.elements:
            # Remove associated connections
            connections_to_remove = []
            for conn_id, connection in self.connections.items():
                if (connection.source_element_id == element_id or
                    connection.target_element_id == element_id):
                    connections_to_remove.append(conn_id)
            
            for conn_id in connections_to_remove:
                del self.connections[conn_id]
            
            # Remove element
            del self.elements[element_id]
            self._mark_graph_stale()
            self.update_timestamp()
            return True
        return False
    
    def add_connection(self, connection: NetworkConnection) -> None:
        """Add a network connection to the topology."""
        self.connections[connection.connection_id] = connection
        self._mark_graph_stale()
        self.update_timestamp()
    
    def remove_connection(self, connection_id: str) -> bool:
        """Remove a network connection from the topology."""
        if connection_id in self.connections:
            del self.connections[connection_id]
            self._mark_graph_stale()
            self.update_timestamp()
            return True
        return False
    
    def get_element_by_id(self, element_id: str) -> Optional[NetworkElement]:
        """Retrieve network element by ID."""
        return self.elements.get(element_id)
    
    def get_elements_by_type(self, element_type: NetworkElementType) -> List[NetworkElement]:
        """Get all elements of a specific type."""
        return [elem for elem in self.elements.values() 
                if elem.element_type == element_type]
    
    def get_elements_by_region(self, region: str) -> List[NetworkElement]:
        """Get all elements in a specific region."""
        return [elem for elem in self.elements.values() if elem.region == region]
    
    def get_cloudwan_elements(self) -> List[NetworkElement]:
        """Get all CloudWAN-specific elements."""
        return [elem for elem in self.elements.values() if elem.is_cloudwan_element()]
    
    def find_connections_for_element(self, element_id: str) -> List[NetworkConnection]:
        """Find all connections involving a specific element."""
        return [conn for conn in self.connections.values()
                if (conn.source_element_id == element_id or 
                    conn.target_element_id == element_id)]
    
    def get_element_neighbors(self, element_id: str) -> List[str]:
        """Get neighboring element IDs."""
        neighbors = []
        for connection in self.find_connections_for_element(element_id):
            if connection.source_element_id == element_id:
                neighbors.append(connection.target_element_id)
            else:
                neighbors.append(connection.source_element_id)
        return list(set(neighbors))
    
    def _mark_graph_stale(self) -> None:
        """Mark the internal graph as needing rebuild."""
        self.graph_stale = True
    
    def _ensure_graph_current(self) -> None:
        """Ensure internal graph is up to date."""
        if self.graph_stale or self.graph is None:
            self._build_graph()
    
    def _build_graph(self) -> None:
        """Build NetworkX graph from elements and connections."""
        self.graph = nx.MultiDiGraph()
        
        # Add nodes (elements)
        for element_id, element in self.elements.items():
            self.graph.add_node(
                element_id,
                element_type=element.element_type.value,
                region=element.region,
                name=element.name or element_id,
                **element.custom_attributes
            )
        
        # Add edges (connections)
        for connection in self.connections.values():
            self.graph.add_edge(
                connection.source_element_id,
                connection.target_element_id,
                connection_id=connection.connection_id,
                connection_type=connection.connection_type.value,
                state=connection.state,
                **connection.properties
            )
        
        self.graph_stale = False
    
    def get_shortest_path(self, source_id: str, target_id: str) -> Optional[List[str]]:
        """Find shortest path between two elements."""
        self._ensure_graph_current()
        try:
            return nx.shortest_path(self.graph, source_id, target_id)
        except (nx.NetworkXNoPath, nx.NetworkXError):
            return None
    
    def get_connected_components(self) -> List[Set[str]]:
        """Get strongly connected components in the topology."""
        self._ensure_graph_current()
        return [set(component) for component in 
                nx.strongly_connected_components(self.graph)]
    
    def calculate_centrality_metrics(self) -> Dict[str, Dict[str, float]]:
        """Calculate various centrality metrics for elements."""
        self._ensure_graph_current()
        
        metrics = {}
        try:
            # Degree centrality
            degree_centrality = nx.degree_centrality(self.graph)
            # Betweenness centrality
            betweenness_centrality = nx.betweenness_centrality(self.graph)
            # Closeness centrality
            closeness_centrality = nx.closeness_centrality(self.graph)
            
            # Combine metrics
            for node_id in self.graph.nodes():
                metrics[node_id] = {
                    'degree_centrality': degree_centrality.get(node_id, 0.0),
                    'betweenness_centrality': betweenness_centrality.get(node_id, 0.0),
                    'closeness_centrality': closeness_centrality.get(node_id, 0.0)
                }
        
        except Exception as e:
            logger.warning(f"Error calculating centrality metrics: {e}")
            
        return metrics
    
    def detect_network_anomalies(self) -> List[Dict[str, Any]]:
        """Detect potential network topology anomalies."""
        anomalies = []
        
        # Check for isolated nodes
        isolated_nodes = []
        for element_id, element in self.elements.items():
            connections = self.find_connections_for_element(element_id)
            if not connections:
                isolated_nodes.append(element_id)
        
        if isolated_nodes:
            anomalies.append({
                "type": "isolated_nodes",
                "description": "Network elements with no connections",
                "affected_elements": isolated_nodes,
                "severity": "medium"
            })
        
        # Check for high-degree nodes that might be bottlenecks
        centrality_metrics = self.calculate_centrality_metrics()
        high_centrality_nodes = []
        
        for element_id, metrics in centrality_metrics.items():
            if metrics.get('degree_centrality', 0) > 0.8:
                high_centrality_nodes.append(element_id)
        
        if high_centrality_nodes:
            anomalies.append({
                "type": "high_centrality_nodes",
                "description": "Network elements with very high connectivity",
                "affected_elements": high_centrality_nodes,
                "severity": "low"
            })
        
        # Check for unhealthy connections
        unhealthy_connections = []
        for conn_id, connection in self.connections.items():
            if not connection.is_healthy():
                unhealthy_connections.append(conn_id)
        
        if unhealthy_connections:
            anomalies.append({
                "type": "unhealthy_connections",
                "description": "Network connections in unhealthy state",
                "affected_connections": unhealthy_connections,
                "severity": "high"
            })
        
        return anomalies
    
    def calculate_health_score(self) -> float:
        """Calculate overall topology health score."""
        if not self.elements and not self.connections:
            return 0.0
        
        # Element health contribution (50% weight)
        element_health_scores = []
        for element in self.elements.values():
            if element.health_status == HealthStatus.HEALTHY:
                element_health_scores.append(1.0)
            elif element.health_status == HealthStatus.WARNING:
                element_health_scores.append(0.8)
            elif element.health_status == HealthStatus.DEGRADED:
                element_health_scores.append(0.6)
            elif element.health_status == HealthStatus.UNHEALTHY:
                element_health_scores.append(0.3)
            else:  # CRITICAL or UNKNOWN
                element_health_scores.append(0.0)
        
        element_avg = (sum(element_health_scores) / len(element_health_scores) 
                      if element_health_scores else 0.0)
        
        # Connection health contribution (40% weight)
        connection_health_scores = []
        for connection in self.connections.values():
            connection_health_scores.append(connection.calculate_quality_score())
        
        connection_avg = (sum(connection_health_scores) / len(connection_health_scores)
                         if connection_health_scores else 0.0)
        
        # Data quality contribution (10% weight)
        data_quality = self.data_quality_score
        
        # Weighted average
        overall_score = (element_avg * 0.5 + connection_avg * 0.4 + data_quality * 0.1)
        
        return round(overall_score, 3)
    
    def update_health_status(self) -> None:
        """Update overall topology health status."""
        health_score = self.calculate_health_score()
        
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
    
    def create_snapshot(self, name: Optional[str] = None) -> TopologySnapshot:
        """Create a point-in-time snapshot of the topology."""
        snapshot = TopologySnapshot(
            topology_id=self.topology_id,
            version=self.version,
            name=name or f"Snapshot_{datetime.now(timezone.utc).isoformat()}",
            scope=self.scope,
            element_count=len(self.elements),
            connection_count=len(self.connections),
            regions_covered=self.regions.copy(),
            environment=self.environment
        )
        
        # Serialize elements
        for element_id, element in self.elements.items():
            snapshot.elements_snapshot[element_id] = element.model_dump()
        
        # Serialize connections
        for connection in self.connections.values():
            snapshot.connections_snapshot.append(connection.model_dump())
        
        # Calculate data completeness
        snapshot.data_completeness_score = self.data_quality_score
        snapshot.validation_status = self.validation_status
        
        return snapshot
    
    def export_topology(self, format_type: TopologyFormat) -> str:
        """Export topology in specified format."""
        if format_type == TopologyFormat.JSON:
            return self.model_dump_json(indent=2, exclude={"graph", "graph_stale"})
        
        elif format_type == TopologyFormat.GRAPHML:
            self._ensure_graph_current()
            import io
            output = io.StringIO()
            nx.writegraphml(self.graph, output)
            return output.getvalue()
        
        elif format_type == TopologyFormat.DOT:
            self._ensure_graph_current()
            return nx.nx_pydot.to_pydot(self.graph).to_string()
        
        elif format_type == TopologyFormat.CYTOSCAPE:
            return json.dumps(nx.cytoscape_data(self.graph), indent=2)
        
        elif format_type == TopologyFormat.D3_JSON:
            return json.dumps(nx.node_link_data(self.graph), indent=2)
        
        else:
            raise ValueError(f"Unsupported export format: {format_type}")
    
    def get_topology_summary(self) -> Dict[str, Any]:
        """Get comprehensive topology summary."""
        return {
            "topology_id": self.topology_id,
            "name": self.name,
            "version": self.version,
            "scope": self.scope.value,
            "regions": list(self.regions),
            "accounts": list(self.account_ids),
            "statistics": {
                "total_elements": len(self.elements),
                "total_connections": len(self.connections),
                "element_types": {
                    elem_type.value: len([e for e in self.elements.values() 
                                        if e.element_type == elem_type])
                    for elem_type in NetworkElementType
                    if any(e.element_type == elem_type for e in self.elements.values())
                },
                "cloudwan_elements": len(self.get_cloudwan_elements()),
                "health_score": self.calculate_health_score(),
                "data_quality": self.data_quality_score,
            },
            "health_status": self.health_status.value,
            "last_discovery": self.last_discovery.isoformat() if self.last_discovery else None,
            "last_change": self.last_change.isoformat() if self.last_change else None,
            "environment": self.environment,
            "business_service": self.business_service,
        }


# Export all classes
__all__ = [
    'TopologyScope',
    'TopologyFormat', 
    'ChangeOperation',
    'NetworkElement',
    'NetworkConnection',
    'TopologySnapshot',
    'TopologyDelta',
    'NetworkTopology',
]