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

"""Main entry point for the AWS HealthImaging MCP server."""

# Standard library imports
import asyncio

# Local imports
from .server import create_healthimaging_server

# Third-party imports
from loguru import logger
from mcp.server.stdio import stdio_server


async def main() -> None:
    """Main entry point for the server."""
    try:
        # Create the HealthImaging MCP server
        server = create_healthimaging_server()

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
