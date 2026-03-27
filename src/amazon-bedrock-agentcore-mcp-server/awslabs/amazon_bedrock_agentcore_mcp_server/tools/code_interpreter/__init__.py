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

"""Code Interpreter tools sub-package for the unified AgentCore MCP server.

Provides 9 code interpreter tools via Amazon Bedrock AgentCore:
- Session lifecycle: start, stop, get, list
- Code execution: execute_code, execute_command, install_packages
- File operations: upload_file, download_file
"""

import os
from . import execution, files, session
from .client import clear_clients, stop_all_sessions
from loguru import logger


async def cleanup_code_interpreter() -> None:
    """Shutdown cleanup — stop sessions if configured, then clear client cache."""
    auto_stop = os.environ.get('AUTO_STOP_SESSIONS', 'false').lower() == 'true'
    if auto_stop:
        logger.info('AUTO_STOP_SESSIONS enabled, stopping all active sessions')
        await stop_all_sessions()
    else:
        clear_clients()


def register_code_interpreter_tools(mcp):
    """Register all 9 code interpreter tools with the MCP server."""
    # Session lifecycle tools
    mcp.tool()(session.start_code_interpreter_session)
    mcp.tool()(session.stop_code_interpreter_session)
    mcp.tool()(session.get_code_interpreter_session)
    mcp.tool()(session.list_code_interpreter_sessions)

    # Code execution tools
    mcp.tool()(execution.execute_code)
    mcp.tool()(execution.execute_command)
    mcp.tool()(execution.install_packages)

    # File operation tools
    mcp.tool()(files.upload_file)
    mcp.tool()(files.download_file)

    logger.info('All code interpreter tool groups registered successfully')
