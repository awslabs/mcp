"""Integration test for VSS HGETALL optimization with live services."""

import pytest
import struct
from awslabs.valkey_mcp_server.common.connection import ValkeyConnectionManager
from awslabs.valkey_mcp_server.tools.index import create_vector_index
from awslabs.valkey_mcp_server.tools.vss import vector_search


class TestVSSLiveIntegration:
    """Live integration tests for vector search HGETALL optimization."""

    @pytest.fixture(autouse=True)
    async def setup_and_teardown(self):
        """Set up test index and data, then tear down after test."""
        self.index_name = 'hgetall_test_idx'
        self.field_name = 'embedding'
        self.doc_id = 'hgetall_test_doc_1'

        # Setup: Create vector index
        try:
            await create_vector_index(
                name=self.index_name,
                dimensions=3,
                embedding_field=self.field_name,
                distance_metric='COSINE',
            )
        except Exception as e:
            print(f'Could not create vector index: {e}')
            pytest.skip(f'Could not create vector index: {e}')

        # Setup: Add test document with vector
        conn = ValkeyConnectionManager.get_connection(decode_responses=False)
        test_doc_json = '{"id": "hgetall_test_doc_1", "title": "Test Document", "content": "Test content", "video_game": "Commander Neek 4"}'
        test_vector = [0.1, 0.2, 0.3]
        vector_bytes = struct.pack('3f', *test_vector)

        conn.hset(
            self.doc_id, mapping={self.field_name: vector_bytes, 'document_json': test_doc_json}
        )

        yield  # Run the test

        # Teardown: Remove test data and index
        try:
            conn.ft(self.index_name).dropindex(delete_documents=True)
        except Exception:
            pass

    @pytest.mark.asyncio
    async def test_vector_search_hgetall_optimization(self):
        """Test vector search with both no_content scenarios to verify HGETALL optimization."""
        test_vector = [0.1, 0.2, 0.3]

        # Test with no_content=False - should return full document content
        result_with_content = await vector_search(
            index=self.index_name,
            field=self.field_name,
            vector=test_vector,
            no_content=False,
            count=1,
        )

        # Verify full content is returned (proving no additional hgetall needed)
        assert result_with_content['status'] == 'success'
        assert len(result_with_content['results']) >= 1

        found_doc = result_with_content['results'][0]
        assert found_doc['id'] == 'hgetall_test_doc_1'
        assert found_doc['title'] == 'Test Document'
        assert found_doc['content'] == 'Test content'
        assert found_doc['video_game'] == 'Commander Neek 4'

        # Test with no_content=True - should return only document IDs
        result_no_content = await vector_search(
            index=self.index_name,
            field=self.field_name,
            vector=test_vector,
            no_content=True,
            count=1,
        )

        # Verify only ID is returned
        assert result_no_content['status'] == 'success'
        assert len(result_no_content['results']) >= 1

        found_doc_no_content = result_no_content['results'][0]
        assert 'id' in found_doc_no_content
        assert len(found_doc_no_content) == 1  # Only ID field
        assert 'video_game' not in found_doc_no_content  # Should not have content fields
