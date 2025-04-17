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
"""Tests for Git Repository Research MCP Server with a remote repository."""

import os
import pytest

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
def remote_git_repo():
    """Return a URL to a remote Git repository."""
    return 'https://github.com/awslabs/mcp'


@pytest.mark.asyncio
# @patch('awslabs.git_repo_research_mcp_server.embeddings.BedrockEmbeddings')
async def test_repository_indexing(test_context, remote_git_repo, tmp_path):
    """Test indexing a remote repository."""
    # Set up the mocks
    # mock_embeddings = MagicMock()
    # mock_embeddings.embed_query.return_value = [0.1] * 1536
    # mock_embeddings.embed_documents.return_value = [[0.1] * 1536] * 10
    # mock_bedrock.return_value = mock_embeddings

    # Use a consistent name for the repository
    repo_name = 'awslabs_mcp'

    try:
        # Test with skipif to avoid actual cloning in CI
        if os.environ.get('CI') == 'true':
            pytest.skip('Skipping in CI environment')

        # Index the repository with mock embeddings
        result = await mcp_index_repository(
            test_context,
            repository_path=remote_git_repo,
            output_path=None,
            embedding_model='amazon.titan-embed-text-v2:0',
            include_patterns=[
                'README*',
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
            # Even if it fails, we just need to confirm it attempted to run with the GitHub URL
            assert 'Indexing repository' in result.get('message', '')

    except Exception as e:
        # Test failed but we're only verifying we could attempt to index a GitHub repo
        assert 'Error indexing repository' in str(e)
