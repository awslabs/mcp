"""
Network topology models for CloudWAN MCP Server.

This package provides comprehensive network topology modeling that consolidates
all existing topology discovery components into unified, research-backed models.
Built with full CloudWAN support, BGP integration, multi-region capabilities,
performance optimization, and change tracking mechanisms.

Key Features:
- Complete network topology representation with hierarchical relationships
- CloudWAN Core Network, Segment, and Attachment modeling with policy integration
- Multi-region topology support with cross-region connectivity analysis
- Integration with BGP domain models for comprehensive routing topology
- Specialized network elements (VPC, Transit Gateway, Security, NFG)
- Performance optimization through lazy loading, caching, and graph algorithms
- Change tracking with versioning, audit trails, and delta calculation
- Network health monitoring and comprehensive metrics collection
- Business impact assessment and operational recommendations

Package Structure:
- topology.py: Core topology models (NetworkTopology, NetworkElement, NetworkConnection)
- elements.py: Specialized element models (VPC, TGW, CloudWAN, Security, NFG)
- metrics.py: Performance and health monitoring models

Integration Points:
- Uses shared enums and base classes from models.shared
- Integrates with BGP domain models from models.bgp
- Compatible with existing topology discovery components
- Supports export to multiple visualization formats

Usage Examples:

Basic Topology Creation:
```python
from awslabs.cloudwan_mcp_server.models.network import NetworkTopology, NetworkElement
from awslabs.cloudwan_mcp_server.models.shared.enums import NetworkElementType, HealthStatus

# Create topology
topology = NetworkTopology(
    name="Production Network",
    description="Multi-region production topology",
    scope=TopologyScope.GLOBAL
)

# Create network element
vpc_element = NetworkElement(
    resource_id="vpc-12345",
    resource_type="vpc",
    region="us-west-2",
    element_type=NetworkElementType.VPC,
    name="Production VPC",
    health_status=HealthStatus.HEALTHY
)

topology.add_element(vpc_element)
```

CloudWAN Integration:
```python
from awslabs.cloudwan_mcp_server.models.network import CloudWANElement
from awslabs.cloudwan_mcp_server.models.shared.enums import AttachmentType, AttachmentState

# Create CloudWAN Core Network element
core_network = CloudWANElement(
    resource_id="core-network-12345",
    resource_type="core_network",
    region="global",
    element_type=NetworkElementType.CORE_NETWORK,
    cloudwan_element_type="core_network",
    global_network_id="global-network-12345"
)

# Add segment configuration
core_network.add_segment("production", {
    "name": "production",
    "description": "Production segment",
    "isolate_attachments": False,
    "require_attachment_acceptance": False
})

topology.add_element(core_network)
```

Specialized Elements:
```python
from awslabs.cloudwan_mcp_server.models.network import (
    VPCElement, TransitGatewayElement, SecurityElement, NetworkFunctionElement
)

# VPC with subnet management
vpc = VPCElement(
    resource_id="vpc-prod-12345",
    resource_type="vpc",
    region="us-west-2",
    vpc_id="vpc-prod-12345",
    cidr_block="10.0.0.0/16",
    security_mode=VPCSecurityMode.STANDARD
)

vpc.add_subnet("subnet-12345", is_public=True)
vpc.add_subnet("subnet-67890", is_public=False)

# Transit Gateway with peering
tgw = TransitGatewayElement(
    resource_id="tgw-12345",
    resource_type="transit_gateway",
    region="us-west-2",
    transit_gateway_id="tgw-12345",
    amazon_side_asn=64512
)

tgw.add_peering_connection("pcx-12345", "tgw-67890", "us-east-1")

# Network Function Group
nfg = NetworkFunctionElement(
    resource_id="nfg-firewall-12345",
    resource_type="network_function_group",
    region="us-west-2",
    function_type=NetworkFunctionType.FIREWALL,
    target_capacity=3,
    auto_scaling_enabled=True
)
```

Performance Monitoring:
```python
from awslabs.cloudwan_mcp_server.models.network import NetworkMetrics, ConnectivityMetrics, TopologyMetrics

# Element performance monitoring
element_metrics = NetworkMetrics(
    element_id=vpc.get_full_identifier(),
    element_type=vpc.element_type.value,
    region=vpc.region
)

element_metrics.add_latency_measurement(45.2)
element_metrics.add_utilization_measurement(0.75)

# Connection monitoring
connection_metrics = ConnectivityMetrics(
    connection_id="conn-12345",
    source_element_id=vpc.get_full_identifier(),
    target_element_id=tgw.get_full_identifier(),
    connection_type="attachment"
)

connection_metrics.update_latency(23.5)
connection_metrics.update_bandwidth_utilization(0.65)

# Topology-wide metrics
topology_metrics = TopologyMetrics(
    topology_id=topology.topology_id,
    topology_name=topology.name,
    scope=topology.scope.value
)

topology_metrics.update_from_element_metrics([element_metrics])
topology_metrics.update_from_connection_metrics([connection_metrics])
```

Change Tracking:
```python
from awslabs.cloudwan_mcp_server.models.network import TopologySnapshot, TopologyDelta

# Create snapshot
snapshot = topology.create_snapshot("Before Maintenance")

# Track changes
delta = TopologyDelta(
    topology_id=topology.topology_id,
    from_version="1.0.0",
    to_version="1.1.0"
)

# Record element change
delta.add_element_change(
    ChangeOperation.UPDATE,
    vpc.get_full_identifier(),
    before={"health_status": "healthy"},
    after={"health_status": "warning"}
)
```

Health Assessment:
```python
from awslabs.cloudwan_mcp_server.models.network import NetworkHealth

# Comprehensive health assessment
health = NetworkHealth(
    topology_id=topology.topology_id
)

health.calculate_overall_health([element_metrics], [connection_metrics])
health.assess_business_impact()
health.generate_recommendations()

health_report = health.get_health_report()
```

Graph Operations:
```python
# Find shortest path between elements
path = topology.get_shortest_path(
    vpc.get_full_identifier(),
    tgw.get_full_identifier()
)

# Calculate centrality metrics
centrality = topology.calculate_centrality_metrics()

# Detect anomalies
anomalies = topology.detect_network_anomalies()

# Export topology
graphml_export = topology.export_topology(TopologyFormat.GRAPHML)
json_export = topology.export_topology(TopologyFormat.JSON)
```

Migration from Existing Components:
The network models are designed as drop-in replacements for existing topology
discovery components:

1. NetworkElement replaces existing element models with enhanced attributes
2. NetworkTopology provides unified topology representation
3. Specialized elements (VPCElement, etc.) replace component-specific models
4. NetworkMetrics consolidates performance monitoring
5. NetworkHealth provides comprehensive assessment

For detailed migration guides and API documentation, see the individual
component documentation and migration tools.
"""

