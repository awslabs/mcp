"""
BGP session models for CloudWAN MCP Server.

This module provides comprehensive BGP session modeling including session state 
tracking, event history, operational monitoring, and automated remediation capabilities.

Key Features:
- Complete BGP session lifecycle management
- Session state tracking with FSM compliance
- Historical event tracking and audit trails
- Operational alerting and SLA monitoring
- Automated remediation workflow integration
- Multi-region session correlation and analysis
"""

from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field, model_validator
from enum import Enum
import uuid

from ..shared.enums import (
    BGPPeerState,
    HealthStatus
)
from ..shared.base import TimestampMixin


class BGPSessionEventType(str, Enum):
    """Types of BGP session events."""
    
    # Session lifecycle events
    SESSION_ESTABLISHED = "session_established"
    SESSION_TERMINATED = "session_terminated"
    SESSION_RESET = "session_reset"
    CONNECTION_ATTEMPT = "connection_attempt"
    CONNECTION_FAILED = "connection_failed"
    
    # Protocol events
    KEEPALIVE_SENT = "keepalive_sent"
    KEEPALIVE_RECEIVED = "keepalive_received"
    UPDATE_SENT = "update_sent"
    UPDATE_RECEIVED = "update_received"
    NOTIFICATION_SENT = "notification_sent"
    NOTIFICATION_RECEIVED = "notification_received"
    
    # Policy events
    ROUTE_POLICY_APPLIED = "route_policy_applied"
    ROUTE_FILTERED = "route_filtered"
    PREFIX_LIMIT_EXCEEDED = "prefix_limit_exceeded"
    
    # Operational events
    HEALTH_CHECK_PASSED = "health_check_passed"
    HEALTH_CHECK_FAILED = "health_check_failed"
    MAINTENANCE_STARTED = "maintenance_started"
    MAINTENANCE_COMPLETED = "maintenance_completed"
    
    # Security events
    SECURITY_THREAT_DETECTED = "security_threat_detected"
    SECURITY_THREAT_RESOLVED = "security_threat_resolved"
    AUTHENTICATION_FAILED = "authentication_failed"
    
    # Automation events
    AUTOMATED_REMEDIATION = "automated_remediation"
    ESCALATION_TRIGGERED = "escalation_triggered"
    SLA_BREACH_DETECTED = "sla_breach_detected"

    def is_critical_event(self) -> bool:
        """Check if event is considered critical."""
        critical_events = {
            self.SESSION_TERMINATED,
            self.NOTIFICATION_SENT,
            self.NOTIFICATION_RECEIVED,
            self.PREFIX_LIMIT_EXCEEDED,
            self.HEALTH_CHECK_FAILED,
            self.SECURITY_THREAT_DETECTED,
            self.AUTHENTICATION_FAILED,
            self.SLA_BREACH_DETECTED,
        }
        return self in critical_events

    def requires_immediate_attention(self) -> bool:
        """Check if event requires immediate attention."""
        immediate_events = {
            self.SECURITY_THREAT_DETECTED,
            self.SLA_BREACH_DETECTED,
            self.AUTHENTICATION_FAILED,
            self.PREFIX_LIMIT_EXCEEDED,
        }
        return self in immediate_events


