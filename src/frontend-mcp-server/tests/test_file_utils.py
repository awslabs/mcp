# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance
# with the License. A copy of the License is located at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES
# OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions
# and limitations under the License.
"""Tests for file_utils module."""

from awslabs.frontend_mcp_server.utils.file_utils import load_markdown_file
from unittest.mock import mock_open, patch


@patch('pathlib.Path.exists')
@patch('builtins.open', new_callable=mock_open, read_data='Test markdown content')
def test_load_markdown_file_success(mock_file_open, mock_exists):
    """Test load_markdown_file returns content when file exists."""
    # Arrange
    mock_exists.return_value = True

    # Act
    result = load_markdown_file('test-file.md')

    # Assert
    assert mock_exists.called
    mock_file_open.assert_called_once()
    assert result == 'Test markdown content'


@patch('pathlib.Path.exists')
@patch('builtins.print')
def test_load_markdown_file_not_found(mock_print, mock_exists):
    """Test load_markdown_file returns empty string and prints warning when file not found."""
    # Arrange
    mock_exists.return_value = False

    # Act
    result = load_markdown_file('non-existent-file.md')

    # Assert
    assert mock_exists.called
    assert mock_print.called
    assert 'Warning: File not found:' in mock_print.call_args[0][0]
    assert result == ''
