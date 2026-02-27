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

import json
import pytest
import struct
from awslabs.valkey_mcp_server.embeddings.providers import HashEmbeddings
from awslabs.valkey_mcp_server.tools.semantic_search import (
    add_documents,
    collection_info,
    find_similar_documents,
    get_document,
    list_collections,
    semantic_search,
    update_document,
)
from unittest.mock import AsyncMock, Mock, patch


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
    async def test_update_document_embedding_failure(self, mock_connection, dummy_embeddings):
        """Test update_document when embedding generation fails."""
        # Create a mock embeddings provider that raises exception
        mock_embeddings = Mock()
        mock_embeddings.generate_embedding.side_effect = Exception('Embedding service unavailable')

        with patch(
            'awslabs.valkey_mcp_server.tools.semantic_search._embeddings_provider',
            mock_embeddings,
        ):
            # Mock document exists
            mock_connection.exists.return_value = True

            result = await update_document(
                collection='test_collection',
                document={'id': 'test_doc', 'content': 'Test content'},
            )

            # Verify error response
            assert result['status'] == 'error'
            assert result['updated'] == 0
            assert 'Embedding service unavailable' in result['reason']

    @pytest.mark.asyncio
    async def test_update_document_database_failure(self, mock_connection, dummy_embeddings):
        """Test update_document when database operation fails."""
        with patch(
            'awslabs.valkey_mcp_server.tools.semantic_search._embeddings_provider',
            dummy_embeddings,
        ):
            # Mock document exists but hset fails
            mock_connection.exists.return_value = True
            mock_connection.hset.side_effect = Exception('Database connection failed')

            result = await update_document(
                collection='test_collection',
                document={'id': 'test_doc', 'content': 'Test content'},
            )

            # Verify error response
            assert result['status'] == 'error'
            assert result['updated'] == 0
            assert 'Database connection failed' in result['reason']

    @pytest.mark.asyncio
    async def test_update_document_empty_text_fields(self, mock_connection, dummy_embeddings):
        """Test update_document with empty text fields."""
        # Create a mock embeddings provider to track calls
        mock_embeddings = Mock()
        mock_embeddings.generate_embedding = AsyncMock(return_value=[0.1, 0.2, 0.3])

        with patch(
            'awslabs.valkey_mcp_server.tools.semantic_search._embeddings_provider',
            mock_embeddings,
        ):
            # Mock document exists
            mock_connection.exists.return_value = True

            result = await update_document(
                collection='test_collection',
                document={'id': 'test_doc', 'title': 'Test'},
                text_fields=['nonexistent_field'],
            )

            # Should still succeed but with empty embedding text
            assert result['status'] == 'success'
            assert result['updated'] == 1
            # Verify embedding was generated from empty string
            mock_embeddings.generate_embedding.assert_called_with('')

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

    @pytest.mark.asyncio
    async def test_find_similar_documents_successful(self, mock_connection):
        """Test successful find_similar_documents operation."""
        # Mock document exists with embedding
        mock_connection.hget.return_value = struct.pack('3f', 0.1, 0.2, 0.3)

        # Mock vector_search response
        with patch(
            'awslabs.valkey_mcp_server.tools.semantic_search.vector_search'
        ) as mock_vector_search:
            mock_vector_search.return_value = {
                'status': 'success',
                'results': [
                    {'id': 'source_doc', 'title': 'Source Document'},
                    {'id': 'similar_1', 'title': 'Similar Document 1'},
                    {'id': 'similar_2', 'title': 'Similar Document 2'},
                ],
            }

            result = await find_similar_documents(
                collection='test_collection', document_id='source_doc', limit=5
            )

            # Verify results
            assert result['status'] == 'success'
            assert len(result['results']) == 2  # Source doc filtered out
            assert result['results'][0]['id'] == 'similar_1'
            assert result['results'][1]['id'] == 'similar_2'

            # Verify vector_search was called with correct parameters
            mock_vector_search.assert_called_once()
            call_args = mock_vector_search.call_args[1]
            # Use approximate comparison for floating point values
            assert len(call_args['vector']) == 3
            assert abs(call_args['vector'][0] - 0.1) < 1e-6
            assert abs(call_args['vector'][1] - 0.2) < 1e-6
            assert abs(call_args['vector'][2] - 0.3) < 1e-6
            assert call_args['count'] == 6  # limit + 1

    @pytest.mark.asyncio
    async def test_find_similar_documents_not_found(self, mock_connection):
        """Test find_similar_documents when source document doesn't exist."""
        # Mock document doesn't exist
        mock_connection.hget.return_value = None

        result = await find_similar_documents(
            collection='test_collection', document_id='nonexistent_doc'
        )

        # Verify error response
        assert result['status'] == 'error'
        assert result['type'] == 'content'
        assert 'not found' in result['reason']

    @pytest.mark.asyncio
    async def test_find_similar_documents_vector_search_failure(self, mock_connection):
        """Test find_similar_documents when vector search fails."""
        # Mock document exists with embedding
        mock_connection.hget.return_value = struct.pack('3f', 0.1, 0.2, 0.3)

        # Mock vector_search failure
        with patch(
            'awslabs.valkey_mcp_server.tools.semantic_search.vector_search'
        ) as mock_vector_search:
            mock_vector_search.return_value = {
                'status': 'error',
                'type': 'valkey',
                'reason': 'Index not found',
            }

            result = await find_similar_documents(
                collection='test_collection', document_id='test_doc'
            )

            # Verify error response
            assert result['status'] == 'error'
            assert result['type'] == 'valkey'
            assert 'Index not found' in result['reason']

    @pytest.mark.asyncio
    async def test_find_similar_documents_with_offset_limit(self, mock_connection):
        """Test find_similar_documents with offset and limit parameters."""
        # Mock document exists with embedding
        mock_connection.hget.return_value = struct.pack('3f', 0.1, 0.2, 0.3)

        # Mock vector_search response with many results
        with patch(
            'awslabs.valkey_mcp_server.tools.semantic_search.vector_search'
        ) as mock_vector_search:
            mock_vector_search.return_value = {
                'status': 'success',
                'results': [
                    {'id': 'source_doc', 'title': 'Source Document'},
                    {'id': 'similar_1', 'title': 'Similar Document 1'},
                    {'id': 'similar_2', 'title': 'Similar Document 2'},
                    {'id': 'similar_3', 'title': 'Similar Document 3'},
                ],
            }

            result = await find_similar_documents(
                collection='test_collection', document_id='source_doc', offset=5, limit=2
            )

            # Verify results are limited correctly
            assert result['status'] == 'success'
            assert len(result['results']) == 2  # Limited to 2 after filtering source

            # Verify vector_search was called with correct count (limit + 1)
            call_args = mock_vector_search.call_args[1]
            assert call_args['offset'] == 5
            assert call_args['count'] == 3  # limit + 1

    @pytest.mark.asyncio
    async def test_find_similar_documents_valkey_error(self, mock_connection):
        """Test find_similar_documents when Valkey operation fails."""
        from valkey import ValkeyError

        # Mock hget raises ValkeyError
        mock_connection.hget.side_effect = ValkeyError('Connection failed')

        result = await find_similar_documents(collection='test_collection', document_id='test_doc')

        # Verify error response
        assert result['status'] == 'error'
        assert result['type'] == 'valkey'
        assert 'Connection failed' in result['reason']

    @pytest.mark.asyncio
    async def test_get_document_successful(self, mock_connection):
        """Test successful document retrieval."""
        # Mock document exists with valid JSON
        test_doc = {'id': 'test_doc', 'title': 'Test Document', 'content': 'Test content'}
        mock_connection.hgetall.return_value = {
            b'document_json': json.dumps(test_doc).encode('utf-8'),
            b'embedding': b'some_embedding_data',
        }

        result = await get_document(collection='test_collection', document_id='test_doc')

        # Verify results
        assert result['status'] == 'success'
        assert result['result'] == test_doc

    @pytest.mark.asyncio
    async def test_get_document_not_found(self, mock_connection):
        """Test get_document when document doesn't exist."""
        # Mock document doesn't exist (no document_json field)
        mock_connection.hgetall.return_value = {}

        result = await get_document(collection='test_collection', document_id='nonexistent_doc')

        # Verify results
        assert result['status'] == 'success'
        assert result['result'] is None

    @pytest.mark.asyncio
    async def test_get_document_decode_error(self, mock_connection):
        """Test get_document when document JSON is corrupted."""
        # Mock document with invalid JSON
        mock_connection.hgetall.return_value = {
            b'document_json': b'invalid json content',
            b'embedding': b'some_embedding_data',
        }

        result = await get_document(collection='test_collection', document_id='corrupted_doc')

        # Verify error response
        assert result['status'] == 'error'
        assert result['type'] == 'decode'
        assert 'Failed to decode document' in result['reason']

    @pytest.mark.asyncio
    async def test_get_document_unicode_error(self, mock_connection):
        """Test get_document when document has encoding issues."""
        # Mock document with invalid UTF-8 bytes
        mock_connection.hgetall.return_value = {
            b'document_json': b'\xff\xfe invalid utf-8',
            b'embedding': b'some_embedding_data',
        }

        result = await get_document(collection='test_collection', document_id='encoding_error_doc')

        # Verify error response
        assert result['status'] == 'error'
        assert result['type'] == 'decode'
        assert 'Failed to decode document' in result['reason']

    @pytest.mark.asyncio
    async def test_get_document_valkey_error(self, mock_connection):
        """Test get_document when Valkey operation fails."""
        from valkey import ValkeyError

        # Mock hgetall raises ValkeyError
        mock_connection.hgetall.side_effect = ValkeyError('Connection timeout')

        result = await get_document(collection='test_collection', document_id='test_doc')

        # Verify error response
        assert result['status'] == 'error'
        assert result['type'] == 'valkey'
        assert 'Connection timeout' in result['reason']

    @pytest.mark.asyncio
    async def test_get_document_general_exception(self, mock_connection):
        """Test get_document when unexpected exception occurs."""
        # Mock hgetall raises general exception
        mock_connection.hgetall.side_effect = RuntimeError('Unexpected error')

        result = await get_document(collection='test_collection', document_id='test_doc')

        # Verify error response
        assert result['status'] == 'error'
        assert result['type'] == 'general'
        assert 'Unexpected error' in result['reason']

    @pytest.mark.asyncio
    async def test_get_document_string_document_json(self, mock_connection):
        """Test get_document when document_json is already a string."""
        # Mock document where document_json is string (not bytes)
        test_doc = {'id': 'test_doc', 'title': 'String Test'}
        mock_connection.hgetall.return_value = {
            b'document_json': json.dumps(test_doc),  # String instead of bytes
            b'embedding': b'some_embedding_data',
        }

        result = await get_document(collection='test_collection', document_id='test_doc')

        # Verify results
        assert result['status'] == 'success'
        assert result['result'] == test_doc

    @pytest.mark.asyncio
    async def test_list_collections_successful(self, mock_connection):
        """Test successful collections listing."""
        # Mock FT._LIST returns semantic collection indices
        mock_connection.execute_command.return_value = [
            b'semantic_collection_papers',
            b'semantic_collection_reviews',
            b'other_index',  # Should be ignored
            b'semantic_collection_docs',
        ]

        # Mock document counts for each collection
        def mock_keys(pattern):
            if 'papers' in pattern:
                return ['doc1', 'doc2', 'doc3']  # 3 documents
            elif 'reviews' in pattern:
                return ['doc1', 'doc2']  # 2 documents
            elif 'docs' in pattern:
                return ['doc1']  # 1 document
            return []

        mock_connection.keys.side_effect = mock_keys

        result = await list_collections(limit=10)

        # Verify results
        assert result['status'] == 'success'
        assert len(result['results']) == 3

        # Check collection details
        collections = {c['name']: c['document_count'] for c in result['results']}
        assert collections['papers'] == 3
        assert collections['reviews'] == 2
        assert collections['docs'] == 1

    @pytest.mark.asyncio
    async def test_list_collections_empty(self, mock_connection):
        """Test list_collections when no collections exist."""
        # Mock FT._LIST returns empty list
        mock_connection.execute_command.return_value = []

        result = await list_collections()

        # Verify results
        assert result['status'] == 'success'
        assert result['results'] == []

    @pytest.mark.asyncio
    async def test_list_collections_with_limit(self, mock_connection):
        """Test list_collections with limit parameter."""
        # Mock FT._LIST returns many semantic collections
        mock_connection.execute_command.return_value = [
            b'semantic_collection_col1',
            b'semantic_collection_col2',
            b'semantic_collection_col3',
            b'semantic_collection_col4',
        ]

        # Mock all collections have 1 document
        mock_connection.keys.return_value = ['doc1']

        result = await list_collections(limit=2)

        # Verify results respect limit
        assert result['status'] == 'success'
        assert len(result['results']) == 2

    @pytest.mark.asyncio
    async def test_list_collections_valkey_error(self, mock_connection):
        """Test list_collections when Valkey operation fails."""
        from valkey import ValkeyError

        # Mock execute_command raises ValkeyError
        mock_connection.execute_command.side_effect = ValkeyError('Connection failed')

        result = await list_collections()

        # Verify error response
        assert result['status'] == 'error'
        assert result['type'] == 'valkey'
        assert 'Connection failed' in result['reason']

    @pytest.mark.asyncio
    async def test_add_documents_index_creation(self, mock_connection, dummy_embeddings):
        """Test index creation during add_documents when index doesn't exist."""
        # Mock keys to return empty list initially
        mock_connection.keys.return_value = []

        with (
            patch(
                'awslabs.valkey_mcp_server.tools.semantic_search._embeddings_provider',
                dummy_embeddings,
            ),
            patch(
                'awslabs.valkey_mcp_server.tools.semantic_search._index_exists', return_value=False
            ),
            patch(
                'awslabs.valkey_mcp_server.tools.semantic_search.create_vector_index',
                new_callable=AsyncMock,
            ) as mock_create_index,
        ):
            result = await add_documents(
                collection='test_collection', documents=[{'id': 'doc1', 'content': 'Test content'}]
            )

            # Verify index creation was called
            mock_create_index.assert_called_once()
            assert result['status'] == 'success'

    @pytest.mark.asyncio
    async def test_add_documents_general_exception(self, mock_connection, dummy_embeddings):
        """Test add_documents general exception handling."""
        with patch(
            'awslabs.valkey_mcp_server.tools.semantic_search._embeddings_provider',
            dummy_embeddings,
        ):
            # Mock connection to raise unexpected exception
            mock_connection.keys.side_effect = RuntimeError('Unexpected error')

            result = await add_documents(
                collection='test_collection', documents=[{'id': 'doc1', 'content': 'Test'}]
            )

            # Verify error response
            assert result['status'] == 'error'
            assert result['added'] == 0
            assert 'Unexpected error' in result['reason']

    @pytest.mark.asyncio
    async def test_collection_info_general_exception(self, mock_connection):
        """Test collection_info general exception handling."""
        # Mock keys to raise unexpected exception
        mock_connection.keys.side_effect = RuntimeError('Database error')

        result = await collection_info(collection='test_collection')

        # Verify error response
        assert result['status'] == 'error'
        assert 'Database error' in result['reason']

    @pytest.mark.asyncio
    async def test_semantic_search_index_not_exists(self, mock_connection, dummy_embeddings):
        """Test semantic_search when index doesn't exist."""
        with (
            patch(
                'awslabs.valkey_mcp_server.tools.semantic_search._embeddings_provider',
                dummy_embeddings,
            ),
            patch(
                'awslabs.valkey_mcp_server.tools.semantic_search._index_exists', return_value=False
            ),
        ):
            result = await semantic_search(collection='nonexistent_collection', query='test query')

            # Verify error response
            assert result['status'] == 'error'
            assert result['type'] == 'index'

    @pytest.mark.asyncio
    async def test_semantic_search_embedding_failure(self, mock_connection):
        """Test semantic_search when embedding generation fails."""
        # Mock embeddings provider to raise exception
        mock_embeddings = Mock()
        mock_embeddings.generate_embedding.side_effect = Exception('Embedding service down')

        with (
            patch(
                'awslabs.valkey_mcp_server.tools.semantic_search._embeddings_provider',
                mock_embeddings,
            ),
            patch(
                'awslabs.valkey_mcp_server.tools.semantic_search._index_exists', return_value=True
            ),
        ):
            result = await semantic_search(collection='test_collection', query='test query')

            # Verify error response
            assert result['status'] == 'error'
            assert result['type'] == 'embedding'
            assert 'Embedding service down' in result['reason']

    @pytest.mark.asyncio
    async def test_semantic_search_vector_search_failure(self, mock_connection, dummy_embeddings):
        """Test semantic_search when vector_search fails."""
        with (
            patch(
                'awslabs.valkey_mcp_server.tools.semantic_search._embeddings_provider',
                dummy_embeddings,
            ),
            patch(
                'awslabs.valkey_mcp_server.tools.semantic_search._index_exists', return_value=True
            ),
            patch(
                'awslabs.valkey_mcp_server.tools.semantic_search.vector_search'
            ) as mock_vector_search,
        ):
            # Mock vector_search to raise exception
            mock_vector_search.side_effect = Exception('Vector search failed')

            result = await semantic_search(collection='test_collection', query='test query')

            # Verify error response
            assert result['status'] == 'error'
            assert result['type'] == 'vector_search'
            assert 'Vector search failed' in result['reason']

    @pytest.mark.asyncio
    async def test_semantic_search_unexpected_document_format(
        self, mock_connection, dummy_embeddings
    ):
        """Test semantic_search with unexpected document format in results."""
        with (
            patch(
                'awslabs.valkey_mcp_server.tools.semantic_search._embeddings_provider',
                dummy_embeddings,
            ),
            patch(
                'awslabs.valkey_mcp_server.tools.semantic_search._index_exists', return_value=True
            ),
            patch(
                'awslabs.valkey_mcp_server.tools.semantic_search.vector_search'
            ) as mock_vector_search,
        ):
            # Mock vector_search to return unexpected format
            mock_vector_search.return_value = {
                'status': 'success',
                'results': ['invalid_format'],  # String instead of dict
            }

            result = await semantic_search(
                collection='test_collection', query='test query', include_content=False
            )

            # Verify error response
            assert result['status'] == 'error'
            assert result['type'] == 'format'
            assert 'Unexpected document format' in result['reason']

    @pytest.mark.asyncio
    async def test_find_similar_documents_general_exception(self, mock_connection):
        """Test find_similar_documents general exception handling."""
        # Mock hget to raise unexpected exception
        mock_connection.hget.side_effect = RuntimeError('Database connection lost')

        result = await find_similar_documents(collection='test_collection', document_id='test_doc')

        # Verify error response
        assert result['status'] == 'error'
        assert result['type'] == 'general'
        assert 'Database connection lost' in result['reason']

    @pytest.mark.asyncio
    async def test_list_collections_general_exception(self, mock_connection):
        """Test list_collections general exception handling."""
        # Mock execute_command to raise unexpected exception
        mock_connection.execute_command.side_effect = RuntimeError('Command execution failed')

        result = await list_collections()

        # Verify error response
        assert result['status'] == 'error'
        assert result['type'] == 'general'
        assert 'Command execution failed' in result['reason']
