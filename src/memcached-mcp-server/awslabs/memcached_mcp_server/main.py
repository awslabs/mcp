# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance
# with the License. A copy of the License is located at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES
# OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions
# and limitations under the License.

"""awslabs memcached MCP Server implementation."""

import argparse
from awslabs.memcached_mcp_server.common.server import mcp
from awslabs.memcached_mcp_server.tools import cache  # noqa: F401
from loguru import logger


class MemcachedMCPServer:
    """Memcached MCP Server wrapper."""

    def __init__(self, sse=False, port=None):
        """Initialize MCP Server wrapper."""
        self.sse = sse
        self.port = port

    def run(self):
        """Run server with appropriate transport."""
        if self.sse:
            mcp.settings.port = self.port
            mcp.run(transport='sse')
        else:
            mcp.run()


def main():
    """Run the MCP server with CLI argument support."""
    parser = argparse.ArgumentParser(
        description='An AWS Labs Model Context Protocol (MCP) server for Amazon ElastiCache Memcached'
    )
    parser.add_argument('--sse', action='store_true', help='Use SSE transport')
    parser.add_argument('--port', type=int, default=8888, help='Port to run the server on')

    args = parser.parse_args()

    logger.trace('A trace message.')
    logger.debug('A debug message.')
    logger.info('An info message.')
    logger.success('A success message.')
    logger.warning('A warning message.')
    logger.error('An error message.')
    logger.critical('A critical message.')

    # Run server with appropriate transport
    server = MemcachedMCPServer(args.sse, args.port)
    server.run()


if __name__ == '__main__':
    main()
