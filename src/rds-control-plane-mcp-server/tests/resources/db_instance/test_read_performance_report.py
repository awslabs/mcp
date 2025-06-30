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

from awslabs.rds_control_plane_mcp_server.resources.db_instance.read_performance_report import read_performance_report
from awslabs.rds_control_plane_mcp_server.common.connection import PIConnectionManager


@pytest.mark.asyncio
async def test_read_performance_report_success(mock_rds_client):
    """Test the read_performance_report function with successful return."""
    # Setup mock for the get_performance_analysis_report API call
    mock_report_content = {
        'AnalysisReport': {
            'report_id': 'report-123',
            'report_name': 'weekly-performance-report',
            'status': 'completed',
            'instance_id': 'test-instance-1',
            'data': {
                'summary': 'Database performance report',
                'metrics': [
                    {
                        'name': 'cpu_utilization',
                        'average': 45.7,
                        'peak': 85.2
                    },
                    {
                        'name': 'memory_utilization',
                        'average': 65.3,
                        'peak': 78.1
                    }
                ],
                'recommendations': [
                    'Consider scaling up the instance if CPU utilization remains high'
                ]
            }
        }
    }
    
    mock_rds_client.get_performance_analysis_report.return_value = mock_report_content
    
    # Call the resource function with a valid instance ID and report ID with the patched connection
    with patch.object(PIConnectionManager, 'get_connection', return_value=mock_rds_client):
        result = await read_performance_report(dbi_resource_identifier="test-instance-1", report_id="report-123")
    
    # Verify the result is well-formed
    result_dict = json.loads(result)
    assert 'report_id' in result_dict
    assert 'report_name' in result_dict
    assert 'status' in result_dict
    assert 'data' in result_dict
    
    # Check basic report metadata
    assert result_dict['report_id'] == 'report-123'
    assert result_dict['report_name'] == 'weekly-performance-report'
    assert result_dict['status'] == 'completed'
    assert result_dict['instance_id'] == 'test-instance-1'
    
    # Check report data
    report_data = result_dict['data']
    assert 'summary' in report_data
    assert 'metrics' in report_data
    assert 'recommendations' in report_data
    assert len(report_data['metrics']) == 2
    assert 'cpu_utilization' == report_data['metrics'][0]['name']


@pytest.mark.asyncio
async def test_read_performance_report_not_found(mock_rds_client):
    """Test the read_performance_report function when report doesn't exist."""
    # Set up the mock to raise a client error for report not found
    from botocore.exceptions import ClientError
    error_response = {
        'Error': {
            'Code': 'ReportNotFoundFault',
            'Message': 'Report with ID report-999 not found'
        }
    }
    mock_rds_client.get_performance_analysis_report.side_effect = ClientError(
        error_response, 'GetPerformanceAnalysisReport'
    )
    
    # Call the resource function with a non-existent report ID with the patched connection
    with patch.object(PIConnectionManager, 'get_connection', return_value=mock_rds_client):
        result = await read_performance_report(dbi_resource_identifier="test-instance-1", report_id="report-999")
    
    # Verify the error response
    result_dict = json.loads(result)
    assert 'error' in result_dict
    assert 'ReportNotFoundFault' in result_dict['error']


@pytest.mark.asyncio
async def test_read_performance_report_invalid_json(mock_rds_client):
    """Test the read_performance_report function with invalid JSON in report data."""
    # Setup mock with invalid JSON in AnalysisReport
    mock_rds_client.get_performance_analysis_report.side_effect = json.JSONDecodeError("Invalid JSON", "", 0)
    
    # Call the resource function with the patched connection
    with patch.object(PIConnectionManager, 'get_connection', return_value=mock_rds_client):
        result = await read_performance_report(dbi_resource_identifier="test-instance-1", report_id="report-123")
    
    # Verify error handling for invalid JSON
    result_dict = json.loads(result)
    assert 'error' in result_dict
    assert 'JSON' in result_dict['error']


@pytest.mark.asyncio
async def test_read_performance_report_empty_data(mock_rds_client):
    """Test the read_performance_report function with empty report data."""
    # Setup mock with empty AnalysisReport
    mock_rds_client.get_performance_analysis_report.return_value = {
        'AnalysisReport': {
            'report_id': 'report-123',
            'report_name': 'weekly-performance-report',
            'status': 'completed',
            'instance_id': 'test-instance-1',
            'data': None
        }
    }
    
    # Call the resource function with the patched connection
    with patch.object(PIConnectionManager, 'get_connection', return_value=mock_rds_client):
        result = await read_performance_report(dbi_resource_identifier="test-instance-1", report_id="report-123")
    
    # Verify handling of empty data
    result_dict = json.loads(result)
    assert 'report_id' in result_dict
    assert 'report_name' in result_dict
    assert result_dict['data'] is None  # Or appropriate error handling based on implementation


@pytest.mark.asyncio
async def test_read_performance_report_client_error(mock_rds_client):
    """Test the read_performance_report function with a client error."""
    # Set up the mock to raise a client error
    from botocore.exceptions import ClientError
    error_response = {
        'Error': {
            'Code': 'AccessDenied',
            'Message': 'User is not authorized to perform operation'
        }
    }
    mock_rds_client.get_performance_analysis_report.side_effect = ClientError(
        error_response, 'GetPerformanceAnalysisReport'
    )
    
    # Call the resource function with the patched connection
    with patch.object(PIConnectionManager, 'get_connection', return_value=mock_rds_client):
        result = await read_performance_report(dbi_resource_identifier="test-instance-1", report_id="report-123")
    
    # Verify the error response
    result_dict = json.loads(result)
    assert 'error' in result_dict
    assert 'AccessDenied' in result_dict['error']


@pytest.mark.asyncio
async def test_read_performance_report_general_error(mock_rds_client):
    """Test the read_performance_report function with a general error."""
    # Set up the mock to raise a general exception
    mock_rds_client.get_performance_analysis_report.side_effect = ValueError("Unexpected error")
    
    # Call the resource function with the patched connection
    with patch.object(PIConnectionManager, 'get_connection', return_value=mock_rds_client):
        result = await read_performance_report(dbi_resource_identifier="test-instance-1", report_id="report-123")
    
    # Verify the error response
    result_dict = json.loads(result)
    assert 'error' in result_dict
    assert 'Unexpected error' in result_dict['error']
