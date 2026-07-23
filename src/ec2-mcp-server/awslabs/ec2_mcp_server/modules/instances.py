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
EC2 instances management module.
"""

import logging
from typing import Any, Dict, List, Optional

from mcp.server.fastmcp import FastMCP

from awslabs.ec2_mcp_server.utils.aws import AWSClientManager, handle_aws_error, parse_tags, format_tags
from awslabs.ec2_mcp_server.utils.config import get_config
from awslabs.ec2_mcp_server.utils.security import validate_instance_id, validate_ami_id

logger = logging.getLogger(__name__)

# Initialize AWS client manager
config = get_config()
aws_client = AWSClientManager(
    region=config.get("aws_region", "us-east-1"),
    profile=config.get("aws_profile")
)


async def list_instances(
    filters: Optional[List[Dict[str, Any]]] = None,
    instance_ids: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    List EC2 instances with optional filtering.

    Args:
        filters: Optional list of filters to apply
        instance_ids: Optional list of specific instance IDs to describe

    Returns:
        Dict containing instance information
    """
    try:
        ec2_client = aws_client.get_client("ec2")
        
        # Prepare describe_instances parameters
        params = {}
        if filters:
            params["Filters"] = filters
        if instance_ids:
            params["InstanceIds"] = instance_ids

        response = ec2_client.describe_instances(**params)
        
        instances = []
        for reservation in response["Reservations"]:
            for instance in reservation["Instances"]:
                instances.append({
                    "instance_id": instance["InstanceId"],
                    "instance_type": instance["InstanceType"],
                    "state": instance["State"]["Name"],
                    "ami_id": instance["ImageId"],
                    "key_name": instance.get("KeyName"),
                    "subnet_id": instance.get("SubnetId"),
                    "vpc_id": instance.get("VpcId"),
                    "private_ip": instance.get("PrivateIpAddress"),
                    "public_ip": instance.get("PublicIpAddress"),
                    "launch_time": instance.get("LaunchTime").isoformat() if instance.get("LaunchTime") else None,
                    "availability_zone": instance.get("Placement", {}).get("AvailabilityZone"),
                    "security_groups": [sg["GroupId"] for sg in instance.get("SecurityGroups", [])],
                    "tags": parse_tags(instance.get("Tags", [])),
                })
        
        return {
            "status": "success",
            "instances": instances,
            "count": len(instances),
        }
    
    except Exception as e:
        logger.error(f"Failed to list instances: {e}")
        return handle_aws_error(e)


async def get_instance_details(instance_id: str) -> Dict[str, Any]:
    """
    Get detailed information about a specific EC2 instance.

    Args:
        instance_id: The instance ID to get details for

    Returns:
        Dict containing detailed instance information
    """
    try:
        validate_instance_id(instance_id)
        
        ec2_client = aws_client.get_client("ec2")
        response = ec2_client.describe_instances(InstanceIds=[instance_id])
        
        if not response["Reservations"]:
            return {
                "status": "error",
                "message": f"Instance {instance_id} not found",
            }
        
        instance = response["Reservations"][0]["Instances"][0]
        
        return {
            "status": "success",
            "instance": {
                "instance_id": instance["InstanceId"],
                "instance_type": instance["InstanceType"],
                "state": instance["State"]["Name"],
                "ami_id": instance["ImageId"],
                "key_name": instance.get("KeyName"),
                "subnet_id": instance.get("SubnetId"),
                "vpc_id": instance.get("VpcId"),
                "private_ip": instance.get("PrivateIpAddress"),
                "public_ip": instance.get("PublicIpAddress"),
                "launch_time": instance.get("LaunchTime").isoformat() if instance.get("LaunchTime") else None,
                "availability_zone": instance.get("Placement", {}).get("AvailabilityZone"),
                "security_groups": [
                    {"group_id": sg["GroupId"], "group_name": sg["GroupName"]}
                    for sg in instance.get("SecurityGroups", [])
                ],
                "tags": parse_tags(instance.get("Tags", [])),
                "monitoring": instance.get("Monitoring", {}).get("State"),
                "block_device_mappings": instance.get("BlockDeviceMappings", []),
                "network_interfaces": instance.get("NetworkInterfaces", []),
                "architecture": instance.get("Architecture"),
                "platform": instance.get("Platform"),
                "hypervisor": instance.get("Hypervisor"),
                "virtualization_type": instance.get("VirtualizationType"),
            },
        }
    
    except Exception as e:
        logger.error(f"Failed to get instance details: {e}")
        return handle_aws_error(e)


