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

"""Tests for command tools."""

import os
import sys
from botocore.exceptions import ClientError
from mcp.types import CallToolResult
from unittest.mock import Mock, patch


sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from awslabs.systems_manager_mcp_server.tools.commands import register_tools


class TestCommandTools:
    """Test command tools with direct AWS API calls."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_mcp = Mock()
        self.registered_functions = []

        def capture_function(func):
            self.registered_functions.append(func)
            return func

        self.mock_mcp.tool.return_value = capture_function

    def test_register_tools_creates_functions(self):
        """Test that register_tools creates all tool functions."""
        register_tools(self.mock_mcp)
        assert len(self.registered_functions) == 4

    @patch('awslabs.systems_manager_mcp_server.tools.commands.Context.is_readonly')
    def test_send_command_readonly_mode(self, mock_readonly):
        """Test send_command in readonly mode."""
        mock_readonly.return_value = True

        register_tools(self.mock_mcp)
        send_func = self.registered_functions[0]

        result = send_func(
            document_name='AWS-RunShellScript',
            instance_ids=None,
            targets=None,
            document_version=None,
            parameters=None,
            timeout_seconds=None,
            comment=None,
            max_concurrency=None,
            max_errors=None,
            output_s3_region=None,
            output_s3_bucket_name=None,
            output_s3_key_prefix=None,
            service_role_arn=None,
            notification_config=None,
            cloudwatch_output_config=None,
            alarm_configuration=None,
            region=None,
            profile=None,
        )

        assert isinstance(result, CallToolResult)
        assert result.isError is True
        assert 'read-only mode' in result.content[0].text

    @patch('awslabs.systems_manager_mcp_server.tools.commands.boto3.Session')
    @patch('awslabs.systems_manager_mcp_server.tools.commands.Context.is_readonly')
    def test_send_command_success(self, mock_readonly, mock_session):
        """Test send_command success."""
        mock_readonly.return_value = False

        mock_ssm_client = Mock()
        mock_session.return_value.client.return_value = mock_ssm_client
        mock_ssm_client.send_command.return_value = {
            'Command': {
                'CommandId': 'test-command-id',
                'DocumentName': 'AWS-RunShellScript',
                'Status': 'Pending',
                'RequestedDateTime': '2024-01-15T10:00:00.000Z',
                'InstanceIds': ['i-1234567890abcdef0'],
            }
        }

        register_tools(self.mock_mcp)
        send_func = self.registered_functions[0]

        result = send_func(
            document_name='AWS-RunShellScript',
            instance_ids='i-1234567890abcdef0,i-0987654321fedcba0',
            targets='[{"Key": "tag:Environment", "Values": ["Production"]}]',
            document_version='1',
            parameters='{"commands": ["echo hello"]}',
            timeout_seconds=3600,
            comment='Test command execution',
            max_concurrency='5',
            max_errors='1',
            output_s3_region='us-east-1',
            output_s3_bucket_name='my-test-bucket',
            output_s3_key_prefix='command-outputs/',
            service_role_arn='arn:aws:iam::123456789012:role/SSMServiceRole',
            notification_config='{"NotificationArn": "arn:aws:sns:us-east-1:123456789012:notifications"}',
            cloudwatch_output_config='{"CloudWatchLogGroupName": "/aws/ssm/commands"}',
            alarm_configuration='{"IgnorePollAlarmFailure": false}',
            region='us-east-1',
            profile='default',
        )

        assert isinstance(result, CallToolResult)
        assert result.isError is False
        assert 'test-command-id' in result.content[0].text
        assert '✅' in result.content[0].text

    @patch('awslabs.systems_manager_mcp_server.tools.commands.boto3.Session')
    @patch('awslabs.systems_manager_mcp_server.tools.commands.Context.is_readonly')
    def test_send_command_invalid_targets_json(self, mock_readonly, mock_session):
        """Test send_command with invalid JSON in targets parameter."""
        mock_readonly.return_value = False

        register_tools(self.mock_mcp)
        send_func = self.registered_functions[0]

        result = send_func(
            document_name='AWS-RunShellScript',
            instance_ids=None,
            targets='{"invalid": json}',
            document_version=None,
            parameters=None,
            timeout_seconds=None,
            comment=None,
            max_concurrency=None,
            max_errors=None,
            output_s3_region=None,
            output_s3_bucket_name=None,
            output_s3_key_prefix=None,
            service_role_arn=None,
            notification_config=None,
            cloudwatch_output_config=None,
            alarm_configuration=None,
            region=None,
            profile=None,
        )

        assert isinstance(result, CallToolResult)
        assert result.isError is True
        assert 'Invalid JSON in targets' in result.content[0].text

    @patch('awslabs.systems_manager_mcp_server.tools.commands.boto3.Session')
    @patch('awslabs.systems_manager_mcp_server.tools.commands.Context.is_readonly')
    def test_send_command_invalid_parameters_json(self, mock_readonly, mock_session):
        """Test send_command with invalid JSON in parameters parameter."""
        mock_readonly.return_value = False

        register_tools(self.mock_mcp)
        send_func = self.registered_functions[0]

        result = send_func(
            document_name='AWS-RunShellScript',
            instance_ids=None,
            targets=None,
            document_version=None,
            parameters='{"invalid": json}',
            timeout_seconds=None,
            comment=None,
            max_concurrency=None,
            max_errors=None,
            output_s3_region=None,
            output_s3_bucket_name=None,
            output_s3_key_prefix=None,
            service_role_arn=None,
            notification_config=None,
            cloudwatch_output_config=None,
            alarm_configuration=None,
            region=None,
            profile=None,
        )

        assert isinstance(result, CallToolResult)
        assert result.isError is True
        assert 'Invalid JSON in parameters' in result.content[0].text

    @patch('awslabs.systems_manager_mcp_server.tools.commands.boto3.Session')
    @patch('awslabs.systems_manager_mcp_server.tools.commands.Context.is_readonly')
    def test_send_command_invalid_notification_config_json(self, mock_readonly, mock_session):
        """Test send_command with invalid JSON in notification_config parameter."""
        mock_readonly.return_value = False

        register_tools(self.mock_mcp)
        send_func = self.registered_functions[0]

        result = send_func(
            document_name='AWS-RunShellScript',
            instance_ids=None,
            targets=None,
            document_version=None,
            parameters=None,
            timeout_seconds=None,
            comment=None,
            max_concurrency=None,
            max_errors=None,
            output_s3_region=None,
            output_s3_bucket_name=None,
            output_s3_key_prefix=None,
            service_role_arn=None,
            notification_config='{"invalid": json}',
            cloudwatch_output_config=None,
            alarm_configuration=None,
            region=None,
            profile=None,
        )

        assert isinstance(result, CallToolResult)
        assert result.isError is True
        assert 'Invalid JSON in notification_config' in result.content[0].text

    @patch('awslabs.systems_manager_mcp_server.tools.commands.boto3.Session')
    @patch('awslabs.systems_manager_mcp_server.tools.commands.Context.is_readonly')
    def test_send_command_invalid_cloudwatch_output_config_json(self, mock_readonly, mock_session):
        """Test send_command with invalid JSON in cloudwatch_output_config parameter."""
        mock_readonly.return_value = False

        register_tools(self.mock_mcp)
        send_func = self.registered_functions[0]

        result = send_func(
            document_name='AWS-RunShellScript',
            instance_ids=None,
            targets=None,
            document_version=None,
            parameters=None,
            timeout_seconds=None,
            comment=None,
            max_concurrency=None,
            max_errors=None,
            output_s3_region=None,
            output_s3_bucket_name=None,
            output_s3_key_prefix=None,
            service_role_arn=None,
            notification_config=None,
            cloudwatch_output_config='{"invalid": json}',
            alarm_configuration=None,
            region=None,
            profile=None,
        )

        assert isinstance(result, CallToolResult)
        assert result.isError is True
        assert 'Invalid JSON in cloudwatch_output_config' in result.content[0].text

    @patch('awslabs.systems_manager_mcp_server.tools.commands.boto3.Session')
    @patch('awslabs.systems_manager_mcp_server.tools.commands.Context.is_readonly')
    def test_send_command_invalid_alarm_configuration_json(self, mock_readonly, mock_session):
        """Test send_command with invalid JSON in alarm_configuration parameter."""
        mock_readonly.return_value = False

        register_tools(self.mock_mcp)
        send_func = self.registered_functions[0]

        result = send_func(
            document_name='AWS-RunShellScript',
            instance_ids=None,
            targets=None,
            document_version=None,
            parameters=None,
            timeout_seconds=None,
            comment=None,
            max_concurrency=None,
            max_errors=None,
            output_s3_region=None,
            output_s3_bucket_name=None,
            output_s3_key_prefix=None,
            service_role_arn=None,
            notification_config=None,
            cloudwatch_output_config=None,
            alarm_configuration='{"invalid": json}',
            region=None,
            profile=None,
        )

        assert isinstance(result, CallToolResult)
        assert result.isError is True
        assert 'Invalid JSON in alarm_configuration' in result.content[0].text

    @patch('awslabs.systems_manager_mcp_server.tools.commands.boto3.Session')
    def test_get_command_invocation_success(self, mock_session):
        """Test get_command_invocation success."""
        mock_ssm_client = Mock()
        mock_session.return_value.client.return_value = mock_ssm_client
        mock_ssm_client.get_command_invocation.return_value = {
            'CommandId': 'test-command-id',
            'InstanceId': 'i-1234567890abcdef0',
            'Comment': 'Test command execution',
            'DocumentName': 'AWS-RunShellScript',
            'DocumentVersion': '1',
            'PluginName': 'aws:runShellScript',
            'ResponseCode': 0,
            'ExecutionStartDateTime': '2024-01-15T10:00:00.000Z',
            'ExecutionElapsedTime': 'PT5.123S',
            'ExecutionEndDateTime': '2024-01-15T10:00:05.123Z',
            'Status': 'Success',
            'StatusDetails': 'Success',
            'StandardOutputContent': 'Hello World\n',
            'StandardErrorContent': '',
            'CloudWatchOutputConfig': {
                'CloudWatchLogGroupName': '/aws/ssm/commands',
                'CloudWatchOutputEnabled': True,
            },
        }

        register_tools(self.mock_mcp)
        get_invocation_func = self.registered_functions[1]

        result = get_invocation_func(
            command_id='test-command-id',
            instance_id='i-1234567890abcdef0',
            plugin_name='aws:runShellScript',
            region='us-east-1',
            profile='default',
        )

        assert isinstance(result, CallToolResult)
        assert result.isError is False
        assert 'test-command-id' in result.content[0].text
        assert 'i-1234567890abcdef0' in result.content[0].text
        assert 'Success' in result.content[0].text
        assert '✅' in result.content[0].text

    @patch('awslabs.systems_manager_mcp_server.tools.commands.boto3.Session')
    def test_get_command_invocation_without_plugin(self, mock_session):
        """Test get_command_invocation without plugin_name."""
        mock_ssm_client = Mock()
        mock_session.return_value.client.return_value = mock_ssm_client
        mock_ssm_client.get_command_invocation.return_value = {
            'CommandId': 'test-command-id',
            'InstanceId': 'i-1234567890abcdef0',
            'DocumentName': 'AWS-RunShellScript',
            'Status': 'Success',
        }

        register_tools(self.mock_mcp)
        get_invocation_func = self.registered_functions[1]

        result = get_invocation_func(
            command_id='test-command-id',
            instance_id='i-1234567890abcdef0',
            plugin_name=None,
            region=None,
            profile=None,
        )

        assert isinstance(result, CallToolResult)
        assert result.isError is False
        assert 'test-command-id' in result.content[0].text

        # Verify AWS API was called without PluginName
        mock_ssm_client.get_command_invocation.assert_called_once_with(
            CommandId='test-command-id', InstanceId='i-1234567890abcdef0'
        )

    @patch('awslabs.systems_manager_mcp_server.tools.commands.boto3.Session')
    def test_get_command_invocation_client_error(self, mock_session):
        """Test get_command_invocation with AWS ClientError."""
        mock_ssm_client = Mock()
        mock_session.return_value.client.return_value = mock_ssm_client
        mock_ssm_client.get_command_invocation.side_effect = ClientError(
            error_response={
                'Error': {
                    'Code': 'InvocationDoesNotExist',
                    'Message': 'Command invocation not found',
                }
            },
            operation_name='GetCommandInvocation',
        )

        register_tools(self.mock_mcp)
        get_invocation_func = self.registered_functions[1]

        result = get_invocation_func(
            command_id='invalid-command-id',
            instance_id='i-1234567890abcdef0',
            plugin_name=None,
            region=None,
            profile=None,
        )

        assert isinstance(result, CallToolResult)
        assert result.isError is True
        assert 'AWS Error: Command invocation not found' in result.content[0].text

    @patch('awslabs.systems_manager_mcp_server.tools.commands.log_error')
    @patch('awslabs.systems_manager_mcp_server.tools.commands.boto3.Session')
    def test_get_command_invocation_exception(self, mock_session, mock_log_error):
        """Test get_command_invocation with generic Exception."""
        mock_log_error.return_value = CallToolResult(
            content=[{'type': 'text', 'text': 'Unexpected error occurred'}],
            isError=True,
        )

        mock_ssm_client = Mock()
        mock_session.return_value.client.return_value = mock_ssm_client
        mock_ssm_client.get_command_invocation.side_effect = Exception('Unexpected error')

        register_tools(self.mock_mcp)
        get_invocation_func = self.registered_functions[1]

        result = get_invocation_func(
            command_id='test-command-id',
            instance_id='i-1234567890abcdef0',
            plugin_name=None,
            region=None,
            profile=None,
        )

        assert isinstance(result, CallToolResult)
        assert result.isError is True

    @patch('awslabs.systems_manager_mcp_server.tools.commands.boto3.Session')
    def test_list_commands_success(self, mock_session):
        """Test list_commands success."""
        mock_ssm_client = Mock()
        mock_session.return_value.client.return_value = mock_ssm_client
        mock_ssm_client.list_commands.return_value = {
            'Commands': [
                {
                    'CommandId': 'test-command-id-1',
                    'DocumentName': 'AWS-RunShellScript',
                    'Status': 'Success',
                    'RequestedDateTime': '2024-01-15T10:00:00.000Z',
                    'InstanceIds': ['i-1234567890abcdef0'],
                    'Comment': 'Test command 1',
                },
                {
                    'CommandId': 'test-command-id-2',
                    'DocumentName': 'AWS-ConfigureAWSPackage',
                    'Status': 'InProgress',
                    'RequestedDateTime': '2024-01-15T11:00:00.000Z',
                    'InstanceIds': ['i-0987654321fedcba0', 'i-1111222233334444'],
                },
            ],
            'NextToken': 'next-token-123',
        }

        register_tools(self.mock_mcp)
        list_func = self.registered_functions[2]

        result = list_func(
            command_id=None,
            instance_id='i-1234567890abcdef0',
            max_results=10,
            next_token='previous-token',
            filters='[{"key": "Status", "value": "Success"}]',
            region='us-east-1',
            profile='default',
        )

        assert isinstance(result, CallToolResult)
        assert result.isError is False
        assert 'test-command-id-1' in result.content[0].text
        assert 'test-command-id-2' in result.content[0].text
        assert '✅' in result.content[0].text

    @patch('awslabs.systems_manager_mcp_server.tools.commands.boto3.Session')
    def test_list_commands_no_results(self, mock_session):
        """Test list_commands with no results."""
        mock_ssm_client = Mock()
        mock_session.return_value.client.return_value = mock_ssm_client
        mock_ssm_client.list_commands.return_value = {'Commands': []}

        register_tools(self.mock_mcp)
        list_func = self.registered_functions[2]

        result = list_func(
            command_id=None,
            instance_id=None,
            max_results=50,
            next_token=None,
            filters=None,
            region=None,
            profile=None,
        )

        assert isinstance(result, CallToolResult)
        assert result.isError is False
        assert 'No commands found matching the criteria' in result.content[0].text

    @patch('awslabs.systems_manager_mcp_server.tools.commands.boto3.Session')
    def test_list_commands_invalid_filters_json(self, mock_session):
        """Test list_commands with invalid JSON in filters parameter."""
        register_tools(self.mock_mcp)
        list_func = self.registered_functions[2]

        result = list_func(
            command_id=None,
            instance_id=None,
            max_results=50,
            next_token=None,
            filters='{"invalid": json}',
            region=None,
            profile=None,
        )

        assert isinstance(result, CallToolResult)
        assert result.isError is True
        assert 'Invalid JSON in filters' in result.content[0].text

    @patch('awslabs.systems_manager_mcp_server.tools.commands.boto3.Session')
    def test_list_commands_client_error(self, mock_session):
        """Test list_commands with AWS ClientError."""
        mock_ssm_client = Mock()
        mock_session.return_value.client.return_value = mock_ssm_client
        mock_ssm_client.list_commands.side_effect = ClientError(
            error_response={
                'Error': {'Code': 'InvalidFilterKey', 'Message': 'Invalid filter key specified'}
            },
            operation_name='ListCommands',
        )

        register_tools(self.mock_mcp)
        list_func = self.registered_functions[2]

        result = list_func(
            command_id=None,
            instance_id=None,
            max_results=10,
            next_token=None,
            filters=None,
            region=None,
            profile=None,
        )

        assert isinstance(result, CallToolResult)
        assert result.isError is True
        assert 'AWS Error: Invalid filter key specified' in result.content[0].text

    @patch('awslabs.systems_manager_mcp_server.tools.commands.log_error')
    @patch('awslabs.systems_manager_mcp_server.tools.commands.boto3.Session')
    def test_list_commands_exception(self, mock_session, mock_log_error):
        """Test list_commands with generic Exception."""
        mock_log_error.return_value = CallToolResult(
            content=[{'type': 'text', 'text': 'Unexpected error occurred'}],
            isError=True,
        )

        mock_ssm_client = Mock()
        mock_session.return_value.client.return_value = mock_ssm_client
        mock_ssm_client.list_commands.side_effect = Exception('Unexpected error')

        register_tools(self.mock_mcp)
        list_func = self.registered_functions[2]

        result = list_func(
            command_id=None,
            instance_id=None,
            max_results=50,
            next_token=None,
            filters=None,
            region=None,
            profile=None,
        )

        assert isinstance(result, CallToolResult)
        assert result.isError is True

    @patch('awslabs.systems_manager_mcp_server.tools.commands.boto3.Session')
    @patch('awslabs.systems_manager_mcp_server.tools.commands.Context.is_readonly')
    def test_cancel_command_success(self, mock_readonly, mock_session):
        """Test cancel_command success."""
        mock_readonly.return_value = False

        mock_ssm_client = Mock()
        mock_session.return_value.client.return_value = mock_ssm_client
        mock_ssm_client.cancel_command.return_value = {}

        register_tools(self.mock_mcp)
        cancel_func = self.registered_functions[3]

        result = cancel_func(
            command_id='test-command-id',
            instance_ids='i-1234567890abcdef0,i-0987654321fedcba0',
            region='us-east-1',
            profile='default',
        )

        assert isinstance(result, CallToolResult)
        assert result.isError is False
        assert '✅' in result.content[0].text

        # Verify AWS API was called with correct parameters
        mock_ssm_client.cancel_command.assert_called_once_with(
            CommandId='test-command-id', InstanceIds=['i-1234567890abcdef0', 'i-0987654321fedcba0']
        )

    @patch('awslabs.systems_manager_mcp_server.tools.commands.boto3.Session')
    @patch('awslabs.systems_manager_mcp_server.tools.commands.Context.is_readonly')
    def test_cancel_command_without_instance_ids(self, mock_readonly, mock_session):
        """Test cancel_command without instance_ids."""
        mock_readonly.return_value = False

        mock_ssm_client = Mock()
        mock_session.return_value.client.return_value = mock_ssm_client
        mock_ssm_client.cancel_command.return_value = {}

        register_tools(self.mock_mcp)
        cancel_func = self.registered_functions[3]

        result = cancel_func(
            command_id='test-command-id', instance_ids=None, region=None, profile=None
        )

        assert isinstance(result, CallToolResult)
        assert result.isError is False
        assert '✅' in result.content[0].text

        # Verify AWS API was called without InstanceIds
        mock_ssm_client.cancel_command.assert_called_once_with(CommandId='test-command-id')

    @patch('awslabs.systems_manager_mcp_server.tools.commands.Context.is_readonly')
    def test_cancel_command_readonly_mode(self, mock_readonly):
        """Test cancel_command in readonly mode."""
        mock_readonly.return_value = True

        register_tools(self.mock_mcp)
        cancel_func = self.registered_functions[3]

        result = cancel_func(
            command_id='test-command-id', instance_ids=None, region=None, profile=None
        )

        assert isinstance(result, CallToolResult)
        assert result.isError is True
        assert 'read-only mode' in result.content[0].text

    @patch('awslabs.systems_manager_mcp_server.tools.commands.boto3.Session')
    @patch('awslabs.systems_manager_mcp_server.tools.commands.Context.is_readonly')
    def test_cancel_command_client_error(self, mock_readonly, mock_session):
        """Test cancel_command with AWS ClientError."""
        mock_readonly.return_value = False

        mock_ssm_client = Mock()
        mock_session.return_value.client.return_value = mock_ssm_client
        mock_ssm_client.cancel_command.side_effect = ClientError(
            error_response={'Error': {'Code': 'InvalidCommandId', 'Message': 'Command not found'}},
            operation_name='CancelCommand',
        )

        register_tools(self.mock_mcp)
        cancel_func = self.registered_functions[3]

        result = cancel_func(
            command_id='invalid-command-id', instance_ids=None, region=None, profile=None
        )

        assert isinstance(result, CallToolResult)
        assert result.isError is True
        assert 'AWS Error: Command not found' in result.content[0].text

    @patch('awslabs.systems_manager_mcp_server.tools.commands.log_error')
    @patch('awslabs.systems_manager_mcp_server.tools.commands.boto3.Session')
    @patch('awslabs.systems_manager_mcp_server.tools.commands.Context.is_readonly')
    def test_cancel_command_exception(self, mock_readonly, mock_session, mock_log_error):
        """Test cancel_command with generic Exception."""
        mock_readonly.return_value = False
        mock_log_error.return_value = CallToolResult(
            content=[{'type': 'text', 'text': 'Unexpected error occurred'}],
            isError=True,
        )

        mock_ssm_client = Mock()
        mock_session.return_value.client.return_value = mock_ssm_client
        mock_ssm_client.cancel_command.side_effect = Exception('Unexpected error')

        register_tools(self.mock_mcp)
        cancel_func = self.registered_functions[3]

        result = cancel_func(
            command_id='test-command-id', instance_ids=None, region=None, profile=None
        )

        assert isinstance(result, CallToolResult)
        assert result.isError is True

    @patch('awslabs.systems_manager_mcp_server.tools.commands.boto3.Session')
    @patch('awslabs.systems_manager_mcp_server.tools.commands.Context.is_readonly')
    def test_send_command_client_error(self, mock_readonly, mock_session):
        """Test send_command with AWS ClientError."""
        mock_readonly.return_value = False

        mock_ssm_client = Mock()
        mock_session.return_value.client.return_value = mock_ssm_client
        mock_ssm_client.send_command.side_effect = ClientError(
            error_response={'Error': {'Code': 'InvalidDocument', 'Message': 'Document not found'}},
            operation_name='SendCommand',
        )

        register_tools(self.mock_mcp)
        send_func = self.registered_functions[0]

        result = send_func(
            document_name='NonExistentDocument',
            instance_ids=None,
            targets=None,
            document_version=None,
            parameters=None,
            timeout_seconds=None,
            comment=None,
            max_concurrency=None,
            max_errors=None,
            output_s3_region=None,
            output_s3_bucket_name=None,
            output_s3_key_prefix=None,
            service_role_arn=None,
            notification_config=None,
            cloudwatch_output_config=None,
            alarm_configuration=None,
            region=None,
            profile=None,
        )

        assert isinstance(result, CallToolResult)
        assert result.isError is True
        assert 'AWS Error: Document not found' in result.content[0].text

    @patch('awslabs.systems_manager_mcp_server.tools.commands.log_error')
    @patch('awslabs.systems_manager_mcp_server.tools.commands.boto3.Session')
    @patch('awslabs.systems_manager_mcp_server.tools.commands.Context.is_readonly')
    def test_send_command_exception(self, mock_readonly, mock_session, mock_log_error):
        """Test send_command with generic Exception."""
        mock_readonly.return_value = False
        mock_log_error.return_value = CallToolResult(
            content=[{'type': 'text', 'text': 'Unexpected error occurred'}],
            isError=True,
        )

        mock_ssm_client = Mock()
        mock_session.return_value.client.return_value = mock_ssm_client
        mock_ssm_client.send_command.side_effect = Exception('Unexpected error')

        register_tools(self.mock_mcp)
        send_func = self.registered_functions[0]

        result = send_func(document_name='AWS-RunShellScript')

        assert isinstance(result, CallToolResult)
        assert result.isError is True
