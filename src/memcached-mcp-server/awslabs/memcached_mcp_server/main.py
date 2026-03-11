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

"""awslabs memcached MCP Server implementation."""

import argparse
from awslabs.memcached_mcp_server.common.server import mcp
from awslabs.memcached_mcp_server.context import Context
from awslabs.memcached_mcp_server.tools import cache  # noqa: F401
from loguru import logger
from starlette.requests import Request  # noqa: F401
from starlette.responses import Response


# Add a health check route directly to the MCP server
@mcp.custom_route('/health', methods=['GET'])
async def health_check(request):
    """Simple health check endpoint for ALB Target Group.

    Always returns 200 OK to indicate the service is running.
    """
    return Response(content='healthy', status_code=200, media_type='text/plain')


class MemcachedMCPServer:
    """Memcached MCP Server wrapper."""

    def __init__(self, transport='stdio', host='localhost', port=8000):
        """Initialize with transport, host, and port."""
        self.transport = transport
        self.host = host
        self.port = port

    def run(self):
        """Run server with appropriate transport, host, and port."""
        mcp.run(transport=self.transport, host=self.host, port=self.port)


def main():
    """Run the MCP server with CLI argument support."""
    parser = argparse.ArgumentParser(
        description='An AWS Labs Model Context Protocol (MCP) server for interacting with Memcached'
    )
    parser.add_argument(
        '--readonly',
        action=argparse.BooleanOptionalAction,
        help='Prevents the MCP server from performing mutating operations',
    )
    parser.add_argument(
        '--transport',
        choices=['stdio', 'sse', 'streamable-http'],
        default='stdio',
        help='Transport protocol to use (default: stdio)',
    )
    parser.add_argument(
        '--host',
        type=str,
        default='127.0.0.1',
        help='Host to bind to (default: localhost)',
    )
    parser.add_argument(
        '--port',
        type=int,
        default=8000,
        help='Port to bind to (default: 8000)',
    )

    args = parser.parse_args()
    Context.initialize(args.readonly)

    logger.info('Amazon ElastiCache Memcached MCP Server Started...')
    MemcachedMCPServer(transport=args.transport, host=args.host, port=args.port).run()


if __name__ == '__main__':
    main()
