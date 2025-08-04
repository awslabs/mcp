"""
Network BGP Bridge for CloudWAN MCP Server.

This module implements the bridge between NetworkTopology and BGP models,
providing seamless integration and bidirectional data synchronization.
Based on the DeepSeek R1 architectural design for unified network intelligence.

Key Features:
- Bidirectional synchronization between BGP and network topology
- ASN relationship integration with network elements
- BGP session state correlation with element health
- Network connection creation from BGP peer relationships
- Performance optimization for large-scale topologies
- Troubleshooting workflow support

Integration Points:
- NetworkTopology ↔ BGPTopologyModel
- NetworkElement ↔ BGPPeerModel
- NetworkConnection ↔ BGP peer relationships
- HealthStatus ↔ BGP session states
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum


from .topology import NetworkTopology, NetworkElement, NetworkConnection
from .bgp_topology import BGPTopologyModel, BGPPeerModel
from ..shared.base import PerformanceMetrics
from ..shared.enums import (
    ConnectionType, HealthStatus, BGPPeerState
)

logger = logging.getLogger(__name__)


class SynchronizationConflictType(str, Enum):
    """Types of synchronization conflicts between BGP and network topology."""
    ASN_MISMATCH = "asn_mismatch"
    PEER_STATE_CONFLICT = "peer_state_conflict"
    ELEMENT_NOT_FOUND = "element_not_found"
    DUPLICATE_MAPPING = "duplicate_mapping"
    HEALTH_STATUS_CONFLICT = "health_status_conflict"
    REGIONAL_INCONSISTENCY = "regional_inconsistency"


@dataclass
class SynchronizationConflict:
    """Synchronization conflict between BGP and network topology data."""
    conflict_type: SynchronizationConflictType
    bgp_data: Dict[str, Any]
    network_data: Dict[str, Any]
    severity: str  # low, medium, high, critical
    resolution_suggestion: str
    auto_resolvable: bool = False


@dataclass
class SynchronizationResult:
    """Result of BGP-Network topology synchronization."""
    success: bool
    elements_synced: int
    connections_created: int
    conflicts: List[SynchronizationConflict] = field(default_factory=list)
    performance_metrics: Dict[str, float] = field(default_factory=dict)
    sync_duration: float = 0.0


class NetworkBGPAdapter:
    """
    Bridge adapter for seamless integration between NetworkTopology and BGP models.
    
    Provides bidirectional synchronization, conflict resolution, and unified
    network intelligence for comprehensive troubleshooting workflows.
    """
    
    def __init__(self, network_topology: NetworkTopology, bgp_topology: BGPTopologyModel):
        """
        Initialize Network BGP Bridge.
        
        Args:
            network_topology: Network topology instance
            bgp_topology: BGP topology instance
        """
        self.network_topology = network_topology
        self.bgp_topology = bgp_topology
        self.performance_metrics = PerformanceMetrics()
        self.sync_conflicts: List[SynchronizationConflict] = []
        
        # Mapping caches for performance optimization
        self._asn_element_map: Dict[int, str] = {}  # ASN -> NetworkElement ID
        self._peer_element_map: Dict[str, str] = {}  # BGP Peer ID -> NetworkElement ID
        self._element_peer_map: Dict[str, str] = {}  # NetworkElement ID -> BGP Peer ID
        
        # Synchronization metadata
        self.last_sync_time: Optional[datetime] = None
        self.sync_generation = 0
        
        logger.info(
            f"NetworkBGPAdapter initialized for topology {network_topology.topology_id} "
            f"and BGP topology {bgp_topology.topology_id}"
        )
    
    async def sync_asn_relationships(self, force_refresh: bool = False) -> SynchronizationResult:
        """
        Synchronize ASN relationships between BGP topology and network elements.
        
        Args:
            force_refresh: Force refresh of mapping caches
            
        Returns:
            Synchronization result with metrics and conflicts
        """
        start_time = datetime.now(timezone.utc)
        logger.info("Starting ASN relationship synchronization")
        
        if force_refresh:
            self._asn_element_map.clear()
        
        sync_result = SynchronizationResult(success=False, elements_synced=0, connections_created=0)
        
        try:
            # Sync from BGP to Network Topology
            await self._sync_bgp_asns_to_network_elements(sync_result)
            
            # Sync from Network Topology to BGP
            await self._sync_network_asns_to_bgp_topology(sync_result)
            
            # Validate ASN consistency
            await self._validate_asn_consistency(sync_result)
            
            sync_result.success = len([c for c in sync_result.conflicts if c.severity == 'critical']) == 0
            
        except Exception as e:
            logger.error(f"ASN relationship synchronization failed: {e}")
            sync_result.success = False
        finally:
            sync_duration = (datetime.now(timezone.utc) - start_time).total_seconds()
            sync_result.sync_duration = sync_duration
            self.performance_metrics.add_measurement("asn_sync_time", sync_duration)
        
        logger.info(
            f"ASN synchronization completed: {sync_result.elements_synced} elements, "
            f"{len(sync_result.conflicts)} conflicts"
        )
        
        return sync_result
    
    async def update_element_bgp_connectivity(
        self, 
        element: NetworkElement, 
        bgp_peers: List[BGPPeerModel]
    ) -> None:
        """
        Update network element with BGP connectivity information.
        
        Args:
            element: Network element to update
            bgp_peers: BGP peers associated with the element
        """
        logger.debug(f"Updating BGP connectivity for element {element.get_full_identifier()}")
        
        # Update element with BGP-specific attributes
        bgp_connectivity_info = {
            'bgp_enabled': len(bgp_peers) > 0,
            'bgp_peer_count': len(bgp_peers),
            'bgp_asns': list(set(peer.peer_asn for peer in bgp_peers)),
            'bgp_session_states': {
                peer.peer_id: peer.peer_state.value 
                for peer in bgp_peers
            },
            'bgp_last_updated': datetime.now(timezone.utc).isoformat()
        }
        
        # Add BGP connectivity to element metadata
        if not hasattr(element, 'bgp_connectivity'):
            element.bgp_connectivity = {}
        element.bgp_connectivity.update(bgp_connectivity_info)
        
        # Correlate BGP session health with element health
        await self._correlate_bgp_health_with_element_health(element, bgp_peers)
        
        # Update peer-element mapping
        for peer in bgp_peers:
            self._peer_element_map[peer.peer_id] = element.get_full_identifier()
            self._element_peer_map[element.get_full_identifier()] = peer.peer_id
    
    async def create_bgp_network_connections(
        self, 
        bgp_topology: BGPTopologyModel
    ) -> List[NetworkConnection]:
        """
        Create network connections from BGP peer relationships.
        
        Args:
            bgp_topology: BGP topology model
            
        Returns:
            List of created network connections
        """
        logger.info("Creating network connections from BGP peer relationships")
        
        connections = []
        
        # Create connections for each BGP peer relationship
        for peer in bgp_topology.peers.values():
            connection = await self._create_connection_from_bgp_peer(peer)
            if connection:
                connections.append(connection)
                
                # Add connection to network topology
                self.network_topology.add_connection(connection)
        
        logger.info(f"Created {len(connections)} network connections from BGP peers")
        return connections
    
    async def correlate_session_states_with_element_health(self) -> Dict[str, Any]:
        """
        Correlate BGP session states with network element health status.
        
        Returns:
            Correlation analysis results
        """
        logger.info("Correlating BGP session states with element health")
        
        correlation_results = {
            'total_correlations': 0,
            'healthy_correlations': 0,
            'degraded_correlations': 0,
            'critical_correlations': 0,
            'correlation_accuracy': 0.0,
            'recommendations': []
        }
        
        for peer_id, element_id in self._peer_element_map.items():
            if element_id in self.network_topology.elements:
                element = self.network_topology.elements[element_id]
                peer = self.bgp_topology.peers.get(peer_id)
                
                if peer:
                    correlation = await self._analyze_peer_element_correlation(peer, element)
                    correlation_results['total_correlations'] += 1
                    
                    # Categorize correlation
                    if correlation['health_alignment'] == 'healthy':
                        correlation_results['healthy_correlations'] += 1
                    elif correlation['health_alignment'] == 'degraded':
                        correlation_results['degraded_correlations'] += 1
                    else:
                        correlation_results['critical_correlations'] += 1
                    
                    # Generate recommendations if needed
                    if correlation['needs_attention']:
                        correlation_results['recommendations'].append({
                            'element_id': element_id,
                            'peer_id': peer_id,
                            'issue': correlation['issue'],
                            'recommendation': correlation['recommendation']
                        })
        
        # Calculate correlation accuracy
        if correlation_results['total_correlations'] > 0:
            correlation_results['correlation_accuracy'] = (
                correlation_results['healthy_correlations'] / 
                correlation_results['total_correlations']
            )
        
        return correlation_results
    
    async def detect_topology_inconsistencies(self) -> List[Dict[str, Any]]:
        """
        Detect inconsistencies between BGP topology and network topology.
        
        Returns:
            List of detected inconsistencies
        """
        logger.info("Detecting topology inconsistencies")
        
        inconsistencies = []
        
        # Check for orphaned BGP peers (peers without corresponding network elements)
        orphaned_peers = await self._find_orphaned_bgp_peers()
        inconsistencies.extend([
            {
                'type': 'orphaned_bgp_peer',
                'peer_id': peer_id,
                'severity': 'medium',
                'description': f"BGP peer {peer_id} has no corresponding network element"
            }
            for peer_id in orphaned_peers
        ])
        
        # Check for network elements with ASNs but no BGP peers
        orphaned_elements = await self._find_orphaned_network_elements()
        inconsistencies.extend([
            {
                'type': 'orphaned_network_element',
                'element_id': element_id,
                'severity': 'low',
                'description': f"Network element {element_id} has ASN but no BGP peers"
            }
            for element_id in orphaned_elements
        ])
        
        # Check for ASN conflicts
        asn_conflicts = await self._find_asn_conflicts()
        inconsistencies.extend([
            {
                'type': 'asn_conflict',
                'asn': asn,
                'conflicting_elements': elements,
                'severity': 'high',
                'description': f"ASN {asn} assigned to multiple elements: {elements}"
            }
            for asn, elements in asn_conflicts.items()
        ])
        
        # Check for regional inconsistencies
        regional_inconsistencies = await self._find_regional_inconsistencies()
        inconsistencies.extend(regional_inconsistencies)
        
        logger.info(f"Found {len(inconsistencies)} topology inconsistencies")
        return inconsistencies
    
    async def optimize_integration_performance(self) -> Dict[str, Any]:
        """
        Optimize performance of BGP-Network topology integration.
        
        Returns:
            Optimization results and recommendations
        """
        logger.info("Optimizing integration performance")
        
        optimization_results = {
            'cache_efficiency': await self._analyze_cache_efficiency(),
            'synchronization_performance': await self._analyze_sync_performance(),
            'memory_usage': await self._analyze_memory_usage(),
            'recommendations': []
        }
        
        # Generate optimization recommendations
        if optimization_results['cache_efficiency'] < 0.8:
            optimization_results['recommendations'].append({
                'type': 'cache_optimization',
                'priority': 'high',
                'description': 'Consider increasing cache sizes for mapping tables'
            })
        
        if optimization_results['synchronization_performance'] > 5.0:  # seconds
            optimization_results['recommendations'].append({
                'type': 'sync_optimization',
                'priority': 'medium',
                'description': 'Consider implementing incremental synchronization'
            })
        
        return optimization_results
    
    # Private helper methods
    
    async def _sync_bgp_asns_to_network_elements(self, sync_result: SynchronizationResult) -> None:
        """Sync BGP ASN data to network elements."""
        for peer in self.bgp_topology.peers.values():
            # Find corresponding network element
            element_id = await self._find_network_element_for_peer(peer)
            
            if element_id and element_id in self.network_topology.elements:
                element = self.network_topology.elements[element_id]
                
                # Update element with BGP ASN information
                if not hasattr(element, 'autonomous_systems'):
                    element.autonomous_systems = set()
                
                element.autonomous_systems.add(peer.peer_asn)
                self._asn_element_map[peer.peer_asn] = element_id
                sync_result.elements_synced += 1
            else:
                # Create conflict for orphaned peer
                conflict = SynchronizationConflict(
                    conflict_type=SynchronizationConflictType.ELEMENT_NOT_FOUND,
                    bgp_data={'peer_id': peer.peer_id, 'asn': peer.peer_asn},
                    network_data={},
                    severity='medium',
                    resolution_suggestion='Create network element for BGP peer',
                    auto_resolvable=True
                )
                sync_result.conflicts.append(conflict)
    
    async def _sync_network_asns_to_bgp_topology(self, sync_result: SynchronizationResult) -> None:
        """Sync network topology ASN data to BGP topology."""
        for element in self.network_topology.elements.values():
            if hasattr(element, 'autonomous_systems') and element.autonomous_systems:
                for asn in element.autonomous_systems:
                    if asn not in [peer.peer_asn for peer in self.bgp_topology.peers.values()]:
                        # ASN in network topology but no corresponding BGP peer
                        conflict = SynchronizationConflict(
                            conflict_type=SynchronizationConflictType.ASN_MISMATCH,
                            bgp_data={},
                            network_data={'element_id': element.get_full_identifier(), 'asn': asn},
                            severity='low',
                            resolution_suggestion='Consider adding BGP peer for network element ASN',
                            auto_resolvable=False
                        )
                        sync_result.conflicts.append(conflict)
    
    async def _validate_asn_consistency(self, sync_result: SynchronizationResult) -> None:
        """Validate ASN consistency across both topologies."""
        # Check for ASN conflicts (same ASN mapped to multiple elements)
        asn_element_count = defaultdict(list)
        
        for asn, element_id in self._asn_element_map.items():
            asn_element_count[asn].append(element_id)
        
        for asn, element_ids in asn_element_count.items():
            if len(element_ids) > 1:
                conflict = SynchronizationConflict(
                    conflict_type=SynchronizationConflictType.DUPLICATE_MAPPING,
                    bgp_data={'asn': asn},
                    network_data={'element_ids': element_ids},
                    severity='high',
                    resolution_suggestion='Resolve duplicate ASN assignments',
                    auto_resolvable=False
                )
                sync_result.conflicts.append(conflict)
    
    async def _correlate_bgp_health_with_element_health(
        self, 
        element: NetworkElement, 
        bgp_peers: List[BGPPeerModel]
    ) -> None:
        """Correlate BGP session health with element health status."""
        # Count healthy vs unhealthy BGP sessions
        healthy_sessions = sum(1 for peer in bgp_peers if peer.peer_state == BGPPeerState.ESTABLISHED)
        total_sessions = len(bgp_peers)
        
        if total_sessions > 0:
            health_ratio = healthy_sessions / total_sessions
            
            # Update element health based on BGP session health
            if health_ratio >= 0.8:
                bgp_health_status = HealthStatus.HEALTHY
            elif health_ratio >= 0.5:
                bgp_health_status = HealthStatus.DEGRADED
            else:
                bgp_health_status = HealthStatus.UNHEALTHY
            
            # Store BGP-specific health information
            if not hasattr(element, 'health_contributors'):
                element.health_contributors = {}
            
            element.health_contributors['bgp'] = {
                'status': bgp_health_status.value,
                'healthy_sessions': healthy_sessions,
                'total_sessions': total_sessions,
                'last_updated': datetime.now(timezone.utc).isoformat()
            }
    
    async def _create_connection_from_bgp_peer(self, peer: BGPPeerModel) -> Optional[NetworkConnection]:
        """Create network connection from BGP peer relationship."""
        try:
            # Find source and target elements
            source_element_id = self._peer_element_map.get(peer.peer_id)
            
            if not source_element_id:
                return None
            
            # Create connection
            connection = NetworkConnection(
                source_element_id=source_element_id,
                target_element_id=f"external-asn-{peer.peer_asn}",
                connection_type=ConnectionType.BGP_SESSION,
                connection_id=f"bgp-{peer.peer_id}",
                attributes={
                    'bgp_peer_id': peer.peer_id,
                    'peer_asn': peer.peer_asn,
                    'local_asn': peer.local_asn,
                    'session_state': peer.peer_state.value,
                    'address_families': peer.address_families
                }
            )
            
            return connection
            
        except Exception as e:
            logger.error(f"Failed to create connection from BGP peer {peer.peer_id}: {e}")
            return None
    
    async def _find_network_element_for_peer(self, peer: BGPPeerModel) -> Optional[str]:
        """Find network element corresponding to BGP peer."""
        # Try multiple strategies to find corresponding element
        
        # Strategy 1: Direct IP matching
        for element in self.network_topology.elements.values():
            if hasattr(element, 'ip_addresses') and peer.peer_ip in element.ip_addresses:
                return element.get_full_identifier()
        
        # Strategy 2: Regional and ASN matching
        for element in self.network_topology.elements.values():
            if (element.region == peer.region and 
                hasattr(element, 'autonomous_systems') and 
                peer.local_asn in element.autonomous_systems):
                return element.get_full_identifier()
        
        # Strategy 3: Check existing mappings
        return self._peer_element_map.get(peer.peer_id)
    
    async def _analyze_peer_element_correlation(
        self, 
        peer: BGPPeerModel, 
        element: NetworkElement
    ) -> Dict[str, Any]:
        """Analyze correlation between BGP peer and network element."""
        correlation = {
            'health_alignment': 'unknown',
            'needs_attention': False,
            'issue': None,
            'recommendation': None
        }
        
        # Check health alignment
        peer_healthy = peer.peer_state == BGPPeerState.ESTABLISHED
        element_healthy = element.health_status == HealthStatus.HEALTHY
        
        if peer_healthy and element_healthy:
            correlation['health_alignment'] = 'healthy'
        elif not peer_healthy and not element_healthy:
            correlation['health_alignment'] = 'degraded'
        else:
            correlation['health_alignment'] = 'critical'
            correlation['needs_attention'] = True
            correlation['issue'] = 'Health status mismatch between BGP peer and network element'
            correlation['recommendation'] = 'Investigate discrepancy in health status'
        
        return correlation
    
    async def _find_orphaned_bgp_peers(self) -> List[str]:
        """Find BGP peers without corresponding network elements."""
        orphaned = []
        
        for peer_id in self.bgp_topology.peers.keys():
            if peer_id not in self._peer_element_map:
                orphaned.append(peer_id)
        
        return orphaned
    
    async def _find_orphaned_network_elements(self) -> List[str]:
        """Find network elements with ASNs but no BGP peers."""
        orphaned = []
        
        for element in self.network_topology.elements.values():
            if (hasattr(element, 'autonomous_systems') and 
                element.autonomous_systems and
                element.get_full_identifier() not in self._element_peer_map):
                orphaned.append(element.get_full_identifier())
        
        return orphaned
    
    async def _find_asn_conflicts(self) -> Dict[int, List[str]]:
        """Find ASN conflicts (same ASN assigned to multiple elements)."""
        asn_conflicts = defaultdict(list)
        
        for asn, element_id in self._asn_element_map.items():
            asn_conflicts[asn].append(element_id)
        
        # Only return conflicts (ASNs with multiple elements)
        return {asn: elements for asn, elements in asn_conflicts.items() if len(elements) > 1}
    
    async def _find_regional_inconsistencies(self) -> List[Dict[str, Any]]:
        """Find regional inconsistencies between BGP peers and network elements."""
        inconsistencies = []
        
        for peer_id, element_id in self._peer_element_map.items():
            peer = self.bgp_topology.peers.get(peer_id)
            element = self.network_topology.elements.get(element_id)
            
            if peer and element and peer.region != element.region:
                inconsistencies.append({
                    'type': 'regional_mismatch',
                    'peer_id': peer_id,
                    'element_id': element_id,
                    'peer_region': peer.region,
                    'element_region': element.region,
                    'severity': 'medium',
                    'description': f"Region mismatch: BGP peer in {peer.region}, element in {element.region}"
                })
        
        return inconsistencies
    
    async def _analyze_cache_efficiency(self) -> float:
        """Analyze cache efficiency for mapping tables."""
        # Simplified cache efficiency calculation
        total_lookups = len(self._asn_element_map) + len(self._peer_element_map)
        if total_lookups == 0:
            return 1.0
        
        # In a real implementation, this would track cache hits vs misses
        return 0.85  # Placeholder
    
    async def _analyze_sync_performance(self) -> float:
        """Analyze synchronization performance."""
        # Return average sync time from performance metrics
        sync_times = self.performance_metrics.get_measurements('asn_sync_time')
        if sync_times:
            return sum(sync_times) / len(sync_times)
        return 0.0
    
    async def _analyze_memory_usage(self) -> Dict[str, Any]:
        """Analyze memory usage of mapping caches."""
        import sys
        
        return {
            'asn_map_size': sys.getsizeof(self._asn_element_map),
            'peer_map_size': sys.getsizeof(self._peer_element_map),
            'total_cache_size': (
                sys.getsizeof(self._asn_element_map) + 
                sys.getsizeof(self._peer_element_map) +
                sys.getsizeof(self._element_peer_map)
            )
        }