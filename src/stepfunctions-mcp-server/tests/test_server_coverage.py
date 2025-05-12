"""Additional tests to improve coverage for the server module of the stepfunctions-mcp-server."""

import json
import logging
import pytest
from unittest.mock import MagicMock, patch


with pytest.MonkeyPatch().context() as CTX:
    CTX.setattr('boto3.Session', MagicMock)
    from awslabs.stepfunctions_mcp_server.server import (
        filter_state_machines_by_tag,
        format_state_machine_response,
        register_state_machines,
        sanitize_tool_name,
        validate_state_machine_name,
    )


class TestFormatStateMachineResponseCoverage:
    """Additional tests for the format_state_machine_response function to improve coverage."""

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
            result = format_state_machine_response('test-state-machine', invalid_json)
            assert 'State machine test-state-machine returned payload:' in result
            assert str(invalid_json) in result

    def test_format_state_machine_response_variants(self):
        """Test formatting different types of Step Functions responses."""
        # Test with empty JSON object
        assert 'State machine test-state-machine returned: {}' in format_state_machine_response(
            'test-state-machine', b'{}'
        )

        # Test with nested JSON
        complex_json = json.dumps({'data': {'nested': {'value': 123}}}).encode()
        result = format_state_machine_response('test-state-machine', complex_json)
        assert 'State machine test-state-machine returned:' in result
        assert '"data": {' in result
        assert '"nested": {' in result
        assert '"value": 123' in result


class TestFilterStateMachinesByTagCoverage:
    """Additional tests for the filter_state_machines_by_tag function to improve coverage."""

    def test_specific_error_getting_tags(self, caplog):
        """Test specific error handling when getting tags."""
        with patch('awslabs.stepfunctions_mcp_server.server.lambda_client') as mock_client:
            # Make list_tags raise a specific exception type
            mock_client.list_tags.side_effect = Exception('Access denied')

            state_machines = [
                {
                    'Name': 'test-state-machine-1',
                    'StateMachineArn': 'arn:aws:states:us-east-1:123456789012:stateMachine:test-state-machine-1',
                },
            ]

            with caplog.at_level(logging.WARNING):
                # Should log a warning but not raise an exception
                result = filter_state_machines_by_tag(state_machines, 'test-key', 'test-value')

                # Should return an empty list
                assert len(result) == 0

                # Verify the warning was logged
                assert 'Error getting tags for state machine test-state-machine-1' in caplog.text
                assert 'Access denied' in caplog.text


class TestRegisterStateMachinesCoverage:
    """Additional tests for the register_state_machines function to improve coverage."""

    @patch('awslabs.stepfunctions_mcp_server.server.STATE_MACHINE_TAG_KEY', 'test-key')
    @patch('awslabs.stepfunctions_mcp_server.server.STATE_MACHINE_TAG_VALUE', '')
    @patch('awslabs.stepfunctions_mcp_server.server.create_state_machine_tool')
    def test_register_with_incomplete_tag_config(
        self, mock_create_state_machine_tool, mock_lambda_client, caplog
    ):
        """Test registering Step Functions state machines with incomplete tag configuration."""
        with patch('awslabs.stepfunctions_mcp_server.server.lambda_client', mock_lambda_client):
            with caplog.at_level(logging.WARNING):
                # Call the function
                register_state_machines()

                # Should not register any state machines
                assert mock_create_state_machine_tool.call_count == 0

                # Should log a warning
                assert (
                    'Both STATE_MACHINE_TAG_KEY and STATE_MACHINE_TAG_VALUE must be set to filter by tag'
                    in caplog.text
                )

    @patch('awslabs.stepfunctions_mcp_server.server.STATE_MACHINE_TAG_KEY', '')
    @patch('awslabs.stepfunctions_mcp_server.server.STATE_MACHINE_TAG_VALUE', 'test-value')
    @patch('awslabs.stepfunctions_mcp_server.server.create_state_machine_tool')
    def test_register_with_incomplete_tag_config_reversed(
        self, mock_create_state_machine_tool, mock_lambda_client, caplog
    ):
        """Test registering Step Functions state machines with incomplete tag configuration (reversed case)."""
        with patch('awslabs.stepfunctions_mcp_server.server.lambda_client', mock_lambda_client):
            with caplog.at_level(logging.WARNING):
                # Call the function
                register_state_machines()

                # Should not register any state machines
                assert mock_create_state_machine_tool.call_count == 0

                # Should log a warning
                assert (
                    'Both STATE_MACHINE_TAG_KEY and STATE_MACHINE_TAG_VALUE must be set to filter by tag'
                    in caplog.text
                )


class TestValidateStateMachineNameCoverage:
    """Additional tests for the validate_state_machine_name function to improve coverage."""

    def test_validate_state_machine_name_edge_cases(self):
        """Test edge cases for state machine name validation."""
        # Empty state machine name
        assert validate_state_machine_name('') is True  # When no filters are set

        # With prefix set
        with patch('awslabs.stepfunctions_mcp_server.server.STATE_MACHINE_PREFIX', 'test-'):
            assert validate_state_machine_name('') is False
            assert validate_state_machine_name('test-') is True
            assert validate_state_machine_name('test') is False

        # With list set
        with patch('awslabs.stepfunctions_mcp_server.server.STATE_MACHINE_LIST', ['sm1', 'sm2']):
            assert validate_state_machine_name('') is False
            assert validate_state_machine_name('sm1') is True
            assert validate_state_machine_name('sm3') is False


class TestSanitizeToolNameCoverage:
    """Additional tests for the sanitize_tool_name function to improve coverage."""

    def test_sanitize_tool_name_edge_cases(self):
        """Test edge cases for tool name sanitization."""
        # Empty name
        assert sanitize_tool_name('') == ''

        # Name with only invalid characters
        assert sanitize_tool_name('!@#$%^') == '______'

        # Name with mixed valid and invalid characters
        assert sanitize_tool_name('sm-123!@#') == 'sm_123___'

        # Name starting with multiple numbers
        assert sanitize_tool_name('123sm') == '_123sm'
