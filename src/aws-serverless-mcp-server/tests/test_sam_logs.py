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
"""Tests for the sam_logs module."""

import pytest
import subprocess
from awslabs.aws_serverless_mcp_server.tools.sam.sam_logs import SamLogsTool
from unittest.mock import AsyncMock, MagicMock, patch


class TestSamLogs:
    """Tests for the sam_logs function."""

    @pytest.mark.asyncio
    async def test_sam_logs_success(self):
        """Test successful SAM logs retrieval."""
        # Mock the subprocess.run function
        mock_result = MagicMock()
        mock_result.stdout = b'2023-05-21 12:00:00 INFO Lambda function logs'
        mock_result.stderr = b''

        with patch(
            'awslabs.aws_serverless_mcp_server.tools.sam.sam_logs.run_command',
            return_value=(mock_result.stdout, mock_result.stderr),
        ) as mock_run:
            # Call the function
            result = await SamLogsTool(MagicMock(), True).handle_sam_logs(
                AsyncMock(),
                resource_name='test-function',
                stack_name=None,
                start_time=None,
                end_time=None,
                region=None,
                profile=None,
                cw_log_group=None,
                config_env=None,
                config_file=None,
                save_params=False,
            )

            # Verify the result
            assert result['success'] is True
            assert 'Successfully fetched logs' in result['message']
            assert result['output'] == '2023-05-21 12:00:00 INFO Lambda function logs'

            # Verify run_command was called with the correct arguments
            mock_run.assert_called_once()
            args, kwargs = mock_run.call_args
            cmd = args[0]

            # Check required parameters
            assert 'sam' in cmd
            assert 'logs' in cmd
            assert '--name' in cmd
            assert 'test-function' in cmd

    @pytest.mark.asyncio
    async def test_sam_logs_with_optional_params(self):
        """Test SAM logs retrieval with optional parameters."""
        # Create a mock request with optional parameters

        # Mock the subprocess.run function
        mock_result = MagicMock()
        mock_result.stdout = (
            b'{"timestamp": "2023-05-21 12:00:00", "message": "Lambda function logs"}'
        )
        mock_result.stderr = b''

        with patch(
            'awslabs.aws_serverless_mcp_server.tools.sam.sam_logs.run_command',
            return_value=(mock_result.stdout, mock_result.stderr),
        ) as mock_run:
            # Call the function
            result = await SamLogsTool(MagicMock(), True).handle_sam_logs(
                AsyncMock(),
                resource_name='test-function',
                stack_name='test-stack',
                start_time='2023-05-21 00:00:00',
                end_time='2023-05-21 23:59:59',
                region='us-west-2',
                profile='default',
                cw_log_group=[],
                config_env=None,
                config_file=None,
                save_params=False,
            )

            # Verify the result
            assert result['success'] is True

            # Verify run_command was called with the correct arguments
            mock_run.assert_called_once()
            args, kwargs = mock_run.call_args
            cmd = args[0]

            # Check optional parameters
            assert '--stack-name' in cmd
            assert 'test-stack' in cmd
            assert '--start-time' in cmd
            assert '2023-05-21 00:00:00' in cmd
            assert '--end-time' in cmd
            assert '2023-05-21 23:59:59' in cmd
            assert '--region' in cmd
            assert 'us-west-2' in cmd
            assert '--profile' in cmd
            assert 'default' in cmd

    @pytest.mark.asyncio
    async def test_sam_logs_failure(self):
        """Test SAM logs retrieval failure."""
        # Create a mock request

        # Mock the subprocess.run function to raise an exception
        error_message = b'Command failed with exit code 1'
        with patch(
            'awslabs.aws_serverless_mcp_server.tools.sam.sam_logs.run_command',
            side_effect=subprocess.CalledProcessError(1, 'sam logs', stderr=error_message),
        ):
            # Call the function
            result = await SamLogsTool(MagicMock(), True).handle_sam_logs(
                AsyncMock(),
                resource_name='test-function',
                stack_name=None,
                start_time=None,
                end_time=None,
                region=None,
                profile=None,
                cw_log_group=None,
                config_env=None,
                config_file=None,
                save_params=False,
            )

            # Verify the result
            assert result['success'] is False
            assert 'Failed to fetch logs for resource' in result['message']
            assert 'Command failed with exit code 1' in result['message']

    @pytest.mark.asyncio
    async def test_sam_logs_general_exception(self):
        """Test SAM logs retrieval with a general exception."""
        # Mock the subprocess.run function to raise a general exception
        error_message = 'Some unexpected error'
        with patch(
            'awslabs.aws_serverless_mcp_server.tools.sam.sam_logs.run_command',
            side_effect=Exception(error_message),
        ):
            # Call the function
            result = await SamLogsTool(MagicMock(), True).handle_sam_logs(
                AsyncMock(),
                resource_name='test-function',
                stack_name=None,
                start_time=None,
                end_time=None,
                region=None,
                profile=None,
                cw_log_group=None,
                config_env=None,
                config_file=None,
                save_params=False,
            )

            # Verify the result
            assert result['success'] is False
            assert 'Failed to fetch logs for resource' in result['message']
            assert error_message in result['message']

    @pytest.mark.asyncio
    async def test_sam_logs_access_denied(self):
        """Test SAM logs access denied when sensitive data access is disabled."""
        with pytest.raises(Exception) as exc_info:
            await SamLogsTool(MagicMock(), False).handle_sam_logs(
                AsyncMock(),
                resource_name='test-function',
                stack_name=None,
                start_time=None,
                end_time=None,
                region=None,
                profile=None,
                cw_log_group=None,
                config_env=None,
                config_file=None,
                save_params=False,
            )

        assert 'sensitive data access is not allowed' in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_sam_logs_empty_output(self):
        """Test SAM logs with empty output."""
        mock_result = MagicMock()
        mock_result.stdout = b''
        mock_result.stderr = b''

        with patch(
            'awslabs.aws_serverless_mcp_server.tools.sam.sam_logs.run_command',
            return_value=(mock_result.stdout, mock_result.stderr),
        ):
            result = await SamLogsTool(MagicMock(), True).handle_sam_logs(
                AsyncMock(),
                resource_name='test-function',
            )

            assert result['success'] is True
            assert 'No logs found for the specified resource' in result['message']
            assert result['output'] == ''

    @pytest.mark.asyncio
    async def test_sam_logs_with_multiple_cw_log_groups(self):
        """Test SAM logs with multiple CloudWatch log groups."""
        mock_result = MagicMock()
        mock_result.stdout = b'Logs from multiple groups'
        mock_result.stderr = b''

        with patch(
            'awslabs.aws_serverless_mcp_server.tools.sam.sam_logs.run_command',
            return_value=(mock_result.stdout, mock_result.stderr),
        ) as mock_run:
            result = await SamLogsTool(MagicMock(), True).handle_sam_logs(
                AsyncMock(),
                cw_log_group=['/aws/lambda/func1', '/aws/lambda/func2', '/aws/apigateway/api'],
            )

            mock_run.assert_called_once()
            args, kwargs = mock_run.call_args
            cmd = args[0]

            assert '--cw-log-group' in cmd
            assert '/aws/lambda/func1' in cmd
            assert '/aws/lambda/func2' in cmd
            assert '/aws/apigateway/api' in cmd
            assert result['success'] is True

    @pytest.mark.asyncio
    async def test_sam_logs_with_config_params(self):
        """Test SAM logs with configuration parameters."""
        mock_result = MagicMock()
        mock_result.stdout = b'Config-based logs'
        mock_result.stderr = b''

        with patch(
            'awslabs.aws_serverless_mcp_server.tools.sam.sam_logs.run_command',
            return_value=(mock_result.stdout, mock_result.stderr),
        ) as mock_run:
            result = await SamLogsTool(MagicMock(), True).handle_sam_logs(
                AsyncMock(),
                config_env='production',
                config_file='/path/to/samconfig.toml',
                save_params=True,
            )

            mock_run.assert_called_once()
            args, kwargs = mock_run.call_args
            cmd = args[0]

            assert '--config-env' in cmd
            assert 'production' in cmd
            assert '--config-file' in cmd
            assert '/path/to/samconfig.toml' in cmd
            assert '--save-params' in cmd
            assert result['success'] is True

    @pytest.mark.asyncio
    async def test_sam_logs_parameter_type_validation(self):
        """Test parameter type validation in SAM logs."""
        mock_result = MagicMock()
        mock_result.stdout = b'Valid parameters'
        mock_result.stderr = b''

        with patch(
            'awslabs.aws_serverless_mcp_server.tools.sam.sam_logs.run_command',
            return_value=(mock_result.stdout, mock_result.stderr),
        ) as mock_run:
            # Test with non-string values for string parameters
            result = await SamLogsTool(
                MagicMock(), True
            ).handle_sam_logs(
                AsyncMock(),
                resource_name='123',  # String value that would be ignored if it were actually non-string
                region='us-east-1',  # String value
                save_params=True,  # Boolean value
            )

            mock_run.assert_called_once()
            args, kwargs = mock_run.call_args
            cmd = args[0]

            # Should include valid string/boolean parameters
            assert 'sam' in cmd
            assert 'logs' in cmd
            assert '--name' in cmd
            assert '123' in cmd
            assert '--region' in cmd
            assert 'us-east-1' in cmd
            assert '--save-params' in cmd
            # Function should succeed
            assert result['success'] is True

    @pytest.mark.asyncio
    async def test_sam_logs_with_sensitive_data_sanitization(self):
        """Test that sensitive data is sanitized from log output."""
        # Mock output containing sensitive data  # pragma: allowlist secret
        sensitive_output = b"""
        2024-01-15 10:30:00 START RequestId: 123e4567-e89b-12d3-a456-426614174000
        2024-01-15 10:30:01 AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE
        2024-01-15 10:30:01 AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEK
        2024-01-15 10:30:02 Processing account 123456789012
        2024-01-15 10:30:03 api_key=sk-proj-abcdef123456
        2024-01-15 10:30:04 END RequestId: 123e4567-e89b-12d3-a456-426614174000
        """

        mock_result = MagicMock()
        mock_result.stdout = sensitive_output
        mock_result.stderr = b''

        with patch(
            'awslabs.aws_serverless_mcp_server.tools.sam.sam_logs.run_command',
            return_value=(mock_result.stdout, mock_result.stderr),
        ):
            result = await SamLogsTool(MagicMock(), True).handle_sam_logs(
                AsyncMock(),
                resource_name='test-function',
            )

            # Verify sensitive data is sanitized
            output_str = str(result)
            assert 'AKIAIOSFODNN7EXAMPLE' not in output_str
            assert '123456789012' not in output_str
            assert 'sk-proj-abcdef123456' not in output_str

            # Verify redacted markers are present
            assert '[REDACTED AWS_ACCESS_KEY]' in output_str
            assert '[REDACTED AWS_ACCOUNT_ID]' in output_str
            assert '[REDACTED API_KEY]' in output_str
            assert result['success'] is True

    @pytest.mark.asyncio
    async def test_sam_logs_all_parameters(self):
        """Test SAM logs with all possible parameters."""
        mock_result = MagicMock()
        mock_result.stdout = b'Complete parameter test'
        mock_result.stderr = b''

        with patch(
            'awslabs.aws_serverless_mcp_server.tools.sam.sam_logs.run_command',
            return_value=(mock_result.stdout, mock_result.stderr),
        ) as mock_run:
            result = await SamLogsTool(MagicMock(), True).handle_sam_logs(
                AsyncMock(),
                resource_name='my-function',
                stack_name='my-stack',
                start_time='1 hour ago',
                end_time='now',
                region='eu-west-1',
                profile='dev-profile',
                cw_log_group=['/aws/lambda/my-func'],
                config_env='development',
                config_file='/custom/samconfig.toml',
                save_params=True,
            )

            mock_run.assert_called_once()
            args, kwargs = mock_run.call_args
            cmd = args[0]

            # Verify all parameters are included
            expected_params = [
                'sam',
                'logs',
                '--name',
                'my-function',
                '--stack-name',
                'my-stack',
                '--start-time',
                '1 hour ago',
                '--end-time',
                'now',
                '--region',
                'eu-west-1',
                '--profile',
                'dev-profile',
                '--cw-log-group',
                '/aws/lambda/my-func',
                '--config-env',
                'development',
                '--config-file',
                '/custom/samconfig.toml',
                '--save-params',
            ]

            for param in expected_params:
                assert param in cmd, f'Expected parameter {param} not found in command'

            assert result['success'] is True

    @pytest.mark.asyncio
    async def test_sam_logs_none_and_empty_parameters(self):
        """Test SAM logs with None and empty parameters."""
        mock_result = MagicMock()
        mock_result.stdout = b'Basic logs'
        mock_result.stderr = b''

        with patch(
            'awslabs.aws_serverless_mcp_server.tools.sam.sam_logs.run_command',
            return_value=(mock_result.stdout, mock_result.stderr),
        ) as mock_run:
            result = await SamLogsTool(MagicMock(), True).handle_sam_logs(
                AsyncMock(),
                resource_name=None,
                stack_name='',  # Empty string
                start_time=None,
                end_time=None,
                region=None,
                profile=None,
                cw_log_group=[],  # Empty list
                config_env=None,
                config_file=None,
                save_params=False,
            )

            mock_run.assert_called_once()
            args, kwargs = mock_run.call_args
            cmd = args[0]

            # Should only contain basic command
            assert cmd == ['sam', 'logs']
            assert result['success'] is True
