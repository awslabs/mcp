"""
BGP domain models for CloudWAN MCP Server.

This package provides comprehensive BGP modeling that consolidates functionality
from all BGP analyzers in the CloudWAN MCP Server. The models are designed to
support protocol-level analysis, CloudWAN integration, operational monitoring,
and security assessment in a unified, extensible framework.

Key Features:
- RFC 4271 compliant BGP protocol modeling
- CloudWAN-specific extensions and integrations
- Multi-region BGP operations support
- Comprehensive security threat modeling
- Operational monitoring and automation support
- Historical tracking and audit capabilities
- Performance metrics and SLA monitoring

Package Structure:
- peer.py: BGP peer information and configuration models
- route.py: BGP route information and analysis models
- session.py: BGP session state and lifecycle models

Usage Examples:

Basic BGP Peer Creation:
```python
from awslabs.cloudwan_mcp_server.models.bgp import BGPPeerInfo, BGPPeerConfiguration

config = BGPPeerConfiguration(
    local_asn=65000,
    peer_asn=65001,
    peer_ip="192.168.1.1"
)

peer = BGPPeerInfo(
    local_asn=65000,
    peer_asn=65001,
    peer_ip="192.168.1.1",
    region="us-west-2",
    configuration=config
)
```

CloudWAN BGP Peer:
```python
from awslabs.cloudwan_mcp_server.models.bgp import CloudWANBGPPeer
from awslabs.cloudwan_mcp_server.models.shared.enums import AttachmentType, AttachmentState

cloudwan_peer = CloudWANBGPPeer(
    resource_id="attachment-12345",
    resource_type="cloudwan_attachment",
    region="us-west-2",
    core_network_id="core-network-12345",
    attachment_id="attachment-12345",
    attachment_type=AttachmentType.VPC,
    attachment_state=AttachmentState.AVAILABLE,
    segment_name="production",
    edge_location="us-west-2-1",
    core_network_asn=64512
)
```

BGP Route Analysis:
```python
from awslabs.cloudwan_mcp_server.models.bgp import BGPRouteInfo, BGPPathAttributes
from awslabs.cloudwan_mcp_server.models.shared.enums import BGPRouteType, BGPOriginType

path_attrs = BGPPathAttributes(
    origin=BGPOriginType.IGP,
    as_path=[65000, 65001, 65002],
    next_hop="192.168.1.1"
)

route = BGPRouteInfo(
    prefix="10.0.0.0/24",
    path_attributes=path_attrs,
    route_type=BGPRouteType.PROPAGATED,
    region="us-west-2"
)

# Check route security
if route.is_secure_route():
    print("Route passes all security checks")
```

Session Monitoring:
```python
from awslabs.cloudwan_mcp_server.models.bgp import BGPSessionInfo, BGPSessionState
from awslabs.cloudwan_mcp_server.models.shared.enums import BGPPeerState, HealthStatus

session_state = BGPSessionState(
    local_asn=65000,
    peer_asn=65001,
    current_state=BGPPeerState.ESTABLISHED,
    region="us-west-2"
)

session = BGPSessionInfo(
    current_state=session_state,
    business_criticality="high"
)

# Check if session needs attention
if session.requires_attention():
    health_summary = session.get_health_summary()
    print(f"Session health: {health_summary}")
```

Route Analysis Workflow:
```python
from awslabs.cloudwan_mcp_server.models.bgp import RouteAnalysisResult

# Create analysis result
analysis = RouteAnalysisResult()
analysis.analyzed_routes = [route1, route2, route3]
analysis.calculate_summaries()

# Check security risk
risk_score = analysis.get_security_risk_score()
if risk_score > 0.7:
    print(f"High security risk detected: {risk_score}")
    for issue in analysis.critical_issues:
        print(f"Critical issue: {issue}")
```

Integration with Shared Infrastructure:
```python
# All BGP models integrate with shared enums and exceptions
from awslabs.cloudwan_mcp_server.models.shared.enums import (
    BGPPeerState, BGPRouteType, SecurityThreatLevel
)
from awslabs.cloudwan_mcp_server.models.shared.exceptions import (
    BGPAnalysisError, SecurityThreatError
)

# Models use enhanced base classes for multi-region support
from awslabs.cloudwan_mcp_server.models.shared.base import (
    EnhancedBaseResponse, TimestampMixin
)
```

Migration from Existing Analyzers:
The BGP models are designed to be drop-in replacements for the existing
analyzer-specific models, providing a migration path for:

1. BGP Protocol Analyzer → BGPPeerInfo, BGPSessionInfo
2. CloudWAN BGP Analyzer → CloudWANBGPPeer, BGPRouteInfo  
3. BGP Operations Analyzer → BGPSessionHistory, operational events
4. BGP Security Analyzer → RouteSecurityContext, security models

For detailed migration guides, see the individual analyzer documentation.
"""

