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
"""Tests for the statistics extraction functionality of RepomixManager."""

import os
import tempfile
import xml.etree.ElementTree as ET
from awslabs.code_doc_gen_mcp_server.utils.repomix_manager import RepomixManager
from unittest.mock import patch


def test_extract_statistics():
    """Test extract_statistics correctly extracts statistics from XML."""
    # Arrange
    manager = RepomixManager()

    # Create a temporary XML file
    with tempfile.NamedTemporaryFile(suffix='.xml', delete=False) as tmp:
        tmp.write(b"""
<repository>
  <statistics>
    <total_files>123</total_files>
    <total_chars>456789</total_chars>
    <total_tokens>78901</total_tokens>
    <generated_at>2025-05-07 12:00:00</generated_at>
  </statistics>
</repository>
""")
        tmp_path = tmp.name

    try:
        # Act
        result = manager.extract_statistics(tmp_path)

        # Assert
        assert result is not None
        assert result['total_files'] == 123
        assert result['total_chars'] == 456789
        assert result['total_tokens'] == 78901
        assert result['generated_at'] == '2025-05-07 12:00:00'
    finally:
        # Clean up
        os.unlink(tmp_path)


def test_extract_statistics_file_not_found():
    """Test extract_statistics handles file not found scenario."""
    # Arrange
    manager = RepomixManager()

    # Act
    result = manager.extract_statistics('/path/to/nonexistent/file.xml')

    # Assert
    assert result == {}


def test_extract_statistics_invalid_values():
    """Test extract_statistics handles invalid numeric values."""
    # Arrange
    manager = RepomixManager()

    # Create a temporary XML file with invalid numeric value
    with tempfile.NamedTemporaryFile(suffix='.xml', delete=False) as tmp:
        tmp.write(b"""
<repository>
  <statistics>
    <total_files>invalid</total_files>
    <total_chars>456789</total_chars>
    <total_tokens>78901</total_tokens>
  </statistics>
</repository>
""")
        tmp_path = tmp.name

    try:
        # Act
        result = manager.extract_statistics(tmp_path)

        # Assert - should handle the invalid value gracefully
        assert result['total_files'] == 'invalid'  # Falls back to string
        assert result['total_chars'] == 456789
        assert result['total_tokens'] == 78901
    finally:
        # Clean up
        os.unlink(tmp_path)


def test_extract_statistics_empty_xml():
    """Test extract_statistics handles empty XML files gracefully."""
    # Arrange
    manager = RepomixManager()

    # Create a temporary empty XML file
    with tempfile.NamedTemporaryFile(suffix='.xml', delete=False) as tmp:
        tmp.write(b'')
        tmp_path = tmp.name

    try:
        # Act
        result = manager.extract_statistics(tmp_path)

        # Assert
        assert result == {}
    finally:
        # Clean up
        os.unlink(tmp_path)


def test_extract_statistics_no_statistics_element():
    """Test extract_statistics handles XML without statistics element."""
    # Arrange
    manager = RepomixManager()

    # Create a temporary XML file without statistics element
    with tempfile.NamedTemporaryFile(suffix='.xml', delete=False) as tmp:
        tmp.write(b"""
<repository>
  <other_element>Some content</other_element>
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


def test_extract_statistics_parsing_error():
    """Test extract_statistics handles XML parsing errors."""
    # Arrange
    manager = RepomixManager()

    # Create a temporary invalid XML file
    with tempfile.NamedTemporaryFile(suffix='.xml', delete=False) as tmp:
        tmp.write(b'<invalid_xml>')
        tmp_path = tmp.name

    try:
        # Act
        with patch('xml.etree.ElementTree.parse', side_effect=ET.ParseError('Test parse error')):
            result = manager.extract_statistics(tmp_path)

        # Assert
        assert result == {}
    finally:
        # Clean up
        os.unlink(tmp_path)


def test_convert_repository_structure():
    """Test _convert_repository_structure correctly converts XML to text."""
    # Arrange
    manager = RepomixManager()

    # Create XML elements
    root = ET.Element('repository_structure')

    # Add a file
    file1 = ET.SubElement(root, 'file')
    file1.set('name', 'README.md')

    # Add a directory with nested files
    dir1 = ET.SubElement(root, 'directory')
    dir1.set('name', 'src')

    file2 = ET.SubElement(dir1, 'file')
    file2.set('name', 'index.js')

    dir2 = ET.SubElement(dir1, 'directory')
    dir2.set('name', 'components')

    file3 = ET.SubElement(dir2, 'file')
    file3.set('name', 'Button.jsx')

    # Act
    lines = []
    manager._convert_repository_structure(root, lines)
    result = '\n'.join(lines)

    # Assert
    expected = 'README.md\nsrc/\n  index.js\n  components/\n    Button.jsx'
    assert result == expected


def test_extract_directory_structure_additional_formats():
    """Test extract_directory_structure handles additional XML formats."""
    # Arrange
    manager = RepomixManager()

    # Create a temporary XML file with nested repository structure
    with tempfile.NamedTemporaryFile(suffix='.xml', delete=False) as tmp:
        tmp.write(b"""
<repository>
  <repository_structure>
    <file name="README.md"/>
    <directory name="src">
      <file name="index.js"/>
      <directory name="components">
        <file name="Button.jsx"/>
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
        assert 'README.md' in result
        assert 'src/' in result
        assert 'Button.jsx' in result
    finally:
        # Clean up
        os.unlink(tmp_path)
