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
EC2 EBS volumes management module.
"""

import logging
from typing import Any, Dict, List, Optional

from mcp.server.fastmcp import FastMCP

from awslabs.ec2_mcp_server.utils.aws import AWSClientManager, handle_aws_error, parse_tags, format_tags
from awslabs.ec2_mcp_server.utils.config import get_config
from awslabs.ec2_mcp_server.utils.security import validate_volume_id, validate_instance_id

logger = logging.getLogger(__name__)

# Initialize AWS client manager
config = get_config()
aws_client = AWSClientManager(
    region=config.get("aws_region", "us-east-1"),
    profile=config.get("aws_profile")
)


async def list_volumes(
    volume_ids: Optional[List[str]] = None,
    filters: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """
    List EBS volumes with optional filtering.

    Args:
        volume_ids: Optional list of volume IDs
        filters: Optional list of filters to apply

    Returns:
        Dict containing volume information
    """
    try:
        ec2_client = aws_client.get_client("ec2")
        
        # Prepare describe_volumes parameters
        params = {}
        if volume_ids:
            params["VolumeIds"] = volume_ids
        if filters:
            params["Filters"] = filters

        response = ec2_client.describe_volumes(**params)
        
        volumes = []
        for vol in response["Volumes"]:
            volumes.append({
                "volume_id": vol["VolumeId"],
                "volume_type": vol["VolumeType"],
                "size": vol["Size"],
                "state": vol["State"],
                "availability_zone": vol["AvailabilityZone"],
                "encrypted": vol["Encrypted"],
                "iops": vol.get("Iops"),
                "throughput": vol.get("Throughput"),
                "attachments": vol.get("Attachments", []),
                "tags": parse_tags(vol.get("Tags", [])),
                "create_time": vol.get("CreateTime").isoformat() if vol.get("CreateTime") else None,
            })
        
        return {
            "status": "success",
            "volumes": volumes,
            "count": len(volumes),
        }
    
    except Exception as e:
        logger.error(f"Failed to list volumes: {e}")
        return handle_aws_error(e)


async def create_volume(
    availability_zone: str,
    size: int,
    volume_type: str = "gp3",
    iops: Optional[int] = None,
    throughput: Optional[int] = None,
    encrypted: bool = False,
    tags: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """
    Create a new EBS volume.

    Args:
        availability_zone: Availability zone for the volume
        size: Size in GB
        volume_type: Volume type (gp3, gp2, io1, io2, st1, sc1)
        iops: IOPS for io1/io2 volumes
        throughput: Throughput for gp3 volumes
        encrypted: Whether to encrypt the volume
        tags: Optional tags to apply to the volume

    Returns:
        Dict containing creation results
    """
    try:
        ec2_client = aws_client.get_client("ec2")
        
        params = {
            "AvailabilityZone": availability_zone,
            "Size": size,
            "VolumeType": volume_type,
            "Encrypted": encrypted,
        }
        
        if iops:
            params["Iops"] = iops
        if throughput:
            params["Throughput"] = throughput
        
        if tags:
            params["TagSpecifications"] = [
                {
                    "ResourceType": "volume",
                    "Tags": format_tags(tags),
                }
            ]
        
        response = ec2_client.create_volume(**params)
        
        return {
            "status": "success",
            "message": f"Successfully created volume in {availability_zone}",
            "volume_id": response["VolumeId"],
            "availability_zone": response["AvailabilityZone"],
            "size": response["Size"],
            "volume_type": response["VolumeType"],
            "state": response["State"],
        }
    
    except Exception as e:
        logger.error(f"Failed to create volume: {e}")
        return handle_aws_error(e)


async def delete_volume(volume_id: str) -> Dict[str, Any]:
    """
    Delete an EBS volume.

    Args:
        volume_id: The volume ID to delete

    Returns:
        Dict containing deletion results
    """
    try:
        validate_volume_id(volume_id)
        
        ec2_client = aws_client.get_client("ec2")
        ec2_client.delete_volume(VolumeId=volume_id)
        
        return {
            "status": "success",
            "message": f"Successfully deleted volume {volume_id}",
            "volume_id": volume_id,
        }
    
    except Exception as e:
        logger.error(f"Failed to delete volume: {e}")
        return handle_aws_error(e)


async def attach_volume(
    volume_id: str,
    instance_id: str,
    device: str,
) -> Dict[str, Any]:
    """
    Attach an EBS volume to an instance.

    Args:
        volume_id: The volume ID to attach
        instance_id: The instance ID to attach to
        device: The device name (e.g., /dev/sdf)

    Returns:
        Dict containing attachment results
    """
    try:
        validate_volume_id(volume_id)
        validate_instance_id(instance_id)
        
        ec2_client = aws_client.get_client("ec2")
        response = ec2_client.attach_volume(
            VolumeId=volume_id,
            InstanceId=instance_id,
            Device=device,
        )
        
        return {
            "status": "success",
            "message": f"Successfully attached volume {volume_id} to instance {instance_id}",
            "volume_id": volume_id,
            "instance_id": instance_id,
            "device": device,
            "state": response["State"],
        }
    
    except Exception as e:
        logger.error(f"Failed to attach volume: {e}")
        return handle_aws_error(e)


async def detach_volume(
    volume_id: str,
    instance_id: Optional[str] = None,
    device: Optional[str] = None,
    force: bool = False,
) -> Dict[str, Any]:
    """
    Detach an EBS volume from an instance.

    Args:
        volume_id: The volume ID to detach
        instance_id: The instance ID to detach from (optional)
        device: The device name (optional)
        force: Whether to force detachment

    Returns:
        Dict containing detachment results
    """
    try:
        validate_volume_id(volume_id)
        
        ec2_client = aws_client.get_client("ec2")
        
        params = {
            "VolumeId": volume_id,
            "Force": force,
        }
        
        if instance_id:
            params["InstanceId"] = instance_id
        if device:
            params["Device"] = device
        
        response = ec2_client.detach_volume(**params)
        
        return {
            "status": "success",
            "message": f"Successfully detached volume {volume_id}",
            "volume_id": volume_id,
            "instance_id": response.get("InstanceId"),
            "device": response.get("Device"),
            "state": response["State"],
        }
    
    except Exception as e:
        logger.error(f"Failed to detach volume: {e}")
        return handle_aws_error(e)


def register_module(mcp: FastMCP) -> None:
    """
    Register the volumes module with the MCP server.

    Args:
        mcp: The FastMCP server instance
    """
    mcp.tool("list_volumes")(list_volumes)
    mcp.tool("create_volume")(create_volume)
    mcp.tool("delete_volume")(delete_volume)
    mcp.tool("attach_volume")(attach_volume)
    mcp.tool("detach_volume")(detach_volume)