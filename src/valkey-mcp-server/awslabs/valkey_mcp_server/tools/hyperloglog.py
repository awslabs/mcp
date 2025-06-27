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

"""HyperLogLog operations for Valkey MCP Server."""

from awslabs.valkey_mcp_server.common.connection import ValkeyConnectionManager
from awslabs.valkey_mcp_server.common.server import mcp
from awslabs.valkey_mcp_server.context import Context
from valkey.exceptions import ValkeyError


@mcp.tool()
async def hll_add(key: str, element: str) -> str:
    """Add one element to a HyperLogLog.

    Args:
        key: The name of the HyperLogLog key
        element: One element to add

    Returns:
        Success message or error message
    """
    # Check if readonly mode is enabled
    if Context.readonly_mode():
        return 'Error: Cannot add to HyperLogLog in readonly mode'

    try:
        if not element:
            return 'Error: an element is required'

        r = ValkeyConnectionManager.get_connection()
        result = r.pfadd(key, element)
        if result:
            return f"Added 1 element to '{key}'"
        return f"No new element added to '{key}' (already existed)"
    except ValkeyError as e:
        return f"Error adding element to '{key}': {str(e)}"


@mcp.tool()
async def hll_count(key: str) -> str:
    """Get the estimated cardinality of a HyperLogLog.

    Args:
        key: The name of the HyperLogLog key

    Returns:
        Estimated cardinality or error message
    """
    try:
        r = ValkeyConnectionManager.get_connection()
        count = r.pfcount(key)
        return f"Estimated unique elements in '{key}': {count}"
    except ValkeyError as e:
        return f"Error getting count from '{key}': {str(e)}"
