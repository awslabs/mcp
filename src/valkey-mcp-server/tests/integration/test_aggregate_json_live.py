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

"""Live tests for outstanding bugs — aggregate LOAD, json_set sub-path, add_documents status.

Requires:
    VALKEY_HOST — Valkey instance with search + JSON modules

Run:
    uv run pytest tests/test_aggregate_json_live.py -m live -v
"""

import asyncio
import pytest
import uuid
from awslabs.valkey_mcp_server.tools.json import json_get, json_set
from awslabs.valkey_mcp_server.tools.search_add_documents import add_documents
from awslabs.valkey_mcp_server.tools.search_aggregate import aggregate
from awslabs.valkey_mcp_server.tools.search_manage_index import manage_index
from awslabs.valkey_mcp_server.tools.search_query import search
from unittest.mock import AsyncMock, patch


pytestmark = [pytest.mark.live, pytest.mark.asyncio, pytest.mark.timeout(30)]

_P = f'ob_{uuid.uuid4().hex[:6]}'

JSON_MOD = 'awslabs.valkey_mcp_server.tools.json'
MI_MOD = 'awslabs.valkey_mcp_server.tools.search_manage_index'
AD_MOD = 'awslabs.valkey_mcp_server.tools.search_add_documents'
AG_MOD = 'awslabs.valkey_mcp_server.tools.search_aggregate'
SQ_MOD = 'awslabs.valkey_mcp_server.tools.search_query'


@pytest.fixture(autouse=True)
async def _patch(client):
    mock = AsyncMock(return_value=client)
    with (
        patch(f'{JSON_MOD}.get_client', mock),
        patch(f'{MI_MOD}.get_client', mock),
        patch(f'{AD_MOD}.get_client', mock),
        patch(f'{AG_MOD}.get_client', mock),
        patch(f'{SQ_MOD}.get_client', mock),
    ):
        yield


@pytest.fixture()
async def products_index(client):
    """Create a products index with test data."""
    idx = f'{_P}_products'
    prefix = f'{_P}_prod:'
    await manage_index(action='drop', index_name=idx)
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
            {'id': '1', 'title': 'laptop', 'category': 'Electronics', 'price': 999},
            {'id': '2', 'title': 'headphones', 'category': 'Electronics', 'price': 99},
            {'id': '3', 'title': 'cookbook', 'category': 'Books', 'price': 25},
            {'id': '4', 'title': 'novel', 'category': 'Books', 'price': 15},
        ],
        prefix=prefix,
    )
    await asyncio.sleep(1)
    yield idx
    # Cleanup
    await manage_index(action='drop', index_name=idx)


class TestAggregateLoadBugs:
    async def test_groupby_includes_grouped_field(self, products_index):
        """GROUPBY field must appear in results (requires LOAD)."""
        result = await aggregate(
            index_name=products_index,
            query='@price:[0 inf]',
            pipeline=[
                {
                    'type': 'GROUPBY',
                    'fields': ['@category'],
                    'reducers': [{'function': 'COUNT', 'alias': 'cnt'}],
                }
            ],
        )
        assert result['status'] == 'success'
        assert len(result['results']) >= 2
        assert 'category' in result['results'][0]

    async def test_groupby_with_avg(self, products_index):
        """AVG reducer field must be LOADed."""
        result = await aggregate(
            index_name=products_index,
            query='@price:[0 inf]',
            pipeline=[
                {
                    'type': 'GROUPBY',
                    'fields': ['@category'],
                    'reducers': [
                        {'function': 'COUNT', 'alias': 'cnt'},
                        {'function': 'AVG', 'field': '@price', 'alias': 'avg_price'},
                    ],
                }
            ],
        )
        assert result['status'] == 'success'
        assert len(result['results']) >= 2
        for row in result['results']:
            assert float(row['avg_price']) > 0

    async def test_apply_on_document_field(self, products_index):
        """APPLY referencing a document field must auto-LOAD it."""
        result = await aggregate(
            index_name=products_index,
            query='@price:[0 inf]',
            pipeline=[
                {'type': 'APPLY', 'expression': '@price * 1.1', 'alias': 'taxed'},
            ],
        )
        assert result['status'] == 'success'
        assert len(result['results']) >= 1
        for row in result['results']:
            assert float(row['taxed']) > 0

    async def test_filter_on_document_field(self, products_index):
        """FILTER referencing a document field must auto-LOAD it."""
        result = await aggregate(
            index_name=products_index,
            query='@price:[0 inf]',
            pipeline=[
                {'type': 'FILTER', 'expression': '@price > 50'},
            ],
        )
        assert result['status'] == 'success'
        assert len(result['results']) >= 1

    async def test_wildcard_query(self, products_index):
        """Wildcard * query — returns error or results depending on Valkey version."""
        result = await aggregate(
            index_name=products_index,
            pipeline=[
                {
                    'type': 'GROUPBY',
                    'fields': ['@category'],
                    'reducers': [{'function': 'COUNT', 'alias': 'cnt'}],
                }
            ],
        )
        # Either succeeds or returns a clean error — must NOT crash
        assert result['status'] in ('success', 'error')

    async def test_groupby_sortby_combined(self, products_index):
        """GROUPBY + SORTBY pipeline."""
        result = await aggregate(
            index_name=products_index,
            query='@price:[0 inf]',
            pipeline=[
                {
                    'type': 'GROUPBY',
                    'fields': ['@category'],
                    'reducers': [{'function': 'COUNT', 'alias': 'cnt'}],
                },
                {
                    'type': 'SORTBY',
                    'fields': [{'field': '@cnt', 'order': 'DESC'}],
                },
            ],
        )
        assert result['status'] == 'success'
        assert len(result['results']) >= 2


