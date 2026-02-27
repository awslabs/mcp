import pytest
from awslabs.aws_api_mcp_server.core.aws.regions import get_active_regions
from awslabs.aws_api_mcp_server.core.common.errors import AwsRegionResolutionError
from botocore.exceptions import ClientError
from unittest.mock import Mock, patch


@patch('awslabs.aws_api_mcp_server.core.aws.regions.boto3.Session')
def test_get_active_regions_with_profile(mock_session):
    """Test get_active_regions with a specific profile."""
    mock_client = Mock()
    mock_paginator = Mock()
    mock_session.return_value.client.return_value = mock_client
    mock_client.get_paginator.return_value = mock_paginator

    mock_paginator.paginate.return_value = [
        {
            'Regions': [
                {'RegionName': 'us-east-1', 'RegionOptStatus': 'ENABLED_BY_DEFAULT'},
                {'RegionName': 'us-west-2', 'RegionOptStatus': 'ENABLED'},
                {'RegionName': 'ap-south-1', 'RegionOptStatus': 'DISABLED'},
            ]
        }
    ]

    result = get_active_regions('test-profile')

    assert result == ['us-east-1', 'us-west-2']
    mock_session.assert_called_once_with(profile_name='test-profile')
    mock_client.get_paginator.assert_called_once_with('list_regions')


@patch('awslabs.aws_api_mcp_server.core.aws.regions.boto3.Session')
def test_get_active_regions_without_profile(mock_session):
    """Test get_active_regions without profile (uses default)."""
    mock_client = Mock()
    mock_paginator = Mock()
    mock_session.return_value.client.return_value = mock_client
    mock_client.get_paginator.return_value = mock_paginator

    mock_paginator.paginate.return_value = [
        {
            'Regions': [
                {'RegionName': 'us-east-1', 'RegionOptStatus': 'ENABLED_BY_DEFAULT'},
            ]
        }
    ]

    result = get_active_regions()

    assert result == ['us-east-1']
    mock_session.assert_called_once_with(profile_name=None)


@patch('awslabs.aws_api_mcp_server.core.aws.regions.boto3.Session')
def test_get_active_regions_multiple_pages(mock_session):
    """Test get_active_regions with multiple pages."""
    mock_client = Mock()
    mock_paginator = Mock()
    mock_session.return_value.client.return_value = mock_client
    mock_client.get_paginator.return_value = mock_paginator

    mock_paginator.paginate.return_value = [
        {
            'Regions': [
                {'RegionName': 'us-east-1', 'RegionOptStatus': 'ENABLED_BY_DEFAULT'},
            ]
        },
        {
            'Regions': [
                {'RegionName': 'us-west-2', 'RegionOptStatus': 'ENABLED'},
                {'RegionName': 'eu-west-1', 'RegionOptStatus': 'DISABLED'},
            ]
        },
    ]

    result = get_active_regions()

    assert result == ['us-east-1', 'us-west-2']


@patch('awslabs.aws_api_mcp_server.core.aws.regions.boto3.Session')
def test_get_active_regions_empty_response(mock_session):
    """Test get_active_regions with empty response."""
    mock_client = Mock()
    mock_paginator = Mock()
    mock_session.return_value.client.return_value = mock_client
    mock_client.get_paginator.return_value = mock_paginator

    mock_paginator.paginate.return_value = [{'Regions': []}]

    result = get_active_regions()

    assert result == []


@patch('awslabs.aws_api_mcp_server.core.aws.regions.boto3.Session')
def test_get_active_regions_access_denied_error(mock_session):
    """Test get_active_regions raises AwsRegionResolutionError for AccessDenied."""
    mock_client = Mock()
    mock_session.return_value.client.return_value = mock_client

    error_response = {'Error': {'Code': 'AccessDenied', 'Message': 'Access denied'}}
    mock_client.get_paginator.return_value.paginate.side_effect = ClientError(
        error_response, 'ListRegions'
    )

    with pytest.raises(AwsRegionResolutionError) as exc_info:
        get_active_regions('test-profile')

    assert 'lacks the "account:ListRegions" permission' in str(exc_info.value)
    assert exc_info.value.profile_name == 'test-profile'


@patch('awslabs.aws_api_mcp_server.core.aws.regions.boto3.Session')
def test_get_active_regions_other_client_error(mock_session):
    """Test get_active_regions raises AwsRegionResolutionError for other ClientError."""
    mock_client = Mock()
    mock_session.return_value.client.return_value = mock_client

    error_response = {'Error': {'Code': 'ThrottlingException', 'Message': 'Rate exceeded'}}
    mock_client.get_paginator.return_value.paginate.side_effect = ClientError(
        error_response, 'ListRegions'
    )

    with pytest.raises(AwsRegionResolutionError) as exc_info:
        get_active_regions()

    assert 'Unexpected AWS API error while listing regions' in str(exc_info.value)
    assert exc_info.value.profile_name is None


@patch('awslabs.aws_api_mcp_server.core.aws.regions.boto3.Session')
def test_get_active_regions_unexpected_error(mock_session):
    """Test get_active_regions raises AwsRegionResolutionError for unexpected errors."""
    mock_client = Mock()
    mock_session.return_value.client.return_value = mock_client
    mock_client.get_paginator.return_value.paginate.side_effect = Exception('Network error')

    with pytest.raises(AwsRegionResolutionError) as exc_info:
        get_active_regions('test-profile')

    assert 'Unexpected error while retrieving active AWS regions' in str(exc_info.value)
    assert exc_info.value.profile_name == 'test-profile'
