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
"""Tests for Git Repository Research MCP Server utility functions."""

import json
import pytest
from awslabs.git_repo_research_mcp_server.models import (
    Constants,
    IndexMetadata,
)
from awslabs.git_repo_research_mcp_server.utils import (
    delete_indexed_repository,
    format_size,
    get_default_index_dir,
    list_indexed_repositories,
    load_metadata,
)
from datetime import datetime
from unittest.mock import MagicMock, mock_open, patch


def test_get_default_index_dir():
    """Test getting the default index directory."""
    with patch('os.path.expanduser') as mock_expanduser, patch('os.makedirs') as mock_makedirs:
        # Configure the mock
        mock_expanduser.return_value = '/home/user/.git_repo_research'

        # Call the function
        result = get_default_index_dir()

        # Verify the result
        assert result == '/home/user/.git_repo_research'

        # Verify the mocks were called correctly
        mock_expanduser.assert_called_once_with(f'~/{Constants.DEFAULT_INDEX_DIR}')
        mock_makedirs.assert_called_once_with('/home/user/.git_repo_research', exist_ok=True)


def test_load_metadata_file_not_exists():
    """Test loading metadata when the file doesn't exist."""
    with patch('os.path.exists') as mock_exists:
        # Configure the mock
        mock_exists.return_value = False

        # Call the function
        result = load_metadata('/path/to/metadata.json')

        # Verify the result
        assert result is None

        # Verify the mock was called correctly
        mock_exists.assert_called_once_with('/path/to/metadata.json')


def test_load_metadata_valid_file():
    """Test loading metadata from a valid file."""
    metadata_dict = {
        'repository_name': 'test-repo',
        'repository_path': '/path/to/repo',
        'index_path': '/path/to/index',
        'created_at': '2023-01-01T00:00:00Z',
        'last_accessed': '2023-01-02T00:00:00Z',
        'file_count': 10,
        'embedding_model': 'amazon.titan-embed-text-v2:0',
        'chunk_count': 20,
        'file_types': {'py': 5, 'md': 5},
        'total_tokens': 1000,
        'index_size_bytes': 5000,
        'last_commit_id': 'abc123',
    }

    with (
        patch('os.path.exists') as mock_exists,
        patch('builtins.open', mock_open(read_data=json.dumps(metadata_dict))),
    ):
        # Configure the mock
        mock_exists.return_value = True

        # Call the function
        result = load_metadata('/path/to/metadata.json')

        # Verify the result
        assert result is not None
        assert isinstance(result, IndexMetadata)
        assert result.repository_name == 'test-repo'
        assert result.repository_path == '/path/to/repo'
        assert result.index_path == '/path/to/index'
        assert result.file_count == 10
        assert result.embedding_model == 'amazon.titan-embed-text-v2:0'
        assert result.chunk_count == 20
        assert result.file_types == {'py': 5, 'md': 5}
        assert result.total_tokens == 1000
        assert result.index_size_bytes == 5000
        assert result.last_commit_id == 'abc123'


def test_load_metadata_invalid_file():
    """Test loading metadata from an invalid file."""
    with (
        patch('os.path.exists') as mock_exists,
        patch('builtins.open', mock_open(read_data='invalid json')),
        patch('loguru.logger.error') as mock_logger_error,
    ):
        # Configure the mock
        mock_exists.return_value = True

        # Call the function
        result = load_metadata('/path/to/metadata.json')

        # Verify the result
        assert result is None

        # Verify the logger was called
        mock_logger_error.assert_called_once()
        assert (
            'Error loading metadata from /path/to/metadata.json'
            in mock_logger_error.call_args[0][0]
        )


def test_list_indexed_repositories_empty_dir():
    """Test listing indexed repositories when the directory is empty."""
    with (
        patch(
            'awslabs.git_repo_research_mcp_server.utils.get_default_index_dir'
        ) as mock_get_default_index_dir,
        patch('os.path.exists') as mock_exists,
    ):
        # Configure the mocks
        mock_get_default_index_dir.return_value = '/home/user/.git_repo_research'
        mock_exists.return_value = False

        # Call the function
        result = list_indexed_repositories()

        # Verify the result
        assert result.repositories == []
        assert result.total_count == 0
        assert result.index_directory == '/home/user/.git_repo_research'


