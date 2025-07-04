"""Additional tests to improve coverage for the server module of the lambda-tool-mcp-server."""

import json
import logging
import pytest
from unittest.mock import MagicMock, patch


with pytest.MonkeyPatch().context() as CTX:
    CTX.setattr('boto3.Session', MagicMock)
    from awslabs.lambda_tool_mcp_server.server import (
        filter_functions_by_tag,
        format_lambda_response,
        register_lambda_functions,
        sanitize_tool_name,
        validate_function_name,
    )


class TestFormatLambdaResponseCoverage:
    """Additional tests for the format_lambda_response function to improve coverage."""

    def test_unicode_decode_error(self):
        """Test with payload that causes UnicodeDecodeError."""
        # Create a binary payload that will cause UnicodeDecodeError when trying to decode as JSON
        # This specifically targets line 120 in server.py
        invalid_json = None
        try:
            # Force a UnicodeDecodeError by creating invalid UTF-8 and trying to decode it
            invalid_json = b'{"key": "\x80\x81\x82\x83"}'
            json.loads(invalid_json.decode('utf-8'))
            assert False, 'Should have raised UnicodeDecodeError'
        except UnicodeDecodeError:
            # Now test our function with this payload
            assert invalid_json is not None
            result = format_lambda_response('test-function', invalid_json)
            assert 'Function test-function returned payload:' in result
            assert str(invalid_json) in result

    def test_format_lambda_response_variants(self):
        """Test formatting different types of Lambda responses."""
        # Test with empty JSON object
        assert 'Function test-function returned: {}' in format_lambda_response(
            'test-function', b'{}'
        )

        # Test with nested JSON
        complex_json = json.dumps({'data': {'nested': {'value': 123}}}).encode()
        result = format_lambda_response('test-function', complex_json)
        assert 'Function test-function returned:' in result
        assert '"data": {' in result
        assert '"nested": {' in result
        assert '"value": 123' in result


class TestFilterFunctionsByTagCoverage:
    """Additional tests for the filter_functions_by_tag function to improve coverage."""

    def test_specific_error_getting_tags(self, caplog):
        """Test specific error handling when getting tags."""
        with patch('awslabs.lambda_tool_mcp_server.server.lambda_client') as mock_client:
            # Make list_tags raise a specific exception type
            mock_client.list_tags.side_effect = Exception('Access denied')

            functions = [
                {
                    'FunctionName': 'test-function-1',
                    'FunctionArn': 'arn:aws:lambda:us-east-1:123456789012:function:test-function-1',
                },
            ]

            with caplog.at_level(logging.WARNING):
                # Should log a warning but not raise an exception
                result = filter_functions_by_tag(functions, 'test-key', 'test-value')

                # Should return an empty list
                assert len(result) == 0

                # Verify the warning was logged
                assert 'Error getting tags for function test-function-1' in caplog.text
                assert 'Access denied' in caplog.text


class TestRegisterLambdaFunctionsCoverage:
    """Additional tests for the register_lambda_functions function to improve coverage."""

    @patch('awslabs.lambda_tool_mcp_server.server.FUNCTION_TAG_KEY', 'test-key')
    @patch('awslabs.lambda_tool_mcp_server.server.FUNCTION_TAG_VALUE', '')
    @patch('awslabs.lambda_tool_mcp_server.server.create_lambda_tool')
    def test_register_with_incomplete_tag_config(
        self, mock_create_lambda_tool, mock_lambda_client, caplog
    ):
        """Test registering Lambda functions with incomplete tag configuration."""
        with patch('awslabs.lambda_tool_mcp_server.server.lambda_client', mock_lambda_client):
            with caplog.at_level(logging.WARNING):
                # Call the function
                register_lambda_functions()

                # Should not register any functions
                assert mock_create_lambda_tool.call_count == 0

                # Should log a warning
                assert (
                    'Both FUNCTION_TAG_KEY and FUNCTION_TAG_VALUE must be set to filter by tag'
                    in caplog.text
                )

    @patch('awslabs.lambda_tool_mcp_server.server.FUNCTION_TAG_KEY', '')
    @patch('awslabs.lambda_tool_mcp_server.server.FUNCTION_TAG_VALUE', 'test-value')
    @patch('awslabs.lambda_tool_mcp_server.server.create_lambda_tool')
    def test_register_with_incomplete_tag_config_reversed(
        self, mock_create_lambda_tool, mock_lambda_client, caplog
    ):
        """Test registering Lambda functions with incomplete tag configuration (reversed case)."""
        with patch('awslabs.lambda_tool_mcp_server.server.lambda_client', mock_lambda_client):
            with caplog.at_level(logging.WARNING):
                # Call the function
                register_lambda_functions()

                # Should not register any functions
                assert mock_create_lambda_tool.call_count == 0

                # Should log a warning
                assert (
                    'Both FUNCTION_TAG_KEY and FUNCTION_TAG_VALUE must be set to filter by tag'
                    in caplog.text
                )


class TestValidateFunctionNameCoverage:
    """Additional tests for the validate_function_name function to improve coverage."""

    def test_validate_function_name_edge_cases(self):
        """Test edge cases for function name validation."""
        # Empty function name
        assert validate_function_name('') is True  # When no filters are set

        # With prefix set
        with patch('awslabs.lambda_tool_mcp_server.server.FUNCTION_PREFIX', 'test-'):
            assert validate_function_name('') is False
            assert validate_function_name('test-') is True
            assert validate_function_name('test') is False

        # With list set
        with patch('awslabs.lambda_tool_mcp_server.server.FUNCTION_LIST', ['func1', 'func2']):
            assert validate_function_name('') is False
            assert validate_function_name('func1') is True
            assert validate_function_name('func3') is False


class TestSanitizeToolNameCoverage:
    """Additional tests for the sanitize_tool_name function to improve coverage."""

    def test_sanitize_tool_name_edge_cases(self):
        """Test edge cases for tool name sanitization."""
        # Empty name
        assert sanitize_tool_name('') == ''

        # Name with only invalid characters
        assert sanitize_tool_name('!@#$%^') == '______'

        # Name with mixed valid and invalid characters
        assert sanitize_tool_name('func-123!@#') == 'func_123___'

        # Name starting with multiple numbers
        assert sanitize_tool_name('123func') == '_123func'
