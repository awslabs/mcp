"""
Shared enums for CloudWAN MCP Server.

This module consolidates all shared enumerations used across the MCP server
to eliminate duplication and ensure consistency. All enums follow RFC standards
where applicable and include comprehensive documentation.

Key Features:
- BGP protocol enums following RFC 4271 and CloudWAN extensions
- Network element type classification for multi-region support
- Security threat level standardization across all security tools
- Health and validation status standardization
- Comprehensive type hints and validation support
"""

from enum import Enum
from typing import List, Optional, Dict, Any


# =============================================================================
# BGP Protocol Enums (RFC 4271 Compliant)
# =============================================================================

class BGPPeerState(str, Enum):
    """
    BGP Finite State Machine states per RFC 4271 Section 8.
    
    These states represent the standard BGP peer connection lifecycle
    as defined in the BGP specification. Used for protocol-level analysis
    and peer relationship tracking.
    
    References:
        - RFC 4271: A Border Gateway Protocol 4 (BGP-4)
        - Section 8: BGP Finite State Machine
    """
    IDLE = "Idle"
    CONNECT = "Connect"  
    ACTIVE = "Active"
    OPEN_SENT = "OpenSent"
    OPEN_CONFIRM = "OpenConfirm"
    ESTABLISHED = "Established"

    @classmethod
    def from_attachment_state(cls, attachment_state: str) -> "BGPPeerState":
        """Map AWS attachment state to BGP FSM state."""
        mapping = {
            "available": cls.ESTABLISHED,
            "pending-acceptance": cls.CONNECT,
            "initiating": cls.ACTIVE,
            "creating": cls.CONNECT,
            "updating": cls.ACTIVE,
            "failed": cls.IDLE,
            "deleting": cls.IDLE,
            "deleted": cls.IDLE,
        }
        return mapping.get(attachment_state.lower(), cls.IDLE)

    def is_established(self) -> bool:
        """Check if peer is in established state."""
        return self == self.ESTABLISHED

    def is_connecting(self) -> bool:
        """Check if peer is in connecting states."""
        return self in (self.CONNECT, self.ACTIVE, self.OPEN_SENT, self.OPEN_CONFIRM)


class BGPRouteType(str, Enum):
    """
    BGP route types with CloudWAN extensions.
    
    Covers standard BGP route origins plus CloudWAN-specific route types
    for comprehensive route classification and analysis.
    
    References:
        - RFC 4271: BGP-4 Origin Attribute
        - AWS CloudWAN Route Types
    """
    # Standard BGP origins
    IGP = "igp"                    # Route learned from interior gateway protocol
    EGP = "egp"                    # Route learned from exterior gateway protocol  
    INCOMPLETE = "incomplete"      # Route learned by other means
    
    # CloudWAN specific types
    STATIC = "static"              # Statically configured route
    PROPAGATED = "propagated"      # Route propagated from attachments
    NETWORK_FUNCTION = "network-function"  # Route via network function group
    PEERING = "peering"           # Route via peering connection
    LOCAL = "local"               # Local network route
    
    # Extended types for comprehensive coverage
    AGGREGATE = "aggregate"        # Aggregated route
    REDISTRIBUTED = "redistributed"  # Redistributed from other protocols
    DEFAULT = "default"           # Default route

    def is_learned_route(self) -> bool:
        """Check if route is learned (not locally configured)."""
        return self in (self.PROPAGATED, self.PEERING, self.EGP, self.REDISTRIBUTED)

    def is_local_route(self) -> bool:
        """Check if route is locally configured."""
        return self in (self.STATIC, self.LOCAL, self.IGP, self.AGGREGATE)


class CloudWANBGPPeerState(str, Enum):
    """
    CloudWAN-specific BGP peer states for AWS attachment lifecycle.
    
    Maps CloudWAN attachment states to BGP concepts for consistent
    analysis across CloudWAN and traditional BGP environments.
    
    References:
        - AWS CloudWAN Attachment States
        - CloudWAN BGP Integration
    """
    AVAILABLE = "available"
    PENDING = "pending"
    CREATING = "creating"
    DELETING = "deleting"
    FAILED = "failed"
    UPDATING = "updating"
    PENDING_ACCEPTANCE = "pending-acceptance"
    REJECTED = "rejected"

    def to_bgp_state(self) -> BGPPeerState:
        """Convert to standard BGP FSM state."""
        mapping = {
            self.AVAILABLE: BGPPeerState.ESTABLISHED,
            self.PENDING: BGPPeerState.CONNECT,
            self.CREATING: BGPPeerState.CONNECT,
            self.UPDATING: BGPPeerState.ACTIVE,
            self.PENDING_ACCEPTANCE: BGPPeerState.CONNECT,
            self.FAILED: BGPPeerState.IDLE,
            self.DELETING: BGPPeerState.IDLE,
            self.REJECTED: BGPPeerState.IDLE,
        }
        return mapping.get(self, BGPPeerState.IDLE)


