"""
BGP Integration Manager for CloudWAN MCP Server.

This module implements the central coordinator for all BGP analyzers, providing
a unified interface for comprehensive BGP analysis and troubleshooting workflows.
Based on the DeepSeek R1 multi-agent architectural design.

Key Features:
- Unified BGP analysis coordinating all four analyzers
- Comprehensive troubleshooting workflows for network operations
- ASN relationship management with hierarchy modeling
- Session state correlation with network topology
- Multi-region BGP intelligence aggregation
- Performance optimization for large-scale operations

Integration Components:
- CloudWAN BGP Analyzer (fully migrated)
- BGP Protocol Analyzer (compatibility layer)
- BGP Operations Analyzer (migration required)
- BGP Security Analyzer (migration required)
"""

import asyncio
import logging
import time
import re
import ipaddress
import random
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple
from enum import Enum
from uuid import uuid4
from collections import deque
from dataclasses import dataclass, field
from functools import wraps

from pydantic import BaseModel, Field, ConfigDict

from .topology import NetworkTopology
from .bgp_topology import BGPTopologyModel, BGPPeerModel
from ..shared.base import EnhancedBaseResponse, PerformanceMetrics
from ..shared.enums import (
    BGPPeerState, SecurityThreatLevel, 
    NetworkElementType, HealthStatus
)
from ..shared.exceptions import (
    ValidationError
)

logger = logging.getLogger(__name__)


# Security Components

class RateLimiter:
    """Rate limiter to prevent abuse of BGP analysis operations."""
    
    def __init__(self, max_requests: int = 100, time_window: int = 3600):
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests: deque = deque()
        
    def is_allowed(self, client_id: str = "default") -> bool:
        """Check if request is allowed under rate limits."""
        current_time = time.time()
        
        # Remove old requests outside time window
        while self.requests and self.requests[0] < current_time - self.time_window:
            self.requests.popleft()
        
        # Check if under limit
        if len(self.requests) < self.max_requests:
            self.requests.append(current_time)
            return True
        
        logger.warning(f"Rate limit exceeded for client {client_id}")
        return False


