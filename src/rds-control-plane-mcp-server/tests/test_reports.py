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

"""Tests for the reports module which handles RDS performance reports."""

import pytest
from awslabs.rds_control_plane_mcp_server.constants import MAX_ITEMS
from awslabs.rds_control_plane_mcp_server.models import PerformanceReportSummary
from awslabs.rds_control_plane_mcp_server.reports import (
    list_performance_reports,
    read_performance_report,
)
from datetime import datetime
from unittest.mock import AsyncMock, patch


class TestListPerformanceReports:
    """Tests for the list_performance_reports function."""

    @pytest.mark.asyncio
    async def test_success(self, mock_pi_client):
        """Test successful retrieval and processing of performance reports."""
        dbi_resource_identifier = 'db-ABCDEFGHIJKLMNOPQRSTUVWXYZ'
        mock_reports = [
            {
                'AnalysisReportId': 'report-1',
                'CreateTime': datetime(2023, 1, 1, 12, 0, 0),
                'StartTime': datetime(2023, 1, 1, 10, 0, 0),
                'EndTime': datetime(2023, 1, 1, 11, 0, 0),
                'Status': 'SUCCEEDED',
            },
            {
                'AnalysisReportId': 'report-2',
                'CreateTime': datetime(2023, 1, 2, 12, 0, 0),
                'StartTime': datetime(2023, 1, 2, 10, 0, 0),
                'EndTime': datetime(2023, 1, 2, 11, 0, 0),
                'Status': 'RUNNING',
            },
        ]

        mock_pi_client.list_performance_analysis_reports.return_value = {
            'AnalysisReports': mock_reports
        }

        result = await list_performance_reports(dbi_resource_identifier, mock_pi_client)

        mock_pi_client.list_performance_analysis_reports.assert_called_once_with(
            ServiceType='RDS', Identifier=dbi_resource_identifier, MaxResults=MAX_ITEMS
        )

        assert isinstance(result, list)
        assert len(result) == 2

        assert isinstance(result[0], PerformanceReportSummary)
        assert result[0].analysis_report_id == 'report-1'
        assert result[0].create_time == datetime(2023, 1, 1, 12, 0, 0)
        assert result[0].start_time == datetime(2023, 1, 1, 10, 0, 0)
        assert result[0].end_time == datetime(2023, 1, 1, 11, 0, 0)
        assert result[0].status == 'SUCCEEDED'

        assert isinstance(result[1], PerformanceReportSummary)
        assert result[1].analysis_report_id == 'report-2'
        assert result[1].create_time == datetime(2023, 1, 2, 12, 0, 0)
        assert result[1].start_time == datetime(2023, 1, 2, 10, 0, 0)
        assert result[1].end_time == datetime(2023, 1, 2, 11, 0, 0)
        assert result[1].status == 'RUNNING'

    @pytest.mark.asyncio
    async def test_empty_response(self, mock_pi_client):
        """Test handling of empty response from PI API."""
        dbi_resource_identifier = 'db-ABCDEFGHIJKLMNOPQRSTUVWXYZ'
        mock_pi_client.list_performance_analysis_reports.return_value = {'AnalysisReports': []}

        result = await list_performance_reports(dbi_resource_identifier, mock_pi_client)

        assert isinstance(result, list)
        assert len(result) == 0

    @pytest.mark.asyncio
    async def test_error_handling(self, mock_pi_client):
        """Test exception handling when PI API fails."""
        dbi_resource_identifier = 'db-ABCDEFGHIJKLMNOPQRSTUVWXYZ'
        mock_exception = Exception('Test error')
        mock_error_response = {'error': 'Test error'}

        mock_pi_client.list_performance_analysis_reports.side_effect = mock_exception

        with patch(
            'awslabs.rds_control_plane_mcp_server.reports.handle_aws_error',
            new_callable=AsyncMock,
            return_value=mock_error_response,
        ) as mock_handle_error:
            result = await list_performance_reports(dbi_resource_identifier, mock_pi_client)

            mock_handle_error.assert_called_once()
            error_msg = mock_handle_error.call_args[0][0]
            assert 'list_performance_analysis_reports' in error_msg
            assert '{dbi_resource_identifier}' in error_msg
            assert mock_handle_error.call_args[0][1] == mock_exception
            assert result == mock_error_response


class TestReadPerformanceReport:
    """Tests for the read_performance_report function."""

    @pytest.mark.asyncio
    async def test_success(self, mock_pi_client):
        """Test successful retrieval and processing of a specific performance report."""
        dbi_resource_identifier = 'db-ABCDEFGHIJKLMNOPQRSTUVWXYZ'
        report_id = 'report-1'
        mock_report = {
            'AnalysisReport': {
                'AnalysisReportId': report_id,
                'Status': 'SUCCEEDED',
                'AnalysisResults': [
                    {'Key': 'DbLoadAverage', 'Value': '5.23'},
                    {'Key': 'TopWaitEvents', 'Value': 'CPU, IO'},
                ],
                'Recommendations': [{'Text': 'Consider scaling up the instance'}],
            },
            'ResponseMetadata': {'RequestId': 'abc-123'},
        }

        expected_result = {
            'AnalysisReportId': report_id,
            'Status': 'SUCCEEDED',
            'AnalysisResults': [
                {'Key': 'DbLoadAverage', 'Value': '5.23'},
                {'Key': 'TopWaitEvents', 'Value': 'CPU, IO'},
            ],
            'Recommendations': [{'Text': 'Consider scaling up the instance'}],
        }

        mock_pi_client.get_performance_analysis_report.return_value = mock_report

        #
        with patch(
            'awslabs.rds_control_plane_mcp_server.reports.format_aws_response',
            return_value={'AnalysisReport': expected_result},
        ) as mock_format:
            result = await read_performance_report(
                dbi_resource_identifier, report_id, mock_pi_client
            )

            mock_pi_client.get_performance_analysis_report.assert_called_once_with(
                ServiceType='RDS',
                Identifier=dbi_resource_identifier,
                AnalysisReportId=report_id,
                TextFormat='MARKDOWN',
            )
            mock_format.assert_called_once_with(dict(mock_report))
            assert result == expected_result

    @pytest.mark.asyncio
    async def test_error_handling(self, mock_pi_client):
        """Test exception handling when PI API fails."""
        dbi_resource_identifier = 'db-ABCDEFGHIJKLMNOPQRSTUVWXYZ'
        report_id = 'report-1'
        mock_exception = Exception('Test error')
        mock_error_response = {'error': 'Test error'}

        mock_pi_client.get_performance_analysis_report.side_effect = mock_exception

        with patch(
            'awslabs.rds_control_plane_mcp_server.reports.handle_aws_error',
            new_callable=AsyncMock,
            return_value=mock_error_response,
        ) as mock_handle_error:
            result = await read_performance_report(
                dbi_resource_identifier, report_id, mock_pi_client
            )

            mock_handle_error.assert_called_once()
            error_msg = mock_handle_error.call_args[0][0]
            assert dbi_resource_identifier in error_msg
            assert report_id in error_msg
            assert mock_handle_error.call_args[0][1] == mock_exception
            assert result == mock_error_response
