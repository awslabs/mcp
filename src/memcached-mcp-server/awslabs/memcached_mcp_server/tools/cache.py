"""Cache operations for Memcached MCP Server."""

from awslabs.memcached_mcp_server.common.connection import MemcachedConnectionManager
from awslabs.memcached_mcp_server.common.server import mcp
from pymemcache.exceptions import MemcacheError
from typing import Any, Dict, List, Optional


@mcp.tool()
async def cache_get(key: str) -> str:
    """Get a value from the cache.

    Args:
        key: The key to retrieve

    Returns:
        Value or error message
    """
    try:
        client = MemcachedConnectionManager.get_connection()
        result = client.get(key)
        if result is None:
            return f"Key '{key}' not found"
        return str(result)
    except MemcacheError as e:
        return f"Error getting key '{key}': {str(e)}"


@mcp.tool()
async def cache_gets(key: str) -> str:
    """Get a value and its CAS token from the cache.

    Args:
        key: The key to retrieve

    Returns:
        Value and CAS token or error message
    """
    try:
        client = MemcachedConnectionManager.get_connection()
        result = client.gets(key)
        if result is None:
            return f"Key '{key}' not found"
        value, cas = result
        return f'Value: {value}, CAS: {cas}'
    except MemcacheError as e:
        return f"Error getting key '{key}' with CAS: {str(e)}"


@mcp.tool()
async def cache_get_many(keys: List[str]) -> str:
    """Get multiple values from the cache.

    Args:
        keys: List of keys to retrieve

    Returns:
        Dictionary of key-value pairs or error message
    """
    try:
        client = MemcachedConnectionManager.get_connection()
        result = client.get_many(keys)
        if not result:
            return 'No keys found'
        return str(result)
    except MemcacheError as e:
        return f'Error getting multiple keys: {str(e)}'


@mcp.tool()
async def cache_get_multi(keys: List[str]) -> str:
    """Get multiple values from the cache (alias for get_many).

    Args:
        keys: List of keys to retrieve

    Returns:
        Dictionary of key-value pairs or error message
    """
    return await cache_get_many(keys)


@mcp.tool()
async def cache_set(key: str, value: Any, expire: Optional[int] = None) -> str:
    """Set a value in the cache.

    Args:
        key: The key to set
        value: The value to store
        expire: Optional expiration time in seconds

    Returns:
        Success message or error message
    """
    try:
        client = MemcachedConnectionManager.get_connection()
        client.set(key, value, expire=expire)
        expiry_msg = f' with {expire}s expiry' if expire else ''
        return f"Successfully set key '{key}'{expiry_msg}"
    except MemcacheError as e:
        return f"Error setting key '{key}': {str(e)}"


@mcp.tool()
async def cache_cas(key: str, value: Any, cas: int, expire: Optional[int] = None) -> str:
    """Set a value using CAS (Check And Set).

    Args:
        key: The key to set
        value: The value to store
        cas: CAS token from gets()
        expire: Optional expiration time in seconds

    Returns:
        Success message or error message
    """
    try:
        client = MemcachedConnectionManager.get_connection()
        if client.cas(key, value, cas, expire=expire):
            expiry_msg = f' with {expire}s expiry' if expire else ''
            return f"Successfully set key '{key}' using CAS{expiry_msg}"
        return f"CAS operation failed for key '{key}' (value changed)"
    except MemcacheError as e:
        return f"Error setting key '{key}' with CAS: {str(e)}"


@mcp.tool()
async def cache_set_many(mapping: Dict[str, Any], expire: Optional[int] = None) -> str:
    """Set multiple values in the cache.

    Args:
        mapping: Dictionary of key-value pairs
        expire: Optional expiration time in seconds

    Returns:
        Success message or error message
    """
    try:
        client = MemcachedConnectionManager.get_connection()
        failed = client.set_many(mapping, expire=expire)
        if not failed:
            expiry_msg = f' with {expire}s expiry' if expire else ''
            return f'Successfully set {len(mapping)} keys{expiry_msg}'
        return f'Failed to set keys: {failed}'
    except MemcacheError as e:
        return f'Error setting multiple keys: {str(e)}'


@mcp.tool()
async def cache_set_multi(mapping: Dict[str, Any], expire: Optional[int] = None) -> str:
    """Set multiple values in the cache (alias for set_many).

    Args:
        mapping: Dictionary of key-value pairs
        expire: Optional expiration time in seconds

    Returns:
        Success message or error message
    """
    return await cache_set_many(mapping, expire)


@mcp.tool()
async def cache_add(key: str, value: Any, expire: Optional[int] = None) -> str:
    """Add a value to the cache only if the key doesn't exist.

    Args:
        key: The key to add
        value: The value to store
        expire: Optional expiration time in seconds

    Returns:
        Success message or error message
    """
    try:
        client = MemcachedConnectionManager.get_connection()
        if client.add(key, value, expire=expire):
            expiry_msg = f' with {expire}s expiry' if expire else ''
            return f"Successfully added key '{key}'{expiry_msg}"
        return f"Key '{key}' already exists"
    except MemcacheError as e:
        return f"Error adding key '{key}': {str(e)}"


@mcp.tool()
async def cache_replace(key: str, value: Any, expire: Optional[int] = None) -> str:
    """Replace a value in the cache only if the key exists.

    Args:
        key: The key to replace
        value: The new value
        expire: Optional expiration time in seconds

    Returns:
        Success message or error message
    """
    try:
        client = MemcachedConnectionManager.get_connection()
        if client.replace(key, value, expire=expire):
            expiry_msg = f' with {expire}s expiry' if expire else ''
            return f"Successfully replaced key '{key}'{expiry_msg}"
        return f"Key '{key}' not found"
    except MemcacheError as e:
        return f"Error replacing key '{key}': {str(e)}"


