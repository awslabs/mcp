"""
Network Intelligence Bridge for CloudWAN MCP Server.

This module provides cross-domain intelligence sharing and analysis capabilities
across topology, BGP, security, and operations domains. It serves as the central
coordination point for network-wide intelligence gathering and anomaly detection.

Key Features:
- Cross-domain data correlation and analysis
- Real-time anomaly detection across network domains
- Comprehensive network health assessment
- Security threat propagation and impact analysis
- Performance optimization through intelligent data sharing
"""

import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Set
from dataclasses import dataclass, field
from enum import Enum
from uuid import uuid4
from collections import defaultdict, deque
import statistics


from ..models.network.topology import NetworkTopology
from ..models.bgp.peer import BGPPeerInfo
from ..models.bgp.route import BGPRouteInfo
from ..models.shared.enums import (
    BGPPeerState, HealthStatus, SecurityThreatLevel
)
from ..models.shared.exceptions import ValidationError

from .topology_bgp_integration import TopologyBGPIntegrationAdapter

logger = logging.getLogger(__name__)


class IntelligenceLevel(str, Enum):
    """Levels of network intelligence analysis."""
    
    BASIC = "basic"           # Basic correlation and health monitoring
    ENHANCED = "enhanced"     # Advanced pattern detection and prediction
    COMPREHENSIVE = "comprehensive"  # Full cross-domain analysis
    PREDICTIVE = "predictive"  # Predictive analytics and forecasting


class AnomalyType(str, Enum):
    """Types of network anomalies that can be detected."""
    
    TOPOLOGY_BGP_MISMATCH = "topology_bgp_mismatch"
    ROUTING_INCONSISTENCY = "routing_inconsistency"
    SECURITY_THREAT_PROPAGATION = "security_threat_propagation"
    PERFORMANCE_DEGRADATION = "performance_degradation"
    CONNECTIVITY_ISSUE = "connectivity_issue"
    CONFIGURATION_DRIFT = "configuration_drift"
    CAPACITY_ISSUE = "capacity_issue"
    HEALTH_CORRELATION_ANOMALY = "health_correlation_anomaly"


@dataclass
class NetworkAnomaly:
    """Represents a detected network anomaly across domains."""
    
    anomaly_id: str = field(default_factory=lambda: str(uuid4()))
    anomaly_type: AnomalyType = AnomalyType.TOPOLOGY_BGP_MISMATCH
    severity: SecurityThreatLevel = SecurityThreatLevel.MEDIUM
    confidence_score: float = 0.7  # 0.0-1.0
    
    # Affected components
    affected_domains: Set[str] = field(default_factory=set)
    affected_elements: Set[str] = field(default_factory=set)
    affected_connections: Set[str] = field(default_factory=set)
    
    # Detection metadata
    detection_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    detection_method: str = "cross_domain_analysis"
    evidence: List[Dict[str, Any]] = field(default_factory=list)
    
    # Impact assessment
    impact_radius: Set[str] = field(default_factory=set)  # Elements potentially impacted
    business_impact: str = "unknown"
    estimated_resolution_time: Optional[timedelta] = None
    
    # Tracking
    status: str = "open"  # open, investigating, resolved, false_positive
    assignee: Optional[str] = None
    resolution_notes: Optional[str] = None
    
    def add_evidence(self, evidence_type: str, data: Any, source: str) -> None:
        """Add evidence for this anomaly."""
        self.evidence.append({
            'type': evidence_type,
            'data': data,
            'source': source,
            'timestamp': datetime.now(timezone.utc).isoformat()
        })
    
    def is_critical(self) -> bool:
        """Check if anomaly is critical severity."""
        return self.severity in [SecurityThreatLevel.CRITICAL, SecurityThreatLevel.HIGH]
    
    def get_age_hours(self) -> float:
        """Get age of anomaly in hours."""
        return (datetime.now(timezone.utc) - self.detection_time).total_seconds() / 3600


