#!/usr/bin/env python3
"""
Seed Valkey with sample documents and vector embeddings for testing VSS.

This script creates a sample index and populates it with product documents,
each with a vector embedding generated from the product description.
"""

import asyncio
import os
import sys
import struct
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from awslabs.valkey_mcp_server.embeddings import create_embeddings_provider
from awslabs.valkey_mcp_server.common.connection import ValkeyConnectionManager


# Sample product data
SAMPLE_PRODUCTS = [
    {
        "id": "prod_001",
        "name": "Wireless Bluetooth Headphones",
        "description": "High-quality wireless headphones with active noise cancellation, long battery life, and premium sound quality for music and calls",
        "category": "Electronics",
        "price": 149.99
    },
    {
        "id": "prod_002",
        "name": "Organic Green Tea",
        "description": "Premium organic green tea leaves from Japan, rich in antioxidants and provides a smooth, refreshing taste",
        "category": "Food & Beverage",
        "price": 24.99
    },
    {
        "id": "prod_003",
        "name": "Running Shoes",
        "description": "Lightweight athletic running shoes with cushioned sole and breathable mesh upper for marathon and jogging",
        "category": "Sports & Outdoors",
        "price": 89.99
    },
    {
        "id": "prod_004",
        "name": "Laptop Stand",
        "description": "Ergonomic aluminum laptop stand for better posture and ventilation, compatible with all laptop sizes",
        "category": "Office Supplies",
        "price": 39.99
    },
    {
        "id": "prod_005",
        "name": "Yoga Mat",
        "description": "Non-slip yoga mat with extra cushioning for comfort during meditation, pilates, and exercise",
        "category": "Sports & Outdoors",
        "price": 29.99
    },
    {
        "id": "prod_006",
        "name": "Smartwatch",
        "description": "Fitness tracker smartwatch with heart rate monitor, GPS tracking, and smartphone notifications",
        "category": "Electronics",
        "price": 199.99
    },
    {
        "id": "prod_007",
        "name": "Coffee Maker",
        "description": "Programmable drip coffee maker with thermal carafe, auto-brew timer, and pause-and-serve function",
        "category": "Home & Kitchen",
        "price": 79.99
    },
    {
        "id": "prod_008",
        "name": "Noise Cancelling Earbuds",
        "description": "True wireless earbuds with active noise cancellation, water resistance, and premium audio quality",
        "category": "Electronics",
        "price": 129.99
    },
    {
        "id": "prod_009",
        "name": "Protein Powder",
        "description": "Whey protein powder for muscle building and recovery after workouts, vanilla flavor",
        "category": "Health & Wellness",
        "price": 44.99
    },
    {
        "id": "prod_010",
        "name": "Mechanical Keyboard",
        "description": "RGB backlit mechanical gaming keyboard with tactile switches and programmable macro keys",
        "category": "Electronics",
        "price": 119.99
    }
]


