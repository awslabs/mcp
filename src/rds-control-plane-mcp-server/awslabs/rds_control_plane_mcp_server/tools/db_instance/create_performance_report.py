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

"""Performance report creation tool for RDS instances."""

from ...common.connection import PIConnectionManager
from ...common.decorators.handle_exceptions import handle_exceptions
from ...common.decorators.readonly_check import readonly_check
from ...common.server import mcp
from datetime import datetime, timedelta
from typing import Optional


# Constants
MIN_DURATION_MINUTES = 5
MAX_DURATION_DAYS = 6
DEFAULT_START_DAYS_AGO = 5
DEFAULT_END_DAYS_AGO = 2

REPORT_CREATION_SUCCESS_RESPONSE = """Performance analysis report creation has been initiated successfully.

The report ID is: {}

This process is asynchronous and will take some time to complete. Once generated,
you can access the report details using the Performance Insights dashboard or the aws-rds://db-instance/{}/performance_report resource.

Note: Report generation typically takes a few minutes depending on the time range selected.
"""

CREATE_PERF_REPORT_TOOL_DESCRIPTION = """Create a performance report for an RDS instance.

This tool creates a performance analysis report for a specific RDS instance over a time period that can range from 5 minutes to 6 days, helping identify performance bottlenecks, analyze database behavior patterns, and support optimization efforts.

<warning>
This operation will fail if running in read-only mode. The analysis period must be between 5 minutes and 6 days, with at least 24 hours of performance data before the analysis start time.
</warning>
"""


def _parse_datetime(time_str: Optional[str], default_days_ago: int) -> datetime:
    """Parse ISO8601 datetime string or return default time.

    Args:
        time_str: ISO8601 formatted datetime string or None
        default_days_ago: Days to subtract from now for default value

    Returns:
        datetime: Parsed datetime object

    Raises:
        ValueError: If time string format is invalid
    """
    if not time_str:
        return datetime.now() - timedelta(days=default_days_ago)

    if time_str.endswith('Z'):
        time_str = time_str.replace('Z', '+00:00')

    try:
        return datetime.fromisoformat(time_str)
    except ValueError as e:
        raise ValueError(f'Invalid time format: {e}')


def _validate_time_range(start: datetime, end: datetime) -> None:
    """Validate that the time range meets requirements.

    Args:
        start: Start datetime to validate
        end: End datetime to validate

    Raises:
        ValueError: If time range is invalid
    """
    if start >= end:
        raise ValueError('start_time must be before end_time')

    duration = end - start
    if duration < timedelta(minutes=MIN_DURATION_MINUTES):
        raise ValueError(f'Time range must be at least {MIN_DURATION_MINUTES} minutes')
    if duration > timedelta(days=MAX_DURATION_DAYS):
        raise ValueError(f'Time range cannot exceed {MAX_DURATION_DAYS} days')


@mcp.tool(name='CreatePerformanceReport', description=CREATE_PERF_REPORT_TOOL_DESCRIPTION)
@handle_exceptions
@readonly_check
async def create_performance_report(
    dbi_resource_identifier: str,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
) -> str:
    """Create a performance analysis report for a specific RDS instance.

    Args:
        dbi_resource_identifier: The DbiResourceId of the RDS instance to analyze
        start_time: The beginning of the time interval for the report (ISO8601 format)
        end_time: The end of the time interval for the report (ISO8601 format)

    Returns:
        str: A confirmation message with the report ID and access instructions

    Raises:
        ValueError: If running in readonly mode or if parameters are invalid
    """
    start = _parse_datetime(start_time, DEFAULT_START_DAYS_AGO)
    end = _parse_datetime(end_time, DEFAULT_END_DAYS_AGO)
    _validate_time_range(start, end)

    params = {
        'ServiceType': 'RDS',
        'Identifier': dbi_resource_identifier,
        'StartTime': start,
        'EndTime': end,
        'Tags': [
            {'Key': 'mcp_server_version', 'Value': 'latest'},
            {'Key': 'created_by', 'Value': 'rds-control-plane-mcp-server'},
        ],
    }

    pi_client = PIConnectionManager.get_connection()
    response = pi_client.create_performance_analysis_report(**params)

    report_id = response.get('AnalysisReportId')
    if not report_id:
        raise ValueError('Failed to create performance report: No report ID returned')

    return REPORT_CREATION_SUCCESS_RESPONSE.format(report_id, dbi_resource_identifier)
