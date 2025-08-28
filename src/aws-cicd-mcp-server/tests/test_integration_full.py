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

"""Integration tests for AWS CI/CD MCP Server."""

import pytest
from moto import mock_aws
from awslabs.aws_cicd_mcp_server.core.codepipeline import tools as pipeline_tools
from awslabs.aws_cicd_mcp_server.core.codebuild import tools as build_tools
from awslabs.aws_cicd_mcp_server.core.codedeploy import tools as deploy_tools


@pytest.mark.asyncio
async def test_full_cicd_workflow():
    """Test full CI/CD workflow integration."""
    with mock_aws():
        # Test listing all services
        pipelines = await pipeline_tools.list_pipelines()
        projects = await build_tools.list_projects()
        applications = await deploy_tools.list_applications()
        
        assert "pipelines" in pipelines
        assert "projects" in projects
        assert "applications" in applications
        
        # All should return empty lists initially
        assert pipelines["count"] == 0
        assert projects["count"] == 0
        assert applications["count"] == 0


@pytest.mark.asyncio
async def test_error_handling():
    """Test error handling across all services."""
    # Test with non-existent resources
    result = await pipeline_tools.get_pipeline_details("non-existent")
    assert "error" in result
    
    result = await build_tools.get_project_details("non-existent")
    assert "error" in result
    
    result = await deploy_tools.get_application_details("non-existent")
    assert "error" in result


@pytest.mark.asyncio
async def test_parameter_validation():
    """Test parameter validation."""
    # Test with valid parameters
    result = await pipeline_tools.list_pipelines("us-east-1")
    assert "pipelines" in result
    
    result = await build_tools.list_projects("us-east-1")
    assert "projects" in result
    
    result = await deploy_tools.list_applications("us-east-1")
    assert "applications" in result