class InputValidator:
    """Input validation for BGP integration operations."""
    
    @staticmethod
    def validate_regions(regions: List[str]) -> List[str]:
        """Validate and sanitize AWS region names."""
        if not regions:
            return []
        
        # AWS region pattern: us-east-1, eu-west-1, etc.
        region_pattern = re.compile(r'^[a-z]{2}-[a-z]+-\d+$|^us-gov-[a-z]+-\d+$|^cn-[a-z]+-\d+$')
        
        validated_regions = []
        for region in regions[:10]:  # Limit to 10 regions max
            if isinstance(region, str) and region_pattern.match(region.lower()):
                validated_regions.append(region.lower())
            else:
                logger.warning(f"Invalid region format rejected: {region}")
        
        return validated_regions
    
    @staticmethod
    def validate_asn(asn: int) -> bool:
        """Validate ASN is in acceptable range."""
        # Valid ASN ranges: 1-23455, 23457-64495, 131072-4199999999
        return (1 <= asn <= 23455) or (23457 <= asn <= 64495) or (131072 <= asn <= 4199999999)
    
    @staticmethod
    def validate_ip_address(ip: str) -> bool:
        """Validate IP address format."""
        try:
            ipaddress.ip_address(ip)
            return True
        except ValueError:
            return False
    
    @staticmethod
    def sanitize_string(value: str, max_length: int = 255) -> str:
        """Sanitize string input to prevent injection attacks."""
        if not isinstance(value, str):
            return ""
        
        # Remove potentially dangerous characters
        sanitized = re.sub(r'[<>"\';]', '', value)
        
        # Limit length
        return sanitized[:max_length]
    
    @staticmethod
    def validate_troubleshooting_context(context: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Validate and sanitize troubleshooting context."""
        if not context:
            return {}
        
        validated_context = {}
        
        # Limit context size
        if len(str(context)) > 10000:  # 10KB limit
            logger.warning("Troubleshooting context too large, truncating")
            return {}
        
        # Validate known safe fields
        safe_fields = {
            'incident_id', 'severity', 'reporter', 'description',
            'affected_services', 'regions', 'start_time', 'end_time'
        }
        
        for key, value in context.items():
            if key in safe_fields:
                if isinstance(value, str):
                    validated_context[key] = InputValidator.sanitize_string(value)
                elif isinstance(value, list) and all(isinstance(v, str) for v in value):
                    validated_context[key] = [InputValidator.sanitize_string(v) for v in value[:10]]
                elif key in ['start_time', 'end_time'] and isinstance(value, (int, float)):
                    validated_context[key] = value
        
        return validated_context


class SecurityEnforcer:
    """Security enforcement for BGP integration operations."""
    
    def __init__(self):
        self.rate_limiter = RateLimiter(max_requests=50, time_window=3600)  # 50 requests per hour
        self.validator = InputValidator()
        
    def enforce_security(self, operation: str, **kwargs) -> Dict[str, Any]:
        """Enforce security policies for operations."""
        # Rate limiting
        if not self.rate_limiter.is_allowed(operation):
            raise SecurityError(f"Rate limit exceeded for operation: {operation}")
        
        # Input validation
        validated_kwargs = {}
        
        if 'regions' in kwargs:
            validated_kwargs['regions'] = self.validator.validate_regions(kwargs['regions'])
        
        if 'troubleshooting_context' in kwargs:
            validated_kwargs['troubleshooting_context'] = self.validator.validate_troubleshooting_context(
                kwargs['troubleshooting_context']
            )
        
        # Sanitize string parameters
        for key, value in kwargs.items():
            if key not in validated_kwargs:
                if isinstance(value, str):
                    validated_kwargs[key] = self.validator.sanitize_string(value)
                elif isinstance(value, (int, float, bool, type(None))):
                    validated_kwargs[key] = value
                else:
                    # For complex types, validate they're not dangerous
                    if len(str(value)) < 1000:  # Basic size check
                        validated_kwargs[key] = value
        
        return validated_kwargs


class SecurityError(Exception):
    """Security-related error in BGP integration operations."""
    pass


# Error Recovery and Retry Logic Components

class RetryConfig:
    """Configuration for retry logic."""
    
    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_backoff: bool = True,
        jitter: bool = True
    ):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_backoff = exponential_backoff
        self.jitter = jitter
    
    def get_delay(self, attempt: int) -> float:
        """Calculate delay for retry attempt."""
        if self.exponential_backoff:
            delay = self.base_delay * (2 ** attempt)
        else:
            delay = self.base_delay
        
        # Apply max delay limit
        delay = min(delay, self.max_delay)
        
        # Add jitter to prevent thundering herd
        if self.jitter:
            delay = delay * (0.5 + random.random() * 0.5)
        
        return delay


class CircuitBreaker:
    """Circuit breaker to prevent cascading failures."""
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        success_threshold: int = 2
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.success_threshold = success_threshold
        
        # State tracking
        self.state = "closed"  # closed, open, half-open
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: Optional[float] = None
        
    def is_open(self) -> bool:
        """Check if circuit breaker is open."""
        return self.state == "open"
    
    def should_attempt_reset(self) -> bool:
        """Check if we should attempt to reset the circuit breaker."""
        if (self.state == "open" and self.last_failure_time and
            time.time() - self.last_failure_time > self.recovery_timeout):
            return True
        return False
    
    def record_success(self):
        """Record a successful operation."""
        if self.state == "half-open":
            self.success_count += 1
            if self.success_count >= self.success_threshold:
                self.state = "closed"
                self.failure_count = 0
                self.success_count = 0
                logger.info("Circuit breaker reset to closed state")
        elif self.state == "closed":
            self.failure_count = max(0, self.failure_count - 1)
    
    def record_failure(self):
        """Record a failed operation."""
        self.failure_count += 1
        self.last_failure_time = time.time()
        self.success_count = 0
        
        if self.failure_count >= self.failure_threshold:
            self.state = "open"
            logger.warning(f"Circuit breaker opened after {self.failure_count} failures")
    
    def attempt_reset(self):
        """Attempt to reset circuit breaker to half-open state."""
        if self.should_attempt_reset():
            self.state = "half-open"
            self.success_count = 0
            logger.info("Circuit breaker set to half-open state")


def retry_with_backoff(
    retry_config: Optional[RetryConfig] = None,
    retryable_exceptions: Tuple[Exception, ...] = (Exception,)
):
    """Decorator for retry logic with exponential backoff."""
    
    if retry_config is None:
        retry_config = RetryConfig()
    
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(retry_config.max_retries + 1):
                try:
                    result = await func(*args, **kwargs)
                    if attempt > 0:
                        logger.info(f"Operation {func.__name__} succeeded on retry attempt {attempt}")
                    return result
                    
                except retryable_exceptions as e:
                    last_exception = e
                    
                    if attempt == retry_config.max_retries:
                        logger.error(f"Operation {func.__name__} failed after {retry_config.max_retries} retries: {e}")
                        break
                    
                    delay = retry_config.get_delay(attempt)
                    logger.warning(
                        f"Operation {func.__name__} failed (attempt {attempt + 1}/{retry_config.max_retries + 1}): {e}. "
                        f"Retrying in {delay:.2f}s"
                    )
                    await asyncio.sleep(delay)
                
                except Exception as e:
                    # Non-retryable exception
                    logger.error(f"Non-retryable error in {func.__name__}: {e}")
                    raise
            
            # All retries exhausted
            raise last_exception
        
        return wrapper
    return decorator


class ErrorRecoveryManager:
    """Manager for error recovery strategies."""
    
    def __init__(self):
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        self.retry_configs: Dict[str, RetryConfig] = {}
        
        # Default configurations
        self.retry_configs['default'] = RetryConfig(max_retries=3, base_delay=1.0)
        self.retry_configs['analyzer_call'] = RetryConfig(max_retries=2, base_delay=2.0)
        self.retry_configs['network_operation'] = RetryConfig(max_retries=5, base_delay=0.5)
    
    def get_circuit_breaker(self, operation: str) -> CircuitBreaker:
        """Get or create circuit breaker for operation."""
        if operation not in self.circuit_breakers:
            self.circuit_breakers[operation] = CircuitBreaker()
        return self.circuit_breakers[operation]
    
    def get_retry_config(self, operation_type: str) -> RetryConfig:
        """Get retry configuration for operation type."""
        return self.retry_configs.get(operation_type, self.retry_configs['default'])
    
    async def execute_with_recovery(
        self,
        operation: str,
        func: callable,
        *args,
        operation_type: str = 'default',
        **kwargs
    ):
        """Execute operation with full error recovery."""
        circuit_breaker = self.get_circuit_breaker(operation)
        
        # Check circuit breaker
        if circuit_breaker.is_open():
            if circuit_breaker.should_attempt_reset():
                circuit_breaker.attempt_reset()
            else:
                raise CircuitBreakerError(f"Circuit breaker is open for operation: {operation}")
        
        retry_config = self.get_retry_config(operation_type)
        
        try:
            # Execute with retry logic
            @retry_with_backoff(retry_config, (ConnectionError, TimeoutError, asyncio.TimeoutError))
            async def execute():
                return await func(*args, **kwargs)
            
            result = await execute()
            circuit_breaker.record_success()
            return result
            
        except Exception:
            circuit_breaker.record_failure()
            raise


class CircuitBreakerError(Exception):
    """Error raised when circuit breaker is open."""
    pass


class ASNRelationshipType(str, Enum):
    """ASN relationship types for hierarchy modeling."""
    PROVIDER = "provider"
    CUSTOMER = "customer"
    PEER = "peer"
    SIBLING = "sibling"
    TRANSIT = "transit"
    UNKNOWN = "unknown"


class BGPAnalysisScope(str, Enum):
    """Scope of BGP analysis for troubleshooting workflows."""
    COMPREHENSIVE = "comprehensive"
    PROTOCOL_ONLY = "protocol_only"
    SECURITY_ONLY = "security_only"
    OPERATIONS_ONLY = "operations_only"
    CLOUDWAN_ONLY = "cloudwan_only"
    TROUBLESHOOTING = "troubleshooting"


class BGPTroubleshootingScenario(str, Enum):
    """Common BGP troubleshooting scenarios."""
    PEER_DOWN = "peer_down"
    ROUTE_LEAKAGE = "route_leakage"
    HIJACKING = "hijacking"
    PERFORMANCE_DEGRADATION = "performance_degradation"
    CONFIGURATION_MISMATCH = "configuration_mismatch"
    POLICY_VIOLATION = "policy_violation"
    CONNECTIVITY_ISSUE = "connectivity_issue"
    SECURITY_INCIDENT = "security_incident"


@dataclass
class ASNHierarchyInfo:
    """Enhanced ASN relationship modeling for hierarchy analysis."""
    asn: int
    relationship_type: ASNRelationshipType
    parent_asns: Set[int] = field(default_factory=set)
    child_asns: Set[int] = field(default_factory=set)
    peer_asns: Set[int] = field(default_factory=set)
    hierarchy_level: int = 0
    business_relationship: Dict[str, Any] = field(default_factory=dict)
    routing_policies: List[Dict[str, Any]] = field(default_factory=list)
    regional_presence: List[str] = field(default_factory=list)
    trust_score: float = 0.0


@dataclass
class NetworkElementCorrelation:
    """Correlation between BGP peers and network elements."""
    bgp_peer_id: str
    network_element_id: str
    element_type: NetworkElementType
    correlation_confidence: float
    last_updated: datetime
    health_correlation: bool = False
    performance_correlation: bool = False
    security_correlation: bool = False


class NetworkTopologyIntegration(BaseModel):
    """Integration metadata between BGP and network topology."""
    
    model_config = ConfigDict(
        extra="allow",
        validate_assignment=True,
        use_enum_values=True
    )
    
    network_topology_id: str = Field(
        description="Network topology identifier"
    )
    bgp_topology_id: str = Field(
        description="BGP topology identifier"
    )
    last_sync_timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Last synchronization timestamp"
    )
    asn_correlation_map: Dict[int, str] = Field(
        default_factory=dict,
        description="ASN to NetworkElement ID mapping"
    )
    peer_correlation_map: Dict[str, str] = Field(
        default_factory=dict,
        description="BGP Peer ID to NetworkElement ID mapping"
    )
    integration_health_score: float = Field(
        default=0.0,
        description="Integration health score (0.0-1.0)"
    )
    sync_conflicts: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Synchronization conflicts"
    )


class BGPTopologyAnalysisResult(EnhancedBaseResponse):
    """Comprehensive BGP analysis result from all analyzers."""
    
    # Analysis results from each analyzer
    protocol_analysis: Optional[Dict[str, Any]] = Field(
        default=None,
        description="BGP protocol analysis results"
    )
    cloudwan_analysis: Optional[Dict[str, Any]] = Field(
        default=None,
        description="CloudWAN BGP integration results"
    )
    operations_analysis: Optional[Dict[str, Any]] = Field(
        default=None,
        description="BGP operations monitoring results"
    )
    security_analysis: Optional[Dict[str, Any]] = Field(
        default=None,
        description="BGP security assessment results"
    )
    
    # Unified topology representation
    unified_bgp_topology: Optional[BGPTopologyModel] = Field(
        default=None,
        description="Unified BGP topology model"
    )
    
    # Integration metadata
    network_topology_integration: Optional[NetworkTopologyIntegration] = Field(
        default=None,
        description="Network topology integration metadata"
    )
    analysis_correlation_id: str = Field(
        default_factory=lambda: str(uuid4()),
        description="Analysis correlation identifier"
    )
    multi_region_insights: Dict[str, Any] = Field(
        default_factory=dict,
        description="Multi-region analysis insights"
    )
    
    # Troubleshooting context
    troubleshooting_scenarios: List[BGPTroubleshootingScenario] = Field(
        default_factory=list,
        description="Identified troubleshooting scenarios"
    )
    recommended_actions: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Recommended troubleshooting actions"
    )
    severity_assessment: SecurityThreatLevel = Field(
        default=SecurityThreatLevel.LOW,
        description="Overall severity assessment"
    )


class BGPIntegrationManager:
    """
    Central coordinator for all BGP analyzers with shared model integration.
    
    This class provides a unified interface for comprehensive BGP analysis,
    troubleshooting workflows, and network operations support. It coordinates
    between all four BGP analyzers and integrates with the network topology
    framework for holistic network intelligence.
    """
    
    def __init__(self, network_topology: NetworkTopology):
        """
        Initialize BGP Integration Manager.
        
        Args:
            network_topology: Network topology instance for integration
        """
        self.network_topology = network_topology
        self.bgp_topology = BGPTopologyModel()
        self.asn_hierarchy: Dict[int, ASNHierarchyInfo] = {}
        self.session_correlations: Dict[str, NetworkElementCorrelation] = {}
        self.integration_metadata = NetworkTopologyIntegration(
            network_topology_id=network_topology.topology_id,
            bgp_topology_id=self.bgp_topology.topology_id
        )
        
        # Initialize analyzer references (will be populated by dependency injection)
        self.analyzers = {
            'cloudwan': None,      # CloudWANBGPAnalyzer (already migrated)
            'protocol': None,      # BGPProtocolAnalyzer (needs completion)
            'operations': None,    # BGPOperationsAnalyzer (needs migration)
            'security': None       # BGPSecurityAnalyzer (needs migration)
        }
        
        # Performance metrics
        self.performance_metrics = PerformanceMetrics()
        
        # Security enforcement
        self.security_enforcer = SecurityEnforcer()
        
        # Error recovery management
        self.error_recovery_manager = ErrorRecoveryManager()
        
        logger.info(
            f"BGP Integration Manager initialized for topology {network_topology.topology_id}"
        )
    
    def register_analyzer(self, analyzer_type: str, analyzer_instance: Any) -> None:
        """
        Register a BGP analyzer instance.
        
        Args:
            analyzer_type: Type of analyzer ('cloudwan', 'protocol', 'operations', 'security')
            analyzer_instance: Analyzer instance to register
        """
        if analyzer_type not in self.analyzers:
            raise ValueError(f"Unknown analyzer type: {analyzer_type}")
        
        self.analyzers[analyzer_type] = analyzer_instance
        logger.info(f"Registered {analyzer_type} BGP analyzer")
    
    async def analyze_comprehensive_bgp_topology(
        self,
        regions: List[str],
        analysis_scope: BGPAnalysisScope = BGPAnalysisScope.COMPREHENSIVE,
        include_security_analysis: bool = True,
        include_operational_metrics: bool = True,
        include_cloudwan_integration: bool = True,
        troubleshooting_context: Optional[Dict[str, Any]] = None
    ) -> BGPTopologyAnalysisResult:
        """
        Perform comprehensive BGP topology analysis using all available analyzers.
        
        This is the primary method for network troubleshooting workflows, providing
        unified analysis across all BGP domains with integrated network topology context.
        
        Args:
            regions: List of AWS regions to analyze
            analysis_scope: Scope of analysis to perform
            include_security_analysis: Include security threat assessment
            include_operational_metrics: Include operational monitoring
            include_cloudwan_integration: Include CloudWAN integration analysis
            troubleshooting_context: Additional context for troubleshooting
            
        Returns:
            Comprehensive BGP analysis result
        """
        start_time = datetime.now(timezone.utc)
        correlation_id = str(uuid4())
        
        # Security enforcement - validate and sanitize inputs
        try:
            validated_params = self.security_enforcer.enforce_security(
                'analyze_comprehensive_bgp_topology',
                regions=regions,
                troubleshooting_context=troubleshooting_context
            )
            regions = validated_params.get('regions', [])
            troubleshooting_context = validated_params.get('troubleshooting_context', {})
        except SecurityError as e:
            logger.error(f"Security enforcement failed: {e}")
            raise ValidationError(f"Invalid input parameters: {e}")
        
        # Validate regions not empty after security checks
        if not regions:
            raise ValidationError("At least one valid region must be specified")
        
        logger.info(
            f"Starting comprehensive BGP analysis [correlation_id={correlation_id}] "
            f"for regions: {regions}, scope: {analysis_scope}"
        )
        
        result = BGPTopologyAnalysisResult(
            analysis_correlation_id=correlation_id,
            regions=regions,
            analysis_type="comprehensive_bgp_topology"
        )
        
        # Parallel analysis execution
        analysis_tasks = []
        
        # CloudWAN BGP Analysis (if available and requested)
        if (self.analyzers['cloudwan'] and 
            analysis_scope in [BGPAnalysisScope.COMPREHENSIVE, BGPAnalysisScope.CLOUDWAN_ONLY]):
            analysis_tasks.append(
                self._analyze_cloudwan_bgp(regions, troubleshooting_context)
            )
        
        # Protocol Analysis (if available and requested)
        if (self.analyzers['protocol'] and 
            analysis_scope in [BGPAnalysisScope.COMPREHENSIVE, BGPAnalysisScope.PROTOCOL_ONLY]):
            analysis_tasks.append(
                self._analyze_protocol_bgp(regions, troubleshooting_context)
            )
        
        # Operations Analysis (if available and requested)
        if (self.analyzers['operations'] and include_operational_metrics and
            analysis_scope in [BGPAnalysisScope.COMPREHENSIVE, BGPAnalysisScope.OPERATIONS_ONLY]):
            analysis_tasks.append(
                self._analyze_operations_bgp(regions, troubleshooting_context)
            )
        
        # Security Analysis (if available and requested)
        if (self.analyzers['security'] and include_security_analysis and
            analysis_scope in [BGPAnalysisScope.COMPREHENSIVE, BGPAnalysisScope.SECURITY_ONLY]):
            analysis_tasks.append(
                self._analyze_security_bgp(regions, troubleshooting_context)
            )
        
        # Execute all analysis tasks in parallel
        if analysis_tasks:
            analysis_results = await asyncio.gather(*analysis_tasks, return_exceptions=True)
            
            # Process results from each analyzer
            for i, analyzer_result in enumerate(analysis_results):
                if isinstance(analyzer_result, Exception):
                    logger.error(f"Analyzer {i} failed: {analyzer_result}")
                    continue
                
                # Merge results based on analyzer type
                if i == 0 and self.analyzers['cloudwan']:  # CloudWAN
                    result.cloudwan_analysis = analyzer_result
                elif i == 1 and self.analyzers['protocol']:  # Protocol
                    result.protocol_analysis = analyzer_result
                elif i == 2 and self.analyzers['operations']:  # Operations
                    result.operations_analysis = analyzer_result
                elif i == 3 and self.analyzers['security']:  # Security
                    result.security_analysis = analyzer_result
        
        # Unified topology creation
        await self._create_unified_topology(result)
        
        # Network topology integration
        await self._integrate_with_network_topology(result)
        
        # Multi-region insights
        await self._generate_multi_region_insights(result, regions)
        
        # Troubleshooting analysis
        await self._analyze_troubleshooting_scenarios(result, troubleshooting_context)
        
        # Performance metrics
        execution_time = (datetime.now(timezone.utc) - start_time).total_seconds()
        self.performance_metrics.add_measurement("comprehensive_analysis_time", execution_time)
        
        result.execution_time_seconds = execution_time
        result.success = True
        
        logger.info(
            f"Comprehensive BGP analysis completed [correlation_id={correlation_id}] "
            f"in {execution_time:.2f}s"
        )
        
        return result
    
    async def discover_bgp_peers_unified(
        self,
        regions: List[str],
        include_inactive: bool = False,
        filter_by_asn: Optional[List[int]] = None
    ) -> List[BGPPeerModel]:
        """
        Unified BGP peer discovery across all analyzers.
        
        Args:
            regions: List of regions to discover peers in
            include_inactive: Include inactive/down peers
            filter_by_asn: Filter peers by specific ASNs
            
        Returns:
            List of discovered BGP peers
        """
        logger.info(f"Starting unified BGP peer discovery for regions: {regions}")
        
        all_peers = []
        discovery_tasks = []
        
        # Collect peers from all available analyzers
        for analyzer_type, analyzer in self.analyzers.items():
            if analyzer and hasattr(analyzer, 'discover_bgp_peers'):
                discovery_tasks.append(
                    self._discover_peers_from_analyzer(
                        analyzer, analyzer_type, regions, include_inactive, filter_by_asn
                    )
                )
        
        if discovery_tasks:
            peer_results = await asyncio.gather(*discovery_tasks, return_exceptions=True)
            
            # Merge and deduplicate peers
            peer_map = {}
            for result in peer_results:
                if isinstance(result, Exception):
                    logger.error(f"Peer discovery failed: {result}")
                    continue
                
                for peer in result:
                    peer_key = f"{peer.peer_ip}:{peer.peer_asn}"
                    if peer_key not in peer_map:
                        peer_map[peer_key] = peer
                    else:
                        # Merge peer information
                        peer_map[peer_key] = self._merge_peer_information(
                            peer_map[peer_key], peer
                        )
            
            all_peers = list(peer_map.values())
        
        # Update session correlations
        await self._update_session_correlations(all_peers)
        
        logger.info(f"Discovered {len(all_peers)} unified BGP peers")
        return all_peers
    
    async def get_troubleshooting_recommendations(
        self,
        scenario: BGPTroubleshootingScenario,
        context: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Get troubleshooting recommendations for specific BGP scenarios.
        
        Args:
            scenario: Troubleshooting scenario type
            context: Additional context for recommendations
            
        Returns:
            List of recommended troubleshooting actions
        """
        recommendations = []
        
        if scenario == BGPTroubleshootingScenario.PEER_DOWN:
            recommendations.extend([
                {
                    "action": "check_peer_connectivity",
                    "description": "Verify network connectivity to BGP peer",
                    "priority": "high",
                    "analyzer": "protocol"
                },
                {
                    "action": "check_cloudwan_attachment",
                    "description": "Verify CloudWAN attachment state",
                    "priority": "high",
                    "analyzer": "cloudwan"
                },
                {
                    "action": "review_security_policies",
                    "description": "Check for security policy blocks",
                    "priority": "medium",
                    "analyzer": "security"
                }
            ])
        
        elif scenario == BGPTroubleshootingScenario.ROUTE_LEAKAGE:
            recommendations.extend([
                {
                    "action": "analyze_route_propagation",
                    "description": "Analyze route propagation patterns",
                    "priority": "critical",
                    "analyzer": "security"
                },
                {
                    "action": "check_routing_policies",
                    "description": "Verify routing policy configuration",
                    "priority": "high",
                    "analyzer": "operations"
                }
            ])
        
        elif scenario == BGPTroubleshootingScenario.PERFORMANCE_DEGRADATION:
            recommendations.extend([
                {
                    "action": "check_peer_performance",
                    "description": "Analyze peer performance metrics",
                    "priority": "high",
                    "analyzer": "operations"
                },
                {
                    "action": "verify_cloudwan_optimization",
                    "description": "Check CloudWAN optimization settings",
                    "priority": "medium",
                    "analyzer": "cloudwan"
                }
            ])
        
        # Add context-specific recommendations
        if context.get("affected_peers"):
            recommendations.append({
                "action": "isolate_affected_peers",
                "description": f"Focus analysis on peers: {context['affected_peers']}",
                "priority": "high",
                "analyzer": "comprehensive"
            })
        
        return recommendations
    
    async def sync_with_network_topology(self) -> None:
        """
        Perform bidirectional synchronization between BGP and network topology.
        """
        logger.info("Starting BGP-Network topology synchronization")
        
        try:
            # Sync ASN relationships
            await self._sync_asn_relationships()
            
            # Sync peer correlations
            await self._sync_peer_correlations()
            
            # Update integration metadata
            self.integration_metadata.last_sync_timestamp = datetime.now(timezone.utc)
            self.integration_metadata.integration_health_score = await self._calculate_integration_health()
            
            logger.info("BGP-Network topology synchronization completed")
            
        except Exception as e:
            logger.error(f"BGP-Network topology synchronization failed: {e}")
            raise
    
    # Private helper methods
    
    async def _analyze_cloudwan_bgp(
        self, 
        regions: List[str], 
        context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Analyze BGP through CloudWAN analyzer with error recovery."""
        if not self.analyzers['cloudwan']:
            return {}
        
        analyzer = self.analyzers['cloudwan']
        
        # Assuming the analyzer has a method for comprehensive analysis
        if hasattr(analyzer, 'analyze_bgp_topology'):
            try:
                return await self.error_recovery_manager.execute_with_recovery(
                    'cloudwan_bgp_analysis',
                    analyzer.analyze_bgp_topology,
                    regions=regions,
                    context=context,
                    operation_type='analyzer_call'
                )
            except CircuitBreakerError as e:
                logger.warning(f"CloudWAN analyzer circuit breaker open: {e}")
                return {'error': 'CloudWAN analyzer temporarily unavailable'}
            except Exception as e:
                logger.error(f"CloudWAN BGP analysis failed: {e}")
                return {'error': str(e)}
        else:
            logger.warning("CloudWAN analyzer missing analyze_bgp_topology method")
            return {}
    
    async def _analyze_protocol_bgp(
        self, 
        regions: List[str], 
        context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Analyze BGP through protocol analyzer."""
        if not self.analyzers['protocol']:
            return {}
        
        # Call BGP Protocol analyzer
        analyzer = self.analyzers['protocol']
        
        # Assuming the analyzer has a method for protocol analysis
        if hasattr(analyzer, 'analyze_protocol_state'):
            return await analyzer.analyze_protocol_state(regions=regions, context=context)
        else:
            logger.warning("Protocol analyzer missing analyze_protocol_state method")
            return {}
    
    async def _analyze_operations_bgp(
        self, 
        regions: List[str], 
        context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Analyze BGP through operations analyzer."""
        if not self.analyzers['operations']:
            return {}
        
        # Call BGP Operations analyzer
        analyzer = self.analyzers['operations']
        
        # Assuming the analyzer has a method for operations analysis
        if hasattr(analyzer, 'analyze_operational_state'):
            return await analyzer.analyze_operational_state(regions=regions, context=context)
        else:
            logger.warning("Operations analyzer missing analyze_operational_state method")
            return {}
    
    async def _analyze_security_bgp(
        self, 
        regions: List[str], 
        context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Analyze BGP through security analyzer."""
        if not self.analyzers['security']:
            return {}
        
        # Call BGP Security analyzer
        analyzer = self.analyzers['security']
        
        # Assuming the analyzer has a method for security analysis
        if hasattr(analyzer, 'analyze_security_threats'):
            return await analyzer.analyze_security_threats(regions=regions, context=context)
        else:
            logger.warning("Security analyzer missing analyze_security_threats method")
            return {}
    
    async def _create_unified_topology(self, result: BGPTopologyAnalysisResult) -> None:
        """Create unified BGP topology from all analyzer results."""
        try:
            # Merge BGP topology data from all analyzers
            merged_peers = {}
            merged_routes = {}
            
            # Collect peers from all analyzers
            for analyzer_type, analyzer in self.analyzers.items():
                if analyzer:
                    try:
                        # Get peers from each analyzer
                        analyzer_peers = getattr(analyzer, 'peers', {})
                        for peer_id, peer in analyzer_peers.items():
                            if peer_id in merged_peers:
                                # Merge peer information
                                merged_peers[peer_id] = self._merge_peer_information(merged_peers[peer_id], peer)
                            else:
                                merged_peers[peer_id] = peer
                        
                        # Get routes from each analyzer
                        analyzer_routes = getattr(analyzer, 'routes', {})
                        for route_id, route in analyzer_routes.items():
                            if route_id not in merged_routes:
                                merged_routes[route_id] = route
                    except Exception as e:
                        logger.warning(f"Failed to merge data from {analyzer_type} analyzer: {e}")
            
            # Update BGP topology with merged data
            self.bgp_topology.peers.update(merged_peers)
            self.bgp_topology.routes.update(merged_routes)
            
            # Update result with unified topology
            result.bgp_topology = self.bgp_topology
            
            logger.info(f"Created unified topology with {len(merged_peers)} peers and {len(merged_routes)} routes")
            
        except Exception as e:
            logger.error(f"Failed to create unified topology: {e}")
            raise
    
    async def _integrate_with_network_topology(self, result: BGPTopologyAnalysisResult) -> None:
        """Integrate BGP analysis with network topology."""
        result.network_topology_integration = self.integration_metadata
    
    async def _generate_multi_region_insights(
        self, 
        result: BGPTopologyAnalysisResult, 
        regions: List[str]
    ) -> None:
        """Generate multi-region insights."""
        result.multi_region_insights = {
            "analyzed_regions": regions,
            "cross_region_connections": [],
            "regional_performance": {},
            "regional_security_status": {}
        }
    
    async def _analyze_troubleshooting_scenarios(
        self, 
        result: BGPTopologyAnalysisResult,
        context: Optional[Dict[str, Any]]
    ) -> None:
        """Analyze and identify troubleshooting scenarios."""
        scenarios = []
        
        # Analyze for common troubleshooting scenarios
        if result.security_analysis and result.security_analysis.get('threats'):
            scenarios.append(BGPTroubleshootingScenario.SECURITY_INCIDENT)
        
        if result.operations_analysis and result.operations_analysis.get('degraded_peers'):
            scenarios.append(BGPTroubleshootingScenario.PERFORMANCE_DEGRADATION)
        
        result.troubleshooting_scenarios = scenarios
        
        # Generate recommendations for identified scenarios
        for scenario in scenarios:
            recommendations = await self.get_troubleshooting_recommendations(scenario, context or {})
            result.recommended_actions.extend(recommendations)
    
    async def _discover_peers_from_analyzer(
        self,
        analyzer: Any,
        analyzer_type: str,
        regions: List[str],
        include_inactive: bool,
        filter_by_asn: Optional[List[int]]
    ) -> List[BGPPeerModel]:
        """Discover peers from specific analyzer."""
        # Implementation would depend on each analyzer's interface
        # This is a placeholder for the actual implementation
        return []
    
    def _merge_peer_information(self, peer1: BGPPeerModel, peer2: BGPPeerModel) -> BGPPeerModel:
        """Merge information from two peer models."""
        try:
            # Start with peer1 as base
            merged_peer = peer1.model_copy(deep=True) if hasattr(peer1, 'model_copy') else peer1
            
            # Merge key attributes from peer2
            if hasattr(peer2, 'peer_state') and peer2.peer_state:
                # Use more recent or established state
                if (peer2.peer_state == BGPPeerState.ESTABLISHED or 
                    getattr(merged_peer, 'peer_state', None) != BGPPeerState.ESTABLISHED):
                    merged_peer.peer_state = peer2.peer_state
            
            # Merge session information if available
            if hasattr(peer2, 'session_info') and peer2.session_info:
                if not hasattr(merged_peer, 'session_info') or not merged_peer.session_info:
                    merged_peer.session_info = peer2.session_info
                else:
                    # Merge session metrics
                    if hasattr(peer2.session_info, 'metrics') and peer2.session_info.metrics:
                        merged_peer.session_info.metrics = peer2.session_info.metrics
            
            # Merge troubleshooting notes
            if hasattr(peer2, 'troubleshooting_notes') and peer2.troubleshooting_notes:
                if not hasattr(merged_peer, 'troubleshooting_notes'):
                    merged_peer.troubleshooting_notes = []
                merged_peer.troubleshooting_notes.extend(peer2.troubleshooting_notes)
                # Keep only last 10 notes to prevent memory bloat
                merged_peer.troubleshooting_notes = merged_peer.troubleshooting_notes[-10:]
            
            # Merge security threats
            if hasattr(peer2, 'security_threats') and peer2.security_threats:
                if not hasattr(merged_peer, 'security_threats'):
                    merged_peer.security_threats = set()
                merged_peer.security_threats.update(peer2.security_threats)
            
            # Update last seen timestamp to most recent
            if hasattr(peer2, 'last_seen') and hasattr(merged_peer, 'last_seen'):
                if (peer2.last_seen and 
                    (not merged_peer.last_seen or peer2.last_seen > merged_peer.last_seen)):
                    merged_peer.last_seen = peer2.last_seen
            
            return merged_peer
            
        except Exception as e:
            logger.warning(f"Failed to merge peer information: {e}")
            # Return peer1 as fallback
            return peer1
    
    async def _update_session_correlations(self, peers: List[BGPPeerModel]) -> None:
        """Update session correlations with network elements."""
        for peer in peers:
            correlation = NetworkElementCorrelation(
                bgp_peer_id=peer.peer_id,
                network_element_id=f"ne-{peer.peer_ip}",
                element_type=NetworkElementType.BGP_PEER,
                correlation_confidence=0.8,
                last_updated=datetime.now(timezone.utc)
            )
            self.session_correlations[peer.peer_id] = correlation
    
    async def _sync_asn_relationships(self) -> None:
        """Synchronize ASN relationships with network topology."""
        try:
            # Build ASN hierarchy from BGP topology
            for peer in self.bgp_topology.peers.values():
                if hasattr(peer, 'peer_asn') and peer.peer_asn:
                    asn = peer.peer_asn
                    
                    if asn not in self.asn_hierarchy:
                        self.asn_hierarchy[asn] = ASNHierarchyInfo(
                            asn=asn,
                            peer_relationships=[],
                            network_elements=[]
                        )
                    
                    # Find corresponding network element
                    element_id = self._find_network_element_for_asn(asn, peer)
                    if element_id and element_id not in self.asn_hierarchy[asn].network_elements:
                        self.asn_hierarchy[asn].network_elements.append(element_id)
            
            # Update network topology with ASN information
            for asn, hierarchy_info in self.asn_hierarchy.items():
                for element_id in hierarchy_info.network_elements:
                    if element_id in self.network_topology.elements:
                        element = self.network_topology.elements[element_id]
                        if not hasattr(element, 'autonomous_systems'):
                            element.autonomous_systems = set()
                        element.autonomous_systems.add(asn)
            
            logger.info(f"Synchronized {len(self.asn_hierarchy)} ASN relationships")
            
        except Exception as e:
            logger.error(f"Failed to sync ASN relationships: {e}")
            raise
    
    async def _sync_peer_correlations(self) -> None:
        """Synchronize peer correlations with network elements."""
        try:
            # Update peer correlations based on current session states
            for correlation_id, correlation in self.session_correlations.items():
                peer = self.bgp_topology.peers.get(correlation_id)
                if peer and correlation.network_element_id:
                    element = self.network_topology.elements.get(correlation.network_element_id)
                    
                    if element:
                        # Update correlation health based on BGP state and element health
                        bgp_healthy = hasattr(peer, 'peer_state') and peer.peer_state == BGPPeerState.ESTABLISHED
                        element_healthy = hasattr(element, 'health_status') and element.health_status == HealthStatus.HEALTHY
                        
                        if bgp_healthy and element_healthy:
                            correlation.correlation_health = HealthStatus.HEALTHY
                        elif bgp_healthy or element_healthy:
                            correlation.correlation_health = HealthStatus.DEGRADED
                        else:
                            correlation.correlation_health = HealthStatus.UNHEALTHY
                        
                        correlation.last_updated = datetime.now(timezone.utc)
                        
                        # Update element with BGP correlation info
                        if not hasattr(element, 'bgp_correlations'):
                            element.bgp_correlations = {}
                        element.bgp_correlations[peer.peer_id] = correlation.correlation_health.value
            
            logger.info(f"Synchronized {len(self.session_correlations)} peer correlations")
            
        except Exception as e:
            logger.error(f"Failed to sync peer correlations: {e}")
            raise
    
    async def _calculate_integration_health(self) -> float:
        """Calculate integration health score."""
        try:
            if not self.session_correlations:
                return 0.0
            
            total_correlations = len(self.session_correlations)
            healthy_correlations = 0
            degraded_correlations = 0
            
            for correlation in self.session_correlations.values():
                if correlation.correlation_health == HealthStatus.HEALTHY:
                    healthy_correlations += 1
                elif correlation.correlation_health == HealthStatus.DEGRADED:
                    degraded_correlations += 1
            
            # Calculate weighted health score
            health_score = (
                (healthy_correlations * 1.0) + 
                (degraded_correlations * 0.5)
            ) / total_correlations
            
            # Factor in BGP topology completeness
            topology_completeness = min(len(self.bgp_topology.peers) / 10.0, 1.0)  # Assume 10 peers is "complete"
            
            # Factor in ASN relationship coverage
            asn_coverage = min(len(self.asn_hierarchy) / 5.0, 1.0)  # Assume 5 ASNs is good coverage
            
            # Weighted final score
            final_score = (
                health_score * 0.6 +          # 60% from correlation health
                topology_completeness * 0.25 + # 25% from topology completeness
                asn_coverage * 0.15            # 15% from ASN coverage
            )
            
            return max(0.0, min(1.0, final_score))  # Ensure 0.0-1.0 range
            
        except Exception as e:
            logger.error(f"Failed to calculate integration health: {e}")
            return 0.0
    
    def _find_network_element_for_asn(self, asn: int, peer: BGPPeerModel) -> Optional[str]:
        """Find network element corresponding to ASN and BGP peer."""
        try:
            # Strategy 1: Look for element with matching ASN
            for element_id, element in self.network_topology.elements.items():
                if hasattr(element, 'autonomous_systems') and asn in element.autonomous_systems:
                    return element_id
            
            # Strategy 2: Look for element in same region with compatible type
            peer_region = getattr(peer, 'region', None)
            if peer_region:
                for element_id, element in self.network_topology.elements.items():
                    if (hasattr(element, 'region') and element.region == peer_region and
                        hasattr(element, 'element_type') and 
                        element.element_type in [NetworkElementType.TRANSIT_GATEWAY, NetworkElementType.ROUTER]):
                        return element_id
            
            # Strategy 3: Create placeholder element if none found
            placeholder_id = f"bgp-element-asn-{asn}"
            if placeholder_id not in self.network_topology.elements:
                logger.info(f"Creating placeholder network element for ASN {asn}")
                # Would create placeholder element here in real implementation
            
            return placeholder_id
            
        except Exception as e:
            logger.warning(f"Failed to find network element for ASN {asn}: {e}")
            return None