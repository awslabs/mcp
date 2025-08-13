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

"""Tests for read-only mode security."""

import pytest
from awslabs.aws_cicd_mcp_server.core.common.config import READ_ONLY_MODE


def test_readonly_mode_enabled():
    """Test that read-only mode is enabled by default."""
    assert READ_ONLY_MODE is True


@pytest.mark.asyncio
async def test_write_operations_blocked():
    """Test that write operations are blocked in read-only mode."""
    from awslabs.aws_cicd_mcp_server.core.codepipeline import tools as pipeline_tools
    from awslabs.aws_cicd_mcp_server.core.codebuild import tools as build_tools
    from awslabs.aws_cicd_mcp_server.core.codedeploy import tools as deploy_tools
    
    # Test CodePipeline write operations
    result = await pipeline_tools.start_pipeline_execution("test-pipeline")
    assert "error" in result
    assert "read-only mode" in result["error"].lower()
    
    result = await pipeline_tools.create_pipeline(
        "test-pipeline", "test-role", "test-bucket", "test-repo"
    )
    assert "error" in result
    assert "read-only mode" in result["error"].lower()
    
    # Test CodeBuild write operations
    result = await build_tools.start_build("test-project")
    assert "error" in result
    assert "read-only mode" in result["error"].lower()
    
    result = await build_tools.create_project(
        "test-project", "test-role", "test-location"
    )
    assert "error" in result
    assert "read-only mode" in result["error"].lower()
    
    # Test CodeDeploy write operations
    result = await deploy_tools.create_deployment(
        "test-app", "test-group", "test-bucket", "test-key"
    )
    assert "error" in result
    assert "read-only mode" in result["error"].lower()
    
    result = await deploy_tools.create_application("test-app")
    assert "error" in result
    assert "read-only mode" in result["error"].lower()