class BGPSessionEvent(TimestampMixin):
    """Individual BGP session event with comprehensive context."""
    
    event_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique event identifier"
    )
    
    # Event classification
    event_type: BGPSessionEventType = Field(description="Type of BGP session event")
    severity: str = Field(
        default="info",
        description="Event severity (info, warning, error, critical)"
    )
    
    # Event details
    description: str = Field(description="Human-readable event description")
    details: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional event context and data"
    )
    
    # Session context
    session_id: str = Field(description="BGP session identifier")
    peer_asn: int = Field(description="Peer ASN involved in event")
    local_asn: int = Field(description="Local ASN")
    
    # Location context
    region: str = Field(description="AWS region where event occurred")
    edge_location: Optional[str] = Field(
        default=None,
        description="CloudWAN edge location if applicable"
    )
    
    # Error context (for error events)
    error_code: Optional[str] = Field(default=None, description="BGP error code if applicable")
    error_subcode: Optional[str] = Field(default=None, description="BGP error subcode")
    
    # Automation context
    triggered_automation: bool = Field(
        default=False,
        description="Whether event triggered automation"
    )
    automation_action: Optional[str] = Field(
        default=None,
        description="Automation action taken"
    )
    
    # Correlation context
    correlation_id: Optional[str] = Field(
        default=None,
        description="ID for correlating related events"
    )
    parent_event_id: Optional[str] = Field(
        default=None,
        description="Parent event ID if this is a child event"
    )
    
    # Resolution context
    acknowledged: bool = Field(default=False, description="Whether event was acknowledged")
    acknowledged_by: Optional[str] = Field(default=None, description="Who acknowledged the event")
    acknowledged_at: Optional[datetime] = Field(default=None, description="When event was acknowledged")
    resolved: bool = Field(default=False, description="Whether event was resolved")
    resolved_at: Optional[datetime] = Field(default=None, description="When event was resolved")
    resolution_notes: Optional[str] = Field(default=None, description="Resolution notes")

    def acknowledge(self, acknowledged_by: str, notes: Optional[str] = None) -> None:
        """Acknowledge the event."""
        self.acknowledged = True
        self.acknowledged_by = acknowledged_by
        self.acknowledged_at = datetime.now(timezone.utc)
        if notes:
            self.details["acknowledgment_notes"] = notes

    def resolve(self, resolution_notes: Optional[str] = None) -> None:
        """Mark event as resolved."""
        self.resolved = True
        self.resolved_at = datetime.now(timezone.utc)
        if resolution_notes:
            self.resolution_notes = resolution_notes

    def get_age_seconds(self) -> float:
        """Get event age in seconds."""
        return (datetime.now(timezone.utc) - self.created_at).total_seconds()

    def is_recent(self, max_age_seconds: int = 3600) -> bool:
        """Check if event is recent (within specified seconds)."""
        return self.get_age_seconds() <= max_age_seconds


