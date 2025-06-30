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

"""Resource for listing availble RDS DB Performance Reports."""

import json
from ...common.connection import PIConnectionManager
from ...common.constants import RESOURCE_PREFIX_DB_PERFORMANCE_REPORT
from ...common.decorator import handle_exceptions
from ...common.server import mcp
from ...common.utils import convert_datetime_to_string
from ...context import Context
from pydantic import BaseModel, Field
from typing import List, Literal


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


class PerformanceReportSummary(BaseModel):
    """Performance analysis report information.

    This model represents an Amazon RDS performance analysis report with its metadata,
    including report ID, creation time, time range of the analysis, and status.

    Attributes:
        analysis_report_id: Unique identifier for the performance report.
        create_time: Timestamp when the report was created.
        start_time: Start time of the performance analysis period.
        end_time: End time of the performance analysis period.
        status: Current status of the report (RUNNING, SUCCEEDED, or FAILED).
    """

    # Models the AnalysisReportSummaryTypeDef class which has no required fields
    analysis_report_id: str | None = Field(
        None, description='Unique identifier for the performance report'
    )
    create_time: str | None = Field(None, description='Time when the report was created')
    start_time: str | None = Field(None, description='Start time of the analysis period')
    end_time: str | None = Field(None, description='End time of the analysis period')
    status: Literal['RUNNING', 'SUCCEEDED', 'FAILED'] | None = None


class PerformanceReportListModel(BaseModel):
    """DB cluster list model."""

    reports: List[PerformanceReportSummary] = Field(
        default_factory=list, description='List of performance reports for a RDS instance'
    )
    count: int = Field(description='Total number of performance reports')
    resource_uri: str = Field(description='The resource URI for the performance reports')


@mcp.resource(
    uri='aws-rds://db-instance/{dbi_resource_identifier}/performance_report',
    name='ListPerformanceReports',
    mime_type='application/json',
    description=LIST_PERFORMANCE_REPORTS_DOCSTRING,
)
@handle_exceptions
async def list_performance_reports(
    dbi_resource_identifier: str = Field(
        ...,
        description='The resource identifier for the DB instance. This is the DbiResourceId returned by the ListDBInstances resource',
    ),
) -> str:
    """Retrieve all performance reports for a given DB instance.

    Args:
        dbi_resource_identifier: The DB instance resource identifier

    Returns:
        JSON string with list of performance reports
    """
    pi_client = PIConnectionManager.get_connection()
    reports: List[PerformanceReportSummary] = []

    # Only get up to max_items reports
    response = pi_client.list_performance_analysis_reports(
        ServiceType='RDS', Identifier=dbi_resource_identifier, MaxResults=Context.max_items()
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
