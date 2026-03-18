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

"""awslabs SSM for SAP MCP Server implementation."""

from awslabs.aws_systems_manager_for_sap_mcp_server.ssm_sap_applications.tools import (
    SSMSAPApplicationTools,
)
from awslabs.aws_systems_manager_for_sap_mcp_server.ssm_sap_config_checks.tools import (
    SSMSAPConfigCheckTools,
)
from awslabs.aws_systems_manager_for_sap_mcp_server.ssm_sap_scheduling.tools import (
    SSMSAPSchedulingTools,
)
from loguru import logger
from mcp.server.fastmcp import FastMCP


mcp = FastMCP(
    'awslabs.aws-systems-manager-for-sap-mcp-server',
    instructions=(
        'Use this MCP server to manage SAP applications registered with '
        'AWS Systems Manager for SAP. Supports listing and inspecting SAP applications, '
        'running and reviewing configuration checks, and scheduling recurring operations '
        '(configuration checks, start/stop) via Amazon EventBridge Scheduler. '
        'All tools support multi-region and multi-profile AWS access.'
    ),
    dependencies=[
        'pydantic',
        'loguru',
    ],
)

# Initialize and register tool modules
try:
    application_tools = SSMSAPApplicationTools()
    application_tools.register(mcp)
    logger.info('SSM SAP Application tools registered successfully')

    config_check_tools = SSMSAPConfigCheckTools()
    config_check_tools.register(mcp)
    logger.info('SSM SAP Configuration Check tools registered successfully')

    scheduling_tools = SSMSAPSchedulingTools()
    scheduling_tools.register(mcp)
    logger.info('SSM SAP Scheduling tools registered successfully')
except Exception as e:
    logger.error(f'Error initializing SSM SAP tools: {str(e)}')
    raise


def main():
    """Run the MCP server."""
    mcp.run()
    logger.info('SSM for SAP MCP server started')


if __name__ == '__main__':
    main()
