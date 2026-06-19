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

"""awslabs Amazon Connect MCP Server implementation."""

from awslabs.amazon_connect_mcp_server.connect_admin.tools import ConnectAdminTools
from awslabs.amazon_connect_mcp_server.connect_historical.tools import ConnectHistoricalTools
from awslabs.amazon_connect_mcp_server.connect_realtime.tools import ConnectRealtimeTools
from loguru import logger
from mcp.server.fastmcp import FastMCP


mcp = FastMCP(
    'awslabs.amazon-connect-mcp-server',
    instructions=(
        'Use this MCP server to run read-only commands and generate realtime and '
        'historical reports from Amazon Connect contact centers using natural language. '
        'Start by discovering resources with list_connect_instances, then list_queues, '
        'list_agents, and list_routing_profiles to resolve the identifiers used as filters. '
        'Use get_current_metric_data and get_current_agent_status for realtime operational '
        'reporting (contacts in queue, oldest contact age, agent availability and status). '
        'Use get_historical_metric_data for historical reporting over the last 90 days '
        '(contacts handled/abandoned, average handle time, service level, occupancy, etc.) '
        'grouped by queue, channel, agent, or routing profile. All tools accept optional '
        'region and profile_name arguments and operate read-only.'
    ),
    dependencies=[
        'boto3',
        'pydantic',
        'loguru',
    ],
)

# Initialize and register Amazon Connect tools
try:
    connect_admin_tools = ConnectAdminTools()
    connect_admin_tools.register(mcp)
    logger.info('Amazon Connect administration tools registered successfully')

    connect_realtime_tools = ConnectRealtimeTools()
    connect_realtime_tools.register(mcp)
    logger.info('Amazon Connect realtime tools registered successfully')

    connect_historical_tools = ConnectHistoricalTools()
    connect_historical_tools.register(mcp)
    logger.info('Amazon Connect historical tools registered successfully')
except Exception as e:
    logger.error(f'Error initializing Amazon Connect tools: {str(e)}')
    raise


def main():
    """Run the MCP server."""
    logger.info('Starting Amazon Connect MCP server')
    mcp.run()


if __name__ == '__main__':
    main()