def test_list_indexed_repositories_with_repositories():
    """Test listing indexed repositories when there are repositories."""
    with (
        patch(
            'awslabs.git_repo_research_mcp_server.utils.get_default_index_dir'
        ) as mock_get_default_index_dir,
        patch('os.path.exists') as mock_exists,
        patch('os.listdir') as mock_listdir,
        patch('os.path.isdir') as mock_isdir,
        patch('awslabs.git_repo_research_mcp_server.utils.load_metadata') as mock_load_metadata,
    ):
        # Configure the mocks
        mock_get_default_index_dir.return_value = '/home/user/.git_repo_research'
        mock_exists.return_value = True
        mock_listdir.return_value = ['repo1', 'repo2', 'not_a_repo']

        # Configure isdir to return True for repo1 and repo2, False for not_a_repo
        def mock_isdir_side_effect(path):
            return 'not_a_repo' not in path

        mock_isdir.side_effect = mock_isdir_side_effect

        # Configure load_metadata to return metadata for repo1 and repo2
        metadata1 = IndexMetadata(
            repository_name='repo1',
            repository_path='/path/to/repo1',
            index_path='/home/user/.git_repo_research/repo1',
            created_at=datetime.now(),
            last_accessed=datetime.now(),
            file_count=10,
            embedding_model='amazon.titan-embed-text-v2:0',
            chunk_count=20,
            file_types={'py': 5, 'md': 5},
            total_tokens=1000,
            index_size_bytes=5000,
            last_commit_id='abc123',
            repository_directory='/path/to/repo1/repository',
        )
        metadata2 = IndexMetadata(
            repository_name='repo2',
            repository_path='/path/to/repo2',
            index_path='/home/user/.git_repo_research/repo2',
            created_at=datetime.now(),
            last_accessed=datetime.now(),
            file_count=5,
            embedding_model='amazon.titan-embed-text-v2:0',
            chunk_count=10,
            file_types={'py': 3, 'md': 2},
            total_tokens=500,
            index_size_bytes=2500,
            last_commit_id='def456',
            repository_directory='/path/to/repo1/repository',
        )

        def mock_load_metadata_side_effect(path):
            if 'repo1' in path:
                return metadata1
            elif 'repo2' in path:
                return metadata2
            return None

        mock_load_metadata.side_effect = mock_load_metadata_side_effect

        # Call the function
        result = list_indexed_repositories()

        # Verify the result
        assert len(result.repositories) == 2
        assert result.total_count == 2
        assert result.index_directory == '/home/user/.git_repo_research'

        # Verify the repositories
        assert result.repositories[0].repository_name == 'repo1'
        assert result.repositories[0].repository_path == '/path/to/repo1'
        assert result.repositories[0].index_path == '/home/user/.git_repo_research/repo1'
        assert result.repositories[0].file_count == 10

        assert result.repositories[1].repository_name == 'repo2'
        assert result.repositories[1].repository_path == '/path/to/repo2'
        assert result.repositories[1].index_path == '/home/user/.git_repo_research/repo2'
        assert result.repositories[1].file_count == 5


def test_list_indexed_repositories_with_missing_metadata():
    """Test listing indexed repositories when metadata is missing or invalid."""
    with (
        patch(
            'awslabs.git_repo_research_mcp_server.utils.get_default_index_dir'
        ) as mock_get_default_index_dir,
        patch('os.path.exists') as mock_exists,
        patch('os.listdir') as mock_listdir,
        patch('os.path.isdir') as mock_isdir,
        patch('awslabs.git_repo_research_mcp_server.utils.load_metadata') as mock_load_metadata,
    ):
        # Configure the mocks
        mock_get_default_index_dir.return_value = '/home/user/.git_repo_research'
        mock_exists.return_value = True
        mock_listdir.return_value = ['repo1', 'repo2', 'repo3']
        mock_isdir.return_value = True

        # Configure load_metadata to return None for repo1 (missing metadata)
        # and valid metadata for repo2
        metadata2 = IndexMetadata(
            repository_name='repo2',
            repository_path='/path/to/repo2',
            index_path='/home/user/.git_repo_research/repo2',
            created_at=datetime.now(),
            last_accessed=datetime.now(),
            file_count=5,
            embedding_model='amazon.titan-embed-text-v2:0',
            chunk_count=10,
            file_types={'py': 3, 'md': 2},
            total_tokens=500,
            index_size_bytes=2500,
            last_commit_id='def456',
            repository_directory='/path/to/repo1/repository',
        )

        def mock_load_metadata_side_effect(path):
            if 'repo1' in path:
                return None  # Missing or invalid metadata
            elif 'repo2' in path:
                return metadata2
            elif 'repo3' in path:
                # Simulate metadata.json not existing
                return None
            return None

        mock_load_metadata.side_effect = mock_load_metadata_side_effect

        # Call the function
        result = list_indexed_repositories()

        # Verify the result - should only include repo2
        assert len(result.repositories) == 1
        assert result.total_count == 1
        assert result.repositories[0].repository_name == 'repo2'