async def launch_instance(
    ami_id: str,
    instance_type: str = "t2.micro",
    key_name: Optional[str] = None,
    security_group_ids: Optional[List[str]] = None,
    subnet_id: Optional[str] = None,
    vpc_id: Optional[str] = None,
    user_data: Optional[str] = None,
    tags: Optional[Dict[str, str]] = None,
    min_count: int = 1,
    max_count: int = 1,
    associate_public_ip: Optional[bool] = None,
    disable_api_termination: bool = False,
    monitoring_enabled: bool = False,
) -> Dict[str, Any]:
    """
    Launch a new EC2 instance with enhanced configuration options.
    If no subnet_id is provided, automatically selects a suitable subnet based on 
    the associate_public_ip parameter (public subnet if True, private if False, any if None).

    Args:
        ami_id: AMI ID to launch from
        instance_type: EC2 instance type (default: t2.micro)
        key_name: Key pair name for SSH access
        security_group_ids: List of security group IDs
        subnet_id: Subnet ID to launch in (if not provided, will auto-select)
        vpc_id: VPC ID to launch in (if not provided, uses default VPC)
        user_data: User data script to run on instance startup (base64 encoded automatically)
        tags: Tags to apply to the instance
        min_count: Minimum number of instances to launch
        max_count: Maximum number of instances to launch
        associate_public_ip: Whether to associate a public IP (also determines subnet type if subnet_id not provided)
        disable_api_termination: Prevent accidental termination via API
        monitoring_enabled: Enable detailed CloudWatch monitoring

    Returns:
        Dict containing launch results
    """
    try:
        validate_ami_id(ami_id)
        
        ec2_client = aws_client.get_client("ec2")
        
        # Auto-select subnet if not provided
        if not subnet_id:
            from awslabs.ec2_mcp_server.modules.vpc_management import find_suitable_subnet
            
            # Determine subnet type requirement based on associate_public_ip
            require_public = associate_public_ip
            
            subnet_result = await find_suitable_subnet(
                vpc_id=vpc_id,
                require_public=require_public
            )
            
            if subnet_result["status"] != "success":
                return {
                    "status": "error",
                    "message": f"Failed to find suitable subnet: {subnet_result.get('message', 'Unknown error')}",
                }
            
            subnet_id = subnet_result["subnet"]["subnet_id"]
            vpc_id = subnet_result["vpc_id"]
            
            logger.info(f"Auto-selected subnet {subnet_id} in VPC {vpc_id}")
        
        # Prepare launch parameters
        params = {
            "ImageId": ami_id,
            "MinCount": min_count,
            "MaxCount": max_count,
            "InstanceType": instance_type,
            "DisableApiTermination": disable_api_termination,
            "Monitoring": {"Enabled": monitoring_enabled},
        }
        
        if key_name:
            params["KeyName"] = key_name
        
        if security_group_ids:
            params["SecurityGroupIds"] = security_group_ids
        
        if subnet_id:
            params["SubnetId"] = subnet_id
            
            # Handle public IP assignment
            if associate_public_ip is not None:
                params["NetworkInterfaces"] = [{
                    "DeviceIndex": 0,
                    "SubnetId": subnet_id,
                    "AssociatePublicIpAddress": associate_public_ip,
                    "Groups": security_group_ids if security_group_ids else [],
                }]
                # Remove conflicting parameters when using NetworkInterfaces
                if "SecurityGroupIds" in params:
                    del params["SecurityGroupIds"]
                if "SubnetId" in params:
                    del params["SubnetId"]
        
        if user_data:
            # Base64 encode user data if it's not already encoded
            import base64
            try:
                # Try to decode to check if already base64 encoded
                base64.b64decode(user_data, validate=True)
                params["UserData"] = user_data
            except Exception:
                # Not base64 encoded, encode it
                params["UserData"] = base64.b64encode(user_data.encode('utf-8')).decode('utf-8')
        
        if tags:
            params["TagSpecifications"] = [
                {
                    "ResourceType": "instance",
                    "Tags": format_tags(tags),
                }
            ]
        
        response = ec2_client.run_instances(**params)
        
        instances = []
        for instance in response["Instances"]:
            instances.append({
                "instance_id": instance["InstanceId"],
                "instance_type": instance["InstanceType"],
                "state": instance["State"]["Name"],
                "ami_id": instance["ImageId"],
                "availability_zone": instance.get("Placement", {}).get("AvailabilityZone"),
                "launch_time": instance.get("LaunchTime").isoformat() if instance.get("LaunchTime") else None,
                "subnet_id": instance.get("SubnetId"),
                "vpc_id": instance.get("VpcId"),
                "private_ip": instance.get("PrivateIpAddress"),
                "public_ip": instance.get("PublicIpAddress"),
                "security_groups": [sg["GroupId"] for sg in instance.get("SecurityGroups", [])],
                "key_name": instance.get("KeyName"),
                "monitoring_enabled": monitoring_enabled,
                "api_termination_disabled": disable_api_termination,
            })
        
        return {
            "status": "success",
            "message": f"Successfully launched {len(instances)} instance(s)",
            "instances": instances,
            "launch_configuration": {
                "ami_id": ami_id,
                "instance_type": instance_type,
                "subnet_id": subnet_id,
                "associate_public_ip": associate_public_ip,
                "user_data_provided": bool(user_data),
                "monitoring_enabled": monitoring_enabled,
                "api_termination_disabled": disable_api_termination,
            },
        }
    
    except Exception as e:
        logger.error(f"Failed to launch instance: {e}")
        return handle_aws_error(e)


