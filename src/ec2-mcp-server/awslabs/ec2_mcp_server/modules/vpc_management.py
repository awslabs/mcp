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

"""
EC2 VPC management module.
"""

import logging
from typing import Any, Dict, List, Optional

from mcp.server.fastmcp import FastMCP

from awslabs.ec2_mcp_server.utils.aws import AWSClientManager, handle_aws_error, parse_tags, format_tags
from awslabs.ec2_mcp_server.utils.config import get_config
from awslabs.ec2_mcp_server.utils.security import validate_vpc_id, validate_subnet_id

logger = logging.getLogger(__name__)

# Initialize AWS client manager
config = get_config()
aws_client = AWSClientManager(
    region=config.get("aws_region", "us-east-1"),
    profile=config.get("aws_profile")
)


async def list_vpcs(
    vpc_ids: Optional[List[str]] = None,
    filters: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """
    List VPCs with optional filtering.

    Args:
        vpc_ids: Optional list of VPC IDs
        filters: Optional list of filters to apply

    Returns:
        Dict containing VPC information
    """
    try:
        ec2_client = aws_client.get_client("ec2")
        
        # Prepare describe_vpcs parameters
        params = {}
        if vpc_ids:
            params["VpcIds"] = vpc_ids
        if filters:
            params["Filters"] = filters

        response = ec2_client.describe_vpcs(**params)
        
        vpcs = []
        for vpc in response["Vpcs"]:
            vpcs.append({
                "vpc_id": vpc["VpcId"],
                "cidr_block": vpc["CidrBlock"],
                "state": vpc["State"],
                "is_default": vpc["IsDefault"],
                "instance_tenancy": vpc["InstanceTenancy"],
                "dhcp_options_id": vpc["DhcpOptionsId"],
                "tags": parse_tags(vpc.get("Tags", [])),
            })
        
        return {
            "status": "success",
            "vpcs": vpcs,
            "count": len(vpcs),
        }
    
    except Exception as e:
        logger.error(f"Failed to list VPCs: {e}")
        return handle_aws_error(e)


async def get_default_vpc() -> Dict[str, Any]:
    """
    Get the default VPC for the current region.

    Returns:
        Dict containing default VPC information
    """
    try:
        ec2_client = aws_client.get_client("ec2")
        
        response = ec2_client.describe_vpcs(
            Filters=[
                {
                    "Name": "is-default",
                    "Values": ["true"]
                }
            ]
        )
        
        if not response["Vpcs"]:
            return {
                "status": "error",
                "message": "No default VPC found in this region",
            }
        
        vpc = response["Vpcs"][0]
        return {
            "status": "success",
            "vpc": {
                "vpc_id": vpc["VpcId"],
                "cidr_block": vpc["CidrBlock"],
                "state": vpc["State"],
                "is_default": vpc["IsDefault"],
                "instance_tenancy": vpc["InstanceTenancy"],
                "dhcp_options_id": vpc["DhcpOptionsId"],
                "tags": parse_tags(vpc.get("Tags", [])),
            }
        }
    
    except Exception as e:
        logger.error(f"Failed to get default VPC: {e}")
        return handle_aws_error(e)


async def find_suitable_subnet(
    vpc_id: Optional[str] = None,
    require_public: Optional[bool] = None,
    availability_zone: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Find a suitable existing subnet based on requirements.

    Args:
        vpc_id: VPC ID to search in (if None, uses default VPC)
        require_public: True for public subnet, False for private, None for any
        availability_zone: Specific AZ requirement

    Returns:
        Dict containing suitable subnet information
    """
    try:
        # If no VPC specified, get default VPC
        target_vpc_id = vpc_id
        if not target_vpc_id:
            default_vpc_result = await get_default_vpc()
            if default_vpc_result["status"] != "success":
                return default_vpc_result
            target_vpc_id = default_vpc_result["vpc"]["vpc_id"]
        
        ec2_client = aws_client.get_client("ec2")
        
        # Get subnets in the VPC
        filters = [
            {
                "Name": "vpc-id",
                "Values": [target_vpc_id]
            },
            {
                "Name": "state",
                "Values": ["available"]
            }
        ]
        
        if availability_zone:
            filters.append({
                "Name": "availability-zone",
                "Values": [availability_zone]
            })
        
        response = ec2_client.describe_subnets(Filters=filters)
        
        if not response["Subnets"]:
            return {
                "status": "error",
                "message": f"No available subnets found in VPC {target_vpc_id}",
            }
        
        suitable_subnets = []
        
        for subnet in response["Subnets"]:
            # Check if subnet matches public/private requirement
            if require_public is not None:
                # Check route tables to determine if subnet is public
                route_tables_response = ec2_client.describe_route_tables(
                    Filters=[
                        {
                            "Name": "association.subnet-id",
                            "Values": [subnet["SubnetId"]]
                        }
                    ]
                )
                
                is_public = False
                for route_table in route_tables_response["RouteTables"]:
                    for route in route_table["Routes"]:
                        if (route.get("DestinationCidrBlock") == "0.0.0.0/0" and 
                            route.get("GatewayId", "").startswith("igw-")):
                            is_public = True
                            break
                    if is_public:
                        break
                
                # Also check if subnet auto-assigns public IPs
                if subnet["MapPublicIpOnLaunch"]:
                    is_public = True
                
                if require_public and not is_public:
                    continue
                if not require_public and is_public:
                    continue
            
            suitable_subnets.append({
                "subnet_id": subnet["SubnetId"],
                "vpc_id": subnet["VpcId"],
                "cidr_block": subnet["CidrBlock"],
                "availability_zone": subnet["AvailabilityZone"],
                "state": subnet["State"],
                "available_ip_address_count": subnet["AvailableIpAddressCount"],
                "map_public_ip_on_launch": subnet["MapPublicIpOnLaunch"],
                "default_for_az": subnet["DefaultForAz"],
                "tags": parse_tags(subnet.get("Tags", [])),
            })
        
        if not suitable_subnets:
            public_private = "public" if require_public else "private" if require_public is False else "any"
            return {
                "status": "error",
                "message": f"No suitable {public_private} subnets found in VPC {target_vpc_id}",
            }
        
        # Sort by available IP count (descending) and return the best option
        suitable_subnets.sort(key=lambda s: s["available_ip_address_count"], reverse=True)
        
        return {
            "status": "success",
            "subnet": suitable_subnets[0],
            "all_suitable_subnets": suitable_subnets,
            "vpc_id": target_vpc_id,
        }
    
    except Exception as e:
        logger.error(f"Failed to find suitable subnet: {e}")
        return handle_aws_error(e)


async def delete_vpc(vpc_id: str) -> Dict[str, Any]:
    """
    Delete a VPC.

    Args:
        vpc_id: The VPC ID to delete

    Returns:
        Dict containing deletion results
    """
    try:
        validate_vpc_id(vpc_id)
        
        ec2_client = aws_client.get_client("ec2")
        ec2_client.delete_vpc(VpcId=vpc_id)
        
        return {
            "status": "success",
            "message": f"Successfully deleted VPC {vpc_id}",
            "vpc_id": vpc_id,
        }
    
    except Exception as e:
        logger.error(f"Failed to delete VPC: {e}")
        return handle_aws_error(e)


async def list_subnets(
    subnet_ids: Optional[List[str]] = None,
    filters: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """
    List subnets with optional filtering.

    Args:
        subnet_ids: Optional list of subnet IDs
        filters: Optional list of filters to apply

    Returns:
        Dict containing subnet information
    """
    try:
        ec2_client = aws_client.get_client("ec2")
        
        # Prepare describe_subnets parameters
        params = {}
        if subnet_ids:
            params["SubnetIds"] = subnet_ids
        if filters:
            params["Filters"] = filters

        response = ec2_client.describe_subnets(**params)
        
        subnets = []
        for subnet in response["Subnets"]:
            subnets.append({
                "subnet_id": subnet["SubnetId"],
                "vpc_id": subnet["VpcId"],
                "cidr_block": subnet["CidrBlock"],
                "availability_zone": subnet["AvailabilityZone"],
                "state": subnet["State"],
                "available_ip_address_count": subnet["AvailableIpAddressCount"],
                "map_public_ip_on_launch": subnet["MapPublicIpOnLaunch"],
                "default_for_az": subnet["DefaultForAz"],
                "tags": parse_tags(subnet.get("Tags", [])),
            })
        
        return {
            "status": "success",
            "subnets": subnets,
            "count": len(subnets),
        }
    
    except Exception as e:
        logger.error(f"Failed to list subnets: {e}")
        return handle_aws_error(e)


def register_module(mcp: FastMCP) -> None:
    """
    Register the VPC management module with the MCP server.

    Args:
        mcp: The FastMCP server instance
    """
    mcp.tool("list_vpcs")(list_vpcs)
    mcp.tool("get_default_vpc")(get_default_vpc)
    mcp.tool("find_suitable_subnet")(find_suitable_subnet)
    mcp.tool("delete_vpc")(delete_vpc)
    mcp.tool("list_subnets")(list_subnets)