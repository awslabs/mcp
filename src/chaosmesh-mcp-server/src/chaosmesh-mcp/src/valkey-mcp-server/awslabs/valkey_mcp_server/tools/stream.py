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

"""Stream operations for Valkey MCP Server."""

from awslabs.valkey_mcp_server.common.connection import ValkeyConnectionManager
from awslabs.valkey_mcp_server.common.server import mcp
from awslabs.valkey_mcp_server.context import Context
from typing import Any, Dict, Optional
from valkey.exceptions import ValkeyError


@mcp.tool()
async def stream_add(
    key: str,
    field_dict: Dict[str, Any],
    id: str = '*',
    maxlen: Optional[int] = None,
    approximate: bool = True,
) -> str:
    """Add entry to stream.

    Args:
        key: The name of the key
        field_dict: Dictionary of field-value pairs
        id: Entry ID (default "*" for auto-generation)
        maxlen: Maximum length of stream (optional)
        approximate: Whether maxlen is approximate

    Returns:
        Success message or error message
    """
    # Check if readonly mode is enabled
    if Context.readonly_mode():
        return 'Error: Cannot add to stream in readonly mode'

    try:
        r = ValkeyConnectionManager.get_connection()
        options = {}
        if maxlen is not None:
            if approximate:
                options['maxlen'] = '~' + str(maxlen)
            else:
                options['maxlen'] = maxlen

        result = r.xadd(key, field_dict, id=id, **options)
        return f"Successfully added entry with ID '{result}' to stream '{key}'"
    except ValkeyError as e:
        return f"Error adding to stream '{key}': {str(e)}"


@mcp.tool()
async def stream_delete(key: str, id: str) -> str:
    """Delete entries from stream.

    Args:
        key: The name of the key
        id: Entry ID to delete

    Returns:
        Success message or error message
    """
    # Check if readonly mode is enabled
    if Context.readonly_mode():
        return 'Error: Cannot delete from stream in readonly mode'

    try:
        r = ValkeyConnectionManager.get_connection()
        result = r.xdel(key, id)
        return f"Successfully deleted {result} entries from stream '{key}'"
    except ValkeyError as e:
        return f"Error deleting from stream '{key}': {str(e)}"


@mcp.tool()
async def stream_trim(key: str, maxlen: int, approximate: bool = True) -> str:
    """Trim stream to specified length.

    Args:
        key: The name of the key
        maxlen: Maximum length to trim to
        approximate: Whether maxlen is approximate

    Returns:
        Success message or error message
    """
    # Check if readonly mode is enabled
    if Context.readonly_mode():
        return 'Error: Cannot trim stream in readonly mode'

    try:
        r = ValkeyConnectionManager.get_connection()
        result = r.xtrim(key, maxlen=maxlen, approximate=approximate)
        return f"Successfully trimmed stream '{key}', removed {result} entries"
    except ValkeyError as e:
        return f"Error trimming stream '{key}': {str(e)}"


@mcp.tool()
async def stream_length(key: str) -> str:
    """Get length of stream.

    Args:
        key: The name of the key

    Returns:
        Length or error message
    """
    try:
        r = ValkeyConnectionManager.get_connection()
        result = r.xlen(key)
        return str(result)
    except ValkeyError as e:
        return f"Error getting stream length for '{key}': {str(e)}"


@mcp.tool()
async def stream_range(
    key: str, start: str = '-', end: str = '+', count: Optional[int] = None, reverse: bool = False
) -> str:
    """Get range of entries from stream.

    Args:
        key: The name of the key
        start: Start ID (default "-" for beginning)
        end: End ID (default "+" for end)
        count: Maximum number of entries to return
        reverse: Return entries in reverse order

    Returns:
        List of entries or error message
    """
    try:
        r = ValkeyConnectionManager.get_connection()
        result = (
            r.xrevrange(key, end, start, count=count)
            if reverse
            else r.xrange(key, start, end, count=count)
        )
        if not result:
            return f"No entries found in range for stream '{key}'"
        return str(result)
    except ValkeyError as e:
        return f"Error getting range from stream '{key}': {str(e)}"


@mcp.tool()
async def stream_read(
    key: str, count: Optional[int] = None, block: Optional[int] = None, last_id: str = '$'
) -> str:
    """Read entries from stream.

    Args:
        key: The name of the key
        count: Maximum number of entries to return
        block: Milliseconds to block (optional)
        last_id: Last ID received (default "$" for new entries only)

    Returns:
        List of entries or error message
    """
    try:
        r = ValkeyConnectionManager.get_connection()
        streams = {key: last_id}
        result = r.xread(streams, count=count, block=block)
        if not result:
            return f"No new entries in stream '{key}'"
        return str(result)
    except ValkeyError as e:
        return f"Error reading from stream '{key}': {str(e)}"


