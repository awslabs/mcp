"""
Base data models for CloudWAN MCP Server.

This module contains base classes and common data structures used across
all MCP tool responses.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator


class CloudWANOperationError(Exception):
    """Exception raised for CloudWAN operations errors."""

    def __init__(
        self,
        message: str,
        operation_id: Optional[str] = None,
        status_code: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        self.message = message
        self.operation_id = operation_id
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)


class BaseResponse(BaseModel):
    """Base response model for all MCP tool responses."""

    timestamp: datetime = Field(default_factory=datetime.now)
    operation_id: Optional[str] = None
    regions_analyzed: List[str] = Field(default_factory=list)
    status: str = Field(default="success")  # success, partial, error
    error_message: Optional[str] = None
    error_details: Optional[Dict[str, Any]] = Field(
        default=None, description="Detailed error information"
    )
    success_count: int = Field(default=0, description="Number of successful operations")
    failure_count: int = Field(default=0, description="Number of failed operations")

    @field_validator("status")
    @classmethod
    def validate_status(cls, v):
        """Validate status field."""
        if v not in ["success", "partial", "error"]:
            raise ValueError(f"Invalid status: {v}. Must be one of: success, partial, error")
        return v


class AWSResource(BaseModel):
    """Base AWS resource model."""

    resource_id: str
    resource_type: str
    region: str
    arn: Optional[str] = None
    tags: Dict[str, str] = Field(default_factory=dict)
    created_date: Optional[datetime] = None


class RouteInfo(BaseModel):
    """Route table entry information."""

    destination_cidr: str
    state: str  # active, blackhole, pending
    route_type: str  # static, propagated, local
    target_type: Optional[str] = None  # gateway, attachment, peering
    target_id: Optional[str] = None
    origin: Optional[str] = None  # which attachment or service created this route
    prefix_length: int = Field(ge=0, le=32)


class AttachmentInfo(BaseModel):
    """Network attachment information."""

    attachment_id: str
    attachment_type: str  # vpc, transit-gateway, direct-connect-gateway
    state: str  # available, pending, deleting, etc.
    resource_arn: Optional[str] = None
    core_network_id: Optional[str] = None
    segment_name: Optional[str] = None
    edge_location: Optional[str] = None
    tags: Dict[str, str] = Field(default_factory=dict)


class SecurityGroupInfo(BaseModel):
    """Security group information."""

    group_id: str
    group_name: str
    description: str = ""
    vpc_id: str
    rules_inbound: List[Dict[str, Any]] = Field(default_factory=list)
    rules_outbound: List[Dict[str, Any]] = Field(default_factory=list)


class NetworkHop(BaseModel):
    """Network path hop information."""

    hop_number: int
    hop_type: str  # route-table, security-group, network-acl, firewall
    resource_id: str
    resource_type: str
    region: str
    action: str  # allow, deny, inspect
    details: Dict[str, Any] = Field(default_factory=dict)


class InspectionPoint(BaseModel):
    """Network inspection point information."""

    vpc_id: str
    region: str
    firewall_arn: Optional[str] = None
    inspection_type: str  # network-firewall, security-group, nacl
    rules_evaluated: List[Dict[str, Any]] = Field(default_factory=list)
    verdict: str  # allow, deny, drop


class IPContext(BaseModel):
    """IP address context information."""

    ip_address: str
    region: str
    availability_zone: Optional[str] = None
    vpc_id: Optional[str] = None
    subnet_id: Optional[str] = None
    eni_id: Optional[str] = None
    resource_type: str
    resource_id: Optional[str] = None
    is_public: bool = False
    segment_name: Optional[str] = None  # CloudWAN segment if attached


class SecurityGroupRule(BaseModel):
    """Security group rule information."""

    ip_protocol: str
    from_port: Optional[int] = None
    to_port: Optional[int] = None
    cidr_blocks: List[str] = Field(default_factory=list)
    security_group_ids: List[str] = Field(default_factory=list)
    description: str = ""
    is_egress: bool = False


class RouteTableInfo(BaseModel):
    """Route table information."""

    route_table_id: str
    vpc_id: str
    is_main: bool = False
    routes: List[RouteInfo] = Field(default_factory=list)
    associated_subnets: List[str] = Field(default_factory=list)
    tags: Dict[str, str] = Field(default_factory=dict)


class SegmentAllowFilter(BaseModel):
    """CloudWAN segment allow filter configuration."""

    types: List[str] = Field(default_factory=list, description="Allowed attachment types")


class NetworkSegment(BaseModel):
    """CloudWAN network segment information."""

    name: str = Field(description="Segment name")
    description: Optional[str] = Field(default=None, description="Segment description")
    edge_locations: List[str] = Field(
        default_factory=list, description="Edge locations for this segment"
    )
    shared_segments: List[str] = Field(
        default_factory=list, description="Segments this segment shares routes with"
    )
    allow_filter: Optional[SegmentAllowFilter] = Field(
        default=None, description="Attachment type filters"
    )
    requires_attachment_acceptance: bool = Field(
        default=False, description="Whether attachments require acceptance"
    )
    attachment_count: int = Field(default=0, description="Number of attachments in this segment")
    isolate_attachments: bool = Field(
        default=False, description="Whether attachments are isolated from each other"
    )


class CloudWANSegmentsResponse(BaseResponse):
    """Response model for CloudWAN segments discovery."""

    core_network_id: str = Field(description="Core network identifier")
    segments: List[NetworkSegment] = Field(default_factory=list, description="Network segments")
    total_segments: int = Field(default=0, description="Total number of segments")
    policy_version: Optional[str] = Field(default=None, description="Core network policy version")
    operation_details: Dict[str, Any] = Field(
        default_factory=dict, description="Additional operation details"
    )
    cache_used: bool = Field(
        default=False, description="Whether the response was served from cache"
    )
    cache_ttl: Optional[int] = Field(default=None, description="Cache TTL in seconds if cached")

    def add_segment(self, segment: NetworkSegment) -> None:
        """Add a segment to the response."""
        self.segments.append(segment)
        self.total_segments = len(self.segments)

    def merge(self, other: "CloudWANSegmentsResponse") -> None:
        """Merge another response into this one."""
        # Merge segments
        existing_names = {segment.name for segment in self.segments}
        for segment in other.segments:
            if segment.name not in existing_names:
                self.segments.append(segment)
                existing_names.add(segment.name)

        # Update counts
        self.total_segments = len(self.segments)

        # Merge regions
        self.regions_analyzed = list(set(self.regions_analyzed + other.regions_analyzed))

        # Merge operation details
        self.operation_details.update(other.operation_details)

        # Update status if needed
        if self.status == "success" and other.status != "success":
            self.status = "partial"

        # Merge error messages if any
        if other.error_message and not self.error_message:
            self.error_message = other.error_message
        elif other.error_message and self.error_message:
            self.error_message = f"{self.error_message}; {other.error_message}"

        # Update success/failure counts
        self.success_count += other.success_count
        self.failure_count += other.failure_count

        # Handle cache fields
        # If either response used cache, consider the merged response as using cache
        if other.cache_used:
            self.cache_used = True

        # If both have cache_ttl, use the smaller (more conservative) value
        if self.cache_ttl is not None and other.cache_ttl is not None:
            self.cache_ttl = min(self.cache_ttl, other.cache_ttl)
        elif other.cache_ttl is not None:
            self.cache_ttl = other.cache_ttl

        # Add cache information to operation details
        if self.cache_used:
            self.operation_details["cache"] = {"used": True, "ttl": self.cache_ttl}


class IPResourceResponse(BaseResponse):
    """Response for IP resource resolution operations."""
    
    ip_address: str
    resource_details: Dict[str, Any] = Field(default_factory=dict)
    resource_type: Optional[str] = None
    vpc_context: Optional[Dict[str, Any]] = Field(default_factory=dict)
    security_groups: List[Dict[str, Any]] = Field(default_factory=list)
    route_tables: List[Dict[str, Any]] = Field(default_factory=list)
    network_interfaces: List[Dict[str, Any]] = Field(default_factory=list)
    dns_resolution: Optional[str] = None
    is_reachable: Optional[bool] = None
