"""Tests for the server module of the lambda-tool-mcp-server."""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


with pytest.MonkeyPatch().context() as CTX:
    CTX.setattr('boto3.Session', MagicMock)
    from awslabs.lambda_tool_mcp_server.server import (
        create_lambda_tool,
        filter_functions_by_tag,
        format_lambda_response,
        invoke_lambda_function_impl,
        main,
        register_lambda_functions,
        sanitize_tool_name,
        validate_function_name,
    )

    class TestValidateFunctionName:
        """Tests for the validate_function_name function."""

        def test_empty_prefix_and_list(self):
            """Test with empty prefix and list."""
            assert validate_function_name('any-function') is True

        @patch('awslabs.lambda_tool_mcp_server.server.FUNCTION_PREFIX', 'test-')
        def test_prefix_match(self):
            """Test with matching prefix."""
            assert validate_function_name('test-function') is True
            assert validate_function_name('other-function') is False

        @patch('awslabs.lambda_tool_mcp_server.server.FUNCTION_LIST', 'func1,func2,func3')
        def test_list_match(self):
            """Test with function in list."""
            assert validate_function_name('func1') is True
            assert validate_function_name('func2') is True
            assert validate_function_name('other-func') is False

        @patch('awslabs.lambda_tool_mcp_server.server.FUNCTION_PREFIX', 'test-')
        @patch('awslabs.lambda_tool_mcp_server.server.FUNCTION_LIST', 'func1,func2')
        def test_prefix_and_list(self):
            """Test with both prefix and list."""
            assert validate_function_name('test-function') is True
            assert validate_function_name('func1') is True
            assert validate_function_name('other-func') is False

    class TestSanitizeToolName:
        """Tests for the sanitize_tool_name function."""

        @patch('awslabs.lambda_tool_mcp_server.server.FUNCTION_PREFIX', 'prefix-')
        @patch('awslabs.lambda_tool_mcp_server.server.FUNCTION_LIST', 'func1,func2')
        def test_remove_prefix(self):
            """Test removing prefix from function name."""
            assert sanitize_tool_name('prefix-function') == 'function'

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

    class TestFormatLambdaResponse:
        """Tests for the format_lambda_response function."""

        def test_json_payload(self):
            """Test with valid JSON payload."""
            payload = json.dumps({'result': 'success'}).encode()
            result = format_lambda_response('test-function', payload)
            assert 'Function test-function returned:' in result
            assert '"result": "success"' in result

        def test_non_json_payload(self):
            """Test with non-JSON payload."""
            payload = b'Non-JSON response'
            result = format_lambda_response('test-function', payload)
            assert "Function test-function returned payload: b'Non-JSON response'" == result

        def test_json_decode_error(self):
            """Test with invalid JSON payload."""
            payload = b'{invalid json}'
            result = format_lambda_response('test-function', payload)
            assert 'Function test-function returned payload:' in result

    class TestInvokeLambdaFunctionImpl:
        """Tests for the invoke_lambda_function_impl function."""

        @pytest.mark.asyncio
        async def test_successful_invocation(self, mock_lambda_client):
            """Test successful Lambda function invocation."""
            with patch('awslabs.lambda_tool_mcp_server.server.lambda_client', mock_lambda_client):
                ctx = AsyncMock()
                result = await invoke_lambda_function_impl(
                    'test-function-1', {'param': 'value'}, ctx
                )

                # Check that the Lambda function was invoked with the correct parameters
                mock_lambda_client.invoke.assert_called_once_with(
                    FunctionName='test-function-1',
                    InvocationType='RequestResponse',
                    Payload=json.dumps({'param': 'value'}),
                )

                # Check that the context methods were called
                ctx.info.assert_called()

                # Check the result
                assert 'Function test-function-1 returned:' in result
                assert '"result": "success"' in result

        @pytest.mark.asyncio
        async def test_function_error(self, mock_lambda_client):
            """Test Lambda function invocation with error."""
            with patch('awslabs.lambda_tool_mcp_server.server.lambda_client', mock_lambda_client):
                ctx = AsyncMock()
                result = await invoke_lambda_function_impl(
                    'error-function', {'param': 'value'}, ctx
                )

                # Check that the context methods were called
                ctx.info.assert_called()
                ctx.error.assert_called_once()

                # Check the result
                assert 'Function error-function returned with error:' in result

        @pytest.mark.asyncio
        async def test_non_json_response(self, mock_lambda_client):
            """Test Lambda function invocation with non-JSON response."""
            with patch('awslabs.lambda_tool_mcp_server.server.lambda_client', mock_lambda_client):
                ctx = AsyncMock()
                result = await invoke_lambda_function_impl(
                    'test-function-2', {'param': 'value'}, ctx
                )

                # Check the result
                assert "Function test-function-2 returned payload: b'Non-JSON response'" == result

    class TestCreateLambdaTool:
        """Tests for the create_lambda_tool function."""

        @patch('awslabs.lambda_tool_mcp_server.server.mcp')
        def test_create_tool(self, mock_mcp):
            """Test creating a Lambda tool."""
            # Set up the mock
            mock_decorator = MagicMock()
            mock_mcp.tool.return_value = mock_decorator

            # Call the function
            function_name = 'test-function'
            description = 'Test function description'
            create_lambda_tool(function_name, description)

            # Check that mcp.tool was called with the correct name
            mock_mcp.tool.assert_called_once_with(name='test_function')

            # Check that the decorator was applied to a function
            mock_decorator.assert_called_once()

            # Get the function that was decorated
            decorated_function = mock_decorator.call_args[0][0]

            # Check that the function has the correct docstring
            assert decorated_function.__doc__ == description

        @patch('awslabs.lambda_tool_mcp_server.server.FUNCTION_PREFIX', 'test-')
        @patch('awslabs.lambda_tool_mcp_server.server.mcp')
        def test_create_tool_with_prefix(self, mock_mcp):
            """Test creating a Lambda tool with prefix."""
            # Set up the mock
            mock_decorator = MagicMock()
            mock_mcp.tool.return_value = mock_decorator

            # Call the function
            function_name = 'prefix-test-function'
            description = 'Test function description'
            create_lambda_tool(function_name, description)

            # Check that mcp.tool was called with the correct name (prefix removed)
            mock_mcp.tool.assert_called_once_with(name=function_name.replace('-', '_'))

    class TestFilterFunctionsByTag:
        """Tests for the filter_functions_by_tag function."""

        def test_matching_tags(self, mock_lambda_client):
            """Test filtering functions with matching tags."""
            with patch('awslabs.lambda_tool_mcp_server.server.lambda_client', mock_lambda_client):
                functions = [
                    {
                        'FunctionName': 'test-function-1',
                        'FunctionArn': 'arn:aws:lambda:us-east-1:123456789012:function:test-function-1',
                    },
                    {
                        'FunctionName': 'test-function-2',
                        'FunctionArn': 'arn:aws:lambda:us-east-1:123456789012:function:test-function-2',
                    },
                    {
                        'FunctionName': 'prefix-test-function-3',
                        'FunctionArn': 'arn:aws:lambda:us-east-1:123456789012:function:prefix-test-function-3',
                    },
                ]

                result = filter_functions_by_tag(functions, 'test-key', 'test-value')

                # Should return functions with the matching tag
                assert len(result) == 2
                assert result[0]['FunctionName'] == 'test-function-1'
                assert result[1]['FunctionName'] == 'prefix-test-function-3'

        def test_no_matching_tags(self, mock_lambda_client):
            """Test filtering functions with no matching tags."""
            with patch('awslabs.lambda_tool_mcp_server.server.lambda_client', mock_lambda_client):
                functions = [
                    {
                        'FunctionName': 'test-function-1',
                        'FunctionArn': 'arn:aws:lambda:us-east-1:123456789012:function:test-function-1',
                    },
                    {
                        'FunctionName': 'test-function-2',
                        'FunctionArn': 'arn:aws:lambda:us-east-1:123456789012:function:test-function-2',
                    },
                ]

                result = filter_functions_by_tag(
                    functions, 'non-existent-key', 'non-existent-value'
                )

                # Should return an empty list
                assert len(result) == 0

        def test_error_getting_tags(self, mock_lambda_client):
            """Test error handling when getting tags."""
            with patch('awslabs.lambda_tool_mcp_server.server.lambda_client', mock_lambda_client):
                # Make list_tags raise an exception
                mock_lambda_client.list_tags.side_effect = Exception('Error getting tags')

                functions = [
                    {
                        'FunctionName': 'test-function-1',
                        'FunctionArn': 'arn:aws:lambda:us-east-1:123456789012:function:test-function-1',
                    },
                ]

                # Should not raise an exception, but log a warning
                result = filter_functions_by_tag(functions, 'test-key', 'test-value')

                # Should return an empty list
                assert len(result) == 0

    class TestRegisterLambdaFunctions:
        """Tests for the register_lambda_functions function."""

        @patch('awslabs.lambda_tool_mcp_server.server.FUNCTION_PREFIX', 'prefix-')
        # @patch('awslabs.lambda_tool_mcp_server.server.lambda_client')
        @patch('awslabs.lambda_tool_mcp_server.server.create_lambda_tool')
        def test_register_with_prefix(self, mock_create_lambda_tool, mock_lambda_client):
            """Test registering Lambda functions with prefix filter."""
            with patch('awslabs.lambda_tool_mcp_server.server.lambda_client', mock_lambda_client):
                # Call the function
                register_lambda_functions()

                # Should only register functions with the prefix
                assert mock_create_lambda_tool.call_count == 1
                mock_create_lambda_tool.assert_called_with(
                    'prefix-test-function-3', 'Test function 3 with prefix', None
                )

        @patch(
            'awslabs.lambda_tool_mcp_server.server.FUNCTION_LIST',
            'test-function-1,test-function-2',
        )
        # @patch('awslabs.lambda_tool_mcp_server.server.lambda_client')
        @patch('awslabs.lambda_tool_mcp_server.server.create_lambda_tool')
        def test_register_with_list(self, mock_create_lambda_tool, mock_lambda_client):
            """Test registering Lambda functions with list filter."""
            with patch('awslabs.lambda_tool_mcp_server.server.lambda_client', mock_lambda_client):
                # Set environment variables
                # monkeypatch = pytest.MonkeyPatch()
                # monkeypatch.setattr(
                #     awslabs.lambda_tool_mcp_server.server, 'FUNCTION_PREFIX', '', raising=False
                # )
                # monkeypatch.setattr(
                #     awslabs.lambda_tool_mcp_server.server,
                #     'FUNCTION_LIST',
                #     'test-function-1,test-function-2',
                #     raising=False,
                # )
                # monkeypatch.setattr(
                #     awslabs.lambda_tool_mcp_server.server, 'FUNCTION_TAG_KEY', '', raising=False
                # )
                # monkeypatch.setattr(
                #     awslabs.lambda_tool_mcp_server.server, 'FUNCTION_TAG_VALUE', '', raising=False
                # )
                # os.environ['FUNCTION_PREFIX'] = ''
                # os.environ['FUNCTION_LIST'] = 'test-function-1,test-function-2'
                # os.environ['FUNCTION_TAG_KEY'] = ''
                # os.environ['FUNCTION_TAG_VALUE'] = ''

                # try:
                # Call the function
                register_lambda_functions()

                # Should only register functions in the list
                assert mock_create_lambda_tool.call_count == 2
                mock_create_lambda_tool.assert_any_call(
                    'test-function-1', 'Test function 1 description', None
                )
                mock_create_lambda_tool.assert_any_call(
                    'test-function-2', 'Test function 2 description', None
                )
                # finally:
                #     # Clean up environment variables
                #     monkeypatch.setattr(
                #         awslabs.lambda_tool_mcp_server.server, 'FUNCTION_PREFIX', '', raising=False
                #     )
                #     monkeypatch.setattr(
                #         awslabs.lambda_tool_mcp_server.server, 'FUNCTION_LIST', '', raising=False
                #     )
                #     monkeypatch.setattr(
                #         awslabs.lambda_tool_mcp_server.server, 'FUNCTION_TAG_KEY', '', raising=False
                #     )
                #     monkeypatch.setattr(
                #         awslabs.lambda_tool_mcp_server.server, 'FUNCTION_TAG_VALUE', '', raising=False
                #     )
                #     del os.environ['FUNCTION_PREFIX']
                #     del os.environ['FUNCTION_LIST']
                #     del os.environ['FUNCTION_TAG_KEY']
                #     del os.environ['FUNCTION_TAG_VALUE']

        @patch('awslabs.lambda_tool_mcp_server.server.FUNCTION_TAG_KEY', 'test-key')
        @patch('awslabs.lambda_tool_mcp_server.server.FUNCTION_TAG_VALUE', 'test-value')
        @patch('awslabs.lambda_tool_mcp_server.server.create_lambda_tool')
        def test_register_with_tags(self, mock_create_lambda_tool, mock_lambda_client):
            """Test registering Lambda functions with tag filter."""
            with patch('awslabs.lambda_tool_mcp_server.server.lambda_client', mock_lambda_client):
                # Set environment variables
                # monkeypatch = pytest.MonkeyPatch()
                # monkeypatch.setattr(
                #     awslabs.lambda_tool_mcp_server.server, 'FUNCTION_PREFIX', '', raising=False
                # )
                # monkeypatch.setattr(
                #     awslabs.lambda_tool_mcp_server.server, 'FUNCTION_LIST', '', raising=False
                # )
                # monkeypatch.setattr(
                #     awslabs.lambda_tool_mcp_server.server, 'FUNCTION_TAG_KEY', 'test-key', raising=False
                # )
                # monkeypatch.setattr(
                #     awslabs.lambda_tool_mcp_server.server, 'FUNCTION_TAG_VALUE', 'test-value', raising=False
                # )
                # os.environ['FUNCTION_PREFIX'] = ''
                # os.environ['FUNCTION_LIST'] = ''
                # os.environ['FUNCTION_TAG_KEY'] = 'test-key'
                # os.environ['FUNCTION_TAG_VALUE'] = 'test-value'

                # try:
                # Call the function
                register_lambda_functions()

                # Should only register functions with the matching tag
                assert mock_create_lambda_tool.call_count == 2
                mock_create_lambda_tool.assert_any_call(
                    'test-function-1', 'Test function 1 description', None
                )
                mock_create_lambda_tool.assert_any_call(
                    'prefix-test-function-3', 'Test function 3 with prefix', None
                )
                # finally:
                #     # Clean up environment variables
                #     monkeypatch.setattr(
                #         awslabs.lambda_tool_mcp_server.server, 'FUNCTION_PREFIX', '', raising=False
                #     )
                #     monkeypatch.setattr(
                #         awslabs.lambda_tool_mcp_server.server, 'FUNCTION_LIST', '', raising=False
                #     )
                #     monkeypatch.setattr(
                #         awslabs.lambda_tool_mcp_server.server, 'FUNCTION_TAG_KEY', '', raising=False
                #     )
                #     monkeypatch.setattr(
                #         awslabs.lambda_tool_mcp_server.server, 'FUNCTION_TAG_VALUE', '', raising=False
                #     )
                #     del os.environ['FUNCTION_PREFIX']
                #     del os.environ['FUNCTION_LIST']
                #     del os.environ['FUNCTION_TAG_KEY']
                #     del os.environ['FUNCTION_TAG_VALUE']

        @patch('awslabs.lambda_tool_mcp_server.server.create_lambda_tool')
        def test_register_with_no_filters(self, mock_create_lambda_tool, mock_lambda_client):
            """Test registering Lambda functions with no filters."""
            with patch('awslabs.lambda_tool_mcp_server.server.lambda_client', mock_lambda_client):
                # Call the function
                register_lambda_functions()

                # Should register all functions
                assert mock_create_lambda_tool.call_count == 4
                mock_create_lambda_tool.assert_any_call(
                    'test-function-1', 'Test function 1 description', None
                )
                mock_create_lambda_tool.assert_any_call(
                    'test-function-2', 'Test function 2 description', None
                )
                mock_create_lambda_tool.assert_any_call(
                    'prefix-test-function-3', 'Test function 3 with prefix', None
                )
                mock_create_lambda_tool.assert_any_call('other-function', '', None)

        @patch('awslabs.lambda_tool_mcp_server.server.lambda_client')
        def test_register_error_handling(self, mock_lambda_client):
            """Test error handling in register_lambda_functions."""
            # Make list_functions raise an exception
            mock_lambda_client.list_functions.side_effect = Exception('Error listing functions')

            # Should not raise an exception
            register_lambda_functions()

    class TestMain:
        """Tests for the main function."""

        @patch('awslabs.lambda_tool_mcp_server.server.register_lambda_functions')
        @patch('awslabs.lambda_tool_mcp_server.server.mcp')
        def test_main_stdio(self, mock_mcp, mock_register_lambda_functions):
            """Test main function with stdio transport."""
            # Set up the mock

            # Call the function
            main()

            # Check that register_lambda_functions was called
            mock_register_lambda_functions.assert_called_once()

            # Check that mcp.run was called with no transport
            mock_mcp.run.assert_called_once_with()

        @patch('awslabs.lambda_tool_mcp_server.server.mcp.run')
        @patch('sys.argv', ['awslabs.lambda-tool-mcp-server'])
        def test_main_default(self, mock_run):
            """Test main function with default arguments."""
            # Call the main function
            main()

            # Check that mcp.run was called with the correct arguments
            mock_run.assert_called_once()
            assert mock_run.call_args[1].get('transport') is None
