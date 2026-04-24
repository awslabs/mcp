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

"""awslabs valkey MCP Server implementation."""

from __future__ import annotations

import argparse
import asyncio
import atexit
import logging
import os
import sys
from awslabs.valkey_mcp_server.common.connection import close_client
from awslabs.valkey_mcp_server.common.server import mcp
from awslabs.valkey_mcp_server.context import Context
from awslabs.valkey_mcp_server.tools import (  # noqa: F401
    json,
    search_add_documents,
    search_aggregate,
    search_manage_index,
    search_query,
    valkey_admin,
    valkey_read,
    valkey_write,
)
from loguru import logger
from starlette.requests import Request  # noqa: F401
from starlette.responses import Response


def _configure_logging():
    """Configure loguru file sink and bridge stdlib logging into loguru."""
    log_file = os.environ.get('MCP_LOG_FILE', 'valkey-mcp-server.log')
    log_level = os.environ.get('MCP_LOG_LEVEL', 'DEBUG')

    # File sink — persists across crashes for post-mortem analysis
    logger.add(
        log_file,
        level=log_level,
        rotation='10 MB',
        retention='3 days',
        backtrace=True,
        diagnose=True,
        format='{time:YYYY-MM-DD HH:mm:ss.SSS} | {level:<8} | {name}:{function}:{line} | {message}',
    )

    # Bridge stdlib logging → loguru so tool modules (which use logging.getLogger) are captured
    class _LoguruHandler(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            try:
                level = logger.level(record.levelname).name
            except ValueError:
                level = record.levelno
            # depth=6: logging.info() → Logger.info() → Logger._log() → Logger.handle()
            #          → Handler.emit() → _LoguruHandler.emit() → loguru
            # See: https://loguru.readthedocs.io/en/stable/overview.html#entirely-compatible-with-standard-logging
            frame, depth = sys._getframe(6), 6
            while frame and frame.f_code.co_filename == logging.__file__:
                frame = frame.f_back
                depth += 1
            logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())

    logging.basicConfig(handlers=[_LoguruHandler()], level=logging.DEBUG, force=True)


@mcp.custom_route('/health', methods=['GET'])
async def health_check(request):
    """Simple health check endpoint for ALB Target Group."""
    return Response(content='healthy', status_code=200, media_type='text/plain')


class ValkeyMCPServer:
    """Valkey MCP Server wrapper."""

    def __init__(self):
        """Initialize MCP Server wrapper."""

    def run(self):
        """Run server with appropriate transport."""
        mcp.run()


def main():
    """Run the MCP server with CLI argument support."""
    parser = argparse.ArgumentParser(
        description='An AWS Labs Model Context Protocol (MCP) server for interacting with Valkey'
    )
    parser.add_argument(
        '--readonly',
        action=argparse.BooleanOptionalAction,
        help='Prevents the MCP server from performing mutating operations',
    )

    args = parser.parse_args()

    # Redirect the native stdout fd to stderr BEFORE GLIDE initializes.
    # GLIDE's Rust logger_core writes ANSI-colored warnings directly to the native
    # stdout fd, which corrupts the MCP stdio JSON-RPC transport. By redirecting
    # fd 1 to stderr, native writes go to stderr while Python's sys.stdout (used
    # by the MCP transport) continues to use the original fd via its buffered wrapper.
    _original_stdout_fd = os.dup(1)
    os.dup2(2, 1)  # fd 1 (stdout) now points to stderr
    sys.stdout = os.fdopen(_original_stdout_fd, 'w')  # Python stdout uses the saved fd

    _configure_logging()
    Context.initialize(args.readonly)

    atexit.register(lambda: asyncio.run(close_client()))

    logger.info('Amazon ElastiCache/MemoryDB Valkey MCP Server Started...')

    server = ValkeyMCPServer()
    server.run()


if __name__ == '__main__':
    main()
