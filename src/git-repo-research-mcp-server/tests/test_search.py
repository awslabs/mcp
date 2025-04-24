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
"""Tests for the search functionality in Git Repository Research MCP Server."""

import pytest
from awslabs.git_repo_research_mcp_server.models import (
    SearchResponse,
)
from awslabs.git_repo_research_mcp_server.search import (
    RepositorySearcher,
    get_repository_searcher,
)
from unittest.mock import MagicMock, patch


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
def mock_embedding_generator():
    """Create a mock embedding generator."""
    mock_generator = MagicMock()
    mock_generator.embed_query.return_value = [0.1] * 1536
    mock_generator.embed_documents.side_effect = lambda docs: [[0.1] * 1536 for _ in docs]
    return mock_generator


@pytest.fixture
def mock_repository_indexer():
    """Create a mock repository indexer."""
    mock_indexer = MagicMock()
    return mock_indexer


def test_get_repository_searcher():
    """Test the get_repository_searcher function."""
    with patch('awslabs.git_repo_research_mcp_server.search.RepositorySearcher') as mock_searcher:
        # Configure the mock
        mock_searcher_instance = MagicMock()
        mock_searcher.return_value = mock_searcher_instance

        # Call the function
        searcher = get_repository_searcher(
            embedding_model='test-model',
            aws_region='us-west-2',
            aws_profile='default',
            index_dir='/tmp/index',
        )

        # Verify the result
        assert searcher == mock_searcher_instance
        mock_searcher.assert_called_once_with(
            embedding_model='test-model',
            aws_region='us-west-2',
            aws_profile='default',
            index_dir='/tmp/index',
        )


def test_repository_searcher_init():
    """Test the RepositorySearcher initialization."""
    with (
        patch(
            'awslabs.git_repo_research_mcp_server.search.get_embedding_generator'
        ) as mock_get_embedding,
        patch(
            'awslabs.git_repo_research_mcp_server.search.get_repository_indexer'
        ) as mock_get_indexer,
        patch('os.path.expanduser') as mock_expanduser,
    ):
        # Configure the mocks
        mock_embedding = MagicMock()
        mock_get_embedding.return_value = mock_embedding

        mock_indexer = MagicMock()
        mock_get_indexer.return_value = mock_indexer

        mock_expanduser.return_value = '/home/user/.git_repo_research'

        # Create a RepositorySearcher instance
        searcher = RepositorySearcher(
            embedding_model='test-model',
            aws_region='us-west-2',
            aws_profile='default',
            index_dir='/tmp/index',
        )

        # Verify the initialization
        assert searcher.embedding_model == 'test-model'
        assert searcher.aws_region == 'us-west-2'
        assert searcher.aws_profile == 'default'
        assert searcher.index_dir == '/tmp/index'
        assert searcher.embedding_generator == mock_embedding
        assert searcher.repository_indexer == mock_indexer

        # Verify the mock calls
        mock_get_embedding.assert_called_once_with(
            model_id='test-model',
            aws_region='us-west-2',
            aws_profile='default',
        )

        mock_get_indexer.assert_called_once()


def test_list_repository_files_success():
    """Test the list_repository_files method with a successful case."""
    with (
        patch('awslabs.git_repo_research_mcp_server.search.get_embedding_generator'),
        patch('awslabs.git_repo_research_mcp_server.search.get_repository_indexer'),
        patch('os.path.exists') as mock_exists,
        patch('os.path.isdir') as mock_isdir,
        patch('os.listdir') as mock_listdir,
    ):
        # Configure the mocks
        mock_indexer = MagicMock()
        mock_indexer._get_index_path.return_value = '/tmp/index/test_repo'

        mock_exists.return_value = True
        mock_isdir.return_value = True

        # Mock directory structure
        mock_listdir.side_effect = lambda path: {
            '/tmp/index/test_repo/repository': ['src', 'README.md'],
            '/tmp/index/test_repo/repository/src': ['main.py', 'utils.py'],
        }[path]

        # Create a RepositorySearcher instance with the mock indexer
        searcher = RepositorySearcher()
        searcher.repository_indexer = mock_indexer

        # Mock the _generate_directory_tree method
        searcher._generate_directory_tree = MagicMock(return_value='Directory tree')

        # Call the method
        result = searcher.list_repository_files('test_repo')

        # Verify the result
        assert result == 'Directory tree'
        mock_indexer._get_index_path.assert_called_once_with('test_repo')
        searcher._generate_directory_tree.assert_called_once_with(
            '/tmp/index/test_repo/repository'
        )


