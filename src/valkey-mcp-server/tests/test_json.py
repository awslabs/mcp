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

"""Unit tests for JSON Intelligence tools."""

import pytest
from awslabs.valkey_mcp_server.tools.json import (
    json_arrappend,
    json_arrpop,
    json_arrtrim,
    json_get,
    json_set,
)
from unittest.mock import AsyncMock, patch


pytestmark = pytest.mark.asyncio

MODULE = 'awslabs.valkey_mcp_server.tools.json'


@pytest.fixture()
def mock_client():
    c = AsyncMock()
    c.custom_command = AsyncMock()
    c.expire = AsyncMock()
    return c


@pytest.fixture(autouse=True)
def _patch_client(mock_client):
    with patch(f'{MODULE}.get_client', return_value=mock_client):
        yield


class TestJsonGet:
    async def test_get_success(self, mock_client):
        mock_client.custom_command.return_value = b'[42]'
        result = await json_get(key='k', path='$.val')
        assert result == {'status': 'success', 'value': 42}
        mock_client.custom_command.assert_called_with(['JSON.GET', 'k', '$.val'])

    async def test_get_default_path(self, mock_client):
        mock_client.custom_command.return_value = b'{"a":1}'
        result = await json_get(key='k')
        assert result['status'] == 'success'
        mock_client.custom_command.assert_called_with(['JSON.GET', 'k', '$'])

    async def test_get_not_found(self, mock_client):
        mock_client.custom_command.return_value = None
        result = await json_get(key='missing')
        assert result['status'] == 'error'
        assert 'not found' in result['reason']

    async def test_get_error(self, mock_client):
        mock_client.custom_command.side_effect = Exception('fail')
        result = await json_get(key='k')
        assert result['status'] == 'error'


class TestJsonSet:
    async def test_set_success(self, mock_client):
        result = await json_set(key='k', value={'a': 1})
        assert result == {'status': 'success'}
        cmd = mock_client.custom_command.call_args[0][0]
        assert cmd[0] == 'JSON.SET'
        assert cmd[3] == '{"a": 1}'

    async def test_set_with_ttl(self, mock_client):
        await json_set(key='k', value='hello', ttl=60)
        mock_client.expire.assert_called_once_with('k', 60)

    async def test_set_without_ttl(self, mock_client):
        await json_set(key='k', value='hello')
        mock_client.expire.assert_not_called()

    async def test_set_readonly(self):
        with patch('awslabs.valkey_mcp_server.context.Context') as mock_ctx:
            mock_ctx.readonly_mode.return_value = True
            result = await json_set(key='k', value='x')
        assert result['status'] == 'error'
        assert 'Readonly' in result['reason']


class TestJsonArrappend:
    @pytest.fixture(autouse=True)
    def _mock_type(self):
        with patch(f'{MODULE}._get_json_type', AsyncMock(return_value='array')):
            yield

    async def test_append_success(self, mock_client):
        mock_client.custom_command.return_value = 3
        result = await json_arrappend(key='k', values=[1, 2])
        assert result == {'status': 'success', 'new_length': 3}

    async def test_append_readonly(self):
        with patch('awslabs.valkey_mcp_server.context.Context') as mock_ctx:
            mock_ctx.readonly_mode.return_value = True
            result = await json_arrappend(key='k', values=[1])
        assert result['status'] == 'error'

    async def test_append_nonexistent_key(self):
        with patch(f'{MODULE}._get_json_type', AsyncMock(return_value=None)):
            result = await json_arrappend(key='nope', values=[1])
        assert result['status'] == 'error'
        assert 'does not exist' in result['reason']

    async def test_append_non_array(self):
        with patch(f'{MODULE}._get_json_type', AsyncMock(return_value='integer')):
            result = await json_arrappend(key='k', values=[1])
        assert result['status'] == 'error'
        assert 'not an array' in result['reason']


class TestJsonArrpop:
    @pytest.fixture(autouse=True)
    def _mock_type(self):
        with patch(f'{MODULE}._get_json_type', AsyncMock(return_value='array')):
            yield

    async def test_pop_success(self, mock_client):
        mock_client.custom_command.return_value = b'"hello"'
        result = await json_arrpop(key='k')
        assert result == {'status': 'success', 'popped': 'hello'}

    async def test_pop_with_index(self, mock_client):
        mock_client.custom_command.return_value = b'42'
        result = await json_arrpop(key='k', path='$.arr', index=0)
        assert result['popped'] == 42

    async def test_pop_readonly(self):
        with patch('awslabs.valkey_mcp_server.context.Context') as mock_ctx:
            mock_ctx.readonly_mode.return_value = True
            result = await json_arrpop(key='k')
        assert result['status'] == 'error'

    async def test_pop_nonexistent_key(self):
        with patch(f'{MODULE}._get_json_type', AsyncMock(return_value=None)):
            result = await json_arrpop(key='nope')
        assert result['status'] == 'error'


class TestJsonArrtrim:
    @pytest.fixture(autouse=True)
    def _mock_type(self):
        with patch(f'{MODULE}._get_json_type', AsyncMock(return_value='array')):
            yield

    async def test_trim_success(self, mock_client):
        mock_client.custom_command.return_value = 3
        result = await json_arrtrim(key='k', start=0, stop=2)
        assert result == {'status': 'success', 'new_length': 3}
        cmd = mock_client.custom_command.call_args[0][0]
        assert cmd == ['JSON.ARRTRIM', 'k', '$', '0', '2']

    async def test_trim_readonly(self):
        with patch('awslabs.valkey_mcp_server.context.Context') as mock_ctx:
            mock_ctx.readonly_mode.return_value = True
            result = await json_arrtrim(key='k', start=0, stop=1)
        assert result['status'] == 'error'

    async def test_trim_nonexistent_key(self):
        with patch(f'{MODULE}._get_json_type', AsyncMock(return_value=None)):
            result = await json_arrtrim(key='nope', start=0, stop=1)
        assert result['status'] == 'error'