class NetworkIntelligenceBridge:
    """
    Central intelligence bridge for cross-domain network analysis.
    
    Coordinates intelligence sharing between topology, BGP, security, and
    operations domains to provide comprehensive network visibility and analysis.
    """
    
    def __init__(self,
                 topology_bgp_adapter: TopologyBGPIntegrationAdapter,
                 intelligence_level: IntelligenceLevel = IntelligenceLevel.ENHANCED,
                 anomaly_retention_hours: int = 168,  # 7 days
                 max_concurrent_analysis: int = 5):
        
        self.topology_bgp_adapter = topology_bgp_adapter
        self.intelligence_level = intelligence_level
        self.anomaly_retention_hours = anomaly_retention_hours
        self.max_concurrent_analysis = max_concurrent_analysis
        
        # Intelligence state
        self._active_anomalies: Dict[str, NetworkAnomaly] = {}
        self._resolved_anomalies: deque = deque(maxlen=1000)
        self._intelligence_cache: Dict[str, Any] = {}
        self._correlation_patterns: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        
        # Analysis engines
        self._anomaly_detector = NetworkAnomalyDetector(self)
        self._intelligence_engine = CrossDomainIntelligenceEngine(self)
        
        # Performance tracking
        self._analysis_count = 0
        self._anomalies_detected = 0
        self._false_positives = 0
        
        # Background tasks
        self._background_tasks: Set[asyncio.Task] = set()
        
        logger.info(f"Initialized NetworkIntelligenceBridge with {intelligence_level.value} intelligence level")
    
    async def start_intelligence_services(self) -> None:
        """Start background intelligence services."""
        
        # Start anomaly cleanup task
        cleanup_task = asyncio.create_task(self._anomaly_cleanup_task())
        self._background_tasks.add(cleanup_task)
        cleanup_task.add_done_callback(self._background_tasks.discard)
        
        # Start correlation pattern analysis
        if self.intelligence_level in [IntelligenceLevel.ENHANCED, IntelligenceLevel.COMPREHENSIVE]:
            pattern_task = asyncio.create_task(self._pattern_analysis_task())
            self._background_tasks.add(pattern_task)
            pattern_task.add_done_callback(self._background_tasks.discard)
        
        # Start predictive analysis
        if self.intelligence_level == IntelligenceLevel.PREDICTIVE:
            predictive_task = asyncio.create_task(self._predictive_analysis_task())
            self._background_tasks.add(predictive_task)
            predictive_task.add_done_callback(self._background_tasks.discard)
        
        logger.info("Started network intelligence background services")
    
    async def stop_intelligence_services(self) -> None:
        """Stop background intelligence services."""
        
        # Cancel all background tasks
        for task in self._background_tasks:
            task.cancel()
        
        # Wait for tasks to complete
        if self._background_tasks:
            await asyncio.gather(*self._background_tasks, return_exceptions=True)
        
        self._background_tasks.clear()
        logger.info("Stopped network intelligence background services")
    
    async def analyze_network_intelligence(
        self,
        topology: NetworkTopology,
        bgp_peers: List[BGPPeerInfo],
        bgp_routes: Optional[List[BGPRouteInfo]] = None,
        security_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Perform comprehensive cross-domain network intelligence analysis.
        
        Args:
            topology: Network topology data
            bgp_peers: BGP peer information
            bgp_routes: Optional BGP routing data
            security_context: Optional security intelligence data
            
        Returns:
            Comprehensive intelligence analysis results
        """
        start_time = datetime.now(timezone.utc)
        self._analysis_count += 1
        
        logger.info("Starting cross-domain network intelligence analysis")
        
        try:
            # Create analysis context
            analysis_context = {
                'analysis_id': str(uuid4()),
                'start_time': start_time,
                'topology': topology,
                'bgp_peers': bgp_peers,
                'bgp_routes': bgp_routes or [],
                'security_context': security_context or {}
            }
            
            # Perform multi-domain correlation
            correlation_results = await self._perform_cross_domain_correlation(analysis_context)
            
            # Detect anomalies
            detected_anomalies = await self._anomaly_detector.detect_network_anomalies(analysis_context)
            
            # Assess network health comprehensively
            health_assessment = await self._assess_comprehensive_network_health(analysis_context)
            
            # Generate intelligence insights
            intelligence_insights = await self._intelligence_engine.generate_insights(
                analysis_context, correlation_results, detected_anomalies
            )
            
            # Update active anomalies
            for anomaly in detected_anomalies:
                self._active_anomalies[anomaly.anomaly_id] = anomaly
                self._anomalies_detected += 1
            
            duration = (datetime.now(timezone.utc) - start_time).total_seconds()
            
            results = {
                'analysis_id': analysis_context['analysis_id'],
                'timestamp': start_time.isoformat(),
                'duration_seconds': duration,
                'domains_analyzed': len(self._get_active_domains(analysis_context)),
                'correlation_results': correlation_results,
                'detected_anomalies': [self._serialize_anomaly(a) for a in detected_anomalies],
                'health_assessment': health_assessment,
                'intelligence_insights': intelligence_insights,
                'performance_metrics': {
                    'elements_analyzed': len(topology.elements),
                    'bgp_peers_analyzed': len(bgp_peers),
                    'routes_analyzed': len(bgp_routes) if bgp_routes else 0,
                    'anomalies_detected': len(detected_anomalies),
                    'analysis_duration_ms': duration * 1000
                }
            }
            
            logger.info(f"Completed network intelligence analysis in {duration:.2f}s. "
                       f"Detected {len(detected_anomalies)} anomalies")
            
            return results
            
        except Exception as e:
            logger.error(f"Error during network intelligence analysis: {e}")
            raise ValidationError(f"Network intelligence analysis failed: {e}")
    
    async def _perform_cross_domain_correlation(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Perform cross-domain correlation analysis."""
        
        results = {
            'topology_bgp_correlations': [],
            'routing_topology_paths': [],
            'security_topology_overlays': [],
            'health_correlations': []
        }
        
        topology = context['topology']
        bgp_peers = context['bgp_peers']
        bgp_routes = context['bgp_routes']
        
        # Topology-BGP correlation
        bgp_correlations = []
        for peer in bgp_peers:
            correlation = await self.topology_bgp_adapter.correlate_peer_with_topology(
                peer, topology
            )
            if correlation:
                bgp_correlations.append({
                    'peer_id': correlation.peer_id,
                    'element_id': correlation.element_id,
                    'correlation_type': correlation.correlation_type,
                    'confidence_score': correlation.confidence_score,
                    'correlation_metadata': correlation.correlation_metadata
                })
        
        results['topology_bgp_correlations'] = bgp_correlations
        
        # Routing-topology path correlation
        if bgp_routes:
            routing_paths = await self._correlate_routing_paths_with_topology(
                bgp_routes, topology, bgp_correlations
            )
            results['routing_topology_paths'] = routing_paths
        
        # Health correlation analysis
        health_correlations = await self._analyze_health_correlations(context)
        results['health_correlations'] = health_correlations
        
        return results
    
    async def _correlate_routing_paths_with_topology(
        self,
        bgp_routes: List[BGPRouteInfo],
        topology: NetworkTopology,
        bgp_correlations: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Correlate BGP routing paths with physical topology paths."""
        
        routing_paths = []
        
        # Create correlation lookup
        peer_to_element = {
            corr['peer_id']: corr['element_id'] 
            for corr in bgp_correlations
        }
        
        for route in bgp_routes:
            if hasattr(route, 'as_path') and route.as_path:
                # Try to map AS path to topology path
                topology_path = []
                
                # Find elements corresponding to ASes in the path
                for asn in route.as_path:
                    # Look for elements with matching ASN
                    for element_id, element in topology.elements.items():
                        if (hasattr(element, 'amazon_side_asn') and 
                            element.amazon_side_asn == asn):
                            topology_path.append(element_id)
                            break
                
                if topology_path:
                    routing_paths.append({
                        'route_prefix': getattr(route, 'prefix', 'unknown'),
                        'as_path': route.as_path,
                        'topology_path': topology_path,
                        'path_length': len(topology_path),
                        'route_id': getattr(route, 'route_id', str(uuid4()))
                    })
        
        return routing_paths
    
    async def _analyze_health_correlations(self, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Analyze health correlations across network domains."""
        
        topology = context['topology']
        bgp_peers = context['bgp_peers']
        
        correlations = []
        
        # Analyze BGP peer health vs topology element health
        for peer in bgp_peers:
            correlation = await self.topology_bgp_adapter.correlate_peer_with_topology(
                peer, topology
            )
            if correlation:
                element = topology.get_element_by_id(correlation.element_id)
                if element:
                    # Compare BGP peer state with element health
                    peer_healthy = peer.bgp_state == BGPPeerState.ESTABLISHED
                    element_healthy = element.health_status == HealthStatus.HEALTHY
                    
                    if peer_healthy != element_healthy:
                        correlations.append({
                            'type': 'bgp_topology_health_mismatch',
                            'peer_id': peer.peer_id,
                            'element_id': correlation.element_id,
                            'peer_state': peer.state.value,
                            'element_health': element.health_status.value,
                            'correlation_confidence': correlation.confidence_score,
                            'severity': 'medium' if correlation.confidence_score > 0.8 else 'low'
                        })
        
        return correlations
    
    async def _assess_comprehensive_network_health(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Perform comprehensive network health assessment across all domains."""
        
        topology = context['topology']
        bgp_peers = context['bgp_peers']
        
        assessment = {
            'overall_health_score': 0.0,
            'domain_health_scores': {},
            'health_factors': [],
            'improvement_recommendations': []
        }
        
        # Topology health assessment
        topology_score = topology.calculate_health_score()
        assessment['domain_health_scores']['topology'] = topology_score
        
        # BGP health assessment
        if bgp_peers:
            established_peers = sum(1 for peer in bgp_peers if peer.bgp_state == BGPPeerState.ESTABLISHED)
            bgp_score = established_peers / len(bgp_peers)
            assessment['domain_health_scores']['bgp'] = bgp_score
        else:
            bgp_score = 1.0  # No BGP peers is not necessarily unhealthy
        
        # Cross-domain health correlation
        correlation_penalty = await self._calculate_correlation_health_penalty(context)
        
        # Calculate overall health score
        overall_score = (topology_score * 0.6 + bgp_score * 0.3 - correlation_penalty * 0.1)
        assessment['overall_health_score'] = max(0.0, min(1.0, overall_score))
        
        # Generate health factors and recommendations
        assessment['health_factors'] = await self._identify_health_factors(context, assessment)
        assessment['improvement_recommendations'] = await self._generate_health_recommendations(
            context, assessment
        )
        
        return assessment
    
    async def _calculate_correlation_health_penalty(self, context: Dict[str, Any]) -> float:
        """Calculate health penalty for poor cross-domain correlations."""
        
        topology = context['topology']
        bgp_peers = context['bgp_peers']
        
        if not bgp_peers:
            return 0.0
        
        # Calculate correlation success rate
        successful_correlations = 0
        for peer in bgp_peers:
            correlation = await self.topology_bgp_adapter.correlate_peer_with_topology(
                peer, topology
            )
            if correlation and correlation.confidence_score >= 0.7:
                successful_correlations += 1
        
        correlation_rate = successful_correlations / len(bgp_peers)
        
        # Return penalty (0.0-0.5) based on correlation failures
        return (1.0 - correlation_rate) * 0.5
    
    async def _identify_health_factors(
        self, context: Dict[str, Any], assessment: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Identify factors contributing to overall network health."""
        
        factors = []
        
        # Topology factors
        topology = context['topology']
        topology_score = assessment['domain_health_scores']['topology']
        
        if topology_score < 0.8:
            unhealthy_elements = [
                elem for elem in topology.elements.values()
                if elem.health_status in [HealthStatus.UNHEALTHY, HealthStatus.CRITICAL]
            ]
            if unhealthy_elements:
                factors.append({
                    'factor_type': 'unhealthy_elements',
                    'impact': 'negative',
                    'severity': 'high' if len(unhealthy_elements) > 5 else 'medium',
                    'description': f'{len(unhealthy_elements)} unhealthy topology elements detected',
                    'affected_count': len(unhealthy_elements)
                })
        
        # BGP factors
        bgp_peers = context['bgp_peers']
        if bgp_peers:
            bgp_score = assessment['domain_health_scores']['bgp']
            if bgp_score < 0.8:
                down_peers = [peer for peer in bgp_peers if peer.bgp_state == BGPPeerState.IDLE]
                if down_peers:
                    factors.append({
                        'factor_type': 'bgp_peers_down',
                        'impact': 'negative',
                        'severity': 'high' if len(down_peers) > 3 else 'medium',
                        'description': f'{len(down_peers)} BGP peers are down',
                        'affected_count': len(down_peers)
                    })
        
        return factors
    
    async def _generate_health_recommendations(
        self, context: Dict[str, Any], assessment: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Generate recommendations for improving network health."""
        
        recommendations = []
        
        overall_score = assessment['overall_health_score']
        
        if overall_score < 0.9:
            # General recommendations based on health factors
            for factor in assessment['health_factors']:
                if factor['factor_type'] == 'unhealthy_elements':
                    recommendations.append({
                        'recommendation_type': 'element_health_investigation',
                        'priority': 'high',
                        'description': 'Investigate and remediate unhealthy network elements',
                        'action_items': [
                            'Review element health status and error logs',
                            'Check connectivity and configuration',
                            'Consider redundancy improvements'
                        ]
                    })
                
                elif factor['factor_type'] == 'bgp_peers_down':
                    recommendations.append({
                        'recommendation_type': 'bgp_troubleshooting',
                        'priority': 'high',
                        'description': 'Troubleshoot and restore BGP peer connections',
                        'action_items': [
                            'Check BGP configuration and authentication',
                            'Verify network connectivity to peers',
                            'Review BGP logs for session failures'
                        ]
                    })
        
        return recommendations
    
    def _get_active_domains(self, context: Dict[str, Any]) -> Set[str]:
        """Get set of active domains in analysis context."""
        
        domains = {'topology'}  # Always have topology
        
        if context['bgp_peers']:
            domains.add('bgp')
        
        if context['bgp_routes']:
            domains.add('routing')
        
        if context['security_context']:
            domains.add('security')
        
        return domains
    
    def _serialize_anomaly(self, anomaly: NetworkAnomaly) -> Dict[str, Any]:
        """Serialize network anomaly for JSON response."""
        
        return {
            'anomaly_id': anomaly.anomaly_id,
            'anomaly_type': anomaly.anomaly_type.value,
            'severity': anomaly.severity.value,
            'confidence_score': anomaly.confidence_score,
            'affected_domains': list(anomaly.affected_domains),
            'affected_elements': list(anomaly.affected_elements),
            'detection_time': anomaly.detection_time.isoformat(),
            'detection_method': anomaly.detection_method,
            'evidence_count': len(anomaly.evidence),
            'impact_radius': list(anomaly.impact_radius),
            'business_impact': anomaly.business_impact,
            'status': anomaly.status,
            'age_hours': anomaly.get_age_hours()
        }
    
    async def _anomaly_cleanup_task(self) -> None:
        """Background task to clean up old resolved anomalies."""
        
        while True:
            try:
                current_time = datetime.now(timezone.utc)
                cutoff_time = current_time - timedelta(hours=self.anomaly_retention_hours)
                
                # Clean up old resolved anomalies
                expired_ids = []
                for anomaly_id, anomaly in self._active_anomalies.items():
                    if (anomaly.status == 'resolved' and 
                        anomaly.detection_time < cutoff_time):
                        expired_ids.append(anomaly_id)
                
                for anomaly_id in expired_ids:
                    resolved_anomaly = self._active_anomalies.pop(anomaly_id)
                    self._resolved_anomalies.append(resolved_anomaly)
                
                if expired_ids:
                    logger.debug(f"Cleaned up {len(expired_ids)} old resolved anomalies")
                
                # Sleep for 1 hour before next cleanup
                await asyncio.sleep(3600)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in anomaly cleanup task: {e}")
                await asyncio.sleep(300)  # Wait 5 minutes on error
    
    async def _pattern_analysis_task(self) -> None:
        """Background task for pattern analysis and learning."""
        
        while True:
            try:
                # Analyze patterns in correlation data
                await self._analyze_correlation_patterns()
                
                # Sleep for 30 minutes before next analysis
                await asyncio.sleep(1800)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in pattern analysis task: {e}")
                await asyncio.sleep(900)  # Wait 15 minutes on error
    
    async def _predictive_analysis_task(self) -> None:
        """Background task for predictive analysis."""
        
        while True:
            try:
                # Perform predictive analysis based on historical data
                await self._perform_predictive_analysis()
                
                # Sleep for 1 hour before next analysis
                await asyncio.sleep(3600)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in predictive analysis task: {e}")
                await asyncio.sleep(1800)  # Wait 30 minutes on error
    
    async def _analyze_correlation_patterns(self) -> None:
        """Analyze patterns in cross-domain correlations."""
        
        # This would implement sophisticated pattern analysis
        # for now, just log that it's running
        logger.debug("Running correlation pattern analysis")
    
    async def _perform_predictive_analysis(self) -> None:
        """Perform predictive analysis based on historical data."""
        
        # This would implement predictive analytics
        # for now, just log that it's running
        logger.debug("Running predictive analysis")
    
    def get_intelligence_metrics(self) -> Dict[str, Any]:
        """Get intelligence bridge performance metrics."""
        
        return {
            'analysis_count': self._analysis_count,
            'anomalies_detected': self._anomalies_detected,
            'active_anomalies': len(self._active_anomalies),
            'resolved_anomalies': len(self._resolved_anomalies),
            'false_positives': self._false_positives,
            'intelligence_level': self.intelligence_level.value,
            'cache_size': len(self._intelligence_cache),
            'correlation_patterns': len(self._correlation_patterns),
            'background_tasks_active': len(self._background_tasks)
        }


class CrossDomainIntelligenceEngine:
    """Advanced intelligence engine for cross-domain analysis."""
    
    def __init__(self, bridge: NetworkIntelligenceBridge):
        self.bridge = bridge
        self.logger = logging.getLogger(__name__ + '.CrossDomainIntelligenceEngine')
    
    async def generate_insights(
        self,
        context: Dict[str, Any],
        correlation_results: Dict[str, Any],
        anomalies: List[NetworkAnomaly]
    ) -> List[Dict[str, Any]]:
        """Generate intelligence insights from cross-domain analysis."""
        
        insights = []
        
        # Topology-BGP insights
        bgp_insights = await self._generate_bgp_topology_insights(
            context, correlation_results
        )
        insights.extend(bgp_insights)
        
        # Anomaly pattern insights
        anomaly_insights = await self._generate_anomaly_pattern_insights(anomalies)
        insights.extend(anomaly_insights)
        
        # Network optimization insights
        optimization_insights = await self._generate_optimization_insights(
            context, correlation_results
        )
        insights.extend(optimization_insights)
        
        return insights
    
    async def _generate_bgp_topology_insights(
        self, context: Dict[str, Any], correlation_results: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Generate insights about BGP-topology relationships."""
        
        insights = []
        bgp_correlations = correlation_results.get('topology_bgp_correlations', [])
        
        if bgp_correlations:
            # Calculate correlation quality
            high_confidence = [c for c in bgp_correlations if c['confidence_score'] >= 0.8]
            correlation_rate = len(high_confidence) / len(bgp_correlations)
            
            if correlation_rate >= 0.9:
                insights.append({
                    'insight_type': 'bgp_topology_alignment',
                    'priority': 'low',
                    'description': 'BGP and topology data are well-aligned',
                    'details': {
                        'correlation_rate': correlation_rate,
                        'total_peers': len(bgp_correlations),
                        'high_confidence_correlations': len(high_confidence)
                    }
                })
            elif correlation_rate < 0.7:
                insights.append({
                    'insight_type': 'bgp_topology_misalignment',
                    'priority': 'high',
                    'description': 'Significant BGP-topology correlation issues detected',
                    'details': {
                        'correlation_rate': correlation_rate,
                        'problematic_peers': len(bgp_correlations) - len(high_confidence)
                    },
                    'recommendations': [
                        'Review BGP configuration alignment with topology',
                        'Verify network discovery completeness',
                        'Check for configuration drift'
                    ]
                })
        
        return insights
    
    async def _generate_anomaly_pattern_insights(
        self, anomalies: List[NetworkAnomaly]
    ) -> List[Dict[str, Any]]:
        """Generate insights about anomaly patterns."""
        
        insights = []
        
        if not anomalies:
            return insights
        
        # Analyze anomaly types
        anomaly_counts = defaultdict(int)
        for anomaly in anomalies:
            anomaly_counts[anomaly.anomaly_type] += 1
        
        # Identify dominant anomaly types
        if anomaly_counts:
            dominant_type = max(anomaly_counts.keys(), key=lambda x: anomaly_counts[x])
            dominant_count = anomaly_counts[dominant_type]
            
            if dominant_count > len(anomalies) * 0.5:
                insights.append({
                    'insight_type': 'dominant_anomaly_pattern',
                    'priority': 'medium',
                    'description': f'Dominant anomaly pattern: {dominant_type.value}',
                    'details': {
                        'anomaly_type': dominant_type.value,
                        'occurrence_count': dominant_count,
                        'percentage': (dominant_count / len(anomalies)) * 100
                    },
                    'recommendations': [
                        f'Focus remediation efforts on {dominant_type.value} issues',
                        'Investigate root cause for pattern emergence'
                    ]
                })
        
        return insights
    
    async def _generate_optimization_insights(
        self, context: Dict[str, Any], correlation_results: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Generate network optimization insights."""
        
        insights = []
        topology = context['topology']
        
        # Analyze topology efficiency
        if topology.elements:
            # Check for over-connected elements (potential bottlenecks)
            connection_counts = defaultdict(int)
            for connection in topology.connections.values():
                connection_counts[connection.source_element_id] += 1
                connection_counts[connection.target_element_id] += 1
            
            if connection_counts:
                avg_connections = statistics.mean(connection_counts.values())
                highly_connected = [
                    elem_id for elem_id, count in connection_counts.items()
                    if count > avg_connections * 2
                ]
                
                if highly_connected:
                    insights.append({
                        'insight_type': 'network_bottleneck_risk',
                        'priority': 'medium',
                        'description': 'Potential network bottlenecks detected',
                        'details': {
                            'highly_connected_elements': len(highly_connected),
                            'average_connections': avg_connections,
                            'bottleneck_candidates': highly_connected[:5]  # Top 5
                        },
                        'recommendations': [
                            'Review load balancing for highly connected elements',
                            'Consider redundancy improvements',
                            'Monitor performance of identified elements'
                        ]
                    })
        
        return insights


class NetworkAnomalyDetector:
    """Specialized anomaly detector for network intelligence."""
    
    def __init__(self, bridge: NetworkIntelligenceBridge):
        self.bridge = bridge
        self.logger = logging.getLogger(__name__ + '.NetworkAnomalyDetector')
    
    async def detect_network_anomalies(self, context: Dict[str, Any]) -> List[NetworkAnomaly]:
        """Detect anomalies across network domains."""
        
        anomalies = []
        
        # Topology-BGP mismatch detection
        topology_bgp_anomalies = await self._detect_topology_bgp_mismatches(context)
        anomalies.extend(topology_bgp_anomalies)
        
        # Routing inconsistency detection
        routing_anomalies = await self._detect_routing_inconsistencies(context)
        anomalies.extend(routing_anomalies)
        
        # Health correlation anomalies
        health_anomalies = await self._detect_health_correlation_anomalies(context)
        anomalies.extend(health_anomalies)
        
        # Performance anomalies
        performance_anomalies = await self._detect_performance_anomalies(context)
        anomalies.extend(performance_anomalies)
        
        return anomalies
    
    async def _detect_topology_bgp_mismatches(self, context: Dict[str, Any]) -> List[NetworkAnomaly]:
        """Detect mismatches between topology and BGP data."""
        
        anomalies = []
        topology = context['topology']
        bgp_peers = context['bgp_peers']
        
        # Find BGP peers without topology correlation
        uncorrelated_peers = []
        for peer in bgp_peers:
            correlation = await self.bridge.topology_bgp_adapter.correlate_peer_with_topology(
                peer, topology
            )
            if not correlation or correlation.confidence_score < 0.5:
                uncorrelated_peers.append(peer)
        
        if uncorrelated_peers:
            anomaly = NetworkAnomaly(
                anomaly_type=AnomalyType.TOPOLOGY_BGP_MISMATCH,
                severity=SecurityThreatLevel.MEDIUM,
                confidence_score=0.8,
                affected_domains={'topology', 'bgp'},
                affected_elements=set(),
                detection_method='uncorrelated_peers_detection'
            )
            
            for peer in uncorrelated_peers:
                anomaly.add_evidence(
                    'uncorrelated_bgp_peer',
                    {
                        'peer_id': peer.peer_id,
                        'neighbor_address': peer.peer_ip,
                        'state': peer.bgp_state.value
                    },
                    'topology_bgp_correlator'
                )
            
            anomalies.append(anomaly)
        
        return anomalies
    
    async def _detect_routing_inconsistencies(self, context: Dict[str, Any]) -> List[NetworkAnomaly]:
        """Detect routing inconsistencies."""
        
        anomalies = []
        
        # Implementation would analyze BGP routes vs topology paths
        # For now, return empty list
        
        return anomalies
    
    async def _detect_health_correlation_anomalies(self, context: Dict[str, Any]) -> List[NetworkAnomaly]:
        """Detect anomalies in health correlations across domains."""
        
        anomalies = []
        topology = context['topology']
        bgp_peers = context['bgp_peers']
        
        # Find health mismatches between BGP peers and topology elements
        health_mismatches = []
        
        for peer in bgp_peers:
            correlation = await self.bridge.topology_bgp_adapter.correlate_peer_with_topology(
                peer, topology
            )
            if correlation and correlation.confidence_score >= 0.7:
                element = topology.get_element_by_id(correlation.element_id)
                if element:
                    peer_healthy = peer.bgp_state == BGPPeerState.ESTABLISHED
                    element_healthy = element.health_status in [
                        HealthStatus.HEALTHY, HealthStatus.WARNING
                    ]
                    
                    if peer_healthy != element_healthy:
                        health_mismatches.append({
                            'peer': peer,
                            'element': element,
                            'correlation': correlation
                        })
        
        if health_mismatches:
            anomaly = NetworkAnomaly(
                anomaly_type=AnomalyType.HEALTH_CORRELATION_ANOMALY,
                severity=SecurityThreatLevel.MEDIUM,
                confidence_score=0.7,
                affected_domains={'topology', 'bgp'},
                detection_method='health_correlation_analysis'
            )
            
            for mismatch in health_mismatches:
                anomaly.affected_elements.add(mismatch['element'].get_full_identifier())
                anomaly.add_evidence(
                    'health_mismatch',
                    {
                        'peer_id': mismatch['peer'].peer_id,
                        'peer_state': mismatch['peer'].state.value,
                        'element_id': mismatch['element'].get_full_identifier(),
                        'element_health': mismatch['element'].health_status.value,
                        'correlation_confidence': mismatch['correlation'].confidence_score
                    },
                    'health_correlation_detector'
                )
            
            anomalies.append(anomaly)
        
        return anomalies
    
    async def _detect_performance_anomalies(self, context: Dict[str, Any]) -> List[NetworkAnomaly]:
        """Detect performance-related anomalies."""
        
        anomalies = []
        
        # Implementation would analyze performance metrics
        # For now, return empty list
        
        return anomalies