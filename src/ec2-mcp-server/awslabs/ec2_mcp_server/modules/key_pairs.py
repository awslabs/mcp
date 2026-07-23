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
EC2 key pairs management module.
"""

import logging
from typing import Any, Dict, List, Optional, Literal

from mcp.server.fastmcp import FastMCP

from awslabs.ec2_mcp_server.utils.aws import AWSClientManager, handle_aws_error, parse_tags, format_tags
from awslabs.ec2_mcp_server.utils.config import get_config
from awslabs.ec2_mcp_server.utils.security import validate_key_pair_name
from awslabs.ec2_mcp_server.utils.key_storage import KeyStorageManager

logger = logging.getLogger(__name__)

# Initialize AWS client manager and storage manager
config = get_config()
aws_client = AWSClientManager(
    region=config.get("aws_region", "us-east-1"),
    profile=config.get("aws_profile")
)
key_storage = KeyStorageManager(aws_client, config)


async def list_key_pairs(
    key_names: Optional[List[str]] = None,
    filters: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """
    List EC2 key pairs with optional filtering.

    Args:
        key_names: Optional list of key pair names
        filters: Optional list of filters to apply

    Returns:
        Dict containing key pair information
    """
    try:
        ec2_client = aws_client.get_client("ec2")
        
        # Prepare describe_key_pairs parameters
        params = {}
        if key_names:
            params["KeyNames"] = key_names
        if filters:
            params["Filters"] = filters

        response = ec2_client.describe_key_pairs(**params)
        
        key_pairs = []
        for kp in response["KeyPairs"]:
            key_pairs.append({
                "key_name": kp["KeyName"],
                "key_pair_id": kp["KeyPairId"],
                "key_fingerprint": kp["KeyFingerprint"],
                "key_type": kp["KeyType"],
                "tags": parse_tags(kp.get("Tags", [])),
            })
        
        return {
            "status": "success",
            "key_pairs": key_pairs,
            "count": len(key_pairs),
        }
    
    except Exception as e:
        logger.error(f"Failed to list key pairs: {e}")
        return handle_aws_error(e)


async def create_key_pair(
    key_name: str,
    storage_method: Literal["secrets_manager", "s3_encrypted", "parameter_store"],
    key_type: str = "rsa",
    tags: Optional[Dict[str, str]] = None,
    storage_kwargs: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    create_key_pair
            Creates an EC2 key pair and securely stores the private key using the specified method.
            Private key storage is mandatory for security reasons.
            
            IMPORTANT: You MUST explicitly choose and specify a storage_method. No defaults are provided.
            
            Required:
                key_name: Unique name for the key pair
                storage_method: REQUIRED - Must explicitly choose one: "secrets_manager", "s3_encrypted", or "parameter_store"
            Optional:
                key_type: Key algorithm ("rsa" or "ed25519", default "rsa")
                tags: Tags to associate with the key pair
                storage_kwargs: Extra parameters for the selected storage method
            Returns: 
                Dict with key pair creation details and storage information.
    """
    try:
        validate_key_pair_name(key_name)
        
        ec2_client = aws_client.get_client("ec2")
        
        params = {
            "KeyName": key_name,
            "KeyType": key_type,
        }
        
        if tags:
            params["TagSpecifications"] = [
                {
                    "ResourceType": "key-pair",
                    "Tags": format_tags(tags),
                }
            ]
        
        response = ec2_client.create_key_pair(**params)
        
        # Prepare the result
        result = {
            "status": "success",
            "message": f"Successfully created key pair {key_name}",
            "key_name": response["KeyName"],
            "key_pair_id": response["KeyPairId"],
        }
        
        # Store the private key securely (mandatory for security)
        kwargs = storage_kwargs or {}
        # Extract private key material and immediately clear from response to minimize exposure
        private_key_data = response["KeyMaterial"]
        response["KeyMaterial"] = "[REDACTED]"
        
        storage_result = await key_storage.store_private_key(
            key_name=key_name,
            private_key_material=private_key_data,
            storage_method=storage_method,
            tags=tags,
            **kwargs
        )
        # Clear private key from memory immediately after use
        private_key_data = None
        
        if storage_result.get("status") == "success":
            result.update({
                "private_key_stored": True,
                "storage_method": storage_method,
                "storage_location": storage_result.get("storage_location"),
                "storage_details": {k: v for k, v in storage_result.items() 
                                 if k not in ["status", "message"]}
            })
            result["message"] += f" and private key securely stored using {key_storage.STORAGE_METHODS[storage_method]}"
        else:
            # Storage failed - rollback by deleting the created key pair
            logger.error(f"Storage failed for key pair {key_name}, initiating rollback")
            try:
                ec2_client.delete_key_pair(KeyName=key_name)
                logger.info(f"Successfully rolled back key pair {key_name}")
                return {
                    "status": "error",
                    "message": f"Key pair creation failed: storage error - {storage_result.get('message', 'Unknown storage error')}",
                    "rollback": "Key pair was deleted due to storage failure"
                }
            except Exception as rollback_error:
                logger.error(f"Rollback failed for key pair {key_name}: {rollback_error}")
                return {
                    "status": "error", 
                    "message": f"Key pair creation failed: storage error - {storage_result.get('message', 'Unknown storage error')}",
                    "rollback_error": f"Failed to delete key pair during rollback: {str(rollback_error)}",
                    "warning": f"Key pair {key_name} exists but private key was not stored. Manual cleanup may be required."
                }
        
        return result
    
    except Exception as e:
        logger.error(f"Failed to create key pair: {e}")
        return handle_aws_error(e)



async def delete_key_pair(
    key_name: str,
    storage_method: Optional[Literal["secrets_manager", "s3_encrypted", "parameter_store"]] = None,
    storage_location: Optional[str] = None,
    delete_stored_key: bool = True
) -> Dict[str, Any]:
    """
    Delete an EC2 key pair and optionally its stored private key.

    Args:
        key_name: The key pair name to delete
        storage_method: Storage method used for private key
        storage_location: Location of stored private key
        delete_stored_key: Whether to also delete stored private key (default True)

    Returns:
        Dict containing deletion results
    """
    try:
        validate_key_pair_name(key_name)
        
        ec2_client = aws_client.get_client("ec2")
        ec2_client.delete_key_pair(KeyName=key_name)
        
        result = {
            "status": "success",
            "message": f"Successfully deleted key pair {key_name}",
            "key_name": key_name,
        }
        
        # Delete stored private key if requested and info provided
        if delete_stored_key:
            if storage_method and storage_location:
                storage_result = await key_storage.delete_stored_key(
                    key_name=key_name,
                    storage_method=storage_method,
                    storage_location=storage_location
                )
                
                if storage_result.get("status") == "success":
                    result["stored_key_deleted"] = True
                    result["message"] += " and stored private key deleted"
                else:
                    result["warning"] = f"Key pair deleted but stored key deletion failed: {storage_result.get('message')}"
            else:
                result["warning"] = "Key pair deleted but stored key deletion was requested without storage_method and storage_location. Private key may still exist in AWS storage."
        
        return result
    
    except Exception as e:
        logger.error(f"Failed to delete key pair: {e}")
        return handle_aws_error(e)





def register_module(mcp: FastMCP) -> None:
    """
    Register the key pairs module with the MCP server.

    Args:
        mcp: The FastMCP server instance
    """
    mcp.tool("list_key_pairs")(list_key_pairs)
    mcp.tool("create_key_pair")(create_key_pair)
    mcp.tool("delete_key_pair")(delete_key_pair)
