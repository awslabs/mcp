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

"""awslabs cloudtrail MCP Server implementation."""

import argparse
from awslabs.cloudtrail_mcp_server.tools import CloudTrailTools
from loguru import logger
from fastmcp import FastMCP


mcp = FastMCP(
    'awslabs.cloudtrail-mcp-server',
    instructions='Use this MCP server to query AWS CloudTrail events for security investigations, compliance auditing, and operational troubleshooting. Supports event lookup by various attributes (username, event name, resource name, etc.), user activity analysis, API call tracking, and advanced CloudTrail Lake SQL queries for complex analytics. Can search the last 90 days of management events and provides detailed event summaries and activity analysis.',
)

# Initialize and register CloudTrail tools
try:
    cloudtrail_tools = CloudTrailTools()
    cloudtrail_tools.register(mcp)
    logger.info('CloudTrail tools registered successfully')
except Exception as e:
    logger.error(f'Error initializing CloudTrail tools: {str(e)}')
    raise


def main():
    """Run the MCP server."""
    parser = argparse.ArgumentParser(
        description='An AWS Labs Model Context Protocol (MCP) server'
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
        help='Host to bind to (default: 127.0.0.1)',
    )
    parser.add_argument(
        '--port',
        type=int,
        default=8000,
        help='Port to bind to (default: 8000)',
    )
    args = parser.parse_args()
    mcp.run(transport=args.transport, host=args.host, port=args.port)


if __name__ == '__main__':
    main()
