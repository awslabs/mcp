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
"""Comprehensive tests for Git Repository Research MCP Server."""

import argparse
import json
import os
import pytest
import subprocess
import tempfile
from datetime import datetime
from unittest.mock import MagicMock, patch, ANY

# Import the server functionality
from awslabs.git_repo_research_mcp_server.server import (
    access_file_or_directory,
    list_repositories,
    main,
    mcp,
    mcp_access_file,
    mcp_delete_repository,
    mcp_index_repository,
    mcp_search_github_repos,
    mcp_search_repository,
    repository_summary,
)
from awslabs.git_repo_research_mcp_server.models import (
    DeleteRepositoryResponse,
    EmbeddingModel,
    GitHubRepoSearchResponse,
    GitHubRepoSearchResult,
)
from mcp.server.fastmcp import Image


class TestContext:
    """Context for testing MCP tools."""

    async def info(self, message):
        """Log an informational message."""
        pass

    async def error(self, message):
        """Log an error message."""
        pass

    async def report_progress(self, current, total, message=None):
        """Report progress."""
        pass


@pytest.fixture
def test_context():
    """Create a test context."""
    return TestContext()


@pytest.fixture
def test_git_repo():
    """Create a test Git repository."""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Initialize Git repository
        repo_dir = os.path.join(temp_dir, 'test_repo')
        os.makedirs(repo_dir)

        # Setup Git config
        subprocess.run(['git', 'init'], cwd=repo_dir, check=True)
        subprocess.run(['git', 'config', 'user.name', 'Test User'], cwd=repo_dir, check=True)
        subprocess.run(
            ['git', 'config', 'user.email', 'test@example.com'], cwd=repo_dir, check=True
        )

        # Create README.md
        readme_path = os.path.join(repo_dir, 'README.md')
        with open(readme_path, 'w') as f:
            f.write("""# Test Repository

This is a test repository for the Git Repository Research MCP Server.

## Features

- Semantic search
- Repository indexing
- File access
""")

        # Create src directory
        src_dir = os.path.join(repo_dir, 'src')
        os.makedirs(src_dir)

        # Create Python files
        with open(os.path.join(src_dir, 'main.py'), 'w') as f:
            f.write("""
def main():
    # Main entry point
    print("Hello, World!")

    user_id = "user123"
    user_info = get_user(user_id)
    print(f"User: {user_info}")

    result = calculate_sum(5, 10)
    print(f"Sum: {result}")

if __name__ == "__main__":
    main()
""")

        with open(os.path.join(src_dir, 'utils.py'), 'w') as f:
            f.write('''
def get_user(user_id):
    """
    Get user information by ID.

    Args:
        user_id: The user's ID

    Returns:
        dict: User information
    """
    users = {
        "user123": {"name": "John Doe", "email": "john@example.com"},
        "user456": {"name": "Jane Smith", "email": "jane@example.com"}
    }
    return users.get(user_id, {"name": "Unknown", "email": "unknown@example.com"})

def calculate_sum(a, b):
    """
    Calculate the sum of two numbers.

    Args:
        a: First number
        b: Second number

    Returns:
        int or float: The sum of a and b
    """
    return a + b
''')

        # Create docs directory
        docs_dir = os.path.join(repo_dir, 'docs')
        os.makedirs(docs_dir)

        with open(os.path.join(docs_dir, 'api.md'), 'w') as f:
            f.write("""# API Documentation

## Functions

### get_user(user_id)

Gets user information by ID.

### calculate_sum(a, b)

Calculates the sum of two numbers.
""")

        # Create an image file for testing image access
        img_dir = os.path.join(repo_dir, 'images')
        os.makedirs(img_dir)
        with open(os.path.join(img_dir, 'test.png'), 'wb') as f:
            # Create a minimal valid PNG file
            f.write(b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82')

        # Add everything to Git
        subprocess.run(['git', 'add', '.'], cwd=repo_dir, check=True)
        subprocess.run(['git', 'commit', '-m', 'Initial commit'], cwd=repo_dir, check=True)

        yield repo_dir


@pytest.mark.asyncio
async def test_mcp_index_repository(test_context, test_git_repo, monkeypatch):
    """Test indexing a repository."""
    # Mock the Bedrock embeddings to avoid actual API calls
    with patch(
        'awslabs.git_repo_research_mcp_server.embeddings.BedrockEmbeddings'
    ) as mock_bedrock:
        # Configure the mock
        mock_embeddings = MagicMock()
        mock_embeddings.embed_query.return_value = [0.1] * 1536
        mock_embeddings.embed_documents.return_value = [[0.1] * 1536] * 10
        mock_bedrock.return_value = mock_embeddings

        # Use a unique name for the repository
        repo_name = f'{os.path.basename(test_git_repo)}'

        # Test with default parameters
        result = await mcp_index_repository(
            test_context,
            repository_path=test_git_repo,
            output_path=None,
            embedding_model=EmbeddingModel.AMAZON_TITAN_EMBED_TEXT_V2,
            include_patterns=['**/*.md', '**/*.py'],
            exclude_patterns=['**/.git/**'],
            chunk_size=1000,
            chunk_overlap=200,
        )

        # Verify the indexing result
        assert result['status'] == 'success', f'Indexing failed with message: {result.get("message", "")}'
        assert result['repository_name'] == repo_name, "Repository name doesn't match expected value"
        assert 'index_path' in result, 'Index path missing from result'
        assert result['file_count'] > 0, 'No files were indexed'
        assert result['chunk_count'] > 0, 'No chunks were created'
        assert 'embedding_model' in result, 'Embedding model info missing from result'
        assert result['embedding_model'] == EmbeddingModel.AMAZON_TITAN_EMBED_TEXT_V2, 'Wrong embedding model used'

        # Test with custom output path
        custom_output_path = 'custom_output_repo'
        result_custom = await mcp_index_repository(
            test_context,
            repository_path=test_git_repo,
            output_path=custom_output_path,
            embedding_model=EmbeddingModel.AMAZON_TITAN_EMBED_TEXT_V2,
            include_patterns=['**/*.md'],
            exclude_patterns=['**/.git/**'],
            chunk_size=1000,
            chunk_overlap=200,
        )

        # Verify the custom output path was used
        assert result_custom['status'] == 'success', f'Indexing failed with message: {result_custom.get("message", "")}'
        assert result_custom['repository_name'] == custom_output_path, 'Custom output path not used as repository name'

        # Test with output path containing slashes (should be normalized)
        slash_output_path = 'org/repo'
        result_slash = await mcp_index_repository(
            test_context,
            repository_path=test_git_repo,
            output_path=slash_output_path,
            embedding_model=EmbeddingModel.AMAZON_TITAN_EMBED_TEXT_V2,
            include_patterns=['**/*.md'],
            exclude_patterns=['**/.git/**'],
            chunk_size=1000,
            chunk_overlap=200,
        )

        # Verify the slash output path was normalized
        assert result_slash['status'] == 'success', f'Indexing failed with message: {result_slash.get("message", "")}'
        assert result_slash['repository_name'] == 'org_repo', 'Slash in output path not normalized'

        # Test error handling
        with patch(
            'awslabs.git_repo_research_mcp_server.indexer.RepositoryIndexer.index_repository',
            side_effect=Exception('Test exception'),
        ):
            with pytest.raises(Exception) as excinfo:
                await mcp_index_repository(
                    test_context,
                    repository_path=test_git_repo,
                    output_path=None,
                    embedding_model=EmbeddingModel.AMAZON_TITAN_EMBED_TEXT_V2,
                    include_patterns=['**/*.md'],
                    exclude_patterns=['**/.git/**'],
                    chunk_size=1000,
                    chunk_overlap=200,
                )
            assert 'Test exception' in str(excinfo.value)

        # Clean up
        await mcp_delete_repository(test_context, repository_name_or_path=repo_name)
        await mcp_delete_repository(test_context, repository_name_or_path=custom_output_path)
        await mcp_delete_repository(test_context, repository_name_or_path='org_repo')


@pytest.mark.asyncio
async def test_repository_summary(test_context, test_git_repo, monkeypatch):
    """Test repository summary resource."""
    # Mock the Bedrock embeddings to avoid actual API calls
    with patch(
        'awslabs.git_repo_research_mcp_server.embeddings.BedrockEmbeddings'
    ) as mock_bedrock:
        # Configure the mock
        mock_embeddings = MagicMock()
        mock_embeddings.embed_query.return_value = [0.1] * 1536
        mock_embeddings.embed_documents.return_value = [[0.1] * 1536] * 10
        mock_bedrock.return_value = mock_embeddings

        # Use a unique name for the repository
        repo_name = f'{os.path.basename(test_git_repo)}'

        # Index the repository first
        await mcp_index_repository(
            test_context,
            repository_path=test_git_repo,
            output_path=None,
            embedding_model=EmbeddingModel.AMAZON_TITAN_EMBED_TEXT_V2,
            include_patterns=['**/*.md', '**/*.py'],
            exclude_patterns=['**/.git/**'],
            chunk_size=1000,
            chunk_overlap=200,
        )

        # Test repository summary
        summary_result = await repository_summary(repository_name=repo_name)
        summary_data = json.loads(summary_result)
        
        assert summary_data['status'] == 'success', 'Repository summary failed'
        assert summary_data['repository_name'] == repo_name, 'Wrong repository in summary'
        assert 'tree' in summary_data, 'No tree structure in summary'
        assert 'helpful_files' in summary_data, 'No helpful files in summary'
        
        # Test with repository name containing slashes (should be normalized)
        slash_repo_name = 'org/repo'
        
        # Index with slash name
        await mcp_index_repository(
            test_context,
            repository_path=test_git_repo,
            output_path=slash_repo_name,
            embedding_model=EmbeddingModel.AMAZON_TITAN_EMBED_TEXT_V2,
            include_patterns=['**/*.md'],
            exclude_patterns=['**/.git/**'],
            chunk_size=1000,
            chunk_overlap=200,
        )
        
        # Get summary with slash name
        summary_slash_result = await repository_summary(repository_name=slash_repo_name)
        summary_slash_data = json.loads(summary_slash_result)
        
        assert summary_slash_data['status'] == 'success', 'Repository summary with slash name failed'
        assert summary_slash_data['repository_name'] == slash_repo_name, 'Wrong repository in slash name summary'
        
        # Test error handling - non-existent repository
        summary_error_result = await repository_summary(repository_name='non_existent_repo')
        summary_error_data = json.loads(summary_error_result)
        
        assert summary_error_data['status'] == 'error', 'Error not reported for non-existent repository'
        assert 'not found' in summary_error_data['message'], 'Wrong error message for non-existent repository'
        
        # Test error handling - exception during listing
        with patch(
            'awslabs.git_repo_research_mcp_server.search.RepositorySearcher.list_repository_files',
            side_effect=Exception('Test exception'),
        ):
            summary_exception_result = await repository_summary(repository_name=repo_name)
            summary_exception_data = json.loads(summary_exception_result)
            
            assert summary_exception_data['status'] == 'error', 'Error not reported for exception'
            assert 'Test exception' in summary_exception_data['message'], 'Wrong error message for exception'

        # Clean up
        await mcp_delete_repository(test_context, repository_name_or_path=repo_name)
        await mcp_delete_repository(test_context, repository_name_or_path='org_repo')


@pytest.mark.asyncio
async def test_list_repositories(test_context, test_git_repo, monkeypatch):
    """Test listing repositories resource."""
    # Mock the Bedrock embeddings to avoid actual API calls
    with patch(
        'awslabs.git_repo_research_mcp_server.embeddings.BedrockEmbeddings'
    ) as mock_bedrock:
        # Configure the mock
        mock_embeddings = MagicMock()
        mock_embeddings.embed_query.return_value = [0.1] * 1536
        mock_embeddings.embed_documents.return_value = [[0.1] * 1536] * 10
        mock_bedrock.return_value = mock_embeddings

        # Use unique names for the repositories
        repo_name1 = f'{os.path.basename(test_git_repo)}_1'
        repo_name2 = f'{os.path.basename(test_git_repo)}_2'

        # Index two repositories
        await mcp_index_repository(
            test_context,
            repository_path=test_git_repo,
            output_path=repo_name1,
            embedding_model=EmbeddingModel.AMAZON_TITAN_EMBED_TEXT_V2,
            include_patterns=['**/*.md'],
            exclude_patterns=['**/.git/**'],
            chunk_size=1000,
            chunk_overlap=200,
        )
        
        await mcp_index_repository(
            test_context,
            repository_path=test_git_repo,
            output_path=repo_name2,
            embedding_model=EmbeddingModel.AMAZON_TITAN_EMBED_TEXT_V2,
            include_patterns=['**/*.py'],
            exclude_patterns=['**/.git/**'],
            chunk_size=1000,
            chunk_overlap=200,
        )

        # Test listing repositories
        list_result = await list_repositories()
        list_data = json.loads(list_result)
        
        assert 'repositories' in list_data, 'No repositories field in list result'
        assert len(list_data['repositories']) >= 2, 'Not all repositories found in list'
        
        # Find our repositories in the list
        repo1_found = False
        repo2_found = False
        for repo in list_data['repositories']:
            if repo['repository_name'] == repo_name1:
                repo1_found = True
                assert repo['file_count'] > 0, 'Repository 1 has no files'
                assert repo['chunk_count'] > 0, 'Repository 1 has no chunks'
            elif repo['repository_name'] == repo_name2:
                repo2_found = True
                assert repo['file_count'] > 0, 'Repository 2 has no files'
                assert repo['chunk_count'] > 0, 'Repository 2 has no chunks'
        
        assert repo1_found, f'Repository {repo_name1} not found in list'
        assert repo2_found, f'Repository {repo_name2} not found in list'
        
        # Test error handling
        with patch(
            'awslabs.git_repo_research_mcp_server.utils.list_indexed_repositories',
            side_effect=Exception('Test exception'),
        ):
            list_exception_result = await list_repositories()
            list_exception_data = json.loads(list_exception_result)
            
            assert 'status' in list_exception_data, 'No status field in exception result'
            assert list_exception_data['status'] == 'error', 'Error not reported for exception'
            assert 'Test exception' in list_exception_data['message'], 'Wrong error message for exception'

        # Clean up
        await mcp_delete_repository(test_context, repository_name_or_path=repo_name1)
        await mcp_delete_repository(test_context, repository_name_or_path=repo_name2)


@pytest.mark.asyncio
async def test_access_file_or_directory(test_context, test_git_repo, monkeypatch):
    """Test accessing files and directories."""
    # Mock the Bedrock embeddings to avoid actual API calls
    with patch(
        'awslabs.git_repo_research_mcp_server.embeddings.BedrockEmbeddings'
    ) as mock_bedrock:
        # Configure the mock
        mock_embeddings = MagicMock()
        mock_embeddings.embed_query.return_value = [0.1] * 1536
        mock_embeddings.embed_documents.return_value = [[0.1] * 1536] * 10
        mock_bedrock.return_value = mock_embeddings

        # Use a unique name for the repository
        repo_name = f'{os.path.basename(test_git_repo)}'

        # Index the repository first
        await mcp_index_repository(
            test_context,
            repository_path=test_git_repo,
            output_path=None,
            embedding_model=EmbeddingModel.AMAZON_TITAN_EMBED_TEXT_V2,
            include_patterns=['**/*.md', '**/*.py', '**/*.png'],
            exclude_patterns=['**/.git/**'],
            chunk_size=1000,
            chunk_overlap=200,
        )

        # Get the index path
        list_result = await list_repositories()
        list_data = json.loads(list_result)
        index_path = None
        for repo in list_data['repositories']:
            if repo['repository_name'] == repo_name:
                index_path = repo['index_path']
                break
        
        assert index_path is not None, f'Repository {repo_name} not found in list'
        
        # Test accessing a text file
        readme_path = f'{repo_name}/repository/README.md'
        readme_result = await access_file_or_directory(readme_path)
        assert isinstance(readme_result, str), 'README result is not a string'
        assert 'Test Repository' in readme_result, 'Expected content not found in README'
        
        # Test accessing a directory
        src_path = f'{repo_name}/repository/src'
        src_result = await access_file_or_directory(src_path)
        src_data = json.loads(src_result)
        
        assert src_data['status'] == 'success', 'Directory access failed'
        assert src_data['type'] == 'directory', 'Wrong type for directory'
        assert 'main.py' in src_data['files'], 'Expected file not found in directory'
        assert 'utils.py' in src_data['files'], 'Expected file not found in directory'
        
        # Test accessing an image file
        img_path = f'{repo_name}/repository/images/test.png'
        img_result = await access_file_or_directory(img_path)
        
        assert isinstance(img_result, Image), 'Image result is not an Image object'
        assert img_result.format == 'png', 'Wrong image format'
        assert len(img_result.data) > 0, 'Image data is empty'
        
        # Test accessing a non-existent file
        nonexistent_path = f'{repo_name}/repository/nonexistent.txt'
        nonexistent_result = await access_file_or_directory(nonexistent_path)
        nonexistent_data = json.loads(nonexistent_result)
        
        assert nonexistent_data['status'] == 'error', 'Error not reported for non-existent file'
        assert 'not found' in nonexistent_data['message'], 'Wrong error message for non-existent file'
        
        # Test with repository name containing slashes
        slash_repo_name = 'org/repo'
        
        # Index with slash name
        await mcp_index_repository(
            test_context,
            repository_path=test_git_repo,
            output_path=slash_repo_name.replace('/', '_'),
            embedding_model=EmbeddingModel.AMAZON_TITAN_EMBED_TEXT_V2,
            include_patterns=['**/*.md'],
            exclude_patterns=['**/.git/**'],
            chunk_size=1000,
            chunk_overlap=200,
        )
        
        # Test accessing a file with slash in repository name
        slash_readme_path = f'{slash_repo_name}/repository/README.md'
        slash_readme_result = await access_file_or_directory(slash_readme_path)
        
        assert isinstance(slash_readme_result, str), 'README result with slash repo is not a string'
        assert 'Test Repository' in slash_readme_result, 'Expected content not found in README with slash repo'
        
        # Test error handling
        with patch('os.path.exists', side_effect=Exception('Test exception')):
            error_result = await access_file_or_directory(readme_path)
            error_data = json.loads(error_result)
            
            assert error_data['status'] == 'error', 'Error not reported for exception'
            assert 'Test exception' in error_data['message'], 'Wrong error message for exception'

        # Clean up
        await mcp_delete_repository(test_context, repository_name_or_path=repo_name)
        await mcp_delete_repository(test_context, repository_name_or_path='org_repo')


@pytest.mark.asyncio
async def test_mcp_search_repository(test_context, test_git_repo, monkeypatch):
    """Test searching a repository."""
    # Mock the Bedrock embeddings to avoid actual API calls
    with patch(
        'awslabs.git_repo_research_mcp_server.embeddings.BedrockEmbeddings'
    ) as mock_bedrock:
        # Configure the mock
        mock_embeddings = MagicMock()
        mock_embeddings.embed_query.return_value = [0.1] * 1536
        mock_embeddings.embed_documents.return_value = [[0.1] * 1536] * 10
        mock_bedrock.return_value = mock_embeddings

        # Use a unique name for the repository
        repo_name = f'{os.path.basename(test_git_repo)}'

        # Index the repository first
        await mcp_index_repository(
            test_context,
            repository_path=test_git_repo,
            output_path=None,
            embedding_model=EmbeddingModel.AMAZON_TITAN_EMBED_TEXT_V2,
            include_patterns=['**/*.md', '**/*.py'],
            exclude_patterns=['**/.git/**'],
            chunk_size=1000,
            chunk_overlap=200,
        )

        # Test repository search
        search_result = await mcp_search_repository(
            test_context, 
            index_path=repo_name, 
            query='user information', 
            limit=5, 
            threshold=0.0
        )
        
        assert search_result['status'] == 'success', 'Search failed'
        assert 'results' in search_result, 'No results field in search response'
        assert len(search_result['results']) > 0, 'No search results found'
        assert 'execution_time_ms' in search_result, 'No execution time in search response'
        
        # Test with repository name containing slashes (should be normalized)
        slash_repo_name = 'org/repo'
        
        # Index with slash name
        await mcp_index_repository(
            test_context,
            repository_path=test_git_repo,
            output_path=slash_repo_name,
            embedding_model=EmbeddingModel.AMAZON_TITAN_EMBED_TEXT_V2,
            include_patterns=['**/*.md'],
            exclude_patterns=['**/.git/**'],
            chunk_size=1000,
            chunk_overlap=200,
        )
        
        # Search with slash name
        search_slash_result = await mcp_search_repository(
            test_context, 
            index_path=slash_repo_name, 
            query='repository', 
            limit=5, 
            threshold=0.0
        )
        
        assert search_slash_result['status'] == 'success', 'Search with slash name failed'
        assert 'results' in search_slash_result, 'No results field in search with slash name'
        
        # Test error handling
        with patch(
            'awslabs.git_repo_research_mcp_server.search.RepositorySearcher.search',
            side_effect=Exception('Test exception'),
        ):
            with pytest.raises(Exception) as excinfo:
                await mcp_search_repository(
                    test_context, 
                    index_path=repo_name, 
                    query='test', 
                    limit=5, 
                    threshold=0.0
                )
            assert 'Test exception' in str(excinfo.value)

        # Clean up
        await mcp_delete_repository(test_context, repository_name_or_path=repo_name)
        await mcp_delete_repository(test_context, repository_name_or_path='org_repo')


@pytest.mark.asyncio
async def test_mcp_search_github_repos(test_context):
    """Test searching for GitHub repositories."""
    # Mock the GitHub search function
    with patch(
        'awslabs.git_repo_research_mcp_server.server.github_repo_search_wrapper'
    ) as mock_search:
        # Configure the mock to return sample results
        mock_search.return_value = [
            {
                'url': 'https://github.com/awslabs/mcp',
                'title': 'awslabs/mcp',
                'description': 'Model Context Protocol',
                'organization': 'awslabs',
                'stars': 100,
                'updated_at': '2023-01-01T00:00:00Z',
                'language': 'Python',
                'topics': ['llm', 'ai'],
                'license': 'Apache License 2.0',
                'forks': 20,
                'open_issues': 5,
                'homepage': 'https://awslabs.github.io/mcp/',
            }
        ]

        # Test GitHub repository search
        search_result = await mcp_search_github_repos(
            test_context,
            keywords=['mcp', 'aws'],
            num_results=5,
        )
        
        assert search_result['status'] == 'success', 'GitHub search failed'
        assert 'results' in search_result, 'No results field in GitHub search response'
        assert len(search_result['results']) > 0, 'No GitHub search results found'
        assert search_result['results'][0]['url'] == 'https://github.com/awslabs/mcp', 'Wrong URL in GitHub search result'
        assert 'execution_time_ms' in search_result, 'No execution time in GitHub search response'
        
        # Test error handling
        mock_search.side_effect = Exception('Test exception')
        
        with pytest.raises(Exception) as excinfo:
            await mcp_search_github_repos(
                test_context,
                keywords=['mcp', 'aws'],
                num_results=5,
            )
        assert 'Test exception' in str(excinfo.value)


@pytest.mark.asyncio
async def test_mcp_access_file(test_context):
    """Test accessing files through the MCP tool."""
    # Mock the access_file_or_directory function
    with patch(
        'awslabs.git_repo_research_mcp_server.server.access_file_or_directory'
    ) as mock_access:
        # Test accessing a text file
        mock_access.return_value = "# Test Repository\n\nThis is a test repository."
        
        text_result = await mcp_access_file(
            test_context,
            filepath='test_repo/repository/README.md',
        )
        
        assert text_result['status'] == 'success', 'Text file access failed'
        assert text_result['type'] == 'text', 'Wrong type for text file'
        assert text_result['content'] == "# Test Repository\n\nThis is a test repository.", 'Wrong content for text file'
        
        # Test accessing a directory
        mock_access.return_value = json.dumps({
            'status': 'success',
            'type': 'directory',
            'path': 'test_repo/repository/src',
            'files': ['main.py', 'utils.py'],
        })
        
        dir_result = await mcp_access_file(
            test_context,
            filepath='test_repo/repository/src',
        )
        
        assert dir_result['status'] == 'success', 'Directory access failed'
        assert dir_result['type'] == 'directory', 'Wrong type for directory'
        assert 'files' in dir_result, 'No files field in directory result'
        
        # Test accessing an image file
        mock_access.return_value = Image(data=b'test image data', format='png')
        
        img_result = await mcp_access_file(
            test_context,
            filepath='test_repo/repository/images/test.png',
        )
        
        assert isinstance(img_result, dict), 'Image result is not converted to dict'
        assert img_result['type'] == 'image', 'Wrong type for image'
        
        # Test error handling
        mock_access.return_value = json.dumps({
            'status': 'error',
            'message': 'File not found',
        })
        
        error_result = await mcp_access_file(
            test_context,
            filepath='test_repo/repository/nonexistent.txt',
        )
        
        assert error_result['status'] == 'error', 'Error not reported for non-existent file'
        assert 'message' in error_result, 'No message field in error result'
        
        # Test exception handling
        mock_access.side_effect = Exception('Test exception')
        
        with pytest.raises(Exception) as excinfo:
            await mcp_access_file(
                test_context,
                filepath='test_repo/repository/README.md',
            )
        assert 'Test exception' in str(excinfo.value)


@pytest.mark.asyncio
async def test_mcp_delete_repository(test_context, test_git_repo, monkeypatch):
    """Test deleting a repository."""
    # Mock the Bedrock embeddings to avoid actual API calls
    with patch(
        'awslabs.git_repo_research_mcp_server.embeddings.BedrockEmbeddings'
    ) as mock_bedrock:
        # Configure the mock
        mock_embeddings = MagicMock()
        mock_embeddings.embed_query.return_value = [0.1] * 1536
        mock_embeddings.embed_documents.return_value = [[0.1] * 1536] * 10
        mock_bedrock.return_value = mock_embeddings

        # Use a unique name for the repository
        repo_name = f'{os.path.basename(test_git_repo)}'

        # Index the repository first
        await mcp_index_repository(
            test_context,
            repository_path=test_git_repo,
            output_path=None,
            embedding_model=EmbeddingModel.AMAZON_TITAN_EMBED_TEXT_V2,
            include_patterns=['**/*.md', '**/*.py'],
            exclude_patterns=['**/.git/**'],
            chunk_size=1000,
            chunk_overlap=200,
        )

        # Test deleting the repository
        delete_result = await mcp_delete_repository(
            test_context,
            repository_name_or_path=repo_name,
            index_directory=None,
        )
        
        assert delete_result['status'] == 'success', 'Repository deletion failed'
        assert delete_result['repository_name'] == repo_name, 'Wrong repository deleted'
        assert 'execution_time_ms' in delete_result, 'No execution time in delete response'
        
        # Test with repository name containing slashes (should be normalized)
        slash_repo_name = 'org/repo'
        
        # Index with slash name
        await mcp_index_repository(
            test_context,
            repository_path=test_git_repo,
            output_path=slash_repo_name,
            embedding_model=EmbeddingModel.AMAZON_TITAN_EMBED_TEXT_V2,
            include_patterns=['**/*.md'],
            exclude_patterns=['**/.git/**'],
            chunk_size=1000,
            chunk_overlap=200,
        )
        
        # Delete with slash name
        delete_slash_result = await mcp_delete_repository(
            test_context,
            repository_name_or_path=slash_repo_name,
            index_directory=None,
        )
        
        assert delete_slash_result['status'] == 'success', 'Repository deletion with slash name failed'
        
        # Test error handling - non-existent repository
        with patch(
            'awslabs.git_repo_research_mcp_server.utils.delete_indexed_repository',
            return_value={
                'status': 'error',
                'message': 'Repository not found',
            },
        ):
            delete_error_result = await mcp_delete_repository(
                test_context,
                repository_name_or_path='non_existent_repo',
                index_directory=None,
            )
            
            assert delete_error_result['status'] == 'error', 'Error not reported for non-existent repository'
            assert 'message' in delete_error_result, 'No message field in error result'
        
        # Test exception handling
        with patch(
            'awslabs.git_repo_research_mcp_server.utils.delete_indexed_repository',
            side_effect=Exception('Test exception'),
        ):
            with pytest.raises(Exception) as excinfo:
                await mcp_delete_repository(
                    test_context,
                    repository_name_or_path=repo_name,
                    index_directory=None,
                )
            assert 'Test exception' in str(excinfo.value)


def test_main():
    """Test the main function."""
    # Mock the argparse.ArgumentParser
    with patch('argparse.ArgumentParser.parse_args') as mock_parse_args, \
         patch('awslabs.git_repo_research_mcp_server.server.mcp.run') as mock_run:
        
        # Test with default arguments
        mock_parse_args.return_value = argparse.Namespace(sse=False, port=8888)
        main()
        mock_run.assert_called_once()
        
        # Reset mocks
        mock_run.reset_mock()
        
        # Test with SSE transport
        mock_parse_args.return_value = argparse.Namespace(sse=True, port=9999)
        main()
        assert mcp.settings.port == 9999, 'Port not set correctly'
        mock_run.assert_called_once_with(transport='sse')
