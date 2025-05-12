"""Tests for the server module of the stepfunctions-mcp-server."""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


with pytest.MonkeyPatch().context() as CTX:
    CTX.setattr('boto3.Session', MagicMock)
    from awslabs.stepfunctions_mcp_server.server import (
        create_state_machine_tool,
        filter_state_machines_by_tag,
        format_state_machine_response,
        invoke_state_machine_impl,
        main,
        register_state_machines,
        sanitize_tool_name,
        validate_state_machine_name,
    )

    class TestValidateStateMachineName:
        """Tests for the validate_state_machine_name function."""

        def test_empty_prefix_and_list(self):
            """Test with empty prefix and list."""
            assert validate_state_machine_name('any-state-machine') is True

        @patch('awslabs.stepfunctions_mcp_server.server.STATE_MACHINE_PREFIX', 'test-')
        def test_prefix_match(self):
            """Test with matching prefix."""
            assert validate_state_machine_name('test-state-machine') is True
            assert validate_state_machine_name('other-state-machine') is False

        @patch('awslabs.stepfunctions_mcp_server.server.STATE_MACHINE_LIST', 'sm1,sm2,sm3')
        def test_list_match(self):
            """Test with state machine in list."""
            assert validate_state_machine_name('sm1') is True
            assert validate_state_machine_name('sm2') is True
            assert validate_state_machine_name('other-sm') is False

        @patch('awslabs.stepfunctions_mcp_server.server.STATE_MACHINE_PREFIX', 'test-')
        @patch('awslabs.stepfunctions_mcp_server.server.STATE_MACHINE_LIST', 'sm1,sm2')
        def test_prefix_and_list(self):
            """Test with both prefix and list."""
            assert validate_state_machine_name('test-state-machine') is True
            assert validate_state_machine_name('sm1') is True
            assert validate_state_machine_name('other-sm') is False

    class TestSanitizeToolName:
        """Tests for the sanitize_tool_name function."""

        @patch('awslabs.stepfunctions_mcp_server.server.STATE_MACHINE_PREFIX', 'prefix-')
        @patch('awslabs.stepfunctions_mcp_server.server.STATE_MACHINE_LIST', 'sm1,sm2')
        def test_remove_prefix(self):
            """Test removing prefix from state machine name."""
            assert sanitize_tool_name('prefix-state-machine') == 'state_machine'

        def test_invalid_characters(self):
            """Test replacing invalid characters."""
            assert (
                sanitize_tool_name('function-name.with:invalid@chars')
                == 'function_name_with_invalid_chars'
            )

        def test_numeric_first_character(self):
            """Test handling numeric first character."""
            assert sanitize_tool_name('123function') == '_123function'

        def test_valid_name(self):
            """Test with already valid name."""
            assert sanitize_tool_name('valid_function_name') == 'valid_function_name'

    class TestFormatStateMachineResponse:
        """Tests for the format_state_machine_response function."""

        def test_json_payload(self):
            """Test with valid JSON payload."""
            payload = json.dumps({'result': 'success'}).encode()
            result = format_state_machine_response('test-state-machine', payload)
            assert 'State machine test-state-machine returned:' in result
            assert '"result": "success"' in result

        def test_non_json_payload(self):
            """Test with non-JSON payload."""
            payload = b'Non-JSON response'
            result = format_state_machine_response('test-state-machine', payload)
            assert "State machine test-state-machine returned payload: b'Non-JSON response'" == result

        def test_json_decode_error(self):
            """Test with invalid JSON payload."""
            payload = b'{invalid json}'
            result = format_state_machine_response('test-state-machine', payload)
            assert 'State machine test-state-machine returned payload:' in result

    class TestInvokeStateMachineImpl:
        """Tests for the invoke_state_machine_impl function."""

        @pytest.mark.asyncio
        async def test_successful_invocation(self, mock_lambda_client):
            """Test successful Step Functions state machine invocation."""
            with patch('awslabs.stepfunctions_mcp_server.server.lambda_client', mock_lambda_client):
                ctx = AsyncMock()
                result = await invoke_state_machine_impl(
                    'test-state-machine-1', {'param': 'value'}, ctx
                )

                # Check that the state machine was invoked with the correct parameters
                mock_lambda_client.invoke.assert_called_once_with(
                    FunctionName='test-state-machine-1',
                    InvocationType='RequestResponse',
                    Payload=json.dumps({'param': 'value'}),
                )

                # Check that the context methods were called
                ctx.info.assert_called()

                # Check the result
                assert 'State machine test-state-machine-1 returned:' in result
                assert '"result": "success"' in result

        @pytest.mark.asyncio
        async def test_function_error(self, mock_lambda_client):
            """Test Step Functions state machine invocation with error."""
            with patch('awslabs.stepfunctions_mcp_server.server.lambda_client', mock_lambda_client):
                ctx = AsyncMock()
                result = await invoke_state_machine_impl(
                    'error-state-machine', {'param': 'value'}, ctx
                )

                # Check that the context methods were called
                ctx.info.assert_called()
                ctx.error.assert_called_once()

                # Check the result
                assert 'State machine error-state-machine returned with error:' in result

        @pytest.mark.asyncio
        async def test_non_json_response(self, mock_lambda_client):
            """Test Step Functions state machine invocation with non-JSON response."""
            with patch('awslabs.stepfunctions_mcp_server.server.lambda_client', mock_lambda_client):
                ctx = AsyncMock()
                result = await invoke_state_machine_impl(
                    'test-state-machine-2', {'param': 'value'}, ctx
                )

                # Check the result
                assert "State machine test-state-machine-2 returned payload: b'Non-JSON response'" == result

    class TestCreateStateMachineTool:
        """Tests for the create_state_machine_tool function."""

        @patch('awslabs.stepfunctions_mcp_server.server.mcp')
        def test_create_tool(self, mock_mcp):
            """Test creating a Step Functions tool."""
            # Set up the mock
            mock_decorator = MagicMock()
            mock_mcp.tool.return_value = mock_decorator

            # Call the function
            state_machine_name = 'test-state-machine'
            description = 'Test state machine description'
            create_state_machine_tool(state_machine_name, description)

            # Check that mcp.tool was called with the correct name
            mock_mcp.tool.assert_called_once_with(name='test_state_machine')

            # Check that the decorator was applied to a function
            mock_decorator.assert_called_once()

            # Get the function that was decorated
            decorated_function = mock_decorator.call_args[0][0]

            # Check that the function has the correct docstring
            assert decorated_function.__doc__ == description

        @patch('awslabs.stepfunctions_mcp_server.server.STATE_MACHINE_PREFIX', 'test-')
        @patch('awslabs.stepfunctions_mcp_server.server.mcp')
        def test_create_tool_with_prefix(self, mock_mcp):
            """Test creating a Step Functions tool with prefix."""
            # Set up the mock
            mock_decorator = MagicMock()
            mock_mcp.tool.return_value = mock_decorator

            # Call the function
            state_machine_name = 'prefix-test-state-machine'
            description = 'Test state machine description'
            create_state_machine_tool(state_machine_name, description)

            # Check that mcp.tool was called with the correct name (prefix removed)
            mock_mcp.tool.assert_called_once_with(name=state_machine_name.replace('-', '_'))

    class TestFilterStateMachinesByTag:
        """Tests for the filter_state_machines_by_tag function."""

        def test_matching_tags(self, mock_lambda_client):
            """Test filtering state machines with matching tags."""
            with patch('awslabs.stepfunctions_mcp_server.server.lambda_client', mock_lambda_client):
                state_machines = [
                    {
                        'Name': 'test-state-machine-1',
                        'StateMachineArn': 'arn:aws:states:us-east-1:123456789012:stateMachine:test-state-machine-1',
                    },
                    {
                        'Name': 'test-state-machine-2',
                        'StateMachineArn': 'arn:aws:states:us-east-1:123456789012:stateMachine:test-state-machine-2',
                    },
                    {
                        'Name': 'prefix-test-state-machine-3',
                        'StateMachineArn': 'arn:aws:states:us-east-1:123456789012:stateMachine:prefix-test-state-machine-3',
                    },
                ]

                result = filter_state_machines_by_tag(state_machines, 'test-key', 'test-value')

                # Should return state machines with the matching tag
                assert len(result) == 2
                assert result[0]['Name'] == 'test-state-machine-1'
                assert result[1]['Name'] == 'prefix-test-state-machine-3'

        def test_no_matching_tags(self, mock_lambda_client):
            """Test filtering state machines with no matching tags."""
            with patch('awslabs.stepfunctions_mcp_server.server.lambda_client', mock_lambda_client):
                state_machines = [
                    {
                        'Name': 'test-state-machine-1',
                        'StateMachineArn': 'arn:aws:states:us-east-1:123456789012:stateMachine:test-state-machine-1',
                    },
                    {
                        'Name': 'test-state-machine-2',
                        'StateMachineArn': 'arn:aws:states:us-east-1:123456789012:stateMachine:test-state-machine-2',
                    },
                ]

                result = filter_state_machines_by_tag(
                    state_machines, 'non-existent-key', 'non-existent-value'
                )

                # Should return an empty list
                assert len(result) == 0

        def test_error_getting_tags(self, mock_lambda_client):
            """Test error handling when getting tags."""
            with patch('awslabs.stepfunctions_mcp_server.server.lambda_client', mock_lambda_client):
                # Make list_tags raise an exception
                mock_lambda_client.list_tags.side_effect = Exception('Error getting tags')

                state_machines = [
                    {
                        'Name': 'test-state-machine-1',
                        'StateMachineArn': 'arn:aws:states:us-east-1:123456789012:stateMachine:test-state-machine-1',
                    },
                ]

                # Should not raise an exception, but log a warning
                result = filter_state_machines_by_tag(state_machines, 'test-key', 'test-value')

                # Should return an empty list
                assert len(result) == 0

    class TestRegisterStateMachines:
        """Tests for the register_state_machines function."""

        @patch('awslabs.stepfunctions_mcp_server.server.STATE_MACHINE_PREFIX', 'prefix-')
        @patch('awslabs.stepfunctions_mcp_server.server.create_state_machine_tool')
        def test_register_with_prefix(self, mock_create_state_machine_tool, mock_lambda_client):
            """Test registering Step Functions state machines with prefix filter."""
            with patch('awslabs.stepfunctions_mcp_server.server.lambda_client', mock_lambda_client):
                # Call the function
                register_state_machines()

                # Should only register state machines with the prefix
                assert mock_create_state_machine_tool.call_count == 1
                mock_create_state_machine_tool.assert_called_with(
                    'prefix-test-state-machine-3', 'Test state machine 3 with prefix', None
                )

        @patch('awslabs.stepfunctions_mcp_server.server.STATE_MACHINE_LIST', 'test-state-machine-1,test-state-machine-2')
        @patch('awslabs.stepfunctions_mcp_server.server.create_state_machine_tool')
        def test_register_with_list(self, mock_create_state_machine_tool, mock_lambda_client):
            """Test registering Step Functions state machines with list filter."""
            with patch('awslabs.stepfunctions_mcp_server.server.lambda_client', mock_lambda_client):
                # Call the function
                register_state_machines()

                # Should only register state machines in the list
                assert mock_create_state_machine_tool.call_count == 2
                mock_create_state_machine_tool.assert_any_call(
                    'test-state-machine-1', 'Test state machine 1 description', None
                )
                mock_create_state_machine_tool.assert_any_call(
                    'test-state-machine-2', 'Test state machine 2 description', None
                )

        @patch('awslabs.stepfunctions_mcp_server.server.STATE_MACHINE_TAG_KEY', 'test-key')
        @patch('awslabs.stepfunctions_mcp_server.server.STATE_MACHINE_TAG_VALUE', 'test-value')
        @patch('awslabs.stepfunctions_mcp_server.server.create_state_machine_tool')
        def test_register_with_tags(self, mock_create_state_machine_tool, mock_lambda_client):
            """Test registering Step Functions state machines with tag filter."""
            with patch('awslabs.stepfunctions_mcp_server.server.lambda_client', mock_lambda_client):
                # Call the function
                register_state_machines()

                # Should only register state machines with the matching tag
                assert mock_create_state_machine_tool.call_count == 2
                mock_create_state_machine_tool.assert_any_call(
                    'test-state-machine-1', 'Test state machine 1 description', None
                )
                mock_create_state_machine_tool.assert_any_call(
                    'prefix-test-state-machine-3', 'Test state machine 3 with prefix', None
                )

        @patch('awslabs.stepfunctions_mcp_server.server.create_state_machine_tool')
        def test_register_with_no_filters(self, mock_create_state_machine_tool, mock_lambda_client):
            """Test registering Step Functions state machines with no filters."""
            with patch('awslabs.stepfunctions_mcp_server.server.lambda_client', mock_lambda_client):
                # Call the function
                register_state_machines()

                # Should register all state machines
                assert mock_create_state_machine_tool.call_count == 4
                mock_create_state_machine_tool.assert_any_call(
                    'test-state-machine-1', 'Test state machine 1 description', None
                )
                mock_create_state_machine_tool.assert_any_call(
                    'test-state-machine-2', 'Test state machine 2 description', None
                )
                mock_create_state_machine_tool.assert_any_call(
                    'prefix-test-state-machine-3', 'Test state machine 3 with prefix', None
                )
                mock_create_state_machine_tool.assert_any_call('other-state-machine', '', None)

        @patch('awslabs.stepfunctions_mcp_server.server.lambda_client')
        def test_register_error_handling(self, mock_lambda_client):
            """Test error handling in register_state_machines."""
            # Make list_functions raise an exception
            mock_lambda_client.list_functions.side_effect = Exception('Error listing state machines')

            # Should not raise an exception
            register_state_machines()

    class TestMain:
        """Tests for the main function."""

        @patch('awslabs.stepfunctions_mcp_server.server.register_state_machines')
        @patch('awslabs.stepfunctions_mcp_server.server.mcp')
        @patch('argparse.ArgumentParser.parse_args')
        def test_main_sse(self, mock_parse_args, mock_mcp, mock_register_state_machines):
            """Test main function with SSE transport."""
            # Set up the mock
            mock_parse_args.return_value = MagicMock(sse=True, port=8888)

            # Call the function
            main()

            # Check that register_state_machines was called
            mock_register_state_machines.assert_called_once()

            # Check that mcp.run was called with the correct transport
            mock_mcp.run.assert_called_once_with(transport='sse')

            # Check that mcp.settings.port was set
            assert mock_mcp.settings.port == 8888

        @patch('awslabs.stepfunctions_mcp_server.server.register_state_machines')
        @patch('awslabs.stepfunctions_mcp_server.server.mcp')
        @patch('argparse.ArgumentParser.parse_args')
        def test_main_stdio(self, mock_parse_args, mock_mcp, mock_register_state_machines):
            """Test main function with stdio transport."""
            # Set up the mock
            mock_parse_args.return_value = MagicMock(sse=False, port=8888)

            # Call the function
            main()

            # Check that register_state_machines was called
            mock_register_state_machines.assert_called_once()

            # Check that mcp.run was called with no transport
            mock_mcp.run.assert_called_once_with()
