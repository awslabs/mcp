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

"""Tests for the MCP server tools."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from awslabs.security_agent_mcp_server.server import mcp


def test_server_has_expected_tools():
    """Verify all expected tools are registered."""
    tools = mcp._tool_manager._tools
    expected = {
        'setup_check',
        'setup',
        'start_security_scan',
        'get_scan_status',
        'get_scan_findings',
        'list_scans',
        'stop_scan',

        'call_api',
        'get_api_guide',
    }
    assert set(tools.keys()) == expected


def test_server_name():
    """Verify server name is correct."""
    assert mcp.name == 'awslabs.security-agent-mcp-server'


def test_server_has_instructions():
    """Verify server has instructions set."""
    assert mcp.instructions is not None
    assert 'AWS Security Agent' in mcp.instructions


def test_server_tool_count():
    """Verify correct number of tools."""
    assert len(mcp._tool_manager._tools) == 9


class TestSetupCheck:
    """Tests for setup_check tool."""

    @pytest.mark.asyncio
    @patch('awslabs.security_agent_mcp_server.server._state')
    @patch('awslabs.security_agent_mcp_server.server._client')
    async def test_ready(self, mock_client, mock_state):
        """Returns ready when all configured."""
        mock_state.get_config.return_value = {
            'agent_space_id': 'as-1',
            'service_role': 'arn:role',
            's3_bucket': 'bucket',
        }
        mock_client.get_caller_identity.return_value = {'Account': '123'}
        ctx = MagicMock()
        ctx.error = AsyncMock()

        from awslabs.security_agent_mcp_server.server import setup_check

        result = await setup_check(ctx)
        assert 'true' in result or '"ready": true' in result

    @pytest.mark.asyncio
    @patch('awslabs.security_agent_mcp_server.server._state')
    @patch('awslabs.security_agent_mcp_server.server._client')
    async def test_not_ready(self, mock_client, mock_state):
        """Returns missing items when not configured."""
        mock_state.get_config.return_value = {}
        mock_client.get_caller_identity.return_value = {'Account': '123'}
        ctx = MagicMock()
        ctx.error = AsyncMock()

        from awslabs.security_agent_mcp_server.server import setup_check

        result = await setup_check(ctx)
        assert 'false' in result or '"ready": false' in result
        assert 'agent_space_id' in result

    @pytest.mark.asyncio
    @patch('awslabs.security_agent_mcp_server.server._state')
    @patch('awslabs.security_agent_mcp_server.server._client')
    async def test_creds_error(self, mock_client, mock_state):
        """Reports credential error."""
        mock_state.get_config.return_value = {
            'agent_space_id': 'as-1',
            'service_role': 'arn:role',
            's3_bucket': 'bucket',
        }
        mock_client.get_caller_identity.side_effect = Exception('no creds')
        ctx = MagicMock()
        ctx.error = AsyncMock()

        from awslabs.security_agent_mcp_server.server import setup_check

        result = await setup_check(ctx)
        assert 'aws_credentials' in result


class TestSetup:
    """Tests for setup tool."""

    @pytest.mark.asyncio
    @patch('awslabs.security_agent_mcp_server.server._state')
    @patch('awslabs.security_agent_mcp_server.server._client')
    async def test_creates_new_space_and_role(self, mock_client, mock_state):
        """Creates agent space and role when nothing provided."""
        mock_client.get_caller_identity.return_value = {'Account': '123456789012'}
        mock_client.create_service_role.return_value = 'arn:aws:iam::123456789012:role/SecurityAgentScanRole'
        mock_client.create_agent_space.return_value = {'agentSpaceId': 'as-new'}
        mock_state.get_config.return_value = {}
        mock_state.update_config = MagicMock()
        ctx = MagicMock()
        ctx.error = AsyncMock()

        from awslabs.security_agent_mcp_server.server import setup

        result = await setup(ctx, name='test', agent_space_id=None, service_role_arn=None)
        assert 'ready' in result
        assert 'as-new' in result

    @pytest.mark.asyncio
    @patch('awslabs.security_agent_mcp_server.server._state')
    @patch('awslabs.security_agent_mcp_server.server._client')
    async def test_uses_existing_space_and_role(self, mock_client, mock_state):
        """Uses existing space and role when provided."""
        mock_client.get_caller_identity.return_value = {'Account': '123456789012'}
        mock_client.get_agent_space.return_value = {
            'name': 'existing', 'awsResources': {'iamRoles': ['arn:existing'], 's3Buckets': []}
        }
        mock_client.update_agent_space.return_value = {}
        mock_state.get_config.return_value = {}
        mock_state.update_config = MagicMock()
        ctx = MagicMock()
        ctx.error = AsyncMock()

        from awslabs.security_agent_mcp_server.server import setup

        result = await setup(ctx, name=None, agent_space_id='as-exist', service_role_arn='arn:my-role')
        assert 'ready' in result
        assert 'arn:my-role' in result



class TestCallApi:
    """Tests for call_api tool."""

    @pytest.mark.asyncio
    @patch('awslabs.security_agent_mcp_server.server._client')
    async def test_call_api_success(self, mock_client):
        """Calls API successfully."""
        mock_client.call.return_value = {'result': 'ok'}
        ctx = MagicMock()
        ctx.error = AsyncMock()

        from awslabs.security_agent_mcp_server.server import call_api

        result = await call_api(ctx, operation='ListAgentSpaces', params={})
        assert 'ok' in result

    @pytest.mark.asyncio
    @patch('awslabs.security_agent_mcp_server.server._client')
    async def test_call_api_invalid_operation(self, mock_client):
        """Rejects invalid operation names."""
        ctx = MagicMock()
        ctx.error = AsyncMock()

        from awslabs.security_agent_mcp_server.server import call_api

        result = await call_api(ctx, operation='../evil', params={})
        assert 'Invalid operation' in result


class TestGetApiGuide:
    """Tests for get_api_guide tool."""

    @pytest.mark.asyncio
    async def test_returns_guide(self):
        """Returns operations list."""
        ctx = MagicMock()
        ctx.error = AsyncMock()

        from awslabs.security_agent_mcp_server.server import get_api_guide

        result = await get_api_guide(ctx)
        assert 'documentation' in result
        assert 'operations' in result


class TestSetupCheckNotReady:
    """Tests for setup_check listing spaces."""

    @pytest.mark.asyncio
    @patch('awslabs.security_agent_mcp_server.server._client')
    @patch('awslabs.security_agent_mcp_server.server._state')
    async def test_lists_existing_spaces(self, mock_state, mock_client):
        """Returns existing spaces when not ready."""
        mock_state.get_config.return_value = {}
        mock_client.get_caller_identity.return_value = {'Account': '123'}
        mock_client.list_agent_spaces.return_value = [{'agentSpaceId': 'as-1', 'name': 'test'}]
        ctx = MagicMock()
        ctx.error = AsyncMock()

        from awslabs.security_agent_mcp_server.server import setup_check

        result = await setup_check(ctx)
        assert 'existing_agent_spaces' in result
        assert 'as-1' in result


class TestStartSecurityScan:
    """Tests for start_security_scan lazy bucket creation."""

    @pytest.mark.asyncio
    @patch('awslabs.security_agent_mcp_server.server._scanner')
    @patch('awslabs.security_agent_mcp_server.server._state')
    @patch('awslabs.security_agent_mcp_server.server._client')
    async def test_creates_bucket_when_missing(self, mock_client, mock_state, mock_scanner):
        """Creates S3 bucket on first scan when not in config."""
        mock_state.get_config.return_value = {'agent_space_id': 'as-1', 'service_role': 'arn:role'}
        mock_client.get_caller_identity.return_value = {'Account': '123456789012'}
        mock_client.create_s3_bucket.return_value = 'bucket'
        mock_state.update_config = MagicMock()
        mock_scanner.start_scan = AsyncMock(return_value={'scan_id': 'scan-1'})
        ctx = MagicMock()
        ctx.error = AsyncMock()

        from awslabs.security_agent_mcp_server.server import start_security_scan

        result = await start_security_scan(ctx, path='.', title='test')
        mock_client.create_s3_bucket.assert_called_once()
        assert 'scan-1' in result

    @pytest.mark.asyncio
    @patch('awslabs.security_agent_mcp_server.server._scanner')
    @patch('awslabs.security_agent_mcp_server.server._state')
    @patch('awslabs.security_agent_mcp_server.server._client')
    async def test_handles_bucket_already_exists(self, mock_client, mock_state, mock_scanner):
        """Handles BucketAlreadyOwnedByYou gracefully."""
        mock_state.get_config.return_value = {'agent_space_id': 'as-1', 'service_role': 'arn:role'}
        mock_client.get_caller_identity.return_value = {'Account': '123456789012'}
        error = MagicMock()
        error.response = {'Error': {'Code': 'BucketAlreadyOwnedByYou'}}
        mock_client.create_s3_bucket.side_effect = error
        mock_state.update_config = MagicMock()
        mock_scanner.start_scan = AsyncMock(return_value={'scan_id': 'scan-1'})
        ctx = MagicMock()
        ctx.error = AsyncMock()

        from awslabs.security_agent_mcp_server.server import start_security_scan

        result = await start_security_scan(ctx, path='.', title='test')
        assert 'scan-1' in result

    @pytest.mark.asyncio
    @patch('awslabs.security_agent_mcp_server.server._state')
    async def test_not_configured(self, mock_state):
        """Returns error when not configured."""
        mock_state.get_config.return_value = {}
        ctx = MagicMock()
        ctx.error = AsyncMock()

        from awslabs.security_agent_mcp_server.server import start_security_scan

        result = await start_security_scan(ctx, path='.', title='test')
        assert 'error' in result
        assert 'Not configured' in result
