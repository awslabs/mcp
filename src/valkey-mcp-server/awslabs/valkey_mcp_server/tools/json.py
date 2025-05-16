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

"""JSON operations for Valkey MCP Server."""

from awslabs.valkey_mcp_server.common.connection import ValkeyConnectionManager
from awslabs.valkey_mcp_server.common.server import mcp
from typing import Any, Optional, Union
from valkey.exceptions import ValkeyError


@mcp.tool()
async def json_set(key: str, path: str, value: Any, nx: bool = False, xx: bool = False) -> str:
    """Set the JSON value at path.

    Args:
        key: The name of the key
        path: The path in the JSON document (e.g., "$.name" or "." for root)
        value: The value to set
        nx: Only set if path doesn't exist
        xx: Only set if path exists

    Returns:
        Success message or error message
    """
    try:
        r = ValkeyConnectionManager.get_connection()
        options = {}
        if nx:
            options['nx'] = True
        if xx:
            options['xx'] = True

        result = r.json().set(key, path, value, **options)
        if result:
            return f"Successfully set value at path '{path}' in '{key}'"
        return f"Failed to set value at path '{path}' in '{key}' (path condition not met)"
    except ValkeyError as e:
        return f"Error setting JSON value in '{key}': {str(e)}"


@mcp.tool()
async def json_get(
    key: str,
    path: Optional[str] = None,
    indent: Optional[int] = None,
    newline: Optional[bool] = None,
    space: Optional[bool] = None,
) -> str:
    """Get the JSON value at path.

    Args:
        key: The name of the key
        path: The path in the JSON document (optional, defaults to root)
        indent: Number of spaces for indentation (optional)
        newline: Add newlines in formatted output (optional)
        space: Add spaces in formatted output (optional)

    Returns:
        JSON value or error message
    """
    try:
        r = ValkeyConnectionManager.get_connection()
        options = {}
        if indent is not None:
            options['indent'] = indent
        if newline is not None:
            options['newline'] = newline
        if space is not None:
            options['space'] = space

        result = r.json().get(key, path, **options) if path else r.json().get(key)
        if result is None:
            return f"No value found at path '{path or '.'}' in '{key}'"
        return str(result)
    except ValkeyError as e:
        return f"Error getting JSON value from '{key}': {str(e)}"


@mcp.tool()
async def json_type(key: str, path: Optional[str] = None) -> str:
    """Get the type of JSON value at path.

    Args:
        key: The name of the key
        path: The path in the JSON document (optional, defaults to root)

    Returns:
        JSON type or error message
    """
    try:
        r = ValkeyConnectionManager.get_connection()
        result = r.json().type(key, path) if path else r.json().type(key)
        if result is None:
            return f"No value found at path '{path or '.'}' in '{key}'"
        return f"Type at path '{path or '.'}' in '{key}': {result}"
    except ValkeyError as e:
        return f"Error getting JSON type from '{key}': {str(e)}"


@mcp.tool()
async def json_numincrby(key: str, path: str, value: Union[int, float]) -> str:
    """Increment the number at path by value.

    Args:
        key: The name of the key
        path: The path in the JSON document
        value: The increment value (integer or float)

    Returns:
        New value or error message
    """
    try:
        r = ValkeyConnectionManager.get_connection()
        # Convert float to int by rounding if needed
        int_value = round(value) if isinstance(value, float) else value
        result = r.json().numincrby(key, path, int_value)
        return f"Value at path '{path}' in '{key}' incremented to {result}"
    except ValkeyError as e:
        return f"Error incrementing JSON value in '{key}': {str(e)}"


@mcp.tool()
async def json_nummultby(key: str, path: str, value: Union[int, float]) -> str:
    """Multiply the number at path by value.

    Args:
        key: The name of the key
        path: The path in the JSON document
        value: The multiplier value (integer or float)

    Returns:
        New value or error message
    """
    try:
        r = ValkeyConnectionManager.get_connection()
        # Convert float to int by rounding if needed
        int_value = round(value) if isinstance(value, float) else value
        result = r.json().nummultby(key, path, int_value)
        return f"Value at path '{path}' in '{key}' multiplied to {result}"
    except ValkeyError as e:
        return f"Error multiplying JSON value in '{key}': {str(e)}"


