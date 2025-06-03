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
"""Tests for the sam_build module."""

import os
import pytest
import subprocess
import tempfile
from awslabs.aws_serverless_mcp_server.tools.sam.sam_build import SamBuildTool
from unittest.mock import AsyncMock, MagicMock, patch


class TestSamBuild:
    """Tests for the sam_build function."""

    @pytest.mark.asyncio
    async def test_sam_build_success(self):
        """Test successful SAM build."""
        # Mock the subprocess.run function
        mock_result = MagicMock()
        mock_result.stdout = b'Successfully built SAM project'
        mock_result.stderr = b''

        with patch(
            'awslabs.aws_serverless_mcp_server.tools.sam.sam_build.run_command',
            return_value=(mock_result.stdout, mock_result.stderr),
        ) as mock_run:
            # Call the function
            result = await SamBuildTool(MagicMock()).handle_sam_build(
                AsyncMock(),
                project_directory=os.path.join(tempfile.gettempdir(), 'test-project'),
                template_file=None,
                base_dir=None,
                build_dir=None,
                use_container=False,
                no_use_container=False,
                container_env_vars=None,
                container_env_var_file=None,
                build_image=None,
                debug=False,
                manifest=None,
                parameter_overrides=None,
                region=None,
                save_params=False,
                profile=None,
            )

            # Verify the result
            assert result['success'] is True
            assert 'SAM project built successfully' in result['message']
            assert result['output'] == 'Successfully built SAM project'

            # Verify run_command was called with the correct arguments
            mock_run.assert_called_once()
            args, kwargs = mock_run.call_args
            cmd = args[0]

            # Check required parameters
            assert 'sam' in cmd
            assert 'build' in cmd
            assert kwargs['cwd'] == os.path.join(tempfile.gettempdir(), 'test-project')

    @pytest.mark.asyncio
    async def test_sam_build_with_optional_params(self):
        """Test SAM build with optional parameters."""
        # Mock the subprocess.run function
        mock_result = MagicMock()
        mock_result.stdout = b'Successfully built SAM project'
        mock_result.stderr = b''

        with patch(
            'awslabs.aws_serverless_mcp_server.tools.sam.sam_build.run_command',
            return_value=(mock_result.stdout, mock_result.stderr),
        ) as mock_run:
            # Call the function
            result = await SamBuildTool(MagicMock()).handle_sam_build(
                AsyncMock(),
                project_directory=os.path.join(tempfile.gettempdir(), 'test-project'),
                template_file='template.yaml',
                base_dir=os.path.join(tempfile.gettempdir(), 'base-dir'),
                build_dir=os.path.join(tempfile.gettempdir(), 'build-dir'),
                use_container=True,
                no_use_container=False,
                container_env_vars={'ENV1': 'value1', 'ENV2': 'value2'},
                container_env_var_file='env.json',
                build_image=None,
                debug=True,
                manifest='package.json',
                parameter_overrides='ParameterKey=Key1,ParameterValue=Value1',
                region='us-west-2',
                save_params=False,
                profile=None,
            )
            # Verify the result
            assert result['success'] is True

            # Verify run_command was called with the correct arguments
            mock_run.assert_called_once()
            args, kwargs = mock_run.call_args
            cmd = args[0]

            # Check optional parameters
            assert '--template-file' in cmd
            assert 'template.yaml' in cmd
            assert '--base-dir' in cmd
            assert os.path.join(tempfile.gettempdir(), 'base-dir') in cmd
            assert '--build-dir' in cmd
            assert os.path.join(tempfile.gettempdir(), 'build-dir') in cmd
            assert '--use-container' in cmd
            assert '--container-env-var' in cmd
            assert '--container-env-var-file' in cmd
            assert 'env.json' in cmd
            assert '--debug' in cmd
            assert '--manifest' in cmd
            assert 'package.json' in cmd
            assert '--parameter-overrides' in cmd
            assert '--region' in cmd
            assert 'us-west-2' in cmd

    @pytest.mark.asyncio
    async def test_sam_build_failure(self):
        """Test SAM build failure."""
        # Mock the subprocess.run function to raise an exception
        error_message = b'Command failed with exit code 1'
        with patch(
            'awslabs.aws_serverless_mcp_server.tools.sam.sam_build.run_command',
            side_effect=subprocess.CalledProcessError(1, 'sam build', stderr=error_message),
        ):
            # Call the function
            result = await SamBuildTool(MagicMock()).handle_sam_build(
                AsyncMock(),
                project_directory=os.path.join(tempfile.gettempdir(), 'test-project'),
                template_file=None,
                base_dir=None,
                build_dir=None,
                use_container=False,
                no_use_container=False,
                container_env_vars=None,
                container_env_var_file=None,
                build_image=None,
                debug=False,
                manifest=None,
                parameter_overrides=None,
                region=None,
                save_params=False,
                profile=None,
            )

            # Verify the result
            assert result['success'] is False
            assert 'Failed to build SAM project' in result['message']
            assert 'Command failed with exit code 1' in result['message']

    @pytest.mark.asyncio
    async def test_sam_build_general_exception(self):
        """Test SAM build with a general exception."""
        # Mock the subprocess.run function to raise a general exception
        error_message = 'Some unexpected error'
        with patch(
            'awslabs.aws_serverless_mcp_server.tools.sam.sam_build.run_command',
            side_effect=Exception(error_message),
        ):
            # Call the function
            result = await SamBuildTool(MagicMock()).handle_sam_build(
                AsyncMock(),
                project_directory=os.path.join(tempfile.gettempdir(), 'test-project'),
                template_file=None,
                base_dir=None,
                build_dir=None,
                use_container=False,
                no_use_container=False,
                container_env_vars=None,
                container_env_var_file=None,
                build_image=None,
                debug=False,
                manifest=None,
                parameter_overrides=None,
                region=None,
                save_params=False,
                profile=None,
            )

            # Verify the result
            assert result['success'] is False
            assert 'Failed to build SAM project' in result['message']
            assert error_message in result['message']

    @pytest.mark.asyncio
    async def test_sam_build_with_parallel_default(self):
        """Test SAM build with default parallel parameter (True)."""
        # Mock the subprocess.run function
        mock_result = MagicMock()
        mock_result.stdout = b'Successfully built SAM project'
        mock_result.stderr = b''

        with patch(
            'awslabs.aws_serverless_mcp_server.tools.sam.sam_build.run_command',
            return_value=(mock_result.stdout, mock_result.stderr),
        ) as mock_run:
            # Call the function with default parallel parameter (True)
            result = await SamBuildTool(MagicMock()).handle_sam_build(
                AsyncMock(),
                project_directory=os.path.join(tempfile.gettempdir(), 'test-project'),
                template_file=None,
                base_dir=None,
                build_dir=None,
                use_container=False,
                no_use_container=False,
                container_env_vars=None,
                container_env_var_file=None,
                build_image=None,
                debug=False,
                manifest=None,
                parameter_overrides=None,
                region=None,
                save_params=False,
                profile=None,
            )

            # Verify the result
            assert result['success'] is True
            assert 'SAM project built successfully' in result['message']

            # Verify run_command was called with the correct arguments
            mock_run.assert_called_once()
            args, kwargs = mock_run.call_args
            cmd = args[0]

            # Check that --parallel flag is included by default
            assert '--parallel' in cmd

    @pytest.mark.asyncio
    async def test_sam_build_with_parallel_disabled(self):
        """Test SAM build with parallel parameter set to False."""
        # Mock the subprocess.run function
        mock_result = MagicMock()
        mock_result.stdout = b'Successfully built SAM project'
        mock_result.stderr = b''

        with patch(
            'awslabs.aws_serverless_mcp_server.tools.sam.sam_build.run_command',
            return_value=(mock_result.stdout, mock_result.stderr),
        ) as mock_run:
            # Call the function with parallel=False
            result = await SamBuildTool(MagicMock()).handle_sam_build(
                AsyncMock(),
                project_directory=os.path.join(tempfile.gettempdir(), 'test-project'),
                template_file=None,
                base_dir=None,
                build_dir=None,
                use_container=False,
                no_use_container=False,
                parallel=False,
                container_env_vars=None,
                container_env_var_file=None,
                build_image=None,
                debug=False,
                manifest=None,
                parameter_overrides=None,
                region=None,
                save_params=False,
                profile=None,
            )

            # Verify the result
            assert result['success'] is True
            assert 'SAM project built successfully' in result['message']

            # Verify run_command was called with the correct arguments
            mock_run.assert_called_once()
            args, kwargs = mock_run.call_args
            cmd = args[0]

            # Check that --parallel flag is NOT included when disabled
            assert '--parallel' not in cmd
