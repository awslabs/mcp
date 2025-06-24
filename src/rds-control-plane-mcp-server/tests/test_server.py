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

"""Tests for the rds-control-plane MCP Server."""

import pytest
from awslabs.rds_control_plane_mcp_server.models import (
    DBLogFileSummary,
    PerformanceReportSummary,
)
from awslabs.rds_control_plane_mcp_server.server import (
    list_db_log_files_resource,
    list_performance_reports_resource,
    read_performance_report_resource,
)
from datetime import datetime
from unittest.mock import ANY, AsyncMock, patch


class TestPerformanceReportsResource:
    """Test cases for performance reports resource endpoints."""

    @pytest.mark.asyncio
    async def test_list_performance_reports_success(self):
        """Test successful retrieval of performance reports list."""
        dbi_resource_identifier = 'db-ABCDEFGHIJKLMNOPQRSTUVWXYZ'
        mock_reports = [
            PerformanceReportSummary(
                analysis_report_id='report-123',
                create_time=datetime(2025, 6, 1, 12, 0, 0),
                start_time=datetime(2025, 6, 1, 10, 0, 0),
                end_time=datetime(2025, 6, 1, 11, 0, 0),
                status='SUCCEEDED',
            ),
            PerformanceReportSummary(
                analysis_report_id='report-456',
                create_time=datetime(2025, 6, 2, 12, 0, 0),
                start_time=datetime(2025, 6, 2, 10, 0, 0),
                end_time=datetime(2025, 6, 2, 11, 0, 0),
                status='RUNNING',
            ),
        ]

        with patch(
            'awslabs.rds_control_plane_mcp_server.server.list_performance_reports',
            new_callable=AsyncMock,
            return_value=mock_reports,
        ) as mock_list_reports:
            result = await list_performance_reports_resource(dbi_resource_identifier)

        mock_list_reports.assert_called_once_with(dbi_resource_identifier, ANY)

        assert len(result) == 2
        assert isinstance(result[0], PerformanceReportSummary)
        assert result[0].analysis_report_id == 'report-123'
        assert result[0].status == 'SUCCEEDED'

        assert isinstance(result[1], PerformanceReportSummary)
        assert result[1].analysis_report_id == 'report-456'
        assert result[1].status == 'RUNNING'

    @pytest.mark.asyncio
    async def test_list_performance_reports_error(self):
        """Test handling of errors when listing performance reports."""
        dbi_resource_identifier = 'db-ABCDEFGHIJKLMNOPQRSTUVWXYZ'
        error_response = {
            'error': 'Failed to list performance reports',
            'details': 'Access denied',
        }

        with patch(
            'awslabs.rds_control_plane_mcp_server.server.list_performance_reports',
            new_callable=AsyncMock,
            return_value=error_response,
        ) as mock_list_reports:
            result = await list_performance_reports_resource(dbi_resource_identifier)

        mock_list_reports.assert_called_once()
        assert result == error_response
        assert result.get('error') == 'Failed to list performance reports'
        assert result.get('details') == 'Access denied'

    @pytest.mark.asyncio
    async def test_read_performance_report_success(self):
        """Test successful retrieval of a specific performance report."""
        dbi_resource_identifier = 'db-ABCDEFGHIJKLMNOPQRSTUVWXYZ'
        report_identifier = 'report-123'
        mock_report_content = {}

        with patch(
            'awslabs.rds_control_plane_mcp_server.server.read_performance_report',
            new_callable=AsyncMock,
            return_value=mock_report_content,
        ) as mock_read_report:
            result = await read_performance_report_resource(
                dbi_resource_identifier, report_identifier
            )

        mock_read_report.assert_called_once_with(
            dbi_resource_identifier=dbi_resource_identifier,
            report_id=report_identifier,
            pi_client=ANY,
        )

        assert result == mock_report_content

    @pytest.mark.asyncio
    async def test_read_performance_report_error(self):
        """Test handling of errors when reading a performance report."""
        dbi_resource_identifier = 'db-ABCDEFGHIJKLMNOPQRSTUVWXYZ'
        report_identifier = 'report-999'  # Non-existent report
        error_response = {
            'error': 'Failed to read performance report',
            'details': 'Report not found',
        }

        with patch(
            'awslabs.rds_control_plane_mcp_server.server.read_performance_report',
            new_callable=AsyncMock,
            return_value=error_response,
        ) as mock_read_report:
            result = await read_performance_report_resource(
                dbi_resource_identifier, report_identifier
            )

        mock_read_report.assert_called_once()
        assert result == error_response
        assert result.get('error') == 'Failed to read performance report'
        assert result.get('details') == 'Report not found'


class TestDBLogFilesResource:
    """Test cases for DB log files resource endpoints."""

    @pytest.mark.asyncio
    async def test_list_db_log_files_success(self):
        """Test successful retrieval of database log files."""
        db_instance_identifier = 'instance-123'
        mock_log_files = [
            DBLogFileSummary(
                log_file_name='error.log', last_written=datetime(2025, 6, 1, 12, 0, 0), size=1024
            ),
            DBLogFileSummary(
                log_file_name='slow-query.log',
                last_written=datetime(2025, 6, 1, 12, 30, 0),
                size=2048,
            ),
        ]

        with patch(
            'awslabs.rds_control_plane_mcp_server.server.list_db_log_files',
            new_callable=AsyncMock,
            return_value=mock_log_files,
        ) as mock_list_logs:
            result = await list_db_log_files_resource(db_instance_identifier)

        mock_list_logs.assert_called_once_with(
            db_instance_identifier=db_instance_identifier, rds_client=ANY
        )

        assert len(result) == 2
        assert isinstance(result[0], DBLogFileSummary)
        assert result[0].log_file_name == 'error.log'
        assert result[0].size == 1024
        assert isinstance(result[0].last_written, datetime)

        assert isinstance(result[1], DBLogFileSummary)
        assert result[1].log_file_name == 'slow-query.log'
        assert result[1].size == 2048
        assert isinstance(result[1].last_written, datetime)

    @pytest.mark.asyncio
    async def test_list_db_log_files_error(self):
        """Test handling of errors when listing database log files."""
        db_instance_identifier = 'instance-123'
        error_response = {'error': 'Failed to list log files', 'details': 'Access denied'}

        with patch(
            'awslabs.rds_control_plane_mcp_server.server.list_db_log_files',
            new_callable=AsyncMock,
            return_value=error_response,
        ) as mock_list_logs:
            result = await list_db_log_files_resource(db_instance_identifier)

        mock_list_logs.assert_called_once()
        assert result == error_response
        assert result.get('error') == 'Failed to list log files'
        assert result.get('details') == 'Access denied'
