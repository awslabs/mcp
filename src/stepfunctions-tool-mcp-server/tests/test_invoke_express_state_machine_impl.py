"""Tests for Express state machine functionality."""

import json
import pytest
from mcp.server.fastmcp import Context
from unittest.mock import AsyncMock, MagicMock, patch


with pytest.MonkeyPatch().context() as CTX:
    CTX.setattr('boto3.Session', MagicMock)
    from awslabs.stepfunctions_tool_mcp_server.server import invoke_express_state_machine_impl


class TestExpressStateMachines:
    """Tests for Express state machine functionality."""

    @pytest.mark.asyncio
    @patch('awslabs.stepfunctions_tool_mcp_server.server.sfn_client')
    async def test_express_state_machine_success(self, mock_sfn_client):
        """Test successful execution of an Express state machine."""
        # Set up the mock
        mock_sfn_client.list_state_machines.return_value = {
            'stateMachines': [
                {
                    'stateMachineArn': 'arn:aws:states:us-east-1:123456789012:stateMachine:express-test',
                    'name': 'express-test',
                    'type': 'EXPRESS',
                    'creationDate': '2023-01-01T00:00:00Z',
                },
            ]
        }

        mock_sfn_client.start_sync_execution.return_value = {
            'executionArn': 'arn:aws:states:us-east-1:123456789012:express:express-test:12345',
            'stateMachineArn': 'arn:aws:states:us-east-1:123456789012:stateMachine:express-test',
            'name': '12345',
            'startDate': '2023-01-01T00:00:00Z',
            'stopDate': '2023-01-01T00:00:01Z',
            'status': 'SUCCEEDED',
            'output': '{"result": "success"}',
        }

        # Create a mock context
        ctx = MagicMock(spec=Context)
        ctx.info = AsyncMock()
        ctx.error = AsyncMock()

        # Call the function
        result = await invoke_express_state_machine_impl(
            'express-test',
            'arn:aws:states:us-east-1:123456789012:stateMachine:express-test',
            {'param': 'value'},
            ctx,
        )

        # Check that the state machine was invoked with the correct parameters
        mock_sfn_client.start_sync_execution.assert_called_once_with(
            stateMachineArn='arn:aws:states:us-east-1:123456789012:stateMachine:express-test',
            input='{"param": "value"}',
        )

        # Check that the context methods were called
        ctx.info.assert_called()

        # Check the result
        assert 'State machine express-test returned:' in result
        assert '"result": "success"' in result

    @pytest.mark.asyncio
    @patch('awslabs.stepfunctions_tool_mcp_server.server.sfn_client')
    async def test_express_state_machine_failure(self, mock_sfn_client):
        """Test failed execution of an Express state machine."""
        # Set up the mock
        mock_sfn_client.list_state_machines.return_value = {
            'stateMachines': [
                {
                    'stateMachineArn': 'arn:aws:states:us-east-1:123456789012:stateMachine:express-error',
                    'name': 'express-error',
                    'type': 'EXPRESS',
                    'creationDate': '2023-01-01T00:00:00Z',
                },
            ]
        }

        mock_sfn_client.start_sync_execution.return_value = {
            'executionArn': 'arn:aws:states:us-east-1:123456789012:express:express-error:12345',
            'stateMachineArn': 'arn:aws:states:us-east-1:123456789012:stateMachine:express-error',
            'name': '12345',
            'startDate': '2023-01-01T00:00:00Z',
            'stopDate': '2023-01-01T00:00:01Z',
            'status': 'FAILED',
            'error': 'States.TaskFailed',
            'cause': 'Something went wrong',
        }

        # Create a mock context
        ctx = MagicMock(spec=Context)
        ctx.info = AsyncMock()
        ctx.error = AsyncMock()

        # Call the function
        result = await invoke_express_state_machine_impl(
            'express-error',
            'arn:aws:states:us-east-1:123456789012:stateMachine:express-error',
            {'param': 'value'},
            ctx,
        )

        # Check that the state machine was invoked with the correct parameters
        mock_sfn_client.start_sync_execution.assert_called_once_with(
            stateMachineArn='arn:aws:states:us-east-1:123456789012:stateMachine:express-error',
            input='{"param": "value"}',
        )

        # Check that the context methods were called
        ctx.info.assert_called()
        ctx.error.assert_called_once()

        # Check the result
        assert 'Express state machine express-error execution failed with status: FAILED' in result
        assert 'error: States.TaskFailed' in result
        assert 'cause: Something went wrong' in result

    @pytest.mark.asyncio
    @patch('awslabs.stepfunctions_tool_mcp_server.server.sfn_client')
    async def test_express_state_machine_direct_invocation(self, mock_sfn_client):
        """Test direct invocation of an Express state machine."""
        # Set up the mock
        mock_sfn_client.start_sync_execution.return_value = {
            'executionArn': 'arn:aws:states:us-east-1:123456789012:express:express-test:12345',
            'stateMachineArn': 'arn:aws:states:us-east-1:123456789012:stateMachine:express-test',
            'name': '12345',
            'startDate': '2023-01-01T00:00:00Z',
            'stopDate': '2023-01-01T00:00:01Z',
            'status': 'SUCCEEDED',
            'output': '{"result": "direct success"}',
        }

        # Create a mock context
        ctx = MagicMock(spec=Context)
        ctx.info = AsyncMock()
        ctx.error = AsyncMock()

        # Call the function directly
        result = await invoke_express_state_machine_impl(
            'express-test',
            'arn:aws:states:us-east-1:123456789012:stateMachine:express-test',
            {'param': 'value'},
            ctx,
        )

        # Check that the state machine was invoked with the correct parameters
        mock_sfn_client.start_sync_execution.assert_called_once_with(
            stateMachineArn='arn:aws:states:us-east-1:123456789012:stateMachine:express-test',
            input='{"param": "value"}',
        )

        # Check that the context methods were called
        ctx.info.assert_called()

        # Check the result
        assert 'State machine express-test returned:' in result
        assert '"result": "direct success"' in result

    @pytest.mark.asyncio
    @patch('awslabs.stepfunctions_tool_mcp_server.server.sfn_client')
    async def test_express_state_machine_complex_input(self, mock_sfn_client):
        """Test Express state machine with complex input and output."""
        # Set up complex input
        complex_input = {
            'data': {
                'nested': {
                    'array': [1, 2, 3],
                    'object': {'key': 'value'},
                    'null': None,
                    'boolean': True,
                }
            },
            'metadata': {'timestamp': '2023-01-01T00:00:00Z', 'requestId': '12345'},
        }

        # Set up the mock
        mock_sfn_client.list_state_machines.return_value = {
            'stateMachines': [
                {
                    'stateMachineArn': 'arn:aws:states:us-east-1:123456789012:stateMachine:express-complex',
                    'name': 'express-complex',
                    'type': 'EXPRESS',
                    'creationDate': '2023-01-01T00:00:00Z',
                },
            ]
        }

        mock_sfn_client.start_sync_execution.return_value = {
            'executionArn': 'arn:aws:states:us-east-1:123456789012:express:express-complex:12345',
            'stateMachineArn': 'arn:aws:states:us-east-1:123456789012:stateMachine:express-complex',
            'name': '12345',
            'startDate': '2023-01-01T00:00:00Z',
            'stopDate': '2023-01-01T00:00:01Z',
            'status': 'SUCCEEDED',
            'output': json.dumps(complex_input),
        }

        # Create a mock context
        ctx = MagicMock(spec=Context)
        ctx.info = AsyncMock()
        ctx.error = AsyncMock()

        # Call the function
        result = await invoke_express_state_machine_impl(
            'express-complex',
            'arn:aws:states:us-east-1:123456789012:stateMachine:express-complex',
            complex_input,
            ctx,
        )

        # Check that the state machine was invoked with the correct parameters
        mock_sfn_client.start_sync_execution.assert_called_once_with(
            stateMachineArn='arn:aws:states:us-east-1:123456789012:stateMachine:express-complex',
            input=json.dumps(complex_input),
        )

        # Check the result
        assert 'State machine express-complex returned:' in result
        assert '"data": {' in result
        assert '"nested": {' in result
        assert '"array": [' in result
        assert '"metadata": {' in result