@mcp.tool()
async def json_strappend(key: str, path: str, value: str) -> str:
    """Append a string to the string at path.

    Args:
        key: The name of the key
        path: The path in the JSON document
        value: The string to append

    Returns:
        New string length or error message
    """
    try:
        r = ValkeyConnectionManager.get_connection()
        result = r.json().strappend(key, path, value)
        return f"String at path '{path}' in '{key}' appended, new length: {result}"
    except ValkeyError as e:
        return f"Error appending to JSON string in '{key}': {str(e)}"


@mcp.tool()
async def json_strlen(key: str, path: str) -> str:
    """Get the length of string at path.

    Args:
        key: The name of the key
        path: The path in the JSON document

    Returns:
        String length or error message
    """
    try:
        r = ValkeyConnectionManager.get_connection()
        result = r.json().strlen(key, path)
        if result is None:
            return f"No string found at path '{path}' in '{key}'"
        return f"Length of string at path '{path}' in '{key}': {result}"
    except ValkeyError as e:
        return f"Error getting JSON string length from '{key}': {str(e)}"


@mcp.tool()
async def json_arrappend(key: str, path: str, *values: Any) -> str:
    """Append values to the array at path.

    Args:
        key: The name of the key
        path: The path in the JSON document
        *values: One or more values to append

    Returns:
        New array length or error message
    """
    try:
        if not values:
            return 'Error: at least one value is required'

        r = ValkeyConnectionManager.get_connection()
        result = r.json().arrappend(key, path, *values)
        return f"Array at path '{path}' in '{key}' appended, new length: {result}"
    except ValkeyError as e:
        return f"Error appending to JSON array in '{key}': {str(e)}"


@mcp.tool()
async def json_arrindex(
    key: str, path: str, value: Any, start: Optional[int] = None, stop: Optional[int] = None
) -> str:
    """Get the index of value in array at path.

    Args:
        key: The name of the key
        path: The path in the JSON document
        value: The value to search for
        start: Start offset (optional)
        stop: Stop offset (optional)

    Returns:
        Index or error message
    """
    try:
        r = ValkeyConnectionManager.get_connection()
        args = [value]
        if start is not None:
            args.append(start)
            if stop is not None:
                args.append(stop)

        result = r.json().arrindex(key, path, *args)
        if result == -1:
            range_str = ''
            if start is not None or stop is not None:
                range_str = f' in range [{start or 0}, {stop or "∞"}]'
            return f"Value not found in array at path '{path}' in '{key}'{range_str}"
        return f"Value found at index {result} in array at path '{path}' in '{key}'"
    except ValkeyError as e:
        return f"Error searching JSON array in '{key}': {str(e)}"


@mcp.tool()
async def json_arrlen(key: str, path: str) -> str:
    """Get the length of array at path.

    Args:
        key: The name of the key
        path: The path in the JSON document

    Returns:
        Array length or error message
    """
    try:
        r = ValkeyConnectionManager.get_connection()
        result = r.json().arrlen(key, path)
        if result is None:
            return f"No array found at path '{path}' in '{key}'"
        return f"Length of array at path '{path}' in '{key}': {result}"
    except ValkeyError as e:
        return f"Error getting JSON array length from '{key}': {str(e)}"


@mcp.tool()
async def json_arrpop(key: str, path: str, index: int = -1) -> str:
    """Pop a value from the array at path and index.

    Args:
        key: The name of the key
        path: The path in the JSON document
        index: The index to pop from (-1 for last element)

    Returns:
        Popped value or error message
    """
    try:
        r = ValkeyConnectionManager.get_connection()
        result = r.json().arrpop(key, path, index)
        if result is None:
            return f"No value found at index {index} in array at path '{path}' in '{key}'"
        return f"Popped value from index {index} in array at path '{path}' in '{key}': {result}"
    except ValkeyError as e:
        return f"Error popping from JSON array in '{key}': {str(e)}"


