# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance
# with the License. A copy of the License is located at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES
# OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions
# and limitations under the License.
"""Tests for the sam_pipeline module."""

import pytest
import subprocess
from unittest.mock import patch, MagicMock
from awslabs.aws_lambda_mcp_server.models import SamPipelineRequest
from awslabs.aws_lambda_mcp_server.impl.tools.sam.sam_pipeline import sam_pipeline


class TestSamPipeline:
    """Tests for the sam_pipeline function."""

    @pytest.mark.asyncio
    async def test_sam_pipeline_success(self):
        """Test successful SAM pipeline setup."""
        # Create a mock request
        request = SamPipelineRequest(
            project_directory="/tmp/test-project",
            cicd_provider="github",
            stage="dev"
        )

        # Mock the subprocess.run function
        mock_result = MagicMock()
        mock_result.stdout = "Successfully set up pipeline"
        mock_result.stderr = ""

        with patch('subprocess.run', return_value=mock_result) as mock_run:
            # Call the function
            result = await sam_pipeline(request)

            # Verify the result
            assert result["success"] is True
            assert "Successfully set up pipeline" in result["output"]

            # Verify subprocess.run was called with the correct arguments
            mock_run.assert_called_once()
            args, kwargs = mock_run.call_args
            cmd = args[0]
            
            # Check required parameters
            assert "sam" in cmd
            assert "pipeline" in cmd
            assert "init" in cmd
            assert "--bootstrap" in cmd
            assert "--cicd" in cmd
            assert "github" in cmd
            assert "--stage" in cmd
            assert "dev" in cmd

    @pytest.mark.asyncio
    async def test_sam_pipeline_with_optional_params(self):
        """Test SAM pipeline setup with optional parameters."""
        # Create a mock request with optional parameters
        request = SamPipelineRequest(
            project_directory="/tmp/test-project",
            cicd_provider="github",
            stage="dev",
            bucket="my-bucket",
            bootstrap_ecr=True,
            github_org="my-org",
            deployment_branch="main",
            oidc_provider="github-actions",
            permissions_provider="oidc",
            region="us-west-2",
            save_params=True,
            debug=True
        )

        # Mock the subprocess.run function
        mock_result = MagicMock()
        mock_result.stdout = "Successfully set up pipeline"
        mock_result.stderr = ""

        with patch('subprocess.run', return_value=mock_result) as mock_run:
            # Call the function
            result = await sam_pipeline(request)

            # Verify the result
            assert result["success"] is True

            # Verify subprocess.run was called with the correct arguments
            mock_run.assert_called_once()
            args, kwargs = mock_run.call_args
            cmd = args[0]
            
            # Check optional parameters
            assert "--bucket" in cmd
            assert "my-bucket" in cmd
            assert "--bootstrap-ecr" in cmd
            assert "--github-org" in cmd
            assert "my-org" in cmd
            assert "--deployment-branch" in cmd
            assert "main" in cmd
            assert "--oidc-provider" in cmd
            assert "github-actions" in cmd
            assert "--permissions-provider" in cmd
            assert "oidc" in cmd
            assert "--region" in cmd
            assert "us-west-2" in cmd
            assert "--save-params" in cmd
            assert "--debug" in cmd

    @pytest.mark.asyncio
    async def test_sam_pipeline_failure(self):
        """Test SAM pipeline setup failure."""
        # Create a mock request
        request = SamPipelineRequest(
            project_directory="/tmp/test-project",
            cicd_provider="github",
            stage="dev"
        )

        # Mock the subprocess.run function to raise an exception
        error_message = "Command failed with exit code 1"
        with patch('subprocess.run', side_effect=subprocess.CalledProcessError(1, "sam pipeline init", stderr=error_message)) as mock_run:
            # Call the function
            result = await sam_pipeline(request)

            # Verify the result
            assert result["success"] is False
            assert "Failed to set up SAM pipeline" in result["message"]
            assert error_message in result["message"]

    @pytest.mark.asyncio
    async def test_sam_pipeline_general_exception(self):
        """Test SAM pipeline setup with a general exception."""
        # Create a mock request
        request = SamPipelineRequest(
            project_directory="/tmp/test-project",
            cicd_provider="github",
            stage="dev"
        )

        # Mock the subprocess.run function to raise a general exception
        error_message = "Some unexpected error"
        with patch('subprocess.run', side_effect=Exception(error_message)) as mock_run:
            # Call the function
            result = await sam_pipeline(request)

            # Verify the result
            assert result["success"] is False
            assert "Failed to set up SAM pipeline" in result["message"]
            assert error_message in result["message"]
