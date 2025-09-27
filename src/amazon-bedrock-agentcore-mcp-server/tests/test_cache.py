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

"""Tests for the cache utility module."""

from awslabs.amazon_bedrock_agentcore_mcp_server.utils import cache, doc_fetcher, indexer
from unittest.mock import Mock, patch


class TestCache:
    """Test cases for cache functionality."""

    def setup_method(self):
        """Reset cache state before each test."""
        cache._INDEX = None
        cache._URL_CACHE = {}
        cache._URL_TITLES = {}
        cache._LINKS_LOADED = False

    @patch('awslabs.amazon_bedrock_agentcore_mcp_server.utils.doc_fetcher.parse_llms_txt')
    @patch('awslabs.amazon_bedrock_agentcore_mcp_server.utils.text_processor.normalize')
    @patch('awslabs.amazon_bedrock_agentcore_mcp_server.utils.text_processor.index_title_variants')
    def test_load_links_only(self, mock_index_variants, mock_normalize, mock_parse_llms):
        """Test load_links_only initializes cache with document titles."""
        # Arrange
        mock_parse_llms.return_value = [
            ('AgentCore Overview', 'https://example.com/overview'),
            ('Getting Started', 'https://example.com/getting-started'),
        ]
        mock_normalize.side_effect = lambda x: x
        mock_index_variants.return_value = 'searchable title variants'

        # Act
        cache.load_links_only()

        # Assert
        assert cache._LINKS_LOADED is True
        assert cache._INDEX is not None
        assert len(cache._URL_TITLES) == 2
        assert cache._URL_TITLES['https://example.com/overview'] == 'AgentCore Overview'
        assert cache._URL_TITLES['https://example.com/getting-started'] == 'Getting Started'
        assert len(cache._URL_CACHE) == 2
        assert cache._URL_CACHE['https://example.com/overview'] is None
        assert cache._URL_CACHE['https://example.com/getting-started'] is None

    def test_ensure_ready_calls_load_links_only(self):
        """Test ensure_ready calls load_links_only when not loaded."""
        # Arrange
        assert cache._LINKS_LOADED is False

        with patch.object(cache, 'load_links_only') as mock_load:
            # Act
            cache.ensure_ready()

            # Assert
            mock_load.assert_called_once()

    def test_ensure_ready_skips_when_loaded(self):
        """Test ensure_ready skips loading when already loaded."""
        # Arrange
        cache._LINKS_LOADED = True

        with patch.object(cache, 'load_links_only') as mock_load:
            # Act
            cache.ensure_ready()

            # Assert
            mock_load.assert_not_called()

    @patch('awslabs.amazon_bedrock_agentcore_mcp_server.utils.doc_fetcher.fetch_and_clean')
    @patch('awslabs.amazon_bedrock_agentcore_mcp_server.utils.text_processor.format_display_title')
    def test_ensure_page_fetches_new_page(self, mock_format_title, mock_fetch):
        """Test ensure_page fetches and caches new pages."""
        # Arrange
        test_url = 'https://example.com/doc'
        mock_raw = doc_fetcher.Page(url=test_url, title='Raw Title', content='Content')
        mock_fetch.return_value = mock_raw
        mock_format_title.return_value = 'Formatted Title'

        # Act
        result = cache.ensure_page(test_url)

        # Assert
        assert result is not None
        assert result.url == test_url
        assert result.title == 'Formatted Title'
        assert result.content == 'Content'
        assert cache._URL_CACHE[test_url] == result
        mock_fetch.assert_called_once_with(test_url)

    def test_ensure_page_returns_cached(self):
        """Test ensure_page returns cached page without fetching."""
        # Arrange
        test_url = 'https://example.com/doc'
        cached_page = doc_fetcher.Page(url=test_url, title='Cached', content='Cached content')
        cache._URL_CACHE[test_url] = cached_page

        with patch(
            'awslabs.amazon_bedrock_agentcore_mcp_server.utils.doc_fetcher.fetch_and_clean'
        ) as mock_fetch:
            # Act
            result = cache.ensure_page(test_url)

            # Assert
            assert result == cached_page
            mock_fetch.assert_not_called()

    @patch('awslabs.amazon_bedrock_agentcore_mcp_server.utils.doc_fetcher.fetch_and_clean')
    def test_ensure_page_handles_fetch_error(self, mock_fetch):
        """Test ensure_page handles fetch errors gracefully."""
        # Arrange
        test_url = 'https://example.com/error'
        mock_fetch.side_effect = Exception('Network error')

        # Act
        result = cache.ensure_page(test_url)

        # Assert
        assert result is None

    def test_get_index_returns_current_index(self):
        """Test get_index returns the current index instance."""
        # Arrange
        mock_index = indexer.IndexSearch()
        cache._INDEX = mock_index

        # Act
        result = cache.get_index()

        # Assert
        assert result == mock_index

    def test_get_index_returns_none_when_not_loaded(self):
        """Test get_index returns None when index not loaded."""
        # Arrange
        cache._INDEX = None

        # Act
        result = cache.get_index()

        # Assert
        assert result is None

    def test_get_url_cache_returns_cache_dict(self):
        """Test get_url_cache returns the URL cache dictionary."""
        # Arrange
        test_cache = {'url1': None, 'url2': Mock()}
        cache._URL_CACHE = test_cache

        # Act
        result = cache.get_url_cache()

        # Assert
        assert result == test_cache

    def test_get_url_titles_returns_titles_dict(self):
        """Test get_url_titles returns the URL titles dictionary."""
        # Arrange
        test_titles = {'url1': 'Title 1', 'url2': 'Title 2'}
        cache._URL_TITLES = test_titles

        # Act
        result = cache.get_url_titles()

        # Assert
        assert result == test_titles