from typing import Dict, List, Any, Tuple, Optional
import logging

logger = logging.getLogger(__name__)

# Core topology models
from .topology import (
    # Core classes
    NetworkTopology,
    NetworkElement, 
    NetworkConnection,
    TopologySnapshot,
    TopologyDelta,
    
    # Enums and supporting classes
    TopologyScope,
    TopologyFormat,
    ChangeOperation,
)

# Specialized element models  
from .elements import (
    # VPC elements
    VPCElement,
    VPCSecurityMode,
    
    # IP details
    IPDetailsResponse,
    
    # Transit Gateway elements
    TransitGatewayElement,
    TransitGatewayMode,
    
    # CloudWAN elements
    CloudWANElement,
    
    # Security elements
    SecurityElement,
    SecurityAssessment,
    
    # Network Function elements
    NetworkFunctionElement,
    NetworkFunctionType,
)

# Metrics and monitoring models
from .metrics import (
    # Core metrics classes
    NetworkMetrics,
    ConnectivityMetrics, 
    TopologyMetrics,
    NetworkHealth,
    
    # Data structures
    MetricDataPoint,
    TimeSeriesData,
    
    # Enums
    MetricType,
    MetricUnit,
    AggregationType,
    AlertSeverity,
)

# Import commonly used shared models for convenience
from ..shared.enums import (
    NetworkElementType,
    ConnectionType,
    AttachmentType,
    AttachmentState,
    HealthStatus,
    ValidationStatus,
    SecurityThreatLevel,
)

