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

"""Resource for reading RDS Performance Reports for a RDS DB Instance."""

import asyncio
from ...common.connection import PIConnectionManager
from ...common.decorators.handle_exceptions import handle_exceptions
from ...common.server import mcp
from datetime import datetime
from loguru import logger
from pydantic import BaseModel, Field
from typing import Any, Dict, List


READ_PERFORMANCE_REPORT_RESOURCE_DESCRIPTION = """Read the contents of a specific performance report for a specific Amazon RDS instance.

This resource retrieves detailed performance analysis data from a specific Performance Insights report, containing information about database performance issues, root cause analysis, top SQL queries causing load, wait events, and recommended actions for optimization.
"""


class AnalysisReport(BaseModel):
    """Model representing a complete performance analysis report."""

    AnalysisReportId: str
    Identifier: str
    ServiceType: str
    CreateTime: datetime
    StartTime: datetime
    EndTime: datetime
    Status: str
    Insights: List[Dict[str, Any]] = []


@mcp.resource(
    uri='aws-rds://db-instance/{dbi_resource_identifier}/performance_report/{report_id}',
    name='ReadPerformanceReport',
    mime_type='application/json',
    description=READ_PERFORMANCE_REPORT_RESOURCE_DESCRIPTION,
)
@handle_exceptions
async def read_performance_report(
    dbi_resource_identifier: str = Field(
        ...,
        description='The AWS Region-unique, immutable identifier for the DB instance. This is the DbiResourceId returned by the ListDBInstances resource',
    ),
    report_id: str = Field(
        ..., description='The unique identifier of the performance analysis report to retrieve'
    ),
) -> AnalysisReport:
    """Retrieve a specific performance report from AWS Performance Insights.

    Args:
        dbi_resource_identifier: The resource identifier for the DB instance
        report_id: The ID of the performance report to read

    Returns:
        JSON string containing the complete performance report data including metrics, analysis, and recommendations
    """
    logger.info(
        f'Retrieving performance report {report_id} for DB instance {dbi_resource_identifier}'
    )
    pi_client = PIConnectionManager.get_connection()

    params = {
        'ServiceType': 'RDS',
        'Identifier': dbi_resource_identifier,
        'AnalysisReportId': report_id,
        'TextFormat': 'MARKDOWN',
    }

    response = await asyncio.to_thread(pi_client.get_performance_analysis_report, **params)

    analysis_report = response.get('AnalysisReport', {})
    return AnalysisReport.model_validate(analysis_report)