def test_list_indexed_repositories_detailed():
    """Test listing indexed repositories with detailed information."""
    with (
        patch(
            'awslabs.git_repo_research_mcp_server.utils.get_default_index_dir'
        ) as mock_get_default_index_dir,
        patch('os.path.exists') as mock_exists,
        patch('os.listdir') as mock_listdir,
        patch('os.path.isdir') as mock_isdir,
        patch('awslabs.git_repo_research_mcp_server.utils.load_metadata') as mock_load_metadata,
    ):
        # Configure the mocks
        mock_get_default_index_dir.return_value = '/home/user/.git_repo_research'
        mock_exists.return_value = True
        mock_listdir.return_value = ['repo1']
        mock_isdir.return_value = True

        # Configure load_metadata to return metadata
        metadata = IndexMetadata(
            repository_name='repo1',
            repository_path='/path/to/repo1',
            index_path='/home/user/.git_repo_research/repo1',
            created_at=datetime.now(),
            last_accessed=datetime.now(),
            file_count=10,
            embedding_model='amazon.titan-embed-text-v2:0',
            chunk_count=20,
            file_types={'py': 5, 'md': 5},
            total_tokens=1000,
            index_size_bytes=5000,
            last_commit_id='abc123',
            repository_directory='/path/to/repo1/repository',
        )
        mock_load_metadata.return_value = metadata

        # Call the function with detailed=True
        result = list_indexed_repositories(detailed=True)

        # Verify the result
        assert len(result.repositories) == 1
        assert result.total_count == 1
        assert result.index_directory == '/home/user/.git_repo_research'

        # Verify the repository details
        repo = result.repositories[0]
        assert repo.repository_name == 'repo1'
        assert repo.repository_path == '/path/to/repo1'
        assert repo.index_path == '/home/user/.git_repo_research/repo1'
        assert repo.file_count == 10
        assert repo.embedding_model == 'amazon.titan-embed-text-v2:0'


def test_format_size():
    """Test formatting sizes in bytes to human-readable strings."""
    # Test bytes
    assert format_size(500) == '500 B'

    # Test kilobytes
    assert format_size(1500) == '1.46 KB'

    # Test megabytes
    assert format_size(1500000) == '1.43 MB'

    # Test gigabytes
    assert format_size(1500000000) == '1.40 GB'


@pytest.mark.asyncio
async def test_delete_indexed_repository_not_found():
    """Test deleting a repository that doesn't exist."""
    with (
        patch(
            'awslabs.git_repo_research_mcp_server.utils.get_default_index_dir'
        ) as mock_get_default_index_dir,
        patch('os.path.exists') as mock_exists,
        patch('os.path.isabs') as mock_isabs,
        patch('os.listdir') as mock_listdir,
        patch('os.path.isdir') as mock_isdir,
        patch('awslabs.git_repo_research_mcp_server.utils.load_metadata') as mock_load_metadata,
    ):
        # Configure the mocks
        mock_get_default_index_dir.return_value = '/home/user/.git_repo_research'
        mock_exists.return_value = True
        mock_isabs.return_value = False

        # Configure exists to return False for the metadata file
        def mock_exists_side_effect(path):
            if 'metadata.json' in path:
                return False
            return True

        mock_exists.side_effect = mock_exists_side_effect

        # Configure listdir to return empty list (no repositories)
        mock_listdir.return_value = []
        mock_isdir.return_value = True

        # Configure load_metadata to return None
        mock_load_metadata.return_value = None

        # Call the function
        result = await delete_indexed_repository('test_repo')

        # Verify the result
        assert result['status'] == 'error'
        assert "Repository 'test_repo' not found in index directory" in result['message']


