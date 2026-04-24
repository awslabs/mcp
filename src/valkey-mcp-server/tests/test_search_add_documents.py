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

"""Unit tests for add_documents tool."""

import pytest
from awslabs.valkey_mcp_server.tools.search_add_documents import add_documents
from unittest.mock import AsyncMock, Mock, patch


pytestmark = pytest.mark.asyncio

MODULE = 'awslabs.valkey_mcp_server.tools.search_add_documents'


@pytest.fixture()
def mock_client():
    c = AsyncMock()
    c.hset = AsyncMock()
    return c


@pytest.fixture(autouse=True)
def _patch_client(mock_client):
    with patch(f'{MODULE}.get_client', return_value=mock_client):
        yield


@pytest.fixture()
def mock_provider():
    p = Mock()
    p.generate_embedding = AsyncMock(return_value=[0.1, 0.2, 0.3, 0.4])
    p.get_provider_name = Mock(return_value='fake')
    p.get_dimensions = Mock(return_value=4)
    return p


class TestAddDocumentsPlain:
    async def test_add_plain_documents(self, mock_client):
        result = await add_documents(
            index_name='idx',
            documents=[{'id': '1', 'title': 'Hello'}, {'id': '2', 'title': 'World'}],
            prefix='doc:',
        )
        assert result['status'] == 'success'
        assert result['added'] == 2
        assert result['errors'] == 0
        assert mock_client.hset.call_count == 2

    async def test_default_prefix(self, mock_client):
        await add_documents(index_name='myidx', documents=[{'id': '1', 'title': 'x'}])
        mock_client.hset.assert_called_once()
        key = mock_client.hset.call_args[0][0]
        assert key == 'myidx:1'

    async def test_missing_id_skipped(self):
        result = await add_documents(
            index_name='idx', documents=[{'title': 'no id'}], prefix='doc:'
        )
        assert result['status'] == 'error'
        assert result['added'] == 0
        assert result['errors'] == 1

    async def test_dict_values_json_serialized(self, mock_client):
        await add_documents(
            index_name='idx',
            documents=[{'id': '1', 'meta': {'a': 1}}],
            prefix='doc:',
        )
        mapping = mock_client.hset.call_args[0][1]
        assert mapping['meta'] == '{"a": 1}'


class TestAddDocumentsWithEmbeddings:
    async def test_embedding_generation(self, mock_client, mock_provider):
        with (
            patch(f'{MODULE}._get_provider', return_value=mock_provider),
            patch(f'{MODULE}.index_exists', return_value=True),
        ):
            result = await add_documents(
                index_name='idx',
                documents=[{'id': '1', 'title': 'Hello'}],
                prefix='doc:',
                embedding_field='embedding',
                text_fields=['title'],
            )
        assert result['status'] == 'success'
        assert result['added'] == 1
        assert result['embedding_dimensions'] == 4
        assert result['embeddings_provider'] == 'fake'
        mapping = mock_client.hset.call_args[0][1]
        assert 'embedding' in mapping

    async def test_auto_creates_index(self, mock_client, mock_provider):
        with (
            patch(f'{MODULE}._get_provider', return_value=mock_provider),
            patch(f'{MODULE}.index_exists', return_value=False),
            patch(f'{MODULE}._auto_create_index', new_callable=AsyncMock) as mock_create,
        ):
            result = await add_documents(
                index_name='idx',
                documents=[{'id': '1', 'title': 'Hello'}],
                prefix='doc:',
                embedding_field='emb',
                text_fields=['title'],
            )
        assert result['status'] == 'success'
        mock_create.assert_called_once()

    async def test_embedding_field_without_text_fields(self):
        result = await add_documents(
            index_name='idx',
            documents=[{'id': '1'}],
            embedding_field='emb',
        )
        assert result['status'] == 'error'
        assert 'text_fields' in result['reason']


class TestAddDocumentsReadonly:
    async def test_readonly_blocked(self):
        with patch(f'{MODULE}.Context') as mock_ctx:
            mock_ctx.readonly_mode.return_value = True
            result = await add_documents(index_name='idx', documents=[{'id': '1'}])
        assert result['status'] == 'error'
        assert 'Readonly' in result['reason']