@mcp.tool()
async def cache_append(key: str, value: str) -> str:
    """Append a string to an existing value.

    Args:
        key: The key to append to
        value: String to append

    Returns:
        Success message or error message
    """
    try:
        client = MemcachedConnectionManager.get_connection()
        if client.append(key, value):
            return f"Successfully appended to key '{key}'"
        return f"Key '{key}' not found or not a string"
    except MemcacheError as e:
        return f"Error appending to key '{key}': {str(e)}"


@mcp.tool()
async def cache_prepend(key: str, value: str) -> str:
    """Prepend a string to an existing value.

    Args:
        key: The key to prepend to
        value: String to prepend

    Returns:
        Success message or error message
    """
    try:
        client = MemcachedConnectionManager.get_connection()
        if client.prepend(key, value):
            return f"Successfully prepended to key '{key}'"
        return f"Key '{key}' not found or not a string"
    except MemcacheError as e:
        return f"Error prepending to key '{key}': {str(e)}"


@mcp.tool()
async def cache_delete(key: str) -> str:
    """Delete a value from the cache.

    Args:
        key: The key to delete

    Returns:
        Success message or error message
    """
    try:
        client = MemcachedConnectionManager.get_connection()
        if client.delete(key):
            return f"Successfully deleted key '{key}'"
        return f"Key '{key}' not found"
    except MemcacheError as e:
        return f"Error deleting key '{key}': {str(e)}"


@mcp.tool()
async def cache_delete_many(keys: List[str]) -> str:
    """Delete multiple values from the cache.

    Args:
        keys: List of keys to delete

    Returns:
        Success message or error message
    """
    try:
        client = MemcachedConnectionManager.get_connection()
        failed = client.delete_many(keys)
        if not failed:
            return f'Successfully deleted {len(keys)} keys'
        return f'Failed to delete keys: {failed}'
    except MemcacheError as e:
        return f'Error deleting multiple keys: {str(e)}'


@mcp.tool()
async def cache_delete_multi(keys: List[str]) -> str:
    """Delete multiple values from the cache (alias for delete_many).

    Args:
        keys: List of keys to delete

    Returns:
        Success message or error message
    """
    return await cache_delete_many(keys)


@mcp.tool()
async def cache_incr(key: str, value: int = 1) -> str:
    """Increment a counter in the cache.

    Args:
        key: The key to increment
        value: Amount to increment by (default 1)

    Returns:
        New value or error message
    """
    try:
        client = MemcachedConnectionManager.get_connection()
        result = client.incr(key, value)
        if result is None:
            return f"Key '{key}' not found or not a counter"
        return str(result)
    except MemcacheError as e:
        return f"Error incrementing key '{key}': {str(e)}"


@mcp.tool()
async def cache_decr(key: str, value: int = 1) -> str:
    """Decrement a counter in the cache.

    Args:
        key: The key to decrement
        value: Amount to decrement by (default 1)

    Returns:
        New value or error message
    """
    try:
        client = MemcachedConnectionManager.get_connection()
        result = client.decr(key, value)
        if result is None:
            return f"Key '{key}' not found or not a counter"
        return str(result)
    except MemcacheError as e:
        return f"Error decrementing key '{key}': {str(e)}"


@mcp.tool()
async def cache_touch(key: str, expire: int) -> str:
    """Update the expiration time for a key.

    Args:
        key: The key to update
        expire: New expiration time in seconds

    Returns:
        Success message or error message
    """
    try:
        client = MemcachedConnectionManager.get_connection()
        if client.touch(key, expire):
            return f"Successfully updated expiry for key '{key}' to {expire}s"
        return f"Key '{key}' not found"
    except MemcacheError as e:
        return f"Error touching key '{key}': {str(e)}"


@mcp.tool()
async def cache_stats(args: Optional[List[str]] = None) -> str:
    """Get cache statistics.

    Args:
        args: Optional list of stats to retrieve

    Returns:
        Statistics or error message
    """
    try:
        client = MemcachedConnectionManager.get_connection()
        result = client.stats(*args if args else [])
        return str(result)
    except MemcacheError as e:
        return f'Error getting stats: {str(e)}'


@mcp.tool()
async def cache_flush_all(delay: int = 0) -> str:
    """Flush all cache entries.

    Args:
        delay: Optional delay in seconds before flushing

    Returns:
        Success message or error message
    """
    try:
        client = MemcachedConnectionManager.get_connection()
        client.flush_all(delay=delay)
        delay_msg = f' with {delay}s delay' if delay else ''
        return f'Successfully flushed all cache entries{delay_msg}'
    except MemcacheError as e:
        return f'Error flushing cache: {str(e)}'


@mcp.tool()
async def cache_quit() -> str:
    """Close the connection to the cache server.

    Returns:
        Success message or error message
    """
    try:
        client = MemcachedConnectionManager.get_connection()
        client.quit()
        MemcachedConnectionManager.close_connection()
        return 'Successfully closed connection'
    except MemcacheError as e:
        return f'Error closing connection: {str(e)}'


@mcp.tool()
async def cache_version() -> str:
    """Get the version of the cache server.

    Returns:
        Version string or error message
    """
    try:
        client = MemcachedConnectionManager.get_connection()
        result = client.version()
        return str(result)
    except MemcacheError as e:
        return f'Error getting version: {str(e)}'
