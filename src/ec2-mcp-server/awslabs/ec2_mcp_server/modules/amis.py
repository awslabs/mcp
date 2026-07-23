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
EC2 AMI (Amazon Machine Image) management module.
"""

import logging
from typing import Any, Dict, List, Optional

from mcp.server.fastmcp import FastMCP

from awslabs.ec2_mcp_server.utils.aws import AWSClientManager, handle_aws_error, parse_tags, format_tags
from awslabs.ec2_mcp_server.utils.config import get_config
from awslabs.ec2_mcp_server.utils.security import validate_ami_id, validate_instance_id

logger = logging.getLogger(__name__)

# Initialize AWS client manager
config = get_config()
aws_client = AWSClientManager(
    region=config.get("aws_region", "us-east-1"),
    profile=config.get("aws_profile")
)


async def list_amis(
    ami_ids: Optional[List[str]] = None,
    owners: Optional[List[str]] = None,
    filters: Optional[List[Dict[str, Any]]] = None,
    include_public: bool = False,
    max_results: int =10,
) -> Dict[str, Any]:
    """
    List AMIs with optional filtering. By default, only shows your own AMIs and popular public AMIs.

    Args:
        ami_ids: Optional list of AMI IDs
        owners: Optional list of owner IDs (defaults to 'self' and 'amazon')
        filters: Optional list of filters to apply
        include_public: Whether to include all public AMIs (warning: can be very slow)
        max_results: Maximum number of results to return (default: 10)

    Returns:
        Dict containing AMI information
    """
    try:
        ec2_client = aws_client.get_client("ec2")
        
        # Prepare describe_images parameters
        params = {}
        
        # Set default owners to prevent listing all public AMIs
        if ami_ids:
            params["ImageIds"] = ami_ids
        elif owners:
            params["Owners"] = owners
        elif include_public:
            # If user explicitly wants public AMIs, include amazon and self
            params["Owners"] = ["amazon", "self"]
        else:
            # By default, only show user's own AMIs
            params["Owners"] = ["self"]
        
        # Add filters
        if filters:
            params["Filters"] = filters
        else:
            # Default filters for better results
            default_filters = [
                {"Name": "state", "Values": ["available"]},
                {"Name": "architecture", "Values": ["x86_64", "arm64"]}
            ]
            params["Filters"] = default_filters

        response = ec2_client.describe_images(**params)
        
        # Sort AMIs by creation date (newest first)
        sorted_amis = sorted(
            response["Images"],
            key=lambda x: x.get("CreationDate", ""),
            reverse=True
        )
        
        # Limit results
        limited_amis = sorted_amis[:max_results]
        
        amis = []
        for ami in limited_amis:
            amis.append({
                "ami_id": ami["ImageId"],
                "name": ami["Name"],
                "description": ami.get("Description"),
                "owner_id": ami["OwnerId"],
                "state": ami["State"],
                "architecture": ami["Architecture"],
                "platform": ami.get("Platform"),
                "root_device_type": ami["RootDeviceType"],
                "virtualization_type": ami["VirtualizationType"],
                "creation_date": ami.get("CreationDate"),
                "public": ami["Public"],
                "tags": parse_tags(ami.get("Tags", [])),
            })
        
        return {
            "status": "success",
            "amis": amis,
            "count": len(amis),
            "total_available": len(response["Images"]),
            "showing_latest": max_results,
            "filters_applied": {
                "owners": params.get("Owners", []),
                "include_public": include_public,
                "max_results": max_results,
            },
        }
    
    except Exception as e:
        logger.error(f"Failed to list AMIs: {e}")
        return handle_aws_error(e)


async def get_popular_amis() -> Dict[str, Any]:
    """
    Get popular public AMIs (Amazon Linux, Ubuntu, Windows, etc.) that are commonly used.

    Returns:
        Dict containing popular AMI information
    """
    try:
        ec2_client = aws_client.get_client("ec2")
        
        popular_amis = []
        logger.info("Fetching popular AMIs...")
        
        # Amazon Linux 2023
        try:
            al2023_response = ec2_client.describe_images(
                Owners=["amazon"],
                Filters=[
                    {"Name": "name", "Values": ["al2023-ami-*-x86_64"]},
                    {"Name": "state", "Values": ["available"]},
                    {"Name": "architecture", "Values": ["x86_64"]},
                ]
            )
            if al2023_response["Images"]:
                ami = sorted(al2023_response["Images"], key=lambda x: x["CreationDate"], reverse=True)[0]
                popular_amis.append({
                    "category": "Amazon Linux",
                    "ami_id": ami["ImageId"],
                    "name": ami["Name"],
                    "description": "Amazon Linux 2023 (Latest)",
                    "architecture": ami["Architecture"],
                    "creation_date": ami["CreationDate"],
                })
        except Exception as e:
            logger.warning(f"Failed to fetch Amazon Linux 2023 AMIs: {e}")
            pass
        
        # Ubuntu 22.04 LTS
        try:
            ubuntu_response = ec2_client.describe_images(
                Owners=["099720109477"],  # Canonical
                Filters=[
                    {"Name": "name", "Values": ["ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-*"]},
                    {"Name": "state", "Values": ["available"]},
                ]
            )
            if ubuntu_response["Images"]:
                ami = sorted(ubuntu_response["Images"], key=lambda x: x["CreationDate"], reverse=True)[0]
                popular_amis.append({
                    "category": "Ubuntu",
                    "ami_id": ami["ImageId"],
                    "name": ami["Name"],
                    "description": "Ubuntu 22.04 LTS (Latest)",
                    "architecture": ami["Architecture"],
                    "creation_date": ami["CreationDate"],
                })
        except Exception as e:
            logger.warning(f"Failed to fetch Ubuntu AMIs: {e}")
            pass
        
        # Windows Server 2022
        try:
            windows_response = ec2_client.describe_images(
                Owners=["amazon"],
                Filters=[
                    {"Name": "name", "Values": ["Windows_Server-2022-English-Full-Base-*"]},
                    {"Name": "state", "Values": ["available"]},
                ]
            )
            if windows_response["Images"]:
                ami = sorted(windows_response["Images"], key=lambda x: x["CreationDate"], reverse=True)[0]
                popular_amis.append({
                    "category": "Windows Server",
                    "ami_id": ami["ImageId"],
                    "name": ami["Name"],
                    "description": "Windows Server 2022 (Latest)",
                    "architecture": ami["Architecture"],
                    "creation_date": ami["CreationDate"],
                })
        except Exception as e:
            logger.warning(f"Failed to fetch Windows Server AMIs: {e}")
            pass
        
        # Amazon Linux 2 (Legacy)
        try:
            al2_response = ec2_client.describe_images(
                Owners=["amazon"],
                Filters=[
                    {"Name": "name", "Values": ["amzn2-ami-hvm-*-x86_64-gp2"]},
                    {"Name": "state", "Values": ["available"]},
                    {"Name": "architecture", "Values": ["x86_64"]},
                ]
            )
            if al2_response["Images"]:
                ami = sorted(al2_response["Images"], key=lambda x: x["CreationDate"], reverse=True)[0]
                popular_amis.append({
                    "category": "Amazon Linux",
                    "ami_id": ami["ImageId"],
                    "name": ami["Name"],
                    "description": "Amazon Linux 2 (Latest)",
                    "architecture": ami["Architecture"],
                    "creation_date": ami["CreationDate"],
                })
        except Exception as e:
            logger.warning(f"Failed to fetch Amazon Linux 2 AMIs: {e}")
            pass
        
        # Red Hat Enterprise Linux 8
        try:
            rhel_response = ec2_client.describe_images(
                Owners=["309956199498"],  # Red Hat
                Filters=[
                    {"Name": "name", "Values": ["RHEL-8.*_HVM-*-x86_64-*"]},
                    {"Name": "state", "Values": ["available"]},
                ]
            )
            if rhel_response["Images"]:
                ami = sorted(rhel_response["Images"], key=lambda x: x["CreationDate"], reverse=True)[0]
                popular_amis.append({
                    "category": "Red Hat Enterprise Linux",
                    "ami_id": ami["ImageId"],
                    "name": ami["Name"],
                    "description": "Red Hat Enterprise Linux 8 (Latest)",
                    "architecture": ami["Architecture"],
                    "creation_date": ami["CreationDate"],
                })
        except Exception as e:
            logger.warning(f"Failed to fetch RHEL AMIs: {e}")
            pass
        
        logger.info(f"Found {len(popular_amis)} popular AMIs")
        
        return {
            "status": "success",
            "popular_amis": popular_amis,
            "count": len(popular_amis),
            "message": "Popular AMIs that are commonly used for launching instances",
        }
    
    except Exception as e:
        logger.error(f"Failed to get popular AMIs: {e}")
        return handle_aws_error(e)


async def create_image(
    instance_id: str,
    name: str,
    description: Optional[str] = None,
    no_reboot: bool = False,
    tags: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """
    Create an AMI from an EC2 instance.

    Args:
        instance_id: The instance ID to create image from
        name: Name for the AMI
        description: Optional description for the AMI
        no_reboot: Whether to avoid rebooting the instance
        tags: Optional tags to apply to the AMI

    Returns:
        Dict containing creation results
    """
    try:
        validate_instance_id(instance_id)
        
        ec2_client = aws_client.get_client("ec2")
        
        params = {
            "InstanceId": instance_id,
            "Name": name,
            "NoReboot": no_reboot,
        }
        
        if description:
            params["Description"] = description
        
        if tags:
            params["TagSpecifications"] = [
                {
                    "ResourceType": "image",
                    "Tags": format_tags(tags),
                }
            ]
        
        response = ec2_client.create_image(**params)
        
        return {
            "status": "success",
            "message": f"Successfully created AMI from instance {instance_id}",
            "ami_id": response["ImageId"],
            "name": name,
            "instance_id": instance_id,
        }
    
    except Exception as e:
        logger.error(f"Failed to create AMI: {e}")
        return handle_aws_error(e)


async def deregister_image(ami_id: str) -> Dict[str, Any]:
    """
    Deregister an AMI.

    Args:
        ami_id: The AMI ID to deregister

    Returns:
        Dict containing deregistration results
    """
    try:
        validate_ami_id(ami_id)
        
        ec2_client = aws_client.get_client("ec2")
        ec2_client.deregister_image(ImageId=ami_id)
        
        return {
            "status": "success",
            "message": f"Successfully deregistered AMI {ami_id}",
            "ami_id": ami_id,
        }
    
    except Exception as e:
        logger.error(f"Failed to deregister AMI: {e}")
        return handle_aws_error(e)


def register_module(mcp: FastMCP) -> None:
    """
    Register the AMIs module with the MCP server.

    Args:
        mcp: The FastMCP server instance
    """
    mcp.tool("list_amis")(list_amis)
    mcp.tool("get_popular_amis")(get_popular_amis)
    mcp.tool("create_image")(create_image)
    mcp.tool("deregister_image")(deregister_image)