# =============================================================================
# Security Enums (Standardized Across All Security Tools)
# =============================================================================

class SecurityThreatLevel(str, Enum):
    """
    Standardized security threat severity levels.
    
    Used consistently across all security analysis tools including
    BGP security analyzer, firewall log analyzer, and anomaly detection.
    Provides numerical mapping for threat scoring and prioritization.
    
    References:
        - NIST Cybersecurity Framework
        - RFC 4949: Internet Security Glossary
    """
    CRITICAL = "critical"    # Immediate action required
    HIGH = "high"           # Urgent attention needed  
    MEDIUM = "medium"       # Moderate risk level
    LOW = "low"            # Minor security concern
    INFO = "info"          # Informational only
    UNKNOWN = "unknown"    # Cannot determine severity

    def get_numeric_value(self) -> int:
        """Get numeric value for threat level comparison."""
        mapping = {
            self.CRITICAL: 100,
            self.HIGH: 80,
            self.MEDIUM: 60,
            self.LOW: 40,
            self.INFO: 20,
            self.UNKNOWN: 0,
        }
        return mapping.get(self, 0)

    def requires_immediate_action(self) -> bool:
        """Check if threat level requires immediate action."""
        return self in (self.CRITICAL, self.HIGH)

    @classmethod
    def from_score(cls, score: int) -> "SecurityThreatLevel":
        """Convert numeric score to threat level."""
        if score >= 90:
            return cls.CRITICAL
        elif score >= 70:
            return cls.HIGH
        elif score >= 50:
            return cls.MEDIUM
        elif score >= 30:
            return cls.LOW
        elif score >= 10:
            return cls.INFO
        else:
            return cls.UNKNOWN


class BGPSecurityViolationType(str, Enum):
    """
    BGP security violation types for comprehensive threat analysis.
    
    Covers all major BGP security threats including prefix hijacking,
    route leaks, and protocol violations. Used by BGP security analyzer
    for consistent threat classification.
    
    References:
        - RFC 7454: BGP Operations and Security
        - RFC 6811: BGP Prefix Origin Validation
        - NIST SP 800-54: Border Gateway Protocol Security
    """
    PREFIX_HIJACKING = "prefix_hijacking"
    ROUTE_LEAK = "route_leak"
    AS_PATH_PREPENDING = "as_path_prepending"
    ORIGIN_SPOOFING = "origin_spoofing"
    BGP_HIJACKING = "bgp_hijacking"
    INVALID_ORIGIN_AS = "invalid_origin_as"
    RPKI_INVALID = "rpki_invalid"
    SUSPICIOUS_ANNOUNCEMENT = "suspicious_announcement"
    WITHDRAWAL_ATTACK = "withdrawal_attack"
    SESSION_HIJACKING = "session_hijacking"

    def get_default_severity(self) -> SecurityThreatLevel:
        """Get default severity level for violation type."""
        severity_mapping = {
            self.PREFIX_HIJACKING: SecurityThreatLevel.CRITICAL,
            self.BGP_HIJACKING: SecurityThreatLevel.CRITICAL,
            self.SESSION_HIJACKING: SecurityThreatLevel.CRITICAL,
            self.ORIGIN_SPOOFING: SecurityThreatLevel.HIGH,
            self.ROUTE_LEAK: SecurityThreatLevel.HIGH,
            self.INVALID_ORIGIN_AS: SecurityThreatLevel.HIGH,
            self.RPKI_INVALID: SecurityThreatLevel.HIGH,
            self.WITHDRAWAL_ATTACK: SecurityThreatLevel.MEDIUM,
            self.AS_PATH_PREPENDING: SecurityThreatLevel.LOW,
            self.SUSPICIOUS_ANNOUNCEMENT: SecurityThreatLevel.MEDIUM,
        }
        return severity_mapping.get(self, SecurityThreatLevel.UNKNOWN)


