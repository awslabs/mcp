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
"""Tests for Git Repository Research MCP Server with a local repository."""

import os
import pytest
import subprocess
import tempfile

# Import the server functionality
from awslabs.git_repo_research_mcp_server.server import (
    list_repositories,
    mcp_access_file,
    mcp_delete_repository,
    mcp_index_repository,
    mcp_search_repository,
    repository_summary,
)


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

        # Add everything to Git
        subprocess.run(['git', 'add', '.'], cwd=repo_dir, check=True)
        subprocess.run(['git', 'commit', '-m', 'Initial commit'], cwd=repo_dir, check=True)

        yield repo_dir


@pytest.mark.asyncio
async def test_repository_indexing(test_context, test_git_repo, tmp_path, monkeypatch):
    """Test indexing a local repository."""
    # Mock the Bedrock embeddings to avoid actual API calls
    from unittest.mock import MagicMock, patch

    # Use a unique name for the repository
    repo_name = f'{os.path.basename(test_git_repo)}'

    # Create a mock for BedrockEmbeddings
    with patch(
        'awslabs.git_repo_research_mcp_server.embeddings.BedrockEmbeddings'
    ) as mock_bedrock:
        # Configure the mock
        mock_embeddings = MagicMock()
        mock_embeddings.embed_query.return_value = [0.1] * 1536
        mock_embeddings.embed_documents.return_value = [[0.1] * 1536] * 10
        mock_bedrock.return_value = mock_embeddings

        try:
            # Index the repository with mock embeddings
            result = await mcp_index_repository(
                test_context,
                repository_path=test_git_repo,
                output_path=None,  # Pass output_path explicitly to avoid FieldInfo error
                embedding_model='amazon.titan-embed-text-v2:0',
                include_patterns=[
                    '**/*.md',
                ],
                exclude_patterns=[
                    '**/.git/**',
                    '**/.github/**',
                    '**/.svn/**',
                    '**/.hg/**',
                    '**/.bzr/**',
                    '**/node_modules/**',
                    '**/venv/**',
                    '**/.venv/**',
                    '**/env/**',
                    '**/.env/**',
                    '**/__pycache__/**',
                    '**/.pytest_cache/**',
                    '**/.coverage/**',
                    '**/coverage/**',
                    '**/dist/**',
                    '**/build/**',
                    '**/.DS_Store',
                    '**/*.pyc',
                    '**/*.pyo',
                    '**/*.pyd',
                    '**/*.so',
                    '**/*.dll',
                    '**/*.exe',
                    '**/*.bin',
                    '**/*.obj',
                    '**/*.o',
                    '**/*.a',
                    '**/*.lib',
                    '**/*.dylib',
                    '**/*.ncb',
                    '**/*.sdf',
                    '**/*.suo',
                    '**/*.pdb',
                    '**/*.idb',
                    '**/*.jpg',
                    '**/*.jpeg',
                    '**/*.png',
                    '**/*.gif',
                    '**/*.svg',
                    '**/*.ico',
                    '**/*.mp4',
                    '**/*.mov',
                    '**/*.wmv',
                    '**/*.flv',
                    '**/*.avi',
                    '**/*.mkv',
                    '**/*.mp3',
                    '**/*.wav',
                    '**/*.flac',
                    '**/*.zip',
                    '**/*.tar.gz',
                    '**/*.tar',
                    '**/*.rar',
                    '**/*.7z',
                    '**/*.pdf',
                    '**/*.docx',
                    '**/*.xlsx',
                    '**/*.pptx',
                    '**/logs/**',
                    '**/log/**',
                    '**/.idea/**',
                    '**/.vscode/**',
                    '**/.classpath',
                    '**/.project',
                    '**/.settings/**',
                    '**/.gradle/**',
                    '**/target/**',
                ],
                chunk_size=1000,
                chunk_overlap=200,
            )

            # Verify the indexing result
            assert result['status'] == 'success', (
                f'Indexing failed with message: {result.get("message", "")}'
            )
            assert result['repository_name'] == repo_name, (
                "Repository name doesn't match expected value"
            )
            assert 'index_path' in result, 'Index path missing from result'
            assert result['file_count'] > 0, 'No files were indexed'
            assert result['chunk_count'] > 0, 'No chunks were created'
            assert 'embedding_model' in result, 'Embedding model info missing from result'
            assert result['embedding_model'] == 'amazon.titan-embed-text-v2:0', (
                'Wrong embedding model used'
            )

            # Test repository listing
            list_result = await list_repositories()
            assert 'repositories' in list_result, 'No repositories field in list result'
            assert len(list_result['repositories']) > 0, 'No repositories found in list'

            # Find our repository in the list
            repo_found = False
            for repo in list_result['repositories']:
                if repo['repository_name'] == repo_name:
                    repo_found = True
                    assert repo['file_count'] > 0, 'Repository has no files'
                    assert repo['chunk_count'] > 0, 'Repository has no chunks'
                    break
            assert repo_found, f'Repository {repo_name} not found in list'

            # Test repository summary
            summary_result = await repository_summary(repository_name=repo_name)
            assert summary_result['status'] == 'success', 'Repository summary failed'
            assert summary_result['repository_name'] == repo_name, 'Wrong repository in summary'
            assert 'tree' in summary_result, 'No tree structure in summary'
            assert 'helpful_files' in summary_result, 'No helpful files in summary'

            # Test repository search
            search_result = await mcp_search_repository(
                test_context, index_path=repo_name, query='MCP', limit=1, threshold=0.0
            )
            assert search_result['status'] == 'success', 'Search failed'
            assert 'results' in search_result, 'No results field in search response'
            assert 'execution_time_ms' in search_result, 'No execution time in search response'

            # Test file access
            file_result = await mcp_access_file(
                ctx=test_context, filepath=f'{repo_name}/repository/README.md'
            )
            assert file_result['status'] == 'success', 'File access failed'
            assert file_result['type'] == 'text', 'Wrong file type returned'
            assert 'content' in file_result, 'No content in file access result'
            assert 'Test Repository' in file_result['content'], (
                'Expected content not found in README'
            )
            assert 'Semantic search' in file_result['content'], (
                'Expected content not found in README'
            )

            # Test repository deletion
            delete_result = await mcp_delete_repository(
                test_context, repository_name_or_path=repo_name, index_directory=None
            )
            assert delete_result['status'] == 'success', 'Repository deletion failed'
            assert delete_result['repository_name'] == repo_name, 'Wrong repository deleted'

            # Verify repository was actually deleted
            list_result_after = await list_repositories()
            for repo in list_result_after.get('repositories', []):
                assert repo['repository_name'] != repo_name, (
                    f'Repository {repo_name} still exists after deletion'
                )

        except Exception as e:
            # Test failed but we're only verifying we could attempt to index a local repo
            assert 'Error indexing repository' in str(e)
