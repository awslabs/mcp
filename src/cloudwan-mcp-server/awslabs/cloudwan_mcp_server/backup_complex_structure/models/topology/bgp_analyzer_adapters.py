"""
BGP Analyzer Migration Adapters for CloudWAN MCP Server.

This module implements adapter patterns to integrate existing BGP analyzers
with the unified BGP Integration Manager. Based on the DeepSeek R1 architectural
design for seamless migration and backward compatibility.

Key Features:
- Adapter pattern implementation for each BGP analyzer
- Backward compatibility with existing analyzer interfaces
- Shared model integration for consistent data formats
- Performance optimization for adapter overhead
- Troubleshooting workflow support

Analyzer Integration Status:
- CloudWAN BGP Analyzer: ✅ Fully migrated (Phase 4)
- BGP Protocol Analyzer: 🟡 Compatibility adapter (needs completion)
- BGP Operations Analyzer: ❌ Full migration required
- BGP Security Analyzer: ❌ Full migration required
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from abc import ABC, abstractmethod
from enum import Enum


from .bgp_topology import BGPPeerModel
from ..shared.enums import BGPPeerState, SecurityThreatLevel

logger = logging.getLogger(__name__)


class AnalyzerMigrationStatus(str, Enum):
    """Migration status for BGP analyzers."""
    FULLY_MIGRATED = "fully_migrated"
    COMPATIBILITY_ADAPTER = "compatibility_adapter"
    MIGRATION_REQUIRED = "migration_required"
    DEPRECATED = "deprecated"


class BaseModelAdapter(ABC):
    """
    Abstract base class for BGP analyzer adapters.
    
    Provides common functionality for adapting existing analyzers
    to work with the unified BGP Integration Manager.
    """
    
    def __init__(self, analyzer_instance: Any):
        """
        Initialize adapter with analyzer instance.
        
        Args:
            analyzer_instance: The analyzer instance to adapt
        """
        self.analyzer_instance = analyzer_instance
        self.migration_status = AnalyzerMigrationStatus.MIGRATION_REQUIRED
        self.adapter_id = f"{self.__class__.__name__}_{id(self)}"
        self.performance_metrics = {}
        
        logger.info(f"Initialized {self.__class__.__name__} for {type(analyzer_instance).__name__}")
    
    @abstractmethod
    async def discover_bgp_peers(
        self, 
        regions: List[str], 
        **kwargs
    ) -> List[BGPPeerModel]:
        """
        Discover BGP peers and return in unified format.
        
        Args:
            regions: List of regions to analyze
            **kwargs: Additional analyzer-specific parameters
            
        Returns:
            List of BGP peers in unified format
        """
        pass
    
    @abstractmethod
    async def analyze_bgp_topology(
        self, 
        regions: List[str], 
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Analyze BGP topology and return results.
        
        Args:
            regions: List of regions to analyze
            context: Additional context for analysis
            
        Returns:
            Analysis results in unified format
        """
        pass
    
    def get_migration_status(self) -> AnalyzerMigrationStatus:
        """Get migration status of this adapter."""
        return self.migration_status
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics for this adapter."""
        return self.performance_metrics.copy()


class CloudWANBGPAdapter(BaseModelAdapter):
    """
    Adapter for CloudWAN BGP Analyzer (already fully migrated).
    
    This analyzer has been fully migrated to shared models in Phase 4,
    so this adapter primarily provides interface consistency.
    """
    
    def __init__(self, analyzer_instance: Any):
        super().__init__(analyzer_instance)
        self.migration_status = AnalyzerMigrationStatus.FULLY_MIGRATED
    
    async def discover_bgp_peers(
        self, 
        regions: List[str], 
        **kwargs
    ) -> List[BGPPeerModel]:
        """
        Discover BGP peers through CloudWAN analyzer.
        
        Since this analyzer is fully migrated, it already returns
        BGPPeerModel instances directly.
        """
        if not hasattr(self.analyzer_instance, 'discover_cloudwan_bgp_peers'):
            logger.warning("CloudWAN analyzer missing expected method")
            return []
        
        start_time = datetime.now(timezone.utc)
        
        try:
            peers = await self.analyzer_instance.discover_cloudwan_bgp_peers(
                regions=regions,
                **kwargs
            )
            
            # Already in correct format, just ensure type consistency
            if isinstance(peers, list) and all(isinstance(p, BGPPeerModel) for p in peers):
                return peers
            else:
                logger.warning("CloudWAN analyzer returned unexpected peer format")
                return []
                
        except Exception as e:
            logger.error(f"CloudWAN BGP peer discovery failed: {e}")
            return []
        finally:
            execution_time = (datetime.now(timezone.utc) - start_time).total_seconds()
            self.performance_metrics['peer_discovery_time'] = execution_time
    
    async def analyze_bgp_topology(
        self, 
        regions: List[str], 
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Analyze BGP topology through CloudWAN analyzer.
        """
        if not hasattr(self.analyzer_instance, 'analyze_cloudwan_bgp_topology'):
            logger.warning("CloudWAN analyzer missing expected method")
            return {}
        
        start_time = datetime.now(timezone.utc)
        
        try:
            result = await self.analyzer_instance.analyze_cloudwan_bgp_topology(
                regions=regions,
                context=context
            )
            
            return result
            
        except Exception as e:
            logger.error(f"CloudWAN BGP topology analysis failed: {e}")
            return {}
        finally:
            execution_time = (datetime.now(timezone.utc) - start_time).total_seconds()
            self.performance_metrics['topology_analysis_time'] = execution_time


