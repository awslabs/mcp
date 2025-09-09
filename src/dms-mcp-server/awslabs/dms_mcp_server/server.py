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

"""awslabs Database Migration Service MCP Server implementation."""

import argparse
import os
import sys
from awslabs.dms_mcp_server.common.server import mcp
from awslabs.dms_mcp_server.consts import ENV_VARS
from awslabs.dms_mcp_server.context import Context
from awslabs.dms_mcp_server.tools import endpoints, instances, tasks  # noqa: F401
from loguru import logger


# Configure logging according to design guidelines
logger.remove()
# Ensure all logging goes to stderr, never stdout
logger.add(
    sys.stderr,
    level=os.getenv(ENV_VARS['FASTMCP_LOG_LEVEL'], 'WARNING'),
    format='{time} | {level} | {message}',
)


def main():
    """Run the MCP server with CLI argument support."""
    parser = argparse.ArgumentParser(
        description='An AWS Labs Model Context Protocol (MCP) server for AWS Database Migration Service (DMS)'
    )
    parser.add_argument(
        '--read-only-mode',
        action=argparse.BooleanOptionalAction,
        default=True,
        help='Run server in read-only mode (default: True)',
    )

    args = parser.parse_args()
    Context.initialize(args.read_only_mode)

    logger.info('AWS Database Migration Service MCP Server Started...')

    if Context.readonly_mode():
        logger.info('Server running in read-only mode. Write operations are disabled.')
    else:
        logger.info('Write operations are enabled')

    mcp.run()


if __name__ == '__main__':
    main()
