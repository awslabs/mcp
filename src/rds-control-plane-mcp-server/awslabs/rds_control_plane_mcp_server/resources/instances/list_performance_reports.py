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

"""List Performance Report handler for the RDS Control Plane MCP Server."""

import json
from awslabs.rds_control_plane_mcp_server.common.config import max_items
from awslabs.rds_control_plane_mcp_server.common.constants import (
    RESOURCE_PREFIX_DB_PERFORMANCE_REPORT,
)
from awslabs.rds_control_plane_mcp_server.common.models import (
    PerformanceReportListModel,
    PerformanceReportSummary,
)
from awslabs.rds_control_plane_mcp_server.common.utils import (
    convert_datetime_to_string,
    handle_aws_error,
)
from mypy_boto3_pi import PIClient
from pydantic import Field
from typing import List


LIST_PERFORMANCE_REPORTS_DOCSTRING = """List all available performance reports for a specific Amazon RDS instance.

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


class ListPerformanceReportHandler:
    """Handler for RDS Performance Report listing operations in the RDS MCP Server.

    This class provides tools for discovering and getting inventory information about
    RDS performance reports avaible for a specific DB Instance.
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
            uri='aws-rds://db-instance/{dbi_resource_identifier}/performance_report',
            name='ListPerformanceReports',
            mime_type='application/json',
            description=LIST_PERFORMANCE_REPORTS_DOCSTRING,
        )(self.list_performance_reports)

    async def list_performance_reports(
        self,
        dbi_resource_identifier: str = Field(
            description='The resource identifier for the DB instance. This is the DbiResourceId returned by the ListDBInstances resource'
        ),
    ) -> str:
        """Retrieve all performance reports for a given DB instance.

        Args:
            dbi_resource_identifier (str): The DB instance resource identifier
            pi_client (PIClient): The AWS Performance Insights client

        Returns:
            List[PerformanceReport]: A list of performance reports for the DB instance
        """
        reports: List[PerformanceReportSummary] = []

        try:
            # Only get up to max_items reports
            response = self.pi_client.list_performance_analysis_reports(
                ServiceType='RDS', Identifier=dbi_resource_identifier, MaxResults=max_items
            )

            for report in response.get('AnalysisReports', []):
                reports.append(
                    PerformanceReportSummary(
                        analysis_report_id=report.get('AnalysisReportId'),
                        create_time=convert_datetime_to_string(report.get('CreateTime')),
                        start_time=convert_datetime_to_string(report.get('StartTime')),
                        end_time=convert_datetime_to_string(report.get('EndTime')),
                        status=report.get('Status'),
                    )
                )

            result = PerformanceReportListModel(
                reports=reports,
                count=len(reports),
                resource_uri=RESOURCE_PREFIX_DB_PERFORMANCE_REPORT.format(dbi_resource_identifier),
            )
            return json.dumps(result.model_dump(), indent=2)
        except Exception as e:
            error_result = await handle_aws_error(
                'list_performance_analysis_reports({dbi_resource_identifier})', e, None
            )
            return json.dumps(error_result, indent=2)
