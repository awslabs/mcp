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

"""Tests for CodeDeploy tools."""

import pytest
from unittest.mock import patch, MagicMock
from botocore.exceptions import ClientError
from awslabs.aws_cicd_mcp_server.core.codedeploy import tools


@patch('boto3.client')
@pytest.mark.asyncio
async def test_list_applications(mock_boto_client):
    """Test listing CodeDeploy applications."""
    mock_client = MagicMock()
    
    # Mock paginator
    mock_paginator = MagicMock()
    mock_paginator.paginate.return_value = [
        {'applications': ['app1', 'app2']}
    ]
    mock_client.get_paginator.return_value = mock_paginator
    mock_boto_client.return_value = mock_client
    
    result = await tools.list_applications()
    
    assert "applications" in result
    assert "count" in result
    assert result["count"] == 2
    assert result["applications"] == ['app1', 'app2']


@patch('boto3.client')
@pytest.mark.asyncio
async def test_list_applications_error(mock_boto_client):
    """Test listing applications with error."""
    mock_client = MagicMock()
    error = ClientError(
        {'Error': {'Code': 'AccessDenied', 'Message': 'Access denied'}},
        'ListApplications'
    )
    
    # Mock both paginator and direct call to raise the same error
    mock_paginator = MagicMock()
    mock_paginator.paginate.side_effect = error
    mock_client.get_paginator.return_value = mock_paginator
    mock_client.list_applications.side_effect = error
    mock_boto_client.return_value = mock_client
    
    result = await tools.list_applications()
    
    assert "error" in result


@pytest.mark.asyncio
async def test_create_deployment_readonly_mode():
    """Test create deployment in read-only mode."""
    result = await tools.create_deployment(
        application_name="test-app",
        deployment_group_name="test-group",
        s3_location_bucket="test-bucket",
        s3_location_key="test-key"
    )
    
    assert "error" in result
    assert "read-only mode" in result["error"].lower()


@pytest.mark.asyncio
async def test_create_application_readonly_mode():
    """Test create application in read-only mode."""
    result = await tools.create_application("test-app")
    
    assert "error" in result
    assert "read-only mode" in result["error"].lower()
