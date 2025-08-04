"""
BGP-Topology Integration Adapter for CloudWAN MCP Server.

This module provides comprehensive integration between BGP routing data and network
topology information, enabling cross-domain intelligence sharing and enhanced
network analysis capabilities.

Key Features:
- Bidirectional BGP-topology data correlation
- Real-time peer state synchronization 
- Route path topology mapping
- Security threat context propagation
- Performance-optimized integration patterns
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set
from dataclasses import dataclass, field
from collections import defaultdict
import ipaddress
from concurrent.futures import ThreadPoolExecutor


from ..models.network.topology import (
    NetworkTopology, NetworkConnection
)
from ..models.bgp.peer import BGPPeerInfo
from ..models.bgp.route import BGPRouteInfo
from ..models.shared.enums import (
    NetworkElementType, BGPPeerState, HealthStatus, ConnectionType
)
from ..models.shared.exceptions import BGPAnalysisError

logger = logging.getLogger(__name__)


@dataclass
class BGPTopologyCorrelation:
    """Correlation data between BGP peers and topology elements."""
    
    peer_id: str
    element_id: str
    correlation_type: str  # 'direct', 'attached', 'routed', 'inferred'
    confidence_score: float  # 0.0-1.0
    correlation_metadata: Dict[str, Any] = field(default_factory=dict)
    last_verified: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def is_high_confidence(self) -> bool:
        """Check if correlation has high confidence."""
        return self.confidence_score >= 0.8
    
    def is_direct_correlation(self) -> bool:
        """Check if this is a direct correlation."""
        return self.correlation_type == 'direct'


class TopologyBGPIntegrationAdapter:
    """
    Core adapter for integrating BGP routing data with network topology.
    
    Provides bidirectional integration capabilities with performance optimization
    and comprehensive correlation algorithms.
    """
    
    def __init__(self, 
                 cache_ttl_seconds: int = 300,
                 max_concurrent_operations: int = 10,
                 correlation_confidence_threshold: float = 0.7):
        self.cache_ttl_seconds = cache_ttl_seconds
        self.max_concurrent_operations = max_concurrent_operations
        self.correlation_threshold = correlation_confidence_threshold
        
        # Caching and performance
        self._correlation_cache: Dict[str, BGPTopologyCorrelation] = {}
        self._cache_timestamps: Dict[str, datetime] = {}
        self._executor = ThreadPoolExecutor(max_workers=max_concurrent_operations)
        
        # Metrics
        self._correlation_attempts = 0
        self._successful_correlations = 0
        self._cache_hits = 0
        self._cache_misses = 0
        
        logger.info("Initialized TopologyBGPIntegrationAdapter")
    
    async def correlate_peer_with_topology(
        self, 
        peer: BGPPeerInfo, 
        topology: NetworkTopology,
        force_refresh: bool = False
    ) -> Optional[BGPTopologyCorrelation]:
        """
        Find and correlate BGP peer with corresponding topology element.
        
        Args:
            peer: BGP peer to correlate
            topology: Network topology to search
            force_refresh: Skip cache and force fresh correlation
            
        Returns:
            Correlation object if successful, None otherwise
        """
        correlation_key = f"{peer.peer_id}:{topology.topology_id}"
        
        # Check cache first (unless forced refresh)
        if not force_refresh:
            cached_correlation = self._get_cached_correlation(correlation_key)
            if cached_correlation:
                self._cache_hits += 1
                return cached_correlation
        
        self._cache_misses += 1
        self._correlation_attempts += 1
        
        try:
            # Attempt multiple correlation strategies
            correlation = await self._perform_correlation(peer, topology)
            
            if correlation and correlation.confidence_score >= self.correlation_threshold:
                self._cache_correlation(correlation_key, correlation)
                self._successful_correlations += 1
                logger.debug(f"Successfully correlated peer {peer.peer_id} with element "
                           f"{correlation.element_id} (confidence: {correlation.confidence_score})")
                return correlation
            else:
                logger.debug(f"Failed to find high-confidence correlation for peer {peer.peer_id}")
                return None
                
        except Exception as e:
            logger.error(f"Error correlating peer {peer.peer_id}: {e}")
            return None
    
    async def _perform_correlation(
        self, peer: BGPPeerInfo, topology: NetworkTopology
    ) -> Optional[BGPTopologyCorrelation]:
        """Perform the actual correlation using multiple strategies."""
        
        # Strategy 1: Direct IP address matching
        direct_correlation = await self._correlate_by_ip_address(peer, topology)
        if direct_correlation and direct_correlation.confidence_score >= 0.9:
            return direct_correlation
        
        # Strategy 2: CloudWAN attachment correlation
        cloudwan_correlation = await self._correlate_by_cloudwan_attachment(peer, topology)
        if cloudwan_correlation and cloudwan_correlation.confidence_score >= 0.8:
            return cloudwan_correlation
        
        # Strategy 3: Transit Gateway correlation
        tgw_correlation = await self._correlate_by_transit_gateway(peer, topology)
        if tgw_correlation and tgw_correlation.confidence_score >= 0.7:
            return tgw_correlation
        
        # Strategy 4: Network neighborhood analysis
        neighborhood_correlation = await self._correlate_by_network_neighborhood(peer, topology)
        if neighborhood_correlation and neighborhood_correlation.confidence_score >= 0.6:
            return neighborhood_correlation
        
        # Return the best correlation found, even if below threshold
        return max([
            direct_correlation, cloudwan_correlation, tgw_correlation, neighborhood_correlation
        ], key=lambda x: x.confidence_score if x else 0, default=None)
    
    async def _correlate_by_ip_address(
        self, peer: BGPPeerInfo, topology: NetworkTopology
    ) -> Optional[BGPTopologyCorrelation]:
        """Correlate peer by direct IP address matching."""
        
        if not peer.peer_ip:
            return None
        
        try:
            peer_ip = ipaddress.ip_address(peer.peer_ip)
        except ValueError:
            return None
        
        # Search for elements with matching IP addresses
        for element_id, element in topology.elements.items():
            if peer_ip.exploded in element.ip_addresses:
                return BGPTopologyCorrelation(
                    peer_id=peer.peer_id,
                    element_id=element_id,
                    correlation_type='direct',
                    confidence_score=0.95,
                    correlation_metadata={
                        'method': 'ip_address_match',
                        'matched_ip': peer_ip.exploded,
                        'element_type': element.element_type.value
                    }
                )
            
            # Check if peer IP is in element's CIDR blocks
            for cidr_block in element.cidr_blocks:
                try:
                    network = ipaddress.ip_network(cidr_block, strict=False)
                    if peer_ip in network:
                        return BGPTopologyCorrelation(
                            peer_id=peer.peer_id,
                            element_id=element_id,
                            correlation_type='attached',
                            confidence_score=0.85,
                            correlation_metadata={
                                'method': 'cidr_block_match',
                                'matched_cidr': cidr_block,
                                'peer_ip': peer_ip.exploded
                            }
                        )
                except ValueError:
                    continue
        
        return None
    
    async def _correlate_by_cloudwan_attachment(
        self, peer: BGPPeerInfo, topology: NetworkTopology
    ) -> Optional[BGPTopologyCorrelation]:
        """Correlate peer through CloudWAN attachment information."""
        
        # Get attachment ID from CloudWAN info
        attachment_id = None
        if peer.cloudwan_info and hasattr(peer.cloudwan_info, 'attachment_id'):
            attachment_id = peer.cloudwan_info.attachment_id
        
        if not attachment_id:
            return None
        
        # Find elements with matching attachment IDs
        for element_id, element in topology.elements.items():
            # Check CloudWAN specific elements
            if hasattr(element, 'attachments') and attachment_id in element.attachments:
                return BGPTopologyCorrelation(
                    peer_id=peer.peer_id,
                    element_id=element_id,
                    correlation_type='direct',
                    confidence_score=0.9,
                    correlation_metadata={
                        'method': 'cloudwan_attachment',
                        'attachment_id': attachment_id,
                        'element_type': element.element_type.value
                    }
                )
            
            # Check attachment ID in custom attributes
            if attachment_id in str(element.custom_attributes):
                return BGPTopologyCorrelation(
                    peer_id=peer.peer_id,
                    element_id=element_id,
                    correlation_type='attached',
                    confidence_score=0.8,
                    correlation_metadata={
                        'method': 'attachment_reference',
                        'attachment_id': attachment_id
                    }
                )
        
        return None
    
    async def _correlate_by_transit_gateway(
        self, peer: BGPPeerInfo, topology: NetworkTopology
    ) -> Optional[BGPTopologyCorrelation]:
        """Correlate peer through Transit Gateway relationships."""
        
        # Look for Transit Gateway elements with BGP capabilities
        tgw_elements = [
            (eid, elem) for eid, elem in topology.elements.items()
            if elem.element_type == NetworkElementType.TRANSIT_GATEWAY
        ]
        
        for element_id, element in tgw_elements:
            # Check ASN matching for Transit Gateway elements
            if (hasattr(element, 'amazon_side_asn') and 
                peer.local_asn and 
                element.amazon_side_asn == peer.local_asn):
                
                return BGPTopologyCorrelation(
                    peer_id=peer.peer_id,
                    element_id=element_id,
                    correlation_type='routed',
                    confidence_score=0.75,
                    correlation_metadata={
                        'method': 'transit_gateway_asn',
                        'matched_asn': element.amazon_side_asn
                    }
                )
        
        return None
    
    async def _correlate_by_network_neighborhood(
        self, peer: BGPPeerInfo, topology: NetworkTopology
    ) -> Optional[BGPTopologyCorrelation]:
        """Correlate peer through network neighborhood analysis."""
        
        if not peer.peer_ip:
            return None
        
        try:
            peer_ip = ipaddress.ip_address(peer.peer_ip)
        except ValueError:
            return None
        
        # Find elements in the same network neighborhood
        best_correlation = None
        best_score = 0.0
        
        for element_id, element in topology.elements.items():
            for element_ip_str in element.ip_addresses:
                try:
                    element_ip = ipaddress.ip_address(element_ip_str)
                    
                    # Check if IPs are in the same subnet (heuristic approach)
                    if isinstance(peer_ip, ipaddress.IPv4Address) and isinstance(element_ip, ipaddress.IPv4Address):
                        # Check /24 subnet
                        if peer_ip.packed[:-1] == element_ip.packed[:-1]:
                            score = 0.6
                            correlation = BGPTopologyCorrelation(
                                peer_id=peer.peer_id,
                                element_id=element_id,
                                correlation_type='inferred',
                                confidence_score=score,
                                correlation_metadata={
                                    'method': 'network_neighborhood',
                                    'subnet_size': 24,
                                    'peer_ip': peer_ip.exploded,
                                    'element_ip': element_ip.exploded
                                }
                            )
                            
                            if score > best_score:
                                best_score = score
                                best_correlation = correlation
                                
                except ValueError:
                    continue
        
        return best_correlation
    
    async def enhance_topology_with_bgp_data(
        self,
        topology: NetworkTopology,
        bgp_peers: List[BGPPeerInfo],
        bgp_routes: Optional[List[BGPRouteInfo]] = None
    ) -> NetworkTopology:
        """
        Enhance topology with BGP routing information and peer relationships.
        
        Args:
            topology: Base network topology
            bgp_peers: List of BGP peers to integrate
            bgp_routes: Optional BGP routes for path analysis
            
        Returns:
            Enhanced topology with BGP integration
        """
        logger.info(f"Enhancing topology with {len(bgp_peers)} BGP peers")
        start_time = datetime.now(timezone.utc)
        
        try:
            # Create correlations for all peers
            correlations = []
            correlation_tasks = [
                self.correlate_peer_with_topology(peer, topology)
                for peer in bgp_peers
            ]
            
            correlation_results = await asyncio.gather(
                *correlation_tasks, return_exceptions=True
            )
            
            for i, result in enumerate(correlation_results):
                if isinstance(result, Exception):
                    logger.warning(f"Error correlating peer {bgp_peers[i].peer_id}: {result}")
                elif result:
                    correlations.append(result)
            
            # Apply correlations to topology
            await self._apply_bgp_correlations_to_topology(topology, correlations, bgp_peers)
            
            # Add BGP-specific connections
            await self._add_bgp_connections_to_topology(topology, bgp_peers, correlations)
            
            # Integrate routing information if provided
            if bgp_routes:
                await self._integrate_bgp_routes(topology, bgp_routes, correlations)
            
            # Update topology metadata
            topology.bgp_topology_data = {
                'integration_timestamp': datetime.now(timezone.utc).isoformat(),
                'peers_integrated': len(correlations),
                'total_peers': len(bgp_peers),
                'correlation_rate': len(correlations) / len(bgp_peers) if bgp_peers else 0.0,
                'routes_integrated': len(bgp_routes) if bgp_routes else 0
            }
            
            # Update health status based on BGP integration
            await self._update_topology_health_with_bgp(topology, bgp_peers)
            
            duration = (datetime.now(timezone.utc) - start_time).total_seconds()
            logger.info(f"Enhanced topology with BGP data in {duration:.2f}s. "
                       f"Integrated {len(correlations)}/{len(bgp_peers)} peers")
            
            return topology
            
        except Exception as e:
            logger.error(f"Error enhancing topology with BGP data: {e}")
            raise BGPAnalysisError(f"BGP topology enhancement failed: {e}")
    
    async def _apply_bgp_correlations_to_topology(
        self,
        topology: NetworkTopology,
        correlations: List[BGPTopologyCorrelation],
        bgp_peers: List[BGPPeerInfo]
    ) -> None:
        """Apply BGP correlations to enhance topology elements."""
        
        # Create peer lookup
        peer_lookup = {peer.peer_id: peer for peer in bgp_peers}
        
        for correlation in correlations:
            element = topology.get_element_by_id(correlation.element_id)
            peer = peer_lookup.get(correlation.peer_id)
            
            if element and peer:
                # Add BGP context to element
                if 'bgp_peers' not in element.custom_attributes:
                    element.custom_attributes['bgp_peers'] = []
                
                peer_context = {
                    'peer_id': peer.peer_id,
                    'neighbor_address': peer.peer_ip,
                    'remote_asn': peer.peer_asn,
                    'state': peer.bgp_state.value,
                    'correlation_type': correlation.correlation_type,
                    'confidence_score': correlation.confidence_score,
                    'last_correlated': correlation.last_verified.isoformat()
                }
                element.custom_attributes['bgp_peers'].append(peer_context)
                
                # Update element health based on BGP peer state
                if peer.bgp_state == BGPPeerState.ESTABLISHED:
                    if element.health_status in [HealthStatus.UNKNOWN, HealthStatus.DEGRADED]:
                        element.update_health_status(HealthStatus.HEALTHY, "BGP peer established")
                elif peer.bgp_state == BGPPeerState.IDLE:
                    if element.health_status == HealthStatus.HEALTHY:
                        element.update_health_status(HealthStatus.DEGRADED, "BGP peer down")
                
                element.update_timestamp()
    
    async def _add_bgp_connections_to_topology(
        self,
        topology: NetworkTopology,
        bgp_peers: List[BGPPeerInfo],
        correlations: List[BGPTopologyCorrelation]
    ) -> None:
        """Add BGP session connections to topology."""
        
        # Create correlation lookup
        correlation_lookup = {corr.peer_id: corr for corr in correlations}
        
        for peer in bgp_peers:
            correlation = correlation_lookup.get(peer.peer_id)
            if not correlation:
                continue
            
            # Create BGP session connection
            connection = NetworkConnection(
                source_element_id=correlation.element_id,
                target_element_id=f"bgp_peer_{peer.peer_id}",  # Virtual BGP peer element
                connection_type=ConnectionType.BGP_SESSION,
                state=peer.bgp_state.value,
                health_status=HealthStatus.HEALTHY if peer.bgp_state == BGPPeerState.ESTABLISHED else HealthStatus.DEGRADED,
                bgp_session_info={
                    'peer_id': peer.peer_id,
                    'remote_asn': peer.peer_asn,
                    'local_asn': peer.local_asn,
                    'neighbor_address': peer.peer_ip,
                    'session_established_time': peer.session_established_time.isoformat() if peer.session_established_time else None,
                    'capabilities': peer.capabilities,
                    'route_families': peer.supported_address_families
                },
                properties={
                    'correlation_confidence': correlation.confidence_score,
                    'correlation_type': correlation.correlation_type
                }
            )
            
            topology.add_connection(connection)
    
    async def _integrate_bgp_routes(
        self,
        topology: NetworkTopology,
        bgp_routes: List[BGPRouteInfo],
        correlations: List[BGPTopologyCorrelation]
    ) -> None:
        """Integrate BGP routing information into topology."""
        
        # Create correlation lookup
        element_to_peer = {corr.element_id: corr.peer_id for corr in correlations}
        
        # Group routes by announcing element
        routes_by_element = defaultdict(list)
        
        for route in bgp_routes:
            # Find topology element announcing this route
            for element_id, peer_id in element_to_peer.items():
                if hasattr(route, 'announcing_peer') and route.announcing_peer == peer_id:
                    routes_by_element[element_id].append(route)
                    break
        
        # Add route information to topology elements
        for element_id, routes in routes_by_element.items():
            element = topology.get_element_by_id(element_id)
            if element:
                element.custom_attributes['bgp_routes'] = [
                    {
                        'prefix': route.prefix,
                        'next_hop': route.next_hop,
                        'as_path': route.as_path,
                        'origin': route.origin.value if hasattr(route, 'origin') else None,
                        'med': route.med if hasattr(route, 'med') else None,
                        'local_preference': route.local_preference if hasattr(route, 'local_preference') else None
                    }
                    for route in routes
                ]
                element.update_timestamp()
    
    async def _update_topology_health_with_bgp(
        self, topology: NetworkTopology, bgp_peers: List[BGPPeerInfo]
    ) -> None:
        """Update overall topology health based on BGP peer states."""
        
        if not bgp_peers:
            return
        
        # Calculate BGP health metrics
        total_peers = len(bgp_peers)
        established_peers = sum(1 for peer in bgp_peers if peer.bgp_state == BGPPeerState.ESTABLISHED)
        failed_peers = sum(1 for peer in bgp_peers if peer.bgp_state == BGPPeerState.IDLE)
        
        bgp_health_ratio = established_peers / total_peers if total_peers > 0 else 0.0
        
        # Update topology with BGP health information
        if 'bgp_health_metrics' not in topology.custom_attributes:
            topology.custom_attributes['bgp_health_metrics'] = {}
        
        topology.custom_attributes['bgp_health_metrics'].update({
            'total_peers': total_peers,
            'established_peers': established_peers,
            'failed_peers': failed_peers,
            'health_ratio': bgp_health_ratio,
            'last_updated': datetime.now(timezone.utc).isoformat()
        })
        
        # Adjust topology health status based on BGP health
        current_health_score = topology.calculate_health_score()
        bgp_adjusted_score = current_health_score * (0.7 + 0.3 * bgp_health_ratio)
        
        # Update topology health status
        if bgp_adjusted_score >= 0.9:
            topology.health_status = HealthStatus.HEALTHY
        elif bgp_adjusted_score >= 0.7:
            topology.health_status = HealthStatus.WARNING
        elif bgp_adjusted_score >= 0.5:
            topology.health_status = HealthStatus.DEGRADED
        else:
            topology.health_status = HealthStatus.UNHEALTHY
        
        topology.update_timestamp()
    
    def _get_cached_correlation(self, key: str) -> Optional[BGPTopologyCorrelation]:
        """Retrieve correlation from cache if still valid."""
        
        if key not in self._correlation_cache:
            return None
        
        cache_time = self._cache_timestamps.get(key)
        if not cache_time:
            return None
        
        # Check if cache is still valid
        age_seconds = (datetime.now(timezone.utc) - cache_time).total_seconds()
        if age_seconds > self.cache_ttl_seconds:
            # Remove expired cache entry
            del self._correlation_cache[key]
            del self._cache_timestamps[key]
            return None
        
        return self._correlation_cache[key]
    
    def _cache_correlation(self, key: str, correlation: BGPTopologyCorrelation) -> None:
        """Cache correlation result."""
        self._correlation_cache[key] = correlation
        self._cache_timestamps[key] = datetime.now(timezone.utc)
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get adapter performance metrics."""
        
        success_rate = (
            self._successful_correlations / self._correlation_attempts 
            if self._correlation_attempts > 0 else 0.0
        )
        
        cache_hit_rate = (
            self._cache_hits / (self._cache_hits + self._cache_misses)
            if (self._cache_hits + self._cache_misses) > 0 else 0.0
        )
        
        return {
            'correlation_attempts': self._correlation_attempts,
            'successful_correlations': self._successful_correlations,
            'success_rate': success_rate,
            'cache_hits': self._cache_hits,
            'cache_misses': self._cache_misses,
            'cache_hit_rate': cache_hit_rate,
            'cache_size': len(self._correlation_cache)
        }


