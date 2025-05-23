# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance
# with the License. A copy of the License is located at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES
# OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions
# and limitations under the License.

"""Set operations for Valkey MCP Server."""

from awslabs.valkey_mcp_server.common.connection import ValkeyConnectionManager
from awslabs.valkey_mcp_server.common.server import mcp
from typing import Any, Optional
from valkey.exceptions import ValkeyError


@mcp.tool()
async def set_add(key: str, member: str) -> str:
    """Add member to set.

    Args:
        key: The name of the key
        member: Member to add

    Returns:
        Success message or error message
    """
    try:
        r = ValkeyConnectionManager.get_connection()
        result = r.sadd(key, member)
        return f"Successfully added {result} new member to set '{key}'"
    except ValkeyError as e:
        return f"Error adding to set '{key}': {str(e)}"


@mcp.tool()
async def set_remove(key: str, member: str) -> str:
    """Remove member from set.

    Args:
        key: The name of the key
        member: Member to remove

    Returns:
        Success message or error message
    """
    try:
        r = ValkeyConnectionManager.get_connection()
        result = r.srem(key, member)
        return f"Successfully removed {result} member from set '{key}'"
    except ValkeyError as e:
        return f"Error removing from set '{key}': {str(e)}"


@mcp.tool()
async def set_pop(key: str, count: Optional[int] = None) -> str:
    """Remove and return random member(s) from set.

    Args:
        key: The name of the key
        count: Number of members to pop (optional)

    Returns:
        Popped member(s) or error message
    """
    try:
        r = ValkeyConnectionManager.get_connection()
        if count:
            result = r.spop(key, count)
        else:
            result = r.spop(key)
        if result is None:
            return f"Set '{key}' is empty"
        return str(result)
    except ValkeyError as e:
        return f"Error popping from set '{key}': {str(e)}"


@mcp.tool()
async def set_move(source: str, destination: str, member: Any) -> str:
    """Move member from one set to another.

    Args:
        source: Source set key
        destination: Destination set key
        member: Member to move

    Returns:
        Success message or error message
    """
    try:
        r = ValkeyConnectionManager.get_connection()
        result = r.smove(source, destination, member)
        if result:
            return f"Successfully moved member from set '{source}' to '{destination}'"
        return f"Member not found in source set '{source}'"
    except ValkeyError as e:
        return f'Error moving between sets: {str(e)}'


@mcp.tool()
async def set_cardinality(key: str) -> str:
    """Get number of members in set.

    Args:
        key: The name of the key

    Returns:
        Number of members or error message
    """
    try:
        r = ValkeyConnectionManager.get_connection()
        result = r.scard(key)
        return str(result)
    except ValkeyError as e:
        return f"Error getting set cardinality for '{key}': {str(e)}"


@mcp.tool()
async def set_members(key: str) -> str:
    """Get all members in set.

    Args:
        key: The name of the key

    Returns:
        List of members or error message
    """
    try:
        r = ValkeyConnectionManager.get_connection()
        result = r.smembers(key)
        if not result:
            return f"Set '{key}' is empty"
        return str(result)
    except ValkeyError as e:
        return f"Error getting set members from '{key}': {str(e)}"


@mcp.tool()
async def set_random_member(key: str, count: Optional[int] = None) -> str:
    """Get random member(s) from set without removing.

    Args:
        key: The name of the key
        count: Number of members to return (optional)

    Returns:
        Random member(s) or error message
    """
    try:
        r = ValkeyConnectionManager.get_connection()
        if count:
            result = r.srandmember(key, count)
        else:
            result = r.srandmember(key)
        if result is None:
            return f"Set '{key}' is empty"
        return str(result)
    except ValkeyError as e:
        return f"Error getting random member from set '{key}': {str(e)}"


@mcp.tool()
async def set_contains(key: str, member: Any) -> str:
    """Check if member exists in set.

    Args:
        key: The name of the key
        member: Member to check

    Returns:
        Boolean result or error message
    """
    try:
        r = ValkeyConnectionManager.get_connection()
        result = r.sismember(key, member)
        return str(result).lower()
    except ValkeyError as e:
        return f"Error checking set membership in '{key}': {str(e)}"
