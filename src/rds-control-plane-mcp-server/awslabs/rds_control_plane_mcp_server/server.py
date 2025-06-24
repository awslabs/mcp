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
from .clients import (
    get_pi_client,
    get_rds_client,
)
from .logs import list_db_log_files
from .models import DBLogFileSummary, PerformanceReportSummary
from .reports import list_performance_reports, read_performance_report
from loguru import logger
from mcp.server.fastmcp import FastMCP
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
async def list_performance_reports_resource(
    dbi_resource_identifier: str,
) -> Union[List[PerformanceReportSummary], dict[str, Any]]:
    """List all available performance reports for a specific Amazon RDS instance.

    <use_case>
    Use this resource to discover all available Performance Insights analysis reports for a specific RDS database instance.
    Performance reports provide detailed analysis of database performance issues, helping you identify bottlenecks and optimization opportunities.
    </use_case>

    <important_notes>
    1. The response provides information about performance analysis reports generated for the instance
    2. You must provide a valid DB resource identifier to retrieve reports
    3. Performance reports are only available for instances with Performance Insights enabled
    4. Reports are provided in chronological order with the most recent reports first
    5. Use the `aws-rds://db-instance/{dbi_resource_identifier}/performance_report/{report_identifier}` resource to get detailed information about a specific report
    </important_notes>

    ## Response structure
    Returns an array of performance report objects, each containing:
    - `analysis_report_id`: Unique identifier for the performance report (string)
    - `create_time`: Time when the report was created (datetime)
    - `start_time`: Start time of the analysis period (datetime)
    - `end_time`: End time of the analysis period (datetime)
    - `status`: Current status of the report (RUNNING, SUCCEEDED, or FAILED) (string)
    - `tags`: List of tags attached to the report (array of key-value pairs)

    <examples>
    Example usage scenarios:
    1. Performance monitoring:
       - List all available performance reports to identify periods of potential performance issues
       - Track reports generated during specific time periods of interest

    2. Preparation for optimization:
       - Find specific report identifiers for detailed performance analysis
       - Monitor the status of recently generated performance reports
       - Identify long-running or failed reports that may need investigation
    </examples>
    """
    return await list_performance_reports(
        dbi_resource_identifier,
        pi_client,
    )


@mcp.resource(
    uri='aws-rds://db-instance/{dbi_resource_identifier}/performance_report/{report_identifier}',
    name='ReadPerformanceReport',
    mime_type='text/plain',
)
async def read_performance_report_resource(
    dbi_resource_identifier: str, report_identifier: str
) -> dict[str, Any]:
    """Read the contents of a specific performance report for a specific Amazon RDS instance.

    <use_case>
    Use this resource to retrieve detailed performance analysis data from a specific Performance Insights report.
    These reports contain comprehensive information about database performance issues, including root cause analysis,
    top SQL queries causing load, wait events, and recommended actions for performance optimization.
    </use_case>

    <important_notes>
    1. You must provide both a valid DB instance identifier and report identifier
    2. The report must be in a SUCCEEDED status to be fully readable
    3. Reports in RUNNING status may return partial results
    4. Reports in FAILED status will return error information about why the analysis failed
    5. Large reports may contain extensive data about the performance issues analyzed
    </important_notes>

    ## Response structure
    Returns a detailed performance report object containing:
    - `AnalysisReportId`: Unique identifier for the performance report (string)
    - `ServiceType`: Service type (always 'RDS' for RDS instances) (string)
    - `CreateTime`: Time when the report was created (datetime)
    - `StartTime`: Start time of the analysis period (datetime)
    - `EndTime`: End time of the analysis period (datetime)
    - `Status`: Current status of the report (RUNNING, SUCCEEDED, or FAILED) (string)
    - `AnalysisData`: The detailed performance analysis (object)
      - May include metrics, anomalies, query analysis, and recommendations
    - `Tags`: List of tags attached to the report (array of key-value pairs)

    <examples>
    Example usage scenarios:
    1. Performance troubleshooting:
       - Analyze root causes of performance bottlenecks during a specific period
       - Identify top resource-consuming SQL queries during performance degradation
       - Review wait events that contributed to slowdowns

    2. Performance optimization:
       - Review recommended actions to improve database performance
       - Analyze patterns in resource usage to guide optimization efforts
       - Document performance issues for change management or postmortem analysis
    </examples>
    """
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
async def list_db_log_files_resource(
    db_instance_identifier: str,
) -> Union[List[DBLogFileSummary], dict[str, Any]]:
    """List all available log files for a specific Amazon RDS instance.

    <use_case>
    Use this resource to discover all available log files for a specific RDS database instance.
    Log files provide detailed logs of database activities, helping you troubleshoot issues and monitor performance.
    </use_case>

    <important_notes>
    1. The response provides information about log files generated for the instance
    2. You must provide a valid DB instance identifier to retrieve log files
    3. Log files are only available for instances with logs enabled
    4. Log files are provided in chronological order with the most recent log files first
    5. Use the `aws-rds://db-instance/{dbi_resource_identifier}/log/{log_file_identifier}` resource to get detailed information about a specific log file
    </important_notes>

    ## Response structure
    Returns an array of log file objects, each containing:
    - `log_file_identifier`: Unique identifier for the log file (string)
    - `last_write_time`: Time when the log file was last written to (datetime)
    - `size`: Size of the log file in bytes (integer)

    <examples>
    Example usage scenarios:
    1. Log analysis:
       - List all available log files to identify periods of potential issues
       - Track log files generated during specific time periods of interest

    2. Log troubleshooting:
       - Find specific log file identifiers for detailed log analysis
       - Monitor the status of recently generated log files
       - Identify long-running or failed log files that may need investigation
    </examples>
    """
    return await list_db_log_files(
        db_instance_identifier=db_instance_identifier, rds_client=rds_client
    )


def main():
    """Run the MCP server with CLI argument support."""
    mcp.run()


if __name__ == '__main__':
    main()
