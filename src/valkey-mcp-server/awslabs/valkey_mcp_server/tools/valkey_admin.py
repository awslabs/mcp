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

"""Destructive Valkey command runner (admin tier, opt-in)."""

from __future__ import annotations

import logging
import os
from awslabs.valkey_mcp_server.common.connection import get_client
from awslabs.valkey_mcp_server.common.server import mcp
from awslabs.valkey_mcp_server.common.utils import decode_value as _decode
from awslabs.valkey_mcp_server.common.utils import readonly_guard, tool_errors
from typing import Any


logger = logging.getLogger(__name__)

ADMIN_COMMANDS = frozenset(
    {
        'BGSAVE',
        'BGREWRITEAOF',
        'SAVE',
        'CLIENT KILL',
        'CLIENT NO-EVICT',
        'CLIENT SETNAME',
        'CLUSTER FAILOVER',
        'CLUSTER RESET',
        'CONFIG RESETSTAT',
        'CONFIG SET',
        'DEBUG',
        'EVAL',
        'EVALSHA',
        'FLUSHALL',
        'FLUSHDB',
        'MIGRATE',
        'MODULE',
        'SCRIPT FLUSH',
        'SCRIPT LOAD',
        'SHUTDOWN',
        'SWAPDB',
    }
)


def _is_admin_enabled() -> bool:
    """Check if admin mode is enabled via environment variable."""
    return os.environ.get('VALKEY_ADMIN_ENABLED', '').lower() in ('true', '1', 't')


@mcp.tool()
@readonly_guard
@tool_errors
async def valkey_admin(
    command: str,
    args: list[str] | None = None,
    confirm: bool = False,
) -> dict[str, Any]:
    """Execute a destructive Valkey command.

    Admin tier — disabled by default. Requires both:
    1. Server config: VALKEY_ADMIN_ENABLED=true
    2. confirm=True parameter on each call

    Never enable on staging or production clusters.

    Args:
        command: Valkey command (e.g., "FLUSHALL", "CONFIG SET", "EVAL")
        args: Command arguments as strings
        confirm: Must be True to execute. Double safety gate.

    Returns:
        Dict with "status" and "result".

    Examples:
        valkey_admin(command="FLUSHALL", confirm=True)
        valkey_admin(command="CONFIG SET", args=["maxmemory", "2gb"], confirm=True)
    """
    if not _is_admin_enabled():
        return {
            'status': 'error',
            'reason': 'Admin mode is disabled. Set VALKEY_ADMIN_ENABLED=true to enable.',
        }

    if not confirm:
        return {
            'status': 'error',
            'reason': 'Destructive command requires confirm=True.',
        }

    # Build the full command key for multi-word commands (e.g., "CONFIG SET")
    cmd = command.upper()
    cmd_parts = cmd.split()
    cmd_key = ' '.join(cmd_parts[:2]) if len(cmd_parts) >= 2 else cmd_parts[0]

    if cmd_key not in ADMIN_COMMANDS and cmd_parts[0] not in ADMIN_COMMANDS:
        return {
            'status': 'error',
            'reason': f"Command '{cmd}' is not in the admin allowlist. "
            f'Use valkey_read or valkey_write instead.',
        }

    client = await get_client()
    full_cmd: list = cmd_parts + (args or [])
    raw = await client.custom_command(full_cmd)
    logger.warning('Admin command executed: %s', cmd)
    return {'status': 'success', 'result': _decode(raw)}
