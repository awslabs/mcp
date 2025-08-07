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

"""AWS resource data models and structures."""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class CoreNetwork(BaseModel):
    """Model for CloudWAN Core Network."""
    
    core_network_id: str = Field(..., description="Core network ID")
    global_network_id: str = Field(..., description="Global network ID")
    state: str = Field(..., description="Core network state")
    policy_version_id: Optional[str] = Field(None, description="Policy version ID")
    description: Optional[str] = Field(None, description="Core network description")
    created_at: Optional[str] = Field(None, description="Creation timestamp")


class CoreNetworkPolicy(BaseModel):
    """Model for CloudWAN Core Network Policy."""
    
    core_network_id: str = Field(..., description="Core network ID")
    policy_version_id: str = Field(..., description="Policy version ID")
    policy_document: Optional[Dict[str, Any]] = Field(None, description="Policy document")
    description: Optional[str] = Field(None, description="Policy description")
    created_at: Optional[str] = Field(None, description="Creation timestamp")
    alias: str = Field(default="LIVE", description="Policy alias")


class TransitGatewayRoute(BaseModel):
    """Model for Transit Gateway route information."""
    
    destination_cidr: str = Field(..., description="Destination CIDR")
    route_table_id: str = Field(..., description="Route table ID")
    state: str = Field(..., description="Route state")
    type: Optional[str] = Field(None, description="Route type")
    target_type: Optional[str] = Field(None, description="Target type")
    target_id: Optional[str] = Field(None, description="Target ID")


class TransitGatewayPeering(BaseModel):
    """Model for Transit Gateway peering attachment."""
    
    peer_id: str = Field(..., description="Peering attachment ID")
    region: str = Field(..., description="AWS region")
    state: str = Field(..., description="Peering state")
    status: Optional[str] = Field(None, description="Peering status")
    creation_time: Optional[str] = Field(None, description="Creation timestamp")
    accepter_tgw_info: Optional[Dict[str, Any]] = Field(None, description="Accepter TGW info")
    requester_tgw_info: Optional[Dict[str, Any]] = Field(None, description="Requester TGW info")


class VPCResource(BaseModel):
    """Model for VPC resource information."""
    
    vpc_id: str = Field(..., description="VPC ID")
    region: str = Field(..., description="AWS region")
    cidr_block: str = Field(..., description="Primary CIDR block")
    state: str = Field(..., description="VPC state")
    is_default: bool = Field(default=False, description="Whether this is default VPC")
    tags: Optional[List[Dict[str, str]]] = Field(None, description="VPC tags")


class GlobalNetwork(BaseModel):
    """Model for Global Network resource."""
    
    global_network_id: str = Field(..., description="Global network ID")
    global_network_arn: str = Field(..., description="Global network ARN")
    description: Optional[str] = Field(None, description="Global network description")
    state: str = Field(..., description="Global network state")
    created_at: Optional[str] = Field(None, description="Creation timestamp")
    tags: Optional[List[Dict[str, str]]] = Field(None, description="Global network tags")