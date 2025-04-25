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
"""Repository handling for Git Repository Research MCP Server.

This module provides functionality for cloning, accessing, and processing
Git repositories for indexing and searching.
"""

import fnmatch
import os
import shutil
import tempfile
from awslabs.git_repo_research_mcp_server.defaults import Constants
from git import Repo
from loguru import logger
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse


def is_git_url(repo_path: str) -> bool:
    """Check if a string is a Git URL.

    Args:
        repo_path: Path or URL to check

    Returns:
        True if the string is a Git URL, False otherwise
    """
    parsed = urlparse(repo_path)
    return parsed.scheme in ('http', 'https', 'git', 'ssh')


def is_git_repo(path: str) -> bool:
    """Check if a path is a Git repository.

    Args:
        path: Path to check

    Returns:
        True if the path is a Git repository, False otherwise
    """
    try:
        Repo(path)
        return True
    except Exception:
        return False


def clone_repository(url: str, target_dir: Optional[str] = None) -> str:
    """Clone a Git repository from a URL.

    Args:
        url: URL of the repository to clone
        target_dir: Directory to clone into (optional, uses temp dir if not provided)

    Returns:
        Path to the cloned repository

    Raises:
        Exception: If cloning fails
    """
    if target_dir is None:
        target_dir = tempfile.mkdtemp(prefix='git_repo_research_')

    logger.info(f'Cloning repository from {url} to {target_dir}')
    try:
        # Clone the repository with GitPython
        Repo.clone_from(url, target_dir)

        # Check if .git directory exists after cloning
        git_dir = os.path.join(target_dir, '.git')
        if os.path.exists(git_dir):
            logger.info(f'.git directory exists at {git_dir}')
        else:
            logger.warning(f'.git directory not found after cloning at {git_dir}')
            # List the contents of the directory to debug
            logger.info(f'Contents of {target_dir}: {os.listdir(target_dir)}')

        return target_dir
    except Exception as e:
        # Clean up the target directory if it was created
        if os.path.exists(target_dir):
            shutil.rmtree(target_dir, ignore_errors=True)
        logger.error(f'Failed to clone repository: {e}')
        raise


def get_repository_name(repo_path: str) -> str:
    """Get the name of a repository.

    Args:
        repo_path: Path or URL of the repository

    Returns:
        Name of the repository, including GitHub organization/username if available
        Note: For GitHub repositories, the format is "org_repo" (with underscore)
        instead of "org/repo" for file path compatibility
    """
    if is_git_url(repo_path):
        # Extract the repository name from the URL
        parsed = urlparse(repo_path)
        path_parts = parsed.path.strip('/').split('/')

        # Check if this is a GitHub URL with org/username
        if parsed.netloc in ['github.com', 'www.github.com'] and len(path_parts) >= 2:
            # Include the organization/username in the repository name
            org_name = path_parts[-2]
            repo_name = path_parts[-1]
            if repo_name.endswith('.git'):
                repo_name = repo_name[:-4]
            # Use underscore instead of slash for file path compatibility
            return f'{org_name}_{repo_name}'
        else:
            # For non-GitHub URLs or URLs without clear org structure,
            # just use the last part of the path
            repo_name = path_parts[-1]
            if repo_name.endswith('.git'):
                repo_name = repo_name[:-4]
            return repo_name
    else:
        # Use the directory name as the repository name
        return os.path.basename(os.path.abspath(repo_path))


def get_text_files(
    repo_path: str,
    include_patterns: Optional[List[str]] = None,
    exclude_patterns: Optional[List[str]] = None,
) -> List[str]:
    """Get all text files in a repository.

    Args:
        repo_path: Path to the repository
        include_patterns: Glob patterns for files to include (optional)
        exclude_patterns: Glob patterns for files to exclude (optional)

    Returns:
        List of paths to text files
    """
    if include_patterns is None:
        include_patterns = Constants.TEXT_FILE_INCLUDE_PATTERNS
    if exclude_patterns is None:
        exclude_patterns = Constants.TEXT_FILE_EXCLUDE_PATTERNS

    text_files = []
    for root, _, files in os.walk(repo_path):
        for file in files:
            file_path = os.path.join(root, file)
            rel_path = os.path.relpath(file_path, repo_path)

            # Check if the file matches any include pattern
            included = any(fnmatch.fnmatch(rel_path, pattern) for pattern in include_patterns)
            if not included:
                continue

            # Check if the file matches any exclude pattern
            excluded = any(fnmatch.fnmatch(rel_path, pattern) for pattern in exclude_patterns)
            if excluded:
                continue

            # Try to read the file as text
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    # Read a small sample to check if it's text
                    sample = f.read(1024)
                    # If we can decode it as UTF-8, it's probably text
                    if sample:
                        text_files.append(file_path)
            except UnicodeDecodeError:
                # Not a text file
                pass
            except Exception as e:
                logger.warning(f'Error reading file {file_path}: {e}')

    return text_files


