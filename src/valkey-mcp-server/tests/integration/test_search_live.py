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

"""Live integration tests for semantic search tools.

Requires:
    VALKEY_HOST — Valkey instance with search module
    EMBEDDING_PROVIDER=ollama
    OLLAMA_HOST — Ollama instance
    OLLAMA_EMBEDDING_MODEL — embedding model name

Run:
    uv run pytest tests/test_search_live.py -m live -v
"""

import pytest
import time
import uuid
from awslabs.valkey_mcp_server.tools.search_add_documents import add_documents
from awslabs.valkey_mcp_server.tools.search_aggregate import aggregate
from awslabs.valkey_mcp_server.tools.search_manage_index import manage_index
from awslabs.valkey_mcp_server.tools.search_query import search
from unittest.mock import AsyncMock, patch


pytestmark = [pytest.mark.live, pytest.mark.asyncio, pytest.mark.timeout(60)]

_PREFIX = f'test_{uuid.uuid4().hex[:8]}'


def _idx(name):
    return f'{_PREFIX}_{name}'


def _key(name):
    return f'{_PREFIX}_{name}:'


@pytest.fixture(autouse=True)
async def _patch_client(client):
    """Patch get_client at every tool module's import location."""
    import awslabs.valkey_mcp_server.embeddings as emb_mod

    # Reset centralized embeddings provider so httpx client uses current event loop
    emb_mod.reset_provider()

    mock = AsyncMock(return_value=client)
    with (
        patch('awslabs.valkey_mcp_server.tools.search_manage_index.get_client', mock),
        patch('awslabs.valkey_mcp_server.tools.search_add_documents.get_client', mock),
        patch('awslabs.valkey_mcp_server.tools.search_query.get_client', mock),
        patch('awslabs.valkey_mcp_server.tools.search_aggregate.get_client', mock),
        patch('awslabs.valkey_mcp_server.tools.json.get_client', mock),
    ):
        yield


class TestManageIndexLive:
    async def test_create_and_info(self):
        idx = _idx('mi_create')
        result = await manage_index(
            action='create',
            index_name=idx,
            schema=[
                {'name': 'title', 'type': 'TEXT'},
                {'name': 'category', 'type': 'TAG'},
                {'name': 'year', 'type': 'NUMERIC'},
                {'name': 'embedding', 'type': 'VECTOR', 'dimensions': 4},
            ],
            prefix=[_key('mi_create')],
        )
        assert result['status'] == 'success'
        assert result['created'] is True

        info = await manage_index(action='info', index_name=idx)
        assert info['status'] == 'success'

    async def test_list_includes_created(self):
        idx = _idx('mi_list')
        await manage_index(
            action='create',
            index_name=idx,
            schema=[{'name': 'f', 'type': 'TEXT'}],
            prefix=[_key('mi_list')],
        )
        result = await manage_index(action='list')
        assert result['status'] == 'success'
        assert idx in result['indices']

    async def test_drop(self):
        idx = _idx('mi_drop')
        await manage_index(
            action='create',
            index_name=idx,
            schema=[{'name': 'f', 'type': 'TEXT'}],
            prefix=[_key('mi_drop')],
        )
        result = await manage_index(action='drop', index_name=idx)
        assert result['status'] == 'success'
        assert result['dropped'] is True

        info = await manage_index(action='info', index_name=idx)
        assert info['status'] == 'error'

    async def test_create_json_type(self):
        idx = _idx('mi_json')
        result = await manage_index(
            action='create',
            index_name=idx,
            schema=[{'name': 'title', 'type': 'TEXT'}],
            prefix=[_key('mi_json')],
            index_type='JSON',
        )
        if result['status'] == 'error' and 'not loaded' in result.get('reason', ''):
            pytest.skip('JSON module not loaded on server')
        assert result['status'] == 'success'


class TestAddDocumentsLive:
    async def test_add_plain(self, client):
        idx = _idx('ad_plain')
        prefix = _key('ad_plain')
        await manage_index(
            action='create',
            index_name=idx,
            schema=[{'name': 'title', 'type': 'TEXT'}],
            prefix=[prefix],
        )
        result = await add_documents(
            index_name=idx,
            documents=[
                {'id': '1', 'title': 'First doc'},
                {'id': '2', 'title': 'Second doc'},
            ],
            prefix=prefix,
        )
        assert result['status'] == 'success'
        assert result['added'] == 2

        val = await client.hget(f'{prefix}1', 'title')
        assert val is not None

    async def test_add_with_embeddings(self):
        idx = _idx('ad_emb')
        prefix = _key('ad_emb')
        result = await add_documents(
            index_name=idx,
            documents=[
                {'id': 'a', 'title': 'Machine learning basics'},
                {'id': 'b', 'title': 'Cooking recipes for beginners'},
            ],
            prefix=prefix,
            embedding_field='embedding',
            text_fields=['title'],
        )
        assert result['status'] == 'success'
        assert result['added'] == 2
        assert result['embedding_dimensions'] is not None
        assert 'ollama' in result['embeddings_provider'].lower()

    async def test_auto_creates_index(self):
        idx = _idx('ad_auto')
        prefix = _key('ad_auto')
        result = await add_documents(
            index_name=idx,
            documents=[{'id': 'x', 'title': 'Auto create test'}],
            prefix=prefix,
            embedding_field='embedding',
            text_fields=['title'],
        )
        assert result['status'] == 'success'

        info = await manage_index(action='info', index_name=idx)
        assert info['status'] == 'success'


