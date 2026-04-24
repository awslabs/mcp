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

"""JSON Intelligence tools for Valkey (GLIDE)."""

from __future__ import annotations

import json as json_stdlib
import logging
from awslabs.valkey_mcp_server.common.connection import get_client
from awslabs.valkey_mcp_server.common.server import mcp
from awslabs.valkey_mcp_server.common.utils import decode_value, readonly_guard, tool_errors
from glide_shared.exceptions import RequestError
from typing import Any


logger = logging.getLogger(__name__)


def _parse_json_response(raw: Any) -> Any:
    """Decode bytes and parse JSON from a GLIDE response."""
    if raw is None:
        return None
    decoded = decode_value(raw) if isinstance(raw, bytes) else raw
    if isinstance(decoded, str):
        try:
            return json_stdlib.loads(decoded)
        except (json_stdlib.JSONDecodeError, TypeError):
            return decoded
    return decode_value(decoded)


def _unwrap_single(val: Any, path: str) -> Any:
    """Unwrap single-element arrays for non-wildcard JSONPath results."""
    if isinstance(val, list) and len(val) == 1 and '*' not in path:
        return val[0]
    return val


async def _get_json_type(client: Any, key: str, path: str) -> str | None:
    """Get the JSON type at a path. Returns None if key/path doesn't exist."""
    try:
        result = await client.custom_command(['JSON.TYPE', key, path])
        if result is None:
            return None
        if isinstance(result, list):
            val = result[0] if result else None
            return val.decode() if isinstance(val, bytes) else val
        return result.decode() if isinstance(result, bytes) else result
    except RequestError:
        return None


async def _require_array(client: Any, key: str, path: str) -> dict[str, Any] | None:
    """Validate key exists and path is an array. Returns error dict or None."""
    jtype = await _get_json_type(client, key, path)
    if jtype is None:
        return {
            'status': 'error',
            'reason': f"Key '{key}' does not exist or path '{path}' not found",
        }
    if jtype != 'array':
        return {'status': 'error', 'reason': f"Path '{path}' is type '{jtype}', not an array"}
    return None


@mcp.tool()
@tool_errors
async def json_get(
    key: str,
    path: str = '$',
) -> dict[str, Any]:
    """Get a JSON value at a path from a Valkey key.

    Args:
        key: Valkey key name
        path: JSONPath expression (default: "$" for root)

    Returns:
        Dict with "status" and "value". For non-wildcard paths, single values
        are unwrapped from the JSONPath array.
    """
    client = await get_client()
    result = await client.custom_command(['JSON.GET', key, path])
    if result is None:
        return {
            'status': 'error',
            'reason': f"Key '{key}' not found or path '{path}' does not exist",
        }
    parsed = _parse_json_response(result)
    unwrapped = _unwrap_single(parsed, path)
    logger.debug(
        'json_get: key=%r path=%r raw=%r parsed=%r unwrapped=%r',
        key,
        path,
        result,
        parsed,
        unwrapped,
    )
    return {'status': 'success', 'value': unwrapped}


@mcp.tool()
@readonly_guard
@tool_errors
async def json_set(
    key: str,
    value: str | int | float | bool | list | dict | None,
    path: str = '$',
    ttl: int | None = None,
) -> dict[str, Any]:
    """Set a JSON value at a path on a Valkey key.

    Args:
        key: Valkey key name
        value: Value to set (string, number, boolean, array, object, or null)
        path: JSONPath expression (default: "$" for root)
        ttl: Optional TTL in seconds

    Returns:
        Dict with "status".
    """
    client = await get_client()
    encoded = json_stdlib.dumps(value)
    logger.debug(
        'json_set: key=%r path=%r value=%r type=%s encoded=%r',
        key,
        path,
        value,
        type(value).__name__,
        encoded,
    )
    await client.custom_command(['JSON.SET', key, path, encoded])
    if ttl is not None:
        await client.expire(key, ttl)
    return {'status': 'success'}


@mcp.tool()
@readonly_guard
@tool_errors
async def json_arrappend(
    key: str,
    values: list[Any],
    path: str = '$',
) -> dict[str, Any]:
    """Append values to a JSON array at a path.

    Args:
        key: Valkey key name
        values: Values to append to the array
        path: JSONPath expression pointing to an array (default: "$")

    Returns:
        Dict with "status" and "new_length".
    """
    client = await get_client()
    if err := await _require_array(client, key, path):
        return err
    cmd: list = ['JSON.ARRAPPEND', key, path] + [json_stdlib.dumps(v) for v in values]
    result = await client.custom_command(cmd)
    parsed = result if isinstance(result, list) else [result]
    length = _unwrap_single(parsed, path)
    return {'status': 'success', 'new_length': length}


@mcp.tool()
@readonly_guard
@tool_errors
async def json_arrpop(
    key: str,
    path: str = '$',
    index: int = -1,
) -> dict[str, Any]:
    """Pop an element from a JSON array at a path.

    Args:
        key: Valkey key name
        path: JSONPath expression pointing to an array (default: "$")
        index: Array index to pop (default: -1 for last element)

    Returns:
        Dict with "status" and "popped" value.
    """
    client = await get_client()
    if err := await _require_array(client, key, path):
        return err
    result = await client.custom_command(['JSON.ARRPOP', key, path, str(index)])
    if isinstance(result, list):
        popped = [_parse_json_response(v) for v in result]
        return {'status': 'success', 'popped': _unwrap_single(popped, path)}
    parsed = _parse_json_response(result)
    return {'status': 'success', 'popped': parsed}


@mcp.tool()
@readonly_guard
@tool_errors
async def json_arrtrim(
    key: str,
    start: int,
    stop: int,
    path: str = '$',
) -> dict[str, Any]:
    """Trim a JSON array to a specified range.

    Args:
        key: Valkey key name
        start: Start index (inclusive)
        stop: Stop index (inclusive)
        path: JSONPath expression pointing to an array (default: "$")

    Returns:
        Dict with "status" and "new_length".
    """
    client = await get_client()
    if err := await _require_array(client, key, path):
        return err
    result = await client.custom_command(['JSON.ARRTRIM', key, path, str(start), str(stop)])
    parsed = result if isinstance(result, list) else [result]
    length = _unwrap_single(parsed, path)
    return {'status': 'success', 'new_length': length}
