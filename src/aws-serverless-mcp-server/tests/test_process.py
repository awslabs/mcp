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
"""Tests for the process utility module."""

import asyncio
import pytest
from awslabs.aws_serverless_mcp_server.utils.process import run_command
from unittest.mock import AsyncMock, patch


class TestProcess:
    """Tests for the process utility module."""

    @pytest.mark.asyncio
    async def test_run_command_success(self):
        """Test run_command with a successful command execution."""
        # Mock the subprocess
        mock_process = AsyncMock()
        mock_process.returncode = 0
        mock_process.communicate = AsyncMock(return_value=(b'stdout output', b'stderr output'))

        # Patch asyncio.create_subprocess_exec to return our mock process
        with patch(
            'asyncio.create_subprocess_exec', return_value=mock_process
        ) as mock_create_subprocess:
            # Call the function
            cmd_list = ['echo', 'hello']
            stdout, stderr = await run_command(cmd_list)

            # Verify the result
            assert stdout == b'stdout output'
            assert stderr == b'stderr output'

            # Verify the subprocess was created correctly
            mock_create_subprocess.assert_called_once_with(
                *cmd_list, cwd=None, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            mock_process.communicate.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_command_with_cwd(self):
        """Test run_command with a specified working directory."""
        # Mock the subprocess
        mock_process = AsyncMock()
        mock_process.returncode = 0
        mock_process.communicate = AsyncMock(return_value=(b'stdout output', b'stderr output'))

        # Patch asyncio.create_subprocess_exec to return our mock process
        with patch(
            'asyncio.create_subprocess_exec', return_value=mock_process
        ) as mock_create_subprocess:
            # Call the function with a working directory
            cmd_list = ['ls', '-la']
            cwd = '/dir'
            stdout, stderr = await run_command(cmd_list, cwd=cwd)

            # Verify the result
            assert stdout == b'stdout output'
            assert stderr == b'stderr output'

            # Verify the subprocess was created with the correct working directory
            mock_create_subprocess.assert_called_once_with(
                *cmd_list, cwd=cwd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )

    @pytest.mark.asyncio
    async def test_run_command_failure(self):
        """Test run_command when the command fails."""
        # Mock the subprocess
        mock_process = AsyncMock()
        mock_process.returncode = 1
        mock_process.communicate = AsyncMock(return_value=(b'stdout output', b'command failed'))

        # Patch asyncio.create_subprocess_exec to return our mock process
        with patch('asyncio.create_subprocess_exec', return_value=mock_process):
            # Call the function and expect an exception
            cmd_list = ['nonexistent-command']
            with pytest.raises(Exception, match='Command failed: command failed'):
                await run_command(cmd_list)

            # Verify communicate was called
            mock_process.communicate.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_command_complex_command(self):
        """Test run_command with a more complex command."""
        # Mock the subprocess
        mock_process = AsyncMock()
        mock_process.returncode = 0
        mock_process.communicate = AsyncMock(return_value=(b'stdout output', b'stderr output'))

        # Patch asyncio.create_subprocess_exec to return our mock process
        with patch(
            'asyncio.create_subprocess_exec', return_value=mock_process
        ) as mock_create_subprocess:
            # Call the function with a more complex command
            cmd_list = ['npm', 'install', '--save-dev', 'jest']
            stdout, stderr = await run_command(cmd_list)

            # Verify the result
            assert stdout == b'stdout output'
            assert stderr == b'stderr output'

            # Verify the subprocess was created correctly
            mock_create_subprocess.assert_called_once_with(
                *cmd_list, cwd=None, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