class BGPSessionState(TimestampMixin):
    """Current state of a BGP session with comprehensive tracking."""
    
    # Session identification
    session_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique session identifier"
    )
    
    # Peer information
    local_asn: int = Field(description="Local ASN")
    peer_asn: int = Field(description="Peer ASN")
    local_ip: Optional[str] = Field(default=None, description="Local IP address")
    peer_ip: Optional[str] = Field(default=None, description="Peer IP address")
    
    # Current state
    current_state: BGPPeerState = Field(
        default=BGPPeerState.IDLE,
        description="Current BGP FSM state"
    )
    previous_state: Optional[BGPPeerState] = Field(
        default=None,
        description="Previous BGP FSM state"
    )
    state_change_time: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="When state last changed"
    )
    
    # Session timing
    session_start_time: Optional[datetime] = Field(
        default=None,
        description="When current session was established"
    )
    session_duration_seconds: int = Field(
        default=0,
        description="Current session duration in seconds"
    )
    last_keepalive_sent: Optional[datetime] = Field(
        default=None,
        description="Last keepalive sent timestamp"
    )
    last_keepalive_received: Optional[datetime] = Field(
        default=None,
        description="Last keepalive received timestamp"
    )
    
    # Configuration state
    hold_time: int = Field(default=180, description="Configured hold time")
    keepalive_interval: int = Field(default=60, description="Configured keepalive interval")
    connect_retry_timer: int = Field(default=120, description="Connect retry timer value")
    
    # Counters
    establishment_attempts: int = Field(default=0, description="Session establishment attempts")
    successful_establishments: int = Field(default=0, description="Successful establishments")
    session_resets: int = Field(default=0, description="Session reset count")
    
    # Health and monitoring
    health_status: HealthStatus = Field(
        default=HealthStatus.UNKNOWN,
        description="Session health status"
    )
    last_health_check: Optional[datetime] = Field(
        default=None,
        description="Last health check timestamp"
    )
    monitoring_enabled: bool = Field(default=True, description="Whether monitoring is active")
    
    # Regional context
    region: str = Field(description="AWS region")
    cloudwan_edge_location: Optional[str] = Field(
        default=None,
        description="CloudWAN edge location if applicable"
    )
    
    # Additional state information
    is_passive: bool = Field(default=False, description="Whether session is in passive mode")
    administrative_shutdown: bool = Field(
        default=False,
        description="Whether session is administratively shutdown"
    )
    
    # Error tracking
    last_error: Optional[str] = Field(default=None, description="Last error message")
    last_error_time: Optional[datetime] = Field(default=None, description="Last error timestamp")
    error_count: int = Field(default=0, description="Total error count")

    def transition_to_state(self, new_state: BGPPeerState, 
                           reason: Optional[str] = None) -> None:
        """Transition to a new BGP state."""
        if new_state != self.current_state:
            self.previous_state = self.current_state
            self.current_state = new_state
            self.state_change_time = datetime.now(timezone.utc)
            
            # Handle specific state transitions
            if new_state == BGPPeerState.ESTABLISHED:
                self.session_start_time = self.state_change_time
                self.successful_establishments += 1
                self.health_status = HealthStatus.HEALTHY
            elif new_state == BGPPeerState.IDLE:
                if self.previous_state == BGPPeerState.ESTABLISHED:
                    self.session_resets += 1
                self.session_start_time = None
                self.session_duration_seconds = 0

    def is_established(self) -> bool:
        """Check if session is established."""
        return self.current_state == BGPPeerState.ESTABLISHED

    def is_connecting(self) -> bool:
        """Check if session is in connecting states."""
        return self.current_state.is_connecting()

    def update_session_duration(self) -> None:
        """Update session duration if established."""
        if self.is_established() and self.session_start_time:
            self.session_duration_seconds = int(
                (datetime.now(timezone.utc) - self.session_start_time).total_seconds()
            )

    def get_uptime_percentage(self, observation_period_hours: int = 24) -> float:
        """Calculate session uptime percentage over observation period."""
        if observation_period_hours <= 0:
            return 0.0
            
        observation_seconds = observation_period_hours * 3600
        uptime_seconds = min(self.session_duration_seconds, observation_seconds)
        return (uptime_seconds / observation_seconds) * 100.0

    def is_keepalive_overdue(self) -> bool:
        """Check if keepalive is overdue."""
        if not self.last_keepalive_received:
            return True
            
        overdue_threshold = self.hold_time * 0.8  # 80% of hold time
        time_since_keepalive = (
            datetime.now(timezone.utc) - self.last_keepalive_received
        ).total_seconds()
        
        return time_since_keepalive > overdue_threshold

    def record_error(self, error_message: str) -> None:
        """Record a session error."""
        self.last_error = error_message
        self.last_error_time = datetime.now(timezone.utc)
        self.error_count += 1
        self.health_status = HealthStatus.UNHEALTHY


