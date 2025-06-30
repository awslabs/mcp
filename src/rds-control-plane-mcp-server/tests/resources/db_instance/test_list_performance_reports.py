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

from awslabs.rds_control_plane_mcp_server.resources.db_instance.list_performance_reports import list_performance_reports
from awslabs.rds_control_plane_mcp_server.common.connection import PIConnectionManager


@pytest.mark.asyncio
async def test_list_performance_reports_success(mock_rds_client):
    """Test the list_performance_reports function with successful return."""
    # Setup mock for the list_performance_analysis_reports API call
    mock_rds_client.list_performance_analysis_reports.return_value = {
        'AnalysisReports': [
            {
                'AnalysisReportId': 'report-123',
                'CreateTime': '2023-06-15T08:00:00Z',
                'StartTime': '2023-06-14T08:00:00Z',
                'EndTime': '2023-06-15T08:00:00Z',
                'Status': 'SUCCEEDED',
            },
            {
                'AnalysisReportId': 'report-456',
                'CreateTime': '2023-06-10T10:00:00Z',
                'StartTime': '2023-06-09T10:00:00Z',
                'EndTime': '2023-06-10T10:00:00Z',
                'Status': 'SUCCEEDED',
            }
        ]
    }
    
    # Use a monkeypatch for the connection manager 
    with patch.object(PIConnectionManager, 'get_connection', return_value=mock_rds_client):
        # Call the resource function with a valid instance ID
        result = await list_performance_reports(dbi_resource_identifier="test-instance-1")
    
    # Verify the result is well-formed
    result_dict = json.loads(result)
    assert 'reports' in result_dict
    assert 'count' in result_dict
    assert 'resource_uri' in result_dict
    
    assert result_dict['count'] == 2
    
    # Verify report data
    assert len(result_dict['reports']) == 2
    assert result_dict['reports'][0]['analysis_report_id'] == 'report-123'
    assert result_dict['reports'][0]['status'] == 'SUCCEEDED'
    assert 'create_time' in result_dict['reports'][0]
    assert 'start_time' in result_dict['reports'][0]
    assert 'end_time' in result_dict['reports'][0]


@pytest.mark.asyncio
async def test_list_performance_reports_empty(mock_rds_client):
    """Test the list_performance_reports function with empty response."""
    # Setup mock for empty reports
    mock_rds_client.list_performance_analysis_reports.return_value = {
        'AnalysisReports': []
    }
    
    # Call the resource function with the patched connection
    with patch.object(PIConnectionManager, 'get_connection', return_value=mock_rds_client):
        result = await list_performance_reports(dbi_resource_identifier="test-instance-1")
    
    # Verify the result is well-formed with empty list
    result_dict = json.loads(result)
    assert 'reports' in result_dict
    assert 'count' in result_dict
    assert result_dict['count'] == 0
    assert len(result_dict['reports']) == 0


@pytest.mark.asyncio
async def test_list_performance_reports_with_pagination(mock_rds_client):
    """Test the list_performance_reports function with pagination."""
    # Set up pagination mock
    mock_rds_client.list_performance_analysis_reports.side_effect = [
        {
            'AnalysisReports': [
                {
                    'AnalysisReportId': 'report-123',
                    'CreateTime': '2023-06-15T08:00:00Z',
                    'StartTime': '2023-06-14T08:00:00Z',
                    'EndTime': '2023-06-15T08:00:00Z',
                    'Status': 'SUCCEEDED',
                }
            ],
            'NextToken': 'next-page'
        },
        {
            'AnalysisReports': [
                {
                    'AnalysisReportId': 'report-456',
                    'CreateTime': '2023-06-10T10:00:00Z',
                    'StartTime': '2023-06-09T10:00:00Z',
                    'EndTime': '2023-06-10T10:00:00Z',
                    'Status': 'SUCCEEDED',
                }
            ]
        }
    ]
    
    # Call the resource function with the patched connection
    with patch.object(PIConnectionManager, 'get_connection', return_value=mock_rds_client):
        result = await list_performance_reports(dbi_resource_identifier="test-instance-1")
    
    # Verify the result is well-formed
    result_dict = json.loads(result)
    assert 'reports' in result_dict
    assert 'count' in result_dict
    assert result_dict['count'] == 2
    
    # Verify both reports are included
    report_ids = [report['analysis_report_id'] for report in result_dict['reports']]
    assert 'report-123' in report_ids
    assert 'report-456' in report_ids


@pytest.mark.asyncio
async def test_list_performance_reports_with_filters(mock_rds_client):
    """Test the list_performance_reports function with filters."""
    # Setup mock for API response
    mock_rds_client.list_performance_analysis_reports.return_value = {
        'AnalysisReports': [
            {
                'AnalysisReportId': 'report-123',
                'CreateTime': '2023-06-15T08:00:00Z',
                'StartTime': '2023-06-14T08:00:00Z',
                'EndTime': '2023-06-15T08:00:00Z',
                'Status': 'SUCCEEDED',
            }
        ]
    }
    
    # Call the resource function with the patched connection
    with patch.object(PIConnectionManager, 'get_connection', return_value=mock_rds_client):
        result = await list_performance_reports(dbi_resource_identifier="test-instance-1")
    
    # Verify that API was called
    mock_rds_client.list_performance_analysis_reports.assert_called_once()
    call_kwargs = mock_rds_client.list_performance_analysis_reports.call_args[1]
    assert call_kwargs['ServiceType'] == 'RDS'
    assert call_kwargs['Identifier'] == 'test-instance-1'
    assert 'MaxResults' in call_kwargs


@pytest.mark.asyncio
async def test_list_performance_reports_client_error(mock_rds_client):
    """Test the list_performance_reports function with a client error."""
    # Set up the mock to raise a client error
    from botocore.exceptions import ClientError
    error_response = {
        'Error': {
            'Code': 'DBInstanceNotFound',
            'Message': 'DB instance not found'
        }
    }
    mock_rds_client.list_performance_analysis_reports.side_effect = ClientError(
        error_response, 'ListPerformanceAnalysisReports'
    )
    
    # Call the resource function with the patched connection
    with patch.object(PIConnectionManager, 'get_connection', return_value=mock_rds_client):
        result = await list_performance_reports(dbi_resource_identifier="non-existent-instance")
    
    # Verify the error response
    result_dict = json.loads(result)
    assert 'error' in result_dict
    assert 'error_code' in result_dict
    assert result_dict['error_code'] == 'DBInstanceNotFound'


@pytest.mark.asyncio
async def test_list_performance_reports_general_error(mock_rds_client):
    """Test the list_performance_reports function with a general error."""
    # Set up the mock to raise a general exception
    mock_rds_client.list_performance_analysis_reports.side_effect = ValueError("Unexpected error")
    
    # Call the resource function with the patched connection
    with patch.object(PIConnectionManager, 'get_connection', return_value=mock_rds_client):
        result = await list_performance_reports(dbi_resource_identifier="test-instance")
    
    # Verify the error response
    result_dict = json.loads(result)
    assert 'error' in result_dict
    assert 'error_type' in result_dict
    assert result_dict['error_type'] == 'ValueError'
