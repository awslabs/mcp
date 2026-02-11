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

"""Error handling utilities for MCP tools."""

from loguru import logger
from mcp.server.fastmcp import Context
from typing import Any, Dict


async def handle_tool_error(ctx: Context, error: Exception, operation: str) -> Dict[str, Any]:
    """Handle tool errors by logging and returning error information to the agent.

    This ensures errors are communicated to the agent rather than being swallowed
    by raised exceptions that may not surface properly through the MCP framework.

    Args:
        ctx: MCP context for error reporting
        error: The exception that occurred
        operation: Description of the operation that failed

    Returns:
        Dictionary with 'error' key containing the error message
    """
    error_message = f'{operation}: {str(error)}'
    logger.error(error_message)
    await ctx.error(error_message)
    return {'error': error_message}