class TestJsonSetSubPath:
    async def test_string_subpath_no_double_quoting(self, client):
        """Setting a string at a sub-path should not double-quote."""
        key = f'{_P}:jsonset'
        await json_set(key=key, value={'settings': {'theme': 'dark'}})
        await json_set(key=key, value='light', path='$.settings.theme')
        result = await json_get(key=key, path='$.settings.theme')
        assert result['status'] == 'success'
        assert result['value'] == 'light'  # NOT '"light"'
        await client.delete([key])

    async def test_number_subpath(self, client):
        """Setting a number at a sub-path."""
        key = f'{_P}:jsonnum'
        await json_set(key=key, value={'count': 0})
        await json_set(key=key, value=42, path='$.count')
        result = await json_get(key=key, path='$.count')
        assert result['status'] == 'success'
        assert result['value'] == 42
        await client.delete([key])

    async def test_root_set_string(self, client):
        """Setting a string at root path."""
        key = f'{_P}:jsonroot'
        await json_set(key=key, value='hello')
        result = await json_get(key=key)
        assert result['status'] == 'success'
        assert result['value'] == 'hello'
        await client.delete([key])


class TestAddDocumentsStatus:
    async def test_all_docs_fail_returns_error(self):
        """When all documents fail (missing id), status should be error."""
        result = await add_documents(
            index_name=f'{_P}_idx',
            documents=[{'title': 'no id'}, {'title': 'also no id'}],
            prefix=f'{_P}:',
        )
        assert result['status'] == 'error'
        assert result['added'] == 0
        assert result['errors'] == 2

    async def test_partial_success(self, client):
        """Mix of good and bad docs."""
        result = await add_documents(
            index_name=f'{_P}_idx',
            documents=[
                {'id': '1', 'title': 'good'},
                {'title': 'no id'},
            ],
            prefix=f'{_P}:',
        )
        assert result['status'] == 'success'
        assert result['added'] == 1
        assert result['errors'] == 1
        await client.delete([f'{_P}:1'])


class TestJsonIndexSearch:
    """Search against a JSON-backed index."""

    @pytest.fixture()
    async def json_index(self, client):
        idx = f'{_P}_json'
        prefix = f'{_P}_jdoc:'
        await manage_index(action='drop', index_name=idx)
        await manage_index(
            action='create',
            index_name=idx,
            schema=[
                {'name': 'title', 'type': 'TEXT'},
                {'name': 'category', 'type': 'TAG'},
            ],
            prefix=[prefix],
            index_type='JSON',
        )
        import json as json_mod
        from glide import glide_json

        for i, (title, cat) in enumerate(
            [('laptop', 'Electronics'), ('cookbook', 'Books'), ('headphones', 'Electronics')]
        ):
            doc = json_mod.dumps({'title': title, 'category': cat})
            await glide_json.set(client, f'{prefix}{i}', '$', doc)
        await asyncio.sleep(1)
        yield idx
        await manage_index(action='drop', index_name=idx)

    async def test_text_search_json_index(self, json_index):
        result = await search(
            index_name=json_index,
            query='laptop',
            mode='text',
        )
        assert result['status'] == 'success'
        assert result['total'] >= 1
        assert any('laptop' in str(d) for d in result['results'])

    async def test_filter_search_json_index(self, json_index):
        result = await search(
            index_name=json_index,
            query='@category:{Electronics}',
            mode='text',
        )
        assert result['status'] == 'success'
        assert result['total'] >= 2