@pytest.mark.asyncio
async def test_delete_indexed_repository_success():
    """Test successfully deleting a repository."""
    with (
        patch(
            'awslabs.git_repo_research_mcp_server.utils.get_default_index_dir'
        ) as mock_get_default_index_dir,
        patch('os.path.exists') as mock_exists,
        patch('os.path.isabs') as mock_isabs,
        patch('os.path.isdir') as mock_isdir,
        patch('os.path.isfile') as mock_isfile,
        patch('os.path.splitext') as mock_splitext,
        patch('os.access') as mock_access,
        patch('os.remove') as mock_remove,
        patch('shutil.rmtree') as mock_rmtree,
        patch('awslabs.git_repo_research_mcp_server.utils.load_metadata') as mock_load_metadata,
        patch('loguru.logger.info') as mock_logger_info,
    ):
        # Configure the mocks
        mock_get_default_index_dir.return_value = '/home/user/.git_repo_research'
        mock_exists.return_value = True
        mock_isabs.return_value = False
        mock_isdir.return_value = True
        mock_isfile.return_value = False
        mock_splitext.return_value = ('/home/user/.git_repo_research/test_repo', '')
        mock_access.return_value = True

        # Configure load_metadata to return metadata
        metadata = MagicMock()
        metadata.repository_name = 'test_repo'
        mock_load_metadata.return_value = metadata

        # Call the function
        result = await delete_indexed_repository('test_repo')

        # Verify the result
        assert result['status'] == 'success'
        assert "Successfully deleted repository 'test_repo'" in result['message']
        assert result['repository_name'] == 'test_repo'
        assert len(result['deleted_files']) > 0

        # Verify the mocks were called correctly
        mock_remove.assert_called()  # Metadata file should be removed
        mock_rmtree.assert_called()  # Repository directory should be removed
        mock_logger_info.assert_called()  # Logging should occur


@pytest.mark.asyncio
async def test_delete_indexed_repository_permission_denied():
    """Test deleting a repository with permission issues."""
    with (
        patch(
            'awslabs.git_repo_research_mcp_server.utils.get_default_index_dir'
        ) as mock_get_default_index_dir,
        patch('os.path.exists') as mock_exists,
        patch('os.path.isabs') as mock_isabs,
        patch('os.path.isdir') as mock_isdir,
        patch('os.path.splitext') as mock_splitext,
        patch('os.access') as mock_access,
        patch('awslabs.git_repo_research_mcp_server.utils.load_metadata') as mock_load_metadata,
    ):
        # Configure the mocks
        mock_get_default_index_dir.return_value = '/home/user/.git_repo_research'
        mock_exists.return_value = True
        mock_isabs.return_value = False
        mock_isdir.return_value = True
        mock_splitext.return_value = ('/home/user/.git_repo_research/test_repo', '')
        mock_access.return_value = False  # No write access

        # Configure load_metadata to return metadata
        metadata = MagicMock()
        metadata.repository_name = 'test_repo'
        mock_load_metadata.return_value = metadata

        # Call the function
        result = await delete_indexed_repository('test_repo')

        # Verify the result
        assert result['status'] == 'error'
        assert 'Permission denied for the following files' in result['message']
        assert result['repository_name'] == 'test_repo'
        assert len(result['permission_issues']) > 0


@pytest.mark.asyncio
async def test_delete_indexed_repository_partial_success():
    """Test partially successful repository deletion."""
    with (
        patch(
            'awslabs.git_repo_research_mcp_server.utils.get_default_index_dir'
        ) as mock_get_default_index_dir,
        patch('os.path.exists') as mock_exists,
        patch('os.path.isabs') as mock_isabs,
        patch('os.path.isdir') as mock_isdir,
        patch('os.path.isfile') as mock_isfile,
        patch('os.path.splitext') as mock_splitext,
        patch('os.access') as mock_access,
        patch('os.remove') as mock_remove,
        patch('shutil.rmtree') as mock_rmtree,
        patch('awslabs.git_repo_research_mcp_server.utils.load_metadata') as mock_load_metadata,
        patch('loguru.logger.info') as mock_logger_info,
        patch('loguru.logger.error') as mock_logger_error,
    ):
        # Configure the mocks
        mock_get_default_index_dir.return_value = '/home/user/.git_repo_research'
        mock_exists.return_value = True
        mock_isabs.return_value = False
        mock_isdir.return_value = True
        mock_isfile.return_value = False
        mock_splitext.return_value = ('/home/user/.git_repo_research/test_repo', '')
        mock_access.return_value = True

        # Configure load_metadata to return metadata
        metadata = MagicMock()
        metadata.repository_name = 'test_repo'
        mock_load_metadata.return_value = metadata

        # Configure os.remove to succeed but shutil.rmtree to fail
        mock_remove.return_value = None
        mock_rmtree.side_effect = Exception('Permission denied')

        # Call the function
        result = await delete_indexed_repository('test_repo')

        # Verify the result
        assert result['status'] == 'partial'
        assert "Partially deleted repository 'test_repo'" in result['message']
        assert result['repository_name'] == 'test_repo'
        assert len(result['deleted_files']) > 0
        assert len(result['errors']) > 0

        # Verify the mocks were called correctly
        mock_remove.assert_called()  # Metadata file should be removed
        mock_rmtree.assert_called()  # Repository directory should be attempted to be removed
        mock_logger_info.assert_called()  # Logging should occur
        mock_logger_error.assert_called()  # Error logging should occur


