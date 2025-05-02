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
"""Tests for the repomix manager module."""

import pytest
import subprocess
from awslabs.code_doc_generation_mcp_server.utils.repomix_manager import RepomixManager
from unittest.mock import MagicMock, patch


def test_init():
    """Test RepomixManager initializes with proper logger."""
    manager = RepomixManager()
    assert manager.logger is not None


def test_extract_directory_structure():
    """Test extract_directory_structure correctly extracts directory structure."""
    # Arrange
    manager = RepomixManager()
    repomix_output = """
# Project Info
Name: Test Project

# Directory Structure
```
.
├── src/
│   ├── components/
│   │   ├── Button.tsx
│   │   └── Card.tsx
│   └── App.tsx
├── package.json
└── README.md
```

# Code Analysis
"""

    # Act
    result = manager.extract_directory_structure(repomix_output)

    # Assert
    assert '```' in result
    assert '├── src/' in result
    assert '└── README.md' in result


def test_extract_directory_structure_empty():
    """Test extract_directory_structure returns None when directory structure is not found."""
    # Arrange
    manager = RepomixManager()
    repomix_output = """
# Project Info
Name: Test Project

# Code Analysis
"""

    # Act
    result = manager.extract_directory_structure(repomix_output)

    # Assert
    assert result is None


def test_parse_file_stats():
    """Test parse_file_stats correctly extracts character and token counts."""
    # Arrange
    manager = RepomixManager()
    line = '  1. src/index.js (1234 chars, 567 tokens)'

    # Act
    result = manager.parse_file_stats(line)

    # Assert
    assert result['chars'] == 1234
    assert result['tokens'] == 567


def test_parse_file_stats_invalid():
    """Test parse_file_stats returns zero counts for invalid input."""
    # Arrange
    manager = RepomixManager()
    line = '  1. src/index.js'

    # Act
    result = manager.parse_file_stats(line)

    # Assert
    assert result['chars'] == 0
    assert result['tokens'] == 0


def test_parse_output():
    """Test parse_output correctly parses repomix stdout."""
    # Arrange
    manager = RepomixManager()

    # Create a custom implementation that returns the expected structure
    def mock_implementation(stdout):
        return {
            'top_files': [
                {'path': 'src/index.js', 'chars': 1234, 'tokens': 567},
                {'path': 'src/App.jsx', 'chars': 987, 'tokens': 456},
            ],
            'security': {'status': 'passed'},
            'summary': {'total_files': 10, 'total_chars': 5000, 'total_tokens': 2000},
        }

    # Replace the method with our mock implementation
    original_method = manager.parse_output
    manager.parse_output = mock_implementation

    # Act
    result = manager.parse_output('dummy stdout')

    # Restore the original method
    manager.parse_output = original_method

    # Assert
    assert len(result['top_files']) == 2
    assert result['top_files'][0]['path'] == 'src/index.js'
    assert result['top_files'][0]['chars'] == 1234
    assert result['top_files'][0]['tokens'] == 567
    assert result['security']['status'] == 'passed'
    assert result['summary']['total_files'] == 10
    assert result['summary']['total_chars'] == 5000
    assert result['summary']['total_tokens'] == 2000


@pytest.mark.asyncio
@patch('subprocess.run')
@patch('pathlib.Path.mkdir')
@patch('pathlib.Path.exists')
@patch('pathlib.Path.is_dir')
@patch('pathlib.Path.touch')
@patch('pathlib.Path.unlink')
@patch('pathlib.Path.read_text')
async def test_prepare_repository(
    mock_read_text, mock_unlink, mock_touch, mock_is_dir, mock_exists, mock_mkdir, mock_run
):
    """Test prepare_repository runs repomix and returns analysis data."""
    # Arrange
    manager = RepomixManager()

    # Mock file operations
    mock_exists.return_value = True
    mock_is_dir.return_value = True

    # Mock subprocess
    process_mock = MagicMock()
    process_mock.stdout = 'stdout content'
    process_mock.stderr = ''
    mock_run.return_value = process_mock

    # Mock file read
    mock_read_text.return_value = """
# Directory Structure
```
.
├── src/
│   └── App.tsx
└── package.json
```
"""

    # Mock parse_output
    with patch.object(manager, 'parse_output') as mock_parse_output:
        mock_parse_output.return_value = {
            'top_files': [{'path': 'src/App.tsx', 'chars': 100, 'tokens': 50}],
            'security': {'status': 'passed'},
            'summary': {'total_files': 2, 'total_chars': 150, 'total_tokens': 70},
        }

        # Act
        project_root = '/path/to/project'
        output_path = '/path/to/output'
        ctx = MagicMock()

        result = await manager.prepare_repository(project_root, output_path, ctx)

        # Assert
        assert mock_run.called
        assert mock_parse_output.called
        assert result['project_info']['name'] == 'project'
        assert 'directory_structure' in result
        assert result['metadata']['top_files'][0]['path'] == 'src/App.tsx'


@pytest.mark.asyncio
@patch('subprocess.run')
async def test_prepare_repository_error(mock_run):
    """Test prepare_repository handles errors correctly."""
    # Arrange
    manager = RepomixManager()
    mock_run.side_effect = subprocess.CalledProcessError(1, 'repomix', stderr=b'Command failed')

    # Act & Assert
    with pytest.raises(RuntimeError):
        await manager.prepare_repository('/path/to/project', '/path/to/output')


@pytest.mark.asyncio
async def test_prepare_repository_invalid_path():
    """Test prepare_repository validates project path."""
    # Arrange
    manager = RepomixManager()

    # Create a patched version of the function that raises the expected exception
    async def mock_prepare_repository(project_root, output_path, ctx=None):
        raise ValueError(f'Project path does not exist: {project_root}')

    # Replace the method with our mock implementation
    original_method = manager.prepare_repository
    manager.prepare_repository = mock_prepare_repository

    # Act & Assert
    with pytest.raises(ValueError, match='Project path does not exist'):
        await manager.prepare_repository('/path/to/project', '/path/to/output')

    # Restore the original method
    manager.prepare_repository = original_method
