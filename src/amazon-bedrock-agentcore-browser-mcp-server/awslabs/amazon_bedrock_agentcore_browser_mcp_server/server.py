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

"""Bedrock AgentCore Browser MCP Server.

Provides browser automation tools via Amazon Bedrock AgentCore.
Wraps AgentCore Browser APIs to start cloud browser sessions and
interact with web pages using the accessibility-tree paradigm.
"""

import asyncio
import signal
from awslabs.amazon_bedrock_agentcore_browser_mcp_server.browser.connection_manager import (
    BrowserConnectionManager,
)
from awslabs.amazon_bedrock_agentcore_browser_mcp_server.browser.snapshot_manager import (
    SnapshotManager,
)
from awslabs.amazon_bedrock_agentcore_browser_mcp_server.tools.interaction import InteractionTools
from awslabs.amazon_bedrock_agentcore_browser_mcp_server.tools.management import ManagementTools
from awslabs.amazon_bedrock_agentcore_browser_mcp_server.tools.navigation import NavigationTools
from awslabs.amazon_bedrock_agentcore_browser_mcp_server.tools.observation import ObservationTools
from awslabs.amazon_bedrock_agentcore_browser_mcp_server.tools.session import BrowserSessionTools
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from loguru import logger
from mcp.server.fastmcp import FastMCP


# Shared managers for Playwright connections and accessibility snapshots
connection_manager = BrowserConnectionManager()
snapshot_manager = SnapshotManager()


@asynccontextmanager
async def server_lifespan(server: FastMCP) -> AsyncIterator[None]:
    """Manage server lifecycle — cleanup Playwright on shutdown."""
    logger.info('Bedrock AgentCore Browser MCP server initializing')

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(
            sig, lambda s=sig: asyncio.ensure_future(connection_manager.cleanup())
        )

    try:
        yield
    finally:
        logger.info('Bedrock AgentCore Browser MCP server shutting down')
        await connection_manager.cleanup()


mcp = FastMCP(
    'awslabs.amazon-bedrock-agentcore-browser-mcp-server',
    instructions=(
        'Use this MCP server to start and control cloud browser sessions via '
        'Amazon Bedrock AgentCore. Start a browser session with start_browser_session, '
        'then use browser interaction tools (browser_navigate, browser_snapshot, '
        'browser_click, browser_type, etc.) to interact with web pages. '
        'Each session runs in an isolated cloud environment — no local browser '
        'installation is required. Call stop_browser_session when done.\n\n'
        'Tips:\n'
        '- Use DuckDuckGo or Bing instead of Google — Google blocks cloud browser '
        'IPs with CAPTCHAs.\n'
        '- For content-heavy pages, use browser_evaluate with JavaScript to extract '
        'specific data instead of relying solely on the accessibility snapshot, '
        'which can be very large.'
    ),
    dependencies=[
        'pydantic',
        'loguru',
        'bedrock-agentcore',
        'playwright',
    ],
    lifespan=server_lifespan,
)

# Register all tool groups
try:
    session_tools = BrowserSessionTools(
        connection_manager=connection_manager, snapshot_manager=snapshot_manager
    )
    session_tools.register(mcp)

    navigation_tools = NavigationTools(connection_manager, snapshot_manager)
    navigation_tools.register(mcp)

    interaction_tools = InteractionTools(connection_manager, snapshot_manager)
    interaction_tools.register(mcp)

    observation_tools = ObservationTools(connection_manager, snapshot_manager)
    observation_tools.register(mcp)

    management_tools = ManagementTools(connection_manager, snapshot_manager)
    management_tools.register(mcp)

    logger.info('All browser tools registered successfully')
except Exception as e:
    logger.error(f'Error initializing browser tools: {e}')
    raise


def main():
    """Run the MCP server."""
    mcp.run()


if __name__ == '__main__':
    main()
