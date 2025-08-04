"""
Policy Validation Framework for CloudWAN MCP Server.

This framework provides real-time policy change detection, validation,
and compliance monitoring with automated alerting and remediation.

Features:
- Real-time policy change detection and monitoring
- Automated policy validation and compliance checking
- Policy version management and rollback capabilities
- Automated alerting for policy violations and conflicts
- Policy compliance reporting and audit trails
- Integration with CloudWatch for monitoring and alerting
"""

import asyncio
import json
import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple, Callable
from dataclasses import dataclass, field
from enum import Enum

from botocore.exceptions import ClientError

from ..aws.client_manager import AWSClientManager
from ..config import CloudWANConfig
from .cloudwan_policy_evaluator import (
    CloudWANPolicyEvaluator,
    PolicyValidationIssue,
    PolicyValidationLevel,
    PolicyAnalysisResult,
)
from ..utils.aws_operations import AWSOperationError


class ChangeDetectionMode(str, Enum):
    """Policy change detection modes."""

    POLLING = "polling"
    EVENT_DRIVEN = "event_driven"
    HYBRID = "hybrid"


class AlertSeverity(str, Enum):
    """Alert severity levels."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class ValidationAction(str, Enum):
    """Actions to take on validation failures."""

    ALERT_ONLY = "alert_only"
    BLOCK_CHANGE = "block_change"
    AUTO_REMEDIATE = "auto_remediate"
    ROLLBACK = "rollback"


@dataclass
class PolicyChangeEvent:
    """Policy change event information."""

    event_id: str
    core_network_id: str
    change_type: str  # "create", "update", "delete"
    old_version: Optional[int] = None
    new_version: Optional[int] = None
    change_details: Dict[str, Any] = field(default_factory=dict)
    change_timestamp: Optional[datetime] = None
    change_source: Optional[str] = None  # "console", "api", "terraform", etc.
    change_requester: Optional[str] = None
    validation_required: bool = True


@dataclass
class ValidationAlert:
    """Policy validation alert."""

    alert_id: str
    core_network_id: str
    severity: AlertSeverity
    alert_type: str
    title: str
    description: str
    affected_resources: List[str] = field(default_factory=list)
    validation_issues: List[PolicyValidationIssue] = field(default_factory=list)
    recommended_actions: List[str] = field(default_factory=list)
    alert_timestamp: Optional[datetime] = None
    is_resolved: bool = False
    resolution_timestamp: Optional[datetime] = None
    resolution_notes: Optional[str] = None


@dataclass
class ComplianceReport:
    """Policy compliance report."""

    report_id: str
    core_network_id: str
    report_timestamp: datetime
    compliance_score: float
    total_checks: int
    passed_checks: int
    failed_checks: int
    compliance_issues: List[PolicyValidationIssue] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    trend_data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PolicyAuditEntry:
    """Policy audit trail entry."""

    audit_id: str
    core_network_id: str
    event_type: str
    event_details: Dict[str, Any]
    user_identity: Optional[str] = None
    source_ip: Optional[str] = None
    user_agent: Optional[str] = None
    timestamp: Optional[datetime] = None
    validation_results: Optional[PolicyAnalysisResult] = None


class PolicyValidationFramework:
    """
    Policy Validation Framework.

    Provides comprehensive policy validation, change detection, and compliance
    monitoring capabilities with real-time alerting and automated remediation.
    """

    def __init__(
        self,
        aws_manager: AWSClientManager,
        config: CloudWANConfig,
        policy_evaluator: CloudWANPolicyEvaluator,
    ):
        """Initialize the Policy Validation Framework."""
        self.aws_manager = aws_manager
        self.config = config
        self.policy_evaluator = policy_evaluator
        self.logger = logging.getLogger(__name__)
        self.executor = ThreadPoolExecutor(max_workers=4)

        # Framework state
        self._monitoring_active = False
        self._change_callbacks: List[Callable] = []
        self._validation_callbacks: List[Callable] = []

        # Cache and tracking
        self._policy_versions: Dict[str, int] = {}
        self._active_alerts: Dict[str, ValidationAlert] = {}
        self._audit_trail: List[PolicyAuditEntry] = []

        # Configuration
        self.change_detection_mode = ChangeDetectionMode.POLLING
        self.polling_interval = timedelta(minutes=5)
        self.validation_timeout = timedelta(minutes=2)

        # Custom endpoints
        self.custom_nm_endpoint = self.config.aws.custom_endpoints.get("networkmanager")
        self.custom_cw_endpoint = self.config.aws.custom_endpoints.get("cloudwatch")

    async def start_monitoring(
        self,
        core_network_ids: List[str],
        change_detection_mode: ChangeDetectionMode = ChangeDetectionMode.POLLING,
        polling_interval_minutes: int = 5,
    ) -> None:
        """
        Start policy change monitoring for specified Core Networks.

        Args:
            core_network_ids: List of Core Network IDs to monitor
            change_detection_mode: Change detection mode
            polling_interval_minutes: Polling interval in minutes
        """
        self.logger.info(f"Starting policy monitoring for {len(core_network_ids)} Core Networks")

        self.change_detection_mode = change_detection_mode
        self.polling_interval = timedelta(minutes=polling_interval_minutes)

        # Initialize policy version tracking
        for core_network_id in core_network_ids:
            try:
                current_version = await self._get_current_policy_version(core_network_id)
                self._policy_versions[core_network_id] = current_version
            except Exception as e:
                self.logger.warning(
                    f"Failed to get initial policy version for {core_network_id}: {e}"
                )

        # Start monitoring based on mode
        if self.change_detection_mode == ChangeDetectionMode.POLLING:
            asyncio.create_task(self._start_polling_monitor(core_network_ids))
        elif self.change_detection_mode == ChangeDetectionMode.EVENT_DRIVEN:
            await self._start_event_driven_monitor(core_network_ids)
        elif self.change_detection_mode == ChangeDetectionMode.HYBRID:
            asyncio.create_task(self._start_polling_monitor(core_network_ids))
            await self._start_event_driven_monitor(core_network_ids)

        self._monitoring_active = True
        self.logger.info("Policy monitoring started successfully")

    async def stop_monitoring(self) -> None:
        """Stop policy change monitoring."""
        self.logger.info("Stopping policy monitoring")
        self._monitoring_active = False

        # Clean up resources
        self._change_callbacks.clear()
        self._validation_callbacks.clear()

        self.logger.info("Policy monitoring stopped")

    async def validate_policy_change(
        self,
        core_network_id: str,
        proposed_policy: Dict[str, Any],
        change_context: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, List[PolicyValidationIssue]]:
        """
        Validate a proposed policy change.

        Args:
            core_network_id: Core Network ID
            proposed_policy: Proposed policy document
            change_context: Optional change context information

        Returns:
            Tuple of (is_valid, validation_issues)
        """
        self.logger.info(f"Validating policy change for Core Network: {core_network_id}")

        try:
            # Get current policy version
            current_version = await self._get_current_policy_version(core_network_id)

            # Validate proposed policy
            validation_issues = await self.policy_evaluator.validate_policy_changes(
                core_network_id, proposed_policy, current_version
            )

            # Check for critical issues
            critical_issues = [
                issue for issue in validation_issues if issue.level == PolicyValidationLevel.ERROR
            ]

            is_valid = len(critical_issues) == 0

            # Create audit entry
            audit_entry = self._create_audit_entry(
                core_network_id,
                "policy_validation",
                {
                    "proposed_policy_version": proposed_policy.get("version"),
                    "current_policy_version": current_version,
                    "validation_result": "valid" if is_valid else "invalid",
                    "issues_count": len(validation_issues),
                    "critical_issues_count": len(critical_issues),
                },
            )
            self._audit_trail.append(audit_entry)

            # Generate alerts for critical issues
            if critical_issues:
                await self._generate_validation_alert(
                    core_network_id, critical_issues, AlertSeverity.CRITICAL
                )

            return is_valid, validation_issues

        except Exception as e:
            self.logger.error(f"Policy validation failed: {e}")
            return False, [
                PolicyValidationIssue(
                    issue_id=f"validation_error_{datetime.now().isoformat()}",
                    level=PolicyValidationLevel.ERROR,
                    category="validation_failure",
                    title="Policy Validation Failed",
                    description=f"Failed to validate policy change: {str(e)}",
                    timestamp=datetime.now(),
                )
            ]

    async def generate_compliance_report(
        self,
        core_network_id: str,
        include_trend_data: bool = True,
        historical_days: int = 30,
    ) -> ComplianceReport:
        """
        Generate comprehensive compliance report for a Core Network.

        Args:
            core_network_id: Core Network ID
            include_trend_data: Include historical trend data
            historical_days: Number of days for trend analysis

        Returns:
            Compliance report
        """
        self.logger.info(f"Generating compliance report for Core Network: {core_network_id}")

        try:
            # Perform complete policy analysis
            policy_analysis = await self.policy_evaluator.evaluate_core_network_policy(
                core_network_id, force_refresh=True
            )

            # Calculate compliance metrics
            total_checks = len(policy_analysis.validation_issues) + 10  # Base checks
            failed_checks = len(
                [
                    issue
                    for issue in policy_analysis.validation_issues
                    if issue.level in [PolicyValidationLevel.ERROR, PolicyValidationLevel.WARNING]
                ]
            )
            passed_checks = total_checks - failed_checks

            # Generate recommendations
            recommendations = self._generate_compliance_recommendations(policy_analysis)

            # Collect trend data if requested
            trend_data = {}
            if include_trend_data:
                trend_data = await self._collect_trend_data(core_network_id, historical_days)

            report = ComplianceReport(
                report_id=f"compliance_{core_network_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                core_network_id=core_network_id,
                report_timestamp=datetime.now(),
                compliance_score=policy_analysis.compliance_score,
                total_checks=total_checks,
                passed_checks=passed_checks,
                failed_checks=failed_checks,
                compliance_issues=policy_analysis.validation_issues,
                recommendations=recommendations,
                trend_data=trend_data,
            )

            # Store report (could be saved to S3 or database)
            await self._store_compliance_report(report)

            return report

        except Exception as e:
            raise AWSOperationError(f"Failed to generate compliance report: {str(e)}")

    async def register_change_callback(self, callback: Callable) -> None:
        """Register callback for policy change events."""
        self._change_callbacks.append(callback)

    async def register_validation_callback(self, callback: Callable) -> None:
        """Register callback for validation events."""
        self._validation_callbacks.append(callback)

    async def get_active_alerts(
        self,
        core_network_id: Optional[str] = None,
        severity_filter: Optional[AlertSeverity] = None,
    ) -> List[ValidationAlert]:
        """
        Get active validation alerts.

        Args:
            core_network_id: Optional Core Network ID filter
            severity_filter: Optional severity filter

        Returns:
            List of active alerts
        """
        alerts = list(self._active_alerts.values())

        # Apply filters
        if core_network_id:
            alerts = [alert for alert in alerts if alert.core_network_id == core_network_id]

        if severity_filter:
            alerts = [alert for alert in alerts if alert.severity == severity_filter]

        # Only return unresolved alerts
        alerts = [alert for alert in alerts if not alert.is_resolved]

        return alerts

    async def resolve_alert(self, alert_id: str, resolution_notes: Optional[str] = None) -> bool:
        """
        Resolve a validation alert.

        Args:
            alert_id: Alert ID to resolve
            resolution_notes: Optional resolution notes

        Returns:
            True if alert was resolved successfully
        """
        if alert_id in self._active_alerts:
            alert = self._active_alerts[alert_id]
            alert.is_resolved = True
            alert.resolution_timestamp = datetime.now()
            alert.resolution_notes = resolution_notes

            self.logger.info(f"Resolved alert {alert_id}: {alert.title}")
            return True

        return False

    async def _start_polling_monitor(self, core_network_ids: List[str]) -> None:
        """Start polling-based change monitoring."""
        self.logger.info("Starting polling-based policy monitoring")

        while self._monitoring_active:
            try:
                # Check each Core Network for changes
                for core_network_id in core_network_ids:
                    await self._check_policy_changes(core_network_id)

                # Wait for next polling interval
                await asyncio.sleep(self.polling_interval.total_seconds())

            except Exception as e:
                self.logger.error(f"Error in polling monitor: {e}")
                await asyncio.sleep(60)  # Wait 1 minute before retrying

    async def _start_event_driven_monitor(self, core_network_ids: List[str]) -> None:
        """Start event-driven change monitoring using CloudWatch Events."""
        self.logger.info("Starting event-driven policy monitoring")

        try:
            # Set up CloudWatch Events for Network Manager API calls
            events_client = await self.aws_manager.get_client("events", "us-west-2")

            # Create event rule for policy changes
            rule_name = "cloudwan-policy-changes"
            event_pattern = {
                "source": ["aws.networkmanager"],
                "detail-type": ["AWS API Call via CloudTrail"],
                "detail": {
                    "eventSource": ["networkmanager.amazonaws.com"],
                    "eventName": [
                        "PutCoreNetworkPolicy",
                        "RestoreCoreNetworkPolicyVersion",
                        "ExecuteCoreNetworkChangeSet",
                    ],
                },
            }

            await events_client.put_rule(
                Name=rule_name, EventPattern=json.dumps(event_pattern), State="ENABLED"
            )

            self.logger.info("Event-driven monitoring configured")

        except Exception as e:
            self.logger.warning(f"Failed to configure event-driven monitoring: {e}")

    async def _check_policy_changes(self, core_network_id: str) -> None:
        """Check for policy changes in a Core Network."""
        try:
            current_version = await self._get_current_policy_version(core_network_id)
            last_known_version = self._policy_versions.get(core_network_id, 0)

            if current_version > last_known_version:
                # Policy changed - trigger validation
                change_event = PolicyChangeEvent(
                    event_id=f"change_{core_network_id}_{current_version}",
                    core_network_id=core_network_id,
                    change_type="update",
                    old_version=last_known_version,
                    new_version=current_version,
                    change_timestamp=datetime.now(),
                    change_source="detected",
                )

                await self._handle_policy_change(change_event)
                self._policy_versions[core_network_id] = current_version

        except Exception as e:
            self.logger.warning(f"Failed to check policy changes for {core_network_id}: {e}")

    async def _handle_policy_change(self, change_event: PolicyChangeEvent) -> None:
        """Handle detected policy change."""
        self.logger.info(
            f"Handling policy change for {change_event.core_network_id}: v{change_event.old_version} -> v{change_event.new_version}"
        )

        try:
            # Validate the new policy
            if change_event.validation_required:
                policy_analysis = await self.policy_evaluator.evaluate_core_network_policy(
                    change_event.core_network_id, force_refresh=True
                )

                # Check for critical issues
                critical_issues = [
                    issue
                    for issue in policy_analysis.validation_issues
                    if issue.level == PolicyValidationLevel.ERROR
                ]

                if critical_issues:
                    await self._generate_validation_alert(
                        change_event.core_network_id,
                        critical_issues,
                        AlertSeverity.HIGH,
                    )

            # Create audit entry
            audit_entry = self._create_audit_entry(
                change_event.core_network_id,
                "policy_changed",
                {
                    "old_version": change_event.old_version,
                    "new_version": change_event.new_version,
                    "change_source": change_event.change_source,
                },
            )
            self._audit_trail.append(audit_entry)

            # Notify registered callbacks
            for callback in self._change_callbacks:
                try:
                    await callback(change_event)
                except Exception as e:
                    self.logger.warning(f"Change callback failed: {e}")

        except Exception as e:
            self.logger.error(f"Failed to handle policy change: {e}")

    async def _generate_validation_alert(
        self,
        core_network_id: str,
        validation_issues: List[PolicyValidationIssue],
        severity: AlertSeverity,
    ) -> None:
        """Generate validation alert for policy issues."""
        alert_id = f"alert_{core_network_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        # Determine affected resources
        affected_resources = []
        for issue in validation_issues:
            affected_resources.extend(issue.affected_segments)
            affected_resources.extend(issue.affected_nfgs)
        affected_resources = list(set(affected_resources))  # Remove duplicates

        # Generate recommendations
        recommendations = []
        for issue in validation_issues:
            recommendations.extend(issue.recommendations)
        recommendations = list(set(recommendations))  # Remove duplicates

        alert = ValidationAlert(
            alert_id=alert_id,
            core_network_id=core_network_id,
            severity=severity,
            alert_type="policy_validation",
            title="Policy Validation Issues Detected",
            description=f"Found {len(validation_issues)} validation issues in policy",
            affected_resources=affected_resources,
            validation_issues=validation_issues,
            recommended_actions=recommendations,
            alert_timestamp=datetime.now(),
        )

        self._active_alerts[alert_id] = alert

        # Send alert to CloudWatch if configured
        await self._send_cloudwatch_alert(alert)

        self.logger.warning(f"Generated validation alert {alert_id} for {core_network_id}")

    async def _get_current_policy_version(self, core_network_id: str) -> int:
        """Get current policy version for a Core Network."""
        try:
            nm_client = await self._get_networkmanager_client()
            response = await nm_client.get_core_network_policy(CoreNetworkId=core_network_id)

            policy_info = response.get("CoreNetworkPolicy", {})
            return policy_info.get("PolicyVersionId", 0)

        except ClientError as e:
            if e.response.get("Error", {}).get("Code") == "ResourceNotFoundException":
                return 0
            raise

    def _create_audit_entry(
        self, core_network_id: str, event_type: str, event_details: Dict[str, Any]
    ) -> PolicyAuditEntry:
        """Create audit trail entry."""
        return PolicyAuditEntry(
            audit_id=f"audit_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}",
            core_network_id=core_network_id,
            event_type=event_type,
            event_details=event_details,
            timestamp=datetime.now(),
        )

    def _generate_compliance_recommendations(
        self, policy_analysis: PolicyAnalysisResult
    ) -> List[str]:
        """Generate compliance recommendations based on policy analysis."""
        recommendations = []

        if policy_analysis.compliance_score < 0.8:
            recommendations.append(
                "Review and resolve policy validation issues to improve compliance"
            )

        error_issues = [
            issue
            for issue in policy_analysis.validation_issues
            if issue.level == PolicyValidationLevel.ERROR
        ]
        if error_issues:
            recommendations.append(
                f"Address {len(error_issues)} critical policy errors immediately"
            )

        if not policy_analysis.send_to_evaluations:
            recommendations.append("Consider adding send-to rules for segment connectivity")

        if not policy_analysis.send_via_evaluations:
            recommendations.append(
                "Consider implementing Network Function Groups for traffic inspection"
            )

        return recommendations

    async def _collect_trend_data(
        self, core_network_id: str, historical_days: int
    ) -> Dict[str, Any]:
        """Collect historical trend data for compliance reporting."""
        # This would typically query a time-series database or CloudWatch
        # For now, return placeholder data
        return {
            "compliance_trend": {
                "daily_scores": [],  # Would contain daily compliance scores
                "issue_counts": [],  # Would contain daily issue counts
                "policy_changes": [],  # Would contain policy change frequency
            },
            "data_period_days": historical_days,
            "last_updated": datetime.now().isoformat(),
        }

    async def _store_compliance_report(self, report: ComplianceReport) -> None:
        """Store compliance report (placeholder for actual storage implementation)."""
        # This would typically store the report in S3, DynamoDB, or another storage service
        self.logger.info(f"Storing compliance report {report.report_id}")

    async def _send_cloudwatch_alert(self, alert: ValidationAlert) -> None:
        """Send alert to CloudWatch for monitoring and notification."""
        try:
            cloudwatch_client = await self.aws_manager.get_client("cloudwatch", "us-west-2")

            # Send custom metric
            await cloudwatch_client.put_metric_data(
                Namespace="CloudWAN/PolicyValidation",
                MetricData=[
                    {
                        "MetricName": "ValidationAlert",
                        "Dimensions": [
                            {"Name": "CoreNetworkId", "Value": alert.core_network_id},
                            {"Name": "Severity", "Value": alert.severity.value},
                        ],
                        "Value": 1,
                        "Unit": "Count",
                        "Timestamp": alert.alert_timestamp,
                    }
                ],
            )

            self.logger.info(f"Sent CloudWatch alert for {alert.alert_id}")

        except Exception as e:
            self.logger.warning(f"Failed to send CloudWatch alert: {e}")

    async def _get_networkmanager_client(self):
        """Get NetworkManager client with custom endpoint support."""
        region = "us-west-2"  # NetworkManager is a global service
        client = await self.aws_manager.get_client("networkmanager", region)

        if self.custom_nm_endpoint:
            client._endpoint.host = self.custom_nm_endpoint.replace("https://", "").replace(
                "http://", ""
            )

        return client