def get_file_extension_stats(file_paths: List[str]) -> Dict[str, int]:
    """Get statistics about file extensions.

    Args:
        file_paths: List of file paths

    Returns:
        Dictionary mapping file extensions to counts
    """
    extension_counts = {}
    for file_path in file_paths:
        _, ext = os.path.splitext(file_path)
        if ext:
            # Remove the dot from the extension
            ext = ext[1:].lower()
            extension_counts[ext] = extension_counts.get(ext, 0) + 1
        else:
            extension_counts['no_extension'] = extension_counts.get('no_extension', 0) + 1
    return extension_counts


def read_file_content(file_path: str) -> str:
    """Read the content of a file.

    Args:
        file_path: Path to the file

    Returns:
        Content of the file as a string

    Raises:
        Exception: If reading fails
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        logger.error(f'Failed to read file {file_path}: {e}')
        raise


def chunk_text(text: str, chunk_size: int = 1000, chunk_overlap: int = 200) -> List[str]:
    """Split text into chunks.

    Args:
        text: Text to split
        chunk_size: Maximum size of each chunk in characters
        chunk_overlap: Overlap between chunks in characters

    Returns:
        List of text chunks
    """
    if not text or len(text) <= chunk_size:
        return [text] if text else []

    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        if end >= len(text):
            chunks.append(text[start:])
            break

        # Try to find a good breaking point (newline or space)
        break_point = text.rfind('\n', start + chunk_size - chunk_overlap, end)
        if break_point == -1:
            break_point = text.rfind(' ', start + chunk_size - chunk_overlap, end)
        if break_point == -1:
            break_point = end

        chunks.append(text[start:break_point])
        start = break_point + 1 if text[break_point] in ['\n', ' '] else break_point

    return chunks


def process_repository(
    repo_path: str,
    include_patterns: Optional[List[str]] = None,
    exclude_patterns: Optional[List[str]] = None,
    chunk_size: int = 1000,
    chunk_overlap: int = 200,
) -> Tuple[List[str], Dict[str, str], Dict[str, int]]:
    """Process a repository for indexing.

    Args:
        repo_path: Path to the repository
        include_patterns: Glob patterns for files to include (optional)
        exclude_patterns: Glob patterns for files to exclude (optional)
        chunk_size: Maximum size of each chunk in characters
        chunk_overlap: Overlap between chunks in characters

    Returns:
        Tuple containing:
        - List of text chunks
        - Dictionary mapping chunks to file paths
        - Dictionary of file extension statistics
    """
    logger.info(f'Processing repository at {repo_path}')
    text_files = get_text_files(repo_path, include_patterns, exclude_patterns)
    logger.info(f'Found {len(text_files)} text files')

    extension_stats = get_file_extension_stats(text_files)
    logger.info(f'File extension statistics: {extension_stats}')

    chunks = []
    chunk_to_file = {}

    for file_path in text_files:
        try:
            content = read_file_content(file_path)
            file_chunks = chunk_text(content, chunk_size, chunk_overlap)

            rel_path = os.path.relpath(file_path, repo_path)
            for chunk in file_chunks:
                chunks.append(chunk)
                chunk_to_file[chunk] = rel_path
        except Exception as e:
            logger.warning(f'Error processing file {file_path}: {e}')

    logger.info(f'Created {len(chunks)} text chunks')
    return chunks, chunk_to_file, extension_stats


def cleanup_repository(repo_path: str) -> None:
    """Clean up a cloned repository.

    Args:
        repo_path: Path to the repository
    """
    if os.path.exists(repo_path) and os.path.isdir(repo_path):
        logger.info(f'Cleaning up repository at {repo_path}')
        try:
            shutil.rmtree(repo_path, ignore_errors=True)
        except Exception as e:
            logger.warning(f'Error cleaning up repository: {e}')
