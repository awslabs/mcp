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

"""awslabs rds-control-plane MCP Server implementation."""

import os
import sys
from awslabs.rds_control_plane_mcp_server.clients import (
    get_pi_client,
    get_rds_client,
)
from awslabs.rds_control_plane_mcp_server.logs import list_db_log_files
from awslabs.rds_control_plane_mcp_server.models import DBLogFileSummary, PerformanceReportSummary
from awslabs.rds_control_plane_mcp_server.reports import (
    list_performance_reports,
    read_performance_report,
)
from awslabs.rds_control_plane_mcp_server.resource_docstrings import (
    LIST_DB_LOG_FILES_DOCSTRING,
    LIST_PERFORMANCE_REPORTS_DOCSTRING,
    READ_PERFORMANCE_REPORT_DOCSTRING,
)
from awslabs.rds_control_plane_mcp_server.utils import apply_docstring
from loguru import logger
from mcp.server.fastmcp import FastMCP
from pydantic import Field
from typing import Any, List, Union


# TODO: Update instructions after PR to add discovery tools has been merged
mcp = FastMCP(
    'awslabs.rds-control-plane-mcp-server',
    instructions='Instructions for using this rds-control-plane MCP server. This can be used by clients to improve the LLM'
    's understanding of available tools, resources, etc. It can be thought of like a '
    'hint'
    ' to the model. For example, this information MAY be added to the system prompt. Important to be clear, direct, and detailed.',
    dependencies=[
        'pydantic',
        'loguru',
        'boto3',
    ],
)

# Remove all default handlers then add our own
logger.remove()
logger.add(sys.stderr, level='INFO')

global pi_client
global rds_client
global cloudwatch_client

try:
    pi_client = get_pi_client(
        region_name=os.getenv('AWS_REGION'),
        profile_name=os.getenv('AWS_PROFILE'),
    )
    rds_client = get_rds_client(
        region_name=os.getenv('AWS_REGION'),
        profile_name=os.getenv('AWS_PROFILE'),
    )
except Exception as e:
    logger.error(f'Error getting RDS or PI clients: {e}')
    raise e


@mcp.resource(
    uri='aws-rds://db-instance/{dbi_resource_identifier}/performance_report',
    name='ListPerformanceReports',
    mime_type='application/json',
)
@apply_docstring(LIST_PERFORMANCE_REPORTS_DOCSTRING)
async def list_performance_reports_resource(
    dbi_resource_identifier: str = Field(
        ..., description='The resource identifier for the DB instance'
    ),
) -> Union[List[PerformanceReportSummary], dict[str, Any]]:
    """List all available performance reports for a specific Amazon RDS instance."""
    return await list_performance_reports(
        dbi_resource_identifier,
        pi_client,
    )


@mcp.resource(
    uri='aws-rds://db-instance/{dbi_resource_identifier}/performance_report/{report_identifier}',
    name='ReadPerformanceReport',
    mime_type='text/plain',
)
@apply_docstring(READ_PERFORMANCE_REPORT_DOCSTRING)
async def read_performance_report_resource(
    dbi_resource_identifier: str = Field(
        ..., description='The resource identifier for the DB instance'
    ),
    report_identifier: str = Field(
        ..., description='The identifier for the report you want to read'
    ),
) -> dict[str, Any]:
    """Read the contents of a specific performance report for a specific Amazon RDS instance."""
    return await read_performance_report(
        dbi_resource_identifier=dbi_resource_identifier,
        report_id=report_identifier,
        pi_client=pi_client,
    )


@mcp.resource(
    uri='aws-rds://db-instance/{db_instance_identifier}/log',
    name='ListDBLogFiles',
    mime_type='application/json',
)
@apply_docstring(LIST_DB_LOG_FILES_DOCSTRING)
async def list_db_log_files_resource(
    db_instance_identifier: str = Field(..., description='The identifier for the DB instance'),
) -> Union[List[DBLogFileSummary], dict[str, Any]]:
    """List all available log files for a specific Amazon RDS instance."""
    return await list_db_log_files(
        db_instance_identifier=db_instance_identifier, rds_client=rds_client
    )


def main():
    """Run the MCP server with CLI argument support."""
    mcp.run()


if __name__ == '__main__':
    main()
