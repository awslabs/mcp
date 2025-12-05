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

"""Tests for the Search functionality in the valkey MCP server."""

import pytest
import struct
from awslabs.valkey_mcp_server.tools.vss import vector_search
from unittest.mock import Mock, patch
from valkey.exceptions import ValkeyError


class TestSearch:
    """Tests for Search operations."""

    @pytest.fixture
    def mock_connection(self):
        """Create a mock Valkey connection."""
        with patch('awslabs.valkey_mcp_server.tools.vss.ValkeyConnectionManager') as mock_manager:
            mock_conn = Mock()
            mock_manager.get_connection.return_value = mock_conn
            yield mock_conn

    @pytest.mark.asyncio
    async def test_vector_search_successful(self, mock_connection):
        """Test successful vector search."""
        mock_conn = mock_connection

        index = 'test_index'
        field = 'embedding'
        vector = [0.1, 0.2, 0.3, 0.4]
        count = 5

        # Create mock documents with document_json field
        doc1_fields = {b'document_json': b'{"id": "doc1", "title": "First Document", "content": "This is the first document content", "author": "Alice"}'}
        doc2_fields = {b'document_json': b'{"id": "doc2", "title": "Second Document", "content": "This is the second document content", "author": "Bob"}'}

        # Create mock search result
        mock_doc1 = Mock()
        mock_doc1.id = 'doc1'

        mock_doc2 = Mock()
        mock_doc2.id = 'doc2'

        mock_result = Mock()
        mock_result.total = 2
        mock_result.docs = [mock_doc1, mock_doc2]

        # Setup mock search interface
        mock_ft = Mock()
        mock_ft.search.return_value = mock_result
        mock_conn.ft.return_value = mock_ft

        # Setup mock connection to return document fields
        mock_conn.hgetall.side_effect = [doc1_fields, doc2_fields]

        # Execute search
        result = await vector_search(index, field, vector, offset=0, count=count)

        # Verify results
        assert isinstance(result, list)
        assert len(result) == 2

        # Verify first document
        assert result[0]['id'] == 'doc1'
        assert result[0]['title'] == 'First Document'
        assert result[0]['content'] == 'This is the first document content'
        assert result[0]['author'] == 'Alice'

        # Verify second document
        assert result[1]['id'] == 'doc2'
        assert result[1]['title'] == 'Second Document'
        assert result[1]['content'] == 'This is the second document content'
        assert result[1]['author'] == 'Bob'

        # Verify correct method calls
        mock_conn.ft.assert_called_once_with(index)

    @pytest.mark.asyncio
    async def test_vector_search_with_filter_expression(self, mock_connection):
        """Test vector search with filter expression."""
        mock_conn = mock_connection

        index = 'test_index'
        field = 'embedding'
        vector = [0.1, 0.2, 0.3]
        filter_expression = "@category:electronics"
        count = 3

        # Create mock document
        doc_fields = {b'document_json': b'{"id": "doc1", "title": "Laptop", "category": "electronics", "price": 999}'}

        mock_doc = Mock()
        mock_doc.id = 'doc1'

        mock_result = Mock()
        mock_result.total = 1
        mock_result.docs = [mock_doc]

        # Setup mock search interface
        mock_ft = Mock()
        mock_ft.search.return_value = mock_result
        mock_conn.ft.return_value = mock_ft

        # Setup mock connection to return document fields
        mock_conn.hgetall.return_value = doc_fields

        # Execute search with filter
        result = await vector_search(index, field, vector, filter_expression=filter_expression, count=count)

        # Verify results
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]['category'] == 'electronics'
        assert result[0]['title'] == 'Laptop'

    @pytest.mark.asyncio
    async def test_vector_search_with_no_content(self, mock_connection):
        """Test vector search with no_content parameter."""
        mock_conn = mock_connection

        index = 'test_index'
        field = 'embedding'
        vector = [0.1, 0.2]
        count = 5

        # Create mock search result
        mock_result = Mock()
        mock_result.total = 0
        mock_result.docs = []

        # Setup mock search interface
        mock_ft = Mock()
        mock_ft.search.return_value = mock_result
        mock_conn.ft.return_value = mock_ft

        # Execute search with no_content=True
        result = await vector_search(index, field, vector, no_content=True, count=count)

        # Verify empty list returned
        assert isinstance(result, list)
        assert len(result) == 0

        # Verify search was called
        mock_ft.search.assert_called_once()

    @pytest.mark.asyncio
    async def test_vector_search_no_results(self, mock_connection):
        """Test vector search with no results."""
        mock_conn = mock_connection

        index = 'test_index'
        field = 'embedding'
        vector = [0.1, 0.2]

        # Create mock search result with no documents
        mock_result = Mock()
        mock_result.total = 0
        mock_result.docs = []

        # Setup mock search interface
        mock_ft = Mock()
        mock_ft.search.return_value = mock_result
        mock_conn.ft.return_value = mock_ft

        # Execute search
        result = await vector_search(index, field, vector)

        # Verify empty list returned
        assert isinstance(result, list)
        assert len(result) == 0
        mock_conn.ft.assert_called_once_with(index)

    @pytest.mark.asyncio
    async def test_vector_search_default_count(self, mock_connection):
        """Test vector search with default count parameter."""
        mock_conn = mock_connection

        index = 'test_index'
        field = 'vec'
        vector = [0.5, 0.5]

        # Create mock search result
        mock_result = Mock()
        mock_result.total = 0
        mock_result.docs = []

        # Setup mock search interface
        mock_ft = Mock()
        mock_ft.search.return_value = mock_result
        mock_conn.ft.return_value = mock_ft

        # Execute search without specifying count
        result = await vector_search(index, field, vector)

        # Verify empty list returned
        assert isinstance(result, list)
        assert len(result) == 0

        # Verify search was called
        mock_ft.search.assert_called_once()

    @pytest.mark.asyncio
    async def test_vector_search_error_handling(self, mock_connection):
        """Test error handling in vector search."""
        mock_conn = mock_connection

        index = 'test_index'
        field = 'embedding'
        vector = [0.1, 0.2, 0.3]
        count = 5

        # Setup mock to raise ValkeyError
        mock_ft = Mock()
        mock_ft.search.side_effect = ValkeyError('Index not found')
        mock_conn.ft.return_value = mock_ft

        # Execute search
        result = await vector_search(index, field, vector, 0, count)

        # Verify string message returned on error
        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_vector_search_connection_error(self, mock_connection):
        """Test error when accessing search index."""
        mock_conn = mock_connection

        index = 'invalid_index'
        field = 'vec'
        vector = [0.1, 0.2]
        count = 5

        # Setup mock to raise error when accessing ft
        mock_conn.ft.side_effect = ValkeyError('Connection error')

        # Execute search
        result = await vector_search(index, field, vector, 0, count)

        # Verify string message returned on error
        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_vector_search_large_vector(self, mock_connection):
        """Test vector search with a large vector."""
        mock_conn = mock_connection

        index = 'test_index'
        field = 'high_dim_vector'
        vector = [float(i) * 0.01 for i in range(100)]  # 100-dimensional vector
        count = 3

        # Create mock document with document_json field
        doc_fields = {b'document_json': b'{"id": "doc1", "title": "High Dimensional Document", "description": "Document with 100-dimensional embedding"}'}

        # Create mock document
        mock_doc = Mock()
        mock_doc.id = 'doc1'

        # Create mock search result
        mock_result = Mock()
        mock_result.total = 1
        mock_result.docs = [mock_doc]

        # Setup mock search interface
        mock_ft = Mock()
        mock_ft.search.return_value = mock_result
        mock_conn.ft.return_value = mock_ft

        # Setup mock connection to return document fields
        mock_conn.hgetall.return_value = doc_fields

        # Execute search
        result = await vector_search(index, field, vector, offset=0, count=count)

        # Verify search was called
        mock_ft.search.assert_called_once()

        # Verify result is correct
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]['id'] == 'doc1'
        assert result[0]['title'] == 'High Dimensional Document'
        assert result[0]['description'] == 'Document with 100-dimensional embedding'

    @pytest.mark.asyncio
    async def test_vector_search_missing_document(self, mock_connection):
        """Test vector search when document doesn't exist or has no document_json field."""
        mock_conn = mock_connection

        index = 'test_index'
        field = 'embedding'
        vector = [0.1, 0.2]
        count = 5

        # Create mock document
        mock_doc = Mock()
        mock_doc.id = 'doc1'

        mock_result = Mock()
        mock_result.total = 1
        mock_result.docs = [mock_doc]

        # Setup mock search interface
        mock_ft = Mock()
        mock_ft.search.return_value = mock_result
        mock_conn.ft.return_value = mock_ft

        # Setup mock fetch to return dict without document_json field
        mock_conn.hgetall.return_value = {b'other_field': b'value'}

        # Execute search
        result = await vector_search(index, field, vector, offset=0, count=count)

        # Verify empty list since document doesn't have document_json field
        assert isinstance(result, list)
        assert len(result) == 0
