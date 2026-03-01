import base64
import json
import pytest
from awslabs.aws_api_mcp_server.core.common.helpers import (
    as_json,
    get_requests_session,
    is_help_operation,
    validate_aws_region,
)
from botocore.response import StreamingBody
from io import BytesIO
from requests.adapters import HTTPAdapter
from unittest.mock import MagicMock, patch


@pytest.mark.parametrize(
    'valid_region',
    [
        'af-south-1',
        'ap-east-1',
        'ap-east-2',
        'ap-northeast-1',
        'ap-northeast-2',
        'ap-northeast-3',
        'ap-south-1',
        'ap-south-2',
        'ap-southeast-1',
        'ap-southeast-2',
        'ap-southeast-3',
        'ap-southeast-4',
        'ap-southeast-5',
        'ap-southeast-7',
        'ca-central-1',
        'ca-west-1',
        'cn-north-1',
        'cn-northwest-1',
        'eusc-de-east-1',
        'eu-central-1',
        'eu-central-2',
        'eu-north-1',
        'eu-south-1',
        'eu-south-2',
        'eu-west-1',
        'eu-west-2',
        'eu-west-3',
        'il-central-1',
        'me-central-1',
        'me-south-1',
        'mx-central-1',
        'sa-east-1',
        'us-east-1',
        'us-east-2',
        'us-gov-east-1',
        'us-gov-west-1',
        'us-iso-east-1',
        'us-isob-east-1',
        'us-west-1',
        'us-west-2',
    ],
)
def test_validate_aws_region_valid_regions(valid_region: str):
    """Test that valid AWS regions pass validation without raising exceptions."""
    # Should not raise any exception
    validate_aws_region(valid_region)


@pytest.mark.parametrize(
    'invalid_region',
    [
        'us-east',
        'us-1',
        'east-1',
        'us-east-1-suffix',
        'verylongstring-us-east-1',
        'us-verylongstring-east-1',
        'us-east-verylongstring-1',
        'us-east-123',
        'us-gov-east-123',
        'this-is-not-a-region-1',
        '',
        ' ',
        'not a region',
    ],
)
@patch('awslabs.aws_api_mcp_server.core.common.helpers.logger')
def test_validate_aws_region_invalid_regions(mock_logger: MagicMock, invalid_region: str):
    """Test that invalid AWS regions raise ValueError and log error."""
    with pytest.raises(ValueError) as exc_info:
        validate_aws_region(invalid_region)

    # Check that the error message contains the invalid region
    assert invalid_region in str(exc_info.value)
    assert 'is not a valid AWS Region' in str(exc_info.value)

    # Check that logger.error was called with the correct message
    expected_error_message = f'{invalid_region} is not a valid AWS Region'
    mock_logger.error.assert_called_once_with(expected_error_message)


def test_get_requests_session():
    """Test that get_requests_session returns a properly configured session."""
    session = get_requests_session()

    https_adapter = session.get_adapter('https://example.com')
    assert isinstance(https_adapter, HTTPAdapter)

    retry_config = https_adapter.max_retries
    assert retry_config.total == 3
    assert retry_config.backoff_factor == 1
    assert retry_config.status_forcelist == [429, 500, 502, 503, 504]
    assert retry_config.allowed_methods == {'HEAD', 'GET', 'OPTIONS', 'POST'}


@pytest.mark.parametrize(
    'args,expected',
    [
        (['help'], True),
        (['--help'], True),
        (['command', 'help'], True),
        (['command', '--help'], True),
        (['help', 'command'], True),
        (['command', 'arg', 'help'], True),
        (['command', 'arg'], False),
        ([], False),
        (['--region', 'us-east-1'], False),
        (['HeLp'], True),
        (['command', 'HELP'], True),
        ([10, 'Arg', 'HELP'], True),
        (['--Help'], True),
        (['command', '--Help'], True),
        (['--help', 'command'], True),
        (['--help', '--region', 'us-west-2'], True),
        (['command', 'help', '--debug'], True),
        (['command', '--region', 'us-east-1', 'help'], True),
        (['command', 'helping'], False),
        (['helping'], False),
        ([{}, {}], False),
        (['-h'], False),
        (['command', '-h'], False),
        ([{'MaxItems': 10}, ''], False),
        ([' ', '--help'], True),
        (['command', ' ', 'help'], True),
        (['--help', '--help'], True),
    ],
)
def test_is_help_operation(args, expected):
    """Test is_help_operation identifies help commands correctly."""
    assert is_help_operation(args) == expected


def test_as_json_basic_dict():
    """Test that as_json converts a basic dictionary to JSON string."""
    data = {'key': 'value', 'number': 42}
    result = as_json(data)
    assert result == '{"key": "value", "number": 42}'


def test_as_json_encodes_streaming_body_with_utf8_content():
    """Test that StreamingBody with valid UTF-8 content is decoded correctly."""
    content = b'Hello, world!'
    raw_stream = BytesIO(content)
    encoded = as_json({'data': StreamingBody(raw_stream, content_length=len(content))})
    assert json.loads(encoded) == {'data': 'Hello, world!'}


def test_as_json_encodes_streaming_body_with_non_utf8_content():
    """Test that StreamingBody with non-UTF-8 content is base64 encoded."""
    # 24 bytes of 0x80 (invalid UTF-8 continuation byte) - divisible by 3 for clean base64
    binary_data = b'\x80' * 24
    data = base64.b64encode(binary_data)
    raw_stream = BytesIO(binary_data)
    encoded = as_json({'data': StreamingBody(raw_stream, content_length=len(binary_data))})
    assert json.loads(encoded) == {'data': data.decode('utf-8')}


def test_as_json_encodes_bytes_with_utf8_content():
    """Test that bytes with valid UTF-8 content is decoded correctly."""
    content = b'Hello, world!'
    encoded = as_json({'data': content})
    assert json.loads(encoded) == {'data': 'Hello, world!'}


def test_as_json_encodes_bytes_with_non_utf8_content():
    """Test that bytes with non-UTF-8 content is base64 encoded."""
    # 24 bytes of 0x80 (invalid UTF-8 continuation byte) - divisible by 3 for clean base64
    binary_data = b'\x80' * 24
    data = base64.b64encode(binary_data)
    encoded = as_json({'data': binary_data})
    assert json.loads(encoded) == {'data': data.decode('utf-8')}


def test_as_json_raises_type_error_for_unsupported_type():
    """Test that as_json raises Exception for non-serializable objects."""

    class CustomObject:
        pass

    with pytest.raises(Exception) as exc_info:
        as_json({'data': CustomObject()})
    assert 'is not JSON serializable' in str(exc_info.value)
