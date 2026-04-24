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

"""Live error-case tests — verify pre-validation prevents GLIDE crashes.

These tests call tools with invalid inputs that would crash the GLIDE native
layer if the pre-validation guards were removed. Each test verifies the server
returns a structured error and stays alive for the next test.

Requires:
    VALKEY_HOST — Valkey instance

Run:
    uv run pytest tests/test_error_cases_live.py -m live -v
"""

import pytest
from awslabs.valkey_mcp_server.tools.json import (
    json_arrappend,
    json_arrpop,
    json_arrtrim,
)
from awslabs.valkey_mcp_server.tools.search_manage_index import manage_index
from awslabs.valkey_mcp_server.tools.search_query import search
from unittest.mock import AsyncMock, patch


pytestmark = [pytest.mark.live, pytest.mark.asyncio, pytest.mark.timeout(15)]

JSON_MOD = 'awslabs.valkey_mcp_server.tools.json'
MI_MOD = 'awslabs.valkey_mcp_server.tools.search_manage_index'
SQ_MOD = 'awslabs.valkey_mcp_server.tools.search_query'


@pytest.fixture(autouse=True)
async def _patch_client(client):
    mock = AsyncMock(return_value=client)
    with (
        patch(f'{JSON_MOD}.get_client', mock),
        patch(f'{MI_MOD}.get_client', mock),
        patch(f'{SQ_MOD}.get_client', mock),
    ):
        yield


class TestJsonErrorCasesLive:
    """These cases crashed the server before pre-validation was added."""

    async def test_arrpop_nonexistent_key(self):
        result = await json_arrpop(key='nonexistent_crash_test_key')
        assert result['status'] == 'error'
        assert result['status'] == 'error'

    async def test_arrtrim_nonexistent_key(self):
        result = await json_arrtrim(key='nonexistent_crash_test_key', start=0, stop=1)
        assert result['status'] == 'error'
        assert result['status'] == 'error'

    async def test_arrappend_to_non_array(self, client):
        await client.custom_command(['JSON.SET', 'crash_test_num', '$', '42'])
        result = await json_arrappend(key='crash_test_num', values=['x'])
        assert result['status'] == 'error'
        assert 'not an array' in result['reason']
        await client.custom_command(['DEL', 'crash_test_num'])

    async def test_arrappend_nonexistent_key(self):
        result = await json_arrappend(key='nonexistent_crash_test_key', values=[1])
        assert result['status'] == 'error'
        assert result['status'] == 'error'

    async def test_server_still_alive_after_errors(self, client):
        """Verify the server didn't crash — this test runs last."""
        await client.custom_command(['JSON.SET', 'alive_check', '$', '"yes"'])
        result = await client.custom_command(['JSON.GET', 'alive_check'])
        assert result is not None
        await client.custom_command(['DEL', 'alive_check'])


class TestManageIndexErrorCasesLive:
    """These cases crashed the server before pre-validation was added."""

    async def test_info_nonexistent_index(self):
        result = await manage_index(action='info', index_name='nonexistent_crash_test_idx')
        assert result['status'] == 'error'
        assert result['status'] == 'error'

    async def test_create_duplicate_index(self, client):
        # Create an index first
        from glide import ft
        from glide_shared.commands.server_modules.ft_options.ft_create_options import (
            FtCreateOptions,
            TextField,
        )

        idx_name = 'crash_test_dup_idx'
        try:
            await ft.dropindex(client, idx_name)
        except Exception:
            pass
        await ft.create(client, idx_name, [TextField('f')], FtCreateOptions(prefixes=['ct:']))

        # Now try to create it again — this would crash without pre-validation
        result = await manage_index(
            action='create',
            index_name=idx_name,
            schema=[{'name': 'f', 'type': 'TEXT'}],
        )
        assert result['status'] == 'error'
        assert result['status'] == 'error'

        await ft.dropindex(client, idx_name)

    async def test_drop_nonexistent_index(self):
        result = await manage_index(action='drop', index_name='nonexistent_crash_test_idx')
        assert result['status'] == 'error'
        assert result['status'] == 'error'


class TestSearchErrorCasesLive:
    """Search on non-existent index would crash without pre-validation."""

    async def test_search_nonexistent_index(self):
        with patch(f'{SQ_MOD}._has_provider', return_value=False):
            result = await search(index_name='nonexistent_crash_test_idx', query_text='hello')
        assert result['status'] == 'error'
        assert result['status'] == 'error'

    async def test_find_similar_nonexistent_index(self):
        result = await search(index_name='nonexistent_crash_test_idx', document_id='doc:1')
        assert result['status'] == 'error'
        assert result['status'] == 'error'