from ..shared.exceptions import (
    NetworkElementError,
    TopologyError,
    ValidationError,
    SecurityThreatError,
)

from ..shared.base import (
    TimestampMixin,
    EnhancedBaseResponse,
    EnhancedAWSResource,
    PerformanceMetrics,
)

# Import base models that are needed
from ..base import (
    BaseResponse,
    AWSResource,
    NetworkHop,
    InspectionPoint,
    AttachmentInfo,
    IPContext,
    RouteInfo,
    RouteTableInfo,
)

# Re-export models from the parent network.py module to resolve import conflicts
# When Python sees both network.py and network/ directory, the directory takes precedence
# So we need to explicitly import and re-export the models from network.py

try:
    # Import from the network.py module (now that the naming conflict is resolved)
    from .. import network as network_module
    
    # Re-export the models from network.py
    GlobalNetworksResponse = network_module.GlobalNetworksResponse
    GlobalNetworkInfo = network_module.GlobalNetworkInfo
    CoreNetworkInfo = network_module.CoreNetworkInfo
    VPCInfo = network_module.VPCInfo
    CoreNetworksResponse = network_module.CoreNetworksResponse
    VPCDiscoveryResponse = network_module.VPCDiscoveryResponse
    NetworkPathTraceResponse = network_module.NetworkPathTraceResponse
    TGWPeerAnalysisResponse = network_module.TGWPeerAnalysisResponse
    SegmentRoutesResponse = network_module.SegmentRoutesResponse
    IPDetailsResponse = network_module.IPDetailsResponse
    
    LEGACY_MODELS_AVAILABLE = True
    
except ImportError as e:
    # Fallback if import fails
    from ..base import BaseResponse
    
    class GlobalNetworksResponse(BaseResponse):
        def __init__(self, **data):
            super().__init__(**data)
            self.global_networks = data.get('global_networks', [])
            self.total_count = data.get('total_count', len(self.global_networks))
            self.regions_searched = data.get('regions_searched', [])
    
    class GlobalNetworkInfo:
        def __init__(self, **data):
            for key, value in data.items():
                setattr(self, key, value)
    
    class CoreNetworkInfo:
        def __init__(self, **data):
            for key, value in data.items():
                setattr(self, key, value)
    
    class VPCInfo:
        def __init__(self, **data):
            for key, value in data.items():
                setattr(self, key, value)
    
    class CoreNetworksResponse(BaseResponse):
        pass
    class VPCDiscoveryResponse(BaseResponse):
        pass
    class NetworkPathTraceResponse(BaseResponse):
        pass
    class TGWPeerAnalysisResponse(BaseResponse):
        pass
    class SegmentRoutesResponse(BaseResponse):
        pass
    class IPDetailsResponse(BaseResponse):
        pass
        
    LEGACY_MODELS_AVAILABLE = False

# Package metadata
__version__ = "1.0.0"
__author__ = "CloudWAN MCP Server - Network Topology Specialist"
__description__ = "Comprehensive network topology models with CloudWAN integration"

# Export groups for organized imports
CORE_TOPOLOGY_MODELS = [
    'NetworkTopology',
    'NetworkElement',
    'NetworkConnection', 
    'TopologySnapshot',
    'TopologyDelta',
    'TopologyScope',
    'TopologyFormat',
    'ChangeOperation',
]

