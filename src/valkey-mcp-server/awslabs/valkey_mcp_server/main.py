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

"""awslabs valkey MCP Server implementation."""

from awslabs.valkey_mcp_server.common.server import mcp
from awslabs.valkey_mcp_server.tools import (
    bitmap,  # noqa: F401
    hash,  # noqa: F401
    hyperloglog,  # noqa: F401
    json,  # noqa: F401
    list,  # noqa: F401
    misc,  # noqa: F401
    server_management,  # noqa: F401
    set,  # noqa: F401
    sorted_set,  # noqa: F401
    stream,  # noqa: F401
    string,  # noqa: F401
)
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


class ValkeyMCPServer:
    """Valkey MCP Server wrapper."""

    def __init__(self):
        """Initialize MCP Server wrapper."""

    def run(self):
        """Run server with appropriate transport."""
        mcp.run()


def main():
    """Run the MCP server with CLI argument support."""
    logger.info('Amazon ElastiCache/MemoryDB Valkey MCP Server Started...')

    server = ValkeyMCPServer()
    server.run()


if __name__ == '__main__':
    main()