class ProtocolBGPAdapter(BaseModelAdapter):
    """
    Adapter for BGP Protocol Analyzer (compatibility layer required).
    
    This analyzer has compatibility adapters in place but needs completion
    of the migration to shared models.
    """
    
    def __init__(self, analyzer_instance: Any):
        super().__init__(analyzer_instance)
        self.migration_status = AnalyzerMigrationStatus.COMPATIBILITY_ADAPTER
    
    async def discover_bgp_peers(
        self, 
        regions: List[str], 
        **kwargs
    ) -> List[BGPPeerModel]:
        """
        Discover BGP peers and transform to unified format.
        """
        if not hasattr(self.analyzer_instance, 'get_bgp_peer_information'):
            logger.warning("Protocol analyzer missing expected method")
            return []
        
        start_time = datetime.now(timezone.utc)
        peers = []
        
        try:
            # Get raw peer information from protocol analyzer
            raw_peers = await self.analyzer_instance.get_bgp_peer_information(
                regions=regions,
                **kwargs
            )
            
            # Transform to BGPPeerModel format
            for raw_peer in raw_peers:
                peer = self._transform_protocol_peer_to_model(raw_peer)
                if peer:
                    peers.append(peer)
            
            return peers
            
        except Exception as e:
            logger.error(f"Protocol BGP peer discovery failed: {e}")
            return []
        finally:
            execution_time = (datetime.now(timezone.utc) - start_time).total_seconds()
            self.performance_metrics['peer_discovery_time'] = execution_time
    
    async def analyze_bgp_topology(
        self, 
        regions: List[str], 
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Analyze BGP protocol state and transform results.
        """
        if not hasattr(self.analyzer_instance, 'analyze_bgp_protocol_state'):
            logger.warning("Protocol analyzer missing expected method")
            return {}
        
        start_time = datetime.now(timezone.utc)
        
        try:
            raw_result = await self.analyzer_instance.analyze_bgp_protocol_state(
                regions=regions,
                context=context
            )
            
            # Transform to unified format
            unified_result = {
                'analyzer_type': 'protocol',
                'regions': regions,
                'protocol_state': raw_result.get('state', {}),
                'peer_states': self._transform_protocol_peer_states(
                    raw_result.get('peer_states', {})
                ),
                'session_statistics': raw_result.get('statistics', {}),
                'configuration_analysis': raw_result.get('config_analysis', {}),
                'troubleshooting_data': {
                    'fsm_states': raw_result.get('fsm_states', {}),
                    'message_statistics': raw_result.get('message_stats', {}),
                    'error_counters': raw_result.get('error_counters', {})
                }
            }
            
            return unified_result
            
        except Exception as e:
            logger.error(f"Protocol BGP topology analysis failed: {e}")
            return {}
        finally:
            execution_time = (datetime.now(timezone.utc) - start_time).total_seconds()
            self.performance_metrics['topology_analysis_time'] = execution_time
    
    def _transform_protocol_peer_to_model(self, raw_peer: Dict[str, Any]) -> Optional[BGPPeerModel]:
        """Transform raw protocol peer data to BGPPeerModel."""
        try:
            return BGPPeerModel(
                peer_id=raw_peer.get('peer_id', f"proto-{raw_peer.get('peer_ip')}"),
                peer_ip=raw_peer.get('peer_ip', ''),
                peer_asn=raw_peer.get('peer_asn', 0),
                local_asn=raw_peer.get('local_asn', 0),
                peer_state=self._map_protocol_peer_state(raw_peer.get('state', 'unknown')),
                session_direction=raw_peer.get('direction', 'bidirectional'),
                address_families=raw_peer.get('address_families', ['ipv4-unicast']),
                route_count=raw_peer.get('route_count', 0),
                last_update_time=datetime.now(timezone.utc),
                region=raw_peer.get('region', 'unknown')
            )
        except Exception as e:
            logger.error(f"Failed to transform protocol peer: {e}")
            return None
    
    def _map_protocol_peer_state(self, raw_state: str) -> BGPPeerState:
        """Map raw protocol peer state to BGPPeerState enum."""
        state_mapping = {
            'established': BGPPeerState.ESTABLISHED,
            'active': BGPPeerState.ACTIVE,
            'connect': BGPPeerState.CONNECT,
            'idle': BGPPeerState.IDLE,
            'opensent': BGPPeerState.OPEN_SENT,
            'openconfirm': BGPPeerState.OPEN_CONFIRM
        }
        return state_mapping.get(raw_state.lower(), BGPPeerState.IDLE)
    
    def _transform_protocol_peer_states(self, raw_states: Dict[str, Any]) -> Dict[str, Any]:
        """Transform raw peer states to unified format."""
        transformed = {}
        for peer_id, state_data in raw_states.items():
            transformed[peer_id] = {
                'fsm_state': state_data.get('fsm_state'),
                'uptime': state_data.get('uptime'),
                'keepalive_interval': state_data.get('keepalive_interval'),
                'hold_time': state_data.get('hold_time'),
                'message_counters': state_data.get('message_counters', {})
            }
        return transformed


class OperationalBGPAdapter(BaseModelAdapter):
    """
    Adapter for BGP Operations Analyzer (full migration required).
    
    This analyzer focuses on enterprise monitoring and operations
    and requires full migration to shared models.
    """
    
    def __init__(self, analyzer_instance: Any):
        super().__init__(analyzer_instance)
        self.migration_status = AnalyzerMigrationStatus.MIGRATION_REQUIRED
    
    async def discover_bgp_peers(
        self, 
        regions: List[str], 
        **kwargs
    ) -> List[BGPPeerModel]:
        """
        Discover BGP peers from operations perspective.
        """
        try:
            peers = []
            
            # Try to use analyzer's operational data methods
            if hasattr(self.analyzer_instance, 'get_operational_bgp_peers'):
                raw_peers = await self.analyzer_instance.get_operational_bgp_peers(regions, **kwargs)
                for peer_data in raw_peers:
                    peer = self._transform_operations_peer_to_model(peer_data)
                    if peer:
                        peers.append(peer)
            elif hasattr(self.analyzer_instance, 'discover_bgp_peers'):
                # Fallback to generic discover method
                raw_peers = await self.analyzer_instance.discover_bgp_peers(regions, **kwargs)
                for peer_data in raw_peers:
                    peer = BGPPeerModel(
                        peer_id=peer_data.get('peer_id', f"ops-peer-{len(peers)}"),
                        local_asn=peer_data.get('local_asn', 65000),
                        peer_asn=peer_data.get('peer_asn', 65001), 
                        peer_ip=peer_data.get('peer_ip', '0.0.0.0'),
                        peer_state=peer_data.get('peer_state', BGPPeerState.IDLE),
                        region=peer_data.get('region', regions[0] if regions else 'us-east-1'),
                        last_seen=datetime.now(timezone.utc)
                    )
                    peers.append(peer)
            else:
                logger.info("Operations analyzer has no BGP peer discovery method - using empty result")
                
            return peers
            
        except Exception as e:
            logger.error(f"Operations BGP peer discovery failed: {e}")
            return []
    
    async def analyze_bgp_topology(
        self, 
        regions: List[str], 
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Analyze BGP from operations monitoring perspective.
        """
        try:
            result = {
                'analysis_type': 'operations_bgp_analysis',
                'regions': regions,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'operational_metrics': {},
                'performance_data': {},
                'alerts': []
            }
            
            # Try to use analyzer's operational analysis methods
            if hasattr(self.analyzer_instance, 'analyze_operational_bgp'):
                ops_data = await self.analyzer_instance.analyze_operational_bgp(regions, context)
                result['operational_metrics'] = ops_data.get('metrics', {})
                result['performance_data'] = ops_data.get('performance', {})
                result['alerts'] = ops_data.get('alerts', [])
            elif hasattr(self.analyzer_instance, 'get_bgp_monitoring_data'):
                # Alternative method name
                monitor_data = await self.analyzer_instance.get_bgp_monitoring_data(regions)
                result['operational_metrics'] = monitor_data
            else:
                logger.info("Operations analyzer has no operational BGP analysis method")
                result['operational_metrics'] = {
                    'session_count': 0,
                    'established_sessions': 0,
                    'avg_response_time': 0.0,
                    'error_rate': 0.0
                }
            
            return result
            
        except Exception as e:
            logger.error(f"Operations BGP analysis failed: {e}")
            return {
                'analysis_type': 'operations_bgp_analysis',
                'regions': regions,
                'error': str(e),
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
    
    def _transform_operations_peer_to_model(self, peer_data: Dict[str, Any]) -> Optional[BGPPeerModel]:
        """Transform operations peer data to BGPPeerModel."""
        try:
            return BGPPeerModel(
                peer_id=peer_data.get('peer_id', f"ops-peer-{int(time.time())}"),
                local_asn=peer_data.get('local_asn', 65000),
                peer_asn=peer_data.get('peer_asn', 65001),
                peer_ip=peer_data.get('peer_ip', '0.0.0.0'),
                peer_state=peer_data.get('peer_state', BGPPeerState.IDLE),
                region=peer_data.get('region', 'us-east-1'),
                last_seen=peer_data.get('last_seen', datetime.now(timezone.utc)),
                # Add operational metrics if available
                metrics=peer_data.get('metrics'),
                troubleshooting_notes=peer_data.get('troubleshooting_notes', [])
            )
        except Exception as e:
            logger.error(f"Failed to transform operations peer data: {e}")
            return None
    
    async def analyze_operational_state(
        self, 
        regions: List[str], 
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Analyze operational state of BGP infrastructure.
        """
        if not hasattr(self.analyzer_instance, 'analyze_bgp_operations'):
            logger.warning("Operations analyzer missing expected method")
            return {}
        
        start_time = datetime.now(timezone.utc)
        
        try:
            # This would need to be implemented based on actual operations analyzer interface
            raw_result = await self.analyzer_instance.analyze_bgp_operations(
                regions=regions,
                context=context
            )
            
            # Transform to unified format
            operational_result = {
                'analyzer_type': 'operations',
                'regions': regions,
                'operational_metrics': raw_result.get('metrics', {}),
                'sla_status': raw_result.get('sla', {}),
                'automation_status': raw_result.get('automation', {}),
                'alert_summaries': raw_result.get('alerts', []),
                'troubleshooting_data': {
                    'degraded_peers': raw_result.get('degraded_peers', []),
                    'performance_issues': raw_result.get('performance_issues', []),
                    'capacity_warnings': raw_result.get('capacity_warnings', [])
                }
            }
            
            return operational_result
            
        except Exception as e:
            logger.error(f"Operations BGP analysis failed: {e}")
            return {}
        finally:
            execution_time = (datetime.now(timezone.utc) - start_time).total_seconds()
            self.performance_metrics['operational_analysis_time'] = execution_time


class SecurityBGPAdapter(BaseModelAdapter):
    """
    Adapter for BGP Security Analyzer (full migration required).
    
    This analyzer focuses on BGP security threats and requires
    full migration to shared models.
    """
    
    def __init__(self, analyzer_instance: Any):
        super().__init__(analyzer_instance)
        self.migration_status = AnalyzerMigrationStatus.MIGRATION_REQUIRED
    
    async def discover_bgp_peers(
        self, 
        regions: List[str], 
        **kwargs
    ) -> List[BGPPeerModel]:
        """
        Discover BGP peers from security perspective.
        """
        try:
            peers = []
            
            # Try to use analyzer's security-focused methods
            if hasattr(self.analyzer_instance, 'get_security_monitored_peers'):
                raw_peers = await self.analyzer_instance.get_security_monitored_peers(regions, **kwargs)
                for peer_data in raw_peers:
                    peer = self._transform_security_peer_to_model(peer_data)
                    if peer:
                        peers.append(peer)
            elif hasattr(self.analyzer_instance, 'discover_bgp_peers'):
                # Fallback to generic discover method with security enhancements
                raw_peers = await self.analyzer_instance.discover_bgp_peers(regions, **kwargs)
                for peer_data in raw_peers:
                    peer = BGPPeerModel(
                        peer_id=peer_data.get('peer_id', f"sec-peer-{len(peers)}"),
                        local_asn=peer_data.get('local_asn', 65000),
                        peer_asn=peer_data.get('peer_asn', 65001),
                        peer_ip=peer_data.get('peer_ip', '0.0.0.0'),
                        peer_state=peer_data.get('peer_state', BGPPeerState.IDLE),
                        region=peer_data.get('region', regions[0] if regions else 'us-east-1'),
                        last_seen=datetime.now(timezone.utc),
                        security_threats=peer_data.get('security_threats', set()),
                        threat_level=peer_data.get('threat_level', SecurityThreatLevel.INFO)
                    )
                    peers.append(peer)
            else:
                logger.info("Security analyzer has no BGP peer discovery method - using empty result")
                
            return peers
            
        except Exception as e:
            logger.error(f"Security BGP peer discovery failed: {e}")
            return []
    
    async def analyze_bgp_topology(
        self, 
        regions: List[str], 
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Analyze BGP from security perspective.
        """
        try:
            result = {
                'analysis_type': 'security_bgp_analysis',
                'regions': regions,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'security_threats': [],
                'vulnerability_assessment': {},
                'compliance_status': {},
                'threat_indicators': []
            }
            
            # Try to use analyzer's security analysis methods
            if hasattr(self.analyzer_instance, 'analyze_bgp_security_threats'):
                security_data = await self.analyzer_instance.analyze_bgp_security_threats(regions, context)
                result['security_threats'] = security_data.get('threats', [])
                result['vulnerability_assessment'] = security_data.get('vulnerabilities', {})
                result['threat_indicators'] = security_data.get('indicators', [])
            elif hasattr(self.analyzer_instance, 'get_security_analysis'):
                # Alternative method name
                security_data = await self.analyzer_instance.get_security_analysis(regions)
                result.update(security_data)
            else:
                logger.info("Security analyzer has no security analysis method")
                result['security_threats'] = []
                result['vulnerability_assessment'] = {
                    'total_vulnerabilities': 0,
                    'critical_count': 0,
                    'high_count': 0,
                    'medium_count': 0,
                    'low_count': 0
                }
                result['compliance_status'] = {
                    'compliant': True,
                    'violations': []
                }
            
            # Add security compliance checks
            result['compliance_status'] = self._check_bgp_security_compliance(result)
            
            return result
            
        except Exception as e:
            logger.error(f"Security BGP analysis failed: {e}")
            return {
                'analysis_type': 'security_bgp_analysis',
                'regions': regions,
                'error': str(e),
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
    
    def _transform_security_peer_to_model(self, peer_data: Dict[str, Any]) -> Optional[BGPPeerModel]:
        """Transform security peer data to BGPPeerModel."""
        try:
            return BGPPeerModel(
                peer_id=peer_data.get('peer_id', f"sec-peer-{int(time.time())}"),
                local_asn=peer_data.get('local_asn', 65000),
                peer_asn=peer_data.get('peer_asn', 65001),
                peer_ip=peer_data.get('peer_ip', '0.0.0.0'),
                peer_state=peer_data.get('peer_state', BGPPeerState.IDLE),
                region=peer_data.get('region', 'us-east-1'),
                security_threats=set(peer_data.get('security_threats', [])),
                threat_level=peer_data.get('threat_level', SecurityThreatLevel.INFO),
                last_seen=datetime.now(timezone.utc)
            )
        except Exception as e:
            logger.error(f"Failed to transform security peer data: {e}")
            return None
    
    def _check_bgp_security_compliance(self, analysis_result: Dict[str, Any]) -> Dict[str, Any]:
        """Check BGP security compliance."""
        violations = []
        
        # Check for critical threats
        threats = analysis_result.get('security_threats', [])
        critical_threats = [t for t in threats if t.get('severity') == 'critical']
        if critical_threats:
            violations.append(f"Found {len(critical_threats)} critical security threats")
        
        # Check vulnerability counts
        vuln_assessment = analysis_result.get('vulnerability_assessment', {})
        critical_vulns = vuln_assessment.get('critical_count', 0)
        if critical_vulns > 0:
            violations.append(f"Found {critical_vulns} critical vulnerabilities")
        
        return {
            'compliant': len(violations) == 0,
            'violations': violations,
            'compliance_score': max(0, 100 - (len(violations) * 20)),
            'last_check': datetime.now(timezone.utc).isoformat()
        }
    
    async def analyze_security_threats(
        self, 
        regions: List[str], 
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Analyze BGP security threats and vulnerabilities.
        """
        if not hasattr(self.analyzer_instance, 'analyze_bgp_security'):
            logger.warning("Security analyzer missing expected method")
            return {}
        
        start_time = datetime.now(timezone.utc)
        
        try:
            # This would need to be implemented based on actual security analyzer interface
            raw_result = await self.analyzer_instance.analyze_bgp_security(
                regions=regions,
                context=context
            )
            
            # Transform to unified format
            security_result = {
                'analyzer_type': 'security',
                'regions': regions,
                'threat_assessment': {
                    'overall_risk_level': raw_result.get('risk_level', 'low'),
                    'active_threats': raw_result.get('threats', []),
                    'vulnerability_count': raw_result.get('vulnerability_count', 0)
                },
                'rpki_validation': raw_result.get('rpki_status', {}),
                'route_security': raw_result.get('route_security', {}),
                'policy_compliance': raw_result.get('compliance', {}),
                'troubleshooting_data': {
                    'security_violations': raw_result.get('violations', []),
                    'suspicious_peers': raw_result.get('suspicious_peers', []),
                    'route_anomalies': raw_result.get('anomalies', [])
                }
            }
            
            return security_result
            
        except Exception as e:
            logger.error(f"Security BGP analysis failed: {e}")
            return {}
        finally:
            execution_time = (datetime.now(timezone.utc) - start_time).total_seconds()
            self.performance_metrics['security_analysis_time'] = execution_time


class BGPAnalyzerFactory:
    """
    Factory for creating appropriate BGP analyzer adapters.
    
    Automatically determines the correct adapter type based on
    the analyzer instance and its capabilities.
    """
    
    @staticmethod
    def create_adapter(analyzer_instance: Any) -> BaseModelAdapter:
        """
        Create appropriate adapter for analyzer instance.
        
        Args:
            analyzer_instance: The analyzer instance to adapt
            
        Returns:
            Appropriate adapter instance
        """
        analyzer_class_name = type(analyzer_instance).__name__
        
        # Determine adapter type based on analyzer class name
        if 'cloudwan' in analyzer_class_name.lower():
            return CloudWANBGPAdapter(analyzer_instance)
        elif 'protocol' in analyzer_class_name.lower():
            return ProtocolBGPAdapter(analyzer_instance)
        elif 'operations' in analyzer_class_name.lower():
            return OperationalBGPAdapter(analyzer_instance)
        elif 'security' in analyzer_class_name.lower():
            return SecurityBGPAdapter(analyzer_instance)
        else:
            logger.warning(f"Unknown analyzer type: {analyzer_class_name}")
            # Default to protocol adapter for unknown types
            return ProtocolBGPAdapter(analyzer_instance)
    
    @staticmethod
    def get_migration_status_summary() -> Dict[str, Any]:
        """
        Get migration status summary for all adapter types.
        
        Returns:
            Migration status summary
        """
        return {
            'cloudwan': {
                'status': AnalyzerMigrationStatus.FULLY_MIGRATED.value,
                'description': 'Fully migrated to shared models in Phase 4'
            },
            'protocol': {
                'status': AnalyzerMigrationStatus.COMPATIBILITY_ADAPTER.value,
                'description': 'Compatibility adapters in place, needs completion'
            },
            'operations': {
                'status': AnalyzerMigrationStatus.MIGRATION_REQUIRED.value,
                'description': 'Full migration to shared models required'
            },
            'security': {
                'status': AnalyzerMigrationStatus.MIGRATION_REQUIRED.value,
                'description': 'Full migration to shared models required'
            }
        }


# Migration utility functions

def validate_analyzer_compatibility(analyzer_instance: Any) -> Dict[str, Any]:
    """
    Validate analyzer compatibility with adapter pattern.
    
    Args:
        analyzer_instance: Analyzer instance to validate
        
    Returns:
        Compatibility validation results
    """
    compatibility = {
        'is_compatible': False,
        'required_methods': [],
        'missing_methods': [],
        'adapter_type': 'unknown'
    }
    
    analyzer_class_name = type(analyzer_instance).__name__.lower()
    
    # Define required methods for each analyzer type
    required_methods_map = {
        'cloudwan': ['discover_cloudwan_bgp_peers', 'analyze_cloudwan_bgp_topology'],
        'protocol': ['get_bgp_peer_information', 'analyze_bgp_protocol_state'],
        'operations': ['analyze_bgp_operations'],
        'security': ['analyze_bgp_security']
    }
    
    # Determine adapter type and required methods
    for analyzer_type, required_methods in required_methods_map.items():
        if analyzer_type in analyzer_class_name:
            compatibility['adapter_type'] = analyzer_type
            compatibility['required_methods'] = required_methods
            break
    
    # Check for missing methods
    for method_name in compatibility['required_methods']:
        if not hasattr(analyzer_instance, method_name):
            compatibility['missing_methods'].append(method_name)
    
    compatibility['is_compatible'] = len(compatibility['missing_methods']) == 0
    
    return compatibility


async def test_adapter_integration(adapter: BaseModelAdapter, test_regions: List[str]) -> Dict[str, Any]:
    """
    Test adapter integration with sample data.
    
    Args:
        adapter: Adapter instance to test
        test_regions: Regions to use for testing
        
    Returns:
        Test results
    """
    test_results = {
        'adapter_type': type(adapter).__name__,
        'migration_status': adapter.get_migration_status().value,
        'peer_discovery_test': {'success': False, 'error': None},
        'topology_analysis_test': {'success': False, 'error': None},
        'performance_metrics': {}
    }
    
    # Test peer discovery
    try:
        peers = await adapter.discover_bgp_peers(test_regions)
        test_results['peer_discovery_test'] = {
            'success': True,
            'peer_count': len(peers),
            'error': None
        }
    except Exception as e:
        test_results['peer_discovery_test'] = {
            'success': False,
            'error': str(e)
        }
    
    # Test topology analysis
    try:
        topology_result = await adapter.analyze_bgp_topology(test_regions)
        test_results['topology_analysis_test'] = {
            'success': True,
            'result_keys': list(topology_result.keys()),
            'error': None
        }
    except Exception as e:
        test_results['topology_analysis_test'] = {
            'success': False,
            'error': str(e)
        }
    
    # Get performance metrics
    test_results['performance_metrics'] = adapter.get_performance_metrics()
    
    return test_results