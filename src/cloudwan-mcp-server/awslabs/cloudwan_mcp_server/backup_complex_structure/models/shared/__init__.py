"""
Shared data models for CloudWAN MCP Server.

This package consolidates all shared data structures, enums, exceptions,
and base classes used across the MCP server to eliminate duplication
and ensure consistency.

Key Components:
- enums: Standardized enumerations for BGP, security, network elements
- exceptions: Comprehensive exception hierarchy with error context
- base: Enhanced base classes with multi-region support

Usage Example:
    from awslabs.cloudwan_mcp_server.models.shared import (
        BGPPeerState,
        SecurityThreatLevel,
        NetworkElementType,
        ValidationError,
        EnhancedBaseResponse
    )
    
    # Use standardized enums
    if peer.state == BGPPeerState.ESTABLISHED:
        print("BGP peer is established")
    
    # Use enhanced base response
    response = EnhancedBaseResponse(
        operation_id="test-123",
        status="success"
    )
    response.add_region_info("us-east-1", success=True, resources_count=5)
"""

# Import all shared enums
from .enums import (
    # BGP Protocol Enums
    BGPPeerState,
    BGPRouteType,
    CloudWANBGPPeerState,
    
    # Security Enums
    SecurityThreatLevel,
    BGPSecurityViolationType,
    RPKIValidationStatus,
    
    # Network Element Classification
    NetworkElementType,
    ConnectionType,
    AttachmentType,
    AttachmentState,
    
    # Health and Status
    HealthStatus,
    ValidationStatus,
    
    # Utility functions
    validate_enum_value,
    get_enum_mapping,
    get_enum_choices,
    
    # Enum collections
    BGP_RELATED_ENUMS,
    SECURITY_RELATED_ENUMS,
    NETWORK_RELATED_ENUMS,
    STATUS_RELATED_ENUMS,
    ALL_SHARED_ENUMS,
)

# Import all shared exceptions
from .exceptions import (
    # Base exception
    CloudWANMCPError,
    
    # Specific exception types
    ValidationError,
    AWSOperationError,
    BGPAnalysisError,
    SecurityThreatError,
    NetworkElementError,
    ConfigurationError,
    MultiRegionOperationError,
    TopologyError,
    
    # Utility functions
    create_error_response,
    is_recoverable_error,
    get_error_severity,
    
    # Exception collections
    VALIDATION_EXCEPTIONS,
    AWS_EXCEPTIONS,
    ANALYSIS_EXCEPTIONS,
    CORE_EXCEPTIONS,
    ALL_SHARED_EXCEPTIONS,
)

# Import enhanced base models
from .base import (
    # Mixins and supporting classes
    TimestampMixin,
    RegionInfo,
    PaginationInfo,
    PerformanceMetrics,
    CacheInfo,
    FilterCriteria,
    
    # Base response and resource models
    EnhancedBaseResponse,
    EnhancedAWSResource,
    
    # Generic types
    PaginatedResponse,
)

# Define what gets imported with "from awslabs.cloudwan_mcp_server.models.shared import *"
__all__ = [
    # Enums - BGP Protocol
    "BGPPeerState",
    "BGPRouteType", 
    "CloudWANBGPPeerState",
    
    # Enums - Security
    "SecurityThreatLevel",
    "BGPSecurityViolationType",
    "RPKIValidationStatus",
    
    # Enums - Network Elements
    "NetworkElementType",
    "ConnectionType",
    "AttachmentType",
    "AttachmentState",
    
    # Enums - Status
    "HealthStatus",
    "ValidationStatus",
    
    # Enum Utilities
    "validate_enum_value",
    "get_enum_mapping", 
    "get_enum_choices",
    
    # Enum Collections
    "BGP_RELATED_ENUMS",
    "SECURITY_RELATED_ENUMS",
    "NETWORK_RELATED_ENUMS", 
    "STATUS_RELATED_ENUMS",
    "ALL_SHARED_ENUMS",
    
    # Exceptions - Core
    "CloudWANMCPError",
    
    # Exceptions - Specific Types
    "ValidationError",
    "AWSOperationError",
    "BGPAnalysisError",
    "SecurityThreatError",
    "NetworkElementError",
    "ConfigurationError",
    "MultiRegionOperationError",
    "TopologyError",
    
    # Exception Utilities
    "create_error_response",
    "is_recoverable_error",
    "get_error_severity",
    
    # Exception Collections
    "VALIDATION_EXCEPTIONS",
    "AWS_EXCEPTIONS",
    "ANALYSIS_EXCEPTIONS",
    "CORE_EXCEPTIONS",
    "ALL_SHARED_EXCEPTIONS",
    
    # Base Models - Supporting Classes
    "TimestampMixin",
    "RegionInfo",
    "PaginationInfo",
    "PerformanceMetrics", 
    "CacheInfo",
    "FilterCriteria",
    
    # Base Models - Core Classes
    "EnhancedBaseResponse",
    "EnhancedAWSResource",
    "PaginatedResponse",
]

