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

"""Tests for the indexer utility module."""

from awslabs.amazon_bedrock_agentcore_mcp_server.utils import indexer


class TestIndexer:
    """Test cases for the indexer functionality."""

    def test_doc_creation(self):
        """Test Doc dataclass creation and attributes."""
        # Arrange & Act
        doc = indexer.Doc(
            uri='https://example.com/doc',
            display_title='Test Document',
            content='This is test content',
            index_title='Test Document searchable',
        )

        # Assert
        assert doc.uri == 'https://example.com/doc'
        assert doc.display_title == 'Test Document'
        assert doc.content == 'This is test content'
        assert doc.index_title == 'Test Document searchable'

    def test_index_search_initialization(self):
        """Test IndexSearch initializes with empty state."""
        # Act
        index = indexer.IndexSearch()

        # Assert
        assert len(index.docs) == 0
        assert len(index.doc_frequency) == 0
        assert len(index.doc_indices) == 0

    def test_add_document_basic(self):
        """Test adding a basic document to the index."""
        # Arrange
        index = indexer.IndexSearch()
        doc = indexer.Doc(
            uri='https://example.com/doc',
            display_title='Test Document',
            content='This is test content with keywords',
            index_title='Test Document',
        )

        # Act
        index.add(doc)

        # Assert
        assert len(index.docs) == 1
        assert index.docs[0] == doc
        assert 'test' in index.doc_indices
        assert 'content' in index.doc_indices
        assert 'keywords' in index.doc_indices
        assert index.doc_frequency['test'] == 1

    def test_add_document_with_markdown_headers(self):
        """Test adding document with markdown headers gets proper weighting."""
        # Arrange
        index = indexer.IndexSearch()
        doc = indexer.Doc(
            uri='https://example.com/doc',
            display_title='Test Document',
            content='# Main Header\n\nThis is content.\n\n## Subheader\n\nMore content.',
            index_title='Test Document',
        )

        # Act
        index.add(doc)

        # Assert
        assert 'header' in index.doc_indices
        assert 'main' in index.doc_indices
        assert 'subheader' in index.doc_indices
        assert 0 in index.doc_indices['header']

    def test_add_document_with_code_blocks(self):
        """Test adding document with code blocks indexes code content."""
        # Arrange
        index = indexer.IndexSearch()
        doc = indexer.Doc(
            uri='https://example.com/doc',
            display_title='API Reference',
            content="Here's an example:\n\n```python\ndef hello_world():\n    return 'Hello'\n```\n\nAnd inline `code` too.",
            index_title='API Reference',
        )

        # Act
        index.add(doc)

        # Assert
        assert 'hello_world' in index.doc_indices
        assert 'python' in index.doc_indices
        assert 'code' in index.doc_indices
        assert 0 in index.doc_indices['hello_world']

    def test_add_document_with_links(self):
        """Test adding document with markdown links indexes link text."""
        # Arrange
        index = indexer.IndexSearch()
        doc = indexer.Doc(
            uri='https://example.com/doc',
            display_title='Documentation',
            content='See the [getting started guide](https://example.com/start) for more info.',
            index_title='Documentation',
        )

        # Act
        index.add(doc)

        # Assert
        assert 'getting' in index.doc_indices
        assert 'started' in index.doc_indices
        assert 'guide' in index.doc_indices
        assert 0 in index.doc_indices['getting']

    def test_add_multiple_documents(self):
        """Test adding multiple documents updates frequencies correctly."""
        # Arrange
        index = indexer.IndexSearch()
        doc1 = indexer.Doc('url1', 'Doc 1', 'test content', 'Doc 1')
        doc2 = indexer.Doc('url2', 'Doc 2', 'test example', 'Doc 2')

        # Act
        index.add(doc1)
        index.add(doc2)

        # Assert
        assert len(index.docs) == 2
        assert index.doc_frequency['test'] == 2  # appears in both docs
        assert index.doc_frequency['content'] == 1  # only in doc1
        assert index.doc_frequency['example'] == 1  # only in doc2
        assert len(index.doc_indices['test']) == 2  # both doc indices

    def test_search_empty_index(self):
        """Test searching empty index returns empty results."""
        # Arrange
        index = indexer.IndexSearch()

        # Act
        results = index.search('test query')

        # Assert
        assert results == []

    def test_search_single_document(self):
        """Test searching with single matching document."""
        # Arrange
        index = indexer.IndexSearch()
        doc = indexer.Doc(
            uri='https://example.com/doc',
            display_title='Test Document',
            content='This document contains test content about agents',
            index_title='Test Document',
        )
        index.add(doc)

        # Act
        results = index.search('test')

        # Assert
        assert len(results) == 1
        score, found_doc = results[0]
        assert found_doc == doc
        assert score > 0

    def test_search_multiple_documents_ranking(self):
        """Test search ranks documents by relevance."""
        # Arrange
        index = indexer.IndexSearch()

        # Document with term in title (should rank higher)
        doc1 = indexer.Doc('url1', 'Agent Guide', 'Basic content', 'Agent Guide')

        # Document with term only in content
        doc2 = indexer.Doc('url2', 'Tutorial', 'This is about agent development', 'Tutorial')

        # Document with no matching terms
        doc3 = indexer.Doc('url3', 'Other', 'Different topic entirely', 'Other')

        index.add(doc1)
        index.add(doc2)
        index.add(doc3)

        # Act
        results = index.search('agent')

        # Assert
        assert len(results) == 2  # doc3 shouldn't match

        # doc1 should rank higher (title match gets boost)
        scores = [score for score, _ in results]
        assert scores[0] > scores[1]

        # Verify correct documents returned
        returned_docs = [doc for _, doc in results]
        assert doc1 in returned_docs
        assert doc2 in returned_docs
        assert doc3 not in returned_docs

    def test_search_respects_k_limit(self):
        """Test search respects the k parameter for result limit."""
        # Arrange
        index = indexer.IndexSearch()

        # Add multiple documents with matching content
        for i in range(10):
            doc = indexer.Doc(f'url{i}', f'Doc {i}', 'test content', f'Doc {i}')
            index.add(doc)

        # Act
        results = index.search('test', k=3)

        # Assert
        assert len(results) <= 3

    def test_search_multi_token_query(self):
        """Test search with multiple tokens."""
        # Arrange
        index = indexer.IndexSearch()

        doc1 = indexer.Doc('url1', 'Agent Core', 'agent core functionality', 'Agent Core')
        doc2 = indexer.Doc('url2', 'Agent Guide', 'basic agent tutorial', 'Agent Guide')
        doc3 = indexer.Doc('url3', 'Core Concepts', 'core programming concepts', 'Core Concepts')

        index.add(doc1)
        index.add(doc2)
        index.add(doc3)

        # Act
        results = index.search('agent core')

        # Assert
        assert len(results) >= 1

        # doc1 should rank highest (has both terms)
        top_doc = results[0][1]
        assert top_doc == doc1

    def test_search_case_insensitive(self):
        """Test search is case insensitive."""
        # Arrange
        index = indexer.IndexSearch()
        doc = indexer.Doc('url', 'Title', 'Agent Core Development', 'Title')
        index.add(doc)

        # Act
        results_lower = index.search('agent')
        results_upper = index.search('AGENT')
        results_mixed = index.search('Agent')

        # Assert
        assert len(results_lower) == 1
        assert len(results_upper) == 1
        assert len(results_mixed) == 1
        assert results_lower[0][1] == doc
        assert results_upper[0][1] == doc
        assert results_mixed[0][1] == doc

    def test_title_boost_empty_content(self):
        """Test title boost is higher for documents with empty content."""
        # Arrange
        index = indexer.IndexSearch()

        # Document with empty content (not fetched yet)
        doc1 = indexer.Doc('url1', 'Agent Guide', '', 'Agent Guide')

        # Document with content but less relevant title
        doc2 = indexer.Doc(
            'url2', 'Tutorial', 'This tutorial covers agent development', 'Tutorial'
        )

        index.add(doc1)
        index.add(doc2)

        # Act
        results = index.search('agent')

        # Assert
        assert len(results) == 2

        # Both documents should be found
        found_docs = [doc for _, doc in results]
        assert doc1 in found_docs
        assert doc2 in found_docs

    def test_title_boost_short_vs_long_content(self):
        """Test title boost varies based on content length."""
        # Arrange
        index = indexer.IndexSearch()

        # Short content document
        short_content = 'Brief agent overview.'
        doc1 = indexer.Doc('url1', 'Agent', short_content, 'Agent Guide')

        # Long content document
        long_content = 'This is a very detailed agent development guide. ' * 50
        doc2 = indexer.Doc('url2', 'Tutorial', long_content, 'Agent Tutorial')

        index.add(doc1)
        index.add(doc2)

        # Act
        results = index.search('agent')

        # Assert
        assert len(results) == 2

        # Both should be found, but short content should get higher title boost
        scores = [score for score, _ in results]
        assert all(score > 0 for score in scores)
