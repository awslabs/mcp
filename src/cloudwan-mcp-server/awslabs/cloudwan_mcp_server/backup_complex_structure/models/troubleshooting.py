"""
Troubleshooting data models for CloudWAN MCP Server.

This module contains Pydantic models for troubleshooting responses,
diagnostics, and validation results.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from enum import Enum

from .base import BaseResponse, RouteInfo, AWSResource


class HealthStatus(str, Enum):
    """Health status enumeration."""

    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


class ValidationStatus(str, Enum):
    """Validation status enumeration."""

    PASS = "pass"
    FAIL = "fail"
    WARNING = "warning"
    UNKNOWN = "unknown"


class PolicyError(BaseModel):
    """Policy validation error."""

    error_type: str
    error_code: str
    message: str
    line_number: Optional[int] = None
    field_path: Optional[str] = None
    severity: str = "error"  # error, warning, info


class PolicyWarning(BaseModel):
    """Policy validation warning."""

    warning_type: str
    warning_code: str
    message: str
    line_number: Optional[int] = None
    field_path: Optional[str] = None
    recommendation: Optional[str] = None


class PolicySummary(BaseModel):
    """Policy document summary."""

    version: str
    core_network_configuration: Dict[str, Any] = Field(default_factory=dict)
    segments: List[Dict[str, Any]] = Field(default_factory=list)
    segment_actions: List[Dict[str, Any]] = Field(default_factory=list)
    attachment_policies: List[Dict[str, Any]] = Field(default_factory=list)
    network_function_groups: List[Dict[str, Any]] = Field(default_factory=list)


class ASNConflict(BaseModel):
    """ASN assignment conflict information."""

    asn: int
    conflict_type: str  # duplicate, overlap, reserved
    resources: List[Dict[str, str]] = Field(
        default_factory=list
    )  # resource_type, resource_id, region
    impact_level: str = "medium"  # low, medium, high, critical
    resolution_options: List[str] = Field(default_factory=list)


class BGPSessionImpact(BaseModel):
    """BGP session impact analysis."""

    session_id: str
    peer_asn: int
    local_asn: int
    impact_type: str  # session_down, route_loss, suboptimal_routing
    affected_prefixes: List[str] = Field(default_factory=list)
    estimated_downtime: Optional[str] = None


class AttachmentIssue(BaseModel):
    """Attachment health issue."""

    issue_type: str
    severity: str  # low, medium, high, critical
    description: str
    affected_resources: List[str] = Field(default_factory=list)
    detection_time: Optional[str] = None


class AttachmentDependency(BaseModel):
    """Attachment dependency information."""

    dependency_type: str  # route_table, policy, segment
    resource_id: str
    status: str
    is_critical: bool = False


class FailurePoint(BaseModel):
    """Network connectivity failure point."""

    hop_number: int
    resource_type: str
    resource_id: str
    failure_reason: str
    confidence_score: float = Field(ge=0.0, le=1.0)
    remediation_steps: List[str] = Field(default_factory=list)


class DiagnosisStep(BaseModel):
    """Connectivity diagnosis step."""

    step_number: int
    step_type: str  # route_check, security_group, firewall, etc.
    description: str
    result: str  # pass, fail, warning
    details: Dict[str, Any] = Field(default_factory=dict)


class MissingRouteAnalysis(BaseModel):
    """Analysis of missing route."""

    expected_route: str
    segment_name: str
    potential_sources: List[str] = Field(default_factory=list)
    blocking_reasons: List[str] = Field(default_factory=list)
    remediation_steps: List[str] = Field(default_factory=list)


class UnexpectedRouteAnalysis(BaseModel):
    """Analysis of unexpected route."""

    unexpected_route: str
    route_source: str
    reason_for_presence: str
    should_be_removed: bool = False
    impact_assessment: str = "low"  # low, medium, high


class PropagationIssue(BaseModel):
    """Route propagation issue."""

    source_attachment: str
    target_segment: str
    issue_type: str
    blocking_policy: Optional[str] = None
    resolution_steps: List[str] = Field(default_factory=list)


# Response Models


class ConnectivityDiagnosisResponse(BaseResponse):
    """Response for connectivity diagnosis."""

    source_ip: str
    destination_ip: str
    protocol: str = "tcp"
    port: Optional[int] = None
    diagnosis_status: str  # SUCCESS, FAILURE, PARTIAL
    failure_points: List[FailurePoint] = Field(default_factory=list)
    step_by_step_analysis: List[DiagnosisStep] = Field(default_factory=list)
    remediation_steps: List[str] = Field(default_factory=list)
    confidence_score: float = Field(ge=0.0, le=1.0, default=0.0)


class ASNValidationResponse(BaseResponse):
    """Response for ASN validation across CloudWAN and TGWs."""

    validation_status: str  # PASS, CONFLICTS_DETECTED, ERROR
    cloudwan_asns: Dict[str, int] = Field(default_factory=dict)  # core_network_id -> ASN
    tgw_asns: Dict[str, Dict[str, int]] = Field(default_factory=dict)  # region -> {tgw_id -> ASN}
    conflicts: List[ASNConflict] = Field(default_factory=list)
    bgp_session_impacts: List[BGPSessionImpact] = Field(default_factory=list)
    remediation_recommendations: List[str] = Field(default_factory=list)
    cross_account_analysis: Optional[Dict[str, Any]] = None


class PolicyValidationResponse(BaseResponse):
    """Response for policy validation."""

    is_valid: bool
    errors: List[PolicyError] = Field(default_factory=list)
    warnings: List[PolicyWarning] = Field(default_factory=list)
    suggestions: List[str] = Field(default_factory=list)
    policy_summary: PolicySummary
    asn_conflicts: Optional[List[ASNConflict]] = None


class AttachmentHealthResponse(BaseResponse):
    """Response for attachment health analysis."""

    attachment_id: str
    state: str
    health_status: str  # HEALTHY, WARNING, CRITICAL
    issues: List[AttachmentIssue] = Field(default_factory=list)
    remediation_steps: List[str] = Field(default_factory=list)
    route_propagation_status: Dict[str, str] = Field(default_factory=dict)
    dependencies: List[AttachmentDependency] = Field(default_factory=list)


class RouteLearningDiagnosisResponse(BaseResponse):
    """Response for route learning diagnosis."""

    segment_name: str
    region: str
    expected_routes: List[str] = Field(default_factory=list)
    actual_routes: List[RouteInfo] = Field(default_factory=list)
    missing_routes: List[MissingRouteAnalysis] = Field(default_factory=list)
    unexpected_routes: List[UnexpectedRouteAnalysis] = Field(default_factory=list)
    propagation_issues: List[PropagationIssue] = Field(default_factory=list)
    remediation_steps: List[str] = Field(default_factory=list)


class RouteComparisonResponse(BaseResponse):
    """Response for route comparison analysis."""

    segment_name: str
    region: str
    baseline_timestamp: Optional[str] = None
    current_routes: List[RouteInfo] = Field(default_factory=list)
    baseline_routes: List[RouteInfo] = Field(default_factory=list)
    added_routes: List[RouteInfo] = Field(default_factory=list)
    removed_routes: List[RouteInfo] = Field(default_factory=list)
    modified_routes: List[Dict[str, Any]] = Field(default_factory=list)
    drift_detected: bool = False


class PolicyConflictAnalysisResponse(BaseResponse):
    """Response for policy conflict analysis."""

    policy_document_id: str
    conflicts_detected: bool
    rule_conflicts: List[Dict[str, Any]] = Field(default_factory=list)
    precedence_issues: List[Dict[str, Any]] = Field(default_factory=list)
    impact_assessment: Dict[str, str] = Field(default_factory=dict)
    resolution_recommendations: List[str] = Field(default_factory=list)


class ASNConflictResponse(BaseResponse):
    """Response for ASN conflict detection."""

    conflicts_detected: bool
    conflict_count: int = 0
    conflicts: List[ASNConflict] = Field(default_factory=list)
    regions_analyzed: List[str] = Field(default_factory=list)
    remediation_suggestions: List[str] = Field(default_factory=list)
    impact_assessment: str = "low"  # low, medium, high, critical


class SegmentRouteComparisonResponse(BaseResponse):
    """Response for segment route comparison."""

    source_segment: str
    target_segment: Optional[str] = None
    region: str
    matching_routes: List[RouteInfo] = Field(default_factory=list)
    missing_routes: List[RouteInfo] = Field(default_factory=list)
    extra_routes: List[RouteInfo] = Field(default_factory=list)
    route_differences: List[Dict[str, Any]] = Field(default_factory=list)
    comparison_summary: str = ""


class ValidationCheck(BaseModel):
    """Network validation check result."""

    check_id: str = Field(description="Unique identifier for the validation check")
    check_name: str = Field(description="Human-readable name of the check")
    category: str = Field(
        description="Category of the validation check (connectivity, security, configuration, etc.)"
    )
    status: ValidationStatus = Field(description="Status of the validation check")
    resource_id: Optional[str] = Field(default=None, description="Resource ID being validated")
    resource_type: Optional[str] = Field(
        default=None, description="Type of resource being validated"
    )
    region: Optional[str] = Field(default=None, description="AWS region for the resource")
    details: Dict[str, Any] = Field(
        default_factory=dict, description="Additional check-specific details"
    )
    message: str = Field(description="Explanation of validation result")
    severity: str = Field(
        default="medium",
        description="Impact severity if check fails (critical, high, medium, low)",
    )
    remediation_steps: List[str] = Field(
        default_factory=list, description="Steps to fix validation failures"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional validation metadata"
    )


class NetworkValidationResponse(BaseResponse):
    """Response for network validation operations."""

    validation_summary: Dict[str, int] = Field(
        default_factory=lambda: {"pass": 0, "fail": 0, "warning": 0, "unknown": 0},
        description="Summary of validation check results",
    )
    overall_status: ValidationStatus = Field(
        default=ValidationStatus.UNKNOWN, description="Overall validation status"
    )
    checks: List[ValidationCheck] = Field(
        default_factory=list, description="List of validation check results"
    )
    resources_validated: List[AWSResource] = Field(
        default_factory=list, description="AWS resources that were validated"
    )
    configuration_errors: List[Dict[str, Any]] = Field(
        default_factory=list, description="Configuration errors detected"
    )
    security_findings: List[Dict[str, Any]] = Field(
        default_factory=list, description="Security-related validation findings"
    )
    performance_recommendations: List[Dict[str, Any]] = Field(
        default_factory=list, description="Performance optimization recommendations"
    )
    validation_coverage: float = Field(
        default=100.0,
        ge=0.0,
        le=100.0,
        description="Percentage of network validated successfully",
    )


class ConnectivityHop(BaseModel):
    """Network connectivity hop information."""
    
    hop_number: int
    hop_type: str  # source_vpc, cloudwan_attachment, core_network, transit_gateway, destination_vpc
    resource_id: str
    resource_type: str
    region: Optional[str] = None
    segment: Optional[str] = None
    core_network_id: Optional[str] = None
    details: Dict[str, Any] = Field(default_factory=dict)


class PathAnalysis(BaseModel):
    """Network path analysis results."""
    
    is_reachable: bool
    path_type: str  # same_vpc, cloudwan, transit_gateway, direct
    hops: List[ConnectivityHop] = Field(default_factory=list)
    segments_traversed: List[str] = Field(default_factory=list)
    total_latency_estimate: Optional[str] = None
    path_efficiency_score: float = Field(ge=0.0, le=100.0, default=0.0)
    issues_detected: List[str] = Field(default_factory=list)


class SecurityRuleAnalysis(BaseModel):
    """Security rule analysis for connectivity."""
    
    rule_type: str  # security_group, network_acl
    resource_id: str
    rule_number: Optional[int] = None
    direction: str  # inbound, outbound
    action: str  # allow, deny
    protocol: str
    port_range: Optional[Dict[str, int]] = None
    source_destination: str
    matches_traffic: bool
    blocks_connectivity: bool


class SecurityAnalysis(BaseModel):
    """Security analysis results for connectivity."""
    
    overall_evaluation: str  # allowed, blocked, partial, unknown
    security_groups_analysis: List[SecurityRuleAnalysis] = Field(default_factory=list)
    network_acls_analysis: List[SecurityRuleAnalysis] = Field(default_factory=list)
    blocking_rules: List[SecurityRuleAnalysis] = Field(default_factory=list)
    allowing_rules: List[SecurityRuleAnalysis] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)


class PerformanceMetrics(BaseModel):
    """Performance metrics for connectivity."""
    
    estimated_latency_ms: Optional[str] = None
    latency_category: str  # intra_region, inter_region, cross_cloud
    bandwidth_estimate: Optional[str] = None
    efficiency_score: float = Field(ge=0.0, le=100.0, default=0.0)
    optimization_opportunities: List[Dict[str, Any]] = Field(default_factory=list)
    routing_efficiency: Dict[str, Any] = Field(default_factory=dict)


class TroubleshootingRecommendation(BaseModel):
    """Troubleshooting recommendation."""
    
    category: str  # connectivity, security, performance, configuration
    priority: str  # critical, high, medium, low
    issue_description: str
    root_cause: Optional[str] = None
    recommended_actions: List[str] = Field(default_factory=list)
    estimated_fix_time: Optional[str] = None
    confidence_level: float = Field(ge=0.0, le=1.0, default=0.8)
    related_resources: List[str] = Field(default_factory=list)


class ConnectivityAnalysisResponse(BaseResponse):
    """Response for connectivity analysis operations."""
    
    analysis_id: str
    source_ip: str
    destination_ip: str
    protocol: str = "tcp"
    port: int = 443
    
    # Core analysis results
    is_reachable: bool
    path_analysis: PathAnalysis
    security_analysis: SecurityAnalysis
    performance_metrics: PerformanceMetrics
    
    # Recommendations and troubleshooting
    troubleshooting_recommendations: List[TroubleshootingRecommendation] = Field(default_factory=list)
    
    # Metadata
    regions_analyzed: List[str] = Field(default_factory=list)
    analysis_duration_seconds: float = 0.0
    cache_hit: bool = False
    topology_snapshot: Dict[str, Any] = Field(default_factory=dict)
    
    # Error handling
    partial_analysis: bool = False
    analysis_warnings: List[str] = Field(default_factory=list)
