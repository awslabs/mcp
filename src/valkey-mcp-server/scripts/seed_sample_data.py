#!/usr/bin/env python3
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

"""Seed Valkey with sample documents and vector embeddings for testing VSS.

This script uses the add_documents function to populate the database
with sample product data and embeddings.
"""

import asyncio
import sys
from pathlib import Path


# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from awslabs.valkey_mcp_server.tools.semantic_search import add_documents


# Sample product data
SAMPLE_PRODUCTS = [
    {
        'id': 'prod_001',
        'name': 'Wireless Bluetooth Headphones',
        'description': 'High-quality wireless headphones with active noise cancellation, long battery life, and premium sound quality for music and calls',
        'category': 'Electronics',
        'price': 149.99,
    },
    {
        'id': 'prod_002',
        'name': 'Organic Green Tea',
        'description': 'Premium organic green tea leaves from Japan, rich in antioxidants and provides a smooth, refreshing taste',
        'category': 'Food & Beverage',
        'price': 24.99,
    },
    {
        'id': 'prod_003',
        'name': 'Running Shoes',
        'description': 'Lightweight athletic running shoes with cushioned sole and breathable mesh upper for marathon and jogging',
        'category': 'Sports & Outdoors',
        'price': 89.99,
    },
    {
        'id': 'prod_004',
        'name': 'Laptop Stand',
        'description': 'Ergonomic aluminum laptop stand for better posture and ventilation, compatible with all laptop sizes',
        'category': 'Office Supplies',
        'price': 39.99,
    },
    {
        'id': 'prod_005',
        'name': 'Yoga Mat',
        'description': 'Non-slip yoga mat with extra cushioning for comfort during meditation, pilates, and exercise',
        'category': 'Sports & Outdoors',
        'price': 29.99,
    },
    {
        'id': 'prod_006',
        'name': 'Smartwatch',
        'description': 'Fitness tracker smartwatch with heart rate monitor, GPS tracking, and smartphone notifications',
        'category': 'Electronics',
        'price': 199.99,
    },
    {
        'id': 'prod_007',
        'name': 'Coffee Maker',
        'description': 'Programmable drip coffee maker with thermal carafe, auto-brew timer, and pause-and-serve function',
        'category': 'Home & Kitchen',
        'price': 79.99,
    },
    {
        'id': 'prod_008',
        'name': 'Noise Cancelling Earbuds',
        'description': 'True wireless earbuds with active noise cancellation, water resistance, and premium audio quality',
        'category': 'Electronics',
        'price': 129.99,
    },
    {
        'id': 'prod_009',
        'name': 'Protein Powder',
        'description': 'Whey protein powder for muscle building and recovery after workouts, vanilla flavor',
        'category': 'Health & Wellness',
        'price': 44.99,
    },
    {
        'id': 'prod_010',
        'name': 'Mechanical Keyboard',
        'description': 'RGB backlit mechanical gaming keyboard with tactile switches and programmable macro keys',
        'category': 'Electronics',
        'price': 119.99,
    },
]


async def seed_data():
    """Seed Valkey with sample product data and embeddings."""
    print('🚀 Starting Valkey data seeding...')

    try:
        result = await add_documents(
            collection='products', documents=SAMPLE_PRODUCTS, text_fields=['name', 'description']
        )

        if result['status'] == 'success':
            print(f'✅ Seeding complete! {result["added"]} documents added')
            print(f'📋 Collection: {result["collection"]}')
            print(f'📋 Total documents: {result["total_documents"]}')
            print(f'📋 Embedding dimensions: {result["embedding_dimensions"]}')
            print(f'📋 Provider: {result["embeddings_provider"]}')
            print('\n🎯 Sample queries:')
            print("  - 'Search for wireless audio devices'")
            print("  - 'Find fitness equipment'")
            print("  - 'Show me beverages'")
            return True
        else:
            print(f'❌ Seeding failed: {result["reason"]}')
            return False

    except Exception as e:
        print(f'❌ Seeding failed: {e}')
        return False


if __name__ == '__main__':
    success = asyncio.run(seed_data())
    sys.exit(0 if success else 1)