SPECIALIZED_ELEMENT_MODELS = [
    'VPCElement',
    'VPCSecurityMode',
    'IPDetailsResponse',
    'TransitGatewayElement', 
    'TransitGatewayMode',
    'CloudWANElement',
    'SecurityElement',
    'SecurityAssessment',
    'NetworkFunctionElement',
    'NetworkFunctionType',
    'VPCInfo',  # Added to exports
    'CoreNetworkInfo',  # Added to exports
    'GlobalNetworkInfo',  # Added to exports
    'SecurityGroupInfo',  # Added to exports
    'SecurityGroupRule',  # Added to exports
    'TGWRouteOperationResponse',  # Added to exports
    'BlackholeRouteInfo',  # Added to exports
    'RouteOverlapInfo',   # Added to exports
    'CrossRegionRouteInfo', # Added to exports
    'RouteSummaryStats',   # Added to exports
    'TGWRouteAnalysisResponse', # Added to exports
    'TGWPeeringInfo',      # Added to exports
    'SegmentRouteInfo',    # Added to exports
    'TGWRouteTableInfo',   # Added to exports
]

METRICS_MODELS = [
    'NetworkMetrics',
    'ConnectivityMetrics',
    'TopologyMetrics', 
    'NetworkHealth',
    'MetricDataPoint',
    'TimeSeriesData',
    'MetricType',
    'MetricUnit',
    'AggregationType',
    'AlertSeverity',
]

SHARED_IMPORTS = [
    'NetworkElementType',
    'ConnectionType', 
    'AttachmentType',
    'AttachmentState',
    'HealthStatus',
    'ValidationStatus',
    'SecurityThreatLevel',
    'NetworkElementError',
    'TopologyError',
    'ValidationError',
    'SecurityThreatError',
    'TimestampMixin',
    'EnhancedBaseResponse',
    'EnhancedAWSResource',
    'PerformanceMetrics',
    'NetworkPathTraceResponse',
    'VPCDiscoveryResponse',
    'CoreNetworksResponse',
    'SegmentRoutesResponse',
    'TGWPeerAnalysisResponse',
    'GlobalNetworksResponse',
    'VPCInfo',  # Added to shared imports
    'CoreNetworkInfo',  # Added to shared imports
    'GlobalNetworkInfo',  # Added to shared imports
    'SecurityGroupInfo',  # Added to shared imports
    'SecurityGroupRule',  # Added to shared imports
    'TGWRouteOperationResponse',  # Added to shared imports
    'BlackholeRouteInfo',  # Added to shared imports
    'RouteOverlapInfo',   # Added to shared imports
    'CrossRegionRouteInfo', # Added to shared imports
    'RouteSummaryStats',   # Added to shared imports
    'TGWRouteAnalysisResponse', # Added to shared imports
    'TGWPeeringInfo',      # Added to shared imports
    'SegmentRouteInfo',    # Added to shared imports
    'TGWRouteTableInfo',   # Added to shared imports
    'NetworkHop',
    'InspectionPoint',
    'AttachmentInfo',
    'IPContext',
    'RouteInfo',
    'RouteTableInfo',
    'BaseResponse',
    'AWSResource',
]

# BGP Integration Models (NEW)
from .bgp_integration_manager import (
    BGPIntegrationManager,
    BGPTopologyAnalysisResult,
    BGPAnalysisScope,
    BGPTroubleshootingScenario,
    ASNHierarchyInfo,
    NetworkTopologyIntegration,
    NetworkElementCorrelation,
)

# BGP Analyzer Adapters (NEW)
from .bgp_analyzer_adapters import (
    BaseModelAdapter,
    CloudWANBGPAdapter,
    ProtocolBGPAdapter,
    OperationalBGPAdapter,
    SecurityBGPAdapter,
    BGPAnalyzerFactory,
    AnalyzerMigrationStatus,
)