@mcp.tool()
async def stream_group_create(
    key: str, group_name: str, id: str = '$', mkstream: bool = False
) -> str:
    """Create consumer group.

    Args:
        key: The name of the key
        group_name: Name of consumer group
        id: ID to start reading from (default "$" for new entries only)
        mkstream: Create stream if it doesn't exist

    Returns:
        Success message or error message
    """
    # Check if readonly mode is enabled
    if Context.readonly_mode():
        return 'Error: Cannot create consumer group in readonly mode'

    try:
        r = ValkeyConnectionManager.get_connection()
        r.xgroup_create(key, group_name, id=id, mkstream=mkstream)
        return f"Successfully created consumer group '{group_name}' for stream '{key}'"
    except ValkeyError as e:
        return f'Error creating consumer group: {str(e)}'


@mcp.tool()
async def stream_group_destroy(key: str, group_name: str) -> str:
    """Destroy consumer group.

    Args:
        key: The name of the key
        group_name: Name of consumer group

    Returns:
        Success message or error message
    """
    # Check if readonly mode is enabled
    if Context.readonly_mode():
        return 'Error: Cannot destroy consumer group in readonly mode'

    try:
        r = ValkeyConnectionManager.get_connection()
        result = r.xgroup_destroy(key, group_name)
        if result:
            return f"Successfully destroyed consumer group '{group_name}' from stream '{key}'"
        return f"Consumer group '{group_name}' not found in stream '{key}'"
    except ValkeyError as e:
        return f'Error destroying consumer group: {str(e)}'


@mcp.tool()
async def stream_group_set_id(key: str, group_name: str, id: str) -> str:
    """Set consumer group's last delivered ID.

    Args:
        key: The name of the key
        group_name: Name of consumer group
        id: ID to set as last delivered

    Returns:
        Success message or error message
    """
    # Check if readonly mode is enabled
    if Context.readonly_mode():
        return 'Error: Cannot set consumer group ID in readonly mode'

    try:
        r = ValkeyConnectionManager.get_connection()
        r.xgroup_setid(key, group_name, id)
        return f"Successfully set last delivered ID for group '{group_name}' in stream '{key}'"
    except ValkeyError as e:
        return f'Error setting group ID: {str(e)}'


@mcp.tool()
async def stream_group_delete_consumer(key: str, group_name: str, consumer_name: str) -> str:
    """Delete consumer from group.

    Args:
        key: The name of the key
        group_name: Name of consumer group
        consumer_name: Name of consumer to delete

    Returns:
        Success message or error message
    """
    # Check if readonly mode is enabled
    if Context.readonly_mode():
        return 'Error: Cannot delete consumer in readonly mode'

    try:
        r = ValkeyConnectionManager.get_connection()
        result = r.xgroup_delconsumer(key, group_name, consumer_name)
        return f"Successfully deleted consumer '{consumer_name}' from group '{group_name}', {result} pending entries"
    except ValkeyError as e:
        return f'Error deleting consumer: {str(e)}'


@mcp.tool()
async def stream_read_group(
    key: str,
    group_name: str,
    consumer_name: str,
    count: Optional[int] = None,
    block: Optional[int] = None,
    noack: bool = False,
) -> str:
    """Read entries from stream as part of consumer group.

    Args:
        key: The name of the key
        group_name: Name of consumer group
        consumer_name: Name of this consumer
        count: Maximum number of entries to return
        block: Milliseconds to block (optional)
        noack: Don't require acknowledgment

    Returns:
        List of entries or error message
    """
    # Check if readonly mode is enabled and acknowledgment is required
    if Context.readonly_mode() and not noack:
        return 'Error: Cannot read from stream with acknowledgment in readonly mode'

    try:
        r = ValkeyConnectionManager.get_connection()
        streams = {key: '>'}  # ">" means read undelivered entries
        result = r.xreadgroup(
            group_name, consumer_name, streams, count=count, block=block, noack=noack
        )
        if not result:
            return f"No new entries for consumer '{consumer_name}' in group '{group_name}'"
        return str(result)
    except ValkeyError as e:
        return f'Error reading from group: {str(e)}'


@mcp.tool()
async def stream_info(key: str) -> str:
    """Get information about stream.

    Args:
        key: The name of the key

    Returns:
        Stream information or error message
    """
    try:
        r = ValkeyConnectionManager.get_connection()
        result = r.xinfo_stream(key)
        return str(result)
    except ValkeyError as e:
        return f"Error getting stream info for '{key}': {str(e)}"


@mcp.tool()
async def stream_info_groups(key: str) -> str:
    """Get information about consumer groups.

    Args:
        key: The name of the key

    Returns:
        Consumer groups information or error message
    """
    try:
        r = ValkeyConnectionManager.get_connection()
        result = r.xinfo_groups(key)
        if not result:
            return f"No consumer groups found for stream '{key}'"
        return str(result)
    except ValkeyError as e:
        return f"Error getting consumer groups info for '{key}': {str(e)}"


@mcp.tool()
async def stream_info_consumers(key: str, group_name: str) -> str:
    """Get information about consumers in group.

    Args:
        key: The name of the key
        group_name: Name of consumer group

    Returns:
        Consumers information or error message
    """
    try:
        r = ValkeyConnectionManager.get_connection()
        result = r.xinfo_consumers(key, group_name)
        if not result:
            return f"No consumers found in group '{group_name}'"
        return str(result)
    except ValkeyError as e:
        return f'Error getting consumers info: {str(e)}'