# Core BGP models
from .peer import (
    # Peer-related models
    BGPPeerInfo,
    BGPPeerConfiguration, 
    BGPSessionCapabilities,
    BGPSessionMetrics,
    CloudWANBGPPeer,
    
    # Supporting enums and classes
    BGPCapability,
)

from .route import (
    # Route-related models
    BGPRouteInfo,
    BGPPathAttributes,
    BGPRouteMetrics,
    RouteSecurityContext,
    RouteAnalysisResult,
    
    # Supporting enums and classes
    BGPOriginType,
    BGPCommunityType,
)

from .session import (
    # Session-related models
    BGPSessionInfo,
    BGPSessionState,
    BGPSessionHistory,
    BGPSessionEvent,
    
    # Supporting enums and classes
    BGPSessionEventType,
)

# Convenience imports for commonly used shared models
from ..shared.enums import (
    BGPPeerState,
    BGPRouteType,
    CloudWANBGPPeerState,
    BGPSecurityViolationType,
    RPKIValidationStatus,
    SecurityThreatLevel,
    AttachmentType,
    AttachmentState,
)

from ..shared.exceptions import (
    BGPAnalysisError,
    SecurityThreatError,
    ValidationError,
)

from ..shared.base import (
    EnhancedBaseResponse,
    TimestampMixin,
    EnhancedAWSResource,
)

# Package metadata
__version__ = "1.0.0"
__author__ = "CloudWAN MCP Server"
__description__ = "Comprehensive BGP domain models for multi-analyzer consolidation"

# Export groups for organized imports
PEER_MODELS = [
    'BGPPeerInfo',
    'BGPPeerConfiguration', 
    'BGPSessionCapabilities',
    'BGPSessionMetrics',
    'CloudWANBGPPeer',
    'BGPCapability',
]

ROUTE_MODELS = [
    'BGPRouteInfo',
    'BGPPathAttributes',
    'BGPRouteMetrics',
    'RouteSecurityContext',
    'RouteAnalysisResult',
    'BGPOriginType',
    'BGPCommunityType',
]

SESSION_MODELS = [
    'BGPSessionInfo',
    'BGPSessionState',
    'BGPSessionHistory',
    'BGPSessionEvent',
    'BGPSessionEventType',
]

SHARED_ENUMS = [
    'BGPPeerState',
    'BGPRouteType',
    'CloudWANBGPPeerState',
    'BGPSecurityViolationType',
    'RPKIValidationStatus',
    'SecurityThreatLevel',
    'AttachmentType',
    'AttachmentState',
]

SHARED_EXCEPTIONS = [
    'BGPAnalysisError',
    'SecurityThreatError', 
    'ValidationError',
]

SHARED_BASE_CLASSES = [
    'EnhancedBaseResponse',
    'TimestampMixin',
    'EnhancedAWSResource',
]

# All exports
__all__ = (
    PEER_MODELS +
    ROUTE_MODELS + 
    SESSION_MODELS +
    SHARED_ENUMS +
    SHARED_EXCEPTIONS +
    SHARED_BASE_CLASSES +
    ['PEER_MODELS', 'ROUTE_MODELS', 'SESSION_MODELS', 'SHARED_ENUMS', 
     'SHARED_EXCEPTIONS', 'SHARED_BASE_CLASSES']
)


# Utility functions for model usage

def create_basic_peer(local_asn: int, peer_asn: int, peer_ip: str, 
                     region: str = "us-east-1") -> BGPPeerInfo:
    """
    Create a basic BGP peer with default configuration.
    
    Args:
        local_asn: Local AS number
        peer_asn: Peer AS number  
        peer_ip: Peer IP address
        region: AWS region
        
    Returns:
        Configured BGP peer instance
    """
    config = BGPPeerConfiguration(
        local_asn=local_asn,
        peer_asn=peer_asn,
        peer_ip=peer_ip
    )
    
    capabilities = BGPSessionCapabilities()
    metrics = BGPSessionMetrics()
    
    return BGPPeerInfo(
        local_asn=local_asn,
        peer_asn=peer_asn,
        peer_ip=peer_ip,
        region=region,
        configuration=config,
        capabilities=capabilities,
        metrics=metrics
    )


def create_cloudwan_peer(core_network_id: str, attachment_id: str, 
                        segment_name: str, edge_location: str,
                        core_network_asn: int, region: str) -> CloudWANBGPPeer:
    """
    Create a CloudWAN BGP peer with standard configuration.
    
    Args:
        core_network_id: Core Network ID
        attachment_id: Attachment ID
        segment_name: Segment name
        edge_location: Edge location
        core_network_asn: Core Network ASN
        region: AWS region
        
    Returns:
        Configured CloudWAN BGP peer instance
    """
    return CloudWANBGPPeer(
        resource_id=attachment_id,
        resource_type="cloudwan_attachment", 
        region=region,
        core_network_id=core_network_id,
        attachment_id=attachment_id,
        attachment_type=AttachmentType.VPC,  # Default to VPC
        attachment_state=AttachmentState.AVAILABLE,
        segment_name=segment_name,
        edge_location=edge_location,
        core_network_asn=core_network_asn
    )


