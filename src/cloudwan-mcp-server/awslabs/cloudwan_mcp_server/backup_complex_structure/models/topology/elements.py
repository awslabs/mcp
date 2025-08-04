"""
Specialized network element models for CloudWAN MCP Server.
"""
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Literal
from enum import Enum
import logging
from ipaddress import ip_network

from pydantic import BaseModel, Field, field_validator

from .topology import NetworkElement
from ..shared.enums import (
    SecurityThreatLevel
)

logger = logging.getLogger(__name__)

class VPCSecurityMode(str, Enum):
    OPEN = "open"
    STANDARD = "standard"
    RESTRICTED = "restricted"
    ISOLATED = "isolated"

class TransitGatewayMode(str, Enum):
    DEFAULT = "default"
    ISOLATED = "isolated"
    SHARED = "shared"
    CUSTOM = "custom"

class NetworkFunctionType(str, Enum):
    FIREWALL = "firewall"
    LOAD_BALANCER = "load_balancer"
    NAT_GATEWAY = "nat_gateway"
    PROXY = "proxy"
    VPN_GATEWAY = "vpn_gateway"
    INTRUSION_DETECTION = "intrusion_detection"
    DATA_LOSS_PREVENTION = "data_loss_prevention"
    WEB_APPLICATION_FIREWALL = "web_application_firewall"
    API_GATEWAY = "api_gateway"
    CONTENT_DELIVERY_NETWORK = "content_delivery_network"
    DNS_RESOLVER = "dns_resolver"
    CUSTOM = "custom"

class SecurityAssessment(BaseModel):
    security_score: float = Field(ge=0.0, le=1.0)
    threat_level: SecurityThreatLevel = Field(default=SecurityThreatLevel.UNKNOWN)
    vulnerabilities: List[Dict[str, Any]] = Field(default_factory=list)
    compliance_status: Dict[str, bool] = Field(default_factory=dict)
    last_assessment: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    recommendations: List[str] = Field(default_factory=list)

class VPCElement(NetworkElement):
    element_id: str
    element_type: Literal['vpc', 'tgw', 'vpn'] = Field(...)
    cidr_blocks: list[str]
    region: str
    state: str
    
    vpc_id: str = Field(description="VPC identifier")
    cidr_block: str = Field(description="Primary CIDR block")
    secondary_cidr_blocks: List[str] = Field(default_factory=list)
    enable_dns_hostnames: bool = Field(default=True)
    enable_dns_support: bool = Field(default=True)
    dhcp_options_set_id: Optional[str] = None
    subnet_ids: Set[str] = Field(default_factory=set)
    public_subnet_ids: Set[str] = Field(default_factory=set)
    private_subnet_ids: Set[str] = Field(default_factory=set)
    availability_zones: Set[str] = Field(default_factory=set)
    internet_gateway_id: Optional[str] = None
    nat_gateway_ids: Set[str] = Field(default_factory=set)
    vpn_gateway_id: Optional[str] = None
    main_route_table_id: str = Field(description="Main route table ID")
    custom_route_table_ids: Set[str] = Field(default_factory=set)
    security_mode: VPCSecurityMode = Field(default=VPCSecurityMode.STANDARD)
    default_security_group_id: str = Field(description="Default security group ID")
    security_assessment: Optional[SecurityAssessment] = None
    network_performance: Optional[Dict[str, Any]] = Field(default_factory=dict)
    bandwidth_utilization: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    cloudwan_attachment_ids: Set[str] = Field(default_factory=set)
    transit_gateway_attachments: Set[str] = Field(default_factory=set)
    
    @field_validator('cidr_block')
    @classmethod
    def validate_cidr_block(cls, v):
        try: ip_network(v, strict=False)
        except ValueError: raise ValueError(f"Invalid CIDR: {v}")
        return v
    
    @field_validator('secondary_cidr_blocks')
    @classmethod
    def validate_secondary_cidrs(cls, v):
        for cidr in v:
            try: ip_network(cidr, strict=False)
            except ValueError: raise ValueError(f"Invalid CIDR: {cidr}")
        return v
    
    def add_subnet(self, subnet_id: str, is_public: bool = False) -> None:
        self.subnet_ids.add(subnet_id)
        self.public_subnet_ids.add(subnet_id) if is_public else self.private_subnet_ids.add(subnet_id)
        self.update_timestamp()

class IPDetailsResponse(BaseModel):
    ip_address: str
    associated_resources: list[VPCElement]
    routing_path: list[str]

class TransitGatewayElement(NetworkElement):
    transit_gateway_id: str
    amazon_side_asn: int
    routing_mode: TransitGatewayMode = Field(default=TransitGatewayMode.DEFAULT)
    default_route_table_association: bool = True
    auto_accept_shared_attachments: bool = False
    default_route_table_id: Optional[str] = None
    custom_route_table_ids: Set[str] = Field(default_factory=set)
    vpc_attachment_ids: Set[str] = Field(default_factory=set)
    vpn_attachment_ids: Set[str] = Field(default_factory=set)
    peering_attachment_ids: Set[str] = Field(default_factory=set)
    peering_connections: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    multicast_support: bool = False
    core_network_attachment_id: Optional[str] = None

class CloudWANElement(NetworkElement):
    cloudwan_element_type: str
    policy_document: Optional[Dict[str, Any]] = None
    global_network_id: str
    edge_locations: Set[str] = Field(default_factory=set)
    segments: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    attachments: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    network_function_groups: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    policy_version: Optional[str] = None
    policy_errors: List[Dict[str, Any]] = Field(default_factory=list)

class SecurityElement(NetworkElement):
    security_element_type: str
    security_function: str
    security_rules: List[Dict[str, Any]] = Field(default_factory=list)
    threat_detection_enabled: bool = False
    compliance_frameworks: Set[str] = Field(default_factory=set)

class NetworkFunctionElement(NetworkElement):
    function_type: NetworkFunctionType
    appliance_instances: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    service_insertion_mode: str = "inline"
    auto_scaling_enabled: bool = False

__all__ = [
    'VPCSecurityMode', 'TransitGatewayMode', 'NetworkFunctionType',
    'SecurityAssessment', 'VPCElement', 'TransitGatewayElement',
    'CloudWANElement', 'SecurityElement', 'NetworkFunctionElement',
    'IPDetailsResponse'
]