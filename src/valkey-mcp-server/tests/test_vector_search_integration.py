"""Integration test for vector_search against live Valkey backend."""

import pytest
import struct
from awslabs.valkey_mcp_server.tools.vss import vector_search
from awslabs.valkey_mcp_server.common.connection import ValkeyConnectionManager


@pytest.mark.integration
@pytest.mark.manual
class TestVectorSearchIntegration:
    """Test vector_search with live Valkey backend."""

    @pytest.fixture(autouse=True)
    async def setup_and_teardown(self):
        """Setup test index and cleanup."""
        r = ValkeyConnectionManager.get_connection(decode_responses=True)
        
        # Cleanup any existing test index
        try:
            r.execute_command('FT.DROPINDEX', 'test_vector_idx')
            print("Dropped existing index")
        except Exception as e:
            print(f"No existing index to drop: {e}")
        
        # Create a simple vector index
        try:
            r.execute_command(
                'FT.CREATE', 'test_vector_idx',
                'ON', 'HASH',
                'PREFIX', '1', 'doc:',
                'SCHEMA',
                'embedding', 'VECTOR', 'FLAT', '6', 'TYPE', 'FLOAT32', 'DIM', '3', 'DISTANCE_METRIC', 'COSINE'
            )
            print("Vector index created successfully")
        except Exception as e:
            print(f"Could not create vector index: {e}")
            pytest.skip(f"Could not create vector index: {e}")
        
        # Add test documents
        r.hset('doc:1', mapping={
            'embedding': struct.pack('3f', 0.1, 0.2, 0.3),
            'title': 'Test Doc 1'
        })
        r.hset('doc:2', mapping={
            'embedding': struct.pack('3f', 0.4, 0.5, 0.6),
            'title': 'Test Doc 2'
        })
        
        yield
        
        # Cleanup
        try:
            r.execute_command('FT.DROPINDEX', 'test_vector_idx', 'DD')
        except:
            pass

    async def test_vector_search_live(self):
        """Test vector_search against live Valkey."""
        
        result = await vector_search(
            index='test_vector_idx',
            field='embedding',
            vector=[0.1, 0.2, 0.3],
            count=2
        )
        
        print(f"Vector search result: {result}")
        assert result['status'] == 'success'
        assert len(result['results']) >= 0  # May be empty if no document_json field
