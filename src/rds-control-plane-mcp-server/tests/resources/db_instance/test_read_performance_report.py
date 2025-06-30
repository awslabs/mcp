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

import json
import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime

from awslabs.rds_control_plane_mcp_server.resources.db_instance.read_performance_report import read_performance_report


@pytest.mark.asyncio
async def test_read_performance_report_success():
    """Test successful retrieval of a performance report."""
    instance_id = 'test-instance-1'
    report_id = 'report-123'
    create_time = datetime(2023, 1, 1, 12, 0, 0)
    start_time = datetime(2023, 1, 1, 10, 0, 0)
    end_time = datetime(2023, 1, 1, 11, 0, 0)

    mock_pi_client = MagicMock()
    mock_pi_client.get_performance_analysis_report.return_value = {
        'AnalysisReport': {
            'AnalysisReportId': report_id,
            'ServiceType': 'RDS',
            'CreateTime': create_time,
            'StartTime': start_time,
            'EndTime': end_time,
            'Status': 'SUCCEEDED',
            'AnalysisData': {
                'Summary': 'Performance analysis for high CPU usage',
                'Findings': [
                    {
                        'Category': 'CPU',
                        'Description': 'High CPU utilization detected',
                        'Impact': 'HIGH',
                        'Recommendations': [
                            'Consider scaling up instance class',
                            'Optimize expensive queries'
                        ]
                    }
                ]
            }
        }
    }

    with patch(
        'awslabs.rds_control_plane_mcp_server.common.connection.PIConnectionManager.get_connection',
        return_value=mock_pi_client
    ):
        result = await read_performance_report(instance_id, report_id)

        mock_pi_client.get_performance_analysis_report.assert_called_once_with(
            ServiceType='RDS',
            Identifier=instance_id,
            AnalysisReportId=report_id,
            TextFormat='MARKDOWN'
        )

        result_dict = json.loads(result)

        assert result_dict['AnalysisReportId'] == report_id
        assert result_dict['ServiceType'] == 'RDS'
        assert result_dict['Status'] == 'SUCCEEDED'
        assert 'AnalysisData' in result_dict
        assert 'Summary' in result_dict['AnalysisData']
        assert len(result_dict['AnalysisData']['Findings']) == 1


@pytest.mark.asyncio
async def test_read_performance_report_not_found():
    """Test read_performance_report when report is not found."""
    from botocore.exceptions import ClientError

    instance_id = 'test-instance-1'
    report_id = 'non-existent-report'

    mock_pi_client = MagicMock()
    mock_pi_client.get_performance_analysis_report.side_effect = ClientError(
        {
            'Error': {
                'Code': 'ResourceNotFoundException',
                'Message': f'Performance report {report_id} not found'
            }
        },
        'GetPerformanceAnalysisReport'
    )

    with patch(
        'awslabs.rds_control_plane_mcp_server.common.connection.PIConnectionManager.get_connection',
        return_value=mock_pi_client
    ):
        result = await read_performance_report(instance_id, report_id)

        result_dict = json.loads(result)
        assert 'error' in result_dict
        assert 'resource' in result_dict
        assert f'Performance report {report_id} not found' in result_dict['error']
        assert f'aws-rds://db-instance/{instance_id}/performance_report/{report_id}' == result_dict['resource']


@pytest.mark.asyncio
async def test_read_performance_report_running():
    """Test read_performance_report for a report that is still running."""
    instance_id = 'test-instance-1'
    report_id = 'running-report'

    mock_pi_client = MagicMock()
    mock_pi_client.get_performance_analysis_report.return_value = {
        'AnalysisReport': {
            'AnalysisReportId': report_id,
            'ServiceType': 'RDS',
            'Status': 'RUNNING',
            'AnalysisData': {
                'Summary': 'Analysis in progress',
                'Progress': '50%'
            }
        }
    }

    with patch(
        'awslabs.rds_control_plane_mcp_server.common.connection.PIConnectionManager.get_connection',
        return_value=mock_pi_client
    ):
        result = await read_performance_report(instance_id, report_id)

        result_dict = json.loads(result)
        assert result_dict['Status'] == 'RUNNING'
        assert 'AnalysisData' in result_dict
        assert result_dict['AnalysisData']['Summary'] == 'Analysis in progress'
        assert result_dict['AnalysisData']['Progress'] == '50%'
