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

"""Tests for read_performance_report resource."""

import pytest
from awslabs.rds_control_plane_mcp_server.resources.db_instance.read_performance_report import (
    AnalysisReport,
    read_performance_report,
)
from datetime import datetime


class TestReadPerformanceReport:
    """Test read_performance_report function."""

    @pytest.mark.asyncio
    async def test_success(self, mock_pi_client):
        """Test successful performance report retrieval."""
        mock_response = {
            'AnalysisReport': {
                'AnalysisReportId': 'report-123',
                'Identifier': 'db-instance-1',
                'ServiceType': 'RDS',
                'CreateTime': datetime(2024, 1, 1, 12, 0, 0),
                'StartTime': datetime(2024, 1, 1, 10, 0, 0),
                'EndTime': datetime(2024, 1, 1, 11, 0, 0),
                'Status': 'SUCCEEDED',
                'Insights': [{'type': 'cpu_utilization', 'value': 85.2}],
            }
        }
        mock_pi_client.get_performance_analysis_report.return_value = mock_response

        result = await read_performance_report(
            dbi_resource_identifier='db-instance-1', report_id='report-123'
        )

        assert result.AnalysisReportId == 'report-123'
        assert result.Identifier == 'db-instance-1'
        assert result.ServiceType == 'RDS'
        assert result.Status == 'SUCCEEDED'
        assert len(result.Insights) == 1

    @pytest.mark.asyncio
    async def test_calls_api_with_correct_parameters(self, mock_pi_client):
        """Test API is called with correct parameters."""
        mock_response = {
            'AnalysisReport': {
                'AnalysisReportId': 'report-123',
                'Identifier': 'db-instance-1',
                'ServiceType': 'RDS',
                'CreateTime': datetime(2024, 1, 1, 12, 0, 0),
                'StartTime': datetime(2024, 1, 1, 10, 0, 0),
                'EndTime': datetime(2024, 1, 1, 11, 0, 0),
                'Status': 'SUCCEEDED',
                'Insights': [],
            }
        }
        mock_pi_client.get_performance_analysis_report.return_value = mock_response

        await read_performance_report(
            dbi_resource_identifier='db-instance-1', report_id='report-123'
        )

        mock_pi_client.get_performance_analysis_report.assert_called_once_with(
            ServiceType='RDS',
            Identifier='db-instance-1',
            AnalysisReportId='report-123',
            TextFormat='MARKDOWN',
        )


class TestAnalysisReport:
    """Test AnalysisReport model."""

    def test_model_validation(self):
        """Test model creation with valid data."""
        data = {
            'AnalysisReportId': 'report-123',
            'Identifier': 'db-instance-1',
            'ServiceType': 'RDS',
            'CreateTime': datetime(2024, 1, 1, 12, 0, 0),
            'StartTime': datetime(2024, 1, 1, 10, 0, 0),
            'EndTime': datetime(2024, 1, 1, 11, 0, 0),
            'Status': 'SUCCEEDED',
            'Insights': [{'type': 'cpu', 'value': 85}],
        }

        report = AnalysisReport.model_validate(data)

        assert report.AnalysisReportId == 'report-123'
        assert report.Identifier == 'db-instance-1'
        assert report.ServiceType == 'RDS'
        assert report.Status == 'SUCCEEDED'
        assert len(report.Insights) == 1

    def test_model_with_empty_insights(self):
        """Test model handles empty insights list."""
        data = {
            'AnalysisReportId': 'report-123',
            'Identifier': 'db-instance-1',
            'ServiceType': 'RDS',
            'CreateTime': datetime(2024, 1, 1, 12, 0, 0),
            'StartTime': datetime(2024, 1, 1, 10, 0, 0),
            'EndTime': datetime(2024, 1, 1, 11, 0, 0),
            'Status': 'RUNNING',
        }

        report = AnalysisReport.model_validate(data)

        assert report.Insights == []
        assert report.Status == 'RUNNING'