class RPKIValidationStatus(str, Enum):
    """
    RPKI validation status for BGP route origin validation.
    
    Implements RFC 6811 validation states for Resource Public Key
    Infrastructure based origin validation of BGP announcements.
    
    References:
        - RFC 6811: BGP Prefix Origin Validation
        - RFC 6480: An Infrastructure to Support Secure Internet Routing
    """
    VALID = "valid"             # Route is RPKI valid
    INVALID = "invalid"         # Route is RPKI invalid
    NOT_FOUND = "not_found"     # No RPKI record found
    ERROR = "error"             # Validation error occurred
    UNKNOWN = "unknown"         # Status cannot be determined

    def is_secure(self) -> bool:
        """Check if validation status indicates secure route."""
        return self == self.VALID

    def has_security_concern(self) -> bool:
        """Check if status indicates potential security issue."""
        return self in (self.INVALID, self.ERROR)


# =============================================================================
# Network Element Classification
# =============================================================================

class NetworkElementType(str, Enum):
    """
    Comprehensive network element types for multi-region CloudWAN topologies.
    
    Provides complete classification of all AWS network components with
    CloudWAN extensions. Used throughout the system for topology discovery,
    diagram generation, and network analysis.
    
    Categories:
        - Core Infrastructure: Global networks, core networks, transit gateways
        - Compute: VPCs, subnets, instances
        - Connectivity: Gateways, endpoints, connections
        - Security: Firewalls, security groups, network ACLs
        - CloudWAN: Segments, attachments, network function groups
    """
    
    # Core Infrastructure
    GLOBAL_NETWORK = "global_network"
    CORE_NETWORK = "core_network"
    TRANSIT_GATEWAY = "transit_gateway"
    
    # Compute & Networking
    VPC = "vpc"
    SUBNET = "subnet"
    INSTANCE = "instance"
    NETWORK_INTERFACE = "network_interface"
    ELASTIC_IP = "elastic_ip"
    
    # Connectivity
    INTERNET_GATEWAY = "internet_gateway"
    NAT_GATEWAY = "nat_gateway"
    VPC_ENDPOINT = "vpc_endpoint"
    DIRECT_CONNECT = "direct_connect"
    DIRECT_CONNECT_GATEWAY = "direct_connect_gateway"
    VPN_CONNECTION = "vpn_connection"
    VPN_GATEWAY = "vpn_gateway"
    CUSTOMER_GATEWAY = "customer_gateway"
    
    # Load Balancing
    LOAD_BALANCER = "load_balancer"
    APPLICATION_LOAD_BALANCER = "application_load_balancer"
    NETWORK_LOAD_BALANCER = "network_load_balancer"
    GATEWAY_LOAD_BALANCER = "gateway_load_balancer"
    
    # Security
    SECURITY_GROUP = "security_group"
    NETWORK_ACL = "network_acl"
    NETWORK_FIREWALL = "network_firewall"
    WEB_APPLICATION_FIREWALL = "web_application_firewall"
    
    # Routing
    ROUTE_TABLE = "route_table"
    ROUTE_53_RESOLVER = "route_53_resolver"
    
    # CloudWAN Specific
    SEGMENT = "segment"
    ATTACHMENT = "attachment"
    NETWORK_FUNCTION_GROUP = "network_function_group"
    EDGE_LOCATION = "edge_location"
    
    # Container & Serverless
    EKS_CLUSTER = "eks_cluster"
    ECS_CLUSTER = "ecs_cluster"
    LAMBDA_FUNCTION = "lambda_function"
    
    # Storage & Data
    S3_ENDPOINT = "s3_endpoint"
    RDS_INSTANCE = "rds_instance"
    ELASTICACHE_CLUSTER = "elasticache_cluster"

    def is_cloudwan_element(self) -> bool:
        """Check if element is CloudWAN specific."""
        return self in (
            self.GLOBAL_NETWORK,
            self.CORE_NETWORK,
            self.SEGMENT,
            self.ATTACHMENT,
            self.NETWORK_FUNCTION_GROUP,
            self.EDGE_LOCATION,
        )

    def is_security_element(self) -> bool:
        """Check if element is security related."""
        return self in (
            self.SECURITY_GROUP,
            self.NETWORK_ACL,
            self.NETWORK_FIREWALL,
            self.WEB_APPLICATION_FIREWALL,
        )

    def is_connectivity_element(self) -> bool:
        """Check if element provides connectivity."""
        return self in (
            self.INTERNET_GATEWAY,
            self.NAT_GATEWAY,
            self.VPN_CONNECTION,
            self.VPN_GATEWAY,
            self.DIRECT_CONNECT,
            self.DIRECT_CONNECT_GATEWAY,
            self.TRANSIT_GATEWAY,
        )

    def get_diagram_category(self) -> str:
        """Get diagram category for visualization grouping."""
        category_mapping = {
            # Infrastructure
            self.GLOBAL_NETWORK: "infrastructure",
            self.CORE_NETWORK: "infrastructure", 
            self.TRANSIT_GATEWAY: "infrastructure",
            
            # Compute
            self.VPC: "compute",
            self.SUBNET: "compute",
            self.INSTANCE: "compute",
            self.EKS_CLUSTER: "compute",
            self.ECS_CLUSTER: "compute",
            
            # Connectivity
            self.INTERNET_GATEWAY: "connectivity",
            self.NAT_GATEWAY: "connectivity",
            self.VPN_CONNECTION: "connectivity",
            self.DIRECT_CONNECT: "connectivity",
            
            # Security
            self.SECURITY_GROUP: "security",
            self.NETWORK_FIREWALL: "security",
            self.NETWORK_ACL: "security",
            
            # CloudWAN
            self.SEGMENT: "cloudwan",
            self.ATTACHMENT: "cloudwan",
            self.NETWORK_FUNCTION_GROUP: "cloudwan",
        }
        return category_mapping.get(self, "other")


