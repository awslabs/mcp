import pytest
from awslabs.aws_api_mcp_server.core.common.helpers import (
    get_requests_session,
    validate_aws_region,
)
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