# Version information
__version__ = "1.0.0"
__author__ = "CloudWAN MCP Server Team"
__description__ = "Shared data models for CloudWAN MCP Server"

# Package metadata
PACKAGE_INFO = {
    "name": "cloudwan_mcp.models.shared",
    "version": __version__,
    "description": __description__,
    "enums_count": len(ALL_SHARED_ENUMS),
    "exceptions_count": len(ALL_SHARED_EXCEPTIONS),
    "provides": {
        "enums": {
            "bgp": len(BGP_RELATED_ENUMS),
            "security": len(SECURITY_RELATED_ENUMS), 
            "network": len(NETWORK_RELATED_ENUMS),
            "status": len(STATUS_RELATED_ENUMS),
        },
        "exceptions": {
            "validation": len(VALIDATION_EXCEPTIONS),
            "aws": len(AWS_EXCEPTIONS),
            "analysis": len(ANALYSIS_EXCEPTIONS),
        },
        "base_models": [
            "EnhancedBaseResponse",
            "EnhancedAWSResource", 
            "PaginatedResponse",
        ],
    }
}


def get_package_info() -> dict:
    """Get package information and statistics."""
    return PACKAGE_INFO.copy()


def validate_shared_models() -> bool:
    """
    Validate that all shared models are properly configured.
    
    Returns:
        True if all models are valid, False otherwise
    """
    try:
        # Test enum creation
        test_bgp_state = BGPPeerState.ESTABLISHED
        test_threat_level = SecurityThreatLevel.CRITICAL
        test_element_type = NetworkElementType.VPC
        test_health = HealthStatus.HEALTHY
        
        # Test exception creation  
        test_error = CloudWANMCPError("Test error")
        test_validation = ValidationError("Test validation error")
        
        # Test base model creation
        test_response = EnhancedBaseResponse()
        test_resource = EnhancedAWSResource(
            resource_id="test-123",
            resource_type="vpc",
            region="us-east-1"
        )
        
        return True
        
    except Exception as e:
        print(f"Shared models validation failed: {e}")
        return False


# Convenience functions for common operations
def create_bgp_peer_state_from_attachment(attachment_state: str) -> BGPPeerState:
    """Create BGP peer state from CloudWAN attachment state."""
    return BGPPeerState.from_attachment_state(attachment_state)


def create_standard_error_response(
    error: Exception,
    operation_id: str = None,
    component: str = None
) -> dict:
    """Create standardized error response from any exception."""
    response = create_error_response(error, operation_id)
    if component:
        response["component"] = component
    return response


def create_multi_region_response(
    operation_id: str = None,
    component: str = None
) -> EnhancedBaseResponse:
    """Create enhanced base response for multi-region operations."""
    response = EnhancedBaseResponse()
    if operation_id:
        response.operation_id = operation_id
    if component:
        response.component = component
    return response


# Export convenience functions
__all__.extend([
    "get_package_info",
    "validate_shared_models", 
    "create_bgp_peer_state_from_attachment",
    "create_standard_error_response",
    "create_multi_region_response",
])

# Initialize package
if __name__ == "__main__":
    # Run validation when package is executed directly
    if validate_shared_models():
        print("✅ All shared models validated successfully")
        print(f"📦 Package info: {get_package_info()}")
    else:
        print("❌ Shared models validation failed")