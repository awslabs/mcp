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

"""This module provides functions to list and read performance reports for a given DB instance."""

from .constants import MAX_ITEMS
from awslabs.rds_control_plane_mcp_server.models import PerformanceReportSummary
from awslabs.rds_control_plane_mcp_server.utils import format_aws_response, handle_aws_error
from mypy_boto3_pi import PIClient
from pydantic import Field
from typing import Annotated, Any, List, Union


async def list_performance_reports(
    dbi_resource_identifier: Annotated[
        str, Field(description='The resource identifier for the DB instance')
    ],
    pi_client: PIClient,
) -> Union[List[PerformanceReportSummary], dict[str, Any]]:
    """Retrieve all performance reports for a given DB instance.

    Args:
        dbi_resource_identifier (str): The DB instance resource identifier
        pi_client (PIClient): The AWS Performance Insights client

    Returns:
        List[PerformanceReport]: A list of performance reports for the DB instance
    """
    reports: List[PerformanceReportSummary] = []

    try:
        # Only get up to MAX_ITEMS reports
        response = pi_client.list_performance_analysis_reports(
            ServiceType='RDS', Identifier=dbi_resource_identifier, MaxResults=MAX_ITEMS
        )

        for report in response.get('AnalysisReports', []):
            reports.append(
                PerformanceReportSummary(
                    analysis_report_id=report.get('AnalysisReportId'),
                    create_time=report.get('CreateTime'),
                    start_time=report.get('StartTime'),
                    end_time=report.get('EndTime'),
                    status=report.get('Status'),
                )
            )

        return reports
    except Exception as e:
        return await handle_aws_error(
            'list_performance_analysis_reports({dbi_resource_identifier})', e, None
        )


async def read_performance_report(
    dbi_resource_identifier: Annotated[
        str, Field(description='The resource identifier for the DB instance')
    ],
    report_id: str,
    pi_client: PIClient,
) -> dict[str, Any]:
    """Retrieve a specific performance report from AWS Performance Insights.

    Args:
        dbi_resource_identifier (str): The resource identifier for the DB instance
        report_id (str): The ID of the performance report to read
        pi_client (PIClient): The AWS Performance Insights client

    Returns:
        dict: The complete performance report data including metrics, analysis, and recommendations
    """
    try:
        response = pi_client.get_performance_analysis_report(
            ServiceType='RDS',
            Identifier=dbi_resource_identifier,
            AnalysisReportId=report_id,
            TextFormat='MARKDOWN',
        )
    except Exception as e:
        return await handle_aws_error(
            f'get_performance_analysis_report({dbi_resource_identifier}, {report_id})', e, None
        )

    # Convert TypedDict to Dict before formatting
    formatted_response = format_aws_response(dict(response))
    return formatted_response.get('AnalysisReport', {})
