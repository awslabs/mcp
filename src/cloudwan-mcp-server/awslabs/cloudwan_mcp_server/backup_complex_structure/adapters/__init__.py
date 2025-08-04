"""
Network Domain Adapters for CloudWAN MCP Server.

This module provides adapter classes for integrating different network domains
including topology, BGP, security, and operations for comprehensive cross-domain
intelligence sharing and analysis.

Key Features:
- BGP-Topology integration for route-topology correlation
- Security threat propagation across network domains
- Performance-optimized cross-domain data synchronization
- Backward compatibility preservation during migration
"""

from .topology_bgp_integration import (
    TopologyBGPIntegrationAdapter,
    BGPTopologyCorrelator,
    TopologyBGPSynchronizer
)
from .network_intelligence_bridge import (
    NetworkIntelligenceBridge,
    CrossDomainIntelligenceEngine,
    NetworkAnomalyDetector
)

__all__ = [
    'TopologyBGPIntegrationAdapter',
    'BGPTopologyCorrelator', 
    'TopologyBGPSynchronizer',
    'NetworkIntelligenceBridge',
    'CrossDomainIntelligenceEngine',
    'NetworkAnomalyDetector',
]