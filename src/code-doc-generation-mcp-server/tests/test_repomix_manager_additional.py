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
"""Additional tests for the streamlined repomix manager module."""

import pytest
import tempfile
import os
import xml.etree.ElementTree as ET
from awslabs.code_doc_generation_mcp_server.utils.repomix_manager import RepomixManager
from unittest.mock import MagicMock, patch, PropertyMock


def test_logger_setup():
    """Test that the logger is properly set up in RepomixManager."""
    # Arrange
    with patch('awslabs.code_doc_generation_mcp_server.utils.repomix_manager.logger') as mock_logger:
        # Act
        manager = RepomixManager()

        # Assert
        assert manager.logger is mock_logger


def test_extract_directory_structure_empty_xml_file():
    """Test extract_directory_structure handles empty XML files gracefully."""
    # Arrange
    manager = RepomixManager()
    
    # Create a temporary empty XML file
    with tempfile.NamedTemporaryFile(suffix=".xml", delete=False) as tmp:
        tmp.write(b"")
        tmp_path = tmp.name
    
    try:
        # Act
        result = manager.extract_directory_structure(tmp_path)
        
        # Assert
        assert result is None
    finally:
        # Clean up
        os.unlink(tmp_path)


def test_extract_directory_structure_xml_parsing():
    """Test XML extraction with different directory_structure locations."""
    # Arrange
    manager = RepomixManager()
    
    # Test with valid XML with standard directory_structure path
    with tempfile.NamedTemporaryFile(suffix=".xml", delete=False) as tmp:
        tmp.write(b"""<?xml version="1.0" encoding="UTF-8"?>
<root>
  <directory_structure>Standard path structure</directory_structure>
</root>""")
        standard_path = tmp.name
        
    # Test with valid XML with nested directory_structure path
    with tempfile.NamedTemporaryFile(suffix=".xml", delete=False) as tmp:
        tmp.write(b"""<?xml version="1.0" encoding="UTF-8"?>
<repo>
  <data>
    <directory_structure>Nested path structure</directory_structure>
  </data>
</repo>""")
        nested_path = tmp.name
    
    try:
        # Act
        result1 = manager.extract_directory_structure(standard_path)
        result2 = manager.extract_directory_structure(nested_path)
            
        # Assert
        assert result1 == "Standard path structure"
        assert result2 == "Nested path structure"
    finally:
        # Clean up
        os.unlink(standard_path)
        os.unlink(nested_path)


def test_extract_directory_structure_xml_error_handling():
    """Test extract_directory_structure handles XML parsing errors."""
    # Arrange
    manager = RepomixManager()
    
    # Create a corrupted XML file
    with tempfile.NamedTemporaryFile(suffix=".xml", delete=False) as tmp:
        tmp.write(b"""<?xml version="1.0" encoding="UTF-8"?>
<root>
  <directory_structure>Broken XML file - missing closing tag
</root>""")
        corrupt_path = tmp.name
    
    try:
        # Mock ET.parse to raise an exception
        with patch.object(ET, 'parse', side_effect=Exception('XML parsing error')):
            # Act
            result = manager.extract_directory_structure(corrupt_path)
            
            # Assert
            assert result is None
    finally:
        # Clean up
        os.unlink(corrupt_path)


@pytest.mark.asyncio
@patch('pathlib.Path.exists')
@patch('pathlib.Path.is_dir')
@patch('pathlib.Path.mkdir')
@patch('pathlib.Path.touch')
@patch('pathlib.Path.unlink')
async def test_prepare_repository_output_dir_error(
    mock_unlink, mock_touch, mock_mkdir, mock_is_dir, mock_exists
):
    """Test prepare_repository handles output directory errors."""
    # Arrange
    manager = RepomixManager()

    # Set up the mocks
    mock_exists.return_value = True
    mock_is_dir.return_value = True

    # Make the mkdir operation raise an exception
    mock_mkdir.side_effect = OSError('Permission denied')

    ctx = MagicMock()

    # Act & Assert
    with pytest.raises(
        RuntimeError, match='Unexpected error during preparation: Output directory is not writable'
    ):
        await manager.prepare_repository('/path/to/project', '/path/to/output', ctx)


