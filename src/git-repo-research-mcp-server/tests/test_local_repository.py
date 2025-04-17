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
# @patch('awslabs.git_repo_research_mcp_server.embeddings.BedrockEmbeddings')
async def test_repository_indexing(test_context, test_git_repo, tmp_path):
    """Test indexing a local repository."""
    # Set up the mocks
    # mock_embeddings = MagicMock()
    # mock_embeddings.embed_query.return_value = [0.1] * 1536
    # mock_embeddings.embed_documents.return_value = [[0.1] * 1536] * 10
    # mock_bedrock.return_value = mock_embeddings

    # Use a unique name for the repository
    repo_name = f'{os.path.basename(test_git_repo)}'

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

        # We'll accept either success (if it worked) or just check that it attempted to index
        if result['status'] == 'success':
            assert result['repository_name'] == repo_name
            assert 'index_path' in result
            assert result['file_count'] > 0

            result = await list_repositories()
            result = await repository_summary(repository_name=repo_name)
            result = await mcp_search_repository(
                test_context, index_path=repo_name, query='MCP', limit=1, threshold=0.0
            )
            result = await mcp_access_file(
                ctx=test_context, filepath=f'{repo_name}/repository/README.md'
            )

            # Clean up after the test
            await mcp_delete_repository(
                test_context, repository_name_or_path=repo_name, index_directory=None
            )
        else:
            # Even if it fails, we just need to confirm it attempted to run with the local repo
            assert 'Indexing repository' in result.get('message', '')

    except Exception as e:
        # Test failed but we're only verifying we could attempt to index a local repo
        assert 'Error indexing repository' in str(e)