class BGPSessionHistory(BaseModel):
    """Historical tracking of BGP session events and state changes."""
    
    session_id: str = Field(description="BGP session identifier")
    
    # Event history
    events: List[BGPSessionEvent] = Field(
        default_factory=list,
        description="Chronological list of session events"
    )
    
    # State change history
    state_changes: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="History of state changes"
    )
    
    # Performance history
    performance_snapshots: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Periodic performance snapshots"
    )
    
    # Maintenance history
    maintenance_windows: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Planned maintenance windows"
    )
    
    # Configuration changes
    configuration_changes: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Configuration change history"
    )

    def add_event(self, event: BGPSessionEvent) -> None:
        """Add an event to history."""
        self.events.append(event)
        # Keep only last 1000 events to prevent unbounded growth
        if len(self.events) > 1000:
            self.events = self.events[-1000:]

    def add_state_change(self, from_state: BGPPeerState, to_state: BGPPeerState,
                        timestamp: datetime, reason: Optional[str] = None) -> None:
        """Record a state change."""
        change_record = {
            "from_state": from_state,
            "to_state": to_state,
            "timestamp": timestamp.isoformat(),
            "reason": reason,
        }
        self.state_changes.append(change_record)
        
        # Keep only last 100 state changes
        if len(self.state_changes) > 100:
            self.state_changes = self.state_changes[-100:]

    def get_recent_events(self, hours: int = 24) -> List[BGPSessionEvent]:
        """Get events from the last N hours."""
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
        return [event for event in self.events if event.created_at >= cutoff_time]

    def get_critical_events(self, hours: int = 24) -> List[BGPSessionEvent]:
        """Get critical events from the last N hours."""
        recent_events = self.get_recent_events(hours)
        return [event for event in recent_events if event.event_type.is_critical_event()]

    def get_event_counts_by_type(self, hours: int = 24) -> Dict[str, int]:
        """Get event counts by type for the last N hours."""
        recent_events = self.get_recent_events(hours)
        counts = {}
        for event in recent_events:
            event_type = event.event_type.value
            counts[event_type] = counts.get(event_type, 0) + 1
        return counts

    def calculate_session_stability(self, hours: int = 24) -> float:
        """Calculate session stability score based on recent events."""
        recent_events = self.get_recent_events(hours)
        if not recent_events:
            return 1.0
            
        # Count destabilizing events
        destabilizing_events = [
            BGPSessionEventType.SESSION_TERMINATED,
            BGPSessionEventType.SESSION_RESET,
            BGPSessionEventType.CONNECTION_FAILED,
            BGPSessionEventType.NOTIFICATION_SENT,
            BGPSessionEventType.NOTIFICATION_RECEIVED,
        ]
        
        destabilizing_count = sum(
            1 for event in recent_events 
            if event.event_type in destabilizing_events
        )
        
        # Calculate stability (lower destabilizing events = higher stability)
        max_expected_events = 10  # Threshold for completely unstable
        stability = max(0.0, 1.0 - (destabilizing_count / max_expected_events))
        return stability


