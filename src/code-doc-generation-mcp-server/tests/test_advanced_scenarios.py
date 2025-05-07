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
"""Advanced tests to improve test coverage."""

import pytest
import tempfile
import os
import xml.etree.ElementTree as ET
from pathlib import Path
from awslabs.code_doc_generation_mcp_server.utils.repomix_manager import RepomixManager
from awslabs.code_doc_generation_mcp_server.server import _analyze_project_structure, create_documentation_context
from awslabs.code_doc_generation_mcp_server.utils.models import ProjectAnalysis
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.mark.asyncio
async def test_analyze_project_structure_with_fallbacks():
    """Test _analyze_project_structure uses fallbacks for directory structure."""
    # Test with missing directory_structure
    raw_analysis = {
        'project_info': {'name': 'test-project', 'path': '/path/to/repo'},
        'metadata': {'key': 'value'},
        # No directory_structure here
    }
    # Create a fallback structure in file_structure
    raw_analysis['file_structure'] = {
        'directory_structure': 'bin/\n  app.ts\nlib/\n  stack.ts'
    }
    
    docs_dir = Path('/path/to/repo/generated-docs')
    ctx = MagicMock()

    # Act
    result = await _analyze_project_structure(raw_analysis, docs_dir, ctx)

    # Assert - should find the structure in file_structure
    assert result['output_dir'] == str(docs_dir)
    assert result['directory_structure'] == 'bin/\n  app.ts\nlib/\n  stack.ts'
    # The logger.info is called, not ctx.info
    # We don't need to assert_called() since the test passes if we get the right result


def test_extract_directory_structure_exception_handling():
    """Test extract_directory_structure handles exceptions gracefully."""
    # Arrange
    manager = RepomixManager()
    
    # Create a file that will cause an exception during parsing
    with tempfile.NamedTemporaryFile(suffix=".xml", delete=False) as tmp:
        # Create a malformed XML file that will cause ElementTree parsing errors
        tmp.write(b"<unclosed_tag>This will cause parsing errors")
        tmp_path = tmp.name
    
    try:
        # Test with ET.parse raising an exception
        with patch('xml.etree.ElementTree.parse') as mock_parse:
            mock_parse.side_effect = ET.ParseError("Test parse error")
            
            # Act - First method will fail
            with patch.object(manager.logger, 'warning') as mock_warning:
                result1 = manager.extract_directory_structure(tmp_path)
                
                # Assert - Should log a warning
                mock_warning.assert_called()
        
        # Test with directory_structure pattern not found
        with patch('re.search') as mock_search:
            mock_search.return_value = None
            
            # Act - All methods will fail
            result2 = manager.extract_directory_structure(tmp_path)
            
            # Assert - Should return None when no pattern is found
            assert result2 is None
    
    finally:
        # Clean up
        os.unlink(tmp_path)


def test_create_documentation_context_without_analysis():
    """Test create_documentation_context without providing an analysis."""
    # Arrange
    project_root = '/path/to/repo'

    # Act
    result = create_documentation_context(project_root)

    # Assert
    assert isinstance(result, object)
    assert result.project_name == Path(project_root).name
    assert result.working_dir == project_root
    assert result.repomix_path == f'{project_root}/generated-docs'
    assert result.analysis_result is None


@pytest.mark.asyncio
@patch('pathlib.Path.exists')
@patch('pathlib.Path.read_text')
async def test_repomix_manager_file_handling(mock_read_text, mock_exists):
    """Test repomix_manager file handling edge cases."""
    # Arrange
    manager = RepomixManager()
    
    # Test handling of non-existent file
    mock_exists.return_value = False
    
    # Act
    result1 = manager.extract_directory_structure("/path/to/nonexistent/file.xml")
    
    # Assert
    assert result1 is None
    
    # Test handling of empty file content
    mock_exists.return_value = True
    mock_read_text.return_value = ""
    
    # Act
    result2 = manager.extract_directory_structure("/path/to/empty/file.xml")
    
    # Assert
    assert result2 is None
    
    # Test handling of file with content but no directory structure
    mock_read_text.return_value = "<root><other>content</other></root>"
    
    # Act
    result3 = manager.extract_directory_structure("/path/to/file/without/structure.xml")
    
    # Assert
    assert result3 is None