def test_list_repository_files_not_found():
    """Test the list_repository_files method when the repository is not found."""
    with (
        patch('awslabs.git_repo_research_mcp_server.search.get_embedding_generator'),
        patch('awslabs.git_repo_research_mcp_server.search.get_repository_indexer'),
        patch('os.path.exists') as mock_exists,
        patch('loguru.logger.warning') as mock_logger_warning,
    ):
        # Configure the mocks
        mock_indexer = MagicMock()
        mock_indexer._get_index_path.return_value = '/tmp/index/test_repo'

        mock_exists.return_value = False

        # Create a RepositorySearcher instance with the mock indexer
        searcher = RepositorySearcher()
        searcher.repository_indexer = mock_indexer

        # Call the method
        result = searcher.list_repository_files('test_repo')

        # Verify the result
        assert result is None
        mock_indexer._get_index_path.assert_called_once_with('test_repo')
        mock_logger_warning.assert_called_once()


def test_list_repository_files_exception():
    """Test the list_repository_files method when an exception occurs."""
    with (
        patch('awslabs.git_repo_research_mcp_server.search.get_embedding_generator'),
        patch('awslabs.git_repo_research_mcp_server.search.get_repository_indexer'),
        patch('os.path.exists') as mock_exists,
        patch('os.path.isdir') as mock_isdir,
        patch('loguru.logger.error') as mock_logger_error,
    ):
        # Configure the mocks
        mock_indexer = MagicMock()
        mock_indexer._get_index_path.return_value = '/tmp/index/test_repo'

        mock_exists.return_value = True
        mock_isdir.return_value = True

        # Create a RepositorySearcher instance with the mock indexer
        searcher = RepositorySearcher()
        searcher.repository_indexer = mock_indexer

        # Mock the _generate_directory_tree method to raise an exception
        searcher._generate_directory_tree = MagicMock(side_effect=Exception('Test exception'))

        # Call the method
        result = searcher.list_repository_files('test_repo')

        # Verify the result
        assert result is None
        mock_indexer._get_index_path.assert_called_once_with('test_repo')
        mock_logger_error.assert_called_once()


def test_generate_directory_tree():
    """Test the _generate_directory_tree method."""
    with (
        patch('awslabs.git_repo_research_mcp_server.search.get_embedding_generator'),
        patch('awslabs.git_repo_research_mcp_server.search.get_repository_indexer'),
        patch('os.path.basename') as mock_basename,
    ):
        # Configure the mocks
        mock_basename.return_value = 'test_repo'

        # Create a RepositorySearcher instance
        searcher = RepositorySearcher()

        # Mock the _generate_tree method
        searcher._generate_tree = MagicMock(return_value='    └── file.txt\n')

        # Call the method
        result = searcher._generate_directory_tree('/tmp/index/test_repo')

        # Verify the result
        assert result == 'Directory structure:\n└── test_repo/\n    └── file.txt\n'
        mock_basename.assert_called_once_with('/tmp/index/test_repo')
        searcher._generate_tree.assert_called_once_with('/tmp/index/test_repo', '', 'test_repo')