class BGPSessionInfo(TimestampMixin):
    """
    Comprehensive BGP session information consolidating state, history, and monitoring.
    
    This model serves as the primary BGP session representation, providing complete
    session lifecycle tracking, operational monitoring, and historical analysis.
    """
    
    # Core session information
    session_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique session identifier"
    )
    
    # Current state
    current_state: BGPSessionState = Field(description="Current session state")
    
    # Historical tracking
    history: BGPSessionHistory = Field(description="Session event and state history")
    
    # Operational configuration
    monitoring_config: Dict[str, Any] = Field(
        default_factory=dict,
        description="Monitoring configuration parameters"
    )
    
    # SLA and performance targets
    sla_targets: Dict[str, Union[int, float]] = Field(
        default_factory=dict,
        description="SLA targets for this session"
    )
    
    # Alerting configuration
    alert_config: Dict[str, Any] = Field(
        default_factory=dict,
        description="Alerting configuration"
    )
    
    # Automation configuration
    automation_enabled: bool = Field(default=False, description="Whether automation is enabled")
    automation_rules: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Configured automation rules"
    )
    
    # Business context
    business_criticality: str = Field(
        default="low",
        description="Business criticality level"
    )
    service_impact: Optional[str] = Field(
        default=None,
        description="Service impact description"
    )
    
    # Troubleshooting aids
    troubleshooting_runbook_url: Optional[str] = Field(
        default=None,
        description="URL to troubleshooting runbook"
    )
    escalation_contacts: List[str] = Field(
        default_factory=list,
        description="Escalation contact list"
    )
    
    # Tags and metadata
    tags: Dict[str, str] = Field(default_factory=dict, description="Session tags")
    custom_attributes: Dict[str, Any] = Field(
        default_factory=dict,
        description="Custom attributes"
    )

    @model_validator(mode='before')
    def ensure_history_session_id(cls, values):
        """Ensure history has the correct session ID."""
        if isinstance(values, dict):
            session_id = values.get('session_id')
            if session_id and 'history' in values:
                if isinstance(values['history'], dict):
                    values['history']['session_id'] = session_id
                elif hasattr(values['history'], 'session_id'):
                    values['history'].session_id = session_id
        return values

    def add_event(self, event_type: BGPSessionEventType, description: str,
                  severity: str = "info", details: Optional[Dict[str, Any]] = None) -> BGPSessionEvent:
        """Add a new session event."""
        event = BGPSessionEvent(
            event_type=event_type,
            description=description,
            severity=severity,
            details=details or {},
            session_id=self.session_id,
            peer_asn=self.current_state.peer_asn,
            local_asn=self.current_state.local_asn,
            region=self.current_state.region
        )
        
        self.history.add_event(event)
        return event

    def transition_state(self, new_state: BGPPeerState, 
                        reason: Optional[str] = None) -> None:
        """Transition session to new state and record event."""
        old_state = self.current_state.current_state
        self.current_state.transition_to_state(new_state, reason)
        
        # Record state change in history
        self.history.add_state_change(
            old_state,
            new_state,
            datetime.now(timezone.utc),
            reason
        )
        
        # Add corresponding event
        self.add_event(
            BGPSessionEventType.SESSION_ESTABLISHED if new_state == BGPPeerState.ESTABLISHED
            else BGPSessionEventType.SESSION_TERMINATED,
            f"Session transitioned from {old_state} to {new_state}",
            "info" if new_state == BGPPeerState.ESTABLISHED else "warning",
            {"previous_state": old_state, "new_state": new_state, "reason": reason}
        )

    def check_sla_compliance(self) -> Dict[str, bool]:
        """Check SLA compliance for configured targets."""
        compliance = {}
        
        if "uptime_percentage" in self.sla_targets:
            target = self.sla_targets["uptime_percentage"]
            actual = self.current_state.get_uptime_percentage()
            compliance["uptime_percentage"] = actual >= target
            
        if "max_flaps_per_hour" in self.sla_targets:
            target = self.sla_targets["max_flaps_per_hour"]
            recent_events = self.history.get_recent_events(1)  # Last hour
            flap_events = [e for e in recent_events 
                          if e.event_type in (BGPSessionEventType.SESSION_TERMINATED,
                                             BGPSessionEventType.SESSION_ESTABLISHED)]
            compliance["max_flaps_per_hour"] = len(flap_events) <= target
            
        return compliance

    def get_health_summary(self) -> Dict[str, Any]:
        """Get comprehensive health summary."""
        self.current_state.update_session_duration()
        
        return {
            "session_id": self.session_id,
            "current_state": self.current_state.current_state,
            "health_status": self.current_state.health_status,
            "is_established": self.current_state.is_established(),
            "uptime_hours": self.current_state.session_duration_seconds / 3600,
            "uptime_percentage": self.current_state.get_uptime_percentage(),
            "establishment_attempts": self.current_state.establishment_attempts,
            "successful_establishments": self.current_state.successful_establishments,
            "session_resets": self.current_state.session_resets,
            "error_count": self.current_state.error_count,
            "last_error": self.current_state.last_error,
            "keepalive_overdue": self.current_state.is_keepalive_overdue(),
            "recent_critical_events": len(self.history.get_critical_events()),
            "session_stability": self.history.calculate_session_stability(),
            "sla_compliance": self.check_sla_compliance(),
            "monitoring_enabled": self.current_state.monitoring_enabled,
            "automation_enabled": self.automation_enabled,
            "business_criticality": self.business_criticality,
            "last_updated": self.updated_at.isoformat(),
        }

    def requires_attention(self) -> bool:
        """Check if session requires immediate attention."""
        return (
            not self.current_state.is_established() or
            self.current_state.health_status in (HealthStatus.UNHEALTHY, HealthStatus.CRITICAL) or
            self.current_state.is_keepalive_overdue() or
            len(self.history.get_critical_events(1)) > 0  # Critical events in last hour
        )

    def trigger_automation(self, rule_name: str, action: str) -> None:
        """Trigger an automation action."""
        self.add_event(
            BGPSessionEventType.AUTOMATED_REMEDIATION,
            f"Automation rule '{rule_name}' triggered action: {action}",
            "info",
            {"rule_name": rule_name, "action": action, "triggered_at": datetime.now(timezone.utc).isoformat()}
        )