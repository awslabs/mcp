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
"""Tests for the streamlined repomix manager module."""

import pytest
from awslabs.code_doc_generation_mcp_server.utils.repomix_manager import RepomixManager
from unittest.mock import AsyncMock, MagicMock, patch


def test_init():
    """Test RepomixManager initializes with proper logger."""
    manager = RepomixManager()
    assert manager.logger is not None


def test_extract_directory_structure_xml():
    """Test extract_directory_structure correctly extracts directory structure from XML."""
    # Arrange
    manager = RepomixManager()

    # Create a temporary XML file
    import tempfile

    with tempfile.NamedTemporaryFile(suffix='.xml', delete=False) as tmp:
        tmp.write(b"""
<repository>
  <directory_structure>
.
|-- src/
|   |-- components/
|   |   |-- Button.tsx
|   |   `-- Card.tsx
|   `-- App.tsx
|-- package.json
`-- README.md
  </directory_structure>
</repository>
""")
        tmp_path = tmp.name

    try:
        # Act
        result = manager.extract_directory_structure(tmp_path)

        # Assert
        assert result is not None
        assert 'src/' in result
        assert 'README.md' in result
    finally:
        # Clean up
        import os

        os.unlink(tmp_path)


def test_extract_directory_structure_file_not_found():
    """Test extract_directory_structure handles file not found scenario."""
    # Arrange
    manager = RepomixManager()

    # Act
    result = manager.extract_directory_structure('/path/to/nonexistent/file.xml')

    # Assert
    assert result is None


@pytest.mark.asyncio
@patch('pathlib.Path.mkdir')
@patch('pathlib.Path.exists')
@patch('pathlib.Path.is_dir')
@patch('pathlib.Path.touch')
@patch('pathlib.Path.unlink')
async def test_prepare_repository(mock_unlink, mock_touch, mock_is_dir, mock_exists, mock_mkdir):
    """Test prepare_repository using Python module approach."""
    # Arrange
    manager = RepomixManager()

    # Mock file operations
    mock_exists.return_value = True
    mock_is_dir.return_value = True

    # Create a mock RepoProcessor class
    mock_processor = MagicMock()
    mock_result = MagicMock()
    mock_result.total_files = 2
    mock_result.total_chars = 150
    mock_result.total_tokens = 70
    mock_result.directory_structure = """
.
├── src/
│   └── App.tsx
└── package.json
"""
    mock_processor.process.return_value = mock_result

    # Mock the extract_statistics method
    with patch.object(manager, 'extract_statistics') as mock_extract_stats:
        mock_extract_stats.return_value = {
            'total_files': 2,
            'total_chars': 150,
            'total_tokens': 70,
        }

        # Mock the RepomixConfig and RepoProcessor
        with patch(
            'awslabs.code_doc_generation_mcp_server.utils.repomix_manager.RepomixConfig'
        ) as _MockConfig:
            with patch(
                'awslabs.code_doc_generation_mcp_server.utils.repomix_manager.RepoProcessor'
            ) as MockProcessor:
                MockProcessor.return_value = mock_processor

                # Act
                project_root = '/path/to/project'
                output_path = '/path/to/output'
                ctx = AsyncMock()

                result = await manager.prepare_repository(project_root, output_path, ctx)

                # Assert
                assert MockProcessor.called
                assert mock_processor.process.called
                assert result['project_info']['name'] == 'project'
                assert result['directory_structure'] == mock_result.directory_structure
                assert result['metadata']['summary']['total_files'] == 2
                assert result['metadata']['summary']['total_chars'] == 150
                assert result['metadata']['summary']['total_tokens'] == 70


@pytest.mark.asyncio
@patch('awslabs.code_doc_generation_mcp_server.utils.repomix_manager.RepoProcessor')
async def test_prepare_repository_module_error(mock_processor):
    """Test prepare_repository handles module errors correctly."""
    # Arrange
    manager = RepomixManager()
    mock_processor_instance = MagicMock()
    mock_processor.return_value = mock_processor_instance
    mock_processor_instance.process.side_effect = Exception('Module error occurred')

    # Act & Assert
    with pytest.raises(RuntimeError):
        await manager.prepare_repository('/path/to/project', '/path/to/output')


@pytest.mark.asyncio
async def test_prepare_repository_invalid_path():
    """Test prepare_repository validates project path."""
    # Arrange
    manager = RepomixManager()

    # Act & Assert
    with patch('pathlib.Path.exists', return_value=False):
        with pytest.raises(
            RuntimeError, match='Unexpected error during preparation: Project path does not exist'
        ):
            await manager.prepare_repository('/path/to/project', '/path/to/output')
