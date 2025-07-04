"""Tests for Standard state machine functionality."""

import json
import pytest
from mcp.server.fastmcp import Context
from unittest.mock import AsyncMock, MagicMock, patch


with pytest.MonkeyPatch().context() as CTX:
    CTX.setattr('boto3.Session', MagicMock)
    from awslabs.stepfunctions_tool_mcp_server.server import invoke_standard_state_machine_impl


class TestStandardStateMachines:
    """Tests for Standard state machine functionality."""

    @pytest.mark.asyncio
    @patch('awslabs.stepfunctions_tool_mcp_server.server.sfn_client')
    async def test_standard_state_machine_success(self, mock_sfn_client):
        """Test successful execution of a Standard state machine."""
        # Set up test data
        state_machine_name = 'test-state-machine'
        state_machine_arn = (
            f'arn:aws:states:us-east-1:123456789012:stateMachine:{state_machine_name}'
        )
        execution_arn = (
            f'arn:aws:states:us-east-1:123456789012:execution:{state_machine_name}:12345'
        )

        # Set up mock responses
        mock_sfn_client.start_execution.return_value = {
            'executionArn': execution_arn,
            'startDate': '2023-01-01T00:00:00Z',
        }

        mock_sfn_client.describe_execution.return_value = {
            'executionArn': execution_arn,
            'stateMachineArn': state_machine_arn,
            'name': '12345',
            'status': 'SUCCEEDED',
            'startDate': '2023-01-01T00:00:00Z',
            'stopDate': '2023-01-01T00:00:01Z',
            'output': '{"result": "success"}',
        }

        # Set up mock context
        ctx = MagicMock(spec=Context)
        ctx.info = AsyncMock()
        ctx.error = AsyncMock()

        # Call the function
        result = await invoke_standard_state_machine_impl(
            state_machine_name, state_machine_arn, {'param': 'value'}, ctx
        )

        # Verify results
        mock_sfn_client.start_execution.assert_called_once_with(
            stateMachineArn=state_machine_arn, input='{"param": "value"}'
        )
        ctx.info.assert_called()
        assert 'State machine test-state-machine returned:' in result
        assert '"result": "success"' in result

    @pytest.mark.asyncio
    @patch('awslabs.stepfunctions_tool_mcp_server.server.sfn_client')
    async def test_standard_state_machine_failure(self, mock_sfn_client):
        """Test failed execution of a Standard state machine."""
        # Set up test data
        state_machine_name = 'error-state-machine'
        state_machine_arn = (
            f'arn:aws:states:us-east-1:123456789012:stateMachine:{state_machine_name}'
        )
        execution_arn = (
            f'arn:aws:states:us-east-1:123456789012:execution:{state_machine_name}:12345'
        )

        # Set up mock responses
        mock_sfn_client.start_execution.return_value = {
            'executionArn': execution_arn,
            'startDate': '2023-01-01T00:00:00Z',
        }

        mock_sfn_client.describe_execution.return_value = {
            'executionArn': execution_arn,
            'stateMachineArn': state_machine_arn,
            'name': '12345',
            'status': 'FAILED',
            'startDate': '2023-01-01T00:00:00Z',
            'stopDate': '2023-01-01T00:00:01Z',
            'error': 'States.TaskFailed',
            'cause': 'Something went wrong',
        }

        # Set up mock context
        ctx = MagicMock(spec=Context)
        ctx.info = AsyncMock()
        ctx.error = AsyncMock()

        # Call the function
        result = await invoke_standard_state_machine_impl(
            state_machine_name, state_machine_arn, {'param': 'value'}, ctx
        )

        # Verify results
        mock_sfn_client.start_execution.assert_called_once_with(
            stateMachineArn=state_machine_arn, input='{"param": "value"}'
        )
        ctx.info.assert_called()
        ctx.error.assert_called_once()
        assert 'State machine error-state-machine execution failed with status: FAILED' in result
        assert 'error: States.TaskFailed' in result
        assert 'cause: Something went wrong' in result

    @pytest.mark.asyncio
    @patch('awslabs.stepfunctions_tool_mcp_server.server.sfn_client')
    async def test_standard_state_machine_polling(self, mock_sfn_client):
        """Test polling behavior during state machine execution."""
        # Set up test data
        state_machine_name = 'test-state-machine'
        state_machine_arn = (
            f'arn:aws:states:us-east-1:123456789012:stateMachine:{state_machine_name}'
        )
        execution_arn = (
            f'arn:aws:states:us-east-1:123456789012:execution:{state_machine_name}:12345'
        )

        # Set up mock responses
        mock_sfn_client.start_execution.return_value = {
            'executionArn': execution_arn,
            'startDate': '2023-01-01T00:00:00Z',
        }

        # Set up describe_execution to return RUNNING twice, then SUCCEEDED
        mock_sfn_client.describe_execution.side_effect = [
            {
                'executionArn': execution_arn,
                'stateMachineArn': state_machine_arn,
                'name': '12345',
                'status': 'RUNNING',
                'startDate': '2023-01-01T00:00:00Z',
            },
            {
                'executionArn': execution_arn,
                'stateMachineArn': state_machine_arn,
                'name': '12345',
                'status': 'RUNNING',
                'startDate': '2023-01-01T00:00:00Z',
            },
            {
                'executionArn': execution_arn,
                'stateMachineArn': state_machine_arn,
                'name': '12345',
                'status': 'SUCCEEDED',
                'startDate': '2023-01-01T00:00:00Z',
                'stopDate': '2023-01-01T00:00:01Z',
                'output': '{"result": "success"}',
            },
        ]

        # Set up mock context
        ctx = MagicMock(spec=Context)
        ctx.info = AsyncMock()
        ctx.error = AsyncMock()

        # Call the function
        result = await invoke_standard_state_machine_impl(
            state_machine_name, state_machine_arn, {'param': 'value'}, ctx
        )

        # Verify results
        assert mock_sfn_client.describe_execution.call_count == 3
        ctx.info.assert_called()
        assert 'State machine test-state-machine returned:' in result
        assert '"result": "success"' in result

    @pytest.mark.asyncio
    @patch('awslabs.stepfunctions_tool_mcp_server.server.sfn_client')
    async def test_standard_state_machine_complex_input(self, mock_sfn_client):
        """Test Standard state machine with complex input and output."""
        # Set up test data
        state_machine_name = 'test-complex'
        state_machine_arn = (
            f'arn:aws:states:us-east-1:123456789012:stateMachine:{state_machine_name}'
        )
        execution_arn = (
            f'arn:aws:states:us-east-1:123456789012:execution:{state_machine_name}:12345'
        )
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

        # Set up mock responses
        mock_sfn_client.start_execution.return_value = {
            'executionArn': execution_arn,
            'startDate': '2023-01-01T00:00:00Z',
        }

        mock_sfn_client.describe_execution.return_value = {
            'executionArn': execution_arn,
            'stateMachineArn': state_machine_arn,
            'name': '12345',
            'status': 'SUCCEEDED',
            'startDate': '2023-01-01T00:00:00Z',
            'stopDate': '2023-01-01T00:00:01Z',
            'output': json.dumps(complex_input),
        }

        # Set up mock context
        ctx = MagicMock(spec=Context)
        ctx.info = AsyncMock()
        ctx.error = AsyncMock()

        # Call the function
        result = await invoke_standard_state_machine_impl(
            state_machine_name, state_machine_arn, complex_input, ctx
        )

        # Verify results
        mock_sfn_client.start_execution.assert_called_once_with(
            stateMachineArn=state_machine_arn, input=json.dumps(complex_input)
        )
        assert 'State machine test-complex returned:' in result
        assert '"data": {' in result
        assert '"nested": {' in result
        assert '"array": [' in result
        assert '"metadata": {' in result

    @pytest.mark.asyncio
    @patch('awslabs.stepfunctions_tool_mcp_server.server.sfn_client')
    async def test_standard_state_machine_other_statuses(self, mock_sfn_client):
        """Test handling of other execution statuses."""
        # Set up test data
        state_machine_name = 'test-state-machine'
        state_machine_arn = (
            f'arn:aws:states:us-east-1:123456789012:stateMachine:{state_machine_name}'
        )
        execution_arn = (
            f'arn:aws:states:us-east-1:123456789012:execution:{state_machine_name}:12345'
        )

        # Test different status types
        status_cases = [
            ('TIMED_OUT', 'Timeout error', 'Execution timed out'),
            ('ABORTED', 'Abort error', 'Execution was aborted'),
        ]

        for status, error, cause in status_cases:
            # Set up mock responses
            mock_sfn_client.start_execution.return_value = {
                'executionArn': execution_arn,
                'startDate': '2023-01-01T00:00:00Z',
            }

            mock_sfn_client.describe_execution.return_value = {
                'executionArn': execution_arn,
                'stateMachineArn': state_machine_arn,
                'name': '12345',
                'status': status,
                'startDate': '2023-01-01T00:00:00Z',
                'stopDate': '2023-01-01T00:00:01Z',
                'error': error,
                'cause': cause,
            }

            # Set up mock context
            ctx = MagicMock(spec=Context)
            ctx.info = AsyncMock()
            ctx.error = AsyncMock()

            # Call the function
            result = await invoke_standard_state_machine_impl(
                state_machine_name, state_machine_arn, {'param': 'value'}, ctx
            )

            # Verify results
            assert (
                f'State machine {state_machine_name} execution failed with status: {status}'
                in result
            )
            assert f'error: {error}' in result
            assert f'cause: {cause}' in result
            ctx.error.assert_called_once()

            # Reset mocks for next iteration
            mock_sfn_client.reset_mock()
            ctx.reset_mock()