def create_session_from_peer(peer: BGPPeerInfo) -> BGPSessionInfo:
    """
    Create a BGP session from a peer configuration.
    
    Args:
        peer: BGP peer instance
        
    Returns:
        Initialized BGP session instance
    """
    session_state = BGPSessionState(
        local_asn=peer.local_asn,
        peer_asn=peer.peer_asn,
        local_ip=peer.local_ip,
        peer_ip=peer.peer_ip,
        region=peer.region
    )
    
    history = BGPSessionHistory(session_id=session_state.session_id)
    
    return BGPSessionInfo(
        session_id=session_state.session_id,
        current_state=session_state,
        history=history
    )


def validate_bgp_models() -> bool:
    """
    Validate that all BGP models are properly configured and importable.
    
    Returns:
        True if all models validate successfully
    """
    try:
        # Test basic model creation
        peer = create_basic_peer(65000, 65001, "192.168.1.1")
        session = create_session_from_peer(peer)
        
        # Test CloudWAN model
        cloudwan_peer = create_cloudwan_peer(
            "core-12345", "attach-12345", "prod", "us-east-1-1", 64512, "us-east-1"
        )
        
        # Test route creation
        path_attrs = BGPPathAttributes(
            origin=BGPOriginType.IGP,
            as_path=[65000, 65001],
            next_hop="192.168.1.1"
        )
        
        route = BGPRouteInfo(
            prefix="10.0.0.0/24",
            path_attributes=path_attrs,
            route_type=BGPRouteType.PROPAGATED,
            region="us-east-1"
        )
        
        # Test analysis result
        analysis = RouteAnalysisResult()
        analysis.analyzed_routes = [route]
        analysis.calculate_summaries()
        
        return True
        
    except Exception as e:
        print(f"BGP model validation failed: {e}")
        return False


# Model compatibility mappings for migration from existing analyzers
BGP_ANALYZER_MIGRATIONS = {
    # BGP Protocol Analyzer migrations
    "BGPPeerInfo": "cloudwan_mcp.models.bgp.BGPPeerInfo",
    "BGPRouteInfo": "cloudwan_mcp.models.bgp.BGPRouteInfo", 
    "BGPSessionMetrics": "cloudwan_mcp.models.bgp.BGPSessionMetrics",
    
    # CloudWAN BGP Analyzer migrations
    "CloudWANBGPPeerInfo": "cloudwan_mcp.models.bgp.CloudWANBGPPeer",
    "CoreNetworkBGPConfig": "cloudwan_mcp.models.bgp.BGPPeerConfiguration",
    
    # Operations Analyzer migrations
    "OperationalAlert": "cloudwan_mcp.models.bgp.BGPSessionEvent",
    "AutomationAction": "cloudwan_mcp.models.bgp.BGPSessionEventType",
    
    # Security Analyzer migrations  
    "BGPSecurityThreat": "cloudwan_mcp.models.bgp.RouteSecurityContext",
    "RPKIValidationResult": "cloudwan_mcp.models.bgp.RouteSecurityContext",
}

# Performance optimization hints
MODEL_PERFORMANCE_HINTS = {
    "BGPPeerInfo": "Use peer_id for efficient lookups, enable monitoring selectively",
    "BGPRouteInfo": "Index by prefix for fast route lookups, use route_id for correlation",
    "BGPSessionInfo": "Monitor session_id for real-time updates, limit event history size",
    "RouteAnalysisResult": "Call calculate_summaries() before accessing summary fields",
}

# Validation rules for production deployment
PRODUCTION_VALIDATION_RULES = {
    "required_fields": [
        "BGPPeerInfo.local_asn", "BGPPeerInfo.peer_asn", "BGPPeerInfo.region",
        "BGPRouteInfo.prefix", "BGPRouteInfo.path_attributes", "BGPRouteInfo.region",
        "BGPSessionInfo.session_id", "BGPSessionInfo.current_state",
    ],
    "performance_limits": {
        "BGPSessionHistory.events": 1000,  # Maximum events to retain
        "BGPRouteMetrics.region_propagation": 50,  # Maximum regions
        "BGPPeerInfo.troubleshooting_notes": 100,  # Maximum notes
    },
    "security_requirements": [
        "Enable RPKI validation for production routes",
        "Monitor security_context for all routes", 
        "Set appropriate business_criticality levels",
        "Configure automation_rules for high-criticality sessions",
    ]
}