async def seed_data():
    """Seed Valkey with sample product data and embeddings."""

    print("🚀 Starting Valkey data seeding...")

    # Initialize embeddings provider
    try:
        embeddings_provider = create_embeddings_provider()
        print(f"✅ Embeddings provider: {embeddings_provider.get_provider_name()}")
        print(f"   Dimensions: {embeddings_provider.get_dimensions()}")
    except Exception as e:
        print(f"❌ Failed to initialize embeddings provider: {e}")
        print("\nMake sure you have:")
        print("  - Ollama running: ollama serve")
        print("  - Model pulled: ollama pull nomic-embed-text")
        print("\nOr configure a different provider via EMBEDDINGS_PROVIDER env var")
        return False

    # Connect to Valkey
    try:
        r = ValkeyConnectionManager.get_connection(decode_responses=True)
        r.ping()
        print("✅ Connected to Valkey")
    except Exception as e:
        print(f"❌ Failed to connect to Valkey: {e}")
        print("\nMake sure Valkey is running on the configured host/port")
        return False

    # Index configuration
    # Use the naming convention expected by semantic_search tools
    # (semantic_collection_{collection_name})
    index_name = "semantic_collection_products"
    vector_dimensions = embeddings_provider.get_dimensions()

    # Drop existing index if it exists
    try:
        r.execute_command('FT.DROPINDEX', index_name, 'DD')
        print(f"🗑️  Dropped existing index: {index_name}")
    except:
        pass  # Index didn't exist

    # Create vector search index
    # Note: Valkey doesn't support TEXT fields yet, so we only index:
    # - category (TAG) for filtering
    # - price (NUMERIC) for range queries
    # - embedding (VECTOR) for similarity search
    # The 'name' and 'description' fields are still stored in the hash,
    # but not indexed for full-text search
    try:
        r.execute_command(
            'FT.CREATE', index_name,
            'ON', 'HASH',
            'PREFIX', '1', 'semantic_collection_products:doc:',
            'SCHEMA',
            'category', 'TAG',
            'price', 'NUMERIC',
            'embedding', 'VECTOR', 'FLAT', '6',
            'TYPE', 'FLOAT32',
            'DIM', str(vector_dimensions),
            'DISTANCE_METRIC', 'L2'
        )
        print(f"✅ Created index: {index_name}")
        print(f"   Indexed fields: category (TAG), price (NUMERIC), embedding (VECTOR)")
        print(f"   Vector dimensions: {vector_dimensions}")
        print(f"   Note: name and description are stored but not indexed (TEXT not yet supported in Valkey)")
    except Exception as e:
        print(f"❌ Failed to create index: {e}")
        return False

    # Add sample products
    print(f"\n📦 Adding {len(SAMPLE_PRODUCTS)} sample products...")

    for i, product in enumerate(SAMPLE_PRODUCTS, 1):
        # Use the same key prefix as the index
        product_key = f"semantic_collection_products:doc:{product['id']}"

        try:
            # Generate embedding from description
            embedding = await embeddings_provider.generate_embedding(product['description'])
            embedding_bytes = struct.pack(f'{len(embedding)}f', *embedding)

            # Store product with embedding
            r.hset(product_key, mapping={
                'name': product['name'],
                'description': product['description'],
                'category': product['category'],
                'price': str(product['price']),
                'embedding': embedding_bytes
            })

            print(f"  [{i:2d}/{len(SAMPLE_PRODUCTS)}] {product['name']}")

        except Exception as e:
            print(f"  ❌ Failed to add {product['name']}: {e}")

    # Wait for indexing
    await asyncio.sleep(0.5)

    # Verify
    try:
        info = r.execute_command('FT.INFO', index_name)
        # Parse the info response to get document count
        info_dict = dict(zip(info[::2], info[1::2]))
        num_docs = info_dict.get(b'num_docs', info_dict.get('num_docs', 0))
        print(f"\n✅ Seeding complete! {num_docs} documents indexed")
        print(f"\n📋 Collection name: products")
        print(f"📋 Index name: {index_name}")
        print(f"📋 Vector field: embedding")
        print(f"📋 Dimensions: {vector_dimensions}")
        print("\n🎯 For high-level semantic_search, try:")
        print('  semantic_search(collection="products", query="wireless audio device")')
        print("\n🎯 For low-level vector_search, use:")
        print(f'  1. vector = generate_embedding("wireless audio device")')
        print(f'  2. vector_search(index="{index_name}", field="embedding", vector=vector)')
        print("\n🎯 Sample natural language queries:")
        print("  - 'Search the products collection for wireless audio devices'")
        print("  - 'Find fitness equipment in the products collection'")
        print("  - 'Show me healthy beverages from the products collection'")

        return True

    except Exception as e:
        print(f"⚠️  Could not verify index: {e}")
        return False


if __name__ == "__main__":
    success = asyncio.run(seed_data())
    sys.exit(0 if success else 1)
