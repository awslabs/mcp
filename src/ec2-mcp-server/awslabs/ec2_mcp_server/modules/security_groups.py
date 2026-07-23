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
EC2 security groups management module.
"""

import logging
from typing import Any, Dict, List, Optional

from mcp.server.fastmcp import FastMCP

from awslabs.ec2_mcp_server.utils.aws import AWSClientManager, handle_aws_error, parse_tags, format_tags
from awslabs.ec2_mcp_server.utils.config import get_config
from awslabs.ec2_mcp_server.utils.security import validate_security_group_id, validate_vpc_id

logger = logging.getLogger(__name__)

# Initialize AWS client manager
config = get_config()
aws_client = AWSClientManager(
    region=config.get("aws_region", "us-east-1"),
    profile=config.get("aws_profile")
)


async def list_security_groups(
    group_ids: Optional[List[str]] = None,
    group_names: Optional[List[str]] = None,
    filters: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """
    List EC2 security groups with optional filtering.

    Args:
        group_ids: Optional list of security group IDs
        group_names: Optional list of security group names
        filters: Optional list of filters to apply

    Returns:
        Dict containing security group information
    """
    try:
        ec2_client = aws_client.get_client("ec2")
        
        # Prepare describe_security_groups parameters
        params = {}
        if group_ids:
            params["GroupIds"] = group_ids
        if group_names:
            params["GroupNames"] = group_names
        if filters:
            params["Filters"] = filters

        response = ec2_client.describe_security_groups(**params)
        
        security_groups = []
        for sg in response["SecurityGroups"]:
            security_groups.append({
                "group_id": sg["GroupId"],
                "group_name": sg["GroupName"],
                "description": sg["Description"],
                "vpc_id": sg["VpcId"],
                "owner_id": sg["OwnerId"],
                "inbound_rules": [
                    {
                        "ip_protocol": rule["IpProtocol"],
                        "from_port": rule.get("FromPort"),
                        "to_port": rule.get("ToPort"),
                        "ip_ranges": rule.get("IpRanges", []),
                        "ipv6_ranges": rule.get("Ipv6Ranges", []),
                        "user_id_group_pairs": rule.get("UserIdGroupPairs", []),
                    }
                    for rule in sg["IpPermissions"]
                ],
                "outbound_rules": [
                    {
                        "ip_protocol": rule["IpProtocol"],
                        "from_port": rule.get("FromPort"),
                        "to_port": rule.get("ToPort"),
                        "ip_ranges": rule.get("IpRanges", []),
                        "ipv6_ranges": rule.get("Ipv6Ranges", []),
                        "user_id_group_pairs": rule.get("UserIdGroupPairs", []),
                    }
                    for rule in sg["IpPermissionsEgress"]
                ],
                "tags": parse_tags(sg.get("Tags", [])),
            })
        
        return {
            "status": "success",
            "security_groups": security_groups,
            "count": len(security_groups),
        }
    
    except Exception as e:
        logger.error(f"Failed to list security groups: {e}")
        return handle_aws_error(e)


async def get_security_group_details(group_id: str) -> Dict[str, Any]:
    """
    Get detailed information about a specific security group.

    Args:
        group_id: The security group ID to get details for

    Returns:
        Dict containing detailed security group information
    """
    try:
        validate_security_group_id(group_id)
        
        ec2_client = aws_client.get_client("ec2")
        response = ec2_client.describe_security_groups(GroupIds=[group_id])
        
        if not response["SecurityGroups"]:
            return {
                "status": "error",
                "message": f"Security group {group_id} not found",
            }
        
        sg = response["SecurityGroups"][0]
        
        return {
            "status": "success",
            "security_group": {
                "group_id": sg["GroupId"],
                "group_name": sg["GroupName"],
                "description": sg["Description"],
                "vpc_id": sg["VpcId"],
                "owner_id": sg["OwnerId"],
                "inbound_rules": [
                    {
                        "ip_protocol": rule["IpProtocol"],
                        "from_port": rule.get("FromPort"),
                        "to_port": rule.get("ToPort"),
                        "ip_ranges": rule.get("IpRanges", []),
                        "ipv6_ranges": rule.get("Ipv6Ranges", []),
                        "user_id_group_pairs": rule.get("UserIdGroupPairs", []),
                    }
                    for rule in sg["IpPermissions"]
                ],
                "outbound_rules": [
                    {
                        "ip_protocol": rule["IpProtocol"],
                        "from_port": rule.get("FromPort"),
                        "to_port": rule.get("ToPort"),
                        "ip_ranges": rule.get("IpRanges", []),
                        "ipv6_ranges": rule.get("Ipv6Ranges", []),
                        "user_id_group_pairs": rule.get("UserIdGroupPairs", []),
                    }
                    for rule in sg["IpPermissionsEgress"]
                ],
                "tags": parse_tags(sg.get("Tags", [])),
            },
        }
    
    except Exception as e:
        logger.error(f"Failed to get security group details: {e}")
        return handle_aws_error(e)


async def create_security_group(
    group_name: str,
    description: str,
    vpc_id: str,
    tags: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """
    Create a new security group.

    Args:
        group_name: Name for the security group
        description: Description for the security group
        vpc_id: VPC ID where the security group should be created
        tags: Optional tags to apply to the security group

    Returns:
        Dict containing creation results
    """
    try:
        validate_vpc_id(vpc_id)
        
        ec2_client = aws_client.get_client("ec2")
        
        response = ec2_client.create_security_group(
            GroupName=group_name,
            Description=description,
            VpcId=vpc_id,
        )
        
        group_id = response["GroupId"]
        
        # Apply tags if provided
        if tags:
            ec2_client.create_tags(
                Resources=[group_id],
                Tags=format_tags(tags),
            )
        
        return {
            "status": "success",
            "message": f"Successfully created security group {group_name}",
            "group_id": group_id,
            "group_name": group_name,
            "vpc_id": vpc_id,
        }
    
    except Exception as e:
        logger.error(f"Failed to create security group: {e}")
        return handle_aws_error(e)


async def delete_security_group(group_id: str) -> Dict[str, Any]:
    """
    Delete a security group.

    Args:
        group_id: The security group ID to delete

    Returns:
        Dict containing deletion results
    """
    try:
        validate_security_group_id(group_id)
        
        ec2_client = aws_client.get_client("ec2")
        ec2_client.delete_security_group(GroupId=group_id)
        
        return {
            "status": "success",
            "message": f"Successfully deleted security group {group_id}",
            "group_id": group_id,
        }
    
    except Exception as e:
        logger.error(f"Failed to delete security group: {e}")
        return handle_aws_error(e)


async def modify_security_group_rules(
    group_id: str,
    action: str,
    rule_type: str,
    ip_protocol: str,
    from_port: Optional[int] = None,
    to_port: Optional[int] = None,
    cidr_blocks: Optional[List[str]] = None,
    source_security_group_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Modify security group rules (add or remove).

    Args:
        group_id: The security group ID to modify
        action: Either "add" or "remove"
        rule_type: Either "inbound" or "outbound"
        ip_protocol: IP protocol (tcp, udp, icmp, or -1 for all)
        from_port: Starting port number
        to_port: Ending port number
        cidr_blocks: List of CIDR blocks
        source_security_group_id: Source security group ID

    Returns:
        Dict containing modification results
    """
    try:
        validate_security_group_id(group_id)
        
        if action not in ["add", "remove"]:
            return {
                "status": "error",
                "message": "Action must be either 'add' or 'remove'",
            }
        
        if rule_type not in ["inbound", "outbound"]:
            return {
                "status": "error",
                "message": "Rule type must be either 'inbound' or 'outbound'",
            }
        
        ec2_client = aws_client.get_client("ec2")
        
        # Prepare rule parameters
        ip_permission = {
            "IpProtocol": ip_protocol,
        }
        
        if from_port is not None:
            ip_permission["FromPort"] = from_port
        if to_port is not None:
            ip_permission["ToPort"] = to_port
        
        if cidr_blocks:
            ip_permission["IpRanges"] = [{"CidrIp": cidr} for cidr in cidr_blocks]
        
        if source_security_group_id:
            ip_permission["UserIdGroupPairs"] = [{"GroupId": source_security_group_id}]
        
        # Apply the rule modification
        if action == "add":
            if rule_type == "inbound":
                ec2_client.authorize_security_group_ingress(
                    GroupId=group_id,
                    IpPermissions=[ip_permission],
                )
            else:  # outbound
                ec2_client.authorize_security_group_egress(
                    GroupId=group_id,
                    IpPermissions=[ip_permission],
                )
        else:  # remove
            if rule_type == "inbound":
                ec2_client.revoke_security_group_ingress(
                    GroupId=group_id,
                    IpPermissions=[ip_permission],
                )
            else:  # outbound
                ec2_client.revoke_security_group_egress(
                    GroupId=group_id,
                    IpPermissions=[ip_permission],
                )
        
        action_past_tense = "added" if action == "add" else "removed"
        return {
            "status": "success",
            "message": f"Successfully {action_past_tense} {rule_type} rule for security group {group_id}",
            "group_id": group_id,
            "action": action,
            "rule_type": rule_type,
            "rule": ip_permission,
        }
    
    except Exception as e:
        logger.error(f"Failed to modify security group rules: {e}")
        return handle_aws_error(e)


def register_module(mcp: FastMCP) -> None:
    """
    Register the security groups module with the MCP server.

    Args:
        mcp: The FastMCP server instance
    """
    mcp.tool("list_security_groups")(list_security_groups)
    mcp.tool("get_security_group_details")(get_security_group_details)
    mcp.tool("create_security_group")(create_security_group)
    mcp.tool("delete_security_group")(delete_security_group)
    mcp.tool("modify_security_group_rules")(modify_security_group_rules)