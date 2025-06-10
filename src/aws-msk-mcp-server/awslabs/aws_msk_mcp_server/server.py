"""
Amazon MSK MCP Server Main Module

This module implements the Model Context Protocol (MCP) server for Amazon MSK.
It exposes the abstracted APIs via the MCP protocol.
"""

import os
import signal

from anyio import create_task_group, open_signal_receiver, run
from anyio.abc import CancelScope
from mcp.server.fastmcp import FastMCP

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

async def signal_handler(scope: CancelScope):
    """Handle SIGINT and SIGTERM signals asynchronously.

    The anyio.open_signal_receiver returns an async generator that yields
    signal numbers whenever a specified signal is received. The async for
    loop waits for signals and processes them as they arrive.
    """
    with open_signal_receiver(signal.SIGINT, signal.SIGTERM) as signals:
        async for _ in signals:  # Shutting down regardless of the signal type
            print("Shutting down MCP server...")
            # Force immediate exit since MCP blocks on stdio.
            # You can also use scope.cancel(), but it means after Ctrl+C, you need to press another
            # 'Enter' to unblock the stdio.
            os._exit(0)


async def run_server():
    """Run the MCP server with signal handling."""
    mcp = FastMCP(
        name="GrandCanyonMSKMCPServer",
        instructions="An example MCP server",
    )

    # Register modules
    read_cluster.register_module(mcp)
    read_global.register_module(mcp)
    read_vpc.register_module(mcp)
    read_config.register_module(mcp)
    mutate_cluster.register_module(mcp)
    mutate_config.register_module(mcp)
    mutate_vpc.register_module(mcp)
    logs_and_telemetry.register_module(mcp)
    static_tools.register_module(mcp)

    # Register prompts

    async with create_task_group() as tg:
        tg.start_soon(signal_handler, tg.cancel_scope)
        await mcp.run_stdio_async()


def main():
    """Entry point for the MCP server."""
    run(run_server)
