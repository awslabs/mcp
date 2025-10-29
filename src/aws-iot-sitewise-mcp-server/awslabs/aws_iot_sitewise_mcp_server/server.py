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

import os
import signal
from anyio import CancelScope, create_task_group, open_signal_receiver, run
from awslabs.aws_iot_sitewise_mcp_server import __version__
from awslabs.aws_iot_sitewise_mcp_server.prompts.asset_hierarchy import (
    asset_hierarchy_visualization_prompt,
)
from awslabs.aws_iot_sitewise_mcp_server.prompts.bulk_import_workflow import (
    bulk_import_workflow_helper_prompt,
)
from awslabs.aws_iot_sitewise_mcp_server.prompts.data_exploration import (
    data_exploration_helper_prompt,
)
from awslabs.aws_iot_sitewise_mcp_server.prompts.data_ingestion import (
    data_ingestion_helper_prompt,
)
from awslabs.aws_iot_sitewise_mcp_server.tool_metadata import is_readonly_tool
from awslabs.aws_iot_sitewise_mcp_server.tools.sitewise_access import (
    describe_default_encryption_configuration_tool,
    describe_logging_options_tool,
    describe_storage_configuration_tool,
    put_default_encryption_configuration_tool,
    put_logging_options_tool,
    put_storage_configuration_tool,
)
from awslabs.aws_iot_sitewise_mcp_server.tools.sitewise_asset_models import (
    create_asset_model_composite_model_tool,
    create_asset_model_tool,
    delete_asset_model_tool,
    describe_asset_model_tool,
    list_asset_model_properties_tool,
    list_asset_models_tool,
    update_asset_model_tool,
)
from awslabs.aws_iot_sitewise_mcp_server.tools.sitewise_assets import (
    associate_assets_tool,
    create_asset_tool,
    delete_asset_tool,
    describe_asset_tool,
    disassociate_assets_tool,
    list_assets_tool,
    list_associated_assets_tool,
    update_asset_tool,
)
from awslabs.aws_iot_sitewise_mcp_server.tools.sitewise_data import (
    batch_get_asset_property_aggregates_tool,
    batch_get_asset_property_value_history_tool,
    batch_get_asset_property_value_tool,
    batch_put_asset_property_value_tool,
    create_buffered_ingestion_job_tool,
    create_bulk_import_iam_role_tool,
    create_bulk_import_job_tool,
    describe_bulk_import_job_tool,
    execute_query_tool,
    get_asset_property_aggregates_tool,
    get_asset_property_value_history_tool,
    get_asset_property_value_tool,
    get_interpolated_asset_property_values_tool,
    list_bulk_import_jobs_tool,
)
from awslabs.aws_iot_sitewise_mcp_server.tools.sitewise_gateways import (
    associate_time_series_to_asset_property_tool,
    create_gateway_tool,
    delete_gateway_tool,
    delete_time_series_tool,
    describe_gateway_capability_configuration_tool,
    describe_gateway_tool,
    describe_time_series_tool,
    disassociate_time_series_from_asset_property_tool,
    list_gateways_tool,
    list_time_series_tool,
    update_gateway_capability_configuration_tool,
    update_gateway_tool,
)
from awslabs.aws_iot_sitewise_mcp_server.tools.sitewise_metadata_transfer import (
    cancel_metadata_transfer_job_tool,
    create_bulk_import_schema_tool,
    create_metadata_transfer_job_tool,
    get_metadata_transfer_job_tool,
    list_metadata_transfer_jobs_tool,
)
from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.tools import Tool
from typing import Any, Dict


# Server instruction constants
WRITE_ENABLED_INSTRUCTIONS = """WRITE ENABLED - AWS IoT SiteWise MCP Server

Full functionality enabled for industrial IoT asset management, data ingestion,
monitoring, and analytics.

This server has write operations ENABLED. Use with appropriate AWS permissions.
Use 'get_sitewise_server_mode' tool to check available capabilities."""

READ_ONLY_INSTRUCTIONS = """READ-ONLY MODE - AWS IoT SiteWise MCP Server

Enhanced security mode with write operations disabled.

💡 To enable write operations: Set SITEWISE_MCP_ALLOW_WRITES=True environment
variable. Use 'get_sitewise_server_mode' tool to check available
capabilities."""

# All available tools (will be filtered based on readonly metadata and
# allow_writes setting)
all_tools = [
    create_asset_tool,
    describe_asset_tool,
    list_assets_tool,
    update_asset_tool,
    delete_asset_tool,
    associate_assets_tool,
    disassociate_assets_tool,
    list_associated_assets_tool,
    create_asset_model_tool,
    describe_asset_model_tool,
    list_asset_models_tool,
    update_asset_model_tool,
    delete_asset_model_tool,
    list_asset_model_properties_tool,
    create_asset_model_composite_model_tool,
    batch_put_asset_property_value_tool,
    get_asset_property_value_tool,
    get_asset_property_value_history_tool,
    get_asset_property_aggregates_tool,
    get_interpolated_asset_property_values_tool,
    batch_get_asset_property_value_tool,
    batch_get_asset_property_value_history_tool,
    batch_get_asset_property_aggregates_tool,
    create_bulk_import_job_tool,
    create_buffered_ingestion_job_tool,
    create_bulk_import_iam_role_tool,
    list_bulk_import_jobs_tool,
    describe_bulk_import_job_tool,
    execute_query_tool,
    create_gateway_tool,
    describe_gateway_tool,
    list_gateways_tool,
    update_gateway_tool,
    delete_gateway_tool,
    describe_gateway_capability_configuration_tool,
    update_gateway_capability_configuration_tool,
    list_time_series_tool,
    describe_time_series_tool,
    associate_time_series_to_asset_property_tool,
    disassociate_time_series_from_asset_property_tool,
    delete_time_series_tool,
    describe_default_encryption_configuration_tool,
    put_default_encryption_configuration_tool,
    describe_logging_options_tool,
    put_logging_options_tool,
    describe_storage_configuration_tool,
    put_storage_configuration_tool,
    create_bulk_import_schema_tool,
    create_metadata_transfer_job_tool,
    cancel_metadata_transfer_job_tool,
    get_metadata_transfer_job_tool,
    list_metadata_transfer_jobs_tool,
]


