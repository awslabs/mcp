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
"""Tests for the sam_local_invoke module."""

import os
import pytest
import tempfile
from awslabs.aws_serverless_mcp_server.models import SamLocalInvokeRequest
from awslabs.aws_serverless_mcp_server.tools.sam.sam_local_invoke import handle_sam_local_invoke
from unittest.mock import MagicMock, mock_open, patch


class TestSamLocalInvoke:
    """Tests for the sam_local_invoke function."""

    @pytest.mark.asyncio
    async def test_sam_local_invoke_success(self):
        """Test successful SAM local invoke."""
        # Create a mock request
        request = SamLocalInvokeRequest(
            project_directory=os.path.join(tempfile.gettempdir(), 'test-project'),
            resource_name='test-function',
            template_file=None,
            event_file=None,
            event_data=None,
            environment_variables_file=None,
            docker_network=None,
            container_env_vars=None,
            parameter=None,
            log_file=None,
            layer_cache_basedir=None,
            region=None,
            profile=None,
        )

        # Mock the subprocess.run function
        mock_result = MagicMock()
        mock_result.stdout = b'{"statusCode": 200, "body": "Success"}'
        mock_result.stderr = b''

        with patch(
            'awslabs.aws_serverless_mcp_server.tools.sam.sam_local_invoke.run_command',
            return_value=(mock_result.stdout, mock_result.stderr),
        ) as mock_run:
            # Call the function
            result = await handle_sam_local_invoke(request)

            # Verify the result
            assert result['success'] is True
            assert 'Successfully invoked resource' in result['message']
            assert result['function_output'] == {'statusCode': 200, 'body': 'Success'}

            # Verify run_command was called with the correct arguments
            mock_run.assert_called_once()
            args, kwargs = mock_run.call_args
            cmd = args[0]

            # Check required parameters
            assert 'sam' in cmd
            assert 'local' in cmd
            assert 'invoke' in cmd
            assert 'test-function' in cmd
            assert kwargs['cwd'] == os.path.join(tempfile.gettempdir(), 'test-project')

    @pytest.mark.asyncio
    async def test_sam_local_invoke_with_event_file(self):
        """Test SAM local invoke with event file."""
        # Create a mock request with event file
        request = SamLocalInvokeRequest(
            project_directory=os.path.join(tempfile.gettempdir(), 'test-project'),
            resource_name='test-function',
            template_file=None,
            event_file=os.path.join(tempfile.gettempdir(), 'event.json'),
            event_data=None,
            environment_variables_file=None,
            docker_network=None,
            container_env_vars=None,
            parameter=None,
            log_file=None,
            layer_cache_basedir=None,
            region=None,
            profile=None,
        )

        # Mock the subprocess.run function
        mock_result = MagicMock()
        mock_result.stdout = b'{"statusCode": 200, "body": "Success"}'
        mock_result.stderr = b''

        with patch(
            'awslabs.aws_serverless_mcp_server.tools.sam.sam_local_invoke.run_command',
            return_value=(mock_result.stdout, mock_result.stderr),
        ) as mock_run:
            # Call the function
            result = await handle_sam_local_invoke(request)

            # Verify the result
            assert result['success'] is True

            # Verify run_command was called with the correct arguments
            mock_run.assert_called_once()
            args, kwargs = mock_run.call_args
            cmd = args[0]

            # Check event file parameter
            assert '--event' in cmd
            assert os.path.join(tempfile.gettempdir(), 'event.json') in cmd

    @pytest.mark.asyncio
    async def test_sam_local_invoke_with_event_data(self):
        """Test SAM local invoke with event data."""
        # Create a mock request with event data
        request = SamLocalInvokeRequest(
            project_directory=os.path.join(tempfile.gettempdir(), 'test-project'),
            resource_name='test-function',
            template_file=None,
            event_file=None,
            event_data='{"key": "value"}',
            environment_variables_file=None,
            docker_network=None,
            container_env_vars=None,
            parameter=None,
            log_file=None,
            layer_cache_basedir=None,
            region=None,
            profile=None,
        )

        # Mock the subprocess.run function
        mock_result = MagicMock()
        mock_result.stdout = b'{"statusCode": 200, "body": "Success"}'
        mock_result.stderr = b''

        # Mock tempfile and os functions
        mock_fd = 123
        mock_temp_file = os.path.join(tempfile.gettempdir(), 'test-project/.temp-event-12345.json')

        with (
            patch('tempfile.mkstemp', return_value=(mock_fd, mock_temp_file)) as mock_mkstemp,
            patch('os.fdopen', mock_open()) as mock_file,
            patch('os.unlink') as mock_unlink,
            patch('os.path.exists', return_value=True),
            patch(
                'awslabs.aws_serverless_mcp_server.tools.sam.sam_local_invoke.run_command',
                return_value=(mock_result.stdout, mock_result.stderr),
            ) as mock_run,
        ):
            # Call the function
            result = await handle_sam_local_invoke(request)

            # Verify the result
            assert result['success'] is True

            # Verify tempfile.mkstemp was called
            mock_mkstemp.assert_called_once()

            # Verify os.fdopen was called
            mock_file.assert_called_once_with(mock_fd, 'w')

            # Verify file write was called with the event data
            mock_file().write.assert_called_once_with('{"key": "value"}')

            # Verify run_command was called with the correct arguments
            mock_run.assert_called_once()
            args, kwargs = mock_run.call_args
            cmd = args[0]

            # Check event file parameter
            assert '--event' in cmd
            assert mock_temp_file in cmd

            # Verify temp file was cleaned up
            mock_unlink.assert_called_once_with(mock_temp_file)

    @pytest.mark.asyncio
    async def test_sam_local_invoke_with_optional_params(self):
        """Test SAM local invoke with optional parameters."""
        # Create a mock request with optional parameters
        request = SamLocalInvokeRequest(
            project_directory=os.path.join(tempfile.gettempdir(), 'test-project'),
            resource_name='test-function',
            template_file='template.yaml',
            event_file=None,
            event_data=None,
            environment_variables_file=os.path.join(tempfile.gettempdir(), 'env.json'),
            docker_network='my-network',
            container_env_vars={'CONTAINER_ENV1': 'value1', 'CONTAINER_ENV2': 'value2'},
            parameter={'param1': 'value1', 'param2': 'value2'},
            log_file=os.path.join(tempfile.gettempdir(), 'log.txt'),
            layer_cache_basedir=os.path.join(tempfile.gettempdir(), 'layer-cache'),
            region='us-west-2',
            profile='default',
        )

        # Mock the subprocess.run function
        mock_result = MagicMock()
        mock_result.stdout = b'{"statusCode": 200, "body": "Success"}'
        mock_result.stderr = b''

        with patch(
            'awslabs.aws_serverless_mcp_server.tools.sam.sam_local_invoke.run_command',
            return_value=(mock_result.stdout, mock_result.stderr),
        ) as mock_run:
            # Call the function
            result = await handle_sam_local_invoke(request)

            # Verify the result
            assert result['success'] is True

            # Verify run_command was called with the correct arguments
            mock_run.assert_called_once()
            args, kwargs = mock_run.call_args
            cmd = args[0]

            # Check optional parameters
            assert '--template' in cmd
            assert 'template.yaml' in cmd
            assert '--env-vars' in cmd
            assert '--docker-network' in cmd
            assert 'my-network' in cmd
            assert '--container-env-vars' in cmd
            assert '--parameter-overrides' in cmd
            assert '--log-file' in cmd
            assert os.path.join(tempfile.gettempdir(), 'log.txt') in cmd
            assert '--layer-cache-basedir' in cmd
            assert os.path.join(tempfile.gettempdir(), 'layer-cache') in cmd
            assert '--region' in cmd
            assert 'us-west-2' in cmd
            assert '--profile' in cmd
            assert 'default' in cmd

    @pytest.mark.asyncio
    async def test_sam_local_invoke_non_json_output(self):
        """Test SAM local invoke with non-JSON output."""
        # Create a mock request
        request = SamLocalInvokeRequest(
            project_directory=os.path.join(tempfile.gettempdir(), 'test-project'),
            resource_name='test-function',
            template_file=None,
            event_file=None,
            event_data=None,
            environment_variables_file=None,
            docker_network=None,
            container_env_vars=None,
            parameter=None,
            log_file=None,
            layer_cache_basedir=None,
            region=None,
            profile=None,
        )

        # Mock the subprocess.run function with non-JSON output
        mock_result = MagicMock()
        mock_result.stdout = b'This is not JSON'
        mock_result.stderr = b''

        with patch(
            'awslabs.aws_serverless_mcp_server.tools.sam.sam_local_invoke.run_command',
            return_value=(mock_result.stdout, mock_result.stderr),
        ):
            # Call the function
            result = await handle_sam_local_invoke(request)

            # Verify the result
            assert result['success'] is True
            assert 'Successfully invoked resource' in result['message']
            assert result['function_output'] == 'This is not JSON'

    @pytest.mark.asyncio
    async def test_sam_local_invoke_failure(self):
        """Test SAM local invoke failure."""
        # Create a mock request
        request = SamLocalInvokeRequest(
            project_directory=os.path.join(tempfile.gettempdir(), 'test-project'),
            resource_name='test-function',
            template_file=None,
            event_file=None,
            event_data=None,
            environment_variables_file=None,
            docker_network=None,
            container_env_vars=None,
            parameter=None,
            log_file=None,
            layer_cache_basedir=None,
            region=None,
            profile=None,
        )

        # Mock the subprocess.run function to raise an exception
        error_message = 'Command failed with exit code 1'
        with patch(
            'awslabs.aws_serverless_mcp_server.tools.sam.sam_local_invoke.run_command',
            side_effect=Exception(error_message),
        ):
            # Call the function
            result = await handle_sam_local_invoke(request)

            # Verify the result
            assert result['success'] is False
            assert 'Failed to invoke resource locally' in result['message']
            assert error_message in result['error']
