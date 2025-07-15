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

"""Tests for list_performance_reports resource."""

import pytest
from awslabs.rds_control_plane_mcp_server.resources.db_instance.list_performance_reports import (
    PerformanceReportSummary,
    list_performance_reports,
)
from datetime import datetime


class TestListPerformanceReports:
    """Test list_performance_reports function."""

    @pytest.mark.asyncio
    async def test_success(self, mock_pi_client):
        """Test successful performance reports retrieval."""
        mock_pi_client.list_performance_analysis_reports.return_value = {
            'AnalysisReports': [
                {
                    'AnalysisReportId': 'report-123',
                    'CreateTime': datetime(2024, 1, 1, 12, 0, 0),
                    'StartTime': datetime(2024, 1, 1, 10, 0, 0),
                    'EndTime': datetime(2024, 1, 1, 11, 0, 0),
                    'Status': 'SUCCEEDED',
                },
                {
                    'AnalysisReportId': 'report-456',
                    'CreateTime': datetime(2024, 1, 2, 12, 0, 0),
                    'StartTime': datetime(2024, 1, 2, 10, 0, 0),
                    'EndTime': datetime(2024, 1, 2, 11, 0, 0),
                    'Status': 'RUNNING',
                },
            ]
        }

        result = await list_performance_reports(dbi_resource_identifier='db-instance-1')

        assert result.count == 2
        assert len(result.reports) == 2
        assert result.reports[0].analysis_report_id == 'report-123'
        assert result.reports[0].status == 'SUCCEEDED'
        assert result.reports[1].analysis_report_id == 'report-456'
        assert result.reports[1].status == 'RUNNING'

    @pytest.mark.asyncio
    async def test_empty_response(self, mock_pi_client):
        """Test handling of empty reports response."""
        mock_pi_client.list_performance_analysis_reports.return_value = {'AnalysisReports': []}

        result = await list_performance_reports(dbi_resource_identifier='db-instance-1')

        assert result.count == 0
        assert len(result.reports) == 0

    @pytest.mark.asyncio
    async def test_pagination(self, mock_pi_client):
        """Test pagination handling."""
        mock_pi_client.list_performance_analysis_reports.side_effect = [
            {
                'AnalysisReports': [
                    {
                        'AnalysisReportId': 'report-123',
                        'CreateTime': datetime(2024, 1, 1, 12, 0, 0),
                        'Status': 'SUCCEEDED',
                    }
                ],
                'NextToken': 'next-page',
            },
            {
                'AnalysisReports': [
                    {
                        'AnalysisReportId': 'report-456',
                        'CreateTime': datetime(2024, 1, 2, 12, 0, 0),
                        'Status': 'RUNNING',
                    }
                ]
            },
        ]

        result = await list_performance_reports(dbi_resource_identifier='db-instance-1')

        assert result.count == 2
        assert mock_pi_client.list_performance_analysis_reports.call_count == 2

    @pytest.mark.asyncio
    async def test_calls_api_with_correct_parameters(self, mock_pi_client):
        """Test API is called with correct parameters."""
        mock_pi_client.list_performance_analysis_reports.return_value = {'AnalysisReports': []}

        await list_performance_reports(dbi_resource_identifier='db-instance-1')

        mock_pi_client.list_performance_analysis_reports.assert_called_once_with(
            ServiceType='RDS', Identifier='db-instance-1'
        )


class TestPerformanceReportSummary:
    """Test PerformanceReportSummary model."""

    def test_model_with_all_fields(self):
        """Test model creation with all fields."""
        report = PerformanceReportSummary(
            analysis_report_id='report-123',
            create_time=datetime(2024, 1, 1, 12, 0, 0),
            start_time=datetime(2024, 1, 1, 10, 0, 0),
            end_time=datetime(2024, 1, 1, 11, 0, 0),
            status='SUCCEEDED',
        )

        assert report.analysis_report_id == 'report-123'
        assert report.status == 'SUCCEEDED'
        assert report.create_time == datetime(2024, 1, 1, 12, 0, 0)
