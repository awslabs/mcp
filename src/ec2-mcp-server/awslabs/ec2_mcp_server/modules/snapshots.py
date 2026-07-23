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
EC2 EBS snapshots management module.
"""

import logging
from typing import Any, Dict, List, Optional

from mcp.server.fastmcp import FastMCP

from awslabs.ec2_mcp_server.utils.aws import AWSClientManager, handle_aws_error, parse_tags, format_tags
from awslabs.ec2_mcp_server.utils.config import get_config
from awslabs.ec2_mcp_server.utils.security import validate_volume_id

logger = logging.getLogger(__name__)

# Initialize AWS client manager
config = get_config()
aws_client = AWSClientManager(
    region=config.get("aws_region", "us-east-1"),
    profile=config.get("aws_profile")
)


async def list_snapshots(
    snapshot_ids: Optional[List[str]] = None,
    owner_ids: Optional[List[str]] = None,
    filters: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """
    List EBS snapshots with optional filtering.

    Args:
        snapshot_ids: Optional list of snapshot IDs
        owner_ids: Optional list of owner IDs
        filters: Optional list of filters to apply

    Returns:
        Dict containing snapshot information
    """
    try:
        ec2_client = aws_client.get_client("ec2")
        
        # Prepare describe_snapshots parameters
        params = {}
        if snapshot_ids:
            params["SnapshotIds"] = snapshot_ids
        if owner_ids:
            params["OwnerIds"] = owner_ids
        if filters:
            params["Filters"] = filters

        response = ec2_client.describe_snapshots(**params)
        
        snapshots = []
        for snap in response["Snapshots"]:
            snapshots.append({
                "snapshot_id": snap["SnapshotId"],
                "volume_id": snap["VolumeId"],
                "state": snap["State"],
                "progress": snap["Progress"],
                "start_time": snap.get("StartTime").isoformat() if snap.get("StartTime") else None,
                "description": snap["Description"],
                "owner_id": snap["OwnerId"],
                "volume_size": snap["VolumeSize"],
                "encrypted": snap["Encrypted"],
                "tags": parse_tags(snap.get("Tags", [])),
            })
        
        return {
            "status": "success",
            "snapshots": snapshots,
            "count": len(snapshots),
        }
    
    except Exception as e:
        logger.error(f"Failed to list snapshots: {e}")
        return handle_aws_error(e)


async def create_snapshot(
    volume_id: str,
    description: Optional[str] = None,
    tags: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """
    Create a snapshot of an EBS volume.

    Args:
        volume_id: The volume ID to snapshot
        description: Optional description for the snapshot
        tags: Optional tags to apply to the snapshot

    Returns:
        Dict containing creation results
    """
    try:
        validate_volume_id(volume_id)
        
        ec2_client = aws_client.get_client("ec2")
        
        params = {
            "VolumeId": volume_id,
        }
        
        if description:
            params["Description"] = description
        
        if tags:
            params["TagSpecifications"] = [
                {
                    "ResourceType": "snapshot",
                    "Tags": format_tags(tags),
                }
            ]
        
        response = ec2_client.create_snapshot(**params)
        
        return {
            "status": "success",
            "message": f"Successfully created snapshot of volume {volume_id}",
            "snapshot_id": response["SnapshotId"],
            "volume_id": response["VolumeId"],
            "state": response["State"],
            "start_time": response.get("StartTime").isoformat() if response.get("StartTime") else None,
            "description": response.get("Description"),
        }
    
    except Exception as e:
        logger.error(f"Failed to create snapshot: {e}")
        return handle_aws_error(e)


def register_module(mcp: FastMCP) -> None:
    """
    Register the snapshots module with the MCP server.

    Args:
        mcp: The FastMCP server instance
    """
    mcp.tool("list_snapshots")(list_snapshots)
    mcp.tool("create_snapshot")(create_snapshot)