# Network BGP Bridge (NEW)
from .network_bgp_bridge import (
    NetworkBGPAdapter,
    SynchronizationResult,
    SynchronizationConflict,
    SynchronizationConflictType,
)

# BGP Performance Optimizer (NEW)
from .bgp_performance_optimizer import (
    BGPPerformanceOptimizer,
    IntelligentCache,
    BatchProcessor,
    LazyLoader,
    CacheStrategy,
    OptimizationLevel,
    optimize_bgp_operation,
)

# BGP Integration Models group
BGP_INTEGRATION_MODELS = [
    'BGPIntegrationManager',
    'BGPTopologyAnalysisResult', 
    'BGPAnalysisScope',
    'BGPTroubleshootingScenario',
    'ASNHierarchyInfo',
    'NetworkTopologyIntegration',
    'NetworkElementCorrelation',
    'BaseModelAdapter',
    'CloudWANBGPAdapter', 
    'ProtocolBGPAdapter',
    'OperationalBGPAdapter',
    'SecurityBGPAdapter',
    'BGPAnalyzerFactory',
    'AnalyzerMigrationStatus',
    'NetworkBGPAdapter',
    'SynchronizationResult',
    'SynchronizationConflict',
    'SynchronizationConflictType',
    'BGPPerformanceOptimizer',
    'IntelligentCache',
    'BatchProcessor',
    'LazyLoader',
    'CacheStrategy',
    'OptimizationLevel',
    'optimize_bgp_operation',
]

# All public exports
__all__ = (
    CORE_TOPOLOGY_MODELS +
    SPECIALIZED_ELEMENT_MODELS +
    METRICS_MODELS +
    SHARED_IMPORTS +
    BGP_INTEGRATION_MODELS +
    ['CORE_TOPOLOGY_MODELS', 'SPECIALIZED_ELEMENT_MODELS', 'METRICS_MODELS', 'SHARED_IMPORTS', 'BGP_INTEGRATION_MODELS']
)


# Utility functions for common operations

def create_vpc_topology(vpc_id: str, region: str, cidr_block: str,
                       subnet_configs: List[Dict[str, Any]]) -> NetworkTopology:
    """
    Create a basic VPC topology with subnets.
    
    Args:
        vpc_id: VPC identifier
        region: AWS region
        cidr_block: VPC CIDR block
        subnet_configs: List of subnet configurations
        
    Returns:
        NetworkTopology with VPC and subnets
    """
    topology = NetworkTopology(
        name=f"VPC Topology - {vpc_id}",
        scope=TopologyScope.VPC_FOCUSED
    )
    
    # Create VPC element
    vpc = VPCElement(
        resource_id=vpc_id,
        resource_type="vpc",
        region=region,
        vpc_id=vpc_id,
        cidr_block=cidr_block,
        main_route_table_id=f"rtb-{vpc_id}",
        default_security_group_id=f"sg-{vpc_id}"
    )
    
    # Add subnets
    for subnet_config in subnet_configs:
        subnet_id = subnet_config["subnet_id"]
        is_public = subnet_config.get("is_public", False)
        vpc.add_subnet(subnet_id, is_public)
        
        # Add subnet as separate element
        subnet_element = NetworkElement(
            resource_id=subnet_id,
            resource_type="subnet",
            region=region,
            element_type=NetworkElementType.SUBNET,
            parent_element_id=vpc.get_full_identifier(),
            cidr_blocks=[subnet_config.get("cidr_block", "")]
        )
        topology.add_element(subnet_element)
    
    topology.add_element(vpc)
    return topology


