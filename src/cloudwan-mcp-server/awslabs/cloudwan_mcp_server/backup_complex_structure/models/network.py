"""
Network analysis data models for CloudWAN MCP Server.

This module contains Pydantic models for network discovery, route analysis,
path tracing responses, and BGP protocol analysis.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Set
from dataclasses import dataclass, field
from pydantic import BaseModel, Field, model_validator

from .base import (
    BaseResponse,
    RouteInfo,
    AttachmentInfo,
    SecurityGroupInfo,
    SecurityGroupRule,
    NetworkHop,
    InspectionPoint,
    IPContext,
    RouteTableInfo,
)


class NetworkElementType(str, Enum):
    """Types of network elements in topology."""

    GLOBAL_NETWORK = "global_network"
    CORE_NETWORK = "core_network"
    VPC = "vpc"
    TRANSIT_GATEWAY = "transit_gateway"
    SUBNET = "subnet"
    SECURITY_GROUP = "security_group"
    ROUTE_TABLE = "route_table"
    NETWORK_INTERFACE = "network_interface"
    LOAD_BALANCER = "load_balancer"
    NAT_GATEWAY = "nat_gateway"
    INTERNET_GATEWAY = "internet_gateway"
    VPC_ENDPOINT = "vpc_endpoint"
    DIRECT_CONNECT = "direct_connect"
    VPN_CONNECTION = "vpn_connection"
    NETWORK_FUNCTION_GROUP = "network_function_group"
    SEGMENT = "segment"
    ATTACHMENT = "attachment"


class ConnectionType(str, Enum):
    """Types of connections between network elements."""

    ATTACHMENT = "attachment"
    PEERING = "peering"
    ROUTING = "routing"
    ASSOCIATION = "association"
    PROPAGATION = "propagation"
    BGP_SESSION = "bgp_session"
    PHYSICAL = "physical"
    SEGMENT_CONNECTION = "segment_connection"  
    NETWORK_FUNCTION = "network_function"
    CROSS_ACCOUNT = "cross_account"


@dataclass
class NetworkElement:
    """Represents a network element in the topology."""
    # ... existing implementation ...


@dataclass
class NetworkConnection:
    """Represents a connection between network elements."""
    # ... existing implementation ...


@dataclass
class NetworkTopology:
    """Represents a complete network topology."""
    # ... existing implementation ...


class AttachmentType(str, Enum):
    """CloudWAN attachment types."""
    
    VPC = "VPC"
    TRANSIT_GATEWAY = "TRANSIT_GATEWAY"
    DIRECT_CONNECT_GATEWAY = "DIRECT_CONNECT_GATEWAY"
    SITE_TO_SITE_VPN = "SITE_TO_SITE_VPN"


class AttachmentState(str, Enum):
    """CloudWAN attachment states."""
    
    CREATING = "CREATING"
    PENDING = "PENDING"
    AVAILABLE = "AVAILABLE"
    DELETING = "DELETING"
    DELETED = "DELETED"
    FAILED = "FAILED"
    UPDATING = "UPDATING"


class BGPPeerState(str, Enum):
    """BGP Finite State Machine states per RFC 4271."""
    # ... existing enum values ...


class BGPRouteType(str, Enum):
    """BGP route types and origins."""
    # ... existing enum values ...


class BGPPeerInfo(BaseModel):
    """BGP peer relationship information."""
    # ... existing implementation ...


class BGPRouteInfo(BaseModel):
    """BGP route information with protocol-level details."""
    # ... existing implementation ...


class BGPSessionMetrics(BaseModel):
    """BGP session performance metrics."""
    # ... existing implementation ...


class BGPAnalysisResponse(BaseResponse):
    """Response for comprehensive BGP protocol analysis."""
    # ... existing implementation ...


class IPDetailsResponse(BaseResponse):
    """Response for IP address resolution and context analysis."""
    
    ip_address: str = Field(description="The IP address that was searched")
    context: Optional[IPContext] = Field(default=None, description="IP context information")
    security_groups: List[SecurityGroupInfo] = Field(
        default_factory=list, description="Associated security groups"
    )
    route_tables: List[RouteTableInfo] = Field(
        default_factory=list, description="Associated route tables"
    )
    cloudwan_segment: Optional[str] = Field(
        default=None, description="CloudWAN segment if applicable"
    )
    is_segment_isolated: bool = Field(
        default=False, description="Whether IP is in an isolated segment"
    )
    dns_resolution: Optional[str] = Field(default=None, description="DNS name if resolved")
    
    def __init__(self, **data):
        """Initialize IPDetailsResponse with proper defaults."""
        super().__init__(**data)
        # Set status based on whether context was found (BaseResponse uses 'status' not 'success')
        if 'status' not in data:
            self.status = "success" if self.context is not None else "error"


class TGWRouteTableInfo(BaseModel):
    """Transit Gateway route table information."""
    # ... existing implementation ...


class TransitGatewayInfo(BaseModel):
    """Transit Gateway information."""
    # ... existing implementation ...


class TGWPeeringInfo(BaseModel):
    """Transit Gateway peering connection information."""
    # ... existing implementation ...


class RouteOverlapInfo(BaseModel):
    """Information about route overlaps in Transit Gateway route tables."""
    # ... existing implementation ...


class BlackholeRouteInfo(BaseModel):
    """Information about blackhole routes in Transit Gateway route tables."""
    # ... existing implementation ...


class CrossRegionRouteInfo(BaseModel):
    """Information about cross-region routes via Transit Gateway peering."""
    # ... existing implementation ...


class RouteSummaryStats(BaseModel):
    """Summary statistics for Transit Gateway routes."""
    # ... existing implementation ...


class TGWRouteAnalysisResponse(BaseResponse):
    """Response for comprehensive Transit Gateway route analysis."""
    # ... existing implementation ...


class CoreNetworkInfo(BaseModel):
    """Core Network information."""
    
    core_network_id: str = Field(description="Core Network identifier")
    core_network_arn: str = Field(description="Core Network ARN")
    global_network_id: str = Field(description="Associated Global Network ID")
    description: Optional[str] = Field(default=None, description="Core Network description")
    state: str = Field(description="Core Network state")
    edge_locations: List[str] = Field(default_factory=list, description="Edge locations")
    segments: List[str] = Field(default_factory=list, description="Network segments")
    tags: Dict[str, str] = Field(default_factory=dict, description="Resource tags")
    created_at: Optional[datetime] = Field(default=None, description="Creation timestamp")
    policy_version_id: Optional[int] = Field(default=None, description="Current policy version")


class SegmentRouteInfo(BaseModel):
    """CloudWAN segment route information."""
    # ... existing implementation ...


class SegmentRoutesResponse(BaseResponse):
    """Response for segment route enumeration."""
    # ... existing implementation ...


class TGWPeerInfo(BaseModel):
    """Transit Gateway peer information with enhanced details."""
    # ... existing implementation ...


class TGWPeeringConnection(BaseModel):
    """Transit Gateway peering connection with enhanced routing context."""
    # ... existing implementation ...


class TGWPeerDiscoveryResponse(BaseResponse):
    """Response for get_tgw_peers tool - focused peer discovery."""
    # ... existing implementation ...


class TGWPeerAnalysisResponse(BaseResponse):
    """Response for comprehensive Transit Gateway peer analysis."""
    # ... existing implementation ...


class NetworkPathTraceResponse(BaseResponse):
    """Response for end-to-end network path tracing."""
    # ... existing implementation ...


class VPCInfo(BaseModel):
    """VPC information with CloudWAN context."""
    __module__ = 'awslabs.cloudwan_mcp_server.models.network'
    
    vpc_id: str
    region: str
    cidr_block: str
    additional_cidr_blocks: List[str] = Field(default_factory=list)
    state: str
    is_default: bool = False
    dhcp_options_id: Optional[str] = None
    instance_tenancy: str = "default"
    attachments: List[AttachmentInfo] = Field(default_factory=list)
    tags: Dict[str, str] = Field(default_factory=dict)


class VPCDiscoveryResponse(BaseResponse):
    """Response for VPC discovery and attachment analysis."""
    
    vpcs: List[VPCInfo] = Field(default_factory=list, description="Discovered VPCs")
    total_count: int = Field(default=0, description="Total number of VPCs found")
    regions_searched: List[str] = Field(
        default_factory=list, description="Regions that were searched"
    )
    cloudwan_attachments: List[AttachmentInfo] = Field(
        default_factory=list, description="CloudWAN attachments found"
    )
    
    def __init__(self, **data):
        """Initialize VPCDiscoveryResponse with proper defaults."""
        super().__init__(**data)
        if 'total_count' not in data:
            self.total_count = len(self.vpcs)
    
    def add_vpc(self, vpc: VPCInfo) -> None:
        """Add a VPC to the response."""
        self.vpcs.append(vpc)
        self.total_count = len(self.vpcs)


class GlobalNetworkInfo(BaseModel):
    """Global Network information with enhanced details."""
    
    global_network_id: str = Field(description="Global Network identifier")
    global_network_arn: str = Field(description="Global Network ARN")
    description: Optional[str] = Field(default=None, description="Network description")
    state: str = Field(description="Global Network state")
    created_at: Optional[datetime] = Field(default=None, description="Creation timestamp")
    tags: Dict[str, str] = Field(default_factory=dict, description="Resource tags")
    core_network_arn: Optional[str] = Field(default=None, description="Associated Core Network ARN")
    region_count: int = Field(default=0, description="Number of regions with resources")
    device_count: int = Field(default=0, description="Number of devices")
    site_count: int = Field(default=0, description="Number of sites")
    link_count: int = Field(default=0, description="Number of links")


class GlobalNetworksResponse(BaseResponse):
    """Response for Global Network discovery."""
    
    global_networks: List[GlobalNetworkInfo] = Field(
        default_factory=list,
        description="Discovered Global Networks"
    )
    total_count: int = Field(
        default=0,
        description="Total number of Global Networks found",
        validate_default=True
    )
    regions_searched: List[str] = Field(
        default_factory=list,
        description="Regions that were searched"
    )
    
    @model_validator(mode="after")
    def set_counts(self) -> "GlobalNetworksResponse":
        """Pydantic-native count management"""
        self.total_count = len(self.global_networks)
        return self
    
    def add_global_network(self, network: GlobalNetworkInfo) -> None:
        """AWS Labs pattern for mutation"""
        self.global_networks.append(network)
        self.total_count = len(self.global_networks)


class NetworkFunctionGroup(BaseModel):
    """Network Function Group information."""
    # ... existing implementation ...


class NFGConfigAnalysisResponse(BaseResponse):
    """Response for Network Function Group configuration analysis."""
    # ... existing implementation ...


class MultiNFGAnalysisResponse(BaseResponse):
    """Response for analyzing multiple Network Function Groups."""
    # ... existing implementation ...


class CoreNetworksResponse(BaseResponse):
    """Response for Core Network discovery."""
    
    global_network_id: str = Field(description="Global Network identifier")
    core_networks: List[CoreNetworkInfo] = Field(
        default_factory=list,
        description="Discovered Core Networks"
    )
    total_count: int = Field(
        default=0,
        description="Total number of Core Networks found",
        validate_default=True
    )
    policy_documents: Dict[str, Dict[str, Any]] = Field(
        default_factory=dict,
        description="Policy documents by Core Network ID"
    )
    
    @model_validator(mode="after")
    def set_counts(self) -> "CoreNetworksResponse":
        """Pydantic-native count management"""
        self.total_count = len(self.core_networks)
        return self
    
    def add_core_network(self, network: CoreNetworkInfo, policy_doc: Optional[Dict[str, Any]] = None) -> None:
        """AWS Labs pattern for mutation"""
        self.core_networks.append(network)
        self.total_count = len(self.core_networks)
        if policy_doc:
            self.policy_documents[network.core_network_id] = policy_doc


class TGWRouteOperationResponse(BaseResponse):
    """Response for Transit Gateway route operations (list/create/delete/blackhole)."""
    # ... existing implementation ...


class NFGConfigIssue(BaseModel):
    """Network Function Group configuration issue."""
    # ... existing implementation ...


class NFGEvaluationResult(BaseModel):
    """Network Function Group evaluation result."""
    # ... existing implementation ...


class NFGSegmentAction(BaseModel):
    """Network Function Group segment action configuration."""
    # ... existing implementation ...


class NetworkFunctionType(str, Enum):
    """Network function types for NFGs."""
    # ... existing enum values ...


class IPResolutionResult(BaseModel):
    """Result of IP address resolution."""
    # ... existing implementation ...


class NetworkResource(BaseModel):
    """Network resource information."""
    # ... existing implementation ...


class RoutingBehavior(BaseModel):
    """Network routing behavior configuration."""
    # ... existing implementation ...
