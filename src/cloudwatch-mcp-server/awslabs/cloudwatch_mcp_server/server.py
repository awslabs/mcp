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

"""awslabs cloudwatch-logs MCP Server implementation."""

from awslabs.cloudwatch_mcp_server.cloudwatch_logs.tools import CloudWatchLogsTools
from loguru import logger
from mcp.server.fastmcp import FastMCP


mcp = FastMCP(
    'awslabs.cloudwatch-mcp-server',
    instructions='Use this MCP server to run read-only commands and analyze CloudWatchLogs. Supports discovering logs groups as well as running CloudWatch Log Insight Queries. With CloudWatch Logs Insights, you can interactively search and analyze your log data in Amazon CloudWatch Logs and perform queries to help you more efficiently and effectively respond to operational issues.',
    dependencies=[
        'pydantic',
        'loguru',
    ],
)

# Initialize and register CloudWatch Logs tools
try:
    cloudwatch_logs_tools = CloudWatchLogsTools()
    cloudwatch_logs_tools.register(mcp)
    logger.info('CloudWatch Logs tools registered successfully')
except Exception as e:
    logger.error(f'Error initializing CloudWatch Logs tools: {str(e)}')
    raise


def main():
    """Run the MCP server."""
    mcp.run()
    logger.info('CloudWatch MCP server started')


if __name__ == '__main__':
    main()