class TestSearchLive:
    @pytest.fixture(autouse=True)
    async def _seed_data(self, client):
        """Seed test data for search tests (once per class)."""
        idx = _idx('search')
        prefix = _key('search')
        info = await manage_index(action='info', index_name=idx)
        if info['status'] == 'success':
            return
        await manage_index(
            action='create',
            index_name=idx,
            schema=[
                {'name': 'title', 'type': 'TEXT'},
                {'name': 'category', 'type': 'TAG'},
                {'name': 'embedding', 'type': 'VECTOR', 'dimensions': 768},
            ],
            prefix=[prefix],
        )
        await add_documents(
            index_name=idx,
            documents=[
                {'id': '1', 'title': 'Introduction to machine learning', 'category': 'tech'},
                {'id': '2', 'title': 'Best pasta recipes from Italy', 'category': 'food'},
                {'id': '3', 'title': 'Deep learning neural networks', 'category': 'tech'},
            ],
            prefix=prefix,
            embedding_field='embedding',
            text_fields=['title'],
        )
        time.sleep(1)  # Let index catch up

    async def test_text_search(self):
        result = await search(
            index_name=_idx('search'),
            query_text='machine learning',
            mode='text',
        )
        assert result['status'] == 'success'
        assert result['mode'] == 'text'
        assert len(result['results']) >= 1

    async def test_semantic_search(self):
        result = await search(
            index_name=_idx('search'),
            query_text='artificial intelligence',
            vector_field='embedding',
        )
        assert result['status'] == 'success'
        assert result['mode'] == 'semantic'
        assert len(result['results']) >= 1

    async def test_find_similar(self):
        prefix = _key('search')
        result = await search(
            index_name=_idx('search'),
            document_id=f'{prefix}1',
            vector_field='embedding',
        )
        assert result['status'] == 'success'
        assert result['mode'] == 'find_similar'
        ids = [r['id'] for r in result['results']]
        assert f'{prefix}1' not in ids

    async def test_hybrid_search(self):
        result = await search(
            index_name=_idx('search'),
            query_text='machine learning',
            vector_field='embedding',
            mode='hybrid',
            hybrid_weight=0.7,
        )
        assert result['status'] == 'success'
        assert result['mode'] == 'hybrid'


class TestAggregateLive:
    @pytest.fixture(autouse=True)
    async def _seed_products(self, client):
        """Seed product data for aggregate tests (once per class)."""
        idx = _idx('agg')
        prefix = _key('agg')
        # Only seed if index doesn't exist yet
        info = await manage_index(action='info', index_name=idx)
        if info['status'] == 'success':
            return
        await manage_index(
            action='create',
            index_name=idx,
            schema=[
                {'name': 'title', 'type': 'TEXT'},
                {'name': 'category', 'type': 'TAG'},
                {'name': 'price', 'type': 'NUMERIC'},
            ],
            prefix=[prefix],
        )
        await add_documents(
            index_name=idx,
            documents=[
                {'id': '1', 'category': 'electronics', 'price': 100, 'title': 'phone'},
                {'id': '2', 'category': 'electronics', 'price': 200, 'title': 'laptop'},
                {'id': '3', 'category': 'books', 'price': 15, 'title': 'novel'},
                {'id': '4', 'category': 'books', 'price': 25, 'title': 'textbook'},
                {'id': '5', 'category': 'books', 'price': 10, 'title': 'comic'},
            ],
            prefix=prefix,
        )
        time.sleep(1)  # Let index catch up

    async def test_groupby_count(self):
        result = await aggregate(
            index_name=_idx('agg'),
            query='@price:[0 500]',
            pipeline=[
                {
                    'type': 'GROUPBY',
                    'fields': ['@category'],
                    'reducers': [{'function': 'COUNT', 'alias': 'cnt'}],
                }
            ],
        )
        assert result['status'] == 'success'
        assert len(result['results']) >= 1
        total = sum(int(r['cnt']) for r in result['results'])
        assert total == 5

    async def test_groupby_avg_with_apply(self):
        result = await aggregate(
            index_name=_idx('agg'),
            query='@category:{electronics}',
            pipeline=[
                {
                    'type': 'GROUPBY',
                    'fields': ['@category'],
                    'reducers': [{'function': 'AVG', 'field': '@price', 'alias': 'avg_price'}],
                },
                {'type': 'APPLY', 'expression': '@avg_price * 1.1', 'alias': 'with_tax'},
            ],
        )
        assert result['status'] == 'success'
        assert len(result['results']) >= 1
        assert 'with_tax' in result['results'][0]

    async def test_filter_and_limit(self):
        result = await aggregate(
            index_name=_idx('agg'),
            query='@price:[0 500]',
            pipeline=[
                {
                    'type': 'GROUPBY',
                    'fields': ['@category'],
                    'reducers': [{'function': 'SUM', 'field': '@price', 'alias': 'total'}],
                },
                {'type': 'LIMIT', 'offset': 0, 'count': 1},
            ],
        )
        assert result['status'] == 'success'
        assert len(result['results']) == 1
        assert int(result['results'][0]['total']) > 0