# =============================================================================
# Connection and Attachment Types
# =============================================================================

class ConnectionType(str, Enum):
    """
    Network connection types between elements.
    
    Defines the nature of connections in network topologies for
    accurate relationship modeling and path analysis.
    """
    ATTACHMENT = "attachment"
    PEERING = "peering"
    ROUTING = "routing"
    ASSOCIATION = "association"
    PROPAGATION = "propagation"
    BGP_SESSION = "bgp_session"
    PHYSICAL = "physical"
    SEGMENT_CONNECTION = "segment_connection"
    NETWORK_FUNCTION = "network_function"
    CROSS_ACCOUNT = "cross_account"
    CROSS_REGION = "cross_region"
    VPN_TUNNEL = "vpn_tunnel"
    DIRECT_CONNECT_VIRTUAL_INTERFACE = "direct_connect_virtual_interface"

    def is_logical_connection(self) -> bool:
        """Check if connection is logical (not physical)."""
        return self not in (self.PHYSICAL, self.DIRECT_CONNECT_VIRTUAL_INTERFACE)

    def requires_authentication(self) -> bool:
        """Check if connection type requires authentication."""
        return self in (
            self.BGP_SESSION,
            self.VPN_TUNNEL,
            self.CROSS_ACCOUNT,
        )


class AttachmentType(str, Enum):
    """
    CloudWAN attachment types following AWS specifications.
    
    References:
        - AWS CloudWAN Attachments Documentation
    """
    VPC = "VPC"
    VPN = "VPN"
    DIRECT_CONNECT_GATEWAY = "DIRECT_CONNECT_GATEWAY"
    CONNECT = "CONNECT"
    SITE_TO_SITE_VPN = "SITE_TO_SITE_VPN"
    PEERING = "PEERING"

    def supports_propagation(self) -> bool:
        """Check if attachment type supports route propagation."""
        return self in (self.VPC, self.VPN, self.DIRECT_CONNECT_GATEWAY)

    def is_site_connection(self) -> bool:
        """Check if attachment connects external sites."""
        return self in (self.VPN, self.SITE_TO_SITE_VPN, self.DIRECT_CONNECT_GATEWAY)


class AttachmentState(str, Enum):
    """
    CloudWAN attachment states following AWS lifecycle.
    
    References:
        - AWS CloudWAN Attachment States
    """
    PENDING_ATTACHMENT_ACCEPTANCE = "PENDING_ATTACHMENT_ACCEPTANCE"
    CREATING = "CREATING"
    AVAILABLE = "AVAILABLE"
    PENDING_NETWORK_UPDATE = "PENDING_NETWORK_UPDATE"
    PENDING_TAG_ACCEPTANCE = "PENDING_TAG_ACCEPTANCE"
    DELETING = "DELETING"
    DELETED = "DELETED"
    FAILED = "FAILED"
    UPDATING = "UPDATING"
    REJECTED = "REJECTED"

    def is_operational(self) -> bool:
        """Check if attachment is in operational state."""
        return self == self.AVAILABLE

    def is_transitional(self) -> bool:
        """Check if attachment is in transitional state."""
        return self in (
            self.CREATING,
            self.UPDATING,
            self.DELETING,
            self.PENDING_NETWORK_UPDATE,
            self.PENDING_ATTACHMENT_ACCEPTANCE,
            self.PENDING_TAG_ACCEPTANCE,
        )

    def is_failed_state(self) -> bool:
        """Check if attachment is in failed state."""
        return self in (self.FAILED, self.REJECTED, self.DELETED)


