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

"""awslabs aws-appsync MCP Server implementation."""

import argparse
from awslabs.aws_appsync_mcp_server.decorators import set_write_allowed
from awslabs.aws_appsync_mcp_server.tools.create_api import register_create_api_tool
from awslabs.aws_appsync_mcp_server.tools.create_api_cache import register_create_api_cache_tool
from awslabs.aws_appsync_mcp_server.tools.create_api_key import register_create_api_key_tool
from awslabs.aws_appsync_mcp_server.tools.create_channel_namespace import (
    register_create_channel_namespace_tool,
)
from awslabs.aws_appsync_mcp_server.tools.create_datasource import register_create_datasource_tool
from awslabs.aws_appsync_mcp_server.tools.create_domain_name import (
    register_create_domain_name_tool,
)
from awslabs.aws_appsync_mcp_server.tools.create_function import register_create_function_tool
from awslabs.aws_appsync_mcp_server.tools.create_graphql_api import (
    register_create_graphql_api_tool,
)
from awslabs.aws_appsync_mcp_server.tools.create_resolver import register_create_resolver_tool
from awslabs.aws_appsync_mcp_server.tools.create_schema import register_create_schema_tool
from loguru import logger
from mcp.server.fastmcp import FastMCP


# Initialize FastMCP app
mcp = FastMCP(
    'awslabs.aws-appsync-mcp-server',
    instructions="""
    AWS AppSync MCP Server provides tools to interact with AWS AppSync API services.

    This server enables you to:
    - Create and manage AppSync APIs
    - Create GraphQL APIs with various authentication types
    - Create API keys for authentication
    - Create API caches for improved performance
    - Create data sources to connect APIs to backend services

    For more information about AWS AppSync, visit:
    https://aws.amazon.com/appsync/
    """,
    dependencies=[
        'pydantic',
        'loguru',
        'boto3',
    ],
)


def main():
    """Run the MCP server with CLI argument support."""
    parser = argparse.ArgumentParser(
        description='An AWS Labs Model Context Protocol (MCP) server for AWS AppSync'
    )
    parser.add_argument(
        '--allow-write',
        action='store_true',
        help='Allow write operations. By default, the server runs in read-only mode.',
    )

    args = parser.parse_args()

    # Set the global write permission state
    set_write_allowed(args.allow_write)

    # Register all tools after setting the write permission
    register_create_api_tool(mcp)
    register_create_graphql_api_tool(mcp)
    register_create_api_key_tool(mcp)
    register_create_api_cache_tool(mcp)
    register_create_datasource_tool(mcp)
    register_create_function_tool(mcp)
    register_create_channel_namespace_tool(mcp)
    register_create_domain_name_tool(mcp)
    register_create_resolver_tool(mcp)
    register_create_schema_tool(mcp)

    logger.info(
        f'Starting AWS AppSync MCP Server (write operations: {"enabled" if args.allow_write else "disabled"}).'
    )
    mcp.run()


if __name__ == '__main__':
    main()
