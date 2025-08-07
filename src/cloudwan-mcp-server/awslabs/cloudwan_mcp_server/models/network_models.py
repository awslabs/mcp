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