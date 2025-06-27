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

"""Bitmap operations for Valkey MCP Server."""

from awslabs.valkey_mcp_server.common.connection import ValkeyConnectionManager
from awslabs.valkey_mcp_server.common.server import mcp
from awslabs.valkey_mcp_server.context import Context
from typing import Optional
from valkey.exceptions import ValkeyError


@mcp.tool()
async def bitmap_set(key: str, offset: int, value: int) -> str:
    """Set the bit at offset to value.

    Args:
        key: The name of the bitmap key
        offset: The bit offset (0-based)
        value: The bit value (0 or 1)

    Returns:
        Success message or error message
    """
    # Check if readonly mode is enabled
    if Context.readonly_mode():
        return 'Error: Cannot set bitmap bit in readonly mode'

    try:
        if value not in (0, 1):
            return f'Error: value must be 0 or 1, got {value}'
        if offset < 0:
            return f'Error: offset must be non-negative, got {offset}'

        r = ValkeyConnectionManager.get_connection()
        previous = r.setbit(key, offset, value)
        return f'Bit at offset {offset} set to {value} (previous value: {previous})'
    except ValkeyError as e:
        return f"Error setting bit in '{key}': {str(e)}"


@mcp.tool()
async def bitmap_get(key: str, offset: int) -> str:
    """Get the bit value at offset.

    Args:
        key: The name of the bitmap key
        offset: The bit offset (0-based)

    Returns:
        Bit value or error message
    """
    try:
        if offset < 0:
            return f'Error: offset must be non-negative, got {offset}'

        r = ValkeyConnectionManager.get_connection()
        value = r.getbit(key, offset)
        return f'Bit at offset {offset} is {value}'
    except ValkeyError as e:
        return f"Error getting bit from '{key}': {str(e)}"


@mcp.tool()
async def bitmap_count(key: str, start: Optional[int] = None, end: Optional[int] = None) -> str:
    """Count the number of set bits (1) in a range.

    Args:
        key: The name of the bitmap key
        start: Start offset (inclusive, optional)
        end: End offset (inclusive, optional)

    Returns:
        Count of set bits or error message
    """
    try:
        r = ValkeyConnectionManager.get_connection()
        if start is not None and end is not None:
            if start < 0 or end < 0:
                return 'Error: start and end must be non-negative'
            if start > end:
                return 'Error: start must be less than or equal to end'
            count = r.bitcount(key, start, end)
            range_str = f' in range [{start}, {end}]'
        else:
            count = r.bitcount(key)
            range_str = ''

        return f'Number of set bits{range_str}: {count}'
    except ValkeyError as e:
        return f"Error counting bits in '{key}': {str(e)}"


@mcp.tool()
async def bitmap_pos(
    key: str,
    bit: int,
    start: Optional[int] = None,
    end: Optional[int] = None,
    count: Optional[int] = None,
) -> str:
    """Find positions of bits set to a specific value.

    Args:
        key: The name of the bitmap key
        bit: Bit value to search for (0 or 1)
        start: Start offset (inclusive, optional)
        end: End offset (inclusive, optional)
        count: Maximum number of positions to return (optional)

    Returns:
        List of positions or error message
    """
    try:
        if bit not in (0, 1):
            return f'Error: bit must be 0 or 1, got {bit}'

        r = ValkeyConnectionManager.get_connection()
        args = []
        if start is not None:
            if start < 0:
                return 'Error: start must be non-negative'
            args.extend(['START', start])
        if end is not None:
            if end < 0:
                return 'Error: end must be non-negative'
            if start is not None and start > end:
                return 'Error: start must be less than or equal to end'
            args.extend(['END', end])
        if count is not None:
            if count < 1:
                return 'Error: count must be positive'
            args.extend(['COUNT', count])

        pos = r.bitpos(key, bit, *args) if args else r.bitpos(key, bit)

        if pos == -1 or pos is None:
            range_str = ''
            if start is not None or end is not None:
                range_str = f' in range [{start or 0}, {end or "∞"}]'
            return f'No bits set to {bit} found{range_str}'

        return f'First bit set to {bit} found at position: {pos}'
    except ValkeyError as e:
        return f"Error finding bit position in '{key}': {str(e)}"
