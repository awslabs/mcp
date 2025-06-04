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
"""Additional tests for the RepomixManager class to improve coverage."""

import os
import pytest
import tempfile
import xml.etree.ElementTree as ET  # Use standard ElementTree instead of defusedxml
from awslabs.code_doc_gen_mcp_server.utils.repomix_manager import RepomixManager
from unittest.mock import AsyncMock, MagicMock, patch


def test_extract_statistics():
    """Test extract_statistics method with valid XML."""
    # Arrange
    manager = RepomixManager()

    # Create a temporary XML file
    with tempfile.NamedTemporaryFile(suffix='.xml', delete=False) as tmp:
        tmp.write(b"""
<repository>
  <statistics>
    <total_files>42</total_files>
    <total_chars>12345</total_chars>
    <total_tokens>7890</total_tokens>
    <text_stat>Some text</text_stat>
  </statistics>
</repository>
""")
        tmp_path = tmp.name

    try:
        # Act
        result = manager.extract_statistics(tmp_path)

        # Assert
        assert result is not None
        assert result['total_files'] == 42
        assert result['total_chars'] == 12345
        assert result['total_tokens'] == 7890
        assert result['text_stat'] == 'Some text'
    finally:
        # Clean up
        os.unlink(tmp_path)


def test_extract_statistics_file_not_found():
    """Test extract_statistics handles file not found gracefully."""
    # Arrange
    manager = RepomixManager()

    # Act
    result = manager.extract_statistics('/path/to/nonexistent/file.xml')

    # Assert
    assert result == {}


def test_extract_statistics_invalid_xml():
    """Test extract_statistics handles invalid XML gracefully."""
    # Arrange
    manager = RepomixManager()

    # Create a temporary XML file
    with tempfile.NamedTemporaryFile(suffix='.xml', delete=False) as tmp:
        tmp.write(b'This is not valid XML content')
        tmp_path = tmp.name

    try:
        # Act
        result = manager.extract_statistics(tmp_path)

        # Assert
        assert result == {}
    finally:
        # Clean up
        os.unlink(tmp_path)


def test_extract_statistics_no_statistics():
    """Test extract_statistics handles XML without statistics element."""
    # Arrange
    manager = RepomixManager()

    # Create a temporary XML file
    with tempfile.NamedTemporaryFile(suffix='.xml', delete=False) as tmp:
        tmp.write(b"""
<repository>
  <other>Some other content</other>
</repository>
""")
        tmp_path = tmp.name

    try:
        # Act
        result = manager.extract_statistics(tmp_path)

        # Assert
        assert result == {}
    finally:
        # Clean up
        os.unlink(tmp_path)


def test_extract_directory_structure_nested_format():
    """Test extract_directory_structure handles newer nested XML format."""
    # Arrange
    manager = RepomixManager()

    # Create a temporary XML file with the nested repository_structure format
    with tempfile.NamedTemporaryFile(suffix='.xml', delete=False) as tmp:
        tmp.write(b"""
<repository>
  <repository_structure>
    <file name="package.json"></file>
    <file name="README.md"></file>
    <directory name="src">
      <file name="index.js"></file>
      <directory name="components">
        <file name="Button.js"></file>
        <file name="Card.js"></file>
      </directory>
    </directory>
  </repository_structure>
</repository>
""")
        tmp_path = tmp.name

    try:
        # Act
        result = manager.extract_directory_structure(tmp_path)

        # Assert
        assert result is not None
        assert 'package.json' in result
        assert 'README.md' in result
        assert 'src/' in result
        assert 'components/' in result
        assert 'Button.js' in result
    finally:
        # Clean up
        os.unlink(tmp_path)


def test_extract_directory_structure_invalid_xml():
    """Test extract_directory_structure handles invalid XML gracefully."""
    # Arrange
    manager = RepomixManager()

    # Create a temporary XML file
    with tempfile.NamedTemporaryFile(suffix='.xml', delete=False) as tmp:
        tmp.write(b'This is not valid XML content')
        tmp_path = tmp.name

    try:
        # Act
        result = manager.extract_directory_structure(tmp_path)

        # Assert
        assert result is None
    finally:
        # Clean up
        os.unlink(tmp_path)


