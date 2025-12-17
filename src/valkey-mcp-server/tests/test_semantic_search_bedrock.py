"""Integration test for add_documents and semantic_search with Bedrock embeddings.

This test directly instantiates the Bedrock provider and patches the module-level
provider to test the semantic_search workflow end-to-end.
"""

import asyncio
import pytest
from awslabs.valkey_mcp_server.common.connection import ValkeyConnectionManager
from awslabs.valkey_mcp_server.embeddings.providers import BedrockEmbeddings
from awslabs.valkey_mcp_server.tools.semantic_search import add_documents, semantic_search
from unittest.mock import patch


@pytest.mark.integration
@pytest.mark.manual
class TestSemanticSearchBedrock:
    """Test semantic search with Bedrock embeddings provider."""

    @pytest.fixture(autouse=True)
    async def setup_and_teardown(self):
        """Clean up before and after test."""
        r = ValkeyConnectionManager.get_connection(decode_responses=True)

        # Check Valkey availability and search module
        try:
            conn = r
            # Test basic connection
            conn.ping()
            # Test search module availability
            conn.execute_command('FT._LIST')
        except Exception as e:
            pytest.skip(f'Valkey is not available or search module is missing: {e}')

        try:
            r.execute_command('FT.DROPINDEX', 'semantic_collection_bedrock_test', 'DD')
        except Exception:
            pass

        yield

        try:
            r.execute_command('FT.DROPINDEX', 'semantic_collection_bedrock_test', 'DD')
        except Exception:
            pass

    async def test_bedrock_semantic_search(self):
        """Test add_documents and semantic_search with Bedrock provider."""
        provider = BedrockEmbeddings(
            region_name='us-east-1', model_id='amazon.titan-embed-text-v1'
        )

        documents = [
            {
                'id': 'coffee_001',
                'name': 'Espresso Coffee',
                'content': 'Strong espresso coffee with high caffeine content to keep you alert and awake',
            },
            {
                'id': 'tea_001',
                'name': 'Green Tea',
                'content': 'Organic green tea with natural antioxidants and mild caffeine for gentle energy',
            },
            {
                'id': 'drink_001',
                'name': 'Energy Drink',
                'content': 'High-caffeine energy drink with taurine and B-vitamins for maximum alertness',
            },
            {
                'id': 'snack_001',
                'name': 'Granola Bar',
                'content': 'Healthy granola bar with oats, nuts, and honey for sustained energy',
            },
        ]

        with patch(
            'awslabs.valkey_mcp_server.tools.semantic_search._embeddings_provider', provider
        ):
            result = await add_documents(
                collection='bedrock_test', documents=documents, text_fields=['name', 'content']
            )

            assert result['status'] == 'success'
            assert result['added'] == 4
            assert result['embedding_dimensions'] == 1536
            assert 'bedrock' in result['embeddings_provider'].lower()

            await asyncio.sleep(1)

            search_result = await semantic_search(
                collection='bedrock_test', query='Drinks to keep me awake', limit=3
            )

            assert search_result['status'] == 'success'
            assert len(search_result['results']) > 0

            top_result = search_result['results'][0]
            assert top_result['id'] in ['coffee_001', 'drink_001', 'tea_001']
