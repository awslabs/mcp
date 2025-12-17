"""Integration test for vector_search against live Valkey backend with Bedrock embeddings."""

import pytest
import struct
from awslabs.valkey_mcp_server.common.connection import ValkeyConnectionManager
from awslabs.valkey_mcp_server.tools.vss import vector_search
from tests import acquire_bedrock_embeddings


@pytest.mark.integration
@pytest.mark.manual
class TestVectorSearchIntegration:
    """Test vector_search with live Valkey backend and Bedrock embeddings."""

    @pytest.fixture(autouse=True)
    async def setup_and_teardown(self):
        """Setup test index and cleanup."""
        r = ValkeyConnectionManager.get_connection(decode_responses=True)

        # Cleanup any existing test index
        try:
            r.execute_command('FT.DROPINDEX', 'test_vector_idx')
            print('Dropped existing index')
        except Exception as e:
            print(f'No existing index to drop: {e}')

        # Create a vector index with 1536 dimensions (Titan embedding size)
        try:
            r.execute_command(
                'FT.CREATE',
                'test_vector_idx',
                'ON',
                'HASH',
                'PREFIX',
                '1',
                'doc:',
                'SCHEMA',
                'embedding',
                'VECTOR',
                'FLAT',
                '6',
                'TYPE',
                'FLOAT32',
                'DIM',
                '1536',
                'DISTANCE_METRIC',
                'COSINE',
            )
            print('Vector index created successfully')
        except Exception as e:
            print(f'Could not create vector index: {e}')
            pytest.skip(f'Could not create vector index: {e}')

        yield

        # Cleanup
        try:
            r.execute_command('FT.DROPINDEX', 'test_vector_idx')
        except Exception:
            pass

    async def test_vector_search_with_bedrock_embeddings(self):
        """Test vector_search with live Bedrock embeddings."""
        await acquire_bedrock_embeddings()

        # Generate embedding for the first text
        text1 = 'The quick brown fox jumped over the lazy dogs'
        embedding1 = await self.provider.generate_embedding(text1)

        # Store document with embedding in Valkey
        r = ValkeyConnectionManager.get_connection(decode_responses=False)
        doc1_json = f'{{"id": "doc1", "text": "{text1}", "category": "animals"}}'

        r.hset(
            'doc:1',
            mapping={
                'embedding': struct.pack(f'{len(embedding1)}f', *embedding1),
                'document_json': doc1_json,
            },
        )

        # Add noise documents
        text2 = 'Orange juice is good for the soul, but only on Wednesdays'
        embedding2 = await self.provider.generate_embedding(text2)
        doc2_json = f'{{"id": "doc2", "text": "{text2}", "category": "beverages"}}'

        r.hset(
            'doc:2',
            mapping={
                'embedding': struct.pack(f'{len(embedding2)}f', *embedding2),
                'document_json': doc2_json,
            },
        )

        text3 = 'Scientists have discovered where all the missing unpaired socks go after going into the drier, they have found a giant ball of socks floating in outer space'
        embedding3 = await self.provider.generate_embedding(text3)
        doc3_json = f'{{"id": "doc3", "text": "{text3}", "category": "science"}}'

        r.hset(
            'doc:3',
            mapping={
                'embedding': struct.pack(f'{len(embedding3)}f', *embedding3),
                'document_json': doc3_json,
            },
        )

        # Generate embedding for the search query
        query_text = 'Something about one species of quadruped leaping over other slothful quadrupeds of another species'
        query_embedding = await self.provider.generate_embedding(query_text)

        # Perform vector search
        result = await vector_search(
            index='test_vector_idx', field='embedding', vector=query_embedding, count=1
        )

        print(f'Vector search result: {result}')
        assert result['status'] == 'success'
        assert len(result['results']) == 1
        # The first result should be the animals document due to semantic similarity
        assert result['results'][0]['id'] == 'doc1'
        assert result['results'][0]['text'] == text1
        assert result['results'][0]['category'] == 'animals'

    async def test_vector_search_dimension_mismatch(self):
        """Test vector search with dimension mismatch using hash embeddings."""
        from awslabs.valkey_mcp_server.embeddings.providers import HashEmbeddings

        index_name = 'test_vector_idx'
        field_name = 'embedding'

        # Create embeddings provider with different dimensions than test setup
        embeddings_128 = HashEmbeddings(dimensions=128)

        # Try to search with 128-dimensional vector (should fail)
        query_vector = await embeddings_128.generate_embedding('test query')
        assert len(query_vector) == 128

        result = await vector_search(index=index_name, field=field_name, vector=query_vector)

        # Should return error due to dimension mismatch
        assert result['status'] == 'error'
        assert 'valkey' in result['type']
