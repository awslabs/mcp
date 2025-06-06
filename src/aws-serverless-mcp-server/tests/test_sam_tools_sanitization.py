#
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance
# with the License. A copy of the License is located at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES
# OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions
# and limitations under the License.
#

"""Tests for SAM tools sanitization."""

import unittest
from awslabs.aws_serverless_mcp_server.tools.sam.sam_local_invoke import SamLocalInvokeTool
from awslabs.aws_serverless_mcp_server.tools.sam.sam_logs import SamLogsTool
from mcp.server.fastmcp import Context, FastMCP
from unittest.mock import AsyncMock, MagicMock, patch


class TestSamToolsSanitization(unittest.IsolatedAsyncioTestCase):
    """Tests for sanitization in SAM tools."""

    def setUp(self):
        """Set up test fixtures."""
        self.mcp = MagicMock(spec=FastMCP)
        self.mcp.tool = MagicMock(return_value=lambda x: x)
        self.ctx = MagicMock(spec=Context)
        self.ctx.info = AsyncMock()

    @patch('awslabs.aws_serverless_mcp_server.tools.sam.sam_logs.run_command')
    async def test_sam_logs_sanitization(self, mock_run_command):
        """Test that sam_logs properly sanitizes CloudWatch logs output."""
        # Mock CloudWatch logs output containing sensitive data
        mock_stdout = b"""
2024-01-15T10:30:00.000Z START RequestId: 550e8400-e29b-41d4-a716-446655440000 Version: $LATEST
2024-01-15T10:30:01.000Z [INFO] Loading configuration...
2024-01-15T10:30:01.000Z [INFO] AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE
2024-01-15T10:30:01.000Z [INFO] AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
2024-01-15T10:30:02.000Z [INFO] Processing account 123456789012
2024-01-15T10:30:02.000Z [INFO] Connecting to database with password=supersecretdbpass
2024-01-15T10:30:03.000Z [INFO] Using API_KEY=sk-proj-1234567890abcdef
2024-01-15T10:30:04.000Z [INFO] Processing complete
2024-01-15T10:30:04.000Z END RequestId: 550e8400-e29b-41d4-a716-446655440000
2024-01-15T10:30:04.000Z REPORT RequestId: 550e8400-e29b-41d4-a716-446655440000 Duration: 4000.00 ms Billed Duration: 4000 ms Memory Size: 128 MB Max Memory Used: 75 MB
"""
        mock_stderr = b''
        mock_run_command.return_value = (mock_stdout, mock_stderr)

        # Create tool instance with sensitive data access allowed
        tool = SamLogsTool(self.mcp, allow_sensitive_data_access=True)

        # Execute the tool
        result = await tool.handle_sam_logs(
            self.ctx, resource_name='MyFunction', stack_name='my-stack'
        )

        # Verify the command was called
        mock_run_command.assert_called_once()

        # Check that sensitive data is sanitized
        output = result['output']
        self.assertNotIn('AKIAIOSFODNN7EXAMPLE', output)
        self.assertNotIn('wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY', output)
        self.assertNotIn('123456789012', output)
        self.assertNotIn('supersecretdbpass', output)
        self.assertNotIn('sk-proj-1234567890abcdef', output)

        # Check that redacted markers are present
        self.assertIn('[REDACTED AWS_ACCESS_KEY]', output)
        self.assertIn('[REDACTED AWS_SECRET_KEY]', output)
        self.assertIn('[REDACTED AWS_ACCOUNT_ID]', output)
        self.assertIn('[REDACTED PASSWORD]', output)
        self.assertIn('[REDACTED API_KEY]', output)

        # Check that non-sensitive data is preserved
        self.assertIn('START RequestId', output)
        self.assertIn('END RequestId', output)
        self.assertIn('REPORT RequestId', output)
        self.assertIn('Processing complete', output)
        self.assertIn('Loading configuration', output)

    @patch('awslabs.aws_serverless_mcp_server.tools.sam.sam_logs.run_command')
    async def test_sam_logs_access_denied(self, mock_run_command):
        """Test that sam_logs throws exception when sensitive data access is not allowed."""
        # Create tool instance with sensitive data access denied
        tool = SamLogsTool(self.mcp, allow_sensitive_data_access=False)

        # Execute the tool and expect an exception
        with self.assertRaises(Exception) as context:
            await tool.handle_sam_logs(self.ctx, resource_name='MyFunction', stack_name='my-stack')

        # Verify the command was not called
        mock_run_command.assert_not_called()

        # Check that the exception message is correct
        self.assertIn('Sensitive data access is not allowed', str(context.exception))

    @patch('awslabs.aws_serverless_mcp_server.tools.sam.sam_local_invoke.run_command')
    async def test_sam_local_invoke_sanitization(self, mock_run_command):
        """Test that sam_local_invoke properly sanitizes Lambda function output."""
        # Mock Lambda function output containing sensitive data
        mock_stdout = b'{"statusCode": 200, "body": "{\\"message\\": \\"Success\\", \\"accountId\\": \\"123456789012\\", \\"apiKey\\": \\"AKIAIOSFODNN7EXAMPLE\\"}"}'
        mock_stderr = b"""
START RequestId: 550e8400-e29b-41d4-a716-446655440000 Version: $LATEST
[INFO] Environment: AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
[INFO] Processing with password=mydbpassword
[INFO] Using x-api-key=sk-1234567890
END RequestId: 550e8400-e29b-41d4-a716-446655440000
REPORT RequestId: 550e8400-e29b-41d4-a716-446655440000 Duration: 100.00 ms Billed Duration: 100 ms Memory Size: 128 MB Max Memory Used: 50 MB
"""
        mock_run_command.return_value = (mock_stdout, mock_stderr)

        # Create tool instance
        tool = SamLocalInvokeTool(self.mcp)

        # Execute the tool
        result = await tool.handle_sam_local_invoke(
            self.ctx, project_directory='/path/to/project', resource_name='MyFunction'
        )

        # Verify the command was called
        mock_run_command.assert_called_once()

        # Check that sensitive data in function output is sanitized
        function_output = str(result['function_output'])
        self.assertNotIn('123456789012', function_output)
        self.assertNotIn('AKIAIOSFODNN7EXAMPLE', function_output)
        self.assertIn('[REDACTED AWS_ACCOUNT_ID]', function_output)
        self.assertIn('[REDACTED AWS_ACCESS_KEY]', function_output)

        # Check that sensitive data in logs is sanitized
        logs = result['logs']
        self.assertNotIn('wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY', logs)
        self.assertNotIn('mydbpassword', logs)
        self.assertNotIn('sk-1234567890', logs)
        self.assertIn('[REDACTED AWS_SECRET_KEY]', logs)
        self.assertIn('[REDACTED PASSWORD]', logs)
        self.assertIn('[REDACTED API_KEY]', logs)

        # Check that non-sensitive data is preserved
        self.assertIn('START RequestId', logs)
        self.assertIn('END RequestId', logs)
        self.assertIn('REPORT RequestId', logs)
        self.assertEqual(result['success'], True)
        self.assertIn('Successfully invoked', result['message'])

    @patch('awslabs.aws_serverless_mcp_server.tools.sam.sam_local_invoke.run_command')
    async def test_sam_local_invoke_with_event_data_sanitization(self, mock_run_command):
        """Test that sam_local_invoke sanitizes even when event data is provided."""
        # Mock Lambda function output
        mock_stdout = b'{"message": "Processed event", "account": "123456789012"}'
        mock_stderr = b"""
START RequestId: 550e8400-e29b-41d4-a716-446655440000 Version: $LATEST
[INFO] Received event with API key: api_key=secret123
END RequestId: 550e8400-e29b-41d4-a716-446655440000
"""
        mock_run_command.return_value = (mock_stdout, mock_stderr)

        # Create tool instance
        tool = SamLocalInvokeTool(self.mcp)

        # Execute the tool with event data
        result = await tool.handle_sam_local_invoke(
            self.ctx,
            project_directory='/path/to/project',
            resource_name='MyFunction',
            event_data='{"key": "value"}',
        )

        # Check that sensitive data is sanitized
        function_output = str(result['function_output'])
        logs = result['logs']

        self.assertNotIn('123456789012', function_output)
        self.assertNotIn('secret123', logs)
        self.assertIn('[REDACTED AWS_ACCOUNT_ID]', function_output)
        self.assertIn('[REDACTED API_KEY]', logs)

    @patch('awslabs.aws_serverless_mcp_server.tools.sam.sam_local_invoke.run_command')
    async def test_sam_local_invoke_error_handling(self, mock_run_command):
        """Test that sam_local_invoke handles errors properly without leaking sensitive data."""
        # Mock an error that contains sensitive data
        mock_run_command.side_effect = Exception(
            'Failed to invoke: Invalid AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE'
        )

        # Create tool instance
        tool = SamLocalInvokeTool(self.mcp)

        # Execute the tool
        result = await tool.handle_sam_local_invoke(
            self.ctx, project_directory='/path/to/project', resource_name='MyFunction'
        )

        # Check that error is returned
        self.assertFalse(result['success'])
        self.assertIn('Failed to invoke resource locally', result['message'])

        # Check that sensitive data is NOT sanitized in error messages
        # (since we're not sanitizing error responses)
        self.assertIn('AKIAIOSFODNN7EXAMPLE', result['error'])

    @patch('awslabs.aws_serverless_mcp_server.tools.sam.sam_logs.run_command')
    async def test_sam_logs_with_multiple_sensitive_patterns(self, mock_run_command):
        """Test sam_logs with logs containing multiple types of sensitive data."""
        # Mock complex CloudWatch logs with various sensitive patterns
        mock_stdout = b"""
2024-01-15T10:30:00.000Z [INFO] Initializing Lambda function
2024-01-15T10:30:01.000Z [INFO] Environment variables loaded:
2024-01-15T10:30:01.000Z [INFO]   AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE
2024-01-15T10:30:01.000Z [INFO]   AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
2024-01-15T10:30:01.000Z [INFO]   DB_PASSWORD=password:mysupersecretpassword
2024-01-15T10:30:01.000Z [INFO]   API_KEY=x-api-key:sk-proj-abcdef1234567890
2024-01-15T10:30:02.000Z [INFO] Processing request for account 123456789012
2024-01-15T10:30:02.000Z [INFO] Connecting to RDS instance in account 987654321098
2024-01-15T10:30:03.000Z [INFO] Request processed successfully
2024-01-15T10:30:03.000Z [INFO] Cleaning up resources
"""
        mock_stderr = b''
        mock_run_command.return_value = (mock_stdout, mock_stderr)

        # Create tool instance
        tool = SamLogsTool(self.mcp, allow_sensitive_data_access=True)

        # Execute the tool
        result = await tool.handle_sam_logs(
            self.ctx, resource_name='MyFunction', stack_name='my-stack'
        )

        # Check that all sensitive patterns are sanitized
        output = result['output']

        # AWS credentials
        self.assertNotIn('AKIAIOSFODNN7EXAMPLE', output)
        self.assertNotIn('wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY', output)

        # Passwords
        self.assertNotIn('mysupersecretpassword', output)

        # API keys
        self.assertNotIn('sk-proj-abcdef1234567890', output)

        # Account IDs
        self.assertNotIn('123456789012', output)
        self.assertNotIn('987654321098', output)

        # Check redacted markers
        self.assertIn('[REDACTED AWS_ACCESS_KEY]', output)
        self.assertIn('[REDACTED AWS_SECRET_KEY]', output)
        self.assertIn('[REDACTED PASSWORD]', output)
        self.assertIn('[REDACTED API_KEY]', output)
        self.assertEqual(
            output.count('[REDACTED AWS_ACCOUNT_ID]'), 2
        )  # Should redact both account IDs


if __name__ == '__main__':
    unittest.main()
