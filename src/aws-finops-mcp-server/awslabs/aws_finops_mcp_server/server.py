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

"""awslabs aws-finops MCP Server implementation."""

import os

# Use absolute imports instead of relative imports
from awslabs.aws_finops_mcp_server.boto3_tools import Boto3ToolRegistry
from awslabs.aws_finops_mcp_server.consts import (
    ENV_STORAGE_LENS_MANIFEST_LOCATION,
    ENV_STORAGE_LENS_OUTPUT_LOCATION,
    MCP_SERVER_DEPENDENCIES,
    MCP_SERVER_INSTRUCTIONS,
    MCP_SERVER_NAME,
    STORAGE_LENS_DEFAULT_DATABASE,
    STORAGE_LENS_DEFAULT_TABLE,
)
from awslabs.aws_finops_mcp_server.models import (
    ServerConfig,
    StorageLensQueryRequest,
)
from awslabs.aws_finops_mcp_server.storage_lens import StorageLensQueryTool
from loguru import logger
from mcp.server.fastmcp import FastMCP
from typing import Any, Awaitable, Callable, Dict


# Create server configuration
server_config = ServerConfig(
    server_name=MCP_SERVER_NAME,
    server_instructions=MCP_SERVER_INSTRUCTIONS,
    dependencies=MCP_SERVER_DEPENDENCIES,
    default_aws_region='us-east-1',
    storage_lens_default_database=STORAGE_LENS_DEFAULT_DATABASE,
    storage_lens_default_table=STORAGE_LENS_DEFAULT_TABLE,
    athena_max_retries=100,
    athena_retry_delay_seconds=1,
)

# Initialize FastMCP with server configuration
mcp = FastMCP(
    server_config.server_name,
    instructions=server_config.server_instructions,
    dependencies=server_config.dependencies,
)


def create_tool_function(
    registry: Boto3ToolRegistry, tool_name: str
) -> Callable[[Dict[str, Any]], Awaitable[Any]]:
    """Create a unique function for each tool."""

    async def tool_function(params: Dict[str, Any]):
        """Tool function that takes a single params object."""
        logger.info(f'Calling tool: {tool_name} with params: {params}')
        return await registry.generic_handler(tool_name, **params)

    # Set the function name to the tool name
    tool_function.__name__ = tool_name
    return tool_function


def register_boto3_tools():
    """Register all boto3 tools with the MCP server."""
    # Create the registry
    registry = Boto3ToolRegistry()

    # Register all tools with the registry
    registry.register_all_tools()

    # For each tool in the registry, create a properly typed function
    for tool_name, tool_info in registry.tools.items():
        # Create a unique function for this tool
        tool_function = create_tool_function(registry, tool_name)

        # Register the tool with FastMCP
        mcp.tool(name=tool_name, description=tool_info.docstring)(tool_function)


# Register all boto3 tools
register_boto3_tools()


# Register Storage Lens query tool
def register_storage_lens_tools():
    """Register Storage Lens query tools with the MCP server."""
    # Read the metrics reference file for the docstring
    metrics_reference_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        'resources',
        'storage_lens_metrics_reference.md',
    )

    try:
        with open(metrics_reference_path, 'r') as f:
            metrics_reference = f.read()
    except FileNotFoundError:
        logger.warning(f'Metrics reference file not found: {metrics_reference_path}')
        metrics_reference = 'S3 Storage Lens Query Tool'

    # Create the tool instance
    storage_lens_tool = StorageLensQueryTool()

    # Get manifest location from environment variable
    manifest_location = os.environ.get(ENV_STORAGE_LENS_MANIFEST_LOCATION)
    if not manifest_location:
        logger.warning(f'{ENV_STORAGE_LENS_MANIFEST_LOCATION} environment variable not set')

    # Register the tool with FastMCP
    @mcp.tool(name='storage_lens_run_query', description=metrics_reference)
    async def storage_lens_run_query(query: str):
        """Query S3 Storage Lens metrics using Athena.

        Args:
            query: SQL query to execute against the data (use {table} as a placeholder for the table name)

        Returns:
            dict: Query results and metadata

        Note:
            This tool uses the following configuration from environment variables:
            - STORAGE_LENS_MANIFEST_LOCATION: S3 URI to manifest file or folder
            - STORAGE_LENS_OUTPUT_LOCATION: (Optional) S3 location for Athena query results

            Default values:
            - database_name: "storage_lens_db"
            - table_name: "storage_lens_metrics"
        """
        logger.info(f'Running Storage Lens query: {query}')

        # Get output location from environment variable (optional)
        output_location = os.environ.get(ENV_STORAGE_LENS_OUTPUT_LOCATION, '')

        try:
            # Create a validated request object
            request = StorageLensQueryRequest(
                manifest_location=manifest_location or '',  # Ensure non-None value
                query=query,
                output_location=output_location,
                database_name=server_config.storage_lens_default_database,
                table_name=server_config.storage_lens_default_table,
            )

            # Pass the request object directly to query_storage_lens
            result = await storage_lens_tool.query_storage_lens(request)

            # Return the Pydantic model directly
            return result
        except Exception as e:
            logger.error(f'Error in storage_lens_run_query: {str(e)}')
            return {'error': str(e), 'message': 'Failed to execute Storage Lens query'}


# Register Storage Lens tools
register_storage_lens_tools()


# Register all prompts
def register_prompts():
    """Register all prompts with the MCP server."""
    try:
        # Use absolute import instead of relative import
        from awslabs.aws_finops_mcp_server.prompts import register_all_prompts

        register_all_prompts(mcp)
        logger.info('Registered all prompts')
    except Exception as e:
        logger.error(f'Error registering prompts: {e}')


# Register all prompts
register_prompts()


def main():
    """Run the MCP server with CLI argument support."""
    mcp.run()


if __name__ == '__main__':
    main()