@pytest.mark.asyncio
async def test_delete_indexed_repository_complete_failure():
    """Test completely failed repository deletion."""
    with (
        patch(
            'awslabs.git_repo_research_mcp_server.utils.get_default_index_dir'
        ) as mock_get_default_index_dir,
        patch('os.path.exists') as mock_exists,
        patch('os.path.isabs') as mock_isabs,
        patch('os.path.isdir') as mock_isdir,
        patch('os.path.isfile') as mock_isfile,
        patch('os.path.splitext') as mock_splitext,
        patch('os.access') as mock_access,
        patch('os.remove') as mock_remove,
        patch('awslabs.git_repo_research_mcp_server.utils.load_metadata') as mock_load_metadata,
        patch('loguru.logger.error') as mock_logger_error,
    ):
        # Configure the mocks
        mock_get_default_index_dir.return_value = '/home/user/.git_repo_research'
        mock_exists.return_value = True
        mock_isabs.return_value = False
        mock_isdir.return_value = True
        mock_isfile.return_value = False
        mock_splitext.return_value = ('/home/user/.git_repo_research/test_repo', '')
        mock_access.return_value = True

        # Configure load_metadata to return metadata
        metadata = MagicMock()
        metadata.repository_name = 'test_repo'
        mock_load_metadata.return_value = metadata

        # Configure os.remove to fail
        mock_remove.side_effect = Exception('Permission denied')

        # Call the function
        result = await delete_indexed_repository('test_repo')

        # Verify the result
        assert result['status'] == 'error'
        assert "Failed to delete repository 'test_repo'" in result['message']
        assert result['repository_name'] == 'test_repo'
        assert len(result['errors']) > 0

        # Verify the mocks were called correctly
        mock_remove.assert_called()  # Metadata file should be attempted to be removed
        mock_logger_error.assert_called()  # Error logging should occur


def test_list_indexed_repositories_with_repository_directory():
    """Test listing indexed repositories with repository directory."""
    with (
        patch(
            'awslabs.git_repo_research_mcp_server.utils.get_default_index_dir'
        ) as mock_get_default_index_dir,
        patch('os.path.exists') as mock_exists,
        patch('os.listdir') as mock_listdir,
        patch('os.path.isdir') as mock_isdir,
        patch('awslabs.git_repo_research_mcp_server.utils.load_metadata') as mock_load_metadata,
    ):
        # Configure the mocks
        mock_get_default_index_dir.return_value = '/home/user/.git_repo_research'
        mock_exists.return_value = True
        mock_listdir.return_value = ['repo1']
        mock_isdir.return_value = True

        # Configure load_metadata to return metadata
        metadata = IndexMetadata(
            repository_name='repo1',
            repository_path='/path/to/repo1',
            index_path='/home/user/.git_repo_research/repo1',
            created_at=datetime.now(),
            last_accessed=datetime.now(),
            file_count=10,
            embedding_model='amazon.titan-embed-text-v2:0',
            chunk_count=20,
            file_types={'py': 5, 'md': 5},
            total_tokens=1000,
            index_size_bytes=5000,
            last_commit_id='abc123',
            repository_directory='/path/to/repo1/repository',
        )
        mock_load_metadata.return_value = metadata

        # Configure exists to return True for repository directory
        def mock_exists_side_effect(path):
            return True

        mock_exists.side_effect = mock_exists_side_effect

        # Call the function
        result = list_indexed_repositories()

        # Verify the result
        assert len(result.repositories) == 1
        assert result.repositories[0].repository_directory is not None
        assert result.repositories[0].repository_directory.endswith('/repository')


