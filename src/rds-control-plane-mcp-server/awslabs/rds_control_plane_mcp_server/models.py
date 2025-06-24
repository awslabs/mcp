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

"""Data models for the RDS Monitoring MCP Server."""

from datetime import datetime
from pydantic import BaseModel, Field
from typing import Literal


# Log Files


class DBLogFileSummary(BaseModel):
    """Database log file information.

    This model represents an Amazon RDS database log file with its metadata,
    including name, last modification time, and size.

    Attributes:
        log_file_name: The name of the log file in the database instance.
        last_written: A POSIX timestamp when the last log entry was written.
        size: Size of the log file in bytes.
    """

    log_file_name: str = Field(
        description='Name of the log file',
    )
    last_written: datetime = Field(
        description='A POSIX timestamp when the last log entry was written.'
    )
    size: int = Field(description='Size of the log file in bytes', ge=0)


# Reporting


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
    create_time: datetime | None = Field(None, description='Time when the report was created')
    start_time: datetime | None = Field(None, description='Start time of the analysis period')
    end_time: datetime | None = Field(None, description='End time of the analysis period')
    status: Literal['RUNNING', 'SUCCEEDED', 'FAILED'] | None = None