@pytest.mark.asyncio
@patch('pathlib.Path.mkdir')
@patch('pathlib.Path.exists')
@patch('pathlib.Path.is_dir')
@patch('pathlib.Path.touch')
@patch('pathlib.Path.unlink')
async def test_prepare_repository_with_ctx_info(
    mock_unlink, mock_touch, mock_is_dir, mock_exists, mock_mkdir
):
    """Test prepare_repository with context info updates."""
    # Arrange
    manager = RepomixManager()

    # Mock file operations
    mock_exists.return_value = True
    mock_is_dir.return_value = True

    # Create a mock RepoProcessor class
    mock_processor = MagicMock()
    mock_result = MagicMock()
    # Set directory_structure to match what the test expects
    mock_result.directory_structure = 'directory structure from xml'
    mock_processor.process.return_value = mock_result

    # Mock the extract_statistics method to return stats
    mock_extract_stats = MagicMock()
    mock_extract_stats.return_value = {
        'total_files': 10,
        'total_chars': 1000,
        'total_tokens': 500,
    }

    # Mock the extract_directory_structure method
    mock_extract_dir = MagicMock()
    mock_extract_dir.return_value = 'directory structure from xml'

    with (
        patch.object(manager, 'extract_statistics', mock_extract_stats),
        patch.object(manager, 'extract_directory_structure', mock_extract_dir),
        patch('awslabs.code_doc_gen_mcp_server.utils.repomix_manager.RepomixConfig'),
        patch(
            'awslabs.code_doc_gen_mcp_server.utils.repomix_manager.RepoProcessor'
        ) as MockProcessor,
    ):
        MockProcessor.return_value = mock_processor

        # Act
        project_root = '/path/to/project'
        output_path = '/path/to/output'
        ctx = AsyncMock()

        result = await manager.prepare_repository(project_root, output_path, ctx)

        # Assert
        ctx.info.assert_called()  # Verify context info was called
        assert result['directory_structure'] == 'directory structure from xml'
        assert result['metadata']['summary'] == mock_extract_stats.return_value


@pytest.mark.asyncio
@patch('pathlib.Path.mkdir')
@patch('pathlib.Path.exists')
@patch('pathlib.Path.is_dir')
async def test_prepare_repository_output_dir_not_writable(mock_is_dir, mock_exists, mock_mkdir):
    """Test prepare_repository handles output directory not writable."""
    # Arrange
    manager = RepomixManager()

    # Mock file operations
    mock_exists.return_value = True
    mock_is_dir.return_value = True

    # Mock mkdir to raise an exception
    mock_mkdir.side_effect = PermissionError('Permission denied')

    # Act & Assert
    with pytest.raises(RuntimeError, match='Unexpected error during preparation'):
        await manager.prepare_repository('/path/to/project', '/path/to/output')


def test_convert_repository_structure():
    """Test _convert_repository_structure handles XML elements correctly."""
    # Arrange
    manager = RepomixManager()
    lines = []

    # Create a mock element tree
    root = ET.Element('repository_structure')

    # Add a file
    file1 = ET.SubElement(root, 'file')
    file1.set('name', 'README.md')

    # Add a directory with files
    dir1 = ET.SubElement(root, 'directory')
    dir1.set('name', 'src')

    file2 = ET.SubElement(dir1, 'file')
    file2.set('name', 'index.js')

    subdir = ET.SubElement(dir1, 'directory')
    subdir.set('name', 'components')

    file3 = ET.SubElement(subdir, 'file')
    file3.set('name', 'Button.js')

    # Act
    manager._convert_repository_structure(root, lines)

    # Assert
    assert len(lines) == 5
    assert lines[0] == 'README.md'
    assert lines[1] == 'src/'
    assert lines[2] == '  index.js'
    assert lines[3] == '  components/'
    assert lines[4] == '    Button.js'
