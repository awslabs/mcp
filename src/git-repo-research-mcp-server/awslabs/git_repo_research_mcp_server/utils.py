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
"""Utility functions for Git Repository Research MCP Server.

This module provides utility functions for the Git Repository Research MCP Server.
"""

import json
import os
import shutil
from awslabs.git_repo_research_mcp_server.defaults import Constants
from awslabs.git_repo_research_mcp_server.models import (
    DetailedIndexedRepositoriesResponse,
    DetailedIndexedRepositoryInfo,
    IndexedRepositoriesResponse,
    IndexedRepositoryInfo,
    IndexMetadata,
)
from datetime import datetime
from loguru import logger
from typing import Dict, List, Optional, Union


def get_default_index_dir() -> str:
    """Get the default index directory.

    Returns:
        Path to the default index directory
    """
    default_dir = os.path.expanduser(f'~/{Constants.DEFAULT_INDEX_DIR}')
    os.makedirs(default_dir, exist_ok=True)
    return default_dir


def load_metadata(metadata_path: str) -> Optional[IndexMetadata]:
    """Load metadata from a file.

    Args:
        metadata_path: Path to the metadata file

    Returns:
        IndexMetadata object if the file exists and is valid, None otherwise
    """
    if not os.path.exists(metadata_path):
        return None

    try:
        with open(metadata_path, 'r') as f:
            metadata_dict = json.load(f)
        return IndexMetadata(**metadata_dict)
    except Exception as e:
        logger.error(f'Error loading metadata from {metadata_path}: {e}')
        return None


def list_indexed_repositories(
    index_dir: Optional[str] = None, detailed: bool = False
) -> Union[IndexedRepositoriesResponse, DetailedIndexedRepositoriesResponse]:
    """List all indexed repositories.

    Args:
        index_dir: Directory to look for indices (optional, uses default if not provided)
        detailed: Whether to return detailed information about each index

    Returns:
        IndexedRepositoriesResponse or DetailedIndexedRepositoriesResponse object
    """
    index_dir = index_dir or get_default_index_dir()
    if not os.path.exists(index_dir):
        if detailed:
            return DetailedIndexedRepositoriesResponse(
                repositories=[],
                total_count=0,
                index_directory=index_dir,
                total_index_size_bytes=0,
            )
        else:
            return IndexedRepositoriesResponse(
                repositories=[],
                total_count=0,
                index_directory=index_dir,
            )

    repositories = []
    total_index_size = 0

    # Look for repository directories in the index directory
    for dirname in os.listdir(index_dir):
        dir_path = os.path.join(index_dir, dirname)
        if os.path.isdir(dir_path):
            # Check if this directory contains a metadata.json file
            metadata_path = os.path.join(dir_path, 'metadata.json')
            if os.path.exists(metadata_path):
                metadata = load_metadata(metadata_path)
                if metadata is None:
                    continue
            else:
                continue  # Skip directories without metadata.json

            # Check if repository directory exists
            repo_files_path = os.path.join(metadata.index_path, 'repository')
            repository_directory = None
            if os.path.exists(repo_files_path) and os.path.isdir(repo_files_path):
                repository_directory = repo_files_path

            # At this point, metadata is guaranteed to be not None
            if detailed:
                # Create a detailed repository info object
                repo_info = DetailedIndexedRepositoryInfo(
                    repository_name=metadata.repository_name,
                    repository_path=metadata.repository_path,
                    index_path=metadata.index_path,
                    repository_directory=repository_directory,
                    created_at=metadata.created_at,
                    last_accessed=metadata.last_accessed,
                    file_count=metadata.file_count,
                    embedding_model=metadata.embedding_model,
                    chunk_count=metadata.chunk_count,
                    file_types=metadata.file_types,
                    total_tokens=metadata.total_tokens,
                    index_size_bytes=metadata.index_size_bytes,
                    last_commit_id=metadata.last_commit_id,
                )
                if metadata.index_size_bytes:
                    total_index_size += metadata.index_size_bytes
            else:
                # Create a basic repository info object
                repo_info = IndexedRepositoryInfo(
                    repository_name=metadata.repository_name,
                    repository_path=metadata.repository_path,
                    index_path=metadata.index_path,
                    repository_directory=repository_directory,
                    created_at=metadata.created_at,
                    last_accessed=metadata.last_accessed,
                    file_count=metadata.file_count,
                    embedding_model=metadata.embedding_model,
                )

            repositories.append(repo_info)

    if detailed:
        return DetailedIndexedRepositoriesResponse(
            repositories=repositories,
            total_count=len(repositories),
            index_directory=index_dir,
            total_index_size_bytes=total_index_size,
        )
    else:
        return IndexedRepositoriesResponse(
            repositories=repositories,
            total_count=len(repositories),
            index_directory=index_dir,
        )


