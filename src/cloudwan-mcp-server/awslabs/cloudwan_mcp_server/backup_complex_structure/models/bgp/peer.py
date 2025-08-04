"""
BGP peer models for CloudWAN MCP Server.

This module provides comprehensive BGP peer modeling that consolidates functionality
from all BGP analyzers including protocol-level analysis, CloudWAN integration,
operational monitoring, and security threat detection.

Key Features:
- RFC 4271 compliant BGP peer state modeling
- CloudWAN attachment-based peer discovery and management
- Comprehensive session metrics and performance tracking
- Multi-region peer relationship support
- Security threat context and RPKI validation
- Operational monitoring with SLA and alerting integration
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Union
from pydantic import BaseModel, Field, field_validator
from enum import Enum
import ipaddress
import uuid

from ..shared.enums import (
    BGPPeerState, 
    CloudWANBGPPeerState,
    AttachmentType,
    AttachmentState,
    HealthStatus
)
from ..shared.base import TimestampMixin, EnhancedAWSResource


class BGPCapability(str, Enum):
    """BGP capabilities as defined in RFC standards."""
    
    MULTIPROTOCOL = "multiprotocol"              # RFC 4760
    ROUTE_REFRESH = "route-refresh"              # RFC 2918
    FOUR_OCTET_ASN = "4-octet-asn"              # RFC 6793
    GRACEFUL_RESTART = "graceful-restart"        # RFC 4724
    ADDPATH = "add-path"                         # RFC 7911
    EXTENDED_NEXTHOP = "extended-nexthop"        # RFC 5549
    BGP_EXTENDED_MESSAGE = "extended-message"    # RFC 8654
    ENHANCED_ROUTE_REFRESH = "enhanced-route-refresh"  # RFC 7313

    def is_multiprotocol_capability(self) -> bool:
        """Check if capability is multiprotocol related."""
        return self in (self.MULTIPROTOCOL, self.EXTENDED_NEXTHOP)

    def is_resilience_capability(self) -> bool:
        """Check if capability enhances session resilience."""
        return self in (self.GRACEFUL_RESTART, self.ENHANCED_ROUTE_REFRESH)


class BGPSessionCapabilities(BaseModel):
    """BGP session capabilities negotiated between peers."""
    
    advertised: Set[BGPCapability] = Field(
        default_factory=set,
        description="Capabilities advertised by local peer"
    )
    received: Set[BGPCapability] = Field(
        default_factory=set,
        description="Capabilities received from remote peer"
    )
    negotiated: Set[BGPCapability] = Field(
        default_factory=set,
        description="Successfully negotiated capabilities"
    )
    
    # Protocol version information
    bgp_version: int = Field(default=4, description="BGP protocol version")
    hold_time: int = Field(default=180, description="Negotiated hold time in seconds")
    keepalive_time: int = Field(default=60, description="Keepalive interval in seconds")
    
    # Address family support
    address_families: List[str] = Field(
        default_factory=list,
        description="Supported address families (IPv4, IPv6, VPNv4, etc.)"
    )
    
    # Extended capabilities
    graceful_restart_time: Optional[int] = Field(
        default=None,
        description="Graceful restart time in seconds"
    )
    max_prefix_limit: Optional[int] = Field(
        default=None,
        description="Maximum number of prefixes accepted"
    )

    def has_capability(self, capability: BGPCapability) -> bool:
        """Check if capability was successfully negotiated."""
        return capability in self.negotiated

    def is_graceful_restart_enabled(self) -> bool:
        """Check if graceful restart is enabled."""
        return BGPCapability.GRACEFUL_RESTART in self.negotiated

    def supports_4byte_asn(self) -> bool:
        """Check if 4-byte ASN support is enabled."""
        return BGPCapability.FOUR_OCTET_ASN in self.negotiated

    def get_capability_mismatch(self) -> Set[BGPCapability]:
        """Get capabilities that were advertised but not negotiated."""
        return self.advertised - self.negotiated


class BGPSessionMetrics(BaseModel):
    """Comprehensive BGP session performance and reliability metrics."""
    
    # Basic counters
    messages_sent: int = Field(default=0, description="Total messages sent")
    messages_received: int = Field(default=0, description="Total messages received")
    keepalive_sent: int = Field(default=0, description="Keepalive messages sent")
    keepalive_received: int = Field(default=0, description="Keepalive messages received")
    
    # Route metrics
    prefixes_received: int = Field(default=0, description="Prefixes received from peer")
    prefixes_advertised: int = Field(default=0, description="Prefixes advertised to peer")
    prefixes_active: int = Field(default=0, description="Active prefixes in RIB")
    prefixes_withdrawn: int = Field(default=0, description="Prefixes withdrawn")
    
    # Session reliability metrics
    session_flaps: int = Field(default=0, description="Number of session flaps")
    last_flap_time: Optional[datetime] = Field(
        default=None, 
        description="Timestamp of last session flap"
    )
    uptime_seconds: int = Field(default=0, description="Current session uptime in seconds")
    total_uptime_seconds: int = Field(default=0, description="Total historical uptime")
    
    # Performance metrics
    avg_message_processing_time_ms: Optional[float] = Field(
        default=None,
        description="Average message processing time in milliseconds"
    )
    max_message_processing_time_ms: Optional[float] = Field(
        default=None,
        description="Maximum message processing time in milliseconds"
    )
    queue_depth: int = Field(default=0, description="Current message queue depth")
    
    # Error tracking
    notification_errors_sent: int = Field(default=0, description="Notification errors sent")
    notification_errors_received: int = Field(default=0, description="Notification errors received")
    last_error_code: Optional[str] = Field(default=None, description="Last BGP error code")
    last_error_time: Optional[datetime] = Field(default=None, description="Last error timestamp")
    
    # Multi-region metrics
    region_metrics: Dict[str, Dict[str, Union[int, float]]] = Field(
        default_factory=dict,
        description="Per-region session metrics"
    )

    def get_session_availability(self) -> float:
        """Calculate session availability percentage."""
        if self.total_uptime_seconds == 0:
            return 0.0
        total_time = self.total_uptime_seconds + (self.session_flaps * 30)  # Assume 30s downtime per flap
        return (self.total_uptime_seconds / total_time) * 100.0

    def get_flap_rate_per_hour(self, observation_period_hours: int = 24) -> float:
        """Calculate session flap rate per hour."""
        if observation_period_hours <= 0:
            return 0.0
        return self.session_flaps / observation_period_hours

    def is_session_stable(self, max_flaps_per_hour: int = 1) -> bool:
        """Check if session is considered stable."""
        return self.get_flap_rate_per_hour() <= max_flaps_per_hour

    def add_region_metric(self, region: str, metric: str, value: Union[int, float]) -> None:
        """Add a metric for a specific region."""
        if region not in self.region_metrics:
            self.region_metrics[region] = {}
        self.region_metrics[region][metric] = value


class BGPPeerConfiguration(BaseModel):
    """BGP peer configuration parameters and policy settings."""
    
    # Core BGP configuration
    local_asn: int = Field(description="Local Autonomous System Number")
    peer_asn: int = Field(description="Peer Autonomous System Number")
    local_ip: Optional[str] = Field(default=None, description="Local BGP speaker IP")
    peer_ip: Optional[str] = Field(default=None, description="Peer IP address")
    
    # Session parameters
    hold_time: int = Field(default=180, description="BGP hold timer in seconds")
    keepalive_interval: int = Field(default=60, description="Keepalive interval in seconds")
    connect_retry_interval: int = Field(default=120, description="Connect retry interval in seconds")
    
    # Route filtering and policy
    import_policy: Optional[str] = Field(default=None, description="Import route policy name")
    export_policy: Optional[str] = Field(default=None, description="Export route policy name")
    route_map_in: Optional[str] = Field(default=None, description="Inbound route map")
    route_map_out: Optional[str] = Field(default=None, description="Outbound route map")
    
    # Prefix limits
    max_prefixes: Optional[int] = Field(default=None, description="Maximum prefixes allowed")
    max_prefixes_warning_threshold: Optional[int] = Field(
        default=None, 
        description="Warning threshold for prefix count"
    )
    max_prefixes_action: Optional[str] = Field(
        default="log", 
        description="Action when max prefixes exceeded (log, shutdown, restart)"
    )
    
    # Authentication and security
    md5_password: Optional[str] = Field(default=None, description="MD5 authentication password")
    ttl_security_hops: Optional[int] = Field(default=None, description="TTL security hop count")
    
    # Advanced features
    bfd_enabled: bool = Field(default=False, description="Bidirectional Forwarding Detection enabled")
    graceful_restart_enabled: bool = Field(default=False, description="Graceful restart enabled")
    route_refresh_enabled: bool = Field(default=True, description="Route refresh capability enabled")
    
    # Multi-hop configuration
    ebgp_multihop: Optional[int] = Field(default=None, description="eBGP multihop TTL value")
    update_source: Optional[str] = Field(default=None, description="Update source interface")
    
    # Performance tuning
    advertisement_interval: int = Field(default=30, description="Advertisement interval in seconds")
    minimum_advertisement_interval: int = Field(default=5, description="Minimum advertisement interval")
    
    @field_validator('peer_ip', 'local_ip')
    @classmethod
    def validate_ip_address(cls, v):
        """Validate IP addresses."""
        if v is not None:
            try:
                ipaddress.ip_address(v)
            except ValueError:
                raise ValueError(f"Invalid IP address: {v}")
        return v

    @field_validator('local_asn', 'peer_asn')
    @classmethod
    def validate_asn(cls, v):
        """Validate ASN ranges."""
        if not (1 <= v <= 4294967295):  # 32-bit ASN range
            raise ValueError(f"ASN must be between 1 and 4294967295, got: {v}")
        return v

    def is_ibgp_session(self) -> bool:
        """Check if this is an iBGP session."""
        return self.local_asn == self.peer_asn

    def is_ebgp_session(self) -> bool:
        """Check if this is an eBGP session."""
        return self.local_asn != self.peer_asn

    def requires_multihop(self) -> bool:
        """Check if session requires multihop configuration."""
        return self.ebgp_multihop is not None and self.ebgp_multihop > 1


class CloudWANBGPPeer(EnhancedAWSResource):
    """CloudWAN-specific BGP peer information extending base AWS resource."""
    
    # CloudWAN specific identification
    core_network_id: str = Field(description="Core Network ID")
    core_network_arn: Optional[str] = Field(default=None, description="Core Network ARN")
    attachment_id: str = Field(description="CloudWAN attachment ID")
    attachment_type: AttachmentType = Field(description="Type of CloudWAN attachment")
    attachment_state: AttachmentState = Field(description="Current attachment state")
    
    # Segment and edge information
    segment_name: str = Field(description="CloudWAN segment name")
    edge_location: str = Field(description="Edge location identifier")
    
    # Network configuration
    core_network_asn: int = Field(description="Core Network ASN")
    peer_asn: Optional[int] = Field(default=None, description="Peer ASN if available")
    
    # Connection details
    resource_arn: Optional[str] = Field(
        default=None, 
        description="ARN of the attached resource (VPC, TGW, etc.)"
    )
    inside_cidr_blocks: List[str] = Field(
        default_factory=list,
        description="Inside CIDR blocks for the attachment"
    )
    
    # Policy and routing
    network_function_group_name: Optional[str] = Field(
        default=None,
        description="Associated Network Function Group"
    )
    routing_policy_version: Optional[int] = Field(
        default=None,
        description="Current routing policy version"
    )
    
    # Enhanced CloudWAN metadata
    creation_time: Optional[datetime] = Field(
        default=None, 
        description="Attachment creation timestamp"
    )
    last_modification_time: Optional[datetime] = Field(
        default=None,
        description="Last modification timestamp"
    )
    proposed_segment_change: Optional[str] = Field(
        default=None,
        description="Proposed segment change pending approval"
    )

    def get_cloudwan_peer_state(self) -> CloudWANBGPPeerState:
        """Convert attachment state to CloudWAN BGP peer state."""
        state_mapping = {
            AttachmentState.AVAILABLE: CloudWANBGPPeerState.AVAILABLE,
            AttachmentState.CREATING: CloudWANBGPPeerState.CREATING,
            AttachmentState.UPDATING: CloudWANBGPPeerState.UPDATING,
            AttachmentState.DELETING: CloudWANBGPPeerState.DELETING,
            AttachmentState.FAILED: CloudWANBGPPeerState.FAILED,
            AttachmentState.REJECTED: CloudWANBGPPeerState.FAILED,
            AttachmentState.PENDING_ATTACHMENT_ACCEPTANCE: CloudWANBGPPeerState.PENDING,
            AttachmentState.PENDING_NETWORK_UPDATE: CloudWANBGPPeerState.UPDATING,
            AttachmentState.PENDING_TAG_ACCEPTANCE: CloudWANBGPPeerState.PENDING,
        }
        return state_mapping.get(self.attachment_state, CloudWANBGPPeerState.PENDING)

    def is_operational(self) -> bool:
        """Check if CloudWAN attachment is operational."""
        return self.attachment_state.is_operational()

    def supports_bgp(self) -> bool:
        """Check if attachment type supports BGP."""
        bgp_supporting_types = {
            AttachmentType.VPC,
            AttachmentType.VPN,
            AttachmentType.DIRECT_CONNECT_GATEWAY,
            AttachmentType.CONNECT
        }
        return self.attachment_type in bgp_supporting_types

    def is_cross_region_attachment(self, core_network_region: str) -> bool:
        """Check if this is a cross-region attachment."""
        return self.region != core_network_region


class BGPPeerInfo(TimestampMixin):
    """
    Comprehensive BGP peer information model consolidating all analyzer functionality.
    
    This model serves as the primary BGP peer representation, integrating protocol-level
    details, CloudWAN specifics, operational metrics, and security context.
    """
    
    # Unique identification
    peer_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique peer identifier"
    )
    
    # Core peer information
    local_asn: int = Field(description="Local Autonomous System Number")
    peer_asn: int = Field(description="Peer Autonomous System Number")
    local_ip: Optional[str] = Field(default=None, description="Local BGP speaker IP")
    peer_ip: Optional[str] = Field(default=None, description="Peer IP address")
    
    # BGP FSM state
    bgp_state: BGPPeerState = Field(
        default=BGPPeerState.IDLE,
        description="Current BGP Finite State Machine state"
    )
    
    # Region and location
    region: str = Field(description="AWS region where peer is located")
    availability_zone: Optional[str] = Field(default=None, description="Availability zone")
    
    # Session information
    session_established_time: Optional[datetime] = Field(
        default=None,
        description="When current session was established"
    )
    session_duration_seconds: int = Field(
        default=0,
        description="Current session duration in seconds"
    )
    session_attempts: int = Field(
        default=0, 
        description="Number of session establishment attempts"
    )
    
    # Configuration
    configuration: BGPPeerConfiguration = Field(default_factory=lambda: BGPPeerConfiguration(local_asn=1, peer_asn=1), description="BGP peer configuration")
    capabilities: BGPSessionCapabilities = Field(default_factory=BGPSessionCapabilities, description="Session capabilities")
    
    # Performance metrics
    metrics: BGPSessionMetrics = Field(default_factory=BGPSessionMetrics, description="Session performance metrics")
    
    # CloudWAN integration (optional)
    cloudwan_info: Optional[CloudWANBGPPeer] = Field(
        default=None,
        description="CloudWAN-specific peer information"
    )
    
    # Health and validation
    health_status: HealthStatus = Field(
        default=HealthStatus.UNKNOWN,
        description="Overall peer health status"
    )
    last_health_check: Optional[datetime] = Field(
        default=None,
        description="Last health check timestamp"
    )
    
    # Error and troubleshooting
    last_error_message: Optional[str] = Field(
        default=None,
        description="Last error message received"
    )
    last_error_time: Optional[datetime] = Field(
        default=None,
        description="Timestamp of last error"
    )
    troubleshooting_notes: List[str] = Field(
        default_factory=list,
        description="Operational troubleshooting notes"
    )
    
    # Security context
    security_threats: List[str] = Field(
        default_factory=list,
        description="Active security threat IDs"
    )
    rpki_validation_enabled: bool = Field(
        default=False,
        description="Whether RPKI validation is enabled"
    )
    
    # Operational context
    monitoring_enabled: bool = Field(default=True, description="Whether monitoring is enabled")
    sla_tier: Optional[str] = Field(default=None, description="SLA tier for this peer")
    business_impact: str = Field(
        default="low", 
        description="Business impact level (low, medium, high, critical)"
    )
    
    # Additional metadata
    tags: Dict[str, str] = Field(default_factory=dict, description="Resource tags")
    custom_attributes: Dict[str, Any] = Field(
        default_factory=dict, 
        description="Custom operational attributes"
    )

    @field_validator('peer_ip', 'local_ip')
    @classmethod
    def validate_ip_addresses(cls, v):
        """Validate IP addresses if provided."""
        if v is not None:
            try:
                ipaddress.ip_address(v)
            except ValueError:
                raise ValueError(f"Invalid IP address: {v}")
        return v

    @field_validator('local_asn', 'peer_asn')
    @classmethod
    def validate_asn_numbers(cls, v):
        """Validate ASN ranges."""
        if not (1 <= v <= 4294967295):
            raise ValueError(f"ASN must be between 1 and 4294967295, got: {v}")
        return v

    def is_session_established(self) -> bool:
        """Check if BGP session is established."""
        return self.bgp_state == BGPPeerState.ESTABLISHED

    def is_session_connecting(self) -> bool:
        """Check if session is in connecting states."""
        return self.bgp_state.is_connecting()

    def is_ibgp_peer(self) -> bool:
        """Check if this is an iBGP peer."""
        return self.local_asn == self.peer_asn

    def is_ebgp_peer(self) -> bool:
        """Check if this is an eBGP peer."""
        return self.local_asn != self.peer_asn

    def is_cloudwan_peer(self) -> bool:
        """Check if this is a CloudWAN-managed peer."""
        return self.cloudwan_info is not None

    def is_healthy(self) -> bool:
        """Check if peer is healthy overall."""
        return (
            self.health_status in (HealthStatus.HEALTHY, HealthStatus.WARNING) and
            self.is_session_established()
        )

    def has_security_threats(self) -> bool:
        """Check if peer has active security threats."""
        return len(self.security_threats) > 0

    def get_session_uptime_hours(self) -> float:
        """Get session uptime in hours."""
        return self.session_duration_seconds / 3600.0

    def add_troubleshooting_note(self, note: str) -> None:
        """Add a troubleshooting note."""
        timestamp = datetime.now(timezone.utc).isoformat()
        self.troubleshooting_notes.append(f"{timestamp}: {note}")

    def add_security_threat(self, threat_id: str) -> None:
        """Add a security threat reference."""
        if threat_id not in self.security_threats:
            self.security_threats.append(threat_id)

    def remove_security_threat(self, threat_id: str) -> None:
        """Remove a security threat reference."""
        if threat_id in self.security_threats:
            self.security_threats.remove(threat_id)

    def update_health_status(self, new_status: HealthStatus, reason: Optional[str] = None) -> None:
        """Update health status with timestamp."""
        self.health_status = new_status
        self.last_health_check = datetime.now(timezone.utc)
        if reason:
            self.add_troubleshooting_note(f"Health status changed to {new_status}: {reason}")

    def to_summary(self) -> Dict[str, Any]:
        """Create a summary view of the BGP peer."""
        return {
            "peer_id": self.peer_id,
            "peer_asn": self.peer_asn,
            "peer_ip": self.peer_ip,
            "bgp_state": self.bgp_state,
            "region": self.region,
            "health_status": self.health_status,
            "session_established": self.is_session_established(),
            "uptime_hours": self.get_session_uptime_hours(),
            "is_cloudwan": self.is_cloudwan_peer(),
            "security_threats": len(self.security_threats),
            "last_updated": self.updated_at.isoformat(),
        }