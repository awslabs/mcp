"""Tests for automation tools module with direct AWS API calls."""

import json
import os
import sys
from botocore.exceptions import ClientError
from mcp.types import CallToolResult
from unittest.mock import Mock, patch


sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from awslabs.systems_manager_mcp_server.tools.automation import register_tools


class TestAutomationTools:
    """Test automation tools with direct AWS API calls."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_mcp = Mock()
        self.registered_functions = []

        def capture_function(func):
            self.registered_functions.append(func)
            return func

        self.mock_mcp.tool.return_value = capture_function

    @patch('awslabs.systems_manager_mcp_server.tools.automation.boto3.Session')
    @patch('awslabs.systems_manager_mcp_server.tools.automation.Context.is_readonly')
    def test_start_automation_execution_aws_sample(self, mock_readonly, mock_session):
        """Test start_automation_execution with AWS API documentation sample request."""
        mock_readonly.return_value = False

        # Mock SSM client and response
        mock_ssm_client = Mock()
        mock_session.return_value.client.return_value = mock_ssm_client
        mock_ssm_client.start_automation_execution.return_value = {
            'AutomationExecutionId': '73c8eef8-f4ee-4a05-820c-e354fEXAMPLE'
        }

        register_tools(self.mock_mcp)
        start_func = self.registered_functions[0]

        # Sample request from AWS API documentation
        parameters = json.dumps({'InstanceId': ['i-1234567890abcdef0']})

        targets = json.dumps([{'Key': 'tag:Environment', 'Values': ['Production']}])

        target_maps = json.dumps(
            [{'InstanceId': ['i-1234567890abcdef0'], 'Region': ['us-east-1']}]
        )

        target_locations = json.dumps(
            [
                {
                    'Accounts': ['123456789012'],
                    'Regions': ['us-east-1', 'us-west-2'],
                    'TargetLocationMaxConcurrency': '5',
                    'TargetLocationMaxErrors': '1',
                }
            ]
        )

        alarm_configuration = json.dumps(
            {'IgnorePollAlarmFailure': False, 'Alarms': [{'Name': 'CPUUtilization'}]}
        )

        result = start_func(
            document_name='AWS-RestartEC2Instance',
            document_version='1',
            parameters=parameters,
            mode='Auto',
            targets=targets,
            target_maps=target_maps,
            target_parameter_name='InstanceId',
            target_locations=target_locations,
            max_concurrency='10',
            max_errors='1',
            alarm_configuration=alarm_configuration,
            region='us-east-1',
            profile='default',
        )

        # Verify result
        assert isinstance(result, CallToolResult)
        assert result.isError is False
        assert '73c8eef8-f4ee-4a05-820c-e354fEXAMPLE' in result.content[0].text

        # Verify AWS API was called with correct parameters
        mock_ssm_client.start_automation_execution.assert_called_once_with(
            DocumentName='AWS-RestartEC2Instance',
            DocumentVersion='1',
            Parameters={'InstanceId': ['i-1234567890abcdef0']},
            Mode='Auto',
            Targets=[{'Key': 'tag:Environment', 'Values': ['Production']}],
            TargetMaps=[{'InstanceId': ['i-1234567890abcdef0'], 'Region': ['us-east-1']}],
            TargetParameterName='InstanceId',
            TargetLocations=[
                {
                    'Accounts': ['123456789012'],
                    'Regions': ['us-east-1', 'us-west-2'],
                    'TargetLocationMaxConcurrency': '5',
                    'TargetLocationMaxErrors': '1',
                }
            ],
            MaxConcurrency='10',
            MaxErrors='1',
            AlarmConfiguration={
                'IgnorePollAlarmFailure': False,
                'Alarms': [{'Name': 'CPUUtilization'}],
            },
        )

    @patch('awslabs.systems_manager_mcp_server.tools.automation.boto3.Session')
    @patch('awslabs.systems_manager_mcp_server.tools.automation.Context.is_readonly')
    def test_get_automation_execution_aws_sample(self, mock_readonly, mock_session):
        """Test get_automation_execution with AWS API documentation sample response."""
        mock_readonly.return_value = False

        # Mock SSM client and response based on AWS API documentation
        mock_ssm_client = Mock()
        mock_session.return_value.client.return_value = mock_ssm_client
        mock_ssm_client.get_automation_execution.return_value = {
            'AutomationExecution': {
                'AutomationExecutionId': '73c8eef8-f4ee-4a05-820c-e354fEXAMPLE',
                'DocumentName': 'AWS-RestartEC2Instance',
                'DocumentVersion': '1',
                'ExecutionStartTime': '2023-01-15T10:30:00.000Z',
                'ExecutionEndTime': '2023-01-15T10:35:00.000Z',
                'AutomationExecutionStatus': 'Success',
                'StepExecutions': [
                    {
                        'StepName': 'stopInstances',
                        'Action': 'aws:changeInstanceState',
                        'ExecutionStartTime': '2023-01-15T10:30:00.000Z',
                        'ExecutionEndTime': '2023-01-15T10:32:00.000Z',
                        'StepStatus': 'Success',
                    },
                    {
                        'StepName': 'startInstances',
                        'Action': 'aws:changeInstanceState',
                        'ExecutionStartTime': '2023-01-15T10:33:00.000Z',
                        'ExecutionEndTime': '2023-01-15T10:35:00.000Z',
                        'StepStatus': 'Success',
                    },
                ],
                'Parameters': {'InstanceId': ['i-1234567890abcdef0']},
                'Mode': 'Auto',
                'ExecutedBy': 'arn:aws:iam::123456789012:user/ExampleUser',
            }
        }

        register_tools(self.mock_mcp)
        get_func = self.registered_functions[1]  # get_automation_execution is index 1

        result = get_func(
            automation_execution_id='73c8eef8-f4ee-4a05-820c-e354fEXAMPLE',
            region='us-east-1',
            profile='default',
        )

        # Verify result
        assert isinstance(result, CallToolResult)
        assert result.isError is False
        assert '73c8eef8-f4ee-4a05-820c-e354fEXAMPLE' in result.content[0].text
        assert 'AWS-RestartEC2Instance' in result.content[0].text
        assert 'Success' in result.content[0].text
        assert 'stopInstances' in result.content[0].text
        assert 'startInstances' in result.content[0].text

        # Verify AWS API was called with correct parameters
        mock_ssm_client.get_automation_execution.assert_called_once_with(
            AutomationExecutionId='73c8eef8-f4ee-4a05-820c-e354fEXAMPLE'
        )

    @patch('awslabs.systems_manager_mcp_server.tools.automation.boto3.Session')
    @patch('awslabs.systems_manager_mcp_server.tools.automation.Context.is_readonly')
    def test_describe_automation_executions_aws_sample(self, mock_readonly, mock_session):
        """Test describe_automation_executions with AWS API documentation sample response."""
        mock_readonly.return_value = False

        # Mock SSM client and response based on AWS API documentation
        mock_ssm_client = Mock()
        mock_session.return_value.client.return_value = mock_ssm_client
        mock_ssm_client.describe_automation_executions.return_value = {
            'AutomationExecutionMetadataList': [
                {
                    'AutomationExecutionId': '73c8eef8-f4ee-4a05-820c-e354fEXAMPLE',
                    'DocumentName': 'AWS-RestartEC2Instance',
                    'DocumentVersion': '1',
                    'AutomationExecutionStatus': 'Success',
                    'ExecutionStartTime': '2023-01-15T10:30:00.000Z',
                    'ExecutionEndTime': '2023-01-15T10:35:00.000Z',
                    'ExecutedBy': 'arn:aws:iam::123456789012:user/ExampleUser',
                    'LogFile': '',
                    'Outputs': {'RestartInstancesResult': ['Success']},
                },
                {
                    'AutomationExecutionId': '84d9def9-g5ff-5b16-931d-f465gFEXAMPLE',
                    'DocumentName': 'AWS-StopEC2Instance',
                    'DocumentVersion': '2',
                    'AutomationExecutionStatus': 'Failed',
                    'ExecutionStartTime': '2023-01-15T11:00:00.000Z',
                    'ExecutionEndTime': '2023-01-15T11:05:00.000Z',
                    'ExecutedBy': 'arn:aws:iam::123456789012:user/ExampleUser',
                    'FailureMessage': 'Instance not found',
                },
            ]
        }

        register_tools(self.mock_mcp)
        describe_func = self.registered_functions[3]  # describe_automation_executions is index 3

        # Test with filters
        filters = json.dumps([{'Key': 'DocumentName', 'Values': ['AWS-RestartEC2Instance']}])

        result = describe_func(
            filters=filters, max_results=10, region='us-east-1', profile='default'
        )

        # Verify result
        assert isinstance(result, CallToolResult)
        assert result.isError is False
        assert '73c8eef8-f4ee-4a05-820c-e354fEXAMPLE' in result.content[0].text
        assert '84d9def9-g5ff-5b16-931d-f465gFEXAMPLE' in result.content[0].text
        assert 'AWS-RestartEC2Instance' in result.content[0].text
        assert 'AWS-StopEC2Instance' in result.content[0].text
        assert 'Success' in result.content[0].text
        assert 'Failed' in result.content[0].text
        assert 'Instance not found' in result.content[0].text

        # Verify AWS API was called with correct parameters
        mock_ssm_client.describe_automation_executions.assert_called_once_with(
            Filters=[{'Key': 'DocumentName', 'Values': ['AWS-RestartEC2Instance']}], MaxResults=10
        )

    @patch('awslabs.systems_manager_mcp_server.tools.automation.boto3.Session')
    @patch('awslabs.systems_manager_mcp_server.tools.automation.Context.is_readonly')
    def test_send_automation_signal_aws_sample(self, mock_readonly, mock_session):
        """Test send_automation_signal with AWS API documentation sample request."""
        mock_readonly.return_value = False

        # Mock SSM client - send_automation_signal returns empty response on success
        mock_ssm_client = Mock()
        mock_session.return_value.client.return_value = mock_ssm_client
        mock_ssm_client.send_automation_signal.return_value = {}

        register_tools(self.mock_mcp)
        signal_func = self.registered_functions[4]  # send_automation_signal is index 4

        # Test with payload from AWS API documentation
        payload = json.dumps({'StepName': 'stopInstances', 'Comment': 'Approved by security team'})

        result = signal_func(
            automation_execution_id='73c8eef8-f4ee-4a05-820c-e354fEXAMPLE',
            signal_type='Approve',
            payload=payload,
            region='us-east-1',
            profile='default',
        )

        # Verify result
        assert isinstance(result, CallToolResult)
        assert result.isError is False
        assert 'Automation signal sent successfully' in result.content[0].text

        # Verify AWS API was called with correct parameters
        mock_ssm_client.send_automation_signal.assert_called_once_with(
            AutomationExecutionId='73c8eef8-f4ee-4a05-820c-e354fEXAMPLE',
            SignalType='Approve',
            Payload={'StepName': 'stopInstances', 'Comment': 'Approved by security team'},
        )

    @patch('awslabs.systems_manager_mcp_server.tools.automation.Context.is_readonly')
    def test_start_automation_execution_readonly_mode(self, mock_readonly):
        """Test start_automation_execution in readonly mode."""
        mock_readonly.return_value = True

        register_tools(self.mock_mcp)
        start_func = self.registered_functions[0]

        result = start_func(document_name='AWS-RestartEC2Instance')

        assert isinstance(result, CallToolResult)
        assert result.isError is True
        assert 'read-only mode' in result.content[0].text

    @patch('awslabs.systems_manager_mcp_server.tools.automation.Context.is_readonly')
    def test_start_automation_execution_invalid_json(self, mock_readonly):
        """Test start_automation_execution with invalid JSON parameters."""
        mock_readonly.return_value = False

        register_tools(self.mock_mcp)
        start_func = self.registered_functions[0]

        result = start_func(document_name='AWS-RestartEC2Instance', parameters='invalid-json')

        assert isinstance(result, CallToolResult)
        assert result.isError is True
        assert 'Invalid JSON in parameters' in result.content[0].text

    @patch('awslabs.systems_manager_mcp_server.tools.automation.boto3.Session')
    @patch('awslabs.systems_manager_mcp_server.tools.automation.Context.is_readonly')
    def test_get_automation_execution_client_error(self, mock_readonly, mock_session):
        """Test get_automation_execution with AWS ClientError."""
        mock_readonly.return_value = False

        mock_ssm_client = Mock()
        mock_session.return_value.client.return_value = mock_ssm_client
        mock_ssm_client.get_automation_execution.side_effect = ClientError(
            {
                'Error': {
                    'Code': 'AutomationExecutionNotFoundException',
                    'Message': 'Automation execution not found',
                }
            },
            'GetAutomationExecution',
        )

        register_tools(self.mock_mcp)
        get_func = self.registered_functions[1]

        result = get_func(automation_execution_id='invalid-id')

        assert isinstance(result, CallToolResult)
        assert result.isError is True
        assert 'AWS Error: Automation execution not found' in result.content[0].text

    @patch('awslabs.systems_manager_mcp_server.tools.automation.Context.is_readonly')
    def test_send_automation_signal_readonly_mode(self, mock_readonly):
        """Test send_automation_signal in readonly mode."""
        mock_readonly.return_value = True

        register_tools(self.mock_mcp)
        signal_func = self.registered_functions[4]

        result = signal_func(
            automation_execution_id='73c8eef8-f4ee-4a05-820c-e354fEXAMPLE', signal_type='Approve'
        )

        assert isinstance(result, CallToolResult)
        assert result.isError is True
        assert 'read-only mode' in result.content[0].text

    @patch('awslabs.systems_manager_mcp_server.tools.automation.Context.is_readonly')
    def test_send_automation_signal_invalid_json_payload(self, mock_readonly):
        """Test send_automation_signal with invalid JSON payload."""
        mock_readonly.return_value = False

        register_tools(self.mock_mcp)
        signal_func = self.registered_functions[4]

        result = signal_func(
            automation_execution_id='73c8eef8-f4ee-4a05-820c-e354fEXAMPLE',
            signal_type='Approve',
            payload='invalid-json',
        )

        assert isinstance(result, CallToolResult)
        assert result.isError is True
        assert 'Invalid JSON in payload' in result.content[0].text

    @patch('awslabs.systems_manager_mcp_server.tools.automation.boto3.Session')
    @patch('awslabs.systems_manager_mcp_server.tools.automation.Context.is_readonly')
    def test_stop_automation_execution_aws_sample(self, mock_readonly, mock_session):
        """Test stop_automation_execution with AWS API documentation sample request."""
        mock_readonly.return_value = False

        # Mock SSM client - stop_automation_execution returns empty response on success
        mock_ssm_client = Mock()
        mock_session.return_value.client.return_value = mock_ssm_client
        mock_ssm_client.stop_automation_execution.return_value = {}

        register_tools(self.mock_mcp)
        stop_func = self.registered_functions[2]  # stop_automation_execution is index 2

        result = stop_func(
            automation_execution_id='73c8eef8-f4ee-4a05-820c-e354fEXAMPLE',
            stop_type='Cancel',
            region='us-east-1',
            profile='default',
        )

        # Verify result
        assert isinstance(result, CallToolResult)
        assert result.isError is False
        assert 'Automation execution stopped successfully' in result.content[0].text

        # Verify AWS API was called with correct parameters
        mock_ssm_client.stop_automation_execution.assert_called_once_with(
            AutomationExecutionId='73c8eef8-f4ee-4a05-820c-e354fEXAMPLE', Type='Cancel'
        )

    @patch('awslabs.systems_manager_mcp_server.tools.automation.Context.is_readonly')
    def test_stop_automation_execution_readonly_mode(self, mock_readonly):
        """Test stop_automation_execution in readonly mode."""
        mock_readonly.return_value = True

        register_tools(self.mock_mcp)
        stop_func = self.registered_functions[2]

        result = stop_func(automation_execution_id='73c8eef8-f4ee-4a05-820c-e354fEXAMPLE')

        assert isinstance(result, CallToolResult)
        assert result.isError is True
        assert 'read-only mode' in result.content[0].text

    @patch('awslabs.systems_manager_mcp_server.tools.automation.boto3.Session')
    @patch('awslabs.systems_manager_mcp_server.tools.automation.Context.is_readonly')
    def test_stop_automation_execution_client_error(self, mock_readonly, mock_session):
        """Test stop_automation_execution with AWS ClientError."""
        mock_readonly.return_value = False

        mock_ssm_client = Mock()
        mock_session.return_value.client.return_value = mock_ssm_client
        mock_ssm_client.stop_automation_execution.side_effect = ClientError(
            {
                'Error': {
                    'Code': 'InvalidAutomationStatusException',
                    'Message': 'Automation execution is already stopped',
                }
            },
            'StopAutomationExecution',
        )

        register_tools(self.mock_mcp)
        stop_func = self.registered_functions[2]

        result = stop_func(automation_execution_id='73c8eef8-f4ee-4a05-820c-e354fEXAMPLE')

        assert isinstance(result, CallToolResult)
        assert result.isError is True
        assert 'Automation execution is already stopped' in result.content[0].text

    @patch('awslabs.systems_manager_mcp_server.tools.automation.boto3.Session')
    @patch('awslabs.systems_manager_mcp_server.tools.automation.Context.is_readonly')
    def test_describe_automation_executions_client_error(self, mock_readonly, mock_session):
        """Test describe_automation_executions with AWS ClientError."""
        mock_readonly.return_value = False

        mock_ssm_client = Mock()
        mock_session.return_value.client.return_value = mock_ssm_client
        mock_ssm_client.describe_automation_executions.side_effect = ClientError(
            {'Error': {'Code': 'InvalidFilterKey', 'Message': 'Invalid filter key specified'}},
            'DescribeAutomationExecutions',
        )

        register_tools(self.mock_mcp)
        describe_func = self.registered_functions[3]

        result = describe_func(filters='[{"Key": "InvalidKey", "Values": ["test"]}]')

        assert isinstance(result, CallToolResult)
        assert result.isError is True
        assert 'Invalid filter key specified' in result.content[0].text

    @patch('awslabs.systems_manager_mcp_server.tools.automation.Context.is_readonly')
    def test_describe_automation_executions_invalid_json_filters(self, mock_readonly):
        """Test describe_automation_executions with invalid JSON filters."""
        mock_readonly.return_value = False

        register_tools(self.mock_mcp)
        describe_func = self.registered_functions[3]

        result = describe_func(filters='invalid-json')

        assert isinstance(result, CallToolResult)
        assert result.isError is True
        assert 'Invalid JSON in filters' in result.content[0].text

    @patch('awslabs.systems_manager_mcp_server.tools.automation.log_error')
    @patch('awslabs.systems_manager_mcp_server.tools.automation.boto3.Session')
    @patch('awslabs.systems_manager_mcp_server.tools.automation.Context.is_readonly')
    def test_start_automation_execution_generic_exception(
        self, mock_readonly, mock_session, mock_log_error
    ):
        """Test start_automation_execution with generic Exception."""
        mock_readonly.return_value = False
        mock_session.side_effect = Exception('Network connection failed')

        # Mock log_error to return a CallToolResult
        mock_log_error.return_value = CallToolResult(
            content=[
                {
                    'type': 'text',
                    'text': 'Error in start automation execution: Network connection failed',
                }
            ],
            isError=True,
        )

        register_tools(self.mock_mcp)
        start_func = self.registered_functions[0]

        result = start_func(document_name='AWS-RestartEC2Instance')

        assert isinstance(result, CallToolResult)
        assert result.isError is True
        assert 'Network connection failed' in result.content[0].text

    @patch('awslabs.systems_manager_mcp_server.tools.automation.log_error')
    @patch('awslabs.systems_manager_mcp_server.tools.automation.boto3.Session')
    @patch('awslabs.systems_manager_mcp_server.tools.automation.Context.is_readonly')
    def test_get_automation_execution_generic_exception(
        self, mock_readonly, mock_session, mock_log_error
    ):
        """Test get_automation_execution with generic Exception."""
        mock_readonly.return_value = False
        mock_session.side_effect = Exception('Connection timeout')

        # Mock log_error to return a CallToolResult
        mock_log_error.return_value = CallToolResult(
            content=[
                {'type': 'text', 'text': 'Error in get automation execution: Connection timeout'}
            ],
            isError=True,
        )

        register_tools(self.mock_mcp)
        get_func = self.registered_functions[1]

        result = get_func(automation_execution_id='73c8eef8-f4ee-4a05-820c-e354fEXAMPLE')

        assert isinstance(result, CallToolResult)
        assert result.isError is True
        assert 'Connection timeout' in result.content[0].text

    '''@patch('awslabs.systems_manager_mcp_server.tools.automation.boto3.Session')
    @patch('awslabs.systems_manager_mcp_server.tools.automation.Context.is_readonly')
    def test_send_automation_signal_client_error(self, mock_readonly, mock_session):
        """Test send_automation_signal with AWS ClientError."""
        mock_readonly.return_value = False

        mock_ssm_client = Mock()
        mock_session.return_value.client.return_value = mock_ssm_client
        mock_ssm_client.send_automation_signal.side_effect = ClientError(
            {"Error": {"Code": "InvalidAutomationSignalException", "Message": "Invalid signal type"}},
            "SendAutomationSignal"
        )

        register_tools(self.mock_mcp)
        signal_func = self.registered_functions[4]

        result = signal_func(
            automation_execution_id="73c8eef8-f4ee-4a05-820c-e354fEXAMPLE",
            signal_type="Approve"
        )

        assert isinstance(result, CallToolResult)
        assert result.isError is True
        assert "Invalid signal type" in result.content[0].text'''

    @patch('awslabs.systems_manager_mcp_server.tools.automation.log_error')
    @patch('awslabs.systems_manager_mcp_server.tools.automation.boto3.Session')
    @patch('awslabs.systems_manager_mcp_server.tools.automation.Context.is_readonly')
    def test_send_automation_signal_generic_exception(
        self, mock_readonly, mock_session, mock_log_error
    ):
        """Test send_automation_signal with generic Exception."""
        mock_readonly.return_value = False
        mock_session.side_effect = Exception('Connection failed')

        mock_log_error.return_value = CallToolResult(
            content=[
                {'type': 'text', 'text': 'Error in send automation signal: Connection failed'}
            ],
            isError=True,
        )

        register_tools(self.mock_mcp)
        signal_func = self.registered_functions[4]

        result = signal_func(
            automation_execution_id='73c8eef8-f4ee-4a05-820c-e354fEXAMPLE', signal_type='Approve'
        )

        assert isinstance(result, CallToolResult)
        assert result.isError is True
        assert 'Connection failed' in result.content[0].text

    @patch('awslabs.systems_manager_mcp_server.tools.automation.log_error')
    @patch('awslabs.systems_manager_mcp_server.tools.automation.boto3.Session')
    @patch('awslabs.systems_manager_mcp_server.tools.automation.Context.is_readonly')
    def test_stop_automation_execution_generic_exception(
        self, mock_readonly, mock_session, mock_log_error
    ):
        """Test stop_automation_execution with generic Exception."""
        mock_readonly.return_value = False
        mock_session.side_effect = Exception('Network timeout')

        mock_log_error.return_value = CallToolResult(
            content=[
                {'type': 'text', 'text': 'Error in stop automation execution: Network timeout'}
            ],
            isError=True,
        )

        register_tools(self.mock_mcp)
        stop_func = self.registered_functions[2]

        result = stop_func(automation_execution_id='73c8eef8-f4ee-4a05-820c-e354fEXAMPLE')

        assert isinstance(result, CallToolResult)
        assert result.isError is True
        assert 'Network timeout' in result.content[0].text

    @patch('awslabs.systems_manager_mcp_server.tools.automation.log_error')
    @patch('awslabs.systems_manager_mcp_server.tools.automation.boto3.Session')
    @patch('awslabs.systems_manager_mcp_server.tools.automation.Context.is_readonly')
    def test_describe_automation_executions_generic_exception(
        self, mock_readonly, mock_session, mock_log_error
    ):
        """Test describe_automation_executions with generic Exception."""
        mock_readonly.return_value = False
        mock_session.side_effect = Exception('Service unavailable')

        mock_log_error.return_value = CallToolResult(
            content=[
                {
                    'type': 'text',
                    'text': 'Error in describe automation executions: Service unavailable',
                }
            ],
            isError=True,
        )

        register_tools(self.mock_mcp)
        describe_func = self.registered_functions[3]

        result = describe_func()

        assert isinstance(result, CallToolResult)
        assert result.isError is True
        assert 'Service unavailable' in result.content[0].text