class DateTimeEncoder(json.JSONEncoder):
    """Custom JSON encoder to handle datetime objects.

    This encoder converts datetime objects to ISO format strings during JSON serialization.
    """

    def default(self, o):
        """Convert datetime objects to ISO format strings.

        Args:
            o: Object to convert

        Returns:
            ISO format string if object is a datetime, otherwise default serialization
        """
        if isinstance(o, datetime):
            return o.isoformat()
        return super().default(o)


def format_size(size_bytes: int) -> str:
    """Format a size in bytes to a human-readable string.

    Args:
        size_bytes: Size in bytes

    Returns:
        Human-readable string
    """
    if size_bytes < 1024:
        return f'{size_bytes} B'
    elif size_bytes < 1024 * 1024:
        return f'{size_bytes / 1024:.2f} KB'
    elif size_bytes < 1024 * 1024 * 1024:
        return f'{size_bytes / (1024 * 1024):.2f} MB'
    else:
        return f'{size_bytes / (1024 * 1024 * 1024):.2f} GB'


async def delete_indexed_repository(
    repository_name_or_path: str, index_dir: Optional[str] = None
) -> Dict[str, Union[str, List[str]]]:
    """Delete an indexed repository.

    Args:
        repository_name_or_path: Name of the repository or path to the index
        index_dir: Directory to look for indices (optional, uses default if not provided)

    Returns:
        Dictionary with status and message
    """
    index_dir = index_dir or get_default_index_dir()
    if not os.path.exists(index_dir):
        return {
            'status': 'error',
            'message': f'Index directory {index_dir} does not exist',
        }

    # Check if the input is a repository name or an index path
    if os.path.isabs(repository_name_or_path) and os.path.exists(repository_name_or_path):
        # It's an index path
        index_path = repository_name_or_path
        metadata_path = os.path.join(index_path, 'metadata.json')
    else:
        # It's a repository name, find the corresponding index directory
        repository_name = repository_name_or_path
        # Sanitize the repository name for use in a directory name
        safe_name = ''.join(c if c.isalnum() or c in '-_' else '_' for c in repository_name)
        index_path = os.path.join(index_dir, safe_name)
        metadata_path = os.path.join(index_path, 'metadata.json')

        if not os.path.exists(index_path) or not os.path.exists(metadata_path):
            # Try to find the repository by checking metadata in all subdirectories
            found = False
            for dirname in os.listdir(index_dir):
                dir_path = os.path.join(index_dir, dirname)
                if os.path.isdir(dir_path):
                    potential_metadata_path = os.path.join(dir_path, 'metadata.json')
                    if os.path.exists(potential_metadata_path):
                        metadata = load_metadata(potential_metadata_path)
                        if metadata and metadata.repository_name == repository_name:
                            index_path = dir_path
                            metadata_path = potential_metadata_path
                            found = True
                            break

            if not found:
                return {
                    'status': 'error',
                    'message': f"Repository '{repository_name}' not found in index directory",
                }

    # Check if the metadata file exists
    if not os.path.exists(metadata_path):
        return {
            'status': 'error',
            'message': f'Metadata file {metadata_path} not found',
        }

    # Load the metadata to get repository information
    metadata = load_metadata(metadata_path)
    if metadata is None:
        return {
            'status': 'error',
            'message': f'Failed to load metadata from {metadata_path}',
        }

    repository_name = metadata.repository_name

    # Check permissions before attempting to delete
    files_to_check = [metadata_path]
    if os.path.exists(index_path):
        files_to_check.append(index_path)

    index_dir_path = os.path.splitext(index_path)[0]
    if os.path.isdir(index_dir_path):
        files_to_check.append(index_dir_path)

    permission_issues = []
    for file_path in files_to_check:
        if not os.access(file_path, os.W_OK):
            permission_issues.append(file_path)

    if permission_issues:
        permission_msg = 'Permission denied for the following files:\n'
        for path in permission_issues:
            permission_msg += f'  - {path}\n'
        permission_msg += '\nTo delete these files, you may need to run the command with sudo or adjust file permissions.'

        return {
            'status': 'error',
            'message': permission_msg,
            'repository_name': repository_name,
            'permission_issues': permission_issues,
        }

    # Delete the files
    deleted_files = []
    errors = []

    # Check if the index path is a file or directory
    is_file = os.path.isfile(index_path)
    is_dir = os.path.isdir(index_path)

    # Check for repository directory
    repo_files_path = os.path.join(index_path, 'repository')
    if os.path.isdir(repo_files_path):
        files_to_check.append(repo_files_path)

    # Try to delete the metadata file first
    try:
        os.remove(metadata_path)
        deleted_files.append(metadata_path)
        logger.info(f'Deleted metadata file: {metadata_path}')
    except Exception as e:
        errors.append(f'Failed to delete metadata file {metadata_path}: {str(e)}')
        logger.error(f'Error deleting metadata file {metadata_path}: {e}')

    # Try to delete the repository directory if it exists
    if os.path.isdir(repo_files_path):
        try:
            shutil.rmtree(repo_files_path)
            deleted_files.append(repo_files_path)
            logger.info(f'Deleted repository directory: {repo_files_path}')
        except Exception as e:
            errors.append(f'Failed to delete repository directory {repo_files_path}: {str(e)}')
            logger.error(f'Error deleting repository directory {repo_files_path}: {e}')

    # If the index path is a file, try to delete it
    if is_file:
        try:
            os.remove(index_path)
            deleted_files.append(index_path)
            logger.info(f'Deleted index file: {index_path}')
        except Exception as e:
            # If we can't delete the file, log the error but don't consider it a failure
            # since the index directory might contain the actual data
            logger.warning(f'Could not delete index file {index_path}: {e}')

    # Try to delete the directory if it exists
    index_dir_path = os.path.splitext(index_path)[0]
    if os.path.isdir(index_dir_path):
        try:
            shutil.rmtree(index_dir_path)
            deleted_files.append(index_dir_path)
            logger.info(f'Deleted index directory: {index_dir_path}')
        except Exception as e:
            errors.append(f'Failed to delete index directory {index_dir_path}: {str(e)}')
            logger.error(f'Error deleting index directory {index_dir_path}: {e}')

    # If the index path itself is a directory, try to delete it
    if is_dir and index_path != index_dir_path:
        try:
            shutil.rmtree(index_path)
            deleted_files.append(index_path)
            logger.info(f'Deleted index directory: {index_path}')
        except Exception as e:
            # If we already deleted the directory with the same name, this is expected
            if index_path in deleted_files:
                logger.info(f'Index directory {index_path} was already deleted')
            else:
                errors.append(f'Failed to delete index directory {index_path}: {str(e)}')
                logger.error(f'Error deleting index directory {index_path}: {e}')

    # Return appropriate response based on results
    if not errors:
        return {
            'status': 'success',
            'message': f"Successfully deleted repository '{repository_name}'",
            'repository_name': repository_name,
            'deleted_files': deleted_files,
        }
    elif deleted_files:
        # Partial success
        return {
            'status': 'partial',
            'message': f"Partially deleted repository '{repository_name}'. Some files could not be deleted.",
            'repository_name': repository_name,
            'deleted_files': deleted_files,
            'errors': errors,
        }
    else:
        # Complete failure
        error_msg = f"Failed to delete repository '{repository_name}':\n"
        for err in errors:
            error_msg += f'  - {err}\n'

        return {
            'status': 'error',
            'message': error_msg,
            'repository_name': repository_name,
            'errors': errors,
        }