def test_search_with_repository_name():
    """Test the search method with a repository name."""
    with (
        patch('awslabs.git_repo_research_mcp_server.search.get_embedding_generator'),
        patch('awslabs.git_repo_research_mcp_server.search.get_repository_indexer'),
        patch('os.path.exists') as mock_exists,
        patch('os.path.isdir') as mock_isdir,
        patch('time.time') as mock_time,
    ):
        # Configure the mocks
        mock_time.side_effect = [1000.0, 1001.0]  # Start and end times
        mock_exists.return_value = False  # Not a directory path
        mock_isdir.return_value = True

        mock_indexer = MagicMock()
        mock_indexer._get_index_path.return_value = '/tmp/index/test_repo'

        # Create mock vector store and chunk map
        mock_vector_store = MagicMock()
        mock_chunk_map = {}

        # Configure the mock vector store to return search results
        mock_doc1 = MagicMock()
        mock_doc1.page_content = 'Test content 1'
        mock_doc1.metadata = {'source': '/path/to/file1.txt', 'chunk_id': '1'}

        mock_doc2 = MagicMock()
        mock_doc2.page_content = 'Test content 2'
        mock_doc2.metadata = {'source': '/path/to/file2.txt', 'chunk_id': '2'}

        mock_vector_store.similarity_search.return_value = [mock_doc1, mock_doc2]
        mock_vector_store.docstore._dict = {1: mock_doc1, 2: mock_doc2}

        mock_indexer.load_index.return_value = (mock_vector_store, mock_chunk_map)

        # Create a RepositorySearcher instance with the mock indexer
        searcher = RepositorySearcher()
        searcher.repository_indexer = mock_indexer

        # Call the method
        result = searcher.search('test_repo', 'test query', limit=10, threshold=0.0)

        # Verify the result
        assert isinstance(result, SearchResponse)
        assert result.query == 'test query'
        assert result.index_path == '/tmp/index/test_repo'
        assert result.repository_name == 'test_repo'
        assert result.repository_directory == '/tmp/index/test_repo/repository'
        assert result.total_results == 2
        assert result.execution_time_ms == 1000

        assert result is not None
        assert result.results is not None
        assert len(result.results) > 0

        # Verify first result
        first_result = result.results[0]
        assert first_result is not None
        assert first_result.file_path == '/path/to/file1.txt'
        assert first_result.content == 'Test content 1'
        assert first_result.score == 1.0
        assert first_result.metadata is not None
        assert first_result.metadata['chunk_id'] == '1'

        # Verify second result
        second_result = result.results[1]
        assert second_result is not None
        assert second_result.file_path == '/path/to/file2.txt'
        assert second_result.content == 'Test content 2'
        assert second_result.score == 1.0
        assert second_result.metadata is not None
        assert second_result.metadata['chunk_id'] == '2'

        # Verify the mock calls
        mock_indexer._get_index_path.assert_called_once_with('test_repo')
        mock_indexer.load_index.assert_called_once_with('test_repo')
        mock_vector_store.similarity_search.assert_called_once_with('test query', k=10)


def test_search_with_directory_path():
    """Test the search method with a directory path."""
    with (
        patch('awslabs.git_repo_research_mcp_server.search.get_embedding_generator'),
        patch('awslabs.git_repo_research_mcp_server.search.get_repository_indexer'),
        patch('os.path.exists') as mock_exists,
        patch('os.path.isdir') as mock_isdir,
        patch('os.path.basename') as mock_basename,
        patch('time.time') as mock_time,
    ):
        # Configure the mocks
        mock_time.side_effect = [1000.0, 1001.0]  # Start and end times
        mock_exists.return_value = True  # It's a directory path
        mock_isdir.return_value = True
        mock_basename.return_value = 'test_repo'

        mock_indexer = MagicMock()

        # Create mock vector store and chunk map
        mock_vector_store = MagicMock()
        mock_chunk_map = {}

        # Configure the mock vector store to return search results
        mock_doc1 = MagicMock()
        mock_doc1.page_content = 'Test content 1'
        mock_doc1.metadata = {'source': '/path/to/file1.txt', 'chunk_id': '1'}

        mock_vector_store.similarity_search.return_value = [mock_doc1]
        mock_vector_store.docstore._dict = {1: mock_doc1}

        mock_indexer.load_index.return_value = (mock_vector_store, mock_chunk_map)

        # Create a RepositorySearcher instance with the mock indexer
        searcher = RepositorySearcher()
        searcher.repository_indexer = mock_indexer

        # Call the method
        result = searcher.search('/tmp/index/test_repo', 'test query', limit=10, threshold=0.0)

        # Verify the result
        assert isinstance(result, SearchResponse)
        assert result.query == 'test query'
        assert result.index_path == '/tmp/index/test_repo'
        assert result.repository_name == 'test_repo'
        assert result.repository_directory == '/tmp/index/test_repo/repository'
        assert result.total_results == 1
        assert result.execution_time_ms == 1000

        assert len(result.results) == 1
        assert result.results[0].file_path == '/path/to/file1.txt'
        assert result.results[0].content == 'Test content 1'
        assert result.results[0].score == 1.0

        # Verify the mock calls
        mock_indexer.load_index.assert_called_once_with('test_repo')


