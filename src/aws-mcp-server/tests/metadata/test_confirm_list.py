import json
import os
import pytest
import tempfile
from awslabs.aws_mcp_server.core.common.models import ActionType
from awslabs.aws_mcp_server.core.metadata.confirm_list import (
    ACTION_TYPE_TO_CONFIRM,
    CONFIRM_LIST_VERSION,
    ConfirmList,
    get_confirm_list,
    main,
)
from unittest.mock import MagicMock, mock_open, patch


@pytest.fixture
def sample_confirm_list_data():
    """Fixture providing sample confirm list data."""
    return {
        'metadata': {'version': CONFIRM_LIST_VERSION},
        'ec2': ['RunInstances', 'TerminateInstances', 'UnknownOpType'],
        's3': ['DeleteBucket', 'PutObject', 'UnknownPlaneType'],
    }


@pytest.fixture
def sample_api_metadata():
    """Fixture providing sample API metadata."""
    return {
        'ec2': {
            'RunInstances': {'type': 'Mutating', 'plane': 'ControlPlane'},
            'DescribeInstances': {'type': 'ReadOnly', 'plane': 'ControlPlane'},
            'TerminateInstances': {'type': 'Mutating', 'plane': 'ControlPlane'},
            'UnknownOpType': {'type': 'Unknown', 'plane': 'ControlPlane'},
        },
        's3': {
            'ListBuckets': {'type': 'ReadOnly', 'plane': 'ControlPlane'},
            'DeleteBucket': {'type': 'Mutating', 'plane': 'ControlPlane'},
            'PutObject': {'type': 'Mutating', 'plane': 'DataPlane'},
            'GetObject': {'type': 'ReadOnly', 'plane': 'DataPlane'},
            'UnknownPlaneType': {'type': 'ReadOnly', 'plane': 'Unknown'},
        },
    }


def test_confirm_list_initialization(sample_confirm_list_data):
    """Test ConfirmList initialization and version retrieval."""
    confirm_list = ConfirmList(sample_confirm_list_data)

    assert confirm_list.version == CONFIRM_LIST_VERSION
    assert isinstance(confirm_list, dict)
    assert 'ec2' in confirm_list
    assert 's3' in confirm_list


def test_confirm_list_has_method(sample_confirm_list_data):
    """Test the has method of ConfirmList."""
    confirm_list = ConfirmList(sample_confirm_list_data)

    # Test for existing service and operation
    assert confirm_list.has('ec2', 'RunInstances') is True
    assert confirm_list.has('s3', 'DeleteBucket') is True

    # Test for existing service but non-existing operation
    assert confirm_list.has('ec2', 'NonExistingOperation') is False

    # Test for non-existing service
    assert confirm_list.has('lambda', 'Invoke') is False


@patch('importlib_resources.files')
def test_get_confirm_list(mock_resource_stream, sample_confirm_list_data):
    """Test get_confirm_list function."""
    # Create a mock for the file object
    mock_file = mock_open(read_data=json.dumps(sample_confirm_list_data))

    # Create a mock for the joinpath result
    mock_joinpath = MagicMock()
    mock_joinpath.open.return_value = mock_file()

    # Set up the chain of mocks
    mock_resource_stream.return_value.joinpath.return_value = mock_joinpath

    result = get_confirm_list()

    assert isinstance(result, ConfirmList)
    assert result.version == CONFIRM_LIST_VERSION
    assert 'ec2' in result
    assert 'RunInstances' in result['ec2']


@patch('importlib_resources.files')
@patch('json.dump')
@patch('builtins.open', new_callable=mock_open)
def test_main_function(mock_file, mock_json_dump, mock_resource_stream, sample_api_metadata):
    """Test main function that generates confirm list."""
    # Create a mock for the file object
    mock_file = mock_open(read_data=json.dumps(sample_api_metadata))

    # Create a mock for the joinpath result
    mock_joinpath = MagicMock()
    mock_joinpath.open.return_value = mock_file()

    # Set up the chain of mocks
    mock_resource_stream.return_value.joinpath.return_value = mock_joinpath

    with tempfile.NamedTemporaryFile(delete=False) as temp_file:
        temp_path = temp_file.name

    try:
        # Run the main function with our temporary file
        main(temp_path)

        # Verify json.dump was called
        mock_json_dump.assert_called_once()

        # Extract the first argument of the call (the confirm_list dict)
        confirm_list_arg = mock_json_dump.call_args[0][0]

        # Verify the structure of the generated confirm list
        assert 'metadata' in confirm_list_arg
        assert confirm_list_arg['metadata']['version'] == CONFIRM_LIST_VERSION

        # Verify that mutating operations are in the confirm list
        assert 'ec2' in confirm_list_arg
        assert 'RunInstances' in confirm_list_arg['ec2']
        assert 'TerminateInstances' in confirm_list_arg['ec2']
        assert 'UnknownOpType' in confirm_list_arg['ec2']
        assert 'DescribeInstances' not in confirm_list_arg['ec2']

        assert 's3' in confirm_list_arg
        assert 'DeleteBucket' in confirm_list_arg['s3']
        assert 'PutObject' in confirm_list_arg['s3']
        assert 'ListBuckets' not in confirm_list_arg['s3']
        assert 'UnknownPlaneType' in confirm_list_arg['s3']
        assert 'GetObject' not in confirm_list_arg['s3']

    finally:
        # Clean up the temporary file
        if os.path.exists(temp_path):
            os.unlink(temp_path)


def test_action_type_to_confirm_constant():
    """Test that ACTION_TYPE_TO_CONFIRM contains expected values."""
    assert isinstance(ACTION_TYPE_TO_CONFIRM, frozenset)
    assert ActionType.MUTATING in ACTION_TYPE_TO_CONFIRM
    assert ActionType.UNKNOWN in ACTION_TYPE_TO_CONFIRM
    assert ActionType.READ_ONLY not in ACTION_TYPE_TO_CONFIRM
