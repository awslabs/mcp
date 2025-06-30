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

"""Tests for get_instance_detail resource."""

import json
import pytest
from unittest.mock import MagicMock, patch

from awslabs.rds_control_plane_mcp_server.resources.db_instance.get_instance_detail import get_instance_detail
from awslabs.rds_control_plane_mcp_server.common.models import InstanceModel


@pytest.mark.asyncio
async def test_get_instance_detail_success(mock_rds_client):
    """Test the get_instance_detail function with successful return."""
    # Call the resource function with a valid instance ID
    with patch('awslabs.rds_control_plane_mcp_server.common.connection.RDSConnectionManager.get_connection', return_value=mock_rds_client):
        result = await get_instance_detail(instance_id="test-instance-1")
    
    # Verify the result is well-formed
    result_dict = json.loads(result)
    assert result_dict['instance_id'] == 'test-instance-1'
    assert result_dict['status'] == 'available'
    assert result_dict['engine'] == 'aurora-mysql'
    assert result_dict['engine_version'] == '5.7.12'
    assert result_dict['instance_class'] == 'db.r5.large'
    
    # Check endpoint details
    assert 'endpoint' in result_dict
    assert result_dict['endpoint']['address'] == 'test-instance-1.abc123.us-east-1.rds.amazonaws.com'
    assert result_dict['endpoint']['port'] == 3306
    
    # Check cluster association
    assert result_dict['db_cluster'] == 'test-cluster'


@pytest.mark.asyncio
async def test_get_instance_detail_not_found(mock_rds_client):
    """Test the get_instance_detail function when instance doesn't exist."""
    # Set up the mock to return no instances
    mock_rds_client.describe_db_instances.return_value = {'DBInstances': []}
    
    # Call the resource function with a non-existent instance ID
    with patch('awslabs.rds_control_plane_mcp_server.common.connection.RDSConnectionManager.get_connection', return_value=mock_rds_client):
        result = await get_instance_detail(instance_id="non-existent-instance")
    
    # Verify the error response
    result_dict = json.loads(result)
    assert 'error' in result_dict
    assert 'not found' in result_dict['error'].lower()


@pytest.mark.asyncio
async def test_get_instance_detail_client_error(mock_rds_client):
    """Test the get_instance_detail function with a client error."""
    # Set up the mock to raise a client error
    from botocore.exceptions import ClientError
    error_response = {
        'Error': {
            'Code': 'AccessDenied',
            'Message': 'User is not authorized to perform operation'
        }
    }
    mock_rds_client.describe_db_instances.side_effect = ClientError(
        error_response, 'DescribeDBInstances'
    )
    
    # Call the resource function
    with patch('awslabs.rds_control_plane_mcp_server.common.connection.RDSConnectionManager.get_connection', return_value=mock_rds_client):
        result = await get_instance_detail(instance_id="test-instance")
    
    # Verify the error response
    result_dict = json.loads(result)
    assert 'error' in result_dict
    assert 'error_code' in result_dict
    assert result_dict['error_code'] == 'AccessDenied'


@pytest.mark.asyncio
async def test_get_instance_detail_general_error(mock_rds_client):
    """Test the get_instance_detail function with a general error."""
    # Set up the mock to raise a general exception
    mock_rds_client.describe_db_instances.side_effect = ValueError("Unexpected error")
    
    # Call the resource function
    with patch('awslabs.rds_control_plane_mcp_server.common.connection.RDSConnectionManager.get_connection', return_value=mock_rds_client):
        result = await get_instance_detail(instance_id="test-instance")
    
    # Verify the error response
    result_dict = json.loads(result)
    assert 'error' in result_dict
    assert 'error_type' in result_dict
    assert result_dict['error_type'] == 'ValueError'


@pytest.mark.asyncio
async def test_get_instance_detail_with_resource_uri(mock_rds_client):
    """Test that get_instance_detail sets the resource_uri field properly."""
    # Call the resource function
    with patch('awslabs.rds_control_plane_mcp_server.common.connection.RDSConnectionManager.get_connection', return_value=mock_rds_client):
        result = await get_instance_detail(instance_id="test-instance-1")
    
    # Verify resource_uri is correctly set
    result_dict = json.loads(result)
    assert 'resource_uri' in result_dict
    assert result_dict['resource_uri'] == 'aws-rds://db-instance/test-instance-1'
