"""
Security analysis data models for CloudWAN MCP Server.

This module contains Pydantic models for security tools, including:
- Network Firewall logs
- VPC Flow Logs
- Security analysis responses
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field

from .base import BaseResponse


class FirewallAction(str, Enum):
    """Network Firewall action types."""

    PASS = "PASS"
    DROP = "DROP"
    ALERT = "ALERT"
    REJECT = "REJECT"


class FirewallLogType(str, Enum):
    """Types of AWS Network Firewall logs."""

    ALERT = "ALERT"
    FLOW = "FLOW"


class FirewallLogDestination(str, Enum):
    """Firewall log destination types."""

    S3 = "S3"
    CLOUDWATCH_LOGS = "CLOUDWATCH_LOGS"
    KINESIS_DATA_FIREHOSE = "KINESIS_DATA_FIREHOSE"


class VPCFlowLogStatus(str, Enum):
    """VPC Flow Log traffic status."""

    ACCEPT = "ACCEPT"
    REJECT = "REJECT"


class VPCFlowLogFormat(str, Enum):
    """VPC Flow Log format versions."""

    DEFAULT = "default"
    CUSTOM = "custom"


class FirewallAlert(BaseModel):
    """Network Firewall alert event."""

    timestamp: datetime
    firewall_name: str
    availability_zone: Optional[str] = None
    event_timestamp: datetime
    event: Dict[str, Any]
    src_ip: str
    src_port: int
    dest_ip: str
    dest_port: int
    protocol: str
    alert_id: Optional[str] = None
    alert_severity: Optional[str] = None
    alert_message: Optional[str] = None
    rule_id: Optional[str] = None
    rule_group: Optional[str] = None
    action: FirewallAction


class FirewallFlowRecord(BaseModel):
    """Network Firewall flow record."""

    timestamp: datetime
    firewall_name: str
    availability_zone: Optional[str] = None
    event_timestamp: datetime
    event: Dict[str, Any]
    src_ip: str
    src_port: int
    dest_ip: str
    dest_port: int
    protocol: str
    tcp_flags: Optional[int] = None
    packets: Optional[int] = None
    bytes: Optional[int] = None
    action: FirewallAction
    rule_group_id: Optional[str] = None
    flow_direction: Optional[str] = None


class VPCFlowLogRecord(BaseModel):
    """VPC Flow Log record."""

    version: int = 2
    account_id: str
    interface_id: str
    src_addr: str
    dst_addr: str
    src_port: int
    dst_port: int
    protocol: int
    packets: int
    bytes: int
    start_time: datetime
    end_time: datetime
    action: VPCFlowLogStatus
    log_status: str
    vpc_id: Optional[str] = None
    subnet_id: Optional[str] = None
    instance_id: Optional[str] = None
    region: Optional[str] = None
    az_id: Optional[str] = None
    sublocation_type: Optional[str] = None
    sublocation_id: Optional[str] = None
    tcp_flags: Optional[int] = None
    type: Optional[str] = None
    pkt_src_addr: Optional[str] = None
    pkt_dst_addr: Optional[str] = None
    flow_direction: Optional[str] = None
    traffic_path: Optional[int] = None


class FirewallLogFilter(BaseModel):
    """Filter criteria for firewall logs."""

    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    src_ip: Optional[str] = None
    dest_ip: Optional[str] = None
    src_port: Optional[int] = None
    dest_port: Optional[int] = None
    protocol: Optional[str] = None
    action: Optional[FirewallAction] = None
    min_packets: Optional[int] = None
    min_bytes: Optional[int] = None
    rule_id: Optional[str] = None
    rule_group: Optional[str] = None
    alert_severity: Optional[str] = None
    firewall_name: Optional[str] = None
    regions: List[str] = Field(default_factory=list)


class VPCFlowLogFilter(BaseModel):
    """Filter criteria for VPC Flow Logs."""

    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    src_addr: Optional[str] = None
    dst_addr: Optional[str] = None
    src_port: Optional[int] = None
    dst_port: Optional[int] = None
    protocol: Optional[int] = None
    action: Optional[VPCFlowLogStatus] = None
    min_packets: Optional[int] = None
    min_bytes: Optional[int] = None
    interface_id: Optional[str] = None
    vpc_id: Optional[str] = None
    subnet_id: Optional[str] = None
    instance_id: Optional[str] = None
    regions: List[str] = Field(default_factory=list)


class FirewallLogSummary(BaseModel):
    """Summary statistics for firewall logs."""

    total_records: int
    time_range: Dict[str, datetime]
    records_by_action: Dict[str, int]
    top_source_ips: Dict[str, int]
    top_destination_ips: Dict[str, int]
    top_source_ports: Dict[int, int]
    top_destination_ports: Dict[int, int]
    records_by_protocol: Dict[str, int]
    alerts_by_severity: Dict[str, int] = Field(default_factory=dict)
    bytes_transferred: Optional[int] = None
    packets_transferred: Optional[int] = None


class FirewallLogResponse(BaseResponse):
    """Response for firewall logs analysis."""

    log_type: str  # "NetworkFirewall", "VPCFlowLogs", or "Combined"
    summary: FirewallLogSummary
    network_firewall_alerts: List[FirewallAlert] = Field(default_factory=list)
    network_firewall_flows: List[FirewallFlowRecord] = Field(default_factory=list)
    vpc_flow_logs: List[VPCFlowLogRecord] = Field(default_factory=list)
    filter_applied: Union[FirewallLogFilter, VPCFlowLogFilter, None] = None
    total_records: int
    records_returned: int
    has_more: bool = False
    next_token: Optional[str] = None
    security_analysis: Optional["FirewallSecurityAnalysisResponse"] = None


class SecurityIssue(BaseModel):
    """Security issue identified in logs."""

    issue_id: str
    issue_type: str
    severity: str  # "CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"
    description: str
    source_records: List[Dict[str, Any]]
    affected_resources: List[str]
    recommendation: str
    timestamp: datetime = Field(default_factory=datetime.now)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class FirewallSecurityAnalysisResponse(BaseResponse):
    """Response for security analysis of firewall logs."""

    issues_found: int
    critical_issues: int
    high_issues: int
    medium_issues: int
    low_issues: int
    info_issues: int
    security_issues: List[SecurityIssue]
    analysis_metadata: Dict[str, Any] = Field(default_factory=dict)
    recommendations: List[str] = Field(default_factory=list)
