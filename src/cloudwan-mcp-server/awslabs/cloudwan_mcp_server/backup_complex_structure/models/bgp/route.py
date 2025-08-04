"""
BGP route models for CloudWAN MCP Server.

This module provides comprehensive BGP route modeling that consolidates functionality
from all BGP analyzers including route analysis, path validation, policy compliance,
and security assessment.

Key Features:
- RFC 4271 compliant BGP route attribute modeling
- AS path analysis and validation with loop detection
- BGP community and extended community support
- RPKI validation and route origin verification
- Route policy compliance checking
- Multi-region route propagation tracking
- Security threat correlation and analysis
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple
from pydantic import BaseModel, Field, field_validator, model_validator
from enum import Enum
import ipaddress
import re
import uuid

from ..shared.enums import (
    BGPRouteType,
    BGPSecurityViolationType,
    RPKIValidationStatus,
    SecurityThreatLevel,
    ValidationStatus
)
from ..shared.base import TimestampMixin, EnhancedBaseResponse


class BGPOriginType(str, Enum):
    """BGP origin attribute types per RFC 4271."""
    
    IGP = "IGP"           # Route learned from interior gateway protocol
    EGP = "EGP"           # Route learned from exterior gateway protocol  
    INCOMPLETE = "INCOMPLETE"  # Route learned by other means

    def get_preference_value(self) -> int:
        """Get preference value for route selection (lower is better)."""
        preference_mapping = {
            self.IGP: 0,
            self.EGP: 1,
            self.INCOMPLETE: 2,
        }
        return preference_mapping.get(self, 2)


class BGPCommunityType(str, Enum):
    """Types of BGP communities."""
    
    STANDARD = "standard"      # Standard communities (RFC 1997)
    EXTENDED = "extended"      # Extended communities (RFC 4360)
    LARGE = "large"           # Large communities (RFC 8092)
    WELL_KNOWN = "well_known"  # Well-known communities

    def get_format_pattern(self) -> str:
        """Get regex pattern for community format validation."""
        patterns = {
            self.STANDARD: r"^\d+:\d+$",
            self.EXTENDED: r"^(RT|RD):\d+:\d+$",
            self.LARGE: r"^\d+:\d+:\d+$",
            self.WELL_KNOWN: r"^(NO_EXPORT|NO_ADVERTISE|NO_EXPORT_SUBCONFED|INTERNET)$"
        }
        return patterns.get(self, r".*")


class BGPPathAttributes(BaseModel):
    """Comprehensive BGP path attributes model."""
    
    # Mandatory attributes
    origin: BGPOriginType = Field(description="BGP origin attribute")
    as_path: List[int] = Field(description="AS path as list of ASNs")
    next_hop: str = Field(description="BGP next hop IP address")
    
    # Optional attributes
    multi_exit_discriminator: Optional[int] = Field(
        default=None, 
        description="Multi-Exit Discriminator (MED) value"
    )
    local_preference: Optional[int] = Field(
        default=None,
        description="Local preference value (iBGP only)"
    )
    atomic_aggregate: bool = Field(
        default=False,
        description="Atomic aggregate flag"
    )
    aggregator: Optional[Tuple[int, str]] = Field(
        default=None,
        description="Aggregator ASN and IP address tuple"
    )
    
    # Community attributes
    communities: List[str] = Field(
        default_factory=list,
        description="Standard BGP communities"
    )
    extended_communities: List[str] = Field(
        default_factory=list,
        description="Extended BGP communities"
    )
    large_communities: List[str] = Field(
        default_factory=list,
        description="Large BGP communities"
    )
    
    # Route reflection attributes
    originator_id: Optional[str] = Field(
        default=None,
        description="Originator ID for route reflection"
    )
    cluster_list: List[str] = Field(
        default_factory=list,
        description="Cluster list for route reflection"
    )
    
    # Additional attributes
    weight: Optional[int] = Field(
        default=None,
        description="Cisco-specific weight attribute"
    )
    route_tag: Optional[int] = Field(
        default=None,
        description="Route tag for policy matching"
    )
    
    # CloudWAN specific attributes
    cloudwan_segment: Optional[str] = Field(
        default=None,
        description="CloudWAN segment name"
    )
    cloudwan_attachment_id: Optional[str] = Field(
        default=None,
        description="CloudWAN attachment ID"
    )

    @field_validator('next_hop')
    @classmethod
    def validate_next_hop(cls, v):
        """Validate next hop IP address."""
        try:
            ipaddress.ip_address(v)
        except ValueError:
            raise ValueError(f"Invalid next hop IP address: {v}")
        return v

    @field_validator('as_path')
    @classmethod
    def validate_as_path(cls, v):
        """Validate AS path contains valid ASNs."""
        for asn in v:
            if not (1 <= asn <= 4294967295):
                raise ValueError(f"Invalid ASN in path: {asn}")
        return v

    @field_validator('communities', 'extended_communities', 'large_communities')
    @classmethod
    def validate_communities(cls, v, info):
        """Validate community format based on type."""
        if not v:
            return v
            
        # Determine community type from field name
        field_name = info.field_name if hasattr(info, 'field_name') else 'communities'
        if field_name == 'communities':
            community_type = BGPCommunityType.STANDARD
        elif field_name == 'extended_communities':
            community_type = BGPCommunityType.EXTENDED
        else:  # large_communities
            community_type = BGPCommunityType.LARGE
            
        pattern = community_type.get_format_pattern()
        for community in v:
            if not re.match(pattern, community):
                raise ValueError(f"Invalid {community_type} community format: {community}")
        return v

    def has_as_path_loop(self) -> bool:
        """Check if AS path contains loops."""
        return len(self.as_path) != len(set(self.as_path))

    def get_as_path_length(self) -> int:
        """Get AS path length."""
        return len(self.as_path)

    def get_origin_asn(self) -> Optional[int]:
        """Get the originating ASN (last ASN in path)."""
        return self.as_path[-1] if self.as_path else None

    def is_ibgp_route(self, local_asn: int) -> bool:
        """Check if route was received via iBGP."""
        return self.get_origin_asn() == local_asn

    def has_community(self, community: str) -> bool:
        """Check if route has a specific community."""
        return (
            community in self.communities or
            community in self.extended_communities or
            community in self.large_communities
        )

    def get_all_communities(self) -> List[str]:
        """Get all communities as a single list."""
        return self.communities + self.extended_communities + self.large_communities

    def is_no_export(self) -> bool:
        """Check if route has NO_EXPORT community."""
        return self.has_community("NO_EXPORT")

    def is_no_advertise(self) -> bool:
        """Check if route has NO_ADVERTISE community."""
        return self.has_community("NO_ADVERTISE")


class BGPRouteMetrics(BaseModel):
    """BGP route-specific performance and reliability metrics."""
    
    # Advertisement metrics
    advertise_count: int = Field(default=0, description="Number of times route was advertised")
    withdraw_count: int = Field(default=0, description="Number of times route was withdrawn")
    
    # Timing information
    first_advertised: Optional[datetime] = Field(
        default=None,
        description="First time route was advertised"
    )
    last_advertised: Optional[datetime] = Field(
        default=None,
        description="Last time route was advertised"
    )
    last_withdrawn: Optional[datetime] = Field(
        default=None,
        description="Last time route was withdrawn"
    )
    
    # Route flap detection
    flap_count: int = Field(default=0, description="Number of route flaps")
    flap_penalty: int = Field(default=0, description="Current flap penalty score")
    is_dampened: bool = Field(default=False, description="Whether route is dampened")
    dampen_until: Optional[datetime] = Field(
        default=None,
        description="When dampening will be removed"
    )
    
    # Peer metrics
    advertising_peers: Set[str] = Field(
        default_factory=set,
        description="Set of peers that advertised this route"
    )
    withdrawn_by_peers: Set[str] = Field(
        default_factory=set,
        description="Set of peers that withdrew this route"
    )
    
    # Regional propagation
    region_propagation: Dict[str, Dict[str, Any]] = Field(
        default_factory=dict,
        description="Per-region route propagation metrics"
    )
    
    # Performance metrics
    convergence_time_ms: Optional[float] = Field(
        default=None,
        description="Time to convergence in milliseconds"
    )
    processing_time_ms: Optional[float] = Field(
        default=None,
        description="Route processing time in milliseconds"
    )

    def get_route_age_seconds(self) -> int:
        """Get route age in seconds since first advertisement."""
        if not self.first_advertised:
            return 0
        return int((datetime.now(timezone.utc) - self.first_advertised).total_seconds())

    def get_flap_rate_per_hour(self, observation_period_hours: int = 24) -> float:
        """Calculate route flap rate per hour."""
        if observation_period_hours <= 0:
            return 0.0
        return self.flap_count / observation_period_hours

    def is_stable_route(self, max_flaps_per_hour: int = 2) -> bool:
        """Check if route is considered stable."""
        return self.get_flap_rate_per_hour() <= max_flaps_per_hour and not self.is_dampened

    def add_region_propagation(self, region: str, peer_id: str, action: str) -> None:
        """Add region propagation information."""
        if region not in self.region_propagation:
            self.region_propagation[region] = {"peers": set(), "actions": []}
        self.region_propagation[region]["peers"].add(peer_id)
        self.region_propagation[region]["actions"].append({
            "action": action,
            "peer_id": peer_id,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })


class RouteSecurityContext(BaseModel):
    """Security context and threat information for BGP routes."""
    
    # RPKI validation
    rpki_status: RPKIValidationStatus = Field(
        default=RPKIValidationStatus.UNKNOWN,
        description="RPKI validation status"
    )
    rpki_roa_found: bool = Field(
        default=False,
        description="Whether Route Origin Authorization was found"
    )
    rpki_validation_time: Optional[datetime] = Field(
        default=None,
        description="When RPKI validation was performed"
    )
    
    # Security threats
    security_violations: List[BGPSecurityViolationType] = Field(
        default_factory=list,
        description="Detected security violations"
    )
    threat_level: SecurityThreatLevel = Field(
        default=SecurityThreatLevel.UNKNOWN,
        description="Overall threat level"
    )
    threat_indicators: List[str] = Field(
        default_factory=list,
        description="Security threat indicators"
    )
    
    # Anomaly detection
    is_anomalous: bool = Field(
        default=False,
        description="Whether route exhibits anomalous behavior"
    )
    anomaly_score: float = Field(
        default=0.0,
        description="Anomaly detection confidence score (0.0-1.0)"
    )
    anomaly_reasons: List[str] = Field(
        default_factory=list,
        description="Reasons for anomaly detection"
    )
    
    # Threat intelligence
    threat_intelligence: Dict[str, Any] = Field(
        default_factory=dict,
        description="External threat intelligence data"
    )
    
    # Compliance status
    policy_violations: List[str] = Field(
        default_factory=list,
        description="Security policy violations"
    )
    compliance_status: ValidationStatus = Field(
        default=ValidationStatus.UNKNOWN,
        description="Security compliance status"
    )

    def is_rpki_valid(self) -> bool:
        """Check if route is RPKI valid."""
        return self.rpki_status == RPKIValidationStatus.VALID

    def has_security_issues(self) -> bool:
        """Check if route has any security issues."""
        return (
            len(self.security_violations) > 0 or
            self.threat_level in (SecurityThreatLevel.HIGH, SecurityThreatLevel.CRITICAL) or
            self.is_anomalous or
            len(self.policy_violations) > 0
        )

    def requires_immediate_attention(self) -> bool:
        """Check if route requires immediate security attention."""
        return (
            self.threat_level == SecurityThreatLevel.CRITICAL or
            BGPSecurityViolationType.PREFIX_HIJACKING in self.security_violations or
            BGPSecurityViolationType.BGP_HIJACKING in self.security_violations
        )

    def add_security_violation(self, violation: BGPSecurityViolationType, 
                              indicator: str) -> None:
        """Add a security violation with indicator."""
        if violation not in self.security_violations:
            self.security_violations.append(violation)
        if indicator not in self.threat_indicators:
            self.threat_indicators.append(indicator)

    def update_threat_level(self) -> None:
        """Update threat level based on current violations."""
        if not self.security_violations:
            self.threat_level = SecurityThreatLevel.UNKNOWN
            return
            
        # Determine highest threat level from violations
        max_level = SecurityThreatLevel.INFO
        for violation in self.security_violations:
            violation_level = violation.get_default_severity()
            if violation_level.get_numeric_value() > max_level.get_numeric_value():
                max_level = violation_level
                
        self.threat_level = max_level


class BGPRouteInfo(TimestampMixin):
    """
    Comprehensive BGP route information model consolidating all analyzer functionality.
    
    This model serves as the primary BGP route representation, integrating protocol-level
    details, policy compliance, security assessment, and operational metrics.
    """
    
    # Unique identification
    route_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique route identifier"
    )
    
    # Route prefix information
    prefix: str = Field(description="Network prefix in CIDR notation")
    prefix_length: int = Field(description="Prefix length")
    
    # Path attributes
    path_attributes: BGPPathAttributes = Field(description="BGP path attributes")
    
    # Route classification
    route_type: BGPRouteType = Field(description="Route type classification")
    
    # Route status
    is_active: bool = Field(default=True, description="Whether route is active")
    is_best_path: bool = Field(default=False, description="Whether this is the best path")
    is_valid: bool = Field(default=True, description="Route validity status")
    is_feasible: bool = Field(default=True, description="Route feasibility status")
    
    # Source information
    learned_from_peer: Optional[str] = Field(
        default=None,
        description="Peer ID that advertised this route"
    )
    advertised_to_peers: List[str] = Field(
        default_factory=list,
        description="List of peer IDs this route was advertised to"
    )
    
    # Region and location context
    region: str = Field(description="AWS region where route is processed")
    source_region: Optional[str] = Field(
        default=None,
        description="Original source region of the route"
    )
    
    # Performance and reliability metrics
    metrics: BGPRouteMetrics = Field(default_factory=BGPRouteMetrics, description="Route performance metrics")
    
    # Security context
    security_context: RouteSecurityContext = Field(default_factory=RouteSecurityContext, description="Security assessment")
    
    # Policy and compliance
    import_policy_matched: Optional[str] = Field(
        default=None,
        description="Import policy that matched this route"
    )
    export_policy_applied: List[str] = Field(
        default_factory=list,
        description="Export policies applied to this route"
    )
    route_map_modifications: Dict[str, Any] = Field(
        default_factory=dict,
        description="Route map modifications applied"
    )
    
    # Validation and errors
    validation_status: ValidationStatus = Field(
        default=ValidationStatus.UNKNOWN,
        description="Overall route validation status"
    )
    validation_errors: List[str] = Field(
        default_factory=list,
        description="Route validation errors"
    )
    validation_warnings: List[str] = Field(
        default_factory=list,
        description="Route validation warnings"
    )
    
    # Operational context
    monitoring_enabled: bool = Field(default=True, description="Whether route monitoring is enabled")
    business_impact: str = Field(
        default="low",
        description="Business impact level (low, medium, high, critical)"
    )
    
    # Additional metadata
    tags: Dict[str, str] = Field(default_factory=dict, description="Route tags")
    custom_attributes: Dict[str, Any] = Field(
        default_factory=dict,
        description="Custom operational attributes"
    )

    @field_validator('prefix')
    @classmethod
    def validate_prefix(cls, v):
        """Validate network prefix format."""
        try:
            network = ipaddress.ip_network(v, strict=False)
            return str(network)
        except ValueError:
            raise ValueError(f"Invalid network prefix: {v}")

    @model_validator(mode='before')
    def set_prefix_length(cls, values):
        """Extract and set prefix length from prefix."""
        if isinstance(values, dict) and 'prefix' in values:
            try:
                network = ipaddress.ip_network(values['prefix'], strict=False)
                values['prefix_length'] = network.prefixlen
            except ValueError:
                pass
        return values

    def get_network(self) -> ipaddress.IPv4Network:
        """Get network object from prefix."""
        return ipaddress.ip_network(self.prefix, strict=False)

    def is_default_route(self) -> bool:
        """Check if this is a default route."""
        network = self.get_network()
        return network.network_address == ipaddress.ip_address('0.0.0.0') and network.prefixlen == 0

    def is_host_route(self) -> bool:
        """Check if this is a host route (/32 for IPv4)."""
        return self.prefix_length == 32

    def is_private_prefix(self) -> bool:
        """Check if prefix is in private address space."""
        network = self.get_network()
        return network.is_private

    def has_as_path_loop(self) -> bool:
        """Check if route has AS path loop."""
        return self.path_attributes.has_as_path_loop()

    def get_origin_asn(self) -> Optional[int]:
        """Get the originating ASN."""
        return self.path_attributes.get_origin_asn()

    def is_secure_route(self) -> bool:
        """Check if route passes all security checks."""
        return (
            self.security_context.is_rpki_valid() and
            not self.security_context.has_security_issues() and
            not self.has_as_path_loop()
        )

    def is_policy_compliant(self) -> bool:
        """Check if route is policy compliant."""
        return (
            self.validation_status in (ValidationStatus.PASS, ValidationStatus.WARNING) and
            len(self.security_context.policy_violations) == 0
        )

    def get_route_preference(self) -> int:
        """Calculate route preference for best path selection."""
        # Simple preference calculation based on multiple factors
        preference = 0
        
        # Local preference (higher is better)
        if self.path_attributes.local_preference:
            preference += self.path_attributes.local_preference
        
        # AS path length (shorter is better)
        preference -= (self.path_attributes.get_as_path_length() * 10)
        
        # Origin type preference
        preference -= self.path_attributes.origin.get_preference_value()
        
        # MED (lower is better)
        if self.path_attributes.multi_exit_discriminator:
            preference -= self.path_attributes.multi_exit_discriminator
            
        return preference

    def add_validation_error(self, error: str) -> None:
        """Add a validation error."""
        if error not in self.validation_errors:
            self.validation_errors.append(error)
        self.validation_status = ValidationStatus.FAIL

    def add_validation_warning(self, warning: str) -> None:
        """Add a validation warning."""
        if warning not in self.validation_warnings:
            self.validation_warnings.append(warning)
        if self.validation_status == ValidationStatus.UNKNOWN:
            self.validation_status = ValidationStatus.WARNING

    def mark_as_best_path(self) -> None:
        """Mark route as the best path."""
        self.is_best_path = True
        self.is_active = True

    def withdraw_route(self, reason: str = "Manual withdrawal") -> None:
        """Withdraw the route."""
        self.is_active = False
        self.is_best_path = False
        self.metrics.withdraw_count += 1
        self.metrics.last_withdrawn = datetime.now(timezone.utc)
        self.custom_attributes["withdrawal_reason"] = reason

    def to_summary(self) -> Dict[str, Any]:
        """Create a summary view of the BGP route."""
        return {
            "route_id": self.route_id,
            "prefix": self.prefix,
            "next_hop": self.path_attributes.next_hop,
            "origin_asn": self.get_origin_asn(),
            "as_path_length": self.path_attributes.get_as_path_length(),
            "route_type": self.route_type,
            "is_active": self.is_active,
            "is_best_path": self.is_best_path,
            "region": self.region,
            "rpki_valid": self.security_context.is_rpki_valid(),
            "has_security_issues": self.security_context.has_security_issues(),
            "validation_status": self.validation_status,
            "last_updated": self.updated_at.isoformat(),
        }


class RouteAnalysisResult(EnhancedBaseResponse):
    """
    Comprehensive route analysis result consolidating all BGP analyzer outputs.
    
    This response model provides a unified view of route analysis across protocol
    compliance, security assessment, policy validation, and operational metrics.
    """
    
    # Analysis scope
    analyzed_routes: List[BGPRouteInfo] = Field(
        default_factory=list,
        description="List of analyzed routes"
    )
    total_routes_analyzed: int = Field(default=0, description="Total number of routes analyzed")
    
    # Analysis summary
    active_routes: int = Field(default=0, description="Number of active routes")
    best_path_routes: int = Field(default=0, description="Number of best path routes")
    invalid_routes: int = Field(default=0, description="Number of invalid routes")
    
    # Security assessment summary
    secure_routes: int = Field(default=0, description="Number of secure routes")
    routes_with_threats: int = Field(default=0, description="Routes with security threats")
    rpki_valid_routes: int = Field(default=0, description="RPKI valid routes")
    rpki_invalid_routes: int = Field(default=0, description="RPKI invalid routes")
    
    # Policy compliance summary
    policy_compliant_routes: int = Field(default=0, description="Policy compliant routes")
    policy_violation_routes: int = Field(default=0, description="Routes with policy violations")
    
    # Performance metrics summary
    avg_as_path_length: Optional[float] = Field(
        default=None,
        description="Average AS path length"
    )
    route_flap_count: int = Field(default=0, description="Total route flaps detected")
    dampened_routes: int = Field(default=0, description="Number of dampened routes")
    
    # Regional analysis
    routes_by_region: Dict[str, int] = Field(
        default_factory=dict,
        description="Route count by region"
    )
    cross_region_routes: int = Field(default=0, description="Cross-region routes")
    
    # Top-level findings
    critical_issues: List[str] = Field(
        default_factory=list,
        description="Critical issues requiring immediate attention"
    )
    recommendations: List[str] = Field(
        default_factory=list,
        description="Analysis recommendations"
    )
    
    # Analysis metadata
    analysis_type: str = Field(default="comprehensive", description="Type of analysis performed")
    filters_applied: Dict[str, Any] = Field(
        default_factory=dict,
        description="Analysis filters that were applied"
    )

    def calculate_summaries(self) -> None:
        """Calculate summary statistics from analyzed routes."""
        if not self.analyzed_routes:
            return
            
        self.total_routes_analyzed = len(self.analyzed_routes)
        
        # Route status summaries
        self.active_routes = sum(1 for r in self.analyzed_routes if r.is_active)
        self.best_path_routes = sum(1 for r in self.analyzed_routes if r.is_best_path)
        self.invalid_routes = sum(1 for r in self.analyzed_routes if not r.is_valid)
        
        # Security summaries
        self.secure_routes = sum(1 for r in self.analyzed_routes if r.is_secure_route())
        self.routes_with_threats = sum(1 for r in self.analyzed_routes 
                                     if r.security_context.has_security_issues())
        self.rpki_valid_routes = sum(1 for r in self.analyzed_routes 
                                   if r.security_context.is_rpki_valid())
        self.rpki_invalid_routes = sum(1 for r in self.analyzed_routes 
                                     if r.security_context.rpki_status == RPKIValidationStatus.INVALID)
        
        # Policy compliance summaries
        self.policy_compliant_routes = sum(1 for r in self.analyzed_routes if r.is_policy_compliant())
        self.policy_violation_routes = sum(1 for r in self.analyzed_routes 
                                         if len(r.security_context.policy_violations) > 0)
        
        # Performance summaries
        as_path_lengths = [r.path_attributes.get_as_path_length() for r in self.analyzed_routes]
        self.avg_as_path_length = sum(as_path_lengths) / len(as_path_lengths) if as_path_lengths else 0
        
        self.route_flap_count = sum(r.metrics.flap_count for r in self.analyzed_routes)
        self.dampened_routes = sum(1 for r in self.analyzed_routes if r.metrics.is_dampened)
        
        # Regional summaries
        self.routes_by_region = {}
        for route in self.analyzed_routes:
            region = route.region
            self.routes_by_region[region] = self.routes_by_region.get(region, 0) + 1
            
        self.cross_region_routes = sum(1 for r in self.analyzed_routes 
                                     if r.source_region and r.source_region != r.region)

    def get_security_risk_score(self) -> float:
        """Calculate overall security risk score (0.0 - 1.0)."""
        if self.total_routes_analyzed == 0:
            return 0.0
            
        risk_factors = [
            (self.routes_with_threats / self.total_routes_analyzed) * 0.4,
            (self.rpki_invalid_routes / self.total_routes_analyzed) * 0.3,
            (self.policy_violation_routes / self.total_routes_analyzed) * 0.2,
            (self.invalid_routes / self.total_routes_analyzed) * 0.1,
        ]
        
        return min(sum(risk_factors), 1.0)

    def get_route_stability_score(self) -> float:
        """Calculate route stability score (0.0 - 1.0)."""
        if self.total_routes_analyzed == 0:
            return 1.0
            
        stability_factors = [
            1.0 - (self.route_flap_count / (self.total_routes_analyzed * 10)),  # Normalize flaps
            1.0 - (self.dampened_routes / self.total_routes_analyzed),
            self.active_routes / self.total_routes_analyzed,
        ]
        
        return max(sum(stability_factors) / len(stability_factors), 0.0)

    def add_critical_issue(self, issue: str) -> None:
        """Add a critical issue."""
        if issue not in self.critical_issues:
            self.critical_issues.append(issue)

    def add_recommendation(self, recommendation: str) -> None:
        """Add an analysis recommendation."""
        if recommendation not in self.recommendations:
            self.recommendations.append(recommendation)