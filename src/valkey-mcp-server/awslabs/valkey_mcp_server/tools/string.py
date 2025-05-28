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

"""String operations for Valkey MCP Server."""

from awslabs.valkey_mcp_server.common.connection import ValkeyConnectionManager
from awslabs.valkey_mcp_server.common.server import mcp
from typing import Any, Optional
from valkey.exceptions import ValkeyError


@mcp.tool()
async def string_set(
    key: str,
    value: Any,
    ex: Optional[int] = None,
    px: Optional[int] = None,
    nx: bool = False,
    xx: bool = False,
    keepttl: bool = False,
) -> str:
    """Set string value.

    Args:
        key: The name of the key
        value: The value to set
        ex: Expire time in seconds
        px: Expire time in milliseconds
        nx: Only set if key does not exist
        xx: Only set if key exists
        keepttl: Retain the time to live associated with the key

    Returns:
        Success message or error message
    """
    try:
        r = ValkeyConnectionManager.get_connection()
        result = r.set(key, value, ex=ex, px=px, nx=nx, xx=xx, keepttl=keepttl)
        if result is None:
            return f"Failed to set value for key '{key}' (condition not met)"
        return f"Successfully set value for key '{key}'"
    except ValkeyError as e:
        return f"Error setting string value for '{key}': {str(e)}"


@mcp.tool()
async def string_get(key: str) -> str:
    """Get string value.

    Args:
        key: The name of the key

    Returns:
        Value or error message
    """
    try:
        r = ValkeyConnectionManager.get_connection()
        result = r.get(key)
        if result is None:
            return f"Key '{key}' not found"
        return str(result)
    except ValkeyError as e:
        return f"Error getting string value from '{key}': {str(e)}"


@mcp.tool()
async def string_append(key: str, value: str) -> str:
    """Append to string value.

    Args:
        key: The name of the key
        value: String to append

    Returns:
        Success message or error message
    """
    try:
        r = ValkeyConnectionManager.get_connection()
        result = r.append(key, value)
        return f"Successfully appended to key '{key}', new length: {result}"
    except ValkeyError as e:
        return f"Error appending to string '{key}': {str(e)}"


@mcp.tool()
async def string_get_range(key: str, start: int, end: int) -> str:
    """Get substring.

    Args:
        key: The name of the key
        start: Start index (inclusive)
        end: End index (inclusive)

    Returns:
        Substring or error message
    """
    try:
        r = ValkeyConnectionManager.get_connection()
        result = r.getrange(key, start, end)
        if not result:
            return f"No characters found in range [{start}, {end}] for key '{key}'"
        return str(result)
    except ValkeyError as e:
        return f"Error getting range from string '{key}': {str(e)}"


@mcp.tool()
async def string_get_set(key: str, value: Any) -> str:
    """Set new value and return old value.

    Args:
        key: The name of the key
        value: New value to set

    Returns:
        Old value or error message
    """
    try:
        r = ValkeyConnectionManager.get_connection()
        result = r.getset(key, value)
        if result is None:
            return f"No previous value found for key '{key}'"
        return str(result)
    except ValkeyError as e:
        return f"Error getting and setting string '{key}': {str(e)}"


@mcp.tool()
async def string_increment(key: str, amount: int = 1) -> str:
    """Increment integer value.

    Args:
        key: The name of the key
        amount: Amount to increment by (default 1)

    Returns:
        New value or error message
    """
    try:
        r = ValkeyConnectionManager.get_connection()
        result = r.incrby(key, amount)
        return str(result)
    except ValkeyError as e:
        return f"Error incrementing string '{key}': {str(e)}"


@mcp.tool()
async def string_increment_float(key: str, amount: float) -> str:
    """Increment float value.

    Args:
        key: The name of the key
        amount: Amount to increment by

    Returns:
        New value or error message
    """
    try:
        r = ValkeyConnectionManager.get_connection()
        result = r.incrbyfloat(key, amount)
        return str(result)
    except ValkeyError as e:
        return f"Error incrementing float string '{key}': {str(e)}"


@mcp.tool()
async def string_decrement(key: str, amount: int = 1) -> str:
    """Decrement integer value.

    Args:
        key: The name of the key
        amount: Amount to decrement by (default 1)

    Returns:
        New value or error message
    """
    try:
        r = ValkeyConnectionManager.get_connection()
        result = r.decrby(key, amount)
        return str(result)
    except ValkeyError as e:
        return f"Error decrementing string '{key}': {str(e)}"


@mcp.tool()
async def string_length(key: str) -> str:
    """Get string length.

    Args:
        key: The name of the key

    Returns:
        Length or error message
    """
    try:
        r = ValkeyConnectionManager.get_connection()
        result = r.strlen(key)
        return str(result)
    except ValkeyError as e:
        return f"Error getting string length for '{key}': {str(e)}"


@mcp.tool()
async def string_set_range(key: str, offset: int, value: str) -> str:
    """Overwrite part of string.

    Args:
        key: The name of the key
        offset: Position to start overwriting
        value: String to write

    Returns:
        Success message or error message
    """
    try:
        r = ValkeyConnectionManager.get_connection()
        result = r.setrange(key, offset, value)
        return f"Successfully set range in string '{key}', new length: {result}"
    except ValkeyError as e:
        return f"Error setting range in string '{key}': {str(e)}"
