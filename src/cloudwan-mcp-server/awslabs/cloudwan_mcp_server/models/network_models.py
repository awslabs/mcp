# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Network-related data models and structures."""

import ipaddress
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, validator


class NetworkPath(BaseModel):
    """Model for network path tracing results."""
    
    source_ip: str = Field(..., description="Source IP address")
    destination_ip: str = Field(..., description="Destination IP address") 
    region: str = Field(..., description="AWS region")
    total_hops: int = Field(..., description="Total number of hops")
    status: str = Field(..., description="Path status (reachable, unreachable)")
    path_trace: List[Dict[str, Any]] = Field(default_factory=list, description="Hop details")

    @validator("source_ip", "destination_ip")
    def validate_ip_address(cls, v):
        """Validate IP address format."""
        try:
            ipaddress.ip_address(v)
            return v
        except ValueError:
            raise ValueError(f"Invalid IP address: {v}")


class IPDetails(BaseModel):
    """Model for IP address analysis results."""
    
    ip_address: str = Field(..., description="IP address")
    region: str = Field(..., description="AWS region")
    ip_version: int = Field(..., description="IP version (4 or 6)")
    is_private: bool = Field(..., description="Whether IP is private")
    is_multicast: bool = Field(..., description="Whether IP is multicast")
    is_loopback: bool = Field(..., description="Whether IP is loopback")

    @validator("ip_address")
    def validate_ip_address(cls, v):
        """Validate IP address format."""
        try:
            ipaddress.ip_address(v)
            return v
        except ValueError:
            raise ValueError(f"Invalid IP address: {v}")


class CIDRValidation(BaseModel):
    """Model for CIDR validation results."""
    
    operation: str = Field(..., description="Validation operation")
    network: str = Field(..., description="Network CIDR")
    network_address: str = Field(..., description="Network address")
    broadcast_address: Optional[str] = Field(None, description="Broadcast address")
    num_addresses: int = Field(..., description="Number of addresses")
    is_private: bool = Field(..., description="Whether network is private")

    @validator("network")
    def validate_cidr(cls, v):
        """Validate CIDR format."""
        try:
            ipaddress.ip_network(v, strict=False)
            return v
        except ValueError:
            raise ValueError(f"Invalid CIDR: {v}")


class NetworkFunctionGroup(BaseModel):
    """Model for Network Function Group details."""
    
    name: str = Field(..., description="NFG name")
    description: Optional[str] = Field(None, description="NFG description")
    status: str = Field(..., description="NFG status")
    region: str = Field(..., description="AWS region")


class SegmentRouteAnalysis(BaseModel):
    """Model for segment routing analysis results."""
    
    core_network_id: str = Field(..., description="Core network ID")
    segment_name: str = Field(..., description="Segment name")
    region: str = Field(..., description="AWS region")
    segment_found: bool = Field(..., description="Whether segment was found")
    total_routes: int = Field(..., description="Total routes")
    optimized_routes: int = Field(..., description="Optimized routes")
    redundant_routes: int = Field(..., description="Redundant routes")
    recommendations: List[str] = Field(default_factory=list, description="Optimization recommendations")


class NetworkFirewall(BaseModel):
    """Model for AWS Network Firewall details."""
    
    firewall_name: str = Field(..., description="Network Firewall name")
    firewall_arn: str = Field(..., description="Network Firewall ARN")
    vpc_id: str = Field(..., description="VPC ID where firewall is deployed")
    status: str = Field(..., description="Firewall status")
    subnet_mappings: int = Field(..., description="Number of subnet mappings")
    policy_arn: str = Field(..., description="Firewall policy ARN")
    region: str = Field(..., description="AWS region")


class FirewallPolicy(BaseModel):
    """Model for AWS Network Firewall policy details."""
    
    policy_arn: str = Field(..., description="Policy ARN")
    policy_name: str = Field(..., description="Policy name")
    stateless_rule_groups: int = Field(..., description="Number of stateless rule groups")
    stateful_rule_groups: int = Field(..., description="Number of stateful rule groups")
    stateless_default_actions: List[str] = Field(default_factory=list, description="Default actions for stateless rules")
    logging_enabled: bool = Field(..., description="Whether logging is enabled")


class SuricataRule(BaseModel):
    """Model for parsed Suricata rule details."""
    
    action: str = Field(..., description="Rule action (alert, drop, pass, etc.)")
    protocol: str = Field(..., description="Protocol (TCP, UDP, ICMP, etc.)")
    src_ip: Optional[str] = Field(None, description="Source IP or CIDR")
    src_port: Optional[str] = Field(None, description="Source port or range")
    dst_ip: Optional[str] = Field(None, description="Destination IP or CIDR")
    dst_port: Optional[str] = Field(None, description="Destination port or range")
    raw_rule: str = Field(..., description="Original Suricata rule text")
    parsed: bool = Field(..., description="Whether rule was successfully parsed")
    parse_error: Optional[str] = Field(None, description="Parse error if any")


class FlowLog(BaseModel):
    """Model for Network Firewall flow log entry."""
    
    timestamp: str = Field(..., description="Log timestamp")
    firewall_name: str = Field(..., description="Firewall name")
    source_ip: str = Field(..., description="Source IP address")
    destination_ip: str = Field(..., description="Destination IP address")
    source_port: int = Field(..., description="Source port")
    destination_port: int = Field(..., description="Destination port")
    protocol: str = Field(..., description="Protocol")
    action: str = Field(..., description="Action taken (ALLOW, DENY)")
    
    @validator("source_ip", "destination_ip")
    def validate_ip_address(cls, v):
        """Validate IP address format."""
        try:
            ipaddress.ip_address(v)
            return v
        except ValueError:
            raise ValueError(f"Invalid IP address: {v}")


class FiveTupleFlow(BaseModel):
    """Model for 5-tuple flow analysis."""
    
    source_ip: str = Field(..., description="Source IP address")
    destination_ip: str = Field(..., description="Destination IP address")
    protocol: str = Field(..., description="Protocol (TCP, UDP, ICMP)")
    source_port: int = Field(..., ge=1, le=65535, description="Source port")
    destination_port: int = Field(..., ge=1, le=65535, description="Destination port")
    firewall_decision: str = Field(..., description="Firewall decision (ALLOW, DENY)")
    rule_matches: List[Dict[str, Any]] = Field(default_factory=list, description="Matching rules")
    
    @validator("source_ip", "destination_ip")
    def validate_ip_address(cls, v):
        """Validate IP address format."""
        try:
            ipaddress.ip_address(v)
            return v
        except ValueError:
            raise ValueError(f"Invalid IP address: {v}")


class PolicySimulation(BaseModel):
    """Model for policy change simulation results."""
    
    firewall_name: str = Field(..., description="Firewall name")
    change_description: str = Field(..., description="Description of policy changes")
    flows_analyzed: int = Field(..., description="Number of flows analyzed")
    newly_blocked: int = Field(..., description="Flows that would be newly blocked")
    newly_allowed: int = Field(..., description="Flows that would be newly allowed")
    no_change: int = Field(..., description="Flows with no impact")
    detailed_analysis: List[Dict[str, Any]] = Field(default_factory=list, description="Detailed flow analysis")
    recommendations: List[Dict[str, str]] = Field(default_factory=list, description="Policy recommendations")