# =============================================================================
# Health and Status Enums
# =============================================================================

class HealthStatus(str, Enum):
    """
    Standardized health status across all system components.
    
    Used by monitoring, heartbeat, performance analysis, and
    validation systems for consistent health reporting.
    """
    HEALTHY = "healthy"         # All systems operational
    DEGRADED = "degraded"       # Some issues but functional
    UNHEALTHY = "unhealthy"     # Significant issues
    CRITICAL = "critical"       # Critical issues requiring immediate attention
    UNKNOWN = "unknown"         # Health cannot be determined
    WARNING = "warning"         # Warning conditions detected

    def get_numeric_score(self) -> int:
        """Get numeric health score for comparison."""
        mapping = {
            self.HEALTHY: 100,
            self.WARNING: 80,
            self.DEGRADED: 60,
            self.UNHEALTHY: 40,
            self.CRITICAL: 20,
            self.UNKNOWN: 0,
        }
        return mapping.get(self, 0)

    def is_acceptable(self) -> bool:
        """Check if health status is acceptable for operation."""
        return self in (self.HEALTHY, self.WARNING, self.DEGRADED)

    def requires_attention(self) -> bool:
        """Check if health status requires attention."""
        return self in (self.UNHEALTHY, self.CRITICAL, self.UNKNOWN)


class ValidationStatus(str, Enum):
    """
    Validation result status for network validation tools.
    
    Used by network validation, policy validation, and
    configuration analysis tools for consistent reporting.
    """
    PASS = "pass"               # Validation passed
    FAIL = "fail"              # Validation failed
    WARNING = "warning"         # Validation passed with warnings
    UNKNOWN = "unknown"         # Validation status unknown
    SKIPPED = "skipped"         # Validation was skipped
    ERROR = "error"            # Error during validation

    def is_successful(self) -> bool:
        """Check if validation was successful."""
        return self in (self.PASS, self.WARNING)

    def has_issues(self) -> bool:
        """Check if validation found issues."""
        return self in (self.FAIL, self.WARNING, self.ERROR)

    def should_block_deployment(self) -> bool:
        """Check if status should block deployment."""
        return self in (self.FAIL, self.ERROR)


# =============================================================================
# Utility Functions for Enum Conversions and Validation
# =============================================================================

def validate_enum_value(enum_class: type, value: str, default: Optional[Enum] = None) -> Enum:
    """
    Validate and convert string value to enum with fallback.
    
    Args:
        enum_class: The enum class to validate against
        value: String value to convert
        default: Default enum value if conversion fails
        
    Returns:
        Validated enum value or default
    """
    try:
        # Try direct conversion
        if hasattr(enum_class, value.upper()):
            return getattr(enum_class, value.upper())
        
        # Try case-insensitive lookup
        for enum_val in enum_class:
            if enum_val.value.lower() == value.lower():
                return enum_val
                
        # Return default if provided
        if default is not None:
            return default
            
        # Fallback to first enum value
        return list(enum_class)[0]
        
    except (AttributeError, IndexError):
        if default is not None:
            return default
        # Ultimate fallback
        return list(enum_class)[0] if enum_class else None


def get_enum_mapping(enum_class: type) -> Dict[str, Any]:
    """
    Get complete mapping of enum values.
    
    Args:
        enum_class: Enum class to map
        
    Returns:
        Dictionary mapping enum names to values
    """
    return {e.name: e.value for e in enum_class}


def get_enum_choices(enum_class: type) -> List[str]:
    """
    Get list of valid enum choices for validation.
    
    Args:
        enum_class: Enum class
        
    Returns:
        List of valid enum values
    """
    return [e.value for e in enum_class]


# Export commonly used enum combinations
BGP_RELATED_ENUMS = [
    BGPPeerState,
    BGPRouteType, 
    CloudWANBGPPeerState,
    BGPSecurityViolationType,
    RPKIValidationStatus,
]

SECURITY_RELATED_ENUMS = [
    SecurityThreatLevel,
    BGPSecurityViolationType,
    RPKIValidationStatus,
]

NETWORK_RELATED_ENUMS = [
    NetworkElementType,
    ConnectionType,
    AttachmentType,
    AttachmentState,
]

STATUS_RELATED_ENUMS = [
    HealthStatus,
    ValidationStatus,
]

ALL_SHARED_ENUMS = (
    BGP_RELATED_ENUMS + 
    SECURITY_RELATED_ENUMS + 
    NETWORK_RELATED_ENUMS + 
    STATUS_RELATED_ENUMS
)