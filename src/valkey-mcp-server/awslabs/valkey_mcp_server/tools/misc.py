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

from awslabs.valkey_mcp_server.common.connection import ValkeyConnectionManager
from awslabs.valkey_mcp_server.common.server import mcp
from typing import Any, Dict
from valkey.exceptions import ValkeyError as RedisError


@mcp.tool()
async def delete(key: str) -> str:
    """Delete a Valkey key.

    Args:
        key (str): The key to delete.

    Returns:
        str: Confirmation message or an error message.
    """
    try:
        r = ValkeyConnectionManager.get_connection()
        result = r.delete(key)
        return f'Successfully deleted {key}' if result else f'Key {key} not found'
    except RedisError as e:
        return f'Error deleting key {key}: {str(e)}'


@mcp.tool()
async def type(key: str) -> Dict[str, Any]:
    """Returns the string representation of the type of the value stored at key.

    Args:
        key (str): The key to check.

    Returns:
        str: The type of key, or none when key doesn't exist
    """
    try:
        r = ValkeyConnectionManager.get_connection()
        key_type = r.type(key)
        info = {'key': key, 'type': key_type, 'ttl': r.ttl(key)}

        return info
    except RedisError as e:
        return {'error': str(e)}


@mcp.tool()
async def expire(name: str, expire_seconds: int) -> str:
    """Set an expiration time for a Redis key.

    Args:
        name: The Redis key.
        expire_seconds: Time in seconds after which the key should expire.

    Returns:
        A success message or an error message.
    """
    try:
        r = ValkeyConnectionManager.get_connection()
        success = r.expire(name, expire_seconds)
        return (
            f"Expiration set to {expire_seconds} seconds for '{name}'."
            if success
            else f"Key '{name}' does not exist."
        )
    except RedisError as e:
        return f"Error setting expiration for key '{name}': {str(e)}"


@mcp.tool()
async def rename(old_key: str, new_key: str) -> Dict[str, Any]:
    """Renames a Redis key from old_key to new_key.

    Args:
        old_key (str): The current name of the Redis key to rename.
        new_key (str): The new name to assign to the key.

    Returns:
        Dict[str, Any]: A dictionary containing the result of the operation.
            On success: {"status": "success", "message": "..."}
            On error: {"error": "..."}
    """
    try:
        r = ValkeyConnectionManager.get_connection()

        # Check if the old key exists
        if not r.exists(old_key):
            return {'error': f"Key '{old_key}' does not exist."}

        # Rename the key
        r.rename(old_key, new_key)
        return {'status': 'success', 'message': f"Renamed key '{old_key}' to '{new_key}'"}

    except RedisError as e:
        return {'error': str(e)}
