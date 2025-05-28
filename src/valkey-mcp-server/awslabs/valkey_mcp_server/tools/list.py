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

"""List operations for Valkey MCP Server."""

from awslabs.valkey_mcp_server.common.connection import ValkeyConnectionManager
from awslabs.valkey_mcp_server.common.server import mcp
from typing import Any, Optional
from typing import List as PyList
from valkey.exceptions import ValkeyError


@mcp.tool()
async def list_append(key: str, value: Any) -> str:
    """Append value to list.

    Args:
        key: The name of the key
        value: The value to append

    Returns:
        Success message or error message
    """
    try:
        r = ValkeyConnectionManager.get_connection()
        result = r.rpush(key, value)
        return f"Successfully appended value to list '{key}', new length: {result}"
    except ValkeyError as e:
        return f"Error appending to list '{key}': {str(e)}"


@mcp.tool()
async def list_prepend(key: str, value: Any) -> str:
    """Prepend value to list.

    Args:
        key: The name of the key
        value: The value to prepend

    Returns:
        Success message or error message
    """
    try:
        r = ValkeyConnectionManager.get_connection()
        result = r.lpush(key, value)
        return f"Successfully prepended value to list '{key}', new length: {result}"
    except ValkeyError as e:
        return f"Error prepending to list '{key}': {str(e)}"


@mcp.tool()
async def list_append_multiple(key: str, values: PyList[Any]) -> str:
    """Append multiple values to list.

    Args:
        key: The name of the key
        values: List of values to append

    Returns:
        Success message or error message
    """
    try:
        r = ValkeyConnectionManager.get_connection()
        result = r.rpush(key, *values)
        return f"Successfully appended {len(values)} values to list '{key}', new length: {result}"
    except ValkeyError as e:
        return f"Error appending multiple values to list '{key}': {str(e)}"


@mcp.tool()
async def list_prepend_multiple(key: str, values: PyList[Any]) -> str:
    """Prepend multiple values to list.

    Args:
        key: The name of the key
        values: List of values to prepend

    Returns:
        Success message or error message
    """
    try:
        r = ValkeyConnectionManager.get_connection()
        result = r.lpush(key, *values)
        return f"Successfully prepended {len(values)} values to list '{key}', new length: {result}"
    except ValkeyError as e:
        return f"Error prepending multiple values to list '{key}': {str(e)}"


@mcp.tool()
async def list_get(key: str, index: int) -> str:
    """Get value at index from list.

    Args:
        key: The name of the key
        index: The index (0-based, negative indices supported)

    Returns:
        Value or error message
    """
    try:
        r = ValkeyConnectionManager.get_connection()
        result = r.lindex(key, index)
        if result is None:
            return f"No value found at index {index} in list '{key}'"
        return str(result)
    except ValkeyError as e:
        return f"Error getting value from list '{key}': {str(e)}"


@mcp.tool()
async def list_set(key: str, index: int, value: Any) -> str:
    """Set value at index in list.

    Args:
        key: The name of the key
        index: The index (0-based, negative indices supported)
        value: The value to set

    Returns:
        Success message or error message
    """
    try:
        r = ValkeyConnectionManager.get_connection()
        r.lset(key, index, value)
        return f"Successfully set value at index {index} in list '{key}'"
    except ValkeyError as e:
        return f"Error setting value in list '{key}': {str(e)}"


@mcp.tool()
async def list_range(key: str, start: int = 0, stop: int = -1) -> str:
    """Get range of values from list.

    Args:
        key: The name of the key
        start: Start index (inclusive, default 0)
        stop: Stop index (inclusive, default -1 for end)

    Returns:
        List of values or error message
    """
    try:
        r = ValkeyConnectionManager.get_connection()
        result = r.lrange(key, start, stop)
        if not result:
            return f"No values found in range [{start}, {stop}] in list '{key}'"
        return str(result)
    except ValkeyError as e:
        return f"Error getting range from list '{key}': {str(e)}"


@mcp.tool()
async def list_trim(key: str, start: int, stop: int) -> str:
    """Trim list to specified range.

    Args:
        key: The name of the key
        start: Start index (inclusive)
        stop: Stop index (inclusive)

    Returns:
        Success message or error message
    """
    try:
        r = ValkeyConnectionManager.get_connection()
        r.ltrim(key, start, stop)
        return f"Successfully trimmed list '{key}' to range [{start}, {stop}]"
    except ValkeyError as e:
        return f"Error trimming list '{key}': {str(e)}"


@mcp.tool()
async def list_length(key: str) -> str:
    """Get length of list.

    Args:
        key: The name of the key

    Returns:
        Length or error message
    """
    try:
        r = ValkeyConnectionManager.get_connection()
        result = r.llen(key)
        return str(result)
    except ValkeyError as e:
        return f"Error getting list length for '{key}': {str(e)}"