class BGPTopologyCorrelator:
    """Specialized correlator for BGP-topology relationships."""
    
    def __init__(self, adapter: TopologyBGPIntegrationAdapter):
        self.adapter = adapter
        self.logger = logging.getLogger(__name__ + '.BGPTopologyCorrelator')
    
    async def find_topology_path_for_bgp_route(
        self,
        bgp_route: BGPRouteInfo,
        topology: NetworkTopology,
        correlations: List[BGPTopologyCorrelation]
    ) -> Optional[List[str]]:
        """Find topology path for BGP route advertisement."""
        
        # This method would implement sophisticated path finding
        # combining BGP AS path with physical topology
        pass
    
    async def detect_bgp_topology_inconsistencies(
        self,
        topology: NetworkTopology,
        bgp_peers: List[BGPPeerInfo],
        bgp_routes: List[BGPRouteInfo]
    ) -> List[Dict[str, Any]]:
        """Detect inconsistencies between BGP and topology data."""
        
        inconsistencies = []
        
        # Find BGP peers without topology representation
        correlations = []
        for peer in bgp_peers:
            corr = await self.adapter.correlate_peer_with_topology(peer, topology)
            if corr:
                correlations.append(corr)
            else:
                inconsistencies.append({
                    'type': 'orphaned_bgp_peer',
                    'peer_id': peer.peer_id,
                    'neighbor_address': peer.peer_ip,
                    'severity': 'medium',
                    'description': f'BGP peer {peer.peer_id} has no topology representation'
                })
        
        # Find topology elements that should have BGP peers but don't
        bgp_capable_elements = [
            elem for elem in topology.elements.values()
            if elem.element_type in [
                NetworkElementType.TRANSIT_GATEWAY,
                NetworkElementType.CORE_NETWORK,
                NetworkElementType.VPN_GATEWAY
            ]
        ]
        
        correlated_elements = {corr.element_id for corr in correlations}
        
        for element in bgp_capable_elements:
            if element.get_full_identifier() not in correlated_elements:
                inconsistencies.append({
                    'type': 'missing_bgp_peer',
                    'element_id': element.get_full_identifier(),
                    'element_type': element.element_type.value,
                    'severity': 'low',
                    'description': f'Element {element.get_identifier()} may be missing BGP configuration'
                })
        
        return inconsistencies