@pytest.mark.asyncio
@patch('pathlib.Path.exists')
@patch('pathlib.Path.is_dir')
@patch('pathlib.Path.mkdir')
@patch('pathlib.Path.touch')
@patch('pathlib.Path.unlink')
async def test_prepare_repository_fallback_extraction(
    mock_unlink, mock_touch, mock_mkdir, mock_is_dir, mock_exists
):
    """Test prepare_repository falls back to extract_directory_structure when needed."""
    # Arrange
    manager = RepomixManager()

    # Set up the mocks
    mock_exists.return_value = True
    mock_is_dir.return_value = True

    # Create mock processor
    mock_processor = MagicMock()
    mock_result = MagicMock()
    # Direct method fails (attribute error)
    type(mock_result).directory_structure = PropertyMock(side_effect=AttributeError("No such attribute"))
    mock_result.total_files = 10
    mock_result.total_chars = 1000
    mock_result.total_tokens = 500
    mock_processor.process.return_value = mock_result

    # Create a mock context
    ctx = MagicMock()

    # The fallback method succeeds
    with patch.object(manager, 'extract_directory_structure') as mock_extract:
        mock_extract.return_value = 'Extracted directory structure'
            
        # Mock the RepomixConfig and RepoProcessor
        with patch('awslabs.code_doc_generation_mcp_server.utils.repomix_manager.RepomixConfig'):
            with patch('awslabs.code_doc_generation_mcp_server.utils.repomix_manager.RepoProcessor') as MockProcessor:
                MockProcessor.return_value = mock_processor
                    
                # Act
                result = await manager.prepare_repository('/path/to/project', '/path/to/output', ctx)

                # Assert
                mock_extract.assert_called_once()
                assert result['directory_structure'] == 'Extracted directory structure'
                assert result['metadata']['summary']['total_files'] == 10


@pytest.mark.asyncio
@patch('pathlib.Path.exists', return_value=True)
@patch('pathlib.Path.is_dir', return_value=True)
@patch('pathlib.Path.mkdir')
@patch('pathlib.Path.touch')
@patch('pathlib.Path.unlink')
async def test_prepare_repository_missing_directory_structure(
    mock_unlink, mock_touch, mock_mkdir
):
    """Test prepare_repository handles missing directory structure."""
    # Arrange
    manager = RepomixManager()
    ctx = MagicMock()

    # Create mock processor
    mock_processor = MagicMock()
    mock_result = MagicMock()
    # Neither direct nor fallback methods succeed
    type(mock_result).directory_structure = PropertyMock(return_value=None)
    mock_processor.process.return_value = mock_result

    # Mock the extract_directory_structure method to return None
    with patch.object(manager, 'extract_directory_structure', return_value=None):
        # Mock the RepomixConfig and RepoProcessor
        with patch('awslabs.code_doc_generation_mcp_server.utils.repomix_manager.RepomixConfig'):
            with patch('awslabs.code_doc_generation_mcp_server.utils.repomix_manager.RepoProcessor', return_value=mock_processor):
                # Act
                result = await manager.prepare_repository('/path/to/project', '/path/to/output', ctx)

                # Assert
                ctx.warning.assert_called_once()
                assert result['directory_structure'] is None


@pytest.mark.asyncio
@patch('pathlib.Path.exists')
@patch('pathlib.Path.is_dir')
async def test_prepare_repository_not_directory(mock_is_dir, mock_exists):
    """Test prepare_repository raises error when project path is not a directory."""
    # Arrange
    manager = RepomixManager()

    # Set up the mocks
    mock_exists.return_value = True
    mock_is_dir.return_value = False

    # Act & Assert
    with pytest.raises(
        RuntimeError, match='Unexpected error during preparation: Project path is not a directory'
    ):
        await manager.prepare_repository('/path/to/file.txt', '/path/to/output')


def test_extract_directory_structure_multiple_xpath():
    """Test extract_directory_structure tries different xpath patterns."""
    # Arrange
    manager = RepomixManager()
    
    # Create an XML file with directory_structure at a specific xpath
    with tempfile.NamedTemporaryFile(suffix=".xml", delete=False) as tmp:
        tmp.write(b"""<?xml version="1.0" encoding="UTF-8"?>
<repository>
  <data>
    <directory_structure>Found with alternative xpath</directory_structure>
  </data>
</repository>""")
        xml_path = tmp.name
    
    try:
        # Mock find to return None for first xpath, then actual result for second
        original_find = ET.Element.find
        
        def mock_find(self, path):
            if path == './/directory_structure':
                return None
            elif path == 'directory_structure':
                element = ET.Element('directory_structure')
                element.text = 'Found with alternative xpath'
                return element
            return original_find(self, path)
            
        with patch('xml.etree.ElementTree.Element.find', mock_find):
            # Act
            result = manager.extract_directory_structure(xml_path)
            
            # Assert
            assert result == 'Found with alternative xpath'
    finally:
        # Clean up
        os.unlink(xml_path)
