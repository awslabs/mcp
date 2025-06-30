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

"""Tests for the read_performance_report module which handles RDS performance report operations."""

import json
import pytest
from awslabs.rds_control_plane_mcp_server.resources.db_instance.read_performance_report import (
    ReadPerformanceReportHandler,
)
from unittest.mock import AsyncMock, patch


class TestReadPerformanceReportHandler:
    """Tests for the ReadPerformanceReportHandler class."""

    def test_init(self, mock_mcp, mock_pi_client):
        """Test initialization of ReadPerformanceReportHandler."""
        handler = ReadPerformanceReportHandler(mock_mcp, mock_pi_client)

        assert handler.mcp == mock_mcp
        assert handler.pi_client == mock_pi_client

        mock_mcp.resource.assert_called_once()
        call_args = mock_mcp.resource.call_args

        assert (
            call_args[1]['uri']
            == 'aws-rds://db-instance/{dbi_resource_identifier}/performance_report/{report_id}'
        )
        assert call_args[1]['name'] == 'ReadPerformanceReport'
        assert call_args[1]['mime_type'] == 'application/json'
        assert 'description' in call_args[1]

    @pytest.mark.asyncio
    async def test_success(self, mock_mcp, mock_pi_client):
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

        handler = ReadPerformanceReportHandler(mock_mcp, mock_pi_client)

        with patch(
            'awslabs.rds_control_plane_mcp_server.resources.instances.read_performance_report.format_aws_response',
            return_value={'AnalysisReport': expected_result},
        ):
            result_json = await handler.read_performance_report(
                dbi_resource_identifier=dbi_resource_identifier, report_id=report_id
            )

            mock_pi_client.get_performance_analysis_report.assert_called_once_with(
                ServiceType='RDS',
                Identifier=dbi_resource_identifier,
                AnalysisReportId=report_id,
                TextFormat='MARKDOWN',
            )

            # The result should be the expected result formatted as JSON
            result = json.loads(result_json)
            assert result == expected_result

    @pytest.mark.asyncio
    async def test_error_handling(self, mock_mcp, mock_pi_client):
        """Test exception handling when PI API fails."""
        dbi_resource_identifier = 'db-ABCDEFGHIJKLMNOPQRSTUVWXYZ'
        report_id = 'report-1'
        mock_exception = Exception('Test error')
        mock_error_response = {'error': 'Test error'}

        mock_pi_client.get_performance_analysis_report.side_effect = mock_exception

        handler = ReadPerformanceReportHandler(mock_mcp, mock_pi_client)

        with patch(
            'awslabs.rds_control_plane_mcp_server.resources.instances.read_performance_report.handle_aws_error',
            new_callable=AsyncMock,
            return_value=mock_error_response,
        ) as mock_handle_error:
            result_json = await handler.read_performance_report(
                dbi_resource_identifier=dbi_resource_identifier, report_id=report_id
            )

            mock_handle_error.assert_called_once()
            error_msg = mock_handle_error.call_args[0][0]
            assert dbi_resource_identifier in error_msg
            assert report_id in error_msg
            assert mock_handle_error.call_args[0][1] == mock_exception

            assert result_json == json.dumps(mock_error_response, indent=2)
