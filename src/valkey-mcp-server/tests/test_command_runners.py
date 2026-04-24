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

"""Unit tests for Command Runner tools (valkey_read, valkey_write, valkey_admin)."""

import pytest
from awslabs.valkey_mcp_server.tools.valkey_admin import valkey_admin
from awslabs.valkey_mcp_server.tools.valkey_read import valkey_read
from awslabs.valkey_mcp_server.tools.valkey_write import valkey_write
from unittest.mock import AsyncMock, patch


pytestmark = pytest.mark.asyncio

READ_MOD = 'awslabs.valkey_mcp_server.tools.valkey_read'
WRITE_MOD = 'awslabs.valkey_mcp_server.tools.valkey_write'
ADMIN_MOD = 'awslabs.valkey_mcp_server.tools.valkey_admin'


@pytest.fixture()
def mock_client():
    c = AsyncMock()
    c.custom_command = AsyncMock(return_value=b'OK')
    return c


# ── valkey_read ──────────────────────────────────────────────────────────


class TestValkeyRead:
    @pytest.fixture(autouse=True)
    def _patch(self, mock_client):
        with patch(f'{READ_MOD}.get_client', AsyncMock(return_value=mock_client)):
            yield

    async def test_allowed_command(self, mock_client):
        result = await valkey_read(command='GET', args=['mykey'])
        assert result['status'] == 'success'
        mock_client.custom_command.assert_called_with(['GET', 'mykey'])

    async def test_case_insensitive(self, mock_client):
        result = await valkey_read(command='get', args=['k'])
        assert result['status'] == 'success'
        mock_client.custom_command.assert_called_with(['GET', 'k'])

    async def test_no_args(self, mock_client):
        mock_client.custom_command.return_value = 42
        result = await valkey_read(command='DBSIZE')
        assert result == {'status': 'success', 'result': 42}

    async def test_blocked_write_command(self):
        result = await valkey_read(command='SET', args=['k', 'v'])
        assert result['status'] == 'error'
        assert 'not in the read allowlist' in result['reason']

    async def test_blocked_admin_command(self):
        result = await valkey_read(command='FLUSHALL')
        assert result['status'] == 'error'

    async def test_decodes_bytes(self, mock_client):
        mock_client.custom_command.return_value = [b'key1', b'val1']
        result = await valkey_read(command='MGET', args=['key1'])
        assert result['result'] == ['key1', 'val1']

    async def test_decodes_dict(self, mock_client):
        mock_client.custom_command.return_value = {b'f1': b'v1'}
        result = await valkey_read(command='HGETALL', args=['k'])
        assert result['result'] == {'f1': 'v1'}

    async def test_scan_command(self, mock_client):
        mock_client.custom_command.return_value = [b'0', [b'k1', b'k2']]
        result = await valkey_read(command='SCAN', args=['0'])
        assert result['status'] == 'success'

    async def test_ft_search_allowed(self, mock_client):
        result = await valkey_read(command='FT.SEARCH', args=['idx', '*'])
        assert result['status'] == 'success'

    async def test_error_handling(self, mock_client):
        from glide_shared.exceptions import RequestError

        mock_client.custom_command.side_effect = RequestError('connection lost')
        result = await valkey_read(command='GET', args=['k'])
        assert result['status'] == 'error'
        assert 'connection lost' in result['reason']


# ── valkey_write ─────────────────────────────────────────────────────────


class TestValkeyWrite:
    @pytest.fixture(autouse=True)
    def _patch(self, mock_client):
        with patch(f'{WRITE_MOD}.get_client', AsyncMock(return_value=mock_client)):
            yield

    async def test_allowed_command(self, mock_client):
        result = await valkey_write(command='SET', args=['k', 'v'])
        assert result['status'] == 'success'
        mock_client.custom_command.assert_called_with(['SET', 'k', 'v'])

    async def test_hset(self, mock_client):
        result = await valkey_write(command='HSET', args=['h', 'f', 'v'])
        assert result['status'] == 'success'

    async def test_del(self, mock_client):
        result = await valkey_write(command='DEL', args=['k1', 'k2'])
        assert result['status'] == 'success'

    async def test_blocked_flushall(self):
        result = await valkey_write(command='FLUSHALL')
        assert result['status'] == 'error'
        assert 'blocked' in result['reason'].lower()

    async def test_blocked_shutdown(self):
        result = await valkey_write(command='SHUTDOWN')
        assert result['status'] == 'error'

    async def test_blocked_eval(self):
        result = await valkey_write(command='EVAL', args=['return 1', '0'])
        assert result['status'] == 'error'

    async def test_blocked_config(self):
        result = await valkey_write(command='CONFIG', args=['SET', 'x', 'y'])
        assert result['status'] == 'error'

    async def test_read_command_rejected(self):
        result = await valkey_write(command='GET', args=['k'])
        assert result['status'] == 'error'
        assert 'not in the write allowlist' in result['reason']

    async def test_readonly_mode(self):
        with patch('awslabs.valkey_mcp_server.context.Context') as ctx:
            ctx.readonly_mode.return_value = True
            result = await valkey_write(command='SET', args=['k', 'v'])
        assert result['status'] == 'error'
        assert 'Readonly' in result['reason']

    async def test_json_set_allowed(self, mock_client):
        result = await valkey_write(command='JSON.SET', args=['k', '$', '{}'])
        assert result['status'] == 'success'

    async def test_ft_create_allowed(self, mock_client):
        result = await valkey_write(
            command='FT.CREATE', args=['idx', 'ON', 'HASH', 'SCHEMA', 'f', 'TEXT']
        )
        assert result['status'] == 'success'


