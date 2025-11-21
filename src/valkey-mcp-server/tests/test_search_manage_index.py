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

"""Unit tests for manage_index tool."""

import pytest
from awslabs.valkey_mcp_server.tools.search_manage_index import manage_index
from unittest.mock import AsyncMock, patch


pytestmark = pytest.mark.asyncio

MODULE = 'awslabs.valkey_mcp_server.tools.search_manage_index'


@pytest.fixture()
def mock_ft():
    m = AsyncMock()
    m.list = AsyncMock(return_value=[b'idx', b'other'])
    m.info = AsyncMock(return_value={'index_name': 'idx'})
    m.create = AsyncMock()
    m.dropindex = AsyncMock()
    return m


@pytest.fixture(autouse=True)
def _patch(mock_ft):
    with (
        patch(f'{MODULE}.get_client', return_value=AsyncMock()),
        patch(f'{MODULE}.ft', mock_ft),
    ):
        yield


def _exists(val=True):
    return patch(f'{MODULE}.index_exists', AsyncMock(return_value=val))


class TestManageIndexList:
    async def test_list_returns_decoded_names(self, mock_ft):
        mock_ft.list = AsyncMock(return_value=[b'idx1', b'idx2'])
        result = await manage_index(action='list')
        assert result == {'status': 'success', 'indices': ['idx1', 'idx2']}

    async def test_list_empty(self, mock_ft):
        mock_ft.list = AsyncMock(return_value=[])
        result = await manage_index(action='list')
        assert result == {'status': 'success', 'indices': []}


class TestManageIndexInfo:
    async def test_info_returns_data(self):
        with _exists(True):
            result = await manage_index(action='info', index_name='idx')
        assert result['status'] == 'success'

    async def test_info_missing_name(self):
        result = await manage_index(action='info')
        assert result['status'] == 'error'

    async def test_info_not_found(self):
        with _exists(False):
            result = await manage_index(action='info', index_name='nope')
        assert result['status'] == 'error'
        assert 'does not exist' in result['reason']


class TestManageIndexDrop:
    async def test_drop_success(self):
        with _exists(True):
            result = await manage_index(action='drop', index_name='idx')
        assert result == {'status': 'success', 'index_name': 'idx', 'dropped': True}

    async def test_drop_not_found(self):
        with _exists(False):
            result = await manage_index(action='drop', index_name='nope')
        assert result['status'] == 'error'

    async def test_drop_readonly(self):
        with patch(f'{MODULE}.Context') as ctx:
            ctx.readonly_mode.return_value = True
            result = await manage_index(action='drop', index_name='idx')
        assert result['status'] == 'error'


class TestManageIndexCreate:
    async def test_create_text_field(self):
        with _exists(False):
            result = await manage_index(
                action='create',
                index_name='new',
                schema=[{'name': 'title', 'type': 'TEXT'}],
            )
        assert result['status'] == 'success'

    async def test_create_vector_field(self):
        with _exists(False):
            result = await manage_index(
                action='create',
                index_name='new',
                schema=[{'name': 'vec', 'type': 'VECTOR', 'dimensions': 128}],
                prefix=['doc:'],
            )
        assert result['status'] == 'success'

    async def test_create_all_field_types(self):
        with _exists(False):
            result = await manage_index(
                action='create',
                index_name='new',
                schema=[
                    {'name': 'title', 'type': 'TEXT'},
                    {'name': 'year', 'type': 'NUMERIC'},
                    {'name': 'cat', 'type': 'TAG'},
                    {'name': 'vec', 'type': 'VECTOR', 'dimensions': 4},
                ],
            )
        assert result['status'] == 'success'

    async def test_create_flat_l2(self):
        with _exists(False):
            result = await manage_index(
                action='create',
                index_name='new',
                schema=[{'name': 'v', 'type': 'VECTOR', 'dimensions': 4}],
                structure_type='FLAT',
                distance_metric='L2',
            )
        assert result['status'] == 'success'

    async def test_create_duplicate(self):
        with _exists(True):
            result = await manage_index(
                action='create',
                index_name='idx',
                schema=[{'name': 't', 'type': 'TEXT'}],
            )
        assert result['status'] == 'error'
        assert 'already exists' in result['reason']

    async def test_create_missing_schema(self):
        with _exists(False):
            result = await manage_index(action='create', index_name='new')
        assert result['status'] == 'error'

    async def test_create_missing_field_name(self):
        with _exists(False):
            result = await manage_index(
                action='create', index_name='new', schema=[{'type': 'TEXT'}]
            )
        assert result['status'] == 'error'

    async def test_create_vector_missing_dimensions(self):
        with _exists(False):
            result = await manage_index(
                action='create',
                index_name='new',
                schema=[{'name': 'v', 'type': 'VECTOR'}],
            )
        assert result['status'] == 'error'

    async def test_create_readonly(self):
        with patch(f'{MODULE}.Context') as ctx:
            ctx.readonly_mode.return_value = True
            result = await manage_index(
                action='create',
                index_name='new',
                schema=[{'name': 't', 'type': 'TEXT'}],
            )
        assert result['status'] == 'error'


class TestManageIndexUnknownAction:
    async def test_unknown_action(self):
        with _exists(True):
            result = await manage_index(action='bogus', index_name='x')
        assert result['status'] == 'error'
        assert 'bogus' in result['reason']
