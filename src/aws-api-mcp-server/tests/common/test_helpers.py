import pytest
import requests
from awslabs.aws_api_mcp_server.core.common.helpers import (
    download_embedding_model,
    validate_aws_region,
)
from unittest.mock import MagicMock, mock_open, patch


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


@patch('awslabs.aws_api_mcp_server.core.common.helpers.EMBEDDING_MODEL_DIR', '/mock/models')
@patch('awslabs.aws_api_mcp_server.core.common.helpers.zipfile.ZipFile')
@patch('awslabs.aws_api_mcp_server.core.common.helpers.requests.get')
@patch('awslabs.aws_api_mcp_server.core.common.helpers.tempfile.TemporaryDirectory')
@patch('awslabs.aws_api_mcp_server.core.common.helpers.Path')
@patch('awslabs.aws_api_mcp_server.core.common.helpers.logger')
def test_download_embedding_model_success(
    mock_logger, mock_path, mock_temp_dir, mock_requests_get, mock_zipfile
):
    """Test successful download and extraction of embedding model."""
    mock_temp_dir_context = MagicMock()
    mock_temp_dir_context.__enter__.return_value = '/tmp/test_dir'
    mock_temp_dir_context.__exit__.return_value = None
    mock_temp_dir.return_value = mock_temp_dir_context

    mock_response = MagicMock()
    mock_response.iter_content.return_value = [b'chunk1', b'chunk2']
    mock_requests_get.return_value = mock_response

    mock_zip_ref = MagicMock()
    mock_zipfile.return_value.__enter__.return_value = mock_zip_ref

    mock_path_instance = MagicMock()
    mock_path.return_value = mock_path_instance
    mock_path_instance.parent.mkdir = MagicMock()

    with patch('builtins.open', mock_open()) as mock_file:
        with patch('os.path.join', side_effect=lambda *args: '/'.join(args)):
            download_embedding_model('test-model')

    mock_requests_get.assert_called_once_with(
        'https://models.knowledge-mcp.global.api.aws/test-model.zip', stream=True, timeout=30
    )
    mock_response.raise_for_status.assert_called_once()
    mock_file.assert_called_once_with('/tmp/test_dir/test-model.zip', 'wb')
    handle = mock_file()
    assert handle.write.call_count == 2
    handle.write.assert_any_call(b'chunk1')
    handle.write.assert_any_call(b'chunk2')
    mock_zip_ref.extractall.assert_called_once_with('/mock/models/test-model')
    mock_logger.debug.assert_any_call(
        'Dowloading embedding model {} to {}', 'test-model', '/tmp/test_dir'
    )


@patch('awslabs.aws_api_mcp_server.core.common.helpers.requests.get')
@patch('awslabs.aws_api_mcp_server.core.common.helpers.tempfile.TemporaryDirectory')
@patch('awslabs.aws_api_mcp_server.core.common.helpers.Path')
@patch('awslabs.aws_api_mcp_server.core.common.helpers.logger')
def test_download_embedding_model_http_error(
    mock_logger, mock_path, mock_temp_dir, mock_requests_get
):
    """Test download failure due to HTTP error."""
    mock_temp_dir_context = MagicMock()
    mock_temp_dir_context.__enter__.return_value = '/tmp/test_dir'
    mock_temp_dir_context.__exit__.return_value = None
    mock_temp_dir.return_value = mock_temp_dir_context

    mock_path_instance = MagicMock()
    mock_path.return_value = mock_path_instance
    mock_path_instance.parent.mkdir = MagicMock()

    mock_response = MagicMock()
    mock_response.raise_for_status.side_effect = requests.HTTPError('404 Not Found')
    mock_requests_get.return_value = mock_response

    with patch('os.path.join', side_effect=lambda *args: '/'.join(args)):
        with pytest.raises(requests.HTTPError):
            download_embedding_model('nonexistent-model')

    mock_requests_get.assert_called_once_with(
        'https://models.knowledge-mcp.global.api.aws/nonexistent-model.zip',
        stream=True,
        timeout=30,
    )
    mock_response.raise_for_status.assert_called_once()


@patch('awslabs.aws_api_mcp_server.core.common.helpers.EMBEDDING_MODEL_DIR', '/mock/models')
@patch('awslabs.aws_api_mcp_server.core.common.helpers.shutil.rmtree')
@patch('awslabs.aws_api_mcp_server.core.common.helpers.os.path.exists')
@patch('awslabs.aws_api_mcp_server.core.common.helpers.zipfile.ZipFile')
@patch('awslabs.aws_api_mcp_server.core.common.helpers.requests.get')
@patch('awslabs.aws_api_mcp_server.core.common.helpers.tempfile.TemporaryDirectory')
@patch('awslabs.aws_api_mcp_server.core.common.helpers.Path')
@patch('awslabs.aws_api_mcp_server.core.common.helpers.logger')
def test_download_embedding_model_zip_extraction_failure(
    mock_logger,
    mock_path,
    mock_temp_dir,
    mock_requests_get,
    mock_zipfile,
    mock_exists,
    mock_rmtree,
):
    """Test that directory is cleaned up when zip extraction fails."""
    mock_temp_dir_context = MagicMock()
    mock_temp_dir_context.__enter__.return_value = '/tmp/test_dir'
    mock_temp_dir_context.__exit__.return_value = None
    mock_temp_dir.return_value = mock_temp_dir_context

    mock_response = MagicMock()
    mock_response.iter_content.return_value = [b'chunk1', b'chunk2']
    mock_requests_get.return_value = mock_response

    mock_zip_ref = MagicMock()
    mock_zip_ref.extractall.side_effect = Exception('Zip extraction failed')
    mock_zipfile.return_value.__enter__.return_value = mock_zip_ref

    mock_path_instance = MagicMock()
    mock_path.return_value = mock_path_instance
    mock_path_instance.parent.mkdir = MagicMock()

    mock_exists.return_value = True

    with patch('builtins.open', mock_open()) as mock_file:
        with patch('os.path.join', side_effect=lambda *args: '/'.join(args)):
            with pytest.raises(Exception, match='Zip extraction failed'):
                download_embedding_model('test-model')

    mock_requests_get.assert_called_once_with(
        'https://models.knowledge-mcp.global.api.aws/test-model.zip', stream=True, timeout=30
    )
    mock_response.raise_for_status.assert_called_once()
    mock_file.assert_called_once_with('/tmp/test_dir/test-model.zip', 'wb')
    mock_zip_ref.extractall.assert_called_once_with('/mock/models/test-model')
    mock_logger.error.assert_called_once_with(
        'Failed to extract embedding model: {}', 'Zip extraction failed'
    )
    mock_exists.assert_called_once_with('/mock/models/test-model')
    mock_rmtree.assert_called_once_with('/mock/models/test-model')
