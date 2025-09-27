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

"""Tests for the Amazon Bedrock AgentCore MCP Server."""

from awslabs.amazon_bedrock_agentcore_mcp_server.server import (
    fetch_agentcore_doc,
    search_agentcore_docs,
)
from awslabs.amazon_bedrock_agentcore_mcp_server.utils import cache, doc_fetcher, indexer
from unittest.mock import Mock, patch


class TestSearchDocs:
    """Test cases for the search_agentcore_docs tool."""

    @patch('awslabs.amazon_bedrock_agentcore_mcp_server.utils.cache.ensure_ready')
    @patch('awslabs.amazon_bedrock_agentcore_mcp_server.utils.cache.get_index')
    @patch('awslabs.amazon_bedrock_agentcore_mcp_server.utils.cache.get_url_cache')
    @patch('awslabs.amazon_bedrock_agentcore_mcp_server.utils.cache.ensure_page')
    def test_search_agentcore_docs_with_results(
        self, mock_ensure_page, mock_get_url_cache, mock_get_index, mock_ensure_ready
    ):
        """Test search_agentcore_docs returns properly formatted results."""
        # Arrange
        mock_doc = indexer.Doc(
            uri='https://example.com/doc1',
            display_title='Test Document',
            content='Test content',
            index_title='Test Document',
        )
        mock_index = Mock()
        mock_index.search.return_value = [(0.95, mock_doc)]
        mock_get_index.return_value = mock_index

        mock_page = doc_fetcher.Page(
            url='https://example.com/doc1',
            title='Test Document',
            content='Test content for snippet generation',
        )
        mock_url_cache = {'https://example.com/doc1': mock_page}
        mock_get_url_cache.return_value = mock_url_cache

        with patch(
            'awslabs.amazon_bedrock_agentcore_mcp_server.utils.text_processor.make_snippet'
        ) as mock_make_snippet:
            mock_make_snippet.return_value = 'Test snippet...'

            # Act
            result = search_agentcore_docs('bedrock agentcore', k=5)

            # Assert
            assert len(result) == 1
            assert result[0]['url'] == 'https://example.com/doc1'
            assert result[0]['title'] == 'Test Document'
            assert result[0]['score'] == 0.95
            assert result[0]['snippet'] == 'Test snippet...'
            mock_ensure_ready.assert_called_once()
            mock_index.search.assert_called_once_with('bedrock agentcore', k=5)

    @patch('awslabs.amazon_bedrock_agentcore_mcp_server.utils.cache.ensure_ready')
    @patch('awslabs.amazon_bedrock_agentcore_mcp_server.utils.cache.get_index')
    def test_search_agentcore_docs_no_index(self, mock_get_index, mock_ensure_ready):
        """Test search_agentcore_docs handles missing index gracefully."""
        # Arrange
        mock_get_index.return_value = None

        # Act
        result = search_agentcore_docs('test query')

        # Assert
        assert result == []
        mock_ensure_ready.assert_called_once()

    @patch('awslabs.amazon_bedrock_agentcore_mcp_server.utils.cache.ensure_ready')
    @patch('awslabs.amazon_bedrock_agentcore_mcp_server.utils.cache.get_index')
    @patch('awslabs.amazon_bedrock_agentcore_mcp_server.utils.cache.get_url_cache')
    def test_search_agentcore_docs_empty_results(
        self, mock_get_url_cache, mock_get_index, mock_ensure_ready
    ):
        """Test search_agentcore_docs handles empty search results."""
        # Arrange
        mock_index = Mock()
        mock_index.search.return_value = []
        mock_get_index.return_value = mock_index
        mock_get_url_cache.return_value = {}

        # Act
        result = search_agentcore_docs('nonexistent query')

        # Assert
        assert result == []

    @patch('awslabs.amazon_bedrock_agentcore_mcp_server.utils.cache.ensure_ready')
    @patch('awslabs.amazon_bedrock_agentcore_mcp_server.utils.cache.get_index')
    @patch('awslabs.amazon_bedrock_agentcore_mcp_server.utils.cache.get_url_cache')
    @patch('awslabs.amazon_bedrock_agentcore_mcp_server.utils.cache.ensure_page')
    def test_search_agentcore_docs_hydrates_top_results(
        self, mock_ensure_page, mock_get_url_cache, mock_get_index, mock_ensure_ready
    ):
        """Test search_agentcore_docs hydrates content for top results."""
        # Arrange
        docs = [
            indexer.Doc(
                uri=f'https://example.com/doc{i}',
                display_title=f'Doc {i}',
                content='',
                index_title=f'Doc {i}',
            )
            for i in range(10)
        ]
        mock_results = [(0.9 - i * 0.1, doc) for i, doc in enumerate(docs)]

        mock_index = Mock()
        mock_index.search.return_value = mock_results
        mock_get_index.return_value = mock_index

        mock_url_cache = {doc.uri: None for doc in docs}  # No content cached yet
        mock_get_url_cache.return_value = mock_url_cache

        with patch(
            'awslabs.amazon_bedrock_agentcore_mcp_server.utils.text_processor.make_snippet'
        ) as mock_make_snippet:
            mock_make_snippet.return_value = 'Test snippet'

            # Act
            result = search_agentcore_docs('test', k=10)

            # Assert
            # Should only hydrate top SNIPPET_HYDRATE_MAX results
            assert mock_ensure_page.call_count == min(len(docs), cache.SNIPPET_HYDRATE_MAX)
            assert len(result) == 10


