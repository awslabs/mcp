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
    format_aws_response,
    handle_aws_error,
)
from mypy_boto3_pi import PIClient
from pydantic import Field
from typing import Annotated, List


async def list_performance_reports(
    dbi_resource_identifier: Annotated[
        str, Field(description='The resource identifier for the DB instance')
    ],
    pi_client: PIClient,
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
        response = pi_client.list_performance_analysis_reports(
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


async def read_performance_report(
    dbi_resource_identifier: Annotated[
        str, Field(description='The resource identifier for the DB instance')
    ],
    report_id: str,
    pi_client: PIClient,
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
        response = pi_client.get_performance_analysis_report(
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