async def terminate_instance(instance_id: str) -> Dict[str, Any]:
    """
    Terminate an EC2 instance.

    Args:
        instance_id: The instance ID to terminate

    Returns:
        Dict containing termination results
    """
    try:
        validate_instance_id(instance_id)
        
        ec2_client = aws_client.get_client("ec2")
        response = ec2_client.terminate_instances(InstanceIds=[instance_id])
        
        terminating_instances = []
        for instance in response["TerminatingInstances"]:
            terminating_instances.append({
                "instance_id": instance["InstanceId"],
                "current_state": instance["CurrentState"]["Name"],
                "previous_state": instance["PreviousState"]["Name"],
            })
        
        return {
            "status": "success",
            "message": f"Successfully initiated termination of instance {instance_id}",
            "terminating_instances": terminating_instances,
        }
    
    except Exception as e:
        logger.error(f"Failed to terminate instance: {e}")
        return handle_aws_error(e)


async def start_instance(instance_id: str) -> Dict[str, Any]:
    """
    Start a stopped EC2 instance.

    Args:
        instance_id: The instance ID to start

    Returns:
        Dict containing start results
    """
    try:
        validate_instance_id(instance_id)
        
        ec2_client = aws_client.get_client("ec2")
        response = ec2_client.start_instances(InstanceIds=[instance_id])
        
        starting_instances = []
        for instance in response["StartingInstances"]:
            starting_instances.append({
                "instance_id": instance["InstanceId"],
                "current_state": instance["CurrentState"]["Name"],
                "previous_state": instance["PreviousState"]["Name"],
            })
        
        return {
            "status": "success",
            "message": f"Successfully started instance {instance_id}",
            "starting_instances": starting_instances,
        }
    
    except Exception as e:
        logger.error(f"Failed to start instance: {e}")
        return handle_aws_error(e)


async def stop_instance(instance_id: str, force: bool = False) -> Dict[str, Any]:
    """
    Stop a running EC2 instance.

    Args:
        instance_id: The instance ID to stop
        force: Whether to force stop the instance

    Returns:
        Dict containing stop results
    """
    try:
        validate_instance_id(instance_id)
        
        ec2_client = aws_client.get_client("ec2")
        response = ec2_client.stop_instances(InstanceIds=[instance_id], Force=force)
        
        stopping_instances = []
        for instance in response["StoppingInstances"]:
            stopping_instances.append({
                "instance_id": instance["InstanceId"],
                "current_state": instance["CurrentState"]["Name"],
                "previous_state": instance["PreviousState"]["Name"],
            })
        
        return {
            "status": "success",
            "message": f"Successfully stopped instance {instance_id}",
            "stopping_instances": stopping_instances,
        }
    
    except Exception as e:
        logger.error(f"Failed to stop instance: {e}")
        return handle_aws_error(e)