def create_cloudwan_topology(global_network_id: str, core_network_id: str,
                           segments: List[Dict[str, Any]],
                           attachments: List[Dict[str, Any]]) -> NetworkTopology:
    """
    Create CloudWAN topology with core network and attachments.
    
    Args:
        global_network_id: Global Network ID
        core_network_id: Core Network ID
        segments: Segment configurations
        attachments: Attachment configurations
        
    Returns:
        NetworkTopology with CloudWAN components
    """
    topology = NetworkTopology(
        name=f"CloudWAN Topology - {core_network_id}",
        scope=TopologyScope.CORE_NETWORK
    )
    
    # Create Core Network element
    core_network = CloudWANElement(
        resource_id=core_network_id,
        resource_type="core_network",
        region="global",
        element_type=NetworkElementType.CORE_NETWORK,
        cloudwan_element_type="core_network",
        global_network_id=global_network_id
    )
    
    # Add segments
    for segment in segments:
        core_network.add_segment(segment["name"], segment)
        
        # Create segment element
        segment_element = NetworkElement(
            resource_id=f"segment-{segment['name']}",
            resource_type="segment", 
            region="global",
            element_type=NetworkElementType.SEGMENT,
            segment_name=segment["name"],
            core_network_id=core_network_id,
            parent_element_id=core_network.get_full_identifier()
        )
        topology.add_element(segment_element)
    
    # Add attachments
    for attachment in attachments:
        core_network.add_attachment(attachment["attachment_id"], attachment)
        
        # Create attachment element
        attachment_element = NetworkElement(
            resource_id=attachment["attachment_id"],
            resource_type="attachment",
            region=attachment.get("region", "us-east-1"),
            element_type=NetworkElementType.ATTACHMENT,
            attachment_id=attachment["attachment_id"],
            segment_name=attachment.get("segment_name"),
            core_network_id=core_network_id,
            parent_element_id=core_network.get_full_identifier()
        )
        topology.add_element(attachment_element)
    
    topology.add_element(core_network)
    return topology


def create_monitoring_dashboard_topology(topology: NetworkTopology) -> Dict[str, Any]:
    """
    Create monitoring dashboard data from topology.
    
    Args:
        topology: Network topology to monitor
        
    Returns:
        Dashboard configuration dict
    """
    dashboard = {
        "topology_id": topology.topology_id,
        "name": f"Monitoring - {topology.name}",
        "widgets": [],
        "alerts": [],
        "metrics": []
    }
    
    # Add topology health widget
    dashboard["widgets"].append({
        "type": "health_overview",
        "title": "Topology Health",
        "config": {
            "topology_id": topology.topology_id,
            "metrics": ["overall_health_score", "element_count", "connection_count"]
        }
    })
    
    # Add per-element health widgets
    for element_id, element in topology.elements.items():
        if element.element_type.is_cloudwan_element():
            dashboard["widgets"].append({
                "type": "element_health",
                "title": f"{element.name or element_id} Health",
                "config": {
                    "element_id": element_id,
                    "element_type": element.element_type.value,
                    "metrics": ["health_status", "utilization", "performance_score"]
                }
            })
    
    # Add connection quality widgets
    for connection_id, connection in topology.connections.items():
        if connection.connection_type in (ConnectionType.BGP_SESSION, ConnectionType.ATTACHMENT):
            dashboard["widgets"].append({
                "type": "connection_quality",
                "title": f"Connection {connection_id} Quality",
                "config": {
                    "connection_id": connection_id,
                    "metrics": ["latency", "packet_loss", "quality_score"]
                }
            })
    
    return dashboard


