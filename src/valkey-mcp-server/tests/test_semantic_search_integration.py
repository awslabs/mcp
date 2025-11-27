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

"""Integration tests for AI-friendly semantic search tools."""
import os

import pytest
from awslabs.valkey_mcp_server.tools.semantic_search import (
    add_documents,
    semantic_search,
    find_similar_documents,
    get_document,
    list_collections
)
from awslabs.valkey_mcp_server.common.connection import ValkeyConnectionManager
from awslabs.valkey_mcp_server.common.config import VALKEY_CFG
from valkey.exceptions import ValkeyError


@pytest.mark.integration
@pytest.mark.manual
class TestSemanticSearchIntegration:
    """Integration tests for semantic search functionality."""

    @pytest.fixture(autouse=True)
    def setup_valkey_config(self):
        """Configure Valkey connection to use environment variables."""
        original_config = VALKEY_CFG.copy()

        # Override configuration for integration test
        VALKEY_CFG['host'] = os.environ.get('VALKEY_HOST', 'localhost')
        VALKEY_CFG['port'] = int(os.environ.get('VALKEY_PORT', 6379))
        VALKEY_CFG['cluster_mode'] = os.environ.get('VALKEY_CLUSTER_MODE', 'false').lower() == 'true'

        # Reset connection instance to force new connection with new config
        ValkeyConnectionManager.reset()

        yield

        # Restore original configuration
        VALKEY_CFG.update(original_config)
        ValkeyConnectionManager.reset()

    @pytest.mark.asyncio
    async def test_semantic_search_workflow(self):
        """Test complete workflow: add documents, search, find similar, retrieve."""
        collection = "test_articles"

        print("\n" + "="*70)
        print("TESTING AI-FRIENDLY SEMANTIC SEARCH")
        print("="*70)

        # Step 1: Add documents
        print("\n1. Adding documents to collection...")
        documents = [
            {
                "id": "article_1",
                "title": "Climate Change Impact on Agriculture",
                "content": "Rising temperatures are affecting crop yields worldwide. Farmers are adapting to new weather patterns.",
                "author": "Dr. Jane Smith",
                "year": 2024
            },
            {
                "id": "article_2",
                "title": "Renewable Energy Solutions",
                "content": "Solar and wind power are becoming more cost-effective. Clean energy transition is accelerating globally.",
                "author": "Prof. John Doe",
                "year": 2024
            },
            {
                "id": "article_3",
                "title": "AI in Healthcare Diagnostics",
                "content": "Machine learning algorithms are improving medical diagnosis accuracy. AI is transforming healthcare delivery.",
                "author": "Dr. Sarah Lee",
                "year": 2023
            },
            {
                "id": "article_4",
                "title": "Sustainable Farming Practices",
                "content": "Organic farming and crop rotation help maintain soil health. Sustainable agriculture protects the environment.",
                "author": "Dr. Jane Smith",
                "year": 2024
            }
        ]

        result = await add_documents(
            collection=collection,
            documents=documents,
            text_fields=["title", "content"]
        )

        print(f"   ✓ Added {result['added']} documents")
        print(f"   ✓ Total in collection: {result['total_documents']}")
        assert result['status'] == 'success'
        assert result['added'] == 4

        # Step 2: Semantic search
        print("\n2. Searching for 'farming and agriculture'...")
        search_results = await semantic_search(
            collection=collection,
            query="farming and agriculture",
            limit=2
        )

        print(f"   ✓ Found {len(search_results)} results:")
        for doc in search_results:
            print(f"     - {doc['id']}: {doc['title']}")

        assert len(search_results) > 0
        # Should find agriculture-related articles
        titles = [doc['title'] for doc in search_results]
        assert any('Agriculture' in title or 'Farming' in title for title in titles)

        # Step 3: Find similar documents
        print("\n3. Finding documents similar to article_1...")
        similar_docs = await find_similar_documents(
            collection=collection,
            document_id="article_1",
            limit=2
        )

        print(f"   ✓ Found {len(similar_docs)} similar documents:")
        for doc in similar_docs:
            print(f"     - {doc['id']}: {doc['title']}")

        assert len(similar_docs) > 0

        # Step 4: Get specific document
        print("\n4. Retrieving article_2...")
        doc = await get_document(
            collection=collection,
            document_id="article_2"
        )

        print(f"   ✓ Retrieved: {doc['title']}")
        print(f"     Author: {doc['author']}")
        print(f"     Year: {doc['year']}")

        assert doc is not None
        assert doc['id'] == "article_2"
        assert doc['title'] == "Renewable Energy Solutions"

        # Step 5: List collections
        print("\n5. Listing all collections...")
        collections = await list_collections()

        print(f"   ✓ Found {len(collections)} collections:")
        for coll in collections:
            print(f"     - {coll['name']}: {coll['document_count']} documents")

        assert any(c['name'] == collection for c in collections)

        print("\n" + "="*70)
        print("✓ ALL TESTS PASSED - Semantic search is working!")
        print("="*70)

        # Print cleanup commands
        print("\nTo clean up test data:")
        print(f"  valkey-cli -h {VALKEY_CFG['host']} -p {VALKEY_CFG['port']} FT.DROPINDEX semantic_collection_{collection}")
        print(f"  valkey-cli -h {VALKEY_CFG['host']} -p {VALKEY_CFG['port']} DEL semantic_collection_{collection}:doc:article_*")
        print()