def test_search_with_similarity_search_with_score_fallback():
    """Test the search method with similarity_search_with_score fallback."""
    with (
        patch('awslabs.git_repo_research_mcp_server.search.get_embedding_generator'),
        patch('awslabs.git_repo_research_mcp_server.search.get_repository_indexer'),
        patch('os.path.exists') as mock_exists,
        patch('os.path.isdir') as mock_isdir,
        patch('time.time') as mock_time,
        patch('loguru.logger.error') as mock_logger_error,
    ):
        # Configure the mocks
        mock_time.side_effect = [1000.0, 1001.0]  # Start and end times
        mock_exists.return_value = False  # Not a directory path
        mock_isdir.return_value = True

        mock_indexer = MagicMock()
        mock_indexer._get_index_path.return_value = '/tmp/index/test_repo'

        # Create mock vector store and chunk map
        mock_vector_store = MagicMock()
        mock_chunk_map = {}

        # Configure the mock vector store to fail with similarity_search but succeed with similarity_search_with_score
        mock_vector_store.similarity_search.side_effect = Exception('Test exception')

        mock_doc1 = MagicMock()
        mock_doc1.page_content = 'Test content 1'
        mock_doc1.metadata = {'source': '/path/to/file1.txt', 'chunk_id': '1'}

        mock_vector_store.similarity_search_with_score.return_value = [(mock_doc1, 0.5)]
        mock_vector_store.docstore._dict = {1: mock_doc1}

        mock_indexer.load_index.return_value = (mock_vector_store, mock_chunk_map)

        # Create a RepositorySearcher instance with the mock indexer
        searcher = RepositorySearcher()
        searcher.repository_indexer = mock_indexer

        # Call the method
        result = searcher.search('test_repo', 'test query', limit=10, threshold=0.0)

        # Verify the result
        assert isinstance(result, SearchResponse)
        assert result.query == 'test query'
        assert result.index_path == '/tmp/index/test_repo'
        assert result.repository_name == 'test_repo'
        assert result.repository_directory == '/tmp/index/test_repo/repository'
        assert result.total_results == 1
        assert result.execution_time_ms == 1000

        assert len(result.results) == 1
        assert result.results[0].file_path == '/path/to/file1.txt'
        assert result.results[0].content == 'Test content 1'
        assert result.results[0].score == 0.75  # 1.0 - min(1.0, 0.5/2.0)

        # Verify the mock calls
        mock_indexer._get_index_path.assert_called_once_with('test_repo')
        mock_indexer.load_index.assert_called_once_with('test_repo')
        mock_vector_store.similarity_search.assert_called_once_with('test query', k=10)
        mock_vector_store.similarity_search_with_score.assert_called_once_with('test query', k=10)
        mock_logger_error.assert_called_once()


def test_search_with_both_search_methods_failing():
    """Test the search method when both similarity search methods fail."""
    with (
        patch('awslabs.git_repo_research_mcp_server.search.get_embedding_generator'),
        patch('awslabs.git_repo_research_mcp_server.search.get_repository_indexer'),
        patch('os.path.exists') as mock_exists,
        patch('os.path.isdir') as mock_isdir,
        patch('time.time') as mock_time,
    ):
        # Configure the mocks
        mock_time.side_effect = [1000.0, 1001.0]  # Start and end times
        mock_exists.return_value = False  # Not a directory path
        mock_isdir.return_value = True

        mock_indexer = MagicMock()
        mock_indexer._get_index_path.return_value = '/tmp/index/test_repo'

        # Create mock vector store and chunk map
        mock_vector_store = MagicMock()
        mock_chunk_map = {}

        # Configure the mock vector store to fail with both search methods
        mock_vector_store.similarity_search.side_effect = Exception('Test exception 1')
        mock_vector_store.similarity_search_with_score.side_effect = Exception('Test exception 2')
        mock_vector_store.docstore._dict = {1: MagicMock()}

        mock_indexer.load_index.return_value = (mock_vector_store, mock_chunk_map)

        # Create a RepositorySearcher instance with the mock indexer
        searcher = RepositorySearcher()
        searcher.repository_indexer = mock_indexer

        # Call the method
        result = searcher.search('test_repo', 'test query', limit=10, threshold=0.0)

        # Verify the result
        assert isinstance(result, SearchResponse)
        assert result.query == 'test query'
        assert result.index_path == '/tmp/index/test_repo'
        assert result.repository_name == 'test_repo'
        assert result.repository_directory == '/tmp/index/test_repo/repository'
        assert result.total_results == 0
        assert result.execution_time_ms == 1000
        assert len(result.results) == 0

        # Verify the mock calls
        mock_indexer._get_index_path.assert_called_once_with('test_repo')