class TestFetchDoc:
    """Test cases for the fetch_agentcore_doc tool."""

    @patch('awslabs.amazon_bedrock_agentcore_mcp_server.utils.cache.ensure_ready')
    @patch('awslabs.amazon_bedrock_agentcore_mcp_server.utils.cache.ensure_page')
    def test_fetch_agentcore_doc_success(self, mock_ensure_page, mock_ensure_ready):
        """Test fetch_agentcore_doc successfully retrieves document content."""
        # Arrange
        test_url = 'https://example.com/doc'
        mock_page = doc_fetcher.Page(
            url=test_url, title='Test Document', content='Full document content here'
        )
        mock_ensure_page.return_value = mock_page

        # Act
        result = fetch_agentcore_doc(test_url)

        # Assert
        assert result['url'] == test_url
        assert result['title'] == 'Test Document'
        assert result['content'] == 'Full document content here'
        assert 'error' not in result
        mock_ensure_ready.assert_called_once()
        mock_ensure_page.assert_called_once_with(test_url)

    @patch('awslabs.amazon_bedrock_agentcore_mcp_server.utils.cache.ensure_ready')
    @patch('awslabs.amazon_bedrock_agentcore_mcp_server.utils.cache.ensure_page')
    def test_fetch_agentcore_doc_failure(self, mock_ensure_page, mock_ensure_ready):
        """Test fetch_agentcore_doc handles fetch failures gracefully."""
        # Arrange
        test_url = 'https://example.com/nonexistent'
        mock_ensure_page.return_value = None

        # Act
        result = fetch_agentcore_doc(test_url)

        # Assert
        assert result['error'] == 'fetch failed'
        assert result['url'] == test_url
        assert 'title' not in result
        assert 'content' not in result

    @patch('awslabs.amazon_bedrock_agentcore_mcp_server.utils.cache.ensure_ready')
    @patch('awslabs.amazon_bedrock_agentcore_mcp_server.utils.cache.ensure_page')
    def test_fetch_agentcore_doc_http_url(self, mock_ensure_page, mock_ensure_ready):
        """Test fetch_agentcore_doc accepts HTTP URLs."""
        # Arrange
        test_url = 'http://example.com/doc'
        mock_page = doc_fetcher.Page(url=test_url, title='Test', content='Content')
        mock_ensure_page.return_value = mock_page

        # Act
        result = fetch_agentcore_doc(test_url)

        # Assert
        assert 'error' not in result
        assert result['url'] == test_url
        mock_ensure_page.assert_called_once_with(test_url)