@mcp.tool()
async def json_arrtrim(key: str, path: str, start: int, stop: int) -> str:
    """Trim array at path to include only elements within range.

    Args:
        key: The name of the key
        path: The path in the JSON document
        start: Start index (inclusive)
        stop: Stop index (inclusive)

    Returns:
        New array length or error message
    """
    try:
        r = ValkeyConnectionManager.get_connection()
        result = r.json().arrtrim(key, path, start, stop)
        return f"Array at path '{path}' in '{key}' trimmed to range [{start}, {stop}], new length: {result}"
    except ValkeyError as e:
        return f"Error trimming JSON array in '{key}': {str(e)}"


@mcp.tool()
async def json_objkeys(key: str, path: str) -> str:
    """Get the keys in the object at path.

    Args:
        key: The name of the key
        path: The path in the JSON document

    Returns:
        List of keys or error message
    """
    try:
        r = ValkeyConnectionManager.get_connection()
        result = r.json().objkeys(key, path)
        if result is None:
            return f"No object found at path '{path}' in '{key}'"
        if not result:
            return f"Object at path '{path}' in '{key}' has no keys"
        # Filter out None values and ensure all elements are strings
        valid_keys = [str(key) for key in result if key is not None]
        return f"Keys in object at path '{path}' in '{key}': {', '.join(valid_keys)}"
    except ValkeyError as e:
        return f"Error getting JSON object keys from '{key}': {str(e)}"


@mcp.tool()
async def json_objlen(key: str, path: str) -> str:
    """Get the number of keys in the object at path.

    Args:
        key: The name of the key
        path: The path in the JSON document

    Returns:
        Number of keys or error message
    """
    try:
        r = ValkeyConnectionManager.get_connection()
        result = r.json().objlen(key, path)
        if result is None:
            return f"No object found at path '{path}' in '{key}'"
        return f"Number of keys in object at path '{path}' in '{key}': {result}"
    except ValkeyError as e:
        return f"Error getting JSON object length from '{key}': {str(e)}"


@mcp.tool()
async def json_toggle(key: str, path: str) -> str:
    """Toggle boolean value at path.

    Args:
        key: The name of the key
        path: The path in the JSON document

    Returns:
        New boolean value or error message
    """
    try:
        r = ValkeyConnectionManager.get_connection()
        result = r.json().toggle(key, path)
        if result is None:
            return f"No boolean value found at path '{path}' in '{key}'"
        return f"Boolean value at path '{path}' in '{key}' toggled to: {str(result).lower()}"
    except ValkeyError as e:
        return f"Error toggling JSON boolean in '{key}': {str(e)}"


@mcp.tool()
async def json_clear(key: str, path: str) -> str:
    """Clear container at path (array or object).

    Args:
        key: The name of the key
        path: The path in the JSON document

    Returns:
        Success message or error message
    """
    try:
        r = ValkeyConnectionManager.get_connection()
        result = r.json().clear(key, path)
        if result == 1:
            return f"Successfully cleared container at path '{path}' in '{key}'"
        return f"No container found at path '{path}' in '{key}'"
    except ValkeyError as e:
        return f"Error clearing JSON container in '{key}': {str(e)}"


@mcp.tool()
async def json_del(key: str, path: str) -> str:
    """Delete value at path.

    Args:
        key: The name of the key
        path: The path in the JSON document

    Returns:
        Success message or error message
    """
    try:
        r = ValkeyConnectionManager.get_connection()
        result = r.json().delete(key, path)
        if result == 1:
            return f"Successfully deleted value at path '{path}' in '{key}'"
        return f"No value found at path '{path}' in '{key}'"
    except ValkeyError as e:
        return f"Error deleting JSON value in '{key}': {str(e)}"
