#!/usr/bin/env python3
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

"""Main entry point for the AWS HealthLake MCP server."""

# Standard library imports
import argparse
import asyncio
import os
import sys

# Local imports
from .server import create_healthlake_server

# Third-party imports
from loguru import logger
from mcp.server.stdio import stdio_server


# Configure logging
logger.remove()
logger.add(sys.stderr, level=os.getenv('MCP_LOG_LEVEL', 'WARNING'))


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='AWS HealthLake MCP Server')
    parser.add_argument(
        '--readonly',
        action='store_true',
        help='Run server in read-only mode (prevents all mutating operations)',
    )
    return parser.parse_args()


async def main() -> None:
    """Main entry point for the server."""
    try:
        # Parse command line arguments
        args = parse_args()

        # Create the HealthLake MCP server with read-only mode
        server = create_healthlake_server(read_only=args.readonly)

        # Log server mode
        if args.readonly:
            logger.info('Server started in READ-ONLY mode - mutating operations disabled')
        else:
            logger.info('Server started in FULL ACCESS mode')

        # Run the server using stdio transport
        async with stdio_server() as (read_stream, write_stream):
            await server.run(read_stream, write_stream, server.create_initialization_options())
    except Exception as e:
        logger.error(f'Server error: {e}')
        raise


def sync_main() -> None:
    """Synchronous wrapper for the main function."""
    asyncio.run(main())


if __name__ == '__main__':
    sync_main()