def validate_topology_consistency(topology: NetworkTopology) -> Tuple[bool, List[str]]:
    """
    Validate topology for consistency and completeness.
    
    Args:
        topology: Topology to validate
        
    Returns:
        Tuple of (is_valid, error_messages)
    """
    errors = []
    
    # Check element-connection consistency
    element_ids = set(topology.elements.keys())
    for connection in topology.connections.values():
        if connection.source_element_id not in element_ids:
            errors.append(f"Connection {connection.connection_id} references missing source element {connection.source_element_id}")
        if connection.target_element_id not in element_ids:
            errors.append(f"Connection {connection.connection_id} references missing target element {connection.target_element_id}")
    
    # Check parent-child relationships
    for element_id, element in topology.elements.items():
        if element.parent_element_id and element.parent_element_id not in element_ids:
            errors.append(f"Element {element_id} references missing parent {element.parent_element_id}")
        
        for child_id in element.child_element_ids:
            if child_id not in element_ids:
                errors.append(f"Element {element_id} references missing child {child_id}")
    
    # Check CloudWAN consistency
    for element in topology.elements.values():
        if element.is_cloudwan_element():
            if element.core_network_id and element.core_network_id not in [e.resource_id for e in topology.elements.values()]:
                errors.append(f"Element {element.get_full_identifier()} references unknown core network {element.core_network_id}")
    
    # Check regional consistency
    regional_elements = {}
    for element in topology.elements.values():
        if element.region not in regional_elements:
            regional_elements[element.region] = []
        regional_elements[element.region].append(element)
    
    # Validate cross-region connections have appropriate elements
    for connection in topology.connections.values():
        source_element = topology.elements.get(connection.source_element_id)
        target_element = topology.elements.get(connection.target_element_id)
        
        if source_element and target_element:
            if (source_element.region != target_element.region and 
                connection.connection_type not in (ConnectionType.CROSS_REGION, ConnectionType.PEERING)):
                errors.append(f"Cross-region connection {connection.connection_id} should use cross-region connection type")
    
    return len(errors) == 0, errors


# Model validation and compatibility functions
def get_model_compatibility_info() -> Dict[str, Any]:
    """Get model compatibility information for migrations."""
    return {
        "version": __version__,
        "compatible_with": {
            "existing_topology_discovery": "1.x",
            "network_topology_visualizer": "1.x", 
            "bgp_domain_models": "1.x",
            "shared_infrastructure": "1.x"
        },
        "migration_mappings": {
            # Legacy model -> New model mappings
            "NetworkElement": "NetworkElement",
            "NetworkConnection": "NetworkConnection", 
            "NetworkTopology": "NetworkTopology",
            "VPCInfo": "VPCElement",
            "TGWInfo": "TransitGatewayElement",
            "CoreNetworkInfo": "CloudWANElement"
        },
        "breaking_changes": [
            "NetworkElementType enum moved to shared.enums",
            "ConnectionType enum moved to shared.enums", 
            "Health status now uses HealthStatus enum from shared.enums",
            "Metrics moved to separate NetworkMetrics class"
        ],
        "new_features": [
            "Specialized element models (VPCElement, etc.)",
            "Comprehensive metrics and health monitoring",
            "Change tracking with snapshots and deltas",
            "Graph-based topology operations",
            "Business impact assessment",
            "Multi-format topology export"
        ]
    }


def validate_model_installation() -> bool:
    """Validate that all network models are properly installed and importable."""
    try:
        # Test core topology models
        topology = NetworkTopology(name="test")
        element = NetworkElement(
            resource_id="test",
            resource_type="test",
            region="us-east-1",
            element_type=NetworkElementType.VPC
        )
        connection = NetworkConnection(
            source_element_id="test1",
            target_element_id="test2", 
            connection_type=ConnectionType.ATTACHMENT
        )
        
        # Test specialized elements
        vpc = VPCElement(
            resource_id="vpc-test",
            resource_type="vpc",
            region="us-east-1",
            element_id="vpc-test",
            element_type="vpc",
            cidr_blocks=["10.0.0.0/16"],
            state="available",
            vpc_id="vpc-test",
            cidr_block="10.0.0.0/16",
            main_route_table_id="rtb-test",
            default_security_group_id="sg-test"
        )
        
        # Test metrics
        metrics = NetworkMetrics(
            element_id="test",
            element_type="vpc",
            region="us-east-1"
        )
        
        # Test health assessment
        health = NetworkHealth(topology_id="test")
        
        return True
        
    except Exception as e:
        logger.error(f"Model validation failed: {e}")
        return False