"""Tests for the format_state_machine_response function."""

import json
import pytest
from unittest.mock import MagicMock


with pytest.MonkeyPatch().context() as CTX:
    CTX.setattr('boto3.Session', MagicMock)
    from awslabs.stepfunctions_mcp_server.server import format_state_machine_response


class TestFormatResponse:
    """Tests for the format_state_machine_response function."""

    def test_format_response_json_success(self):
        """Test formatting a successful JSON response."""
        # Set up test data
        payload = json.dumps({'result': 'success'}).encode()

        # Call the function
        result = format_state_machine_response('test-state-machine', payload)

        # Verify results
        assert 'State machine test-state-machine returned:' in result
        assert '"result": "success"' in result

    def test_format_response_non_json(self):
        """Test formatting a non-JSON response."""
        # Set up test data
        payload = b'Non-JSON response'

        # Call the function
        result = format_state_machine_response('test-state-machine', payload)

        # Verify results
        assert result == "State machine test-state-machine returned payload: b'Non-JSON response'"

    def test_format_response_invalid_json(self):
        """Test formatting an invalid JSON response."""
        # Set up test data
        payload = b'{invalid json}'

        # Call the function
        result = format_state_machine_response('test-state-machine', payload)

        # Verify results
        assert 'State machine test-state-machine returned payload:' in result
        assert str(payload) in result

    def test_format_response_unicode_error(self):
        """Test formatting a response that causes UnicodeDecodeError."""
        # Create a binary payload that will cause UnicodeDecodeError
        payload = b'{"key": "\x80\x81\x82\x83"}'

        # Call the function
        result = format_state_machine_response('test-state-machine', payload)

        # Verify results
        assert 'State machine test-state-machine returned payload:' in result
        assert str(payload) in result

    def test_format_response_complex_json(self):
        """Test formatting a complex JSON response."""
        # Set up test data with nested structure
        complex_data = {
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
        payload = json.dumps(complex_data).encode()

        # Call the function
        result = format_state_machine_response('test-state-machine', payload)

        # Verify results
        assert 'State machine test-state-machine returned:' in result
        assert '"data": {' in result
        assert '"nested": {' in result
        assert '"array": [' in result
        assert '"metadata": {' in result

    def test_format_response_empty_json(self):
        """Test formatting an empty JSON response."""
        # Set up test data
        payload = b'{}'

        # Call the function
        result = format_state_machine_response('test-state-machine', payload)

        # Verify results
        assert 'State machine test-state-machine returned: {}' in result
