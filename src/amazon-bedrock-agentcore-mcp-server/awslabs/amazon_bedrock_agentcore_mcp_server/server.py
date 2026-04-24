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

"""awslabs AWS Bedrock AgentCore MCP Server implementation."""

import asyncio
import os
import signal
from .tools import docs, gateway
from .utils import cache
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from loguru import logger
from mcp.server.fastmcp import FastMCP


APP_NAME = 'amazon-bedrock-agentcore-mcp-server'

AGENTCORE_MCP_INSTRUCTIONS = (
    'Use this MCP server to access Amazon Bedrock AgentCore services — '
    'agent runtime, code interpreter sandboxes, cloud browser sessions, '
    'memory, gateway, identity, policy, evaluations, and documentation.\n\n'
    '## Code Interpreter Tools\n'
    'Use start_code_interpreter_session to create a sandbox, then execute_code, '
    'execute_command, or install_packages to run code. Use upload_file and '
    'download_file to transfer data. Stop sessions when done to release '
    'resources.\n\n'
    '## Browser Tools\n'
    'Start a browser session with start_browser_session, then use browser '
    'interaction tools (browser_navigate, browser_snapshot, browser_click, '
    'browser_type, etc.) to interact with web pages. Each session runs in an '
    'isolated cloud environment — no local browser installation is required. '
    'Call stop_browser_session when done.\n\n'
    'Tips:\n'
    '- Use DuckDuckGo or Bing instead of Google — Google blocks cloud browser '
    'IPs with CAPTCHAs.\n'
    '- For content-heavy pages, use browser_evaluate with JavaScript to extract '
    'specific data instead of relying solely on the accessibility snapshot, '
    'which can be very large.\n'
    '- For data extraction, prefer browser_evaluate over browser_snapshot. '
    'Use querySelectorAll to extract structured JSON (e.g., '
    '`[...document.querySelectorAll("tr")].map(r => r.innerText)`). '
    'Snapshots are best for understanding page structure and finding element '
    'refs; evaluate is best for extracting actual text and data.\n'
    '- To set long text in form fields, use browser_evaluate with '
    '`document.querySelector("selector").value = "text"` instead of '
    'browser_type or browser_fill_form, which type character-by-character '
    'and may timeout on long inputs.\n'
    '- The timeout_seconds parameter on start_browser_session is an idle '
    'timeout measured from the last activity, not an absolute session '
    'duration. Active sessions persist as long as there is interaction '
    'within the timeout window.'
)


def _is_service_enabled(name: str) -> bool:
    """Check if a service should be registered based on env vars."""
    disable = os.getenv('AGENTCORE_DISABLE_TOOLS', '')
    enable = os.getenv('AGENTCORE_ENABLE_TOOLS', '')

    if enable and disable:
        logger.warning(
            'Both AGENTCORE_ENABLE_TOOLS and AGENTCORE_DISABLE_TOOLS are set.'
            ' AGENTCORE_ENABLE_TOOLS takes precedence;'
            ' AGENTCORE_DISABLE_TOOLS is ignored.'
        )

    if enable:
        allowed = {t.strip().lower() for t in enable.split(',') if t.strip()}
        if not allowed:
            logger.warning(
                'AGENTCORE_ENABLE_TOOLS is set but contains no valid '
                'entries. All services enabled.'
            )
            return True
        return name.lower() in allowed
    if disable:
        blocked = {t.strip().lower() for t in disable.split(',') if t.strip()}
        return name.lower() not in blocked
    return True


# Browser managers — set during registration, used by lifespan
_browser_cm = None
_browser_sm = None

# Code interpreter cleanup function
_code_interpreter_cleanup = None


@asynccontextmanager
async def server_lifespan(server: FastMCP) -> AsyncIterator[None]:
    """Manage server lifecycle.

    Handles browser cleanup task, code interpreter cleanup, and
    graceful shutdown.
    """
    if _browser_cm is not None and _browser_sm is not None:
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(
                sig,
                lambda cm=_browser_cm: asyncio.ensure_future(cm.cleanup()),
            )

        from .tools.browser import cleanup_stale_sessions

        task = asyncio.create_task(cleanup_stale_sessions(_browser_cm, _browser_sm))
        try:
            yield
        finally:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            await _browser_cm.cleanup()
            if _code_interpreter_cleanup is not None:
                await _code_interpreter_cleanup()
    else:
        try:
            yield
        finally:
            if _code_interpreter_cleanup is not None:
                await _code_interpreter_cleanup()


mcp = FastMCP(
    APP_NAME,
    instructions=AGENTCORE_MCP_INSTRUCTIONS,
    lifespan=server_lifespan,
)

# Docs tools are always registered (no opt-out)
mcp.tool()(docs.search_agentcore_docs)
mcp.tool()(docs.fetch_agentcore_doc)

if _is_service_enabled('runtime'):
    try:
        from .tools.runtime import register_runtime_tools

        register_runtime_tools(mcp)
        logger.info('Runtime tools registered')
    except ImportError as e:
        logger.error(f'Runtime tools disabled — failed to import dependencies: {e}.')
    except Exception as e:
        logger.error(
            f'Runtime tools disabled — initialization failed: {e}. '
            f'Set AGENTCORE_DISABLE_TOOLS=runtime to suppress.'
        )

if _is_service_enabled('memory'):
    try:
        from .tools.memory import register_memory_tools

        register_memory_tools(mcp)
        logger.info('Memory tools registered (21 tools)')
    except ImportError as e:
        logger.error(
            f'Memory tools disabled — failed to import dependencies: {e}.'
            f' Ensure boto3 and botocore are installed.'
        )
    except Exception as e:
        logger.error(
            f'Memory tools disabled — initialization failed: {e}. '
            f'Set AGENTCORE_DISABLE_TOOLS=memory to suppress.'
        )

if _is_service_enabled('gateway'):
    mcp.tool()(gateway.manage_agentcore_gateway)

if _is_service_enabled('browser'):
    try:
        from .tools.browser import register_browser_tools

        _browser_cm, _browser_sm = register_browser_tools(mcp)
        logger.info('Browser tools registered (25 tools)')
    except ImportError as e:
        logger.error(
            f'Browser tools disabled — failed to import dependencies: '
            f'{e}. Ensure playwright and bedrock-agentcore are installed.'
        )
    except Exception as e:
        logger.error(
            f'Browser tools disabled — initialization failed: {e}. '
            f'Set AGENTCORE_DISABLE_TOOLS=browser to suppress.'
        )

if _is_service_enabled('code_interpreter'):
    try:
        from .tools.code_interpreter import (
            cleanup_code_interpreter,
            register_code_interpreter_tools,
        )

        register_code_interpreter_tools(mcp)
        _code_interpreter_cleanup = cleanup_code_interpreter
        logger.info('Code interpreter tools registered (9 tools)')
    except ImportError as e:
        logger.error(
            f'Code interpreter tools disabled — failed to import '
            f'dependencies: {e}. Ensure bedrock-agentcore is installed.'
        )
    except Exception as e:
        logger.error(
            f'Code interpreter tools disabled — initialization failed: '
            f'{e}. Set AGENTCORE_DISABLE_TOOLS=code_interpreter '
            f'to suppress.'
        )


def main() -> None:
    """Main entry point for the MCP server.

    Initializes the document cache and starts the FastMCP server.
    The cache is loaded with document titles only for fast startup,
    with full content fetched on-demand.
    """
    cache.ensure_ready()
    mcp.run()


if __name__ == '__main__':
    main()
