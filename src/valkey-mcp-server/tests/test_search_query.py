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

"""Unit tests for unified search tool."""

import pytest
import struct
from awslabs.valkey_mcp_server.tools.search_query import _decode_docs, search
from unittest.mock import AsyncMock, Mock, patch


pytestmark = pytest.mark.asyncio

MODULE = 'awslabs.valkey_mcp_server.tools.search_query'


@pytest.fixture()
def mock_client():
    c = AsyncMock()
    c.exists = AsyncMock(return_value=1)
    return c


@pytest.fixture()
def mock_ft():
    m = AsyncMock()
    m.list = AsyncMock(return_value=[b'idx'])
    m.search = AsyncMock(return_value=[0, {}])
    return m


@pytest.fixture(autouse=True)
def _patch(mock_client, mock_ft):
    with (
        patch(f'{MODULE}.get_client', return_value=mock_client),
        patch(f'{MODULE}.ft', mock_ft),
    ):
        yield


@pytest.fixture()
def mock_provider():
    p = Mock()
    p.generate_embedding = AsyncMock(return_value=[0.1, 0.2, 0.3, 0.4])
    p.get_provider_name = Mock(return_value='fake')
    return p


def _make_search_result(docs_dict):
    encoded = {}
    for key, fields in docs_dict.items():
        encoded[key.encode()] = {k.encode(): v.encode() for k, v in fields.items()}
    return [len(docs_dict), encoded]


class TestDecodeDocs:
    def test_basic_decode(self):
        results = [1, {b'doc:1': {b'title': b'Hello', b'score': b'0.9'}}]
        docs = _decode_docs(results)
        assert len(docs) == 1
        assert docs[0]['id'] == 'doc:1'
        assert docs[0]['title'] == 'Hello'

    def test_skip_field(self):
        results = [1, {b'doc:1': {b'title': b'Hello', b'embedding': b'\x00\x00'}}]
        docs = _decode_docs(results, skip_field='embedding')
        assert 'embedding' not in docs[0]

    def test_return_fields_filter(self):
        results = [1, {b'doc:1': {b'title': b'Hello', b'body': b'World'}}]
        docs = _decode_docs(results, return_fields=['title'])
        assert 'title' in docs[0]
        assert 'body' not in docs[0]
        assert 'id' in docs[0]

    def test_empty_results(self):
        assert _decode_docs([0, {}]) == []


class TestSearchNoParams:
    async def test_no_query_or_doc_id(self):
        result = await search(index_name='idx')
        assert result['status'] == 'error'
        assert 'query_text' in result['reason']


class TestTextSearch:
    async def test_text_mode_when_no_provider(self, mock_ft):
        mock_ft.search = AsyncMock(
            return_value=_make_search_result(
                {
                    'doc:1': {'title': 'machine learning'},
                }
            )
        )
        with patch(f'{MODULE}._has_provider', return_value=False):
            result = await search(index_name='idx', query_text='machine')
        assert result['status'] == 'success'
        assert result['mode'] == 'text'
        assert len(result['results']) == 1

    async def test_text_with_filter(self, mock_ft):
        with patch(f'{MODULE}._has_provider', return_value=False):
            await search(
                index_name='idx', query_text='hello', filter_expression='@year:[2020 2024]'
            )
            query_arg = mock_ft.search.call_args.kwargs['query']
            assert '@year:[2020 2024]' in query_arg


class TestSemanticSearch:
    async def test_semantic_mode(self, mock_ft, mock_provider):
        mock_ft.search = AsyncMock(
            return_value=_make_search_result(
                {
                    'doc:1': {'title': 'cats', 'score': '0.95'},
                }
            )
        )
        with (
            patch(f'{MODULE}._has_provider', return_value=True),
            patch(f'{MODULE}._get_provider', return_value=mock_provider),
        ):
            result = await search(index_name='idx', query_text='animals')
        assert result['status'] == 'success'
        assert result['mode'] == 'semantic'
        mock_provider.generate_embedding.assert_called_once_with('animals')


class TestHybridSearch:
    async def test_hybrid_mode(self, mock_ft, mock_provider):
        with (
            patch(f'{MODULE}._has_provider', return_value=True),
            patch(f'{MODULE}._get_provider', return_value=mock_provider),
        ):
            result = await search(index_name='idx', query_text='animals', hybrid_weight=0.8)
        assert result['mode'] == 'hybrid'
        assert result['hybrid_weight'] == 0.8


class TestFindSimilar:
    async def test_find_similar_mode(self, mock_client, mock_ft):
        vec = struct.pack('4f', 0.1, 0.2, 0.3, 0.4)
        mock_client.hget = AsyncMock(return_value=vec)
        mock_ft.search = AsyncMock(
            return_value=_make_search_result(
                {
                    'doc:1': {'title': 'source', 'score': '1.0'},
                    'doc:2': {'title': 'similar', 'score': '0.9'},
                }
            )
        )
        result = await search(index_name='idx', document_id='doc:1')
        assert result['mode'] == 'find_similar'
        ids = [d['id'] for d in result['results']]
        assert 'doc:1' not in ids

    async def test_find_similar_doc_not_found(self, mock_client):
        mock_client.hget = AsyncMock(return_value=None)
        result = await search(index_name='idx', document_id='missing')
        assert result['status'] == 'error'
        assert 'not found' in result['reason']
