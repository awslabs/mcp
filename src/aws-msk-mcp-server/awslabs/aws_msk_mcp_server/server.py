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

"""Amazon MSK MCP Server Main Module.

This module implements the Model Context Protocol (MCP) server for Amazon MSK.
It exposes the abstracted APIs via the MCP protocol.
"""

import argparse
import os
import signal
from anyio import create_task_group, open_signal_receiver, run
from anyio.abc import CancelScope
from awslabs.aws_msk_mcp_server.tools import (
    logs_and_telemetry,
    mutate_cluster,
    mutate_config,
    mutate_vpc,
    read_cluster,
    read_config,
    read_global,
    read_vpc,
    static_tools,
)
from loguru import logger
from mcp.server.fastmcp import FastMCP


# Global variables
read_only = True  # Default to read-only mode
ERROR_WRITE_OPERATION_IN_READ_ONLY_MODE = 'Your MSK MCP server does not allow writes. To use write operations, change the MCP configuration to include the --allow-writes parameter.'


async def signal_handler(scope: CancelScope):
    """Handle SIGINT and SIGTERM signals asynchronously.

    The anyio.open_signal_receiver returns an async generator that yields
    signal numbers whenever a specified signal is received. The async for
    loop waits for signals and processes them as they arrive.
    """
    with open_signal_receiver(signal.SIGINT, signal.SIGTERM) as signals:
        async for _ in signals:  # Shutting down regardless of the signal type
            print('Shutting down MCP server...')
            # Force immediate exit since MCP blocks on stdio.
            # You can also use scope.cancel(), but it means after Ctrl+C, you need to press another
            # 'Enter' to unblock the stdio.
            os._exit(0)


async def run_server():
    """Run the MCP server with signal handling."""
    mcp = FastMCP(
        name='awslabs.aws-msk-mcp-server',
        instructions="""
        AWS MSK MCP Server providing tools to interact with MSK Clusters.

        This server enables you to:
        - Read global/clusterlevel/configuration/vpc information given a specified region
        - Get details regarding metrics and customer access
        - Create and update clusters, configurations, vpc connections
        """,
    )

    # Register read modules (always available)
    read_cluster.register_module(mcp)
    read_global.register_module(mcp)
    read_vpc.register_module(mcp)
    read_config.register_module(mcp)
    logs_and_telemetry.register_module(mcp)
    static_tools.register_module(mcp)

    # Only register mutate modules if write operations are allowed
    if not read_only:
        logger.info('Write operations are enabled')
        mutate_cluster.register_module(mcp)
        mutate_config.register_module(mcp)
        mutate_vpc.register_module(mcp)
    else:
        logger.info('Server running in read-only mode. Write operations are disabled.')

    # Register prompts

    async with create_task_group() as tg:
        tg.start_soon(signal_handler, tg.cancel_scope)
        await mcp.run_stdio_async()


def main():
    """Entry point for the MCP server."""
    # Parse command-line arguments
    parser = argparse.ArgumentParser(
        description='An AWS Labs Model Context Protocol (MCP) server for Amazon MSK'
    )
    parser.add_argument(
        '--allow-writes',
        action='store_true',
        help='Allow use of tools that may perform write operations',
    )
    args = parser.parse_args()

    # Set global read_only flag based on command-line arguments
    global read_only
    read_only = not args.allow_writes

    logger.info('AWS MSK MCP server initialized with ALLOW-WRITES:{}', not read_only)

    run(run_server)


if __name__ == '__main__':
    main()
