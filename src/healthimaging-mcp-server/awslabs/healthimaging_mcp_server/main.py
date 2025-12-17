#!/usr/bin/env python3
"""Main entry point for the AWS HealthImaging MCP server."""

# Standard library imports
import asyncio
import logging

# Local imports
from .server import create_healthimaging_server

# Third-party imports
from mcp.server.stdio import stdio_server


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


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
