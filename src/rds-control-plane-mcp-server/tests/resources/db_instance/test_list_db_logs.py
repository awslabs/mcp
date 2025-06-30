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

"""Tests for list_db_log_files resource."""

import json
import pytest
from unittest.mock import MagicMock, patch

from awslabs.rds_control_plane_mcp_server.resources.db_instance.list_db_logs import list_db_log_files
from awslabs.rds_control_plane_mcp_server.common.connection import RDSConnectionManager


@pytest.mark.asyncio
async def test_list_db_logs_success(mock_rds_client):
    """Test the list_db_log_files function with successful return."""
    mock_rds_client.describe_db_log_files.return_value = {
        'DescribeDBLogFiles': [
            {
                'LogFileName': 'error/mysql-error.log',
                'LastWritten': 1625097600000,
                'Size': 1024
            },
            {
                'LogFileName': 'error/mysql-error-running.log',
                'LastWritten': 1625098200000,
                'Size': 512
            }
        ]
    }
    
    paginator_mock = MagicMock()
    paginator_mock.paginate.return_value = [{
        'DescribeDBLogFiles': [
            {
                'LogFileName': 'error/mysql-error.log',
                'LastWritten': 1625097600000,
                'Size': 1024
            },
            {
                'LogFileName': 'error/mysql-error-running.log',
                'LastWritten': 1625098200000,
                'Size': 512
            }
        ]
    }]
    mock_rds_client.get_paginator.return_value = paginator_mock
    
    with patch.object(RDSConnectionManager, 'get_connection', return_value=mock_rds_client):
        result = await list_db_log_files(db_instance_identifier="test-instance-1")
    
    result_dict = json.loads(result)
    assert 'log_files' in result_dict
    assert 'count' in result_dict
    assert 'resource_uri' in result_dict
    
    assert result_dict['count'] == 2
    
    assert len(result_dict['log_files']) == 2
    assert result_dict['log_files'][0]['log_file_name'] == 'error/mysql-error.log'
    assert result_dict['log_files'][0]['size'] == 1024
    assert 'last_written' in result_dict['log_files'][0]


@pytest.mark.asyncio
async def test_list_db_logs_empty(mock_rds_client):
    """Test the list_db_log_files function with empty response."""
    paginator_mock = MagicMock()
    paginator_mock.paginate.return_value = [{'DescribeDBLogFiles': []}]
    mock_rds_client.get_paginator.return_value = paginator_mock
    
    with patch.object(RDSConnectionManager, 'get_connection', return_value=mock_rds_client):
        result = await list_db_log_files(db_instance_identifier="test-instance-1")
    
    result_dict = json.loads(result)
    assert 'log_files' in result_dict
    assert 'count' in result_dict
    assert 'resource_uri' in result_dict
    assert result_dict['count'] == 0
    assert len(result_dict['log_files']) == 0

@pytest.mark.asyncio
async def test_list_db_logs_client_error(mock_rds_client):
    """Test the list_db_log_files function with a client error."""
    from botocore.exceptions import ClientError
    error_response = {
        'Error': {
            'Code': 'DBInstanceNotFound',
            'Message': 'DB instance not found'
        }
    }
    mock_rds_client.get_paginator.side_effect = ClientError(
        error_response, 'DescribeDBLogFiles'
    )
    
    with patch.object(RDSConnectionManager, 'get_connection', return_value=mock_rds_client):
        result = await list_db_log_files(db_instance_identifier="non-existent-instance")
    
    result_dict = json.loads(result)
    assert 'error' in result_dict
    assert 'error_code' in result_dict
    assert result_dict['error_code'] == 'DBInstanceNotFound'


@pytest.mark.asyncio
async def test_list_db_logs_general_error(mock_rds_client):
    """Test the list_db_log_files function with a general error."""
    mock_rds_client.get_paginator.side_effect = ValueError("Unexpected error")
    
    with patch.object(RDSConnectionManager, 'get_connection', return_value=mock_rds_client):
        result = await list_db_log_files(db_instance_identifier="test-instance")
    
    result_dict = json.loads(result)
    assert 'error' in result_dict
    assert 'error_type' in result_dict
    assert result_dict['error_type'] == 'ValueError'