# ── valkey_admin ─────────────────────────────────────────────────────────


class TestValkeyAdmin:
    @pytest.fixture(autouse=True)
    def _patch(self, mock_client):
        with patch(f'{ADMIN_MOD}.get_client', AsyncMock(return_value=mock_client)):
            yield

    async def test_flushall_with_confirm(self, mock_client):
        with patch.dict('os.environ', {'VALKEY_ADMIN_ENABLED': 'true'}):
            result = await valkey_admin(command='FLUSHALL', confirm=True)
        assert result['status'] == 'success'

    async def test_config_set_with_confirm(self, mock_client):
        with patch.dict('os.environ', {'VALKEY_ADMIN_ENABLED': 'true'}):
            result = await valkey_admin(
                command='CONFIG SET', args=['maxmemory', '2gb'], confirm=True
            )
        assert result['status'] == 'success'
        mock_client.custom_command.assert_called_with(['CONFIG', 'SET', 'maxmemory', '2gb'])

    async def test_disabled_by_default(self):
        with patch.dict('os.environ', {}, clear=True):
            result = await valkey_admin(command='FLUSHALL', confirm=True)
        assert result['status'] == 'error'
        assert 'disabled' in result['reason'].lower()

    async def test_requires_confirm(self):
        with patch.dict('os.environ', {'VALKEY_ADMIN_ENABLED': 'true'}):
            result = await valkey_admin(command='FLUSHALL', confirm=False)
        assert result['status'] == 'error'
        assert 'confirm=True' in result['reason']

    async def test_confirm_default_false(self):
        with patch.dict('os.environ', {'VALKEY_ADMIN_ENABLED': 'true'}):
            result = await valkey_admin(command='FLUSHALL')
        assert result['status'] == 'error'
        assert 'confirm=True' in result['reason']

    async def test_non_admin_command_rejected(self):
        with patch.dict('os.environ', {'VALKEY_ADMIN_ENABLED': 'true'}):
            result = await valkey_admin(command='GET', args=['k'], confirm=True)
        assert result['status'] == 'error'
        assert 'not in the admin allowlist' in result['reason']

    async def test_readonly_mode(self):
        with (
            patch.dict('os.environ', {'VALKEY_ADMIN_ENABLED': 'true'}),
            patch('awslabs.valkey_mcp_server.context.Context') as ctx,
        ):
            ctx.readonly_mode.return_value = True
            result = await valkey_admin(command='FLUSHALL', confirm=True)
        assert result['status'] == 'error'
        assert 'Readonly' in result['reason']

    async def test_eval_allowed(self, mock_client):
        with patch.dict('os.environ', {'VALKEY_ADMIN_ENABLED': 'true'}):
            result = await valkey_admin(command='EVAL', args=['return 1', '0'], confirm=True)
        assert result['status'] == 'success'

    async def test_double_gate_both_required(self):
        # Admin disabled + no confirm
        with patch.dict('os.environ', {}, clear=True):
            result = await valkey_admin(command='FLUSHALL')
        assert result['status'] == 'error'

    async def test_error_handling(self, mock_client):
        from glide_shared.exceptions import RequestError

        mock_client.custom_command.side_effect = RequestError('refused')
        with patch.dict('os.environ', {'VALKEY_ADMIN_ENABLED': 'true'}):
            result = await valkey_admin(command='FLUSHALL', confirm=True)
        assert result['status'] == 'error'
        assert 'refused' in result['reason']
