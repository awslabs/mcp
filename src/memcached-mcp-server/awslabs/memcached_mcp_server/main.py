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

from awslabs.memcached_mcp_server.common.server import mcp
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

    def run(self):
        """Run server with appropriate transport."""
        mcp.run()


def main():
    """Run the MCP server with CLI argument support."""
    logger.info('Amazon ElastiCache Memcached MCP Server Started...')
    MemcachedMCPServer().run()


if __name__ == '__main__':
    main()
