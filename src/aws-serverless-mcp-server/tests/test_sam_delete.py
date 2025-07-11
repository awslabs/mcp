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
"""Tests for the sam_delete module."""

import os
import pytest
import subprocess
import tempfile
from awslabs.aws_serverless_mcp_server.tools.sam.sam_delete import SamDeleteTool
from unittest.mock import AsyncMock, MagicMock, patch


class TestSamDelete:
    """Tests for the sam_delete function."""

    @pytest.mark.asyncio
    async def test_sam_delete_success(self):
        """Test successful SAM deletion."""
        # Mock the subprocess.run function
        mock_result = MagicMock()
        mock_result.stdout = b'Successfully deleted SAM project'
        mock_result.stderr = b''

        with patch(
            'awslabs.aws_serverless_mcp_server.tools.sam.sam_delete.run_command',
            return_value=(mock_result.stdout, mock_result.stderr),
        ) as mock_run:
            # Call the function
            result = await SamDeleteTool(MagicMock(), True).handle_sam_delete(
                AsyncMock(),
                stack_name='test-app',
                project_directory=os.path.join(tempfile.gettempdir(), 'test-project'),
                region=None,
                profile=None,
                config_file=None,
                config_env=None,
                s3_bucket=None,
                s3_prefix=None,
                beta_features=None,
                debug=False,
                save_params=False,
            )

            # Verify the result
            assert result['success'] is True
            assert 'SAM project deleted successfully' in result['message']
            assert result['output'] == 'Successfully deleted SAM project'

            # Verify run_command was called with the correct arguments
            mock_run.assert_called_once()
            args, kwargs = mock_run.call_args
            cmd = args[0]

            # Check required parameters
            assert 'sam' in cmd
            assert 'delete' in cmd
            assert '--stack-name' in cmd
            assert 'test-app' in cmd
            assert '--no-prompts' in cmd  # Always included
            assert kwargs['cwd'] == os.path.join(tempfile.gettempdir(), 'test-project')

    @pytest.mark.asyncio
    async def test_sam_delete_with_optional_params(self):
        """Test SAM deletion with optional parameters."""
        # Mock the subprocess.run function
        mock_result = MagicMock()
        mock_result.stdout = b'Successfully deleted SAM project'
        mock_result.stderr = b''

        with patch(
            'awslabs.aws_serverless_mcp_server.tools.sam.sam_delete.run_command',
            return_value=(mock_result.stdout, mock_result.stderr),
        ) as mock_run:
            # Call the function
            result = await SamDeleteTool(MagicMock(), True).handle_sam_delete(
                AsyncMock(),
                stack_name='test-app',
                project_directory=os.path.join(tempfile.gettempdir(), 'test-project'),
                region='us-west-2',
                profile='default',
                config_file='samconfig.toml',
                config_env='dev',
                s3_bucket='my-bucket',
                s3_prefix='my-prefix',
                beta_features=True,
                debug=True,
                save_params=True,
            )

            # Verify the result
            assert result['success'] is True

            # Verify run_command was called with the correct arguments
            mock_run.assert_called_once()
            args, kwargs = mock_run.call_args
            cmd = args[0]

            # Check optional parameters
            assert '--region' in cmd
            assert 'us-west-2' in cmd
            assert '--profile' in cmd
            assert 'default' in cmd
            assert '--config-file' in cmd
            assert 'samconfig.toml' in cmd
            assert '--config-env' in cmd
            assert 'dev' in cmd
            assert '--no-prompts' in cmd  # Always included
            assert '--s3-bucket' in cmd
            assert 'my-bucket' in cmd
            assert '--s3-prefix' in cmd
            assert 'my-prefix' in cmd
            assert '--beta-features' in cmd
            assert '--debug' in cmd
            assert '--save-params' in cmd

    @pytest.mark.asyncio
    async def test_sam_delete_with_no_beta_features(self):
        """Test SAM deletion with no beta features."""
        # Mock the subprocess.run function
        mock_result = MagicMock()
        mock_result.stdout = b'Successfully deleted SAM project'
        mock_result.stderr = b''

        with patch(
            'awslabs.aws_serverless_mcp_server.tools.sam.sam_delete.run_command',
            return_value=(mock_result.stdout, mock_result.stderr),
        ) as mock_run:
            # Call the function
            result = await SamDeleteTool(MagicMock(), True).handle_sam_delete(
                AsyncMock(),
                stack_name='test-app',
                project_directory=os.path.join(tempfile.gettempdir(), 'test-project'),
                beta_features=False,
            )

            # Verify the result
            assert result['success'] is True

            # Verify run_command was called with the correct arguments
            mock_run.assert_called_once()
            args, kwargs = mock_run.call_args
            cmd = args[0]

            # Check beta_features parameter
            assert '--no-beta-features' in cmd
            assert '--no-prompts' in cmd  # Always included

    @pytest.mark.asyncio
    async def test_sam_delete_failure(self):
        """Test SAM deletion failure."""
        # Mock the subprocess.run function to raise an exception
        error_message = b'Command failed with exit code 1'
        with patch(
            'awslabs.aws_serverless_mcp_server.tools.sam.sam_delete.run_command',
            side_effect=subprocess.CalledProcessError(1, 'sam delete', stderr=error_message),
        ):
            # Call the function
            result = await SamDeleteTool(MagicMock(), True).handle_sam_delete(
                AsyncMock(),
                stack_name='test-app',
                project_directory=os.path.join(tempfile.gettempdir(), 'test-project'),
                region=None,
                profile=None,
                config_file=None,
                config_env=None,
                s3_bucket=None,
                s3_prefix=None,
                beta_features=None,
                debug=False,
                save_params=False,
            )

            # Verify the result
            assert result['success'] is False
            assert 'Failed to delete SAM project' in result['message']
            assert 'Command failed with exit code 1' in result['message']

    @pytest.mark.asyncio
    async def test_sam_delete_general_exception(self):
        """Test SAM deletion with a general exception."""
        # Mock the subprocess.run function to raise a general exception
        error_message = 'Some unexpected error'
        with patch(
            'awslabs.aws_serverless_mcp_server.tools.sam.sam_delete.run_command',
            side_effect=Exception(error_message),
        ):
            # Call the function
            result = await SamDeleteTool(MagicMock(), True).handle_sam_delete(
                AsyncMock(),
                stack_name='test-app',
                project_directory=os.path.join(tempfile.gettempdir(), 'test-project'),
                region=None,
                profile=None,
                config_file=None,
                config_env=None,
                s3_bucket=None,
                s3_prefix=None,
                beta_features=None,
                debug=False,
                save_params=False,
            )

            # Verify the result
            assert result['success'] is False
            assert 'Failed to delete SAM project' in result['message']
            assert error_message in result['message']

    @pytest.mark.asyncio
    async def test_sam_delete_allow_write_false(self):
        """Test SAM deletion when allow_write is False."""
        # Create the tool with allow_write set to False
        tool = SamDeleteTool(MagicMock(), allow_write=False)

        # Call the function
        with pytest.raises(Exception) as exc_info:
            await tool.handle_sam_delete(
                AsyncMock(),
                stack_name='test-app',
                project_directory=os.path.join(tempfile.gettempdir(), 'test-project'),
                region=None,
                profile=None,
                config_file=None,
                config_env=None,
                s3_bucket=None,
                s3_prefix=None,
                beta_features=None,
                debug=False,
                save_params=False,
            )

        # Verify the exception message
        assert (
            'Write operations are not allowed. Set --allow-write flag to true to enable write operations.'
            in str(exc_info.value)
        )
