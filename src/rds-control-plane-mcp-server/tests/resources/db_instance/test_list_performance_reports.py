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

import json
import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime

from awslabs.rds_control_plane_mcp_server.resources.db_instance.list_performance_reports import list_performance_reports
from awslabs.rds_control_plane_mcp_server.common.constants import RESOURCE_PREFIX_DB_PERFORMANCE_REPORT


@pytest.mark.asyncio
async def test_list_performance_reports_success():
    """Test successful retrieval of performance reports."""
    instance_id = 'test-instance-1'
    create_time = datetime(2023, 1, 1, 12, 0, 0)
    start_time = datetime(2023, 1, 1, 10, 0, 0)
    end_time = datetime(2023, 1, 1, 11, 0, 0)

    mock_pi_client = MagicMock()
    mock_pi_client.list_performance_analysis_reports.return_value = {
        'AnalysisReports': [
            {
                'AnalysisReportId': 'report-1',
                'CreateTime': create_time,
                'StartTime': start_time,
                'EndTime': end_time,
                'Status': 'SUCCEEDED'
            },
            {
                'AnalysisReportId': 'report-2',
                'CreateTime': create_time,
                'StartTime': start_time,
                'EndTime': end_time,
                'Status': 'RUNNING'
            }
        ]
    }

    with patch(
        'awslabs.rds_control_plane_mcp_server.common.connection.PIConnectionManager.get_connection',
        return_value=mock_pi_client
    ):
        result = await list_performance_reports(instance_id)

        mock_pi_client.list_performance_analysis_reports.assert_called_once()
        call_args = mock_pi_client.list_performance_analysis_reports.call_args[1]
        assert call_args['ServiceType'] == 'RDS'
        assert call_args['Identifier'] == instance_id

        result_dict = json.loads(result)

        assert 'reports' in result_dict
        assert 'count' in result_dict
        assert 'resource_uri' in result_dict

        assert result_dict['count'] == 2
        assert result_dict['resource_uri'] == RESOURCE_PREFIX_DB_PERFORMANCE_REPORT.format(instance_id)

        assert len(result_dict['reports']) == 2

        report1 = result_dict['reports'][0]
        assert report1['analysis_report_id'] == 'report-1'
        assert 'create_time' in report1
        assert 'start_time' in report1
        assert 'end_time' in report1
        assert report1['status'] == 'SUCCEEDED'

        report2 = result_dict['reports'][1]
        assert report2['analysis_report_id'] == 'report-2'
        assert report2['status'] == 'RUNNING'


@pytest.mark.asyncio
async def test_list_performance_reports_empty():
    """Test list_performance_reports when no reports are available."""
    instance_id = 'test-empty-reports'

    mock_pi_client = MagicMock()
    mock_pi_client.list_performance_analysis_reports.return_value = {
        'AnalysisReports': []
    }

    with patch(
        'awslabs.rds_control_plane_mcp_server.common.connection.PIConnectionManager.get_connection',
        return_value=mock_pi_client
    ):
        result = await list_performance_reports(instance_id)

        result_dict = json.loads(result)
        assert result_dict['reports'] == []
        assert result_dict['count'] == 0
        assert result_dict['resource_uri'] == RESOURCE_PREFIX_DB_PERFORMANCE_REPORT.format(instance_id)


@pytest.mark.asyncio
async def test_list_performance_reports_client_error():
    """Test list_performance_reports when PI client raises an error."""
    from botocore.exceptions import ClientError

    instance_id = 'test-error'

    mock_pi_client = MagicMock()
    mock_pi_client.list_performance_analysis_reports.side_effect = ClientError(
        {
            'Error': {
                'Code': 'InvalidArgumentException',
                'Message': 'Performance Insights is not enabled for this instance'
            }
        },
        'ListPerformanceAnalysisReports'
    )

    with patch(
        'awslabs.rds_control_plane_mcp_server.common.connection.PIConnectionManager.get_connection',
        return_value=mock_pi_client
    ):
        result = await list_performance_reports(instance_id)

        result_dict = json.loads(result)
        assert 'error' in result_dict
        assert 'error_code' in result_dict
        assert result_dict['error_code'] == 'InvalidArgumentException'
        assert 'Performance Insights is not enabled' in result_dict['error_message']
