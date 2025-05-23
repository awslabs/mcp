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
"""Tests for the perforce MCP Server."""

import pytest
import subprocess
from awslabs.perforce_mcp_server.server import (
    check_out,
    get_file,
    list_files,
)


@pytest.mark.asyncio
async def test_list_files(mocker):
    """Test the list_files function returns the expected response with mocked subprocess."""
    # Arrange
    test_path = '//depot/project/...'
    mock_result = mocker.Mock()
    mock_result.returncode = 0
    mock_result.stdout = '//depot/project/file1.txt#1 - add change 123\n//depot/project/file2.txt#1 - add change 123'
    mocker.patch('subprocess.run', return_value=mock_result)

    # Expected result based on the mock response
    expected_result = {
        'files': [
            '//depot/project/file1.txt#1 - add change 123',
            '//depot/project/file2.txt#1 - add change 123',
        ],
        'count': 2,
    }

    # Act
    result = await list_files(test_path)

    # Assert
    assert result == expected_result
    subprocess.run.assert_called_once_with(
        ['p4', 'files', test_path], capture_output=True, text=True, check=True
    )


@pytest.mark.asyncio
async def test_list_files_with_changelist(mocker):
    """Test the list_files function with changelist parameter."""
    # Arrange
    test_path = '//depot/project/...'
    test_changelist = '123'
    mock_result = mocker.Mock()
    mock_result.returncode = 0
    mock_result.stdout = '//depot/project/file1.txt#1 - add change 123'
    mocker.patch('subprocess.run', return_value=mock_result)

    # Expected result
    expected_result = {'files': ['//depot/project/file1.txt#1 - add change 123'], 'count': 1}

    # Act
    result = await list_files(test_path, test_changelist)

    # Assert
    assert result == expected_result
    subprocess.run.assert_called_once_with(
        ['p4', 'files', test_path, '@123'], capture_output=True, text=True, check=True
    )


@pytest.mark.asyncio
async def test_list_files_error(mocker):
    """Test the list_files function handles errors correctly."""
    # Arrange
    test_path = '//depot/project/...'
    mocker.patch('subprocess.run', side_effect=Exception('Command failed'))

    # Expected result
    expected_result = {'error': 'Command failed'}

    # Act
    result = await list_files(test_path)

    # Assert
    assert result == expected_result


@pytest.mark.asyncio
async def test_get_file(mocker):
    """Test the get_file function returns the expected response."""
    # Arrange
    test_file_path = '//depot/project/file.txt'
    mock_result = mocker.Mock()
    mock_result.returncode = 0
    mock_result.stdout = 'File content'
    mocker.patch('subprocess.run', return_value=mock_result)

    # Expected result
    expected_result = {'content': 'File content'}

    # Act
    result = await get_file(test_file_path)

    # Assert
    assert result == expected_result
    subprocess.run.assert_called_once_with(
        ['p4', 'print', '-q', test_file_path], capture_output=True, text=True
    )


@pytest.mark.asyncio
async def test_get_file_with_revision(mocker):
    """Test the get_file function with revision parameter."""
    # Arrange
    test_file_path = '//depot/project/file.txt'
    test_revision = '2'
    mock_result = mocker.Mock()
    mock_result.returncode = 0
    mock_result.stdout = 'File content version 2'
    mocker.patch('subprocess.run', return_value=mock_result)

    # Expected result
    expected_result = {'content': 'File content version 2'}

    # Act
    result = await get_file(test_file_path, test_revision)

    # Assert
    assert result == expected_result
    subprocess.run.assert_called_once_with(
        ['p4', 'print', '-q', f'{test_file_path}#{test_revision}'], capture_output=True, text=True
    )


@pytest.mark.asyncio
async def test_get_file_error(mocker):
    """Test the get_file function handles errors correctly."""
    # Arrange
    test_file_path = '//depot/project/file.txt'
    mock_result = mocker.Mock()
    mock_result.returncode = 1
    mock_result.stderr = 'File not found'
    mocker.patch('subprocess.run', return_value=mock_result)

    # Expected result
    expected_result = {'error': 'File not found'}

    # Act
    result = await get_file(test_file_path)

    # Assert
    assert result == expected_result


@pytest.mark.asyncio
async def test_check_out(mocker):
    """Test the check_out function returns the expected response."""
    # Arrange
    test_file_path = '//depot/project/file.txt'
    mock_result = mocker.Mock()
    mock_result.returncode = 0
    mock_result.stdout = '//depot/project/file.txt#1 - opened for edit'
    mocker.patch('subprocess.run', return_value=mock_result)

    # Expected result
    expected_result = {
        'message': f'Successfully checked out {test_file_path}',
        'output': '//depot/project/file.txt#1 - opened for edit',
    }

    # Act
    result = await check_out(test_file_path)

    # Assert
    assert result == expected_result
    subprocess.run.assert_called_once_with(
        ['p4', 'edit', test_file_path], capture_output=True, text=True
    )


@pytest.mark.asyncio
async def test_check_out_with_changelist(mocker):
    """Test the check_out function with changelist parameter."""
    # Arrange
    test_file_path = '//depot/project/file.txt'
    test_changelist = '123'
    mock_result = mocker.Mock()
    mock_result.returncode = 0
    mock_result.stdout = '//depot/project/file.txt#1 - opened for edit'
    mocker.patch('subprocess.run', return_value=mock_result)

    # Expected result
    expected_result = {
        'message': f'Successfully checked out {test_file_path}',
        'output': '//depot/project/file.txt#1 - opened for edit',
    }

    # Act
    result = await check_out(test_file_path, test_changelist)

    # Assert
    assert result == expected_result
    subprocess.run.assert_called_once_with(
        ['p4', 'edit', '-c', test_changelist, test_file_path], capture_output=True, text=True
    )


@pytest.mark.asyncio
async def test_check_out_error(mocker):
    """Test the check_out function handles errors correctly."""
    # Arrange
    test_file_path = '//depot/project/file.txt'
    mock_result = mocker.Mock()
    mock_result.returncode = 1
    mock_result.stderr = 'File not in client view'
    mocker.patch('subprocess.run', return_value=mock_result)

    # Expected result
    expected_result = {'error': 'File not in client view'}

    # Act
    result = await check_out(test_file_path)

    # Assert
    assert result == expected_result
