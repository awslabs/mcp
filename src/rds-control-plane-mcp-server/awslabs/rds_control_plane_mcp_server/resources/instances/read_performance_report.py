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

"""Read Performance Report handler for the RDS Control Plane MCP Server."""

import json
from awslabs.rds_control_plane_mcp_server.common.utils import format_aws_response, handle_aws_error
from mypy_boto3_pi import PIClient
from pydantic import Field


READ_PERFORMANCE_REPORT_RESOURCE_DESCRIPTION = """Read the contents of a specific performance report for a specific Amazon RDS instance.

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


class ReadPerformanceReportHandler:
    """Handler for RDS Performance Report reading operations in the RDS MCP Server.

    This class provides tools for reading a previously generated
    RDS performance reports.
    """

    def __init__(self, mcp, pi_client: PIClient):
        """Initialize the RDS Performance Report handler.

        Args:
            mcp: The MCP server instance
            pi_client: The AWS Performance Insights client instance
        """
        self.mcp = mcp
        self.pi_client = pi_client

        # Register resources
        self.mcp.resource(
            uri='aws-rds://db-instance/{dbi_resource_identifier}/performance_report/{report_id}',
            name='ReadPerformanceReport',
            mime_type='application/json',
            description=READ_PERFORMANCE_REPORT_RESOURCE_DESCRIPTION,
        )(self.read_performance_report)

    async def read_performance_report(
        self,
        dbi_resource_identifier: str = Field(
            description='The AWS Region-unique, immutable identifier for the DB instance. This is the DbiResourceId returned by the ListDBInstances resource'
        ),
        report_id: str = Field(
            ..., description='The unique identifier of the performance analysis report to retrieve'
        ),
    ) -> str:
        """Retrieve a specific performance report from AWS Performance Insights.

        Args:
            dbi_resource_identifier (str): The resource identifier for the DB instance
            report_id (str): The ID of the performance report to read
            pi_client (PIClient): The AWS Performance Insights client

        Returns:
            dict: The complete performance report data including metrics, analysis, and recommendations
        """
        try:
            response = self.pi_client.get_performance_analysis_report(
                ServiceType='RDS',
                Identifier=dbi_resource_identifier,
                AnalysisReportId=report_id,
                TextFormat='MARKDOWN',
            )
        except Exception as e:
            error_result = await handle_aws_error(
                f'get_performance_analysis_report({dbi_resource_identifier}, {report_id})', e, None
            )
            return json.dumps(error_result, indent=2)

        # Convert TypedDict to Dict before formatting
        formatted_response = format_aws_response(dict(response))
        analysis_report = formatted_response.get('AnalysisReport', {})
        return json.dumps(analysis_report)
