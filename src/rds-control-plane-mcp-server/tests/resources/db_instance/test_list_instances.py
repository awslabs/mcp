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

"""Tests for list_instances resource."""

import json
import pytest
from unittest.mock import MagicMock, patch

from awslabs.rds_control_plane_mcp_server.resources.db_instance.list_instances import list_instances
from awslabs.rds_control_plane_mcp_server.common.connection import RDSConnectionManager
from awslabs.rds_control_plane_mcp_server.common.models import InstanceModel


@pytest.mark.asyncio
async def test_list_instances_success(mock_rds_client):
    """Test the list_instances function with successful return."""
    # Call the resource function with the patched connection
    with patch.object(RDSConnectionManager, 'get_connection', return_value=mock_rds_client):
        result = await list_instances()
    
    # Verify the result is well-formed
    result_dict = json.loads(result)
    assert 'instances' in result_dict
    assert 'count' in result_dict
    assert 'resource_uri' in result_dict
    assert result_dict['count'] == 2  # From mock_rds_client fixture
    assert isinstance(result_dict['instances'], list)
    
    # Verify the first instance data
    assert result_dict['instances'][0]['instance_id'] == 'test-instance-1'
    assert result_dict['instances'][0]['status'] == 'available'
    assert result_dict['instances'][0]['engine'] == 'aurora-mysql'


@pytest.mark.asyncio
async def test_list_instances_empty(mock_rds_client):
    """Test the list_instances function with empty response."""
    # Override the mock to return empty instances list
    mock_rds_client.describe_db_instances.return_value = {'DBInstances': []}
    
    # Call the resource function with the patched connection
    with patch.object(RDSConnectionManager, 'get_connection', return_value=mock_rds_client):
        result = await list_instances()
    
    # Verify the result is well-formed
    result_dict = json.loads(result)
    assert 'instances' in result_dict
    assert 'count' in result_dict
    assert result_dict['count'] == 0
    assert isinstance(result_dict['instances'], list)
    assert len(result_dict['instances']) == 0


@pytest.mark.asyncio
async def test_list_instances_with_pagination(mock_rds_client):
    """Test the list_instances function with pagination."""
    # Set up pagination mock
    mock_rds_client.describe_db_instances.side_effect = [
        {
            'DBInstances': [{'DBInstanceIdentifier': 'instance-1'}],
            'Marker': 'next-page'
        },
        {
            'DBInstances': [{'DBInstanceIdentifier': 'instance-2'}]
        }
    ]
    
    # Call the resource function with the patched connection
    with patch.object(RDSConnectionManager, 'get_connection', return_value=mock_rds_client):
        result = await list_instances()
    
    # Verify the result is well-formed
    result_dict = json.loads(result)
    assert 'instances' in result_dict
    assert 'count' in result_dict
    assert result_dict['count'] == 2
    
    # Verify both instances are included
    instance_ids = [instance['instance_id'] for instance in result_dict['instances']]
    assert 'instance-1' in instance_ids
    assert 'instance-2' in instance_ids
    

@pytest.mark.asyncio
async def test_list_instances_client_error(mock_rds_client):
    """Test the list_instances function with a client error."""
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
    
    # Call the resource function with the patched connection
    with patch.object(RDSConnectionManager, 'get_connection', return_value=mock_rds_client):
        result = await list_instances()
    
    # Verify the error response
    result_dict = json.loads(result)
    assert 'error' in result_dict
    assert 'error_code' in result_dict
    assert result_dict['error_code'] == 'AccessDenied'


@pytest.mark.asyncio
async def test_list_instances_general_error(mock_rds_client):
    """Test the list_instances function with a general error."""
    # Set up the mock to raise a general exception
    mock_rds_client.describe_db_instances.side_effect = ValueError("Unexpected error")
    
    # Call the resource function with the patched connection
    with patch.object(RDSConnectionManager, 'get_connection', return_value=mock_rds_client):
        result = await list_instances()
    
    # Verify the error response
    result_dict = json.loads(result)
    assert 'error' in result_dict
    assert 'error_type' in result_dict
    assert result_dict['error_type'] == 'ValueError'
