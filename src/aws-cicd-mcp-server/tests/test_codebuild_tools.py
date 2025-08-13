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

"""Tests for CodeBuild tools."""

import pytest
from unittest.mock import patch, MagicMock
from botocore.exceptions import ClientError
from awslabs.aws_cicd_mcp_server.core.codebuild import tools


@patch('boto3.client')
@pytest.mark.asyncio
async def test_list_projects(mock_boto_client):
    """Test listing CodeBuild projects."""
    mock_client = MagicMock()
    mock_client.list_projects.return_value = {
        'projects': ['project1', 'project2']
    }
    mock_boto_client.return_value = mock_client
    
    result = await tools.list_projects()
    
    assert "projects" in result
    assert "count" in result
    assert result["count"] == 2
    assert result["projects"] == ['project1', 'project2']


@patch('boto3.client')
@pytest.mark.asyncio
async def test_list_projects_error(mock_boto_client):
    """Test listing projects with error."""
    mock_client = MagicMock()
    mock_client.list_projects.side_effect = ClientError(
        {'Error': {'Code': 'AccessDenied', 'Message': 'Access denied'}},
        'ListProjects'
    )
    mock_boto_client.return_value = mock_client
    
    result = await tools.list_projects()
    
    assert "error" in result
    assert "projects" in result


@pytest.mark.asyncio
async def test_start_build_readonly_mode():
    """Test start build in read-only mode."""
    result = await tools.start_build("test-project")
    
    assert "error" in result
    assert "read-only mode" in result["error"].lower()


@pytest.mark.asyncio
async def test_create_project_readonly_mode():
    """Test create project in read-only mode."""
    result = await tools.create_project(
        project_name="test-project",
        service_role="arn:aws:iam::123456789012:role/test-role",
        source_location="https://github.com/test/repo"
    )
    
    assert "error" in result
    assert "read-only mode" in result["error"].lower()
