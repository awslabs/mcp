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

"""Hash operations for Valkey MCP Server."""

from awslabs.valkey_mcp_server.common.connection import ValkeyConnectionManager
from awslabs.valkey_mcp_server.common.server import mcp
from awslabs.valkey_mcp_server.context import Context
from typing import Any, Dict, Optional, Union
from valkey.exceptions import ValkeyError


@mcp.tool()
async def hash_set(key: str, field: str, value: Any) -> str:
    """Set field in hash.

    Args:
        key: The name of the key
        field: The field name
        value: The value to set

    Returns:
        Success message or error message
    """
    # Check if readonly mode is enabled
    if Context.readonly_mode():
        return 'Error: Cannot set hash field in readonly mode'

    try:
        r = ValkeyConnectionManager.get_connection()
        r.hset(key, field, value)
        return f"Successfully set field '{field}' in hash '{key}'"
    except ValkeyError as e:
        return f"Error setting hash field in '{key}': {str(e)}"


@mcp.tool()
async def hash_set_multiple(key: str, mapping: Dict[str, Any]) -> str:
    """Set multiple fields in hash.

    Args:
        key: The name of the key
        mapping: Dictionary of field-value pairs

    Returns:
        Success message or error message
    """
    # Check if readonly mode is enabled
    if Context.readonly_mode():
        return 'Error: Cannot set multiple hash fields in readonly mode'

    try:
        r = ValkeyConnectionManager.get_connection()
        result = r.hset(key, mapping=mapping)
        return f"Successfully set {result} fields in hash '{key}'"
    except ValkeyError as e:
        return f"Error setting multiple hash fields in '{key}': {str(e)}"


@mcp.tool()
async def hash_set_if_not_exists(key: str, field: str, value: Any) -> str:
    """Set field in hash only if it does not exist.

    Args:
        key: The name of the key
        field: The field name
        value: The value to set

    Returns:
        Success message or error message
    """
    # Check if readonly mode is enabled
    if Context.readonly_mode():
        return 'Error: Cannot set hash field in readonly mode'

    try:
        r = ValkeyConnectionManager.get_connection()
        result = r.hsetnx(key, field, value)
        if result:
            return f"Successfully set field '{field}' in hash '{key}'"
        return f"Field '{field}' already exists in hash '{key}'"
    except ValkeyError as e:
        return f"Error setting hash field in '{key}': {str(e)}"


@mcp.tool()
async def hash_get(key: str, field: str) -> str:
    """Get field from hash.

    Args:
        key: The name of the key
        field: The field name

    Returns:
        Field value or error message
    """
    try:
        r = ValkeyConnectionManager.get_connection()
        result = r.hget(key, field)
        if result is None:
            return f"Field '{field}' not found in hash '{key}'"
        return str(result)
    except ValkeyError as e:
        return f"Error getting hash field from '{key}': {str(e)}"


@mcp.tool()
async def hash_get_all(key: str) -> str:
    """Get all fields and values from hash.

    Args:
        key: The name of the key

    Returns:
        Dictionary of field-value pairs or error message
    """
    try:
        r = ValkeyConnectionManager.get_connection()
        result = r.hgetall(key)
        if not result:
            return f"No fields found in hash '{key}'"
        return str(result)
    except ValkeyError as e:
        return f"Error getting all hash fields from '{key}': {str(e)}"


@mcp.tool()
async def hash_exists(key: str, field: str) -> str:
    """Check if field exists in hash.

    Args:
        key: The name of the key
        field: The field name

    Returns:
        Boolean result or error message
    """
    try:
        r = ValkeyConnectionManager.get_connection()
        result = r.hexists(key, field)
        return str(result).lower()
    except ValkeyError as e:
        return f"Error checking hash field existence in '{key}': {str(e)}"


@mcp.tool()
async def hash_increment(key: str, field: str, amount: Union[int, float] = 1) -> str:
    """Increment field value in hash.

    Args:
        key: The name of the key
        field: The field name
        amount: Amount to increment by (default: 1)

    Returns:
        New value or error message
    """
    # Check if readonly mode is enabled
    if Context.readonly_mode():
        return 'Error: Cannot increment hash field in readonly mode'

    try:
        r = ValkeyConnectionManager.get_connection()
        if isinstance(amount, int):
            result = r.hincrby(key, field, amount)
        else:
            result = r.hincrbyfloat(key, field, amount)
        return str(result)
    except ValkeyError as e:
        return f"Error incrementing hash field in '{key}': {str(e)}"


@mcp.tool()
async def hash_keys(key: str) -> str:
    """Get all field names from hash.

    Args:
        key: The name of the key

    Returns:
        List of field names or error message
    """
    try:
        r = ValkeyConnectionManager.get_connection()
        result = r.hkeys(key)
        if not result:
            return f"No fields found in hash '{key}'"
        return str(result)
    except ValkeyError as e:
        return f"Error getting hash field names from '{key}': {str(e)}"


@mcp.tool()
async def hash_length(key: str) -> str:
    """Get number of fields in hash.

    Args:
        key: The name of the key

    Returns:
        Number of fields or error message
    """
    try:
        r = ValkeyConnectionManager.get_connection()
        result = r.hlen(key)
        return str(result)
    except ValkeyError as e:
        return f"Error getting hash length from '{key}': {str(e)}"


@mcp.tool()
async def hash_random_field(key: str, count: Optional[int] = None) -> str:
    """Get random field(s) from hash.

    Args:
        key: The name of the key
        count: Number of fields to return (optional)

    Returns:
        Random field(s) or error message
    """
    try:
        r = ValkeyConnectionManager.get_connection()
        if count:
            result = r.hrandfield(key, count)
        else:
            result = r.hrandfield(key)
        if not result:
            return f"No fields found in hash '{key}'"
        return str(result)
    except ValkeyError as e:
        return f"Error getting random hash field from '{key}': {str(e)}"


@mcp.tool()
async def hash_random_field_with_values(key: str, count: int) -> str:
    """Get random field(s) with their values from hash.

    Args:
        key: The name of the key
        count: Number of field-value pairs to return

    Returns:
        Random field-value pairs or error message
    """
    try:
        r = ValkeyConnectionManager.get_connection()
        result = r.hrandfield(key, count, withvalues=True)
        if not result:
            return f"No fields found in hash '{key}'"
        return str(result)
    except ValkeyError as e:
        return f"Error getting random hash field-value pairs from '{key}': {str(e)}"


@mcp.tool()
async def hash_strlen(key: str, field: str) -> str:
    """Get length of field value in hash.

    Args:
        key: The name of the key
        field: The field name

    Returns:
        Length of field value or error message
    """
    try:
        r = ValkeyConnectionManager.get_connection()
        result = r.hstrlen(key, field)
        return str(result)
    except ValkeyError as e:
        return f"Error getting hash field value length from '{key}': {str(e)}"


@mcp.tool()
async def hash_values(key: str) -> str:
    """Get all values from hash.

    Args:
        key: The name of the key

    Returns:
        List of values or error message
    """
    try:
        r = ValkeyConnectionManager.get_connection()
        result = r.hvals(key)
        if not result:
            return f"No values found in hash '{key}'"
        return str(result)
    except ValkeyError as e:
        return f"Error getting hash values from '{key}': {str(e)}"
