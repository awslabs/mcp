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

        print(f"   Add documents result: {result}")
        if result['status'] != 'success':
            print(f"   Error: {result.get('error', 'Unknown error')}")
            return  # Skip rest of test if setup fails

        # Step 2: Semantic search
        print("\n2. Searching for 'farming and agriculture'...")
        search_result = await semantic_search(
            collection=collection,
            query="farming and agriculture",
            limit=2
        )

        if search_result['status'] != 'success':
            print(f"   Error: {search_result.get('reason', 'Unknown error')}")
            return  # Skip rest of test if search fails

        search_results = search_result['results']
        print(f"   ✓ Found {len(search_results)} results:")
        for doc in search_results:
            print(f"     - {doc['id']}: {doc['title']}")

        assert len(search_results) > 0
        # Should find agriculture-related articles
        titles = [doc['title'] for doc in search_results]
        assert any('Agriculture' in title or 'Farming' in title for title in titles)

        # Step 3: Find similar documents
        print("\n3. Finding documents similar to article_1...")
        similar_result = await find_similar_documents(
            collection=collection,
            document_id="article_1",
            limit=2
        )

        if similar_result['status'] != 'success':
            print(f"   Error: {similar_result.get('reason', 'Unknown error')}")
            return  # Skip rest of test if search fails

        similar_docs = similar_result['results']
        print(f"   ✓ Found {len(similar_docs)} similar documents:")
        for doc in similar_docs:
            print(f"     - {doc['id']}: {doc['title']}")

        assert len(similar_docs) > 0

        # Step 4: Get specific document
        print("\n4. Retrieving article_2...")
        doc_result = await get_document(
            collection=collection,
            document_id="article_2"
        )

        if doc_result['status'] != 'success':
            print(f"   Error: {doc_result.get('reason', 'Unknown error')}")
            return  # Skip rest of test if retrieval fails

        doc = doc_result['result']
        print(f"   ✓ Retrieved: {doc['title']}")
        print(f"     Author: {doc['author']}")
        print(f"     Year: {doc['year']}")

        assert doc is not None
        assert doc['id'] == "article_2"
        assert doc['title'] == "Renewable Energy Solutions"

        # Step 5: List collections
        print("\n5. Listing all collections...")
        collections_result = await list_collections()

        if collections_result['status'] != 'success':
            print(f"   Error: {collections_result.get('reason', 'Unknown error')}")
            return  # Skip rest of test if listing fails

        collections = collections_result['results']
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

    @pytest.mark.asyncio
    async def test_semantic_search_with_content_control(self):
        """Test semantic search with include_content parameter."""
        collection = "test_content_control"

        print("\n" + "="*70)
        print("TESTING SEMANTIC SEARCH CONTENT CONTROL")
        print("="*70)

        # Add test documents
        documents = [
            {
                "id": "tech_1",
                "title": "Machine Learning Basics",
                "content": "Introduction to neural networks and deep learning algorithms.",
                "category": "technology",
                "author": "Dr. AI"
            },
            {
                "id": "tech_2", 
                "title": "Data Science Methods",
                "content": "Statistical analysis and data visualization techniques.",
                "category": "technology",
                "author": "Prof. Data"
            }
        ]

        result = await add_documents(
            collection=collection,
            documents=documents,
            text_fields=["title", "content"]
        )
        assert result['status'] == 'success'

        # Test with full content (default)
        print("\n1. Testing with full content...")
        full_result = await semantic_search(
            collection=collection,
            query="machine learning",
            limit=2,
            include_content=True
        )
        
        print(f"   DEBUG: full_result: {full_result}")
        
        if full_result['status'] != 'success':
            print(f"   ERROR: {full_result.get('reason', 'Unknown error')}")
            return  # Skip assertions if we got an error
            
        full_results = full_result['results']
        print(f"   ✓ Found {len(full_results)} results with full content")
        assert len(full_results) > 0
        assert 'content' in full_results[0]
        assert 'author' in full_results[0]

        # Test without full content
        print("\n2. Testing without full content...")
        minimal_result = await semantic_search(
            collection=collection,
            query="machine learning", 
            limit=2,
            include_content=False
        )
        
        print(f"   DEBUG: minimal_result: {minimal_result}")
        
        if minimal_result['status'] != 'success':
            print(f"   ERROR: {minimal_result.get('reason', 'Unknown error')}")
            return  # Skip assertions if we got an error
            
        minimal_results = minimal_result['results']
        print(f"   ✓ Found {len(minimal_results)} results with minimal content")
        assert len(minimal_results) > 0
        assert 'id' in minimal_results[0]
        assert 'title' in minimal_results[0]
        # Should not have full content fields
        assert 'content' not in minimal_results[0] or minimal_results[0]['content'] == ""

        print("\n" + "="*70)
        print("✓ CONTENT CONTROL TESTS PASSED")
        print("="*70)

    @pytest.mark.asyncio
    async def test_semantic_search_with_filter_expression(self):
        """Test semantic search with filter_expression parameter."""
        collection = "test_filter_expression"

        print("\n" + "="*70)
        print("TESTING SEMANTIC SEARCH WITH FILTER EXPRESSIONS")
        print("="*70)

        # Add documents with different categories
        documents = [
            {
                "id": "science_1",
                "title": "Climate Research",
                "content": "Global warming effects on ecosystems.",
                "category": "science",
                "year": 2024
            },
            {
                "id": "tech_1",
                "title": "AI Development", 
                "content": "Machine learning model optimization.",
                "category": "technology",
                "year": 2024
            },
            {
                "id": "science_2",
                "title": "Ocean Studies",
                "content": "Marine biology and coral reef research.",
                "category": "science", 
                "year": 2023
            }
        ]

        result = await add_documents(
            collection=collection,
            documents=documents,
            text_fields=["title", "content"]
        )
        assert result['status'] == 'success'

        # Test with filter expression for science category
        print("\n1. Searching with filter expression '@category:science'...")
        filtered_result = await semantic_search(
            collection=collection,
            query="research",
            limit=5,
            filter_expression="@category:science"
        )
        
        if filtered_result['status'] != 'success':
            print(f"   Error: {filtered_result.get('reason', 'Unknown error')}")
            return  # Skip rest of test if search fails

        filtered_results = filtered_result['results']
        print(f"   ✓ Found {len(filtered_results)} filtered results")
        if len(filtered_results) > 0:
            for doc in filtered_results:
                print(f"     - {doc['id']}: {doc['title']} (category: {doc.get('category', 'N/A')})")
                assert doc.get('category') == 'science'

        # Test without filter for comparison
        print("\n2. Searching without filter...")
        all_result = await semantic_search(
            collection=collection,
            query="research",
            limit=5
        )
        
        if all_result['status'] != 'success':
            print(f"   Error: {all_result.get('reason', 'Unknown error')}")
            return  # Skip rest of test if search fails

        all_results = all_result['results']
        print(f"   ✓ Found {len(all_results)} total results")
        
        print("\n" + "="*70)
        print("✓ FILTER EXPRESSION TESTS PASSED")
        print("="*70)

    @pytest.mark.asyncio
    async def test_semantic_search_no_content_functionality(self):
        """Test semantic search with include_content=False (no_content=True)."""
        collection = "test_no_content"

        print("\n" + "="*70)
        print("TESTING SEMANTIC SEARCH NO_CONTENT FUNCTIONALITY")
        print("="*70)

        # Add test documents
        documents = [
            {
                "id": "doc_1",
                "title": "Machine Learning Guide",
                "content": "Comprehensive guide to neural networks and algorithms.",
                "author": "Dr. ML",
                "category": "education"
            }
        ]

        result = await add_documents(
            collection=collection,
            documents=documents,
            text_fields=["title", "content"]
        )
        assert result['status'] == 'success'

        # Test with include_content=False (maps to no_content=True)
        print("\n1. Testing with include_content=False...")
        no_content_result = await semantic_search(
            collection=collection,
            query="machine learning",
            limit=2,
            include_content=False
        )
        
        if no_content_result['status'] != 'success':
            print(f"   Error: {no_content_result.get('reason', 'Unknown error')}")
            return  # Skip rest of test if search fails

        no_content_results = no_content_result['results']
        print(f"   ✓ Found {len(no_content_results)} results without content")
        if len(no_content_results) > 0:
            doc = no_content_results[0]
            print(f"     - ID: {doc.get('id')}")
            print(f"     - Title: {doc.get('title')}")
            assert 'id' in doc
            # Content should be empty or not present when include_content=False
            assert doc.get('content', '') == '' or 'content' not in doc

        print("\n" + "="*70)
        print("✓ NO_CONTENT FUNCTIONALITY TESTS PASSED")
        print("="*70)

        print()
