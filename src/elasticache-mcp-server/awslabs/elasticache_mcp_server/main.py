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

"""awslabs elasticache MCP Server implementation."""

import argparse
from awslabs.elasticache_mcp_server.common.server import mcp
from awslabs.elasticache_mcp_server.context import Context
from awslabs.elasticache_mcp_server.tools import (  # noqa: F401 - imported for side effects to register tools
    cc,
    ce,
    cw,
    cwlogs,
    firehose,
    misc,
    rg,
    serverless,
)
from loguru import logger


def main():
    """Run the MCP server with CLI argument support."""
    parser = argparse.ArgumentParser(
        description='An AWS Labs Model Context Protocol (MCP) server for interacting with Amazon ElastiCache'
    )
    parser.add_argument(
        '--readonly',
        action=argparse.BooleanOptionalAction,
        help='Prevents the MCP server from performing mutating operations',
    )

    args = parser.parse_args()
    Context.initialize(args.readonly)

    logger.info('Amazon ElastiCache MCP Server Started...')
    mcp.run()


if __name__ == '__main__':
    main()