def get_sitewise_server_mode() -> Dict[str, Any]:
    """Get the current SiteWise server mode and available capabilities.

    This tool helps users understand what operations are available
    and provides guidance for enabling write operations if needed.

    Returns:
        Dictionary containing server mode information and capabilities
    """
    allow_writes = os.environ.get('SITEWISE_MCP_ALLOW_WRITES', 'False').lower() == 'true'

    readonly_count = sum(1 for tool in all_tools if is_readonly_tool(tool.fn))
    write_count = len(all_tools) - readonly_count

    # Add 1 for get_sitewise_server_mode tool which is always available
    total_readonly = readonly_count + 1
    total_available = total_readonly + (write_count if allow_writes else 0)

    if allow_writes:
        mode_info = {
            'success': True,
            'mode': 'WRITE_ENABLED',
            'readonly_tools': total_readonly,
            'write_tools': write_count,
            'total_tools': total_available,
        }
    else:
        mode_info = {
            'success': True,
            'mode': 'READ_ONLY',
            'readonly_tools': total_readonly,
            'write_tools': 0,
            'total_tools': total_readonly,
            'enable_writes': ('Set SITEWISE_MCP_ALLOW_WRITES=True environment variable'),
        }

    return mode_info


async def signal_handler(scope: CancelScope):
    """Handle SIGINT and SIGTERM signals asynchronously.

    The anyio.open_signal_receiver returns an async generator that yields
    signal numbers whenever a specified signal is received. The async for
    loop waits for signals and processes them as they arrive.
    """
    with open_signal_receiver(signal.SIGINT, signal.SIGTERM) as signals:
        async for _ in signals:  # Shutting down regardless of signal type
            print('Shutting down MCP server...')
            # Force immediate exit since MCP blocks on stdio.
            # You can also use scope.cancel(), but it means after Ctrl+C,
            # you need to press another 'Enter' to unblock the stdio.
            os._exit(0)


async def run_server():
    """Run the MCP server with signal handling."""
    # Check if writes are allowed
    allow_writes = os.environ.get('SITEWISE_MCP_ALLOW_WRITES', 'False').lower() == 'true'

    # Update instructions based on mode
    instructions = WRITE_ENABLED_INSTRUCTIONS if allow_writes else READ_ONLY_INSTRUCTIONS

    mcp = FastMCP(
        name='sitewise',
        instructions=instructions,
    )

    mcp._mcp_server.version = __version__

    # Filter tools based on readonly metadata and allow_writes setting
    tools_to_register = []
    readonly_count = 0
    write_count = 0

    for tool in all_tools:
        if is_readonly_tool(tool.fn):
            # Always register read-only tools
            tools_to_register.append(tool)
            readonly_count += 1
        elif allow_writes:
            # Only register write tools if writes are enabled
            tools_to_register.append(tool)
            write_count += 1
        # Skip write tools if allow_writes is False

    # Create the server mode tool
    get_sitewise_server_mode_tool = Tool.from_function(
        fn=get_sitewise_server_mode,
        name='get_sitewise_server_mode',
        description=(
            'Get the current SiteWise server mode and available capabilities. '
            'Use this to understand what operations are available and how to '
            'enable write operations if needed.'
        ),
    )

    # Add the server mode tool (always available)
    mcp.add_tool(
        get_sitewise_server_mode_tool.fn,
        get_sitewise_server_mode_tool.name,
        get_sitewise_server_mode_tool.description,
        str(get_sitewise_server_mode_tool.annotations or ''),
    )

    # Register filtered tools
    for tool in tools_to_register:
        mcp.add_tool(tool.fn, tool.name, tool.description, str(tool.annotations or ''))

    # Print registration summary
    total_tools = len(tools_to_register) + 1  # +1 for get_sitewise_server_mode
    if allow_writes:
        print(
            f'Registered {readonly_count + 1} read-only tools '
            f'(including get_sitewise_server_mode) and {write_count} '
            f'write tools ({total_tools} total)'
        )
    else:
        print(
            f'Registered {readonly_count + 1} read-only tools only '
            f'(including get_sitewise_server_mode) ({total_tools} total)'
        )

    # Add prompts based on mode
    readonly_prompts = [
        asset_hierarchy_visualization_prompt,
        data_exploration_helper_prompt,
    ]

    # Always add read-only prompts
    for prompt in readonly_prompts:
        mcp.add_prompt(prompt)

    # Add data ingestion prompt only in write mode
    if allow_writes:
        mcp.add_prompt(data_ingestion_helper_prompt)
        mcp.add_prompt(bulk_import_workflow_helper_prompt)

    async with create_task_group() as tg:
        tg.start_soon(signal_handler, tg.cancel_scope)
        # proceed with starting the actual application logic
        await mcp.run_stdio_async()


def main():
    """Entry point for the MCP server."""
    run(run_server)


if __name__ == '__main__':
    main()
