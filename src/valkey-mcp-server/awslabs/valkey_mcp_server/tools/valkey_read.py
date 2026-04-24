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

"""Read-only Valkey command runner (safe tier)."""

from __future__ import annotations

import logging
from awslabs.valkey_mcp_server.common.connection import get_client
from awslabs.valkey_mcp_server.common.server import mcp
from awslabs.valkey_mcp_server.common.utils import decode_value as _decode
from awslabs.valkey_mcp_server.common.utils import tool_errors
from typing import Any


logger = logging.getLogger(__name__)

READ_COMMANDS = frozenset(
    {
        'DBSIZE',
        'DUMP',
        'EXISTS',
        'EXPIRETIME',
        'GET',
        'GETRANGE',
        'HEXISTS',
        'HGET',
        'HGETALL',
        'HKEYS',
        'HLEN',
        'HMGET',
        'HRANDFIELD',
        'HSCAN',
        'HVALS',
        'INFO',
        'KEYS',
        'LINDEX',
        'LLEN',
        'LPOS',
        'LRANGE',
        'MGET',
        'OBJECT',
        'PEXPIRETIME',
        'PTTL',
        'RANDOMKEY',
        'SCAN',
        'SCARD',
        'SISMEMBER',
        'SMEMBERS',
        'SMISMEMBER',
        'SORT_RO',
        'SRANDMEMBER',
        'SSCAN',
        'STRLEN',
        'SUBSTR',
        'TTL',
        'TYPE',
        'XINFO',
        'XLEN',
        'XRANGE',
        'XREVRANGE',
        'ZCARD',
        'ZCOUNT',
        'ZLEXCOUNT',
        'ZMSCORE',
        'ZRANDMEMBER',
        'ZRANGE',
        'ZRANGEBYLEX',
        'ZRANGEBYSCORE',
        'ZRANK',
        'ZREVRANGE',
        'ZREVRANGEBYLEX',
        'ZREVRANGEBYSCORE',
        'ZREVRANK',
        'ZSCAN',
        'ZSCORE',
        'FT.INFO',
        'FT.SEARCH',
        'FT.AGGREGATE',
        'FT.EXPLAIN',
        'FT._LIST',
        'FT.PROFILE',
        'FT.TAGVALS',
        'JSON.GET',
        'JSON.MGET',
        'JSON.OBJKEYS',
        'JSON.OBJLEN',
        'JSON.ARRLEN',
        'JSON.ARRINDEX',
        'JSON.STRLEN',
        'JSON.TYPE',
        'MEMORY USAGE',
    }
)


@mcp.tool()
@tool_errors
async def valkey_read(
    command: str,
    args: list[str] | None = None,
) -> dict[str, Any]:
    """Execute a read-only Valkey command.

    Safe tier — always available, even in readonly mode. Only allowlisted
    read-only commands are accepted.

    Args:
        command: Valkey command name (e.g., "GET", "HGETALL", "SCAN", "INFO")
        args: Command arguments as strings

    Returns:
        Dict with "status" and "result".

    Examples:
        valkey_read(command="GET", args=["mykey"])
        valkey_read(command="HGETALL", args=["user:123"])
        valkey_read(command="SCAN", args=["0", "MATCH", "user:*", "COUNT", "100"])
        valkey_read(command="INFO", args=["memory"])
    """
    cmd = command.upper()
    if cmd not in READ_COMMANDS:
        return {
            'status': 'error',
            'reason': f"Command '{cmd}' is not in the read allowlist. "
            f'Use valkey_write for mutations or valkey_admin for destructive commands.',
        }

    client = await get_client()
    full_cmd: list = [cmd] + (args or [])
    raw = await client.custom_command(full_cmd)
    return {'status': 'success', 'result': _decode(raw)}
