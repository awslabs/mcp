"""Tests specifically targeting the format_lambda_response function."""

import pytest
from unittest.mock import MagicMock


with pytest.MonkeyPatch().context() as CTX:
    CTX.setattr('boto3.Session', MagicMock)
    from awslabs.lambda_tool_mcp_server.server import format_lambda_response


def test_format_lambda_response_unicode_decode_error():
    """Test format_lambda_response with a payload that causes UnicodeDecodeError."""
    # Create a binary payload that will cause UnicodeDecodeError
    # This specifically targets line 120 in server.py
    payload = b'\x80\x81\x82\x83'  # Invalid UTF-8 sequence

    # Call the function with the invalid payload
    result = format_lambda_response('test-function', payload)

    # Check the result
    assert 'Function test-function returned payload:' in result
    assert str(payload) in result
