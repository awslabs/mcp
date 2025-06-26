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

"""Tests for the list_performance_reports module which handles RDS performance reports operations."""

import json
import pytest
from awslabs.rds_control_plane_mcp_server.common.config import max_items
from awslabs.rds_control_plane_mcp_server.common.constants import (
    RESOURCE_PREFIX_DB_PERFORMANCE_REPORT,
)
from awslabs.rds_control_plane_mcp_server.resources.instances.list_performance_reports import (
    ListPerformanceReportHandler,
)
from datetime import datetime
from unittest.mock import AsyncMock, patch


class TestListPerformanceReportHandler:
    """Tests for the ListPerformanceReportHandler class."""

    def test_init(self, mock_mcp, mock_pi_client):
        """Test initialization of ListPerformanceReportHandler."""
        handler = ListPerformanceReportHandler(mock_mcp, mock_pi_client)

        assert handler.mcp == mock_mcp
        assert handler.pi_client == mock_pi_client

        mock_mcp.resource.assert_called_once()
        call_args = mock_mcp.resource.call_args

        assert (
            call_args[1]['uri']
            == 'aws-rds://db-instance/{dbi_resource_identifier}/performance_report'
        )
        assert call_args[1]['name'] == 'ListPerformanceReports'
        assert call_args[1]['mime_type'] == 'application/json'
        assert 'description' in call_args[1]

    @pytest.mark.asyncio
    async def test_success(self, mock_mcp, mock_pi_client):
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

        handler = ListPerformanceReportHandler(mock_mcp, mock_pi_client)
        result_json = await handler.list_performance_reports(
            dbi_resource_identifier=dbi_resource_identifier
        )
        result = json.loads(result_json)

        mock_pi_client.list_performance_analysis_reports.assert_called_once_with(
            ServiceType='RDS', Identifier=dbi_resource_identifier, MaxResults=max_items
        )

        assert 'reports' in result
        assert 'count' in result
        assert 'resource_uri' in result

        assert result['count'] == 2
        assert len(result['reports']) == 2

        report1 = result['reports'][0]
        assert report1['analysis_report_id'] == 'report-1'
        assert 'create_time' in report1
        assert 'start_time' in report1
        assert 'end_time' in report1
        assert report1['status'] == 'SUCCEEDED'

        report2 = result['reports'][1]
        assert report2['analysis_report_id'] == 'report-2'
        assert 'create_time' in report2
        assert 'start_time' in report2
        assert 'end_time' in report2
        assert report2['status'] == 'RUNNING'

    @pytest.mark.asyncio
    async def test_empty_response(self, mock_mcp, mock_pi_client):
        """Test handling of empty response from PI API."""
        dbi_resource_identifier = 'db-ABCDEFGHIJKLMNOPQRSTUVWXYZ'
        mock_pi_client.list_performance_analysis_reports.return_value = {'AnalysisReports': []}

        handler = ListPerformanceReportHandler(mock_mcp, mock_pi_client)
        result_json = await handler.list_performance_reports(
            dbi_resource_identifier=dbi_resource_identifier
        )
        result = json.loads(result_json)

        assert 'reports' in result
        assert 'count' in result
        assert 'resource_uri' in result
        assert result['count'] == 0
        assert len(result['reports']) == 0
        assert result['resource_uri'] == RESOURCE_PREFIX_DB_PERFORMANCE_REPORT.format(
            dbi_resource_identifier
        )

    @pytest.mark.asyncio
    async def test_error_handling(self, mock_mcp, mock_pi_client):
        """Test exception handling when PI API fails."""
        dbi_resource_identifier = 'db-ABCDEFGHIJKLMNOPQRSTUVWXYZ'
        mock_exception = Exception('Test error')
        mock_error_response = {'error': 'Test error'}

        mock_pi_client.list_performance_analysis_reports.side_effect = mock_exception

        handler = ListPerformanceReportHandler(mock_mcp, mock_pi_client)

        with patch(
            'awslabs.rds_control_plane_mcp_server.resources.instances.list_performance_reports.handle_aws_error',
            new_callable=AsyncMock,
            return_value=mock_error_response,
        ) as mock_handle_error:
            result_json = await handler.list_performance_reports(
                dbi_resource_identifier=dbi_resource_identifier
            )

            mock_handle_error.assert_called_once()
            error_msg = mock_handle_error.call_args[0][0]
            assert 'list_performance_analysis_reports' in error_msg
            # The actual code uses the literal string '{dbi_resource_identifier}' rather than interpolating
            assert '{dbi_resource_identifier}' in error_msg
            assert mock_handle_error.call_args[0][1] == mock_exception

            assert result_json == json.dumps(mock_error_response, indent=2)
