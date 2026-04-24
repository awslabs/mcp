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

"""Mutating Valkey command runner (write tier)."""

from __future__ import annotations

import logging
from awslabs.valkey_mcp_server.common.connection import get_client
from awslabs.valkey_mcp_server.common.server import mcp
from awslabs.valkey_mcp_server.common.utils import decode_value as _decode
from awslabs.valkey_mcp_server.common.utils import readonly_guard, tool_errors
from typing import Any


logger = logging.getLogger(__name__)

WRITE_COMMANDS = frozenset(
    {
        'APPEND',
        'COPY',
        'DECR',
        'DECRBY',
        'DEL',
        'EXPIRE',
        'EXPIREAT',
        'GETDEL',
        'GETSET',
        'HDEL',
        'HINCRBY',
        'HINCRBYFLOAT',
        'HMSET',
        'HSET',
        'HSETNX',
        'INCR',
        'INCRBY',
        'INCRBYFLOAT',
        'LINSERT',
        'LPOP',
        'LPUSH',
        'LPUSHX',
        'LREM',
        'LSET',
        'LTRIM',
        'MSET',
        'MSETNX',
        'PERSIST',
        'PEXPIRE',
        'PEXPIREAT',
        'PSETEX',
        'PUBLISH',
        'RENAME',
        'RENAMENX',
        'RPOP',
        'RPUSH',
        'RPUSHX',
        'SADD',
        'SET',
        'SETEX',
        'SETNX',
        'SETRANGE',
        'SMOVE',
        'SPOP',
        'SREM',
        'UNLINK',
        'XACK',
        'XADD',
        'XDEL',
        'XTRIM',
        'ZADD',
        'ZINCRBY',
        'ZPOPMAX',
        'ZPOPMIN',
        'ZREM',
        'ZREMRANGEBYLEX',
        'ZREMRANGEBYRANK',
        'ZREMRANGEBYSCORE',
        'FT.CREATE',
        'FT.DROPINDEX',
        'FT.ALTER',
        'FT.ALIASADD',
        'FT.ALIASDEL',
        'FT.ALIASUPDATE',
        'JSON.ARRAPPEND',
        'JSON.ARRPOP',
        'JSON.ARRTRIM',
        'JSON.CLEAR',
        'JSON.DEL',
        'JSON.NUMINCRBY',
        'JSON.NUMMULTBY',
        'JSON.SET',
        'JSON.STRAPPEND',
        'JSON.TOGGLE',
    }
)

BLOCKED_COMMANDS = frozenset(
    {
        'FLUSHALL',
        'FLUSHDB',
        'SHUTDOWN',
        'DEBUG',
        'CONFIG',
        'CLUSTER',
        'SLAVEOF',
        'REPLICAOF',
        'EVAL',
        'EVALSHA',
        'SCRIPT',
        'MODULE',
        'BGSAVE',
        'BGREWRITEAOF',
        'SAVE',
        'SWAPDB',
        'MIGRATE',
        'WAIT',
        'CLIENT',
    }
)


@mcp.tool()
@readonly_guard
@tool_errors
async def valkey_write(
    command: str,
    args: list[str] | None = None,
) -> dict[str, Any]:
    """Execute a mutating Valkey command.

    Write tier — allowlisted mutations only. Destructive commands
    (FLUSHALL, SHUTDOWN, etc.) are blocked. Disabled in readonly mode.

    Args:
        command: Valkey command name (e.g., "SET", "HSET", "DEL", "LPUSH")
        args: Command arguments as strings

    Returns:
        Dict with "status" and "result".

    Examples:
        valkey_write(command="SET", args=["mykey", "myvalue"])
        valkey_write(command="HSET", args=["user:123", "name", "Alice", "age", "30"])
        valkey_write(command="DEL", args=["tempkey"])
        valkey_write(command="EXPIRE", args=["mykey", "3600"])
    """
    cmd = command.upper()

    if cmd in BLOCKED_COMMANDS or cmd.split()[0] in BLOCKED_COMMANDS:
        return {
            'status': 'error',
            'reason': f"Command '{cmd}' is blocked. Use valkey_admin for destructive commands.",
        }

    if cmd not in WRITE_COMMANDS:
        return {
            'status': 'error',
            'reason': f"Command '{cmd}' is not in the write allowlist. "
            f'Use valkey_read for read-only commands.',
        }

    client = await get_client()
    full_cmd: list = [cmd] + (args or [])
    raw = await client.custom_command(full_cmd)
    return {'status': 'success', 'result': _decode(raw)}
