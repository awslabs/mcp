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

from awslabs.valkey_mcp_server.common.connection import ValkeyConnectionManager
from awslabs.valkey_mcp_server.common.server import mcp
from valkey.exceptions import ValkeyError


@mcp.tool()
async def dbsize() -> str:
    """Get the number of keys stored in the Valkey database."""
    try:
        r = ValkeyConnectionManager.get_connection()
        result = r.dbsize()
        return str(result)
    except ValkeyError as e:
        raise RuntimeError(f'Error getting database size: {str(e)}')


@mcp.tool()
async def info(section: str = 'default') -> str:
    """Get Valkey server information and statistics.

    Args:
        section: The section of the info command (default, memory, cpu, etc.).

    Returns:
        A dictionary of server information or an error message.
    """
    try:
        r = ValkeyConnectionManager.get_connection()
        info = r.info(section)
        return str(info)
    except ValkeyError as e:
        raise RuntimeError(f'Error retrieving Redis info: {str(e)}')


@mcp.tool()
async def client_list() -> str:
    """Get a list of connected clients to the Valkey server."""
    try:
        r = ValkeyConnectionManager.get_connection()
        clients = r.client_list()
        return str(clients)
    except ValkeyError as e:
        raise RuntimeError(f'Error retrieving client list: {str(e)}')
