"""
Data models for operational intelligence features.

This module defines Pydantic models for intelligence operations including
monitoring, anomaly detection, drift analysis, and predictive analytics.
"""

from typing import Dict, List, Optional, Any
from enum import Enum
from pydantic import BaseModel, Field


class EventSeverity(Enum):
    """Event severity levels."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class ChangeType(Enum):
    """Types of configuration changes."""

    POLICY = "policy"
    ATTACHMENT = "attachment"
    ROUTE = "route"
    SEGMENT = "segment"
    NFG = "network_function_group"
    TAG = "tag"


class NetworkEvent(BaseModel):
    """A network event detected during monitoring."""

    timestamp: str = Field(description="Event timestamp in ISO format")
    event_type: str = Field(description="Type of event")
    severity: EventSeverity = Field(description="Event severity")
    resource_id: str = Field(description="Affected resource ID")
    resource_type: str = Field(description="Type of affected resource")
    region: Optional[str] = Field(None, description="AWS region")
    description: str = Field(description="Event description")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional event data")
    correlation_id: Optional[str] = Field(None, description="ID for correlated events")


class ConfigurationChange(BaseModel):
    """A detected configuration change."""

    timestamp: str = Field(description="Change timestamp")
    change_type: ChangeType = Field(description="Type of change")
    resource_id: str = Field(description="Changed resource ID")
    change_description: str = Field(description="Description of the change")
    old_value: Optional[Any] = Field(None, description="Previous value")
    new_value: Optional[Any] = Field(None, description="New value")
    impact_assessment: Optional[str] = Field(None, description="Assessed impact of change")
    requires_review: bool = Field(False, description="Whether change requires manual review")


class DriftAnalysis(BaseModel):
    """Configuration drift analysis results."""

    baseline_timestamp: str = Field(description="Baseline comparison timestamp")
    current_timestamp: str = Field(description="Current configuration timestamp")
    drift_detected: bool = Field(description="Whether drift was detected")
    total_changes: int = Field(description="Total number of changes detected")
    changes_by_type: Dict[str, int] = Field(
        default_factory=dict, description="Changes grouped by type"
    )
    critical_changes: List[ConfigurationChange] = Field(
        default_factory=list, description="Critical changes requiring attention"
    )
    detailed_changes: List[ConfigurationChange] = Field(
        default_factory=list, description="All detected changes"
    )
    recommendations: List[str] = Field(default_factory=list, description="Recommended actions")


class PolicySimulation(BaseModel):
    """Results of policy change simulation."""

    simulation_id: str = Field(description="Unique simulation ID")
    simulation_timestamp: str = Field(description="When simulation was run")
    current_policy_version: str = Field(description="Current policy version")
    proposed_changes_summary: str = Field(description="Summary of proposed changes")
    impact_analysis: Dict[str, Any] = Field(description="Detailed impact analysis")
    affected_resources: List[str] = Field(
        default_factory=list, description="Resources that would be affected"
    )
    routing_changes: Dict[str, Any] = Field(
        default_factory=dict, description="Expected routing changes"
    )
    connectivity_impact: Dict[str, Any] = Field(
        default_factory=dict, description="Expected connectivity impact"
    )
    risk_assessment: str = Field(description="Overall risk level")
    warnings: List[str] = Field(default_factory=list, description="Warnings about the changes")
    recommendations: List[str] = Field(
        default_factory=list, description="Recommendations before applying"
    )


class MonitoringAlert(BaseModel):
    """A monitoring alert generated from events."""

    alert_id: str = Field(description="Unique alert ID")
    timestamp: str = Field(description="Alert generation timestamp")
    severity: EventSeverity = Field(description="Alert severity")
    alert_type: str = Field(description="Type of alert")
    description: str = Field(description="Alert description")
    affected_resources: List[str] = Field(default_factory=list, description="Affected resource IDs")
    triggering_events: List[NetworkEvent] = Field(
        default_factory=list, description="Events that triggered the alert"
    )
    recommended_actions: List[str] = Field(
        default_factory=list, description="Recommended response actions"
    )
    auto_remediation_available: bool = Field(
        False, description="Whether automatic remediation is available"
    )
    alert_status: str = Field("active", description="Alert status (active, acknowledged, resolved)")


class PerformanceMetric(BaseModel):
    """A performance metric data point."""

    timestamp: str = Field(description="Metric timestamp")
    metric_name: str = Field(description="Name of the metric")
    value: float = Field(description="Metric value")
    unit: str = Field(description="Metric unit")
    resource_id: Optional[str] = Field(None, description="Associated resource ID")
    dimensions: Dict[str, str] = Field(default_factory=dict, description="Metric dimensions")


class TrendAnalysis(BaseModel):
    """Trend analysis for metrics over time."""

    metric_name: str = Field(description="Analyzed metric name")
    time_period: str = Field(description="Analysis time period")
    trend_direction: str = Field(description="Trend direction (increasing, decreasing, stable)")
    trend_strength: float = Field(description="Trend strength (0-1)")
    average_value: float = Field(description="Average value over period")
    peak_value: float = Field(description="Peak value in period")
    peak_timestamp: str = Field(description="When peak occurred")
    forecast_next_period: Optional[float] = Field(
        None, description="Forecasted value for next period"
    )
    anomalies_detected: int = Field(0, description="Number of anomalies in period")


class AnomalyEvent(BaseModel):
    """An anomaly detected in the network."""

    timestamp: str = Field(description="Anomaly detection timestamp")
    anomaly_type: str = Field(description="Type of anomaly detected")
    severity: str = Field(description="Anomaly severity (low, medium, high, critical)")
    confidence: float = Field(description="Detection confidence (0-1)")
    affected_resources: List[str] = Field(default_factory=list, description="Affected resources")
    description: str = Field(description="Anomaly description")
    metrics: Dict[str, float] = Field(default_factory=dict, description="Related metric values")
    recommended_actions: List[str] = Field(default_factory=list, description="Recommended actions")
    root_cause_analysis: List[str] = Field(
        default_factory=list, description="Potential root causes"
    )


class AnomalyDetectionResponse(BaseModel):
    """Response from AI/ML anomaly detection analysis."""

    detection_timestamp: str = Field(description="When detection was performed")
    time_range_analyzed: str = Field(description="Time range of analyzed data")
    total_metrics_analyzed: int = Field(description="Number of metrics analyzed")
    anomalies_detected: int = Field(description="Total anomalies found")
    anomaly_events: List[AnomalyEvent] = Field(
        default_factory=list, description="Detailed anomaly events"
    )
    pattern_analysis: Dict[str, Any] = Field(
        default_factory=dict, description="Pattern analysis results"
    )
    predictions: List[Dict[str, Any]] = Field(
        default_factory=list, description="Future anomaly predictions"
    )
    summary: Dict[str, Any] = Field(default_factory=dict, description="Analysis summary")
    health_score: float = Field(description="Overall health score (0-100)")
    recommendations: List[str] = Field(default_factory=list, description="Overall recommendations")


class NetworkEventMonitorResponse(BaseModel):
    """Response from network event monitoring."""

    monitoring_period: str = Field(description="Monitoring time period")
    start_timestamp: str = Field(description="Monitoring start time")
    end_timestamp: str = Field(description="Monitoring end time")
    total_events: int = Field(description="Total events detected")
    events_by_type: Dict[str, int] = Field(default_factory=dict, description="Event count by type")
    events_by_severity: Dict[str, int] = Field(
        default_factory=dict, description="Event count by severity"
    )
    events: List[NetworkEvent] = Field(default_factory=list, description="Detailed event list")
    alerts_generated: List[MonitoringAlert] = Field(
        default_factory=list, description="Alerts generated from events"
    )
    trending_issues: List[str] = Field(default_factory=list, description="Trending issues detected")
    recommendations: List[str] = Field(
        default_factory=list, description="Monitoring recommendations"
    )


class ConfigurationDriftResponse(BaseModel):
    """Response from configuration drift detection."""

    analysis_timestamp: str = Field(description="When analysis was performed")
    baseline_info: Dict[str, Any] = Field(description="Baseline configuration info")
    drift_analysis: DriftAnalysis = Field(description="Detailed drift analysis")
    risk_assessment: str = Field(description="Overall risk from drift")
    compliance_impact: Optional[Dict[str, Any]] = Field(
        None, description="Compliance impact assessment"
    )
    rollback_available: bool = Field(description="Whether rollback is possible")
    rollback_steps: List[str] = Field(
        default_factory=list, description="Steps to rollback if needed"
    )


class PolicySimulationResponse(BaseModel):
    """Response from policy change simulation."""

    simulation_results: PolicySimulation = Field(description="Detailed simulation results")
    visualization_available: bool = Field(description="Whether visual comparison is available")
    visualization_url: Optional[str] = Field(None, description="URL to visualization")
    approval_required_from: List[str] = Field(
        default_factory=list, description="Approvals needed before applying"
    )
    estimated_apply_time: Optional[str] = Field(None, description="Estimated time to apply changes")
    rollback_plan: List[str] = Field(default_factory=list, description="Rollback plan if needed")


class ChangeImpactAnalysisResponse(BaseModel):
    """Response from change impact analysis."""

    change_id: str = Field(description="Unique change identifier")
    analysis_timestamp: str = Field(description="When analysis was performed")
    change_summary: str = Field(description="Summary of the change")
    impact_scope: str = Field(description="Scope of impact (local, regional, global)")
    affected_services: List[str] = Field(
        default_factory=list, description="Services that will be affected"
    )
    affected_resources: List[str] = Field(
        default_factory=list, description="Resources that will be affected"
    )
    connectivity_impact: Dict[str, Any] = Field(
        default_factory=dict, description="Impact on connectivity"
    )
    performance_impact: Dict[str, Any] = Field(
        default_factory=dict, description="Expected performance impact"
    )
    security_impact: Dict[str, Any] = Field(
        default_factory=dict, description="Security implications"
    )
    risk_level: str = Field(description="Overall risk level")
    mitigation_steps: List[str] = Field(default_factory=list, description="Steps to mitigate risks")
    recommended_schedule: Optional[str] = Field(None, description="Recommended time to implement")


class TroubleshootingRunbookResponse(BaseModel):
    """Response containing generated troubleshooting runbook."""

    runbook_id: str = Field(description="Unique runbook ID")
    generation_timestamp: str = Field(description="When runbook was generated")
    issue_description: str = Field(description="Issue being addressed")
    severity: str = Field(description="Issue severity")
    estimated_resolution_time: str = Field(description="Estimated time to resolve")
    prerequisites: List[str] = Field(
        default_factory=list, description="Prerequisites before starting"
    )
    diagnostic_steps: List[Dict[str, Any]] = Field(
        default_factory=list, description="Step-by-step diagnostics"
    )
    remediation_steps: List[Dict[str, Any]] = Field(
        default_factory=list, description="Step-by-step remediation"
    )
    verification_steps: List[str] = Field(
        default_factory=list, description="Steps to verify resolution"
    )
    escalation_criteria: List[str] = Field(default_factory=list, description="When to escalate")
    related_documentation: List[str] = Field(
        default_factory=list, description="Related docs and links"
    )
    automation_available: bool = Field(description="Whether automated remediation is available")


class NetworkDiagramResponse(BaseModel):
    """Response containing network diagram generation details."""

    diagram_id: str = Field(description="Unique diagram ID")
    generation_timestamp: str = Field(description="When diagram was generated")
    diagram_type: str = Field(description="Type of diagram generated")
    format: str = Field(description="Output format (svg, png, pdf)")
    diagram_url: Optional[str] = Field(None, description="URL to access diagram")
    diagram_data: Optional[str] = Field(None, description="Base64 encoded diagram data")
    elements_count: int = Field(description="Number of elements in diagram")
    layout_algorithm: str = Field(description="Layout algorithm used")
    interactive_features: List[str] = Field(
        default_factory=list, description="Available interactive features"
    )
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Diagram metadata")


class PolicyVisualizationResponse(BaseModel):
    """Response from policy document visualization."""

    visualization_id: str = Field(description="Unique visualization ID")
    generation_timestamp: str = Field(description="When visualization was generated")
    policy_version: str = Field(description="Policy version visualized")
    visualization_type: str = Field(description="Type of visualization")
    visualization_url: Optional[str] = Field(None, description="URL to visualization")
    key_insights: List[str] = Field(
        default_factory=list, description="Key insights from visualization"
    )
    complexity_score: float = Field(description="Policy complexity score (0-10)")
    optimization_suggestions: List[str] = Field(
        default_factory=list, description="Suggestions to optimize policy"
    )
    conflict_analysis: Dict[str, Any] = Field(
        default_factory=dict, description="Detected conflicts"
    )
    coverage_analysis: Dict[str, Any] = Field(
        default_factory=dict, description="Policy coverage analysis"
    )


class RoutingDecisionExplanationResponse(BaseModel):
    """Response explaining routing decisions."""

    explanation_id: str = Field(description="Unique explanation ID")
    timestamp: str = Field(description="When explanation was generated")
    source_ip: str = Field(description="Source IP address")
    destination_ip: str = Field(description="Destination IP address")
    routing_path: List[Dict[str, Any]] = Field(
        default_factory=list, description="Routing path explanation"
    )
    decision_factors: List[str] = Field(
        default_factory=list, description="Factors influencing routing decision"
    )
    policy_matches: List[Dict[str, Any]] = Field(
        default_factory=list, description="Policy rules that matched"
    )
    alternative_paths: List[Dict[str, Any]] = Field(
        default_factory=list, description="Alternative routing paths available"
    )
    recommendations: List[str] = Field(
        default_factory=list, description="Recommendations for optimization"
    )


class CloudWANEventMonitorResponse(BaseModel):
    """Response from CloudWAN-specific event monitoring."""

    monitoring_id: str = Field(description="Unique monitoring session ID")
    monitoring_period: str = Field(description="Monitoring period")
    core_network_events: List[NetworkEvent] = Field(
        default_factory=list, description="Core network events"
    )
    attachment_events: List[NetworkEvent] = Field(
        default_factory=list, description="Attachment events"
    )
    policy_events: List[NetworkEvent] = Field(
        default_factory=list, description="Policy-related events"
    )
    performance_events: List[NetworkEvent] = Field(
        default_factory=list, description="Performance events"
    )
    security_events: List[NetworkEvent] = Field(
        default_factory=list, description="Security-related events"
    )
    event_summary: Dict[str, int] = Field(default_factory=dict, description="Event count summary")
    recommendations: List[str] = Field(
        default_factory=list, description="Monitoring recommendations"
    )


class NFGValidationResponse(BaseModel):
    """Response from Network Function Group validation."""

    validation_id: str = Field(description="Unique validation ID")
    timestamp: str = Field(description="Validation timestamp")
    nfg_id: str = Field(description="Network Function Group ID")
    validation_status: str = Field(description="Overall validation status")
    configuration_checks: List[Dict[str, Any]] = Field(
        default_factory=list, description="Configuration validation results"
    )
    connectivity_checks: List[Dict[str, Any]] = Field(
        default_factory=list, description="Connectivity validation results"
    )
    policy_compliance: Dict[str, Any] = Field(
        default_factory=dict, description="Policy compliance status"
    )
    performance_metrics: Dict[str, float] = Field(
        default_factory=dict, description="Performance metrics"
    )
    issues_found: List[str] = Field(default_factory=list, description="Issues identified")
    recommendations: List[str] = Field(
        default_factory=list, description="Recommendations for improvement"
    )


class CrossAccountAnalysisResponse(BaseModel):
    """Response from cross-account analysis."""

    analysis_id: str = Field(description="Unique analysis ID")
    timestamp: str = Field(description="Analysis timestamp")
    accounts_analyzed: List[str] = Field(default_factory=list, description="AWS accounts analyzed")
    cross_account_connections: List[Dict[str, Any]] = Field(
        default_factory=list, description="Cross-account connections"
    )
    permission_analysis: Dict[str, Any] = Field(
        default_factory=dict, description="Permission analysis results"
    )
    security_findings: List[str] = Field(default_factory=list, description="Security findings")
    compliance_status: Dict[str, Any] = Field(default_factory=dict, description="Compliance status")
    optimization_opportunities: List[str] = Field(
        default_factory=list, description="Optimization opportunities"
    )
    recommendations: List[str] = Field(
        default_factory=list, description="Cross-account recommendations"
    )


class LongestPrefixMatchResponse(BaseModel):
    """Response from longest prefix match analysis."""

    analysis_id: str = Field(description="Unique analysis ID")
    timestamp: str = Field(description="Analysis timestamp")
    target_ip: str = Field(description="Target IP address for analysis")
    matching_routes: List[Dict[str, Any]] = Field(
        default_factory=list, description="All matching routes"
    )
    longest_prefix_match: Dict[str, Any] = Field(description="The longest prefix match result")
    route_source: str = Field(description="Source of the longest prefix match")
    routing_decision: str = Field(description="Final routing decision")
    alternative_matches: List[Dict[str, Any]] = Field(
        default_factory=list, description="Other prefix matches"
    )
    explanation: str = Field(description="Explanation of the routing decision")
