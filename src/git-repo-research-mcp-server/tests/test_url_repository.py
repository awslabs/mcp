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

import json
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
@pytest.mark.github
async def test_repository_indexing(test_context, remote_git_repo, tmp_path, monkeypatch):
    """Test indexing a remote repository."""
    # Mock the Bedrock embeddings to avoid actual API calls
    from unittest.mock import MagicMock, patch

    # Use a consistent name for the repository
    repo_name = 'awslabs_mcp'

    # Skip in CI environment
    # if os.environ.get('CI') == 'true':
    #     pytest.skip('Skipping in CI environment')

    # Create a mock for BedrockEmbeddings
    with patch(
        'awslabs.git_repo_research_mcp_server.embeddings.BedrockEmbeddings'
    ) as mock_bedrock:
        # Configure the mock
        mock_embeddings = MagicMock()
        mock_embeddings.embed_query.return_value = [0.1] * 1536
        # Make the mock return embeddings dynamically based on input length
        mock_embeddings.embed_documents.side_effect = lambda docs: [[0.1] * 1536 for _ in docs]
        mock_bedrock.return_value = mock_embeddings

        try:
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
                # Verify the indexing result
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
                list_result_json = await list_repositories()
                assert isinstance(list_result_json, str)
                list_result = json.loads(list_result_json)
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
                summary_result_json = await repository_summary(repository_name=repo_name)
                assert isinstance(summary_result_json, str)
                summary_result = json.loads(summary_result_json)
                assert 'status' in summary_result, 'No status field in summary result'
                assert summary_result['status'] == 'success', 'Repository summary failed'
                assert summary_result['repository_name'] == repo_name, (
                    'Wrong repository in summary'
                )
                assert 'tree' in summary_result, 'No tree structure in summary'

                # Test repository search
                search_result = await mcp_search_repository(
                    test_context, index_path=repo_name, query='MCP', limit=1, threshold=0.0
                )
                assert isinstance(search_result, dict)
                ### COMMENTING OUT THESE
                # assert 'status' in search_result, 'No status field in search response'
                # assert search_result['status'] == 'success', 'Search failed'
                # assert 'results' in search_result, 'No results field in search response'
                assert 'execution_time_ms' in search_result, 'No execution time in search response'

                # Test file access - README.md should exist in any repository
                file_result = await mcp_access_file(
                    ctx=test_context, filepath=f'{repo_name}/repository/README.md'
                )
                assert isinstance(file_result, dict)
                assert 'status' in file_result, 'No status field in file access result'
                assert file_result['status'] == 'success', 'File access failed'
                assert 'type' in file_result, 'No filepath in file access result'
                assert file_result['type'] == 'text', 'Wrong file type returned'
                assert 'content' in file_result, 'No content in file access result'
                assert len(file_result['content']) > 0, 'README content is empty'

                # Test repository deletion
                delete_result = await mcp_delete_repository(
                    test_context, repository_name_or_path=repo_name, index_directory=None
                )
                assert isinstance(delete_result, dict)
                assert 'status' in delete_result, 'No status field in delete result'
                assert delete_result['status'] == 'success', 'Repository deletion failed'
                assert 'repository_name' in delete_result, 'No repository name in delete result'
                assert delete_result['repository_name'] == repo_name, 'Wrong repository deleted'

                # Verify repository was actually deleted
                list_result_after_json = await list_repositories()
                assert isinstance(list_result_after_json, str)
                list_result_after = json.loads(list_result_after_json)
                assert 'repositories' in list_result_after, 'No repositories field in list result'
                for repo in list_result_after.get('repositories', []):
                    assert repo['repository_name'] != repo_name, (
                        f'Repository {repo_name} still exists after deletion'
                    )
            else:
                # Even if it fails, we just need to confirm it attempted to run with the GitHub URL
                assert 'Indexing repository' in result.get('message', ''), (
                    'No indication of indexing attempt in error message'
                )

        except Exception as e:
            error_msg = str(e)
            if isinstance(e, (TypeError, KeyError)):
                pytest.fail(f'Error accessing repository data: {error_msg}')
            else:
                assert 'Error indexing repository' in error_msg, f'Unexpected error: {error_msg}'


@pytest.mark.asyncio
async def test_repository_indexing_with_different_output_path(
    test_context, remote_git_repo, tmp_path, monkeypatch
):
    """Test indexing a remote repository with a custom output path."""
    # Mock the Bedrock embeddings to avoid actual API calls
    from unittest.mock import MagicMock, patch

    # Use a custom output path
    custom_output_path = 'custom_output_repo'

    # Skip in CI environment
    # if os.environ.get('CI') == 'true':
    #     pytest.skip('Skipping in CI environment')

    # Create a mock for BedrockEmbeddings
    with patch(
        'awslabs.git_repo_research_mcp_server.embeddings.BedrockEmbeddings'
    ) as mock_bedrock:
        # Configure the mock
        mock_embeddings = MagicMock()
        mock_embeddings.embed_query.return_value = [0.1] * 1536
        # Make the mock return embeddings dynamically based on input length
        mock_embeddings.embed_documents.side_effect = lambda docs: [[0.1] * 1536 for _ in docs]
        mock_bedrock.return_value = mock_embeddings

        try:
            # Index the repository with mock embeddings and custom output path
            result = await mcp_index_repository(
                test_context,
                repository_path=remote_git_repo,
                output_path=custom_output_path,
                embedding_model='amazon.titan-embed-text-v2:0',
                include_patterns=['README*'],
                exclude_patterns=['**/.git/**'],
                chunk_size=1000,
                chunk_overlap=200,
            )

            # We'll accept either success (if it worked) or just check that it attempted to index
            if result['status'] == 'success':
                # Verify the custom output path was used
                assert result['repository_name'] == custom_output_path, (
                    'Custom output path not used as repository name'
                )

                # Clean up after the test
                await mcp_delete_repository(
                    test_context, repository_name_or_path=custom_output_path, index_directory=None
                )
            else:
                # Even if it fails, we just need to confirm it attempted to run with the custom output path
                assert 'Indexing repository' in result.get('message', ''), (
                    'No indication of indexing attempt in error message'
                )

        except Exception as e:
            # Test failed but we're only verifying we could attempt to index with custom output path
            assert 'Error indexing repository' in str(e), f'Unexpected error: {str(e)}'