async def get_subnet_info(subnet_id: str) -> Dict[str, Any]:
    """
    Get information about a subnet to help determine if it's public or private.

    Args:
        subnet_id: The subnet ID to get information for

    Returns:
        Dict containing subnet information
    """
    try:
        ec2_client = aws_client.get_client("ec2")
        
        # Get subnet details
        subnet_response = ec2_client.describe_subnets(SubnetIds=[subnet_id])
        if not subnet_response["Subnets"]:
            return {
                "status": "error",
                "message": f"Subnet {subnet_id} not found",
            }
        
        subnet = subnet_response["Subnets"][0]
        
        # Get route table for this subnet to determine if it's public or private
        route_tables_response = ec2_client.describe_route_tables(
            Filters=[
                {"Name": "association.subnet-id", "Values": [subnet_id]}
            ]
        )
        
        # If no explicit association, check main route table for VPC
        if not route_tables_response["RouteTables"]:
            route_tables_response = ec2_client.describe_route_tables(
                Filters=[
                    {"Name": "vpc-id", "Values": [subnet["VpcId"]]},
                    {"Name": "association.main", "Values": ["true"]}
                ]
            )
        
        is_public = False
        if route_tables_response["RouteTables"]:
            route_table = route_tables_response["RouteTables"][0]
            # Check if there's a route to an internet gateway
            for route in route_table.get("Routes", []):
                if route.get("GatewayId", "").startswith("igw-"):
                    is_public = True
                    break
        
        return {
            "status": "success",
            "subnet": {
                "subnet_id": subnet["SubnetId"],
                "vpc_id": subnet["VpcId"],
                "availability_zone": subnet["AvailabilityZone"],
                "cidr_block": subnet["CidrBlock"],
                "available_ip_count": subnet["AvailableIpAddressCount"],
                "is_public": is_public,
                "auto_assign_public_ip": subnet.get("MapPublicIpOnLaunch", False),
                "state": subnet["State"],
                "tags": parse_tags(subnet.get("Tags", [])),
            },
        }
    
    except Exception as e:
        logger.error(f"Failed to get subnet info: {e}")
        return handle_aws_error(e)


async def list_subnets(vpc_id: Optional[str] = None) -> Dict[str, Any]:
    """
    List available subnets, optionally filtered by VPC.

    Args:
        vpc_id: Optional VPC ID to filter subnets

    Returns:
        Dict containing subnet information
    """
    try:
        ec2_client = aws_client.get_client("ec2")
        
        params = {}
        if vpc_id:
            params["Filters"] = [{"Name": "vpc-id", "Values": [vpc_id]}]
        
        response = ec2_client.describe_subnets(**params)
        
        subnets = []
        for subnet in response["Subnets"]:
            # Get route table info for each subnet
            subnet_info = await get_subnet_info(subnet["SubnetId"])
            if subnet_info["status"] == "success":
                subnets.append(subnet_info["subnet"])
        
        return {
            "status": "success",
            "subnets": subnets,
            "count": len(subnets),
        }
    
    except Exception as e:
        logger.error(f"Failed to list subnets: {e}")
        return handle_aws_error(e)


async def reboot_instance(instance_id: str) -> Dict[str, Any]:
    """
    Reboot an EC2 instance.

    Args:
        instance_id: The instance ID to reboot

    Returns:
        Dict containing reboot results
    """
    try:
        validate_instance_id(instance_id)
        
        ec2_client = aws_client.get_client("ec2")
        ec2_client.reboot_instances(InstanceIds=[instance_id])
        
        return {
            "status": "success",
            "message": f"Successfully initiated reboot of instance {instance_id}",
            "instance_id": instance_id,
        }
    
    except Exception as e:
        logger.error(f"Failed to reboot instance: {e}")
        return handle_aws_error(e)


def register_module(mcp: FastMCP) -> None:
    """
    Register the instances module with the MCP server.

    Args:
        mcp: The FastMCP server instance
    """
    mcp.tool("list_instances")(list_instances)
    mcp.tool("get_instance_details")(get_instance_details)
    mcp.tool("launch_instance")(launch_instance)
    mcp.tool("terminate_instance")(terminate_instance)
    mcp.tool("start_instance")(start_instance)
    mcp.tool("stop_instance")(stop_instance)
    mcp.tool("reboot_instance")(reboot_instance)
    mcp.tool("get_subnet_info")(get_subnet_info)