class TopologyBGPSynchronizer:
    """Synchronizes state between BGP and topology domains."""
    
    def __init__(self, adapter: TopologyBGPIntegrationAdapter):
        self.adapter = adapter
        self.logger = logging.getLogger(__name__ + '.TopologyBGPSynchronizer')
        self._sync_tasks: Set[str] = set()
    
    async def synchronize_peer_states(
        self,
        topology: NetworkTopology,
        bgp_peers: List[BGPPeerInfo]
    ) -> Dict[str, Any]:
        """Synchronize BGP peer states with topology element health."""
        
        sync_results = {
            'synchronized_elements': 0,
            'failed_synchronizations': 0,
            'state_changes': []
        }
        
        for peer in bgp_peers:
            try:
                correlation = await self.adapter.correlate_peer_with_topology(peer, topology)
                if correlation:
                    element = topology.get_element_by_id(correlation.element_id)
                    if element:
                        old_health = element.health_status
                        new_health = self._map_bgp_state_to_health(peer.bgp_state)
                        
                        if old_health != new_health:
                            element.update_health_status(
                                new_health, 
                                f"Synchronized with BGP peer {peer.peer_id} state: {peer.bgp_state.value}"
                            )
                            sync_results['state_changes'].append({
                                'element_id': correlation.element_id,
                                'old_health': old_health.value,
                                'new_health': new_health.value,
                                'peer_id': peer.peer_id,
                                'peer_state': peer.bgp_state.value
                            })
                        
                        sync_results['synchronized_elements'] += 1
            except Exception as e:
                self.logger.warning(f"Failed to synchronize peer {peer.peer_id}: {e}")
                sync_results['failed_synchronizations'] += 1
        
        return sync_results
    
    def _map_bgp_state_to_health(self, bgp_state: BGPPeerState) -> HealthStatus:
        """Map BGP peer state to topology element health status."""
        
        mapping = {
            BGPPeerState.ESTABLISHED: HealthStatus.HEALTHY,
            BGPPeerState.OPEN_CONFIRM: HealthStatus.WARNING,
            BGPPeerState.OPEN_SENT: HealthStatus.WARNING,
            BGPPeerState.ACTIVE: HealthStatus.DEGRADED,
            BGPPeerState.CONNECT: HealthStatus.DEGRADED,
            BGPPeerState.IDLE: HealthStatus.UNHEALTHY,
        }
        
        return mapping.get(bgp_state, HealthStatus.UNKNOWN)