@pytest.mark.asyncio
async def test_delete_indexed_repository_index_dir_not_exists():
    """Test deleting a repository when the index directory doesn't exist."""
    with (
        patch(
            'awslabs.git_repo_research_mcp_server.utils.get_default_index_dir'
        ) as mock_get_default_index_dir,
        patch('os.path.exists') as mock_exists,
    ):
        # Configure the mocks
        mock_get_default_index_dir.return_value = '/home/user/.git_repo_research'
        mock_exists.return_value = False  # Index directory doesn't exist

        # Call the function
        result = await delete_indexed_repository('test_repo')

        # Verify the result
        assert result['status'] == 'error'
        assert 'Index directory /home/user/.git_repo_research does not exist' in result['message']


@pytest.mark.asyncio
async def test_delete_indexed_repository_with_file_index():
    """Test deleting a repository when the index is a file."""
    with (
        patch(
            'awslabs.git_repo_research_mcp_server.utils.get_default_index_dir'
        ) as mock_get_default_index_dir,
        patch('os.path.exists') as mock_exists,
        patch('os.path.isabs') as mock_isabs,
        patch('os.path.isdir') as mock_isdir,
        patch('os.path.isfile') as mock_isfile,
        patch('os.path.splitext') as mock_splitext,
        patch('os.access') as mock_access,
        patch('os.remove') as mock_remove,
        patch('awslabs.git_repo_research_mcp_server.utils.load_metadata') as mock_load_metadata,
        patch('loguru.logger.info') as mock_logger_info,
    ):
        # Configure the mocks
        mock_get_default_index_dir.return_value = '/home/user/.git_repo_research'
        mock_exists.return_value = True
        mock_isabs.return_value = False
        mock_isdir.return_value = False  # Not a directory
        mock_isfile.return_value = True  # It's a file
        mock_splitext.return_value = ('/home/user/.git_repo_research/test_repo', '')
        mock_access.return_value = True

        # Configure load_metadata to return metadata
        metadata = MagicMock()
        metadata.repository_name = 'test_repo'
        mock_load_metadata.return_value = metadata

        # Call the function
        result = await delete_indexed_repository('test_repo')

        # Verify the result
        assert result['status'] == 'success'
        assert "Successfully deleted repository 'test_repo'" in result['message']

        # Verify the mocks were called correctly
        mock_remove.assert_called()  # File should be removed
        mock_logger_info.assert_called()  # Logging should occur


@pytest.mark.asyncio
async def test_delete_indexed_repository_absolute_path():
    """Test deleting a repository using an absolute path."""
    with (
        patch(
            'awslabs.git_repo_research_mcp_server.utils.get_default_index_dir'
        ) as mock_get_default_index_dir,
        patch('os.path.exists') as mock_exists,
        patch('os.path.isabs') as mock_isabs,
        patch('os.path.isdir') as mock_isdir,
        patch('os.path.isfile') as mock_isfile,
        patch('os.path.splitext') as mock_splitext,
        patch('os.access') as mock_access,
        patch('os.remove') as mock_remove,
        patch('shutil.rmtree') as mock_rmtree,
        patch('awslabs.git_repo_research_mcp_server.utils.load_metadata') as mock_load_metadata,
        patch('loguru.logger.info') as mock_logger_info,
    ):
        # Configure the mocks
        mock_get_default_index_dir.return_value = '/home/user/.git_repo_research'
        mock_exists.return_value = True
        mock_isabs.return_value = True  # Absolute path
        mock_isdir.return_value = True
        mock_isfile.return_value = False
        mock_splitext.return_value = ('/absolute/path/to/test_repo', '')
        mock_access.return_value = True

        # Configure load_metadata to return metadata
        metadata = MagicMock()
        metadata.repository_name = 'test_repo'
        mock_load_metadata.return_value = metadata

        # Call the function with absolute path
        result = await delete_indexed_repository('/absolute/path/to/test_repo')

        # Verify the result
        assert result['status'] == 'success'
        assert "Successfully deleted repository 'test_repo'" in result['message']
        assert result['repository_name'] == 'test_repo'
        assert len(result['deleted_files']) > 0

        # Verify the mocks were called correctly
        mock_remove.assert_called()  # Metadata file should be removed
        mock_rmtree.assert_called()  # Repository directory should be removed
        mock_logger_info.assert_called()  # Logging should occur
