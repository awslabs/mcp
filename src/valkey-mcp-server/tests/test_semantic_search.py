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

"""Unit tests for semantic search functionality using dummy embeddings provider."""

import pytest
from awslabs.valkey_mcp_server.embeddings.providers import HashEmbeddings
from awslabs.valkey_mcp_server.tools.semantic_search import (
    add_documents,
    collection_info,
    semantic_search,
    update_document,
)
from unittest.mock import Mock, patch


class TestSemanticSearchUnit:
    """Unit tests for semantic search functionality."""

    @pytest.fixture
    def mock_connection(self):
        """Create a mock Valkey connection."""
        with patch(
            'awslabs.valkey_mcp_server.tools.semantic_search.ValkeyConnectionManager'
        ) as mock_manager:
            mock_conn = Mock()
            mock_manager.get_connection.return_value = mock_conn
            yield mock_conn

    @pytest.fixture
    def dummy_embeddings(self):
        """Create a dummy embeddings provider."""
        return HashEmbeddings(dimensions=128)

    @pytest.mark.asyncio
    async def test_semantic_search_successful(self, mock_connection, dummy_embeddings):
        """Test successful semantic search with dummy embeddings."""
        # Mock the embeddings provider
        with patch(
            'awslabs.valkey_mcp_server.tools.semantic_search._embeddings_provider',
            dummy_embeddings,
        ):
            # Mock vector_search function
            with patch(
                'awslabs.valkey_mcp_server.tools.semantic_search.vector_search'
            ) as mock_vector_search:
                mock_vector_search.return_value = {
                    'status': 'success',
                    'results': [
                        {'id': 'doc1', 'title': 'Test Document', 'content': 'Test content'}
                    ],
                }

                # Execute semantic search
                result = await semantic_search(
                    collection='test_collection', query='test query', limit=5
                )

                # Verify results
                assert result['status'] == 'success'
                assert len(result['results']) == 1
                assert result['results'][0]['id'] == 'doc1'

                # Verify vector_search was called with correct parameters
                mock_vector_search.assert_called_once()
                call_args = mock_vector_search.call_args
                assert call_args[1]['index'] == 'semantic_collection_test_collection'
                assert call_args[1]['field'] == 'embedding'
                assert call_args[1]['count'] == 5
                assert len(call_args[1]['vector']) == 128  # dummy embeddings dimension

    @pytest.mark.asyncio
    async def test_semantic_search_no_results(self, mock_connection, dummy_embeddings):
        """Test semantic search with no results."""
        with patch(
            'awslabs.valkey_mcp_server.tools.semantic_search._embeddings_provider',
            dummy_embeddings,
        ):
            with patch(
                'awslabs.valkey_mcp_server.tools.semantic_search.vector_search'
            ) as mock_vector_search:
                mock_vector_search.return_value = {'status': 'success', 'results': []}

                result = await semantic_search(
                    collection='empty_collection', query='no matches', limit=10
                )

                assert result['status'] == 'success'
                assert len(result['results']) == 0

    @pytest.mark.asyncio
    async def test_semantic_search_error_handling(self, mock_connection, dummy_embeddings):
        """Test semantic search error handling."""
        with patch(
            'awslabs.valkey_mcp_server.tools.semantic_search._embeddings_provider',
            dummy_embeddings,
        ):
            with patch(
                'awslabs.valkey_mcp_server.tools.semantic_search.vector_search'
            ) as mock_vector_search:
                mock_vector_search.return_value = {'status': 'error', 'reason': 'Index not found'}

                result = await semantic_search(
                    collection='nonexistent_collection', query='test query'
                )

                assert result['status'] == 'error'
                assert 'reason' in result

    @pytest.mark.asyncio
    async def test_dummy_embeddings_consistency(self, dummy_embeddings):
        """Test that dummy embeddings are consistent for same input."""
        text = 'test input'

        embedding1 = await dummy_embeddings.generate_embedding(text)
        embedding2 = await dummy_embeddings.generate_embedding(text)

        assert embedding1 == embedding2
        assert len(embedding1) == 128
        assert all(-1.0 <= val <= 1.0 for val in embedding1)

    @pytest.mark.asyncio
    async def test_semantic_search_include_content_false(self, mock_connection, dummy_embeddings):
        """Test semantic search with include_content=False."""
        with patch(
            'awslabs.valkey_mcp_server.tools.semantic_search._embeddings_provider',
            dummy_embeddings,
        ):
            with patch(
                'awslabs.valkey_mcp_server.tools.semantic_search.vector_search'
            ) as mock_vector_search:
                mock_vector_search.return_value = {
                    'status': 'success',
                    'results': [
                        {'id': 'doc1', 'my-shoe': 'is missing'}  # No content field
                    ],
                }

                # Execute semantic search with include_content=False
                result = await semantic_search(
                    collection='test_collection', query='test query', include_content=False
                )

                # Verify results
                assert result['status'] == 'success'
                assert len(result['results']) == 1
                assert result['results'][0]['id'] == 'doc1'
                assert 'my-shoe' not in result['results'][0]

                # Verify vector_search was called with no_content=True
                mock_vector_search.assert_called_once()
                call_args = mock_vector_search.call_args
                assert call_args[1]['no_content']

    @pytest.mark.asyncio
    async def test_update_document_successful(self, mock_connection, dummy_embeddings):
        """Test successful document update."""
        with patch(
            'awslabs.valkey_mcp_server.tools.semantic_search._embeddings_provider',
            dummy_embeddings,
        ):
            # Mock connection methods
            mock_connection.exists.return_value = True  # Document exists
            mock_connection.hset.return_value = None

            # Execute update_document
            result = await update_document(
                collection='test_collection',
                document={'id': 'doc1', 'title': 'Updated Document', 'content': 'Updated content'},
                text_fields=['title', 'content'],
            )

            # Verify results
            assert result['status'] == 'success'
            assert result['updated'] == 1
            assert result['document_id'] == 'doc1'
            assert result['collection'] == 'test_collection'
            assert result['embedding_dimensions'] == 128

            # Verify document existence was checked
            mock_connection.exists.assert_called_once_with(
                'semantic_collection_test_collection:doc:doc1'
            )

            # Verify document was updated
            mock_connection.hset.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_document_not_found(self, mock_connection, dummy_embeddings):
        """Test update_document when document doesn't exist."""
        with patch(
            'awslabs.valkey_mcp_server.tools.semantic_search._embeddings_provider',
            dummy_embeddings,
        ):
            # Mock document doesn't exist
            mock_connection.exists.return_value = False

            result = await update_document(
                collection='test_collection', document={'id': 'nonexistent', 'title': 'Test'}
            )

            # Verify error response
            assert result['status'] == 'error'
            assert 'not found' in result['reason']
            assert result['updated'] == 0

    @pytest.mark.asyncio
    async def test_update_document_missing_id(self, mock_connection, dummy_embeddings):
        """Test update_document with missing id field."""
        with patch(
            'awslabs.valkey_mcp_server.tools.semantic_search._embeddings_provider',
            dummy_embeddings,
        ):
            result = await update_document(
                collection='test_collection',
                document={'title': 'Test Document'},  # Missing 'id'
            )

            # Verify error response
            assert result['status'] == 'error'
            assert 'id' in result['reason'].lower()
            assert result['updated'] == 0

    @pytest.mark.asyncio
    async def test_add_documents_readonly_mode(self, mock_connection, dummy_embeddings):
        """Test add_documents in read-only mode."""
        with patch(
            'awslabs.valkey_mcp_server.tools.semantic_search._embeddings_provider',
            dummy_embeddings,
        ):
            with patch(
                'awslabs.valkey_mcp_server.tools.semantic_search.Context.readonly_mode',
                return_value=True,
            ):
                result = await add_documents(
                    collection='test_collection',
                    documents=[
                        {'id': 'doc1', 'title': 'Test Document', 'content': 'Test content'}
                    ],
                )

                # Verify read-only error response
                assert result['status'] == 'error'
                assert result['added'] == 0
                assert 'read-only mode' in result['reason']

    @pytest.mark.asyncio
    async def test_update_document_readonly_mode(self, mock_connection, dummy_embeddings):
        """Test update_document in read-only mode."""
        with patch(
            'awslabs.valkey_mcp_server.tools.semantic_search._embeddings_provider',
            dummy_embeddings,
        ):
            with patch(
                'awslabs.valkey_mcp_server.tools.semantic_search.Context.readonly_mode',
                return_value=True,
            ):
                result = await update_document(
                    collection='test_collection',
                    document={'id': 'doc1', 'title': 'Test Document', 'content': 'Test content'},
                )

                # Verify read-only error response
                assert result['status'] == 'error'
                assert result['updated'] == 0
                assert 'read-only mode' in result['reason']

    @pytest.mark.asyncio
    async def test_add_documents_error_counting(self, mock_connection, dummy_embeddings):
        """Test add_documents error counting for invalid documents."""
        with patch(
            'awslabs.valkey_mcp_server.tools.semantic_search._embeddings_provider',
            dummy_embeddings,
        ):
            with patch(
                'awslabs.valkey_mcp_server.tools.semantic_search._index_exists', return_value=True
            ):
                # Mock connection methods
                mock_connection.hset.return_value = None
                mock_connection.keys.return_value = ['key1', 'key2']  # Mock total docs count

                result = await add_documents(
                    collection='test_collection',
                    documents=[
                        {'id': 'doc1', 'title': 'Valid Document', 'content': 'Valid content'},
                        {'title': 'Invalid Document'},  # Missing 'id'
                        {
                            'id': 'doc2',
                            'title': 'Another Valid Document',
                            'content': 'More content',
                        },
                    ],
                )

                # Verify error counting
                assert result['status'] == 'success'
                assert result['added'] == 2  # Two valid documents
                assert result['errors'] == 1  # One invalid document (missing id)

    @pytest.mark.asyncio
    async def test_add_documents_hset_error(self, mock_connection, dummy_embeddings):
        """Test add_documents error counting when hset fails."""
        with patch(
            'awslabs.valkey_mcp_server.tools.semantic_search._embeddings_provider',
            dummy_embeddings,
        ):
            with patch(
                'awslabs.valkey_mcp_server.tools.semantic_search._index_exists', return_value=True
            ):
                # Mock hset to raise an error
                mock_connection.hset.side_effect = Exception('Database write error')
                mock_connection.keys.return_value = []

                result = await add_documents(
                    collection='test_collection',
                    documents=[
                        {'id': 'doc1', 'title': 'Document 1', 'content': 'Content 1'},
                        {'id': 'doc2', 'title': 'Document 2', 'content': 'Content 2'},
                    ],
                )

                # Verify all documents failed due to hset error
                assert result['status'] == 'success'
                assert result['added'] == 0  # No documents added
                assert result['errors'] == 2  # Both documents failed

    @pytest.mark.asyncio
    async def test_collection_info_successful(self, mock_connection):
        """Test collection_info tool with successful index query."""
        # Mock stored documents count
        mock_connection.keys.return_value = ['doc1', 'doc2', 'doc3']

        # Mock FT.INFO response
        mock_connection.execute_command.return_value = [
            b'index_name',
            b'semantic_collection_test',
            b'num_docs',
            b'3',
            b'max_doc_id',
            b'3',
            b'hash_indexing_failures',
            b'0',
        ]

        result = await collection_info(collection='test_collection')

        # Verify results
        assert result['status'] == 'success'
        assert result['collection'] == 'test_collection'
        assert result['stored_documents'] == 3
        assert result['indexed_documents'] == 3
        assert result['indexing_complete']
