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
"""awslabs AWS Documentation MCP Server implementation."""

import argparse
import os
import sys
from loguru import logger


# Set up logging
logger.remove()
logger.add(sys.stderr, level=os.getenv('FASTMCP_LOG_LEVEL', 'WARNING'))

PARTITION = os.getenv('AWS_DOCUMENTATION_PARTITION', 'aws').lower()


def main():
    """Run the MCP server with CLI argument support."""
    # Parse command-line arguments to pass through to sub-servers
    parser = argparse.ArgumentParser(
        description='AWS Documentation MCP Server'
    )
    parser.add_argument(
        '--transport',
        type=str,
        choices=['stdio', 'sse', 'streamable-http'],
        default='stdio',
        help='MCP transport to use (default: stdio)',
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

    if PARTITION == 'aws':
        from awslabs.aws_documentation_mcp_server.server_aws import main
    elif PARTITION == 'aws-cn':
        from awslabs.aws_documentation_mcp_server.server_aws_cn import main
    else:
        raise ValueError(f'Unsupported AWS documentation partition: {PARTITION}.')

    main(transport=args.transport, host=args.host, port=args.port)


if __name__ == '__main__':
    main()
