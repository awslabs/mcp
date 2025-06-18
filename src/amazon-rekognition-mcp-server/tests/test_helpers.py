# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Tests for the Amazon Rekognition MCP Server helpers."""

import os
import pytest
from awslabs.amazon_rekognition_mcp_server.helpers import (
    get_aws_session,
    get_base_dir,
    get_image_bytes,
    get_rekognition_client,
    handle_exceptions,
    sanitize_path,
)
from pathlib import Path
from unittest.mock import MagicMock, patch


def test_get_aws_session_default():
    """Test get_aws_session with default settings."""
    with patch('boto3.Session') as mock_session:
        get_aws_session()
        mock_session.assert_called_once_with(region_name='us-east-1')


def test_get_aws_session_with_profile():
    """Test get_aws_session with AWS_PROFILE set."""
    with patch('boto3.Session') as mock_session:
        with patch.dict(os.environ, {'AWS_PROFILE': 'test-profile', 'AWS_REGION': 'us-west-2'}):
            get_aws_session()
            mock_session.assert_called_once_with(
                profile_name='test-profile', region_name='us-west-2'
            )


def test_get_rekognition_client():
    """Test get_rekognition_client."""
    mock_session = MagicMock()
    mock_client = MagicMock()
    mock_session.client.return_value = mock_client

    with patch(
        'awslabs.amazon_rekognition_mcp_server.helpers.get_aws_session', return_value=mock_session
    ):
        client = get_rekognition_client()
        mock_session.client.assert_called_once_with('rekognition')
        assert client == mock_client


@pytest.mark.asyncio
async def test_handle_exceptions_decorator():
    """Test handle_exceptions decorator."""

    @handle_exceptions
    async def test_func():
        return 'success'

    @handle_exceptions
    async def error_func():
        raise RuntimeError('Test error')

    # Test successful function
    result = await test_func()
    assert result == 'success'

    # Test function that raises an exception
    with pytest.raises(ValueError) as excinfo:
        await error_func()
    assert 'Error in error_func: Test error' in str(excinfo.value)


def test_get_base_dir():
    """Test get_base_dir function."""
    # Test with BASE_DIR not set
    with patch.dict(os.environ, {}, clear=True):
        assert get_base_dir() is None

    # Test with BASE_DIR set
    with patch.dict(os.environ, {'BASE_DIR': '/test/base/dir'}):
        assert get_base_dir() == '/test/base/dir'


def test_sanitize_path_no_base_dir():
    """Test sanitize_path without base_dir."""
    path = sanitize_path('test/path.txt')
    assert isinstance(path, Path)
    assert path.is_absolute()


def test_sanitize_path_with_base_dir(tmp_path):
    """Test sanitize_path with base_dir."""
    base_dir = tmp_path
    test_path = 'test/path.txt'

    path = sanitize_path(test_path, str(base_dir))
    assert isinstance(path, Path)
    assert path.is_absolute()
    assert str(path).startswith(str(base_dir))


def test_sanitize_path_traversal_attack(tmp_path):
    """Test sanitize_path prevents path traversal attacks."""
    base_dir = tmp_path
    traversal_path = '../../../etc/passwd'

    with pytest.raises(ValueError) as excinfo:
        sanitize_path(traversal_path, str(base_dir))
    assert 'attempts to traverse outside base directory' in str(excinfo.value)


def test_get_image_bytes_file_not_found():
    """Test get_image_bytes with a non-existent file."""
    with patch(
        'awslabs.amazon_rekognition_mcp_server.helpers.sanitize_path',
        return_value=Path('/non/existent/file.jpg'),
    ):
        with pytest.raises(ValueError) as excinfo:
            get_image_bytes('non_existent_file.jpg')
        assert 'Image file not found' in str(excinfo.value)


def test_get_image_bytes_with_mock_file(tmp_path):
    """Test get_image_bytes with a mock file."""
    # Create a temporary file
    test_file = tmp_path / 'test_image.jpg'
    test_content = b'test image content'
    test_file.write_bytes(test_content)

    # Mock sanitize_path to return our test file path
    with patch(
        'awslabs.amazon_rekognition_mcp_server.helpers.sanitize_path', return_value=test_file
    ):
        # Test get_image_bytes
        result = get_image_bytes(str(test_file))
        assert 'Bytes' in result
        assert result['Bytes'] == test_content


def test_get_image_bytes_with_base_dir(tmp_path):
    """Test get_image_bytes with BASE_DIR environment variable."""
    # Create a temporary file
    test_dir = tmp_path / 'images'
    test_dir.mkdir()
    test_file = test_dir / 'test_image.jpg'
    test_content = b'test image content'
    test_file.write_bytes(test_content)

    # Test with BASE_DIR set
    with patch.dict(os.environ, {'BASE_DIR': str(tmp_path)}):
        with patch(
            'awslabs.amazon_rekognition_mcp_server.helpers.sanitize_path', return_value=test_file
        ):
            result = get_image_bytes('images/test_image.jpg')
            assert 'Bytes' in result
            assert result['Bytes'] == test_content
