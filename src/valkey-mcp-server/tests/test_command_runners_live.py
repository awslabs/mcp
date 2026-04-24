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

"""Live integration tests for Command Runner tools.

Requires:
    VALKEY_HOST — Valkey instance

Run:
    uv run pytest tests/test_command_runners_live.py -m live -v
"""

import pytest
import uuid
from awslabs.valkey_mcp_server.tools.valkey_admin import valkey_admin
from awslabs.valkey_mcp_server.tools.valkey_read import valkey_read
from awslabs.valkey_mcp_server.tools.valkey_write import valkey_write
from unittest.mock import AsyncMock, patch


pytestmark = [pytest.mark.live, pytest.mark.asyncio, pytest.mark.timeout(30)]

_PREFIX = f'tcr_{uuid.uuid4().hex[:8]}'

READ_MOD = 'awslabs.valkey_mcp_server.tools.valkey_read'
WRITE_MOD = 'awslabs.valkey_mcp_server.tools.valkey_write'
ADMIN_MOD = 'awslabs.valkey_mcp_server.tools.valkey_admin'


def _k(name):
    return f'{_PREFIX}:{name}'


@pytest.fixture(autouse=True)
async def _patch_client(client):
    """Patch get_client at every tool module."""
    mock = AsyncMock(return_value=client)
    with (
        patch(f'{READ_MOD}.get_client', mock),
        patch(f'{WRITE_MOD}.get_client', mock),
        patch(f'{ADMIN_MOD}.get_client', mock),
    ):
        yield


class TestValkeyReadLive:
    async def test_get_nonexistent(self):
        result = await valkey_read(command='GET', args=[_k('noexist')])
        assert result['status'] == 'success'
        assert result['result'] is None

    async def test_set_then_get(self, client):
        key = _k('rw1')
        await client.set(key, 'hello')
        result = await valkey_read(command='GET', args=[key])
        assert result['status'] == 'success'
        assert result['result'] == 'hello'
        await client.delete([key])

    async def test_hgetall(self, client):
        key = _k('hash1')
        await client.hset(key, {'name': 'Alice', 'age': '30'})
        result = await valkey_read(command='HGETALL', args=[key])
        assert result['status'] == 'success'
        assert result['result']['name'] == 'Alice'
        await client.delete([key])

    async def test_exists(self, client):
        key = _k('ex1')
        await client.set(key, '1')
        result = await valkey_read(command='EXISTS', args=[key])
        assert result['status'] == 'success'
        assert result['result'] == 1
        await client.delete([key])

    async def test_type(self, client):
        key = _k('type1')
        await client.set(key, 'val')
        result = await valkey_read(command='TYPE', args=[key])
        assert result['status'] == 'success'
        assert result['result'] == 'string'
        await client.delete([key])

    async def test_info(self):
        result = await valkey_read(command='INFO', args=['server'])
        assert result['status'] == 'success'
        assert isinstance(result['result'], str)

    async def test_dbsize(self):
        result = await valkey_read(command='DBSIZE')
        assert result['status'] == 'success'
        assert isinstance(result['result'], int)

    async def test_scan(self, client):
        key = _k('scan1')
        await client.set(key, 'v')
        result = await valkey_read(
            command='SCAN', args=['0', 'MATCH', f'{_PREFIX}:scan*', 'COUNT', '100']
        )
        assert result['status'] == 'success'
        await client.delete([key])

    async def test_blocked_command(self):
        result = await valkey_read(command='SET', args=['k', 'v'])
        assert result['status'] == 'error'


class TestValkeyWriteLive:
    async def test_set_and_get(self):
        key = _k('w1')
        result = await valkey_write(command='SET', args=[key, 'world'])
        assert result['status'] == 'success'
        get_result = await valkey_read(command='GET', args=[key])
        assert get_result['result'] == 'world'
        await valkey_write(command='DEL', args=[key])

    async def test_hset_and_hget(self):
        key = _k('wh1')
        result = await valkey_write(command='HSET', args=[key, 'color', 'blue'])
        assert result['status'] == 'success'
        get_result = await valkey_read(command='HGET', args=[key, 'color'])
        assert get_result['result'] == 'blue'
        await valkey_write(command='DEL', args=[key])

    async def test_lpush_and_lrange(self):
        key = _k('wl1')
        await valkey_write(command='LPUSH', args=[key, 'a', 'b', 'c'])
        result = await valkey_read(command='LRANGE', args=[key, '0', '-1'])
        assert result['status'] == 'success'
        assert len(result['result']) == 3
        await valkey_write(command='DEL', args=[key])

    async def test_sadd_and_smembers(self):
        key = _k('ws1')
        await valkey_write(command='SADD', args=[key, 'x', 'y', 'z'])
        result = await valkey_read(command='SMEMBERS', args=[key])
        assert result['status'] == 'success'
        assert set(result['result']) == {'x', 'y', 'z'}
        await valkey_write(command='DEL', args=[key])

    async def test_expire_and_ttl(self):
        key = _k('wttl')
        await valkey_write(command='SET', args=[key, 'temp'])
        await valkey_write(command='EXPIRE', args=[key, '300'])
        result = await valkey_read(command='TTL', args=[key])
        assert result['status'] == 'success'
        assert result['result'] > 0
        await valkey_write(command='DEL', args=[key])

    async def test_incr(self):
        key = _k('wcnt')
        await valkey_write(command='SET', args=[key, '10'])
        result = await valkey_write(command='INCR', args=[key])
        assert result['status'] == 'success'
        assert result['result'] == 11
        await valkey_write(command='DEL', args=[key])

    async def test_blocked_flushall(self):
        result = await valkey_write(command='FLUSHALL')
        assert result['status'] == 'error'

    async def test_blocked_eval(self):
        result = await valkey_write(command='EVAL', args=['return 1', '0'])
        assert result['status'] == 'error'


class TestValkeyAdminLive:
    async def test_disabled_by_default(self):
        with patch.dict('os.environ', {'VALKEY_ADMIN_ENABLED': ''}):
            result = await valkey_admin(command='FLUSHDB', confirm=True)
        assert result['status'] == 'error'
        assert 'disabled' in result['reason'].lower()

    async def test_requires_confirm(self):
        with patch.dict('os.environ', {'VALKEY_ADMIN_ENABLED': 'true'}):
            result = await valkey_admin(command='FLUSHDB')
        assert result['status'] == 'error'
        assert 'confirm' in result['reason'].lower()

    async def test_config_get_via_admin(self):
        """CONFIG SET requires admin, verify it works with both gates."""
        with patch.dict('os.environ', {'VALKEY_ADMIN_ENABLED': 'true'}):
            result = await valkey_admin(
                command='CONFIG SET',
                args=['hz', '15'],
                confirm=True,
            )
        assert result['status'] == 'success'
        # Reset to default
        with patch.dict('os.environ', {'VALKEY_ADMIN_ENABLED': 'true'}):
            await valkey_admin(command='CONFIG SET', args=['hz', '10'], confirm=True)