@mcp.tool()
async def list_pop_left(key: str, count: Optional[int] = None) -> str:
    """Pop value(s) from left of list.

    Args:
        key: The name of the key
        count: Number of values to pop (optional)

    Returns:
        Value(s) or error message
    """
    try:
        r = ValkeyConnectionManager.get_connection()
        if count:
            result = r.lpop(key, count)
        else:
            result = r.lpop(key)
        if result is None:
            return f"List '{key}' is empty"
        return str(result)
    except ValkeyError as e:
        return f"Error popping from left of list '{key}': {str(e)}"


@mcp.tool()
async def list_pop_right(key: str, count: Optional[int] = None) -> str:
    """Pop value(s) from right of list.

    Args:
        key: The name of the key
        count: Number of values to pop (optional)

    Returns:
        Value(s) or error message
    """
    try:
        r = ValkeyConnectionManager.get_connection()
        if count:
            result = r.rpop(key, count)
        else:
            result = r.rpop(key)
        if result is None:
            return f"List '{key}' is empty"
        return str(result)
    except ValkeyError as e:
        return f"Error popping from right of list '{key}': {str(e)}"


@mcp.tool()
async def list_position(
    key: str,
    value: Any,
    rank: Optional[int] = None,
    count: Optional[int] = None,
    maxlen: Optional[int] = None,
) -> str:
    """Find position(s) of value in list.

    Args:
        key: The name of the key
        value: Value to search for
        rank: Match the Nth occurrence (optional)
        count: Return this many matches (optional)
        maxlen: Limit search to first N elements (optional)

    Returns:
        Position(s) or error message
    """
    try:
        r = ValkeyConnectionManager.get_connection()
        options = {}
        if rank is not None:
            options['rank'] = rank
        if count is not None:
            options['count'] = count
        if maxlen is not None:
            options['maxlen'] = maxlen

        result = r.lpos(key, value, **options)
        if result is None:
            return f"Value not found in list '{key}'"
        return str(result)
    except ValkeyError as e:
        return f"Error finding position in list '{key}': {str(e)}"


@mcp.tool()
async def list_move(
    source: str, destination: str, wherefrom: str = 'LEFT', whereto: str = 'RIGHT'
) -> str:
    """Move element from one list to another.

    Args:
        source: Source list key
        destination: Destination list key
        wherefrom: Where to pop from ("LEFT" or "RIGHT")
        whereto: Where to push to ("LEFT" or "RIGHT")

    Returns:
        Moved value or error message
    """
    try:
        r = ValkeyConnectionManager.get_connection()
        wherefrom = wherefrom.upper()
        whereto = whereto.upper()

        if wherefrom not in ['LEFT', 'RIGHT'] or whereto not in ['LEFT', 'RIGHT']:
            return "Error: wherefrom and whereto must be either 'LEFT' or 'RIGHT'"

        result = r.lmove(source, destination, wherefrom, whereto)
        if result is None:
            return f"Source list '{source}' is empty"
        return f"Successfully moved value '{result}' from {wherefrom} of '{source}' to {whereto} of '{destination}'"
    except ValkeyError as e:
        return f'Error moving value between lists: {str(e)}'


@mcp.tool()
async def list_insert_before(key: str, pivot: Any, value: Any) -> str:
    """Insert value before pivot in list.

    Args:
        key: The name of the key
        pivot: The pivot value
        value: The value to insert

    Returns:
        Success message or error message
    """
    try:
        r = ValkeyConnectionManager.get_connection()
        result = r.linsert(key, 'BEFORE', pivot, value)
        if result == -1:
            return f"Pivot value not found in list '{key}'"
        return f"Successfully inserted value before pivot in list '{key}', new length: {result}"
    except ValkeyError as e:
        return f"Error inserting before pivot in list '{key}': {str(e)}"


@mcp.tool()
async def list_insert_after(key: str, pivot: Any, value: Any) -> str:
    """Insert value after pivot in list.

    Args:
        key: The name of the key
        pivot: The pivot value
        value: The value to insert

    Returns:
        Success message or error message
    """
    try:
        r = ValkeyConnectionManager.get_connection()
        result = r.linsert(key, 'AFTER', pivot, value)
        if result == -1:
            return f"Pivot value not found in list '{key}'"
        return f"Successfully inserted value after pivot in list '{key}', new length: {result}"
    except ValkeyError as e:
        return f"Error inserting after pivot in list '{key}': {str(e)}"


@mcp.tool()
async def list_remove(key: str, value: Any, count: int = 0) -> str:
    """Remove occurrences of value from list.

    Args:
        key: The name of the key
        value: Value to remove
        count: Number of occurrences to remove (0 for all, positive for left-to-right, negative for right-to-left)

    Returns:
        Success message or error message
    """
    try:
        r = ValkeyConnectionManager.get_connection()
        result = r.lrem(key, count, value)
        return f"Successfully removed {result} occurrence(s) of value from list '{key}'"
    except ValkeyError as e:
        return f"Error removing value from list '{key}': {str